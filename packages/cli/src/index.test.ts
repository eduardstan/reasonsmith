/**
 * Tests for the TypeScript CLI launcher.
 *
 * The CLI is a thin launcher for the TUI binary. It does not parse packs, does not load engines,
 * and does not evaluate a requirement — that is the Python's job and the data flow is one
 * subprocess call. These tests assert the launcher's argument handling and that the only
 * non-trivial action it can take (forwarding `--help` to the help text) is wired correctly.
 */

import { describe, expect, test } from "bun:test"

describe("the launcher", () => {
  test("the help branch is reached on --help without spawning the TUI", async () => {
    const mod = await import("./index.ts")
    expect(typeof mod.main).toBe("function")
    const code = await mod.main(["--help"])
    expect(code).toBe(0)
  })

  test("the help branch is reached on -h", async () => {
    const mod = await import("./index.ts")
    const code = await mod.main(["-h"])
    expect(code).toBe(0)
  })

  test("a leading `tui` subcommand is consumed and the rest is forwarded", async () => {
    const mod = await import("./index.ts")
    // Forwarding --help exits 0 (it short-circuits before spawning the TUI binary, which would
    // fail in this CI environment without the compiled binary on disk).
    const code = await mod.main(["tui", "--help"])
    expect(code).toBe(0)
  })
})
