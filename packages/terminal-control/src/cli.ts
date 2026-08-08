#!/usr/bin/env bun
import { lstat, mkdir, readFile, readlink, realpath, symlink } from "node:fs/promises"
import { dirname, join, relative, resolve } from "node:path"
import { pathToFileURL } from "node:url"
import { createEvidenceBundle, type EvidenceBundleOptions, type VerificationResult } from "./evidence"
import { resolveTerminalControlBinary } from "@kitlangton/terminal-control"

const HELP = `terminal-control COMMAND [options]

Commands other than bundle are forwarded to the native termctrl driver. Run
terminal-control COMMAND --help for native command details.

terminal-control install-skill [--workspace DIR] [--json]

Register the bundled skill in WORKSPACE/.agents/skills so nikcli discovers it.
WORKSPACE defaults to the nearest Git worktree. The installation is an
idempotent relative symlink back to this package.

terminal-control bundle --recording FILE --out DIR --result passed|failed|unverified [options]

Create screenshot, video, GIF preview, manifest and PR Markdown from a .termctrl recording.

Options:
  --title TEXT              PR section title
  --summary TEXT            Verification summary
  --link-base PATH          Repository-relative artifact path used by pr.md
  --at-marker NAME          Capture the screenshot at a recording marker
  --at-ms MS                Capture the screenshot at a timestamp
  --edit FILE               Marker-based termctrl video edit plan
  --binary FILE             Explicit termctrl binary
  --fps NUMBER              Video frames per second (default: 20)
  --tail-ms MS              Final-frame hold (default: 1000)
  --include-recording       Copy the sensitive raw recording into the bundle
  --no-video                Produce only screen evidence
  --no-preview              Do not produce an inline GIF preview
  --no-footer               Omit the video footer
  --show-cursor             Keep the terminal cursor in video
  --json                    Print the resulting bundle as JSON
  -h, --help                Show this help
`

export interface SkillInstallation {
  readonly source: string
  readonly target: string
  readonly installed: boolean
}

function samePath(left: string, right: string): boolean {
  return resolve(left) === resolve(right)
}

export async function findWorkspaceRoot(start = process.cwd()): Promise<string> {
  let current = resolve(start)
  while (true) {
    if (await lstat(join(current, ".git")).catch(() => undefined)) return current
    const parent = dirname(current)
    if (parent === current) return resolve(start)
    current = parent
  }
}

export async function installWorkspaceSkill(workspace?: string): Promise<SkillInstallation> {
  const root = workspace ? resolve(workspace) : await findWorkspaceRoot()
  const source = resolve(import.meta.dir, "../skills/terminal-control")
  const sourceManifest = join(source, "SKILL.md")
  const target = join(root, ".agents/skills/terminal-control")

  const manifest = await lstat(sourceManifest).catch(() => undefined)
  if (!manifest?.isFile()) throw new Error(`Bundled terminal-control skill is missing: ${sourceManifest}`)

  const existing = await lstat(target).catch(() => undefined)
  if (existing) {
    if (!existing.isSymbolicLink()) {
      throw new Error(`Skill target already exists and is not a symlink: ${target}`)
    }
    const linked = await readlink(target)
    const targetParent = await realpath(dirname(target)).catch(() => dirname(target))
    const linkedPath = resolve(targetParent, linked)
    const [actualSource, actualTarget] = await Promise.all([
      realpath(source).catch(() => source),
      realpath(linkedPath).catch(() => linkedPath),
    ])
    if (!samePath(actualSource, actualTarget)) {
      throw new Error(`Skill target points somewhere else: ${target} -> ${linked}`)
    }
    return { source, target, installed: false }
  }

  await mkdir(dirname(target), { recursive: true })
  const targetParent = await realpath(dirname(target)).catch(() => dirname(target))
  const link = relative(targetParent, source) || "."
  await symlink(link, target, process.platform === "win32" ? "junction" : "dir")
  return { source, target, installed: true }
}

function parseInstallOptions(argv: readonly string[]): { workspace?: string; json: boolean } {
  const args = [...argv]
  let workspace: string | undefined
  let json = false
  while (args.length > 0) {
    const arg = args.shift()!
    switch (arg) {
      case "--workspace":
        workspace = take(args, arg)
        break
      case "--json":
        json = true
        break
      case "-h":
      case "--help":
        throw new HelpRequested()
      default:
        throw new Error(`Unknown install-skill option: ${arg}`)
    }
  }
  return { ...(workspace ? { workspace } : {}), json }
}

export function renderAgentBundleOutput(
  bundle: Awaited<ReturnType<typeof createEvidenceBundle>>,
  prMarkdown: string,
): string {
  const preview = bundle.preview ?? bundle.screenPng
  const previewUrl = pathToFileURL(preview).href
  const lines = [
    "Terminal evidence created.",
    "",
    `PR Markdown: ${bundle.prMarkdown}`,
    `Manifest: ${bundle.manifest}`,
    `Full MP4: ${bundle.video ?? "not generated"}`,
    `Raw .termctrl: ${bundle.recording ?? "not included"}`,
    "",
    "Inline TUI preview (include this exact line in the assistant response):",
    `![TUI verification preview](<${previewUrl}>)`,
    "",
    "PR section:",
    prMarkdown.trimEnd(),
    "",
  ]
  return lines.join("\n")
}

function take(args: string[], name: string): string {
  const value = args.shift()
  if (value === undefined || value.startsWith("--")) throw new Error(`${name} requires a value.`)
  return value
}

function integer(value: string, name: string): number {
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed) || parsed < 0) throw new Error(`${name} must be a non-negative integer.`)
  return parsed
}

function result(value: string): VerificationResult {
  if (value === "passed" || value === "failed" || value === "unverified") return value
  throw new Error("--result must be passed, failed or unverified.")
}

export function parseBundleOptions(argv: readonly string[]): EvidenceBundleOptions & { readonly json: boolean } {
  const args = [...argv]
  type MutableOptions = {
    -readonly [Key in keyof EvidenceBundleOptions]?: EvidenceBundleOptions[Key]
  }
  const options: MutableOptions & { json?: boolean } = {}
  while (args.length > 0) {
    const arg = args.shift()!
    switch (arg) {
      case "--recording":
        options.recordingPath = take(args, arg)
        break
      case "--out":
        options.outputDirectory = take(args, arg)
        break
      case "--result":
        options.result = result(take(args, arg))
        break
      case "--title":
        options.title = take(args, arg)
        break
      case "--summary":
        options.summary = take(args, arg)
        break
      case "--link-base":
        options.linkBase = take(args, arg)
        break
      case "--at-marker":
        options.atMarker = take(args, arg)
        break
      case "--at-ms":
        options.atMs = integer(take(args, arg), arg)
        break
      case "--edit":
        options.editPath = take(args, arg)
        break
      case "--binary":
        options.binaryPath = take(args, arg)
        break
      case "--fps":
        options.fps = integer(take(args, arg), arg)
        break
      case "--tail-ms":
        options.tailMs = integer(take(args, arg), arg)
        break
      case "--include-recording":
        options.includeRecording = true
        break
      case "--no-video":
        options.video = false
        break
      case "--no-preview":
        options.preview = false
        break
      case "--no-footer":
        options.footer = false
        break
      case "--show-cursor":
        options.hideCursor = false
        break
      case "--json":
        options.json = true
        break
      case "-h":
      case "--help":
        throw new HelpRequested()
      default:
        throw new Error(`Unknown bundle option: ${arg}`)
    }
  }
  if (!options.recordingPath) throw new Error("bundle requires --recording FILE.")
  if (!options.outputDirectory) throw new Error("bundle requires --out DIR.")
  if (!options.result) throw new Error("bundle requires --result passed|failed|unverified.")
  return {
    ...options,
    recordingPath: options.recordingPath,
    outputDirectory: options.outputDirectory,
    result: options.result,
    json: options.json ?? false,
  }
}

class HelpRequested extends Error {}

async function runNative(args: readonly string[]): Promise<void> {
  const child = Bun.spawn([resolveTerminalControlBinary(), ...args], {
    stdin: "inherit",
    stdout: "inherit",
    stderr: "inherit",
  })
  const code = await child.exited
  if (code !== 0) process.exitCode = code
}

export async function main(argv = Bun.argv.slice(2)): Promise<void> {
  const [command, ...args] = argv
  if (command === undefined || command === "help" || command === "--help" || command === "-h") {
    process.stdout.write(HELP)
    return
  }
  if (command === "install-skill") {
    try {
      const options = parseInstallOptions(args)
      const installation = await installWorkspaceSkill(options.workspace)
      if (options.json) {
        process.stdout.write(`${JSON.stringify(installation, null, 2)}\n`)
        return
      }
      const action = installation.installed ? "Installed" : "Already installed"
      process.stdout.write(`${action}: ${installation.target}\nRestart nikcli to load the skill.\n`)
    } catch (error) {
      if (error instanceof HelpRequested) {
        process.stdout.write(HELP)
        return
      }
      throw error
    }
    return
  }
  if (command !== "bundle") {
    await runNative([command, ...args])
    return
  }
  try {
    const { json, ...options } = parseBundleOptions(args)
    const bundle = await createEvidenceBundle(options)
    if (json) {
      process.stdout.write(`${JSON.stringify(bundle, null, 2)}\n`)
      return
    }
    const prMarkdown = await readFile(bundle.prMarkdown, "utf8")
    process.stdout.write(renderAgentBundleOutput(bundle, prMarkdown))
  } catch (error) {
    if (error instanceof HelpRequested) {
      process.stdout.write(HELP)
      return
    }
    throw error
  }
}

if (import.meta.main) {
  main().catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`)
    process.exitCode = 1
  })
}
