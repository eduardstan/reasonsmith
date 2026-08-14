import { afterAll, beforeAll, describe, expect, test } from "bun:test"
import { describeNativeBinary } from "./pty"
import { lstat, mkdir, mkdtemp, readFile, realpath, rm, stat } from "node:fs/promises"
import { join } from "node:path"
import { tmpdir } from "node:os"
import { pathToFileURL } from "node:url"
import { TerminalControl } from "@kitlangton/terminal-control"
import { findWorkspaceRoot, installWorkspaceSkill, parseBundleOptions, renderAgentBundleOutput } from "../src/cli"
import {
  assertCompleteGitHubTuiEvidence,
  changedGitHubTuiEvidence,
  createEvidenceBundle,
  discoverGitHubTuiEvidence,
  GITHUB_TUI_EVIDENCE_START,
  mergeGitHubTuiEvidence,
  renderGitHubTuiEvidence,
  renderPullRequestMarkdown,
  requestsTuiEvidence,
  snapshotGitHubTuiEvidence,
} from "../src/evidence"

describe("PR evidence", () => {
  test("renders inline preview and MP4 link", () => {
    const markdown = renderPullRequestMarkdown({
      result: "passed",
      title: "Provider dialog",
      summary: "Keyboard navigation completed.",
      linkBase: "artifacts/provider",
      hasVideo: true,
      hasPreview: true,
      hasRecording: true,
    })
    expect(markdown).toContain("✅ TUI verification passed.")
    expect(markdown).toContain("![Provider dialog](artifacts/provider/preview.gif)")
    expect(markdown).toContain("[Full MP4 recording](artifacts/provider/demo.mp4)")
    expect(markdown).toContain("[Raw .termctrl recording](artifacts/provider/recording.termctrl)")
  })

  test("requires explicit verification result", () => {
    expect(() => parseBundleOptions(["--recording", "run.termctrl", "--out", "artifacts/run"])).toThrow(
      "bundle requires --result",
    )
  })

  test("recognizes natural-language TUI evidence requests", () => {
    expect(requestsTuiEvidence("fai questo e testa il TUI con un video")).toBe(true)
    expect(requestsTuiEvidence("verify the OpenTUI and record it")).toBe(true)
    expect(requestsTuiEvidence("fix the API tests")).toBe(false)
  })
})

describeNativeBinary("native evidence bundle", () => {
  let root = ""
  let recording = ""

  beforeAll(async () => {
    root = await mkdtemp(join(tmpdir(), "terminal-control-evidence-"))
    recording = join(root, "source.termctrl")
    const control = await TerminalControl.make()
    const session = await control.launch({
      command: ["/bin/sh", "-c", "printf '\\033[32mREADY\\033[0m'; sleep 0.15; printf '\\rDONE'"],
      viewport: { cols: 20, rows: 4 },
      record: recording,
      inheritEnv: false,
      env: { TERM: "xterm-256color" },
    })
    await session.screen.waitForText("DONE", { timeoutMs: 5_000 })
    await session.waitForExit({ timeoutMs: 5_000 })
    await session.stop()
    await control.close()
  })

  afterAll(async () => {
    if (root) await rm(root, { recursive: true, force: true })
  })

  test("creates screen artifacts and a versioned manifest", async () => {
    const bundle = await createEvidenceBundle({
      recordingPath: recording,
      outputDirectory: join(root, "screens"),
      linkBase: "artifacts/screens",
      result: "passed",
      title: "Recorded shell",
      summary: "READY transitioned to DONE.",
      video: false,
    })
    const manifest = JSON.parse(await readFile(bundle.manifest, "utf8"))
    expect(manifest.version).toBe(1)
    expect(manifest.result).toBe("passed")
    expect(manifest.artifacts.length).toBe(5)
    expect(await readFile(bundle.screenText, "utf8")).toContain("DONE")
    expect((await stat(bundle.screenPng)).size).toBeGreaterThan(0)
    expect(await readFile(bundle.prMarkdown, "utf8")).toContain("artifacts/screens/screen.png")
  }, 15_000)

  test("installs the bundled skill idempotently for workspace discovery", async () => {
    const first = await installWorkspaceSkill(root)
    const second = await installWorkspaceSkill(root)
    expect(first.installed).toBe(true)
    expect(second.installed).toBe(false)
    expect((await lstat(first.target)).isSymbolicLink()).toBe(true)
    expect(await realpath(first.target)).toBe(await realpath(first.source))
    expect(await readFile(join(first.target, "SKILL.md"), "utf8")).toContain("name: terminal-control")
  })

  test("finds the nearest Git worktree when --workspace is omitted", async () => {
    const repository = join(root, "repository")
    const nested = join(repository, "packages/example")
    await Promise.all([mkdir(join(repository, ".git"), { recursive: true }), mkdir(nested, { recursive: true })])
    expect(await findWorkspaceRoot(nested)).toBe(repository)
  })

  test("creates MP4 and GIF evidence", async () => {
    const repository = join(root, "publish-repository")
    const before = snapshotGitHubTuiEvidence(await discoverGitHubTuiEvidence(repository))
    const bundle = await createEvidenceBundle({
      recordingPath: recording,
      outputDirectory: join(repository, "artifacts/tui/video"),
      linkBase: "artifacts/video",
      result: "passed",
      tailMs: 100,
      includeRecording: true,
    })
    expect(bundle.video).toBeDefined()
    expect(bundle.preview).toBeDefined()
    expect(bundle.recording).toBeDefined()
    expect((await stat(bundle.video!)).size).toBeGreaterThan(0)
    expect((await stat(bundle.preview!)).size).toBeGreaterThan(0)
    expect((await stat(bundle.recording!)).size).toBeGreaterThan(0)
    const output = renderAgentBundleOutput(bundle, await readFile(bundle.prMarkdown, "utf8"))
    expect(output).toContain(`![TUI verification preview](<${pathToFileURL(bundle.preview!).href}>)`)
    expect(output).toContain(`Full MP4: ${bundle.video}`)
    expect(output).toContain(`Raw .termctrl: ${bundle.recording}`)
    expect(await readFile(bundle.prMarkdown, "utf8")).toContain("artifacts/video/recording.termctrl")

    const discovered = await discoverGitHubTuiEvidence(repository)
    const changed = changedGitHubTuiEvidence(discovered, before)
    assertCompleteGitHubTuiEvidence(changed)
    expect(changed).toHaveLength(1)
    expect(changed[0]?.manifest).toBe("artifacts/tui/video/manifest.json")

    const published = renderGitHubTuiEvidence({
      evidence: changed,
      repository: "nikomatt69/nikcli",
      revision: "abc123",
    })
    expect(published).toContain(
      "https://raw.githubusercontent.com/nikomatt69/nikcli/abc123/artifacts/tui/video/preview.gif",
    )
    expect(published).toContain("https://github.com/nikomatt69/nikcli/blob/abc123/artifacts/tui/video/demo.mp4?raw=1")
    expect(published).toContain("recording.termctrl")

    const firstBody = mergeGitHubTuiEvidence("Existing PR description", published)
    const secondBody = mergeGitHubTuiEvidence(firstBody, published.replaceAll("abc123", "def456"))
    expect(secondBody.match(new RegExp(GITHUB_TUI_EVIDENCE_START, "g"))).toHaveLength(1)
    expect(secondBody).toContain("Existing PR description")
    expect(secondBody).toContain("def456")
    expect(secondBody).not.toContain("abc123")
  }, 30_000)
})
