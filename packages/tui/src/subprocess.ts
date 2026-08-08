/**
 * The TUI's only data path: one subprocess call to `reasonsmith check ... --json`.
 *
 * `src/reasonsmith/cli.py` calls that output *"the complete machine record, deliberately
 * unprojected"* — it was built so that another program could render it. The TUI is that other
 * program. No other module in this package reads a system, runs an engine, or evaluates a
 * property; every verdict the renderer shows was reached by the Python and arrived over stdout.
 *
 * What a reader must not break:
 *
 *   - **The TUI never imports `reasonsmith`.** The Python is reached only as a subprocess. The
 *     reason is the same as for accepting `npm` over the wire: a process boundary is also a
 *     contract boundary, and a library call would be a chance to silently agree with the renderer
 *     about what a verdict is.
 *   - **The command path is fixed here.** `--json` is on; `--audience` is passed through when the
 *     caller gave one. Anything else (an adapter, a pack override, an output file) is a different
 *     run and is the caller's responsibility.
 *   - **The subprocess's stderr is forwarded only on failure.** A clean run produces no stderr;
 *     the Python prints its own undeclared-domain notice into the report, not the stream.
 *   - **Exit code 2 means a violated requirement.** Exit code 1 means the Python could not produce
 *     a record (a usage error, a missing file, a malformed JSON). The TUI treats the latter as a
 *     fatal startup failure and shows the Python's stderr verbatim.
 */

import { spawn } from "bun"
import { parseReport, type ConformanceReport } from "./types/schema.ts"

export interface RunArgs {
  /** Path to a `decisions.jsonl`, or `module:attribute` to a Python system. */
  readonly system: string
  /** Pack id (`ecoa`, `eu-ai-act`, `gdpr`, `table7`). */
  readonly pack: string
  /** Optional audience (`developer` / `deployer` / `auditor` / `regulator` / `affected-individual`). */
  readonly audience?: string
  /** Optional override of the Python interpreter. Defaults to `python3`. */
  readonly python?: string
  /** Optional additional arguments to forward to the Python, *before* `--json`. */
  readonly pythonArgs?: readonly string[]
  /** Optional `system-name` to override what the report's header carries. */
  readonly systemName?: string
  /** Optional `system-scope` to declare a regulatory class. */
  readonly systemScope?: string
  /** Optional `system-domain` flags to declare the kind of decision the system makes. */
  readonly systemDomains?: readonly string[]
  /** Optional `capabilities` file declaring what signals the system emits. */
  readonly capabilities?: string
  /** Working directory for the subprocess. Defaults to `process.cwd()`. */
  readonly cwd?: string
}

export interface RunOutcome {
  readonly report: ConformanceReport
  /** `2` if any result was violated, `0` otherwise, `1` on usage/input error. */
  readonly exitCode: number
}

/**
 * Spawn `python -m reasonsmith.cli check ... --json`, parse stdout, and return the record.
 *
 * Throws on a usage or subprocess error so the caller can print a fatal-startup message. A clean
 * run with `exit_code = 2` (a violated requirement) returns normally — that is the success path
 * for `reasonsmith-tui`, whose own exit code the CLI carries through.
 */
export async function runReasonsmith(args: RunArgs): Promise<RunOutcome> {
  const argv = buildArgv(args)
  const proc = spawn({
    cmd: [args.python ?? "python3", ...argv],
    cwd: args.cwd ?? process.cwd(),
    stdout: "pipe",
    stderr: "pipe",
    env: process.env,
  })

  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ])

  if (exitCode !== 0 && exitCode !== 2) {
    throw new Error(
      `reasonsmith check exited with code ${exitCode}.\n` +
        `${stderr.trim() ? `stderr:\n${stderr.trim()}\n` : ""}` +
        `command: ${(args.python ?? "python3")} ${argv.join(" ")}`,
    )
  }

  let parsed: ConformanceReport
  try {
    parsed = parseReport(JSON.parse(stdout))
  } catch (error) {
    const stderrTail = stderr.trim().split("\n").slice(-10).join("\n")
    throw new Error(
      `reasonsmith check produced a JSON record the TUI cannot read: ` +
        `${error instanceof Error ? error.message : String(error)}.\n` +
        `${stderrTail ? `python stderr (last 10 lines):\n${stderrTail}\n` : ""}`,
    )
  }

  return { report: parsed, exitCode }
}

function buildArgv(args: RunArgs): string[] {
  const argv: string[] = ["-m", "reasonsmith.cli", "check"]
  // A `--system-module` argument takes precedence over a `--system` JSONL path; the TUI passes
  // either one but never both, and the Python refuses the second if it sees the first.
  if (looksLikePythonModule(args.system)) {
    argv.push("--system-module", args.system)
  } else {
    argv.push("--system", args.system)
  }
  argv.push("--pack", args.pack)
  if (args.systemName) argv.push("--system-name", args.systemName)
  if (args.systemScope) argv.push("--system-scope", args.systemScope)
  for (const domain of args.systemDomains ?? []) argv.push("--system-domain", domain)
  if (args.capabilities) argv.push("--capabilities", args.capabilities)
  if (args.audience) argv.push("--audience", args.audience)
  if (args.pythonArgs) argv.push(...args.pythonArgs)
  argv.push("--json")
  return argv
}

/** A `module:attribute` Python system reference — what `--system-module` accepts. */
function looksLikePythonModule(value: string): boolean {
  return /^[A-Za-z_][\w]*(\.[A-Za-z_][\w]*)+:[A-Za-z_][\w]*$/.test(value)
}
