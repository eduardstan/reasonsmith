import { createHash } from "node:crypto"
import { copyFile, mkdir, readFile, stat, writeFile } from "node:fs/promises"
import { basename, delimiter, dirname, isAbsolute, join, relative, resolve, sep } from "node:path"
import { resolveTerminalControlBinary } from "@kitlangton/terminal-control"

export type VerificationResult = "passed" | "failed" | "unverified"

export interface EvidenceBundleOptions {
  /** Recording produced by a `termctrl start --record` session. */
  readonly recordingPath: string
  /** Directory that will contain PR-safe evidence. */
  readonly outputDirectory: string
  readonly result: VerificationResult
  readonly title?: string
  readonly summary?: string
  /** Public repository-relative path used in generated PR Markdown. */
  readonly linkBase?: string
  /** Inspect and capture the recording at this marker instead of its final frame. */
  readonly atMarker?: string
  /** Inspect and capture the recording at this timestamp instead of its final frame. */
  readonly atMs?: number
  /** Marker-based video edit plan accepted by `termctrl video`. */
  readonly editPath?: string
  readonly binaryPath?: string
  readonly video?: boolean
  readonly preview?: boolean
  readonly footer?: boolean
  readonly hideCursor?: boolean
  readonly fps?: number
  readonly tailMs?: number
  /** Raw recordings contain terminal input and are excluded by default. */
  readonly includeRecording?: boolean
}

export interface EvidenceArtifact {
  readonly kind:
    | "screen-text"
    | "screen-frame"
    | "screen-svg"
    | "screen-png"
    | "video"
    | "preview"
    | "recording"
    | "pr-markdown"
  readonly path: string
  readonly bytes: number
  readonly sha256: string
}

export interface EvidenceManifest {
  readonly version: 1
  readonly createdAt: string
  readonly result: VerificationResult
  readonly title: string
  readonly summary: string
  readonly capture: {
    readonly marker?: string
    readonly atMs?: number
    readonly final: boolean
  }
  readonly sourceRecordingSha256: string
  readonly artifacts: ReadonlyArray<EvidenceArtifact>
}

export interface EvidenceBundle {
  readonly directory: string
  readonly manifest: string
  readonly screenText: string
  readonly screenFrame: string
  readonly screenSvg: string
  readonly screenPng: string
  readonly video?: string
  readonly preview?: string
  readonly recording?: string
  readonly prMarkdown: string
}

export interface GitHubTuiEvidence {
  readonly manifest: string
  readonly manifestSha256: string
  readonly directory: string
  readonly result: VerificationResult
  readonly title: string
  readonly summary: string
  readonly screen: string
  readonly preview?: string
  readonly video?: string
  readonly recording?: string
  readonly totalBytes: number
}

export type GitHubTuiEvidenceSnapshot = ReadonlyMap<string, string>

export const GITHUB_TUI_EVIDENCE_START = "<!-- nikcli-tui-evidence:start -->"
export const GITHUB_TUI_EVIDENCE_END = "<!-- nikcli-tui-evidence:end -->"
const MAX_GITHUB_ARTIFACT_BYTES = 95 * 1024 * 1024

class EvidenceCommandError extends Error {
  constructor(command: readonly string[], stderr: string, code: number) {
    const detail = stderr.trim().slice(-2_000)
    super(`Evidence command failed (${code}): ${command.join(" ")}${detail ? `\n${detail}` : ""}`)
    this.name = "EvidenceCommandError"
  }
}

async function run(command: readonly string[], env?: Record<string, string | undefined>): Promise<string> {
  const child = Bun.spawn([...command], {
    stdout: "pipe",
    stderr: "pipe",
    ...(env ? { env } : {}),
  })
  const stdout = new Response(child.stdout).text()
  const stderr = new Response(child.stderr).text()
  const [code, output, errors] = await Promise.all([child.exited, stdout, stderr])
  if (code !== 0) throw new EvidenceCommandError(command, errors, code)
  return output
}

async function resolveFfmpegBinary(): Promise<string> {
  const system = Bun.which("ffmpeg")
  if (system) return system
  const module = await import("@ffmpeg-installer/ffmpeg")
  const installer = module.default
  if (installer.path) return installer.path
  throw new Error("Video evidence requires ffmpeg, but neither PATH nor @ffmpeg-installer/ffmpeg provides it.")
}

function captureSelector(options: EvidenceBundleOptions): string[] {
  if (options.atMarker !== undefined && options.atMs !== undefined) {
    throw new Error("Evidence capture accepts either atMarker or atMs, not both.")
  }
  if (options.atMarker !== undefined) {
    if (options.atMarker.trim().length === 0) throw new Error("Evidence marker must not be empty.")
    return ["--at-marker", options.atMarker]
  }
  if (options.atMs !== undefined) {
    if (!Number.isSafeInteger(options.atMs) || options.atMs < 0) {
      throw new Error("Evidence timestamp must be a non-negative safe integer.")
    }
    return ["--at-ms", String(options.atMs)]
  }
  return []
}

function normalizedLinkBase(options: EvidenceBundleOptions): string {
  const configured = options.linkBase?.trim()
  if (configured) return configured.replaceAll("\\", "/").replace(/\/$/u, "")
  if (!resolve(options.outputDirectory).startsWith(`${process.cwd()}${sep}`)) return basename(options.outputDirectory)
  return relative(process.cwd(), resolve(options.outputDirectory)).replaceAll("\\", "/") || "."
}

function markdownText(value: string): string {
  return value.replace(/[\r\n]+/gu, " ").trim()
}

function statusLine(result: VerificationResult): string {
  if (result === "passed") return "✅ TUI verification passed."
  if (result === "failed") return "❌ TUI verification failed."
  return "⚪ TUI verification recorded without a pass/fail assertion."
}

function isVerificationResult(value: unknown): value is VerificationResult {
  return value === "passed" || value === "failed" || value === "unverified"
}

function repoPath(root: string, value: string): string {
  const output = relative(root, value).replaceAll("\\", "/")
  if (!output || output === ".." || output.startsWith("../") || isAbsolute(output)) {
    throw new Error(`TUI evidence escapes the repository: ${value}`)
  }
  return output
}

async function verifiedArtifact(
  root: string,
  directory: string,
  artifact: EvidenceArtifact | undefined,
): Promise<{ path: string; bytes: number } | undefined> {
  if (!artifact) return undefined
  const absolute = resolve(directory, artifact.path)
  const path = repoPath(root, absolute)
  const data = await readFile(absolute).catch(() => undefined)
  if (!data) throw new Error(`TUI evidence artifact is missing: ${path}`)
  if (data.byteLength !== artifact.bytes) throw new Error(`TUI evidence size mismatch: ${path}`)
  if (data.byteLength > MAX_GITHUB_ARTIFACT_BYTES) {
    throw new Error(`TUI evidence exceeds GitHub's safe file limit (${MAX_GITHUB_ARTIFACT_BYTES} bytes): ${path}`)
  }
  const sha256 = createHash("sha256").update(data).digest("hex")
  if (sha256 !== artifact.sha256) throw new Error(`TUI evidence checksum mismatch: ${path}`)
  return { path, bytes: data.byteLength }
}

/** Discover hash-verified evidence bundles that are safe to reference from a GitHub PR. */
export async function discoverGitHubTuiEvidence(repositoryRoot: string): Promise<GitHubTuiEvidence[]> {
  const root = resolve(repositoryRoot)
  const rootInfo = await stat(root).catch(() => undefined)
  if (!rootInfo?.isDirectory()) return []
  const glob = new Bun.Glob("artifacts/tui/**/manifest.json")
  const matches = await Array.fromAsync(
    glob.scan({ cwd: root, absolute: true, onlyFiles: true, followSymlinks: false }),
  )

  const bundles = await Promise.all(
    matches.sort().map(async (manifestPath) => {
      const raw = await readFile(manifestPath)
      const parsed = JSON.parse(raw.toString()) as Partial<EvidenceManifest>
      if (parsed.version !== 1 || !isVerificationResult(parsed.result) || typeof parsed.title !== "string") {
        throw new Error(`Invalid TUI evidence manifest: ${repoPath(root, manifestPath)}`)
      }
      const artifacts = Array.isArray(parsed.artifacts) ? parsed.artifacts : []
      const directory = dirname(manifestPath)
      const byKind = new Map(artifacts.map((artifact) => [artifact.kind, artifact]))
      const [screen, preview, video, recording] = await Promise.all([
        verifiedArtifact(root, directory, byKind.get("screen-png")),
        verifiedArtifact(root, directory, byKind.get("preview")),
        verifiedArtifact(root, directory, byKind.get("video")),
        verifiedArtifact(root, directory, byKind.get("recording")),
      ])
      if (!screen) throw new Error(`TUI evidence has no PNG screen: ${repoPath(root, manifestPath)}`)
      return {
        manifest: repoPath(root, manifestPath),
        manifestSha256: createHash("sha256").update(raw).digest("hex"),
        directory: repoPath(root, directory),
        result: parsed.result,
        title: parsed.title,
        summary: typeof parsed.summary === "string" ? parsed.summary : "",
        screen: screen.path,
        ...(preview ? { preview: preview.path } : {}),
        ...(video ? { video: video.path } : {}),
        ...(recording ? { recording: recording.path } : {}),
        totalBytes: [screen, preview, video, recording].reduce((total, item) => total + (item?.bytes ?? 0), 0),
      } satisfies GitHubTuiEvidence
    }),
  )
  return bundles
}

export function snapshotGitHubTuiEvidence(evidence: readonly GitHubTuiEvidence[]): GitHubTuiEvidenceSnapshot {
  return new Map(evidence.map((item) => [item.manifest, item.manifestSha256]))
}

export function changedGitHubTuiEvidence(
  evidence: readonly GitHubTuiEvidence[],
  before: GitHubTuiEvidenceSnapshot,
): GitHubTuiEvidence[] {
  return evidence.filter((item) => before.get(item.manifest) !== item.manifestSha256)
}

export function requestsTuiEvidence(prompt: string): boolean {
  const terminal = /\b(?:tui|opentui|terminal(?:e|i)?)\b/iu.test(prompt)
  const verification = /\b(?:test\w*|verif\w*|registr\w*|record\w*|video)\b/iu.test(prompt)
  return terminal && verification
}

export function assertCompleteGitHubTuiEvidence(evidence: readonly GitHubTuiEvidence[]): void {
  if (evidence.length === 0) {
    throw new Error("TUI verification was requested, but no new artifacts/tui evidence bundle was produced.")
  }
  for (const item of evidence) {
    const missing = [
      !item.preview && "preview.gif",
      !item.video && "demo.mp4",
      !item.recording && "recording.termctrl",
    ].filter(Boolean)
    if (missing.length > 0)
      throw new Error(`Incomplete TUI evidence bundle ${item.manifest}: missing ${missing.join(", ")}`)
  }
}

function encodedPath(value: string): string {
  return value.split("/").map(encodeURIComponent).join("/")
}

function markdownLabel(value: string): string {
  return markdownText(value).replaceAll("[", "\\[").replaceAll("]", "\\]")
}

/** Render immutable, commit-addressed GitHub links for one or more verified bundles. */
export function renderGitHubTuiEvidence(input: {
  readonly evidence: readonly GitHubTuiEvidence[]
  readonly repository: string
  readonly revision: string
}): string {
  if (input.evidence.length === 0) return ""
  const repository = input.repository.split("/").map(encodeURIComponent).join("/")
  const revision = encodeURIComponent(input.revision)
  const raw = (path: string) => `https://raw.githubusercontent.com/${repository}/${revision}/${encodedPath(path)}`
  const blob = (path: string) => `https://github.com/${repository}/blob/${revision}/${encodedPath(path)}?raw=1`
  const lines = [GITHUB_TUI_EVIDENCE_START, "", "## TUI evidence"]

  for (const item of input.evidence) {
    const title = markdownLabel(item.title) || "TUI verification"
    lines.push("", `### ${title}`, "", statusLine(item.result))
    if (item.summary.trim()) lines.push("", item.summary.trim())
    lines.push("", `![${title}](${raw(item.preview ?? item.screen)})`)
    if (item.video) lines.push("", `[Full MP4 recording](${blob(item.video)})`)
    if (item.recording) lines.push("", `[Raw .termctrl recording](${blob(item.recording)})`)
    lines.push("", `[Evidence manifest](${blob(item.manifest)})`)
  }

  lines.push("", GITHUB_TUI_EVIDENCE_END)
  return lines.join("\n")
}

/** Append or replace the generated evidence block without disturbing the rest of the PR body. */
export function mergeGitHubTuiEvidence(body: string, evidenceMarkdown: string): string {
  const start = body.indexOf(GITHUB_TUI_EVIDENCE_START)
  const end = start === -1 ? -1 : body.indexOf(GITHUB_TUI_EVIDENCE_END, start)
  const withoutPrevious =
    start === -1 || end === -1
      ? body.trimEnd()
      : `${body.slice(0, start).trimEnd()}${body.slice(end + GITHUB_TUI_EVIDENCE_END.length)}`.trimEnd()
  if (!evidenceMarkdown.trim()) return withoutPrevious
  return `${withoutPrevious}${withoutPrevious ? "\n\n" : ""}${evidenceMarkdown.trim()}\n`
}

export function renderPullRequestMarkdown(input: {
  readonly result: VerificationResult
  readonly title: string
  readonly summary: string
  readonly linkBase: string
  readonly hasVideo: boolean
  readonly hasPreview: boolean
  readonly hasRecording?: boolean
}): string {
  const title = markdownText(input.title) || "TUI verification"
  const base = input.linkBase.replace(/\/$/u, "")
  const image = input.hasPreview ? `${base}/preview.gif` : `${base}/screen.png`
  const lines = [`### ${title}`, "", statusLine(input.result)]
  if (input.summary.trim()) lines.push("", input.summary.trim())
  lines.push("", `![${title}](${image})`)
  if (input.hasVideo) lines.push("", `[Full MP4 recording](${base}/demo.mp4)`)
  if (input.hasRecording) lines.push("", `[Raw .termctrl recording](${base}/recording.termctrl)`)
  lines.push("")
  return lines.join("\n")
}

async function fingerprint(path: string, kind: EvidenceArtifact["kind"], directory: string): Promise<EvidenceArtifact> {
  const data = await readFile(path)
  return {
    kind,
    path: relative(directory, path).replaceAll("\\", "/"),
    bytes: data.byteLength,
    sha256: createHash("sha256").update(data).digest("hex"),
  }
}

async function createGifPreview(video: string, preview: string): Promise<void> {
  const ffmpeg = await resolveFfmpegBinary()
  await run([
    ffmpeg,
    "-y",
    "-loglevel",
    "error",
    "-i",
    video,
    "-filter_complex",
    "fps=10,scale=w='min(960,iw)':h=-2:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
    "-loop",
    "0",
    preview,
  ])
}

export async function createEvidenceBundle(options: EvidenceBundleOptions): Promise<EvidenceBundle> {
  const recordingPath = resolve(options.recordingPath)
  const recordingInfo = await stat(recordingPath).catch(() => undefined)
  if (!recordingInfo?.isFile()) throw new Error(`Terminal recording does not exist: ${recordingPath}`)

  const directory = resolve(options.outputDirectory)
  await mkdir(directory, { recursive: true })
  const binary = resolveTerminalControlBinary(options.binaryPath)
  const selector = captureSelector(options)
  const stem = join(directory, "screen")

  await run([
    binary,
    "save",
    "--recording",
    recordingPath,
    ...selector,
    "--format",
    "txt",
    "--format",
    "json",
    "--format",
    "svg",
    "--format",
    "png",
    "--out",
    stem,
  ])

  const screenText = `${stem}.txt`
  const screenFrame = `${stem}.json`
  const screenSvg = `${stem}.svg`
  const screenPng = `${stem}.png`
  const videoEnabled = options.video ?? true
  const previewEnabled = videoEnabled && (options.preview ?? true)
  const video = videoEnabled ? join(directory, "demo.mp4") : undefined
  const preview = previewEnabled ? join(directory, "preview.gif") : undefined

  if (video) {
    const ffmpeg = await resolveFfmpegBinary()
    const command = [
      binary,
      "video",
      recordingPath,
      "--out",
      video,
      "--fps",
      String(options.fps ?? 20),
      "--tail-ms",
      String(options.tailMs ?? 1000),
    ]
    if (options.footer ?? true) command.push("--footer")
    if (options.hideCursor ?? true) command.push("--hide-cursor")
    if (options.editPath) command.push("--edit", resolve(options.editPath))
    await run(command, {
      ...process.env,
      PATH: [dirname(ffmpeg), process.env.PATH].filter(Boolean).join(delimiter),
    })
  }
  if (video && preview) await createGifPreview(video, preview)

  let recording: string | undefined
  if (options.includeRecording) {
    recording = join(directory, "recording.termctrl")
    if (recording !== recordingPath) await copyFile(recordingPath, recording)
  }

  const title = markdownText(options.title ?? "TUI verification") || "TUI verification"
  const summary = options.summary?.trim() ?? ""
  const prMarkdown = join(directory, "pr.md")
  const markdown = renderPullRequestMarkdown({
    result: options.result,
    title,
    summary,
    linkBase: normalizedLinkBase(options),
    hasVideo: video !== undefined,
    hasPreview: preview !== undefined,
    hasRecording: recording !== undefined,
  })
  await writeFile(prMarkdown, markdown)

  const artifacts = await Promise.all([
    fingerprint(screenText, "screen-text", directory),
    fingerprint(screenFrame, "screen-frame", directory),
    fingerprint(screenSvg, "screen-svg", directory),
    fingerprint(screenPng, "screen-png", directory),
    ...(video ? [fingerprint(video, "video" as const, directory)] : []),
    ...(preview ? [fingerprint(preview, "preview" as const, directory)] : []),
    ...(recording ? [fingerprint(recording, "recording" as const, directory)] : []),
    fingerprint(prMarkdown, "pr-markdown", directory),
  ])
  const sourceRecordingSha256 = createHash("sha256")
    .update(await readFile(recordingPath))
    .digest("hex")
  const manifestData: EvidenceManifest = {
    version: 1,
    createdAt: new Date().toISOString(),
    result: options.result,
    title,
    summary,
    capture: {
      ...(options.atMarker !== undefined ? { marker: options.atMarker } : {}),
      ...(options.atMs !== undefined ? { atMs: options.atMs } : {}),
      final: options.atMarker === undefined && options.atMs === undefined,
    },
    sourceRecordingSha256,
    artifacts,
  }
  const manifest = join(directory, "manifest.json")
  await writeFile(manifest, `${JSON.stringify(manifestData, null, 2)}\n`)

  return {
    directory,
    manifest,
    screenText,
    screenFrame,
    screenSvg,
    screenPng,
    ...(video ? { video } : {}),
    ...(preview ? { preview } : {}),
    ...(recording ? { recording } : {}),
    prMarkdown,
  }
}
