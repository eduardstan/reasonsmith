/**
 * The TUI README is a launch guide a newcomer copy-pastes from; these tests hold it to the
 * workspace it describes, so the guide cannot silently rot (issue #256).
 *
 * What is held:
 *
 *   - **The Bun version the README states is the one the workspace pins** in the root
 *     `package.json`'s `packageManager` field — read at test time, never restated here.
 *   - **Every `--flag` inside the README's shell blocks is a flag the TUI's own parser
 *     accepts** (the USAGE text in `./args.ts`). A flag renamed in the parser fails here
 *     before it reaches a reader.
 *   - **The documented launch example names a system that ships**: the `module:attribute`
 *     reference in the README's run command must resolve to an attribute defined in the
 *     corresponding module under `src/reasonsmith/`.
 */

import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { USAGE } from "./args.ts"

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const README = readFileSync(resolve(REPO_ROOT, "packages", "tui", "README.md"), "utf8")
const ROOT_PACKAGE = JSON.parse(readFileSync(resolve(REPO_ROOT, "package.json"), "utf8"))

/** The fenced ```sh blocks — the copy-pasteable commands the guide stands behind. */
function documentedShellBlocks(): string[] {
  return [...README.matchAll(/```sh\n([\s\S]*?)```/g)].map((m) => m[1])
}

describe("the TUI README", () => {
  test("states the Bun version the workspace pins", () => {
    const pinned = (ROOT_PACKAGE.packageManager as string).replace(/^bun@/, "")
    expect(README).toContain(`Bun ${pinned}`)
  })

  test("documents launch through a script the root package.json has", () => {
    expect(README).toContain("bun run dev:tui --")
    expect(ROOT_PACKAGE.scripts["dev:tui"]).toBeString()
  })

  test("every flag in the shell blocks is one the TUI parser accepts", () => {
    const flags = new Set(
      documentedShellBlocks().flatMap((block) => [...block.matchAll(/--[a-z-]+/g)].map((m) => m[0])),
    )
    expect(flags.size).toBeGreaterThan(0)
    for (const flag of flags) {
      expect(USAGE).toContain(flag)
    }
  })

  test("the documented launch example names a system that ships", () => {
    const reference = README.match(/reasonsmith(\.[\w]+)+:[\w]+/)?.[0]
    expect(reference).toBeString()
    const [modulePath, attribute] = reference!.split(":")
    const source = readFileSync(
      resolve(REPO_ROOT, "src", ...modulePath.split(".")) + ".py",
      "utf8",
    )
    expect(source).toContain(`def ${attribute}`)
  })
})
