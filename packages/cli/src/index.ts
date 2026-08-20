/**
 * The `reasonsmith` TypeScript CLI — a thin launcher for the OpenTUI renderer.
 *
 * The TypeScript CLI's job is **only to start the TUI**. The conformance run, every verdict, every
 * strength and basis, every evidence summary is the Python `reasonsmith` package's work
 * (`src/reasonsmith/`); this launcher hands arguments through to the TUI binary, which spawns the
 * Python subprocess and parses its JSON.
 *
 * Why the TUI gets its own binary: `bun build --compile` produces a single executable that embeds
 * the Bun runtime and the OpenTUI native libraries (`bun:ffi`, `.so`/`.dylib`/`.dll`), and `--target`
 * cross-compiles. So an auditor downloads one file per platform — no Bun, no Node, no
 * `--experimental-ffi` — and the launcher's whole job is to start it.
 *
 * What a reader must not break:
 *
 *   - **No command other than `tui` ships from the TypeScript CLI.** The Python CLI carries the
 *     authoritative command surface (`init`, `check`, `validate-pack`, `verify-engine`,
 *     `published-counts`, `explain`). Duplicating any of those here would be a second copy of a
 *     thing the Python owns; the TUI consumes the Python's JSON and that is the whole contract.
 *   - **The launcher is one function, `main()`.** yargs is the wrong shape for a single-command
 *     surface, and the argument grammar is the TUI's, not this file's. `--help` is the only flag
 *     the launcher parses; everything else is forwarded verbatim.
 *   - **The exit code is the TUI's.** A `2` means a violated requirement; `0` means the run
 *     finished without a violation; `1` means the TUI could not start. None of this code reports
 *     a finding as an error — only a violation is one.
 */

import { spawn } from "bun"
import { fileURLToPath } from "node:url"
import { dirname, resolve } from "node:path"

const HERE = dirname(fileURLToPath(import.meta.url))

/**
 * The compiled TUI binary lives next to this file when the CLI is shipped. `bin/reasonsmith-tui`
 * is the entry the monorepo's `bun build --compile` produces; in a source checkout the launcher
 * falls back to `bun run` against the TUI package's source.
 */
function findTuiCommand(): { cmd: readonly string[] } {
  const compiled = resolve(HERE, "..", "bin", "reasonsmith-tui")
  if (Bun.file(compiled).size > 0) {
    return { cmd: [compiled] }
  }
  return { cmd: ["bun", "run", resolve(HERE, "..", "..", "tui", "src", "index.tsx")] }
}

const HELP = [
  "reasonsmith-tui-launcher — starts the OpenTUI renderer.",
  "",
  "usage: reasonsmith [tui] --system <decisions.jsonl|module:attr> --pack <pack> [options]",
  "",
  "This launcher has no commands other than the default. The Python reasonsmith CLI (`pip install",
  "reasonsmith`) carries the full command surface (`init`, `check`, `validate-pack`,",
  "`verify-engine`, `published-counts`, `explain`); the TypeScript side is a thin launcher for",
  "the TUI over the JSON output those emit.",
  "",
  "All arguments are forwarded to the TUI binary. Run `reasonsmith-tui --help` for the full",
  "argument grammar.",
].join("\n")

export async function main(argv: readonly string[] = process.argv.slice(2)): Promise<number> {
  const args = [...argv]
  // `reasonsmith tui --pack ecoa ...` and `reasonsmith --pack ecoa ...` are both accepted. The
  // first argument is the literal "tui" — drop it; anything else is forwarded unchanged.
  if (args[0] === "tui") args.shift()
  if (args.includes("-h") || args.includes("--help")) {
    process.stdout.write(`${HELP}\n`)
    return 0
  }

  const { cmd } = findTuiCommand()
  const proc = spawn({
    cmd: [...cmd, ...args],
    stdout: "inherit",
    stderr: "inherit",
    stdin: "inherit",
    env: process.env,
  })

  return (await proc.exited)
}

if (import.meta.main) {
  process.exitCode = await main()
}
