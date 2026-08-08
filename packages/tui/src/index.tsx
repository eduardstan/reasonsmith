/**
 * The TUI entry point: parse the arguments, run the conformance check once, then browse the result.
 *
 * The contract with `reasonsmith` Python is one subprocess call — `python -m reasonsmith.cli check
 * ... --json` — whose stdout is parsed and shown. No engine runs in this process; no system is
 * imported; no pack is loaded. `src/reasonsmith/` is the only source of truth, and the TUI renders
 * what it emits over the wire.
 *
 * What a reader must not break:
 *
 *   - **The run happens once, before the renderer mounts.** The TUI reads a result; it does not
 *     watch one form. A live run would mean the report a reader is looking at could change under
 *     them.
 *   - **The exit code is the CLI's contract, kept here too: `2` when any result is violated.** Not
 *     when a duty is unattainable, not when one is not evaluated — those are findings to read, not
 *     verdicts against the system.
 *   - **Argument parsing is in `./args.ts`, not here.** A second `--pack` parser would be a second
 *     place to drift from the Python CLI, and the only command surface we ship is the one in this
 *     file plus `reasonsmith check --help`.
 */

import { tui } from "./app.tsx"
import { runReasonsmith } from "./subprocess.ts"
import { parseArgs, USAGE } from "./args.ts"

export { parseArgs, USAGE }
export type { Args } from "./args.ts"

/** CLI contract — `reasonsmith tui` reaches the TUI through this function only. */
export async function runTUI(): Promise<number> {
  return main()
}

export async function main(argv: readonly string[] = process.argv.slice(2)): Promise<number> {
  const parsed = parseArgs(argv)
  if ("error" in parsed) {
    if (parsed.help) {
      process.stderr.write(`${USAGE}\n`)
      return 0
    }
    process.stderr.write(`reasonsmith-tui: ${parsed.error}\n\n${USAGE}\n`)
    return 1
  }

  let outcome
  try {
    outcome = await runReasonsmith({
      system: parsed.system,
      pack: parsed.pack,
      audience: parsed.audience,
      systemName: parsed.systemName,
      systemScope: parsed.systemScope,
      systemDomains: parsed.systemDomains,
      capabilities: parsed.capabilities,
      python: parsed.python,
    })
  } catch (error) {
    process.stderr.write(
      `reasonsmith-tui: ${error instanceof Error ? error.message : String(error)}\n`,
    )
    return 1
  }

  await tui(outcome.report)
  // Only a violation is a verdict against the system. Unattainable, not applicable and not
  // evaluated are findings to read in the report, not verdicts against the system.
  return outcome.exitCode === 2 ? 2 : 0
}

if (import.meta.main) {
  process.exitCode = await main()
}
