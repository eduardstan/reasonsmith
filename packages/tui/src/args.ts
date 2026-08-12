/**
 * Argument parsing for the TUI.
 *
 * Held in its own module so the test harness can exercise the parser without dragging in the
 * renderer (which loads OpenTUI's JSX runtime and would force every test run through the Solid
 * compiler's `react/jsx-dev-runtime` path). The renderer's entry point imports this module;
 * nothing here imports the renderer.
 *
 * What a reader must not break:
 *
 *   - **Argument grammar is local to this file.** A second `--pack` parser would be a second
 *     place to drift from the Python CLI, and the only command surface we ship is the one in this
 *     file plus `reasonsmith check --help`.
 *   - **`--help` returns `{ error: "help", help: true }`.** The caller writes the help text and
 *     returns exit code 0; the parser does not write to stdout itself.
 */

export interface Args {
  /** Path to a JSONL of decision records, or `module:attribute` to a Python system. */
  system: string
  /** Pack id (`ecoa`, `eu-ai-act`, `gdpr`, `table7`). */
  pack: string
  /** Optional audience (`developer` / `deployer` / `auditor` / `regulator` / `affected-individual`). */
  audience?: string
  /** Optional `system-name` to override what the report's header carries. */
  systemName?: string
  /** Optional `system-scope` to declare a regulatory class. */
  systemScope?: string
  /** Optional `system-domain` flags to declare the kind of decision the system makes. */
  systemDomains: string[]
  /** Optional `capabilities` file declaring what signals the system emits. */
  capabilities?: string
  /** Optional override of the Python interpreter. */
  python?: string
}

export const USAGE = [
  "usage: reasonsmith-tui --system <decisions.jsonl|module:attr> --pack <pack> [options]",
  "",
  "options:",
  "  --system <path|module:attr>   a decisions.jsonl, or a Python system reference",
  "  --pack <name>                 ecoa | eu-ai-act | gdpr | table7",
  "  --audience <reader>           developer | deployer | auditor | regulator | affected-individual",
  "  --system-name <name>          override the report's system_name",
  "  --system-scope <scope>        a regulatory class from REGULATORY_CLASSES",
  "  --system-domain <domain>      declare a decision domain (repeatable)",
  "  --capabilities <file>         declare what signals the system emits",
  "  --python <interpreter>        override `python3`",
  "  -h, --help                    show this help and exit",
  "",
  "The TUI's data path is one subprocess call to `reasonsmith check ... --json`. Every verdict it",
  "shows was reached by the Python side and arrived over stdout; this process imports no engine",
  "and reads no trace.",
].join("\n")

export function parseArgs(argv: readonly string[]): Args | { error: string; help?: boolean } {
  const out: Args = {
    system: "",
    pack: "",
    systemDomains: [],
  }
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i]
    const value = argv[i + 1]
    const next = (): string | { error: string } => {
      if (value === undefined || value.startsWith("--")) {
        return { error: `${token} needs a value` }
      }
      return value
    }
    switch (token) {
      case "-h":
      case "--help":
        return { error: "help", help: true }
      case "--system": {
        const v = next()
        if (typeof v !== "string") return v
        out.system = v
        i++
        continue
      }
      case "--pack": {
        const v = next()
        if (typeof v !== "string") return v
        out.pack = v
        i++
        continue
      }
      case "--audience": {
        const v = next()
        if (typeof v !== "string") return v
        out.audience = v
        i++
        continue
      }
      case "--system-name": {
        const v = next()
        if (typeof v !== "string") return v
        out.systemName = v
        i++
        continue
      }
      case "--system-scope": {
        const v = next()
        if (typeof v !== "string") return v
        out.systemScope = v
        i++
        continue
      }
      case "--system-domain": {
        const v = next()
        if (typeof v !== "string") return v
        out.systemDomains.push(v)
        i++
        continue
      }
      case "--capabilities": {
        const v = next()
        if (typeof v !== "string") return v
        out.capabilities = v
        i++
        continue
      }
      case "--python": {
        const v = next()
        if (typeof v !== "string") return v
        out.python = v
        i++
        continue
      }
      default:
        return { error: `unknown argument ${token}` }
    }
  }
  if (!out.system) return { error: "--system is required" }
  if (!out.pack) return { error: "--pack is required" }
  return out
}
