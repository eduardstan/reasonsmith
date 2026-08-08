/**
 * The limits route: what this report does not claim.
 *
 * Two blocks. The first is `report.limits` **verbatim and whole** — `docs/semantics.md` §7 makes it a
 * rule that no audience projection may drop a word of it, so this screen is reachable from every
 * route and prints the same text to every reader. The second quotes the four headings of
 * `docs/what-this-does-not-do.md`, which is that document's whole structure: four things this tool
 * cannot do, stated together.
 *
 * What a reader must not break:
 *
 *   - **The four headings are quoted, not summarised.** They are the document's own words. A
 *     paraphrase here would be this TUI making a claim about the tool's limits in its own voice,
 *     which is exactly the move every rule in this repository is written to prevent. The one-line
 *     glosses under them are quoted from the same document's body.
 *   - **This route is never gated by audience.** Every projection keeps the limits; there is no flag
 *     to consult, and adding one would be the drop the rule forbids.
 *   - **Both blocks render through OpenTUI's `<markdown>`.** The verdict language is markdown so a
 *     paragraph survives into other renderings without re-parsing it here, and a renderer that knows
 *     the language will bold the headings and dim the quoted attribution. The text itself is
 *     unchanged.
 */

import { SyntaxStyle } from "@opentui/core"
import { useReport } from "../context/report.tsx"
import { useTheme } from "../context/theme.tsx"

/**
 * One `SyntaxStyle` for every `<markdown>` on this screen. The renderer needs a syntax style to
 * colour headings and emphasis; an empty one bolds headings and dims everything else by convention,
 * which is exactly what this screen wants. A single instance for the lifetime of the process — the
 * renderable does not own the style, and the OS reclaims it on exit.
 */
const SYNTAX_STYLE = SyntaxStyle.create()

/**
 * The four headings of `docs/what-this-does-not-do.md`, with one quoted line each. Kept verbatim so
 * a reader who opens the document recognises what they were shown. The whole block is one markdown
 * document so the rendered headings stay paired with their glosses.
 */
const CANNOT_MARKDOWN = [
  "## 1. It takes the system's word about what it is",
  "",
  "Read a satisfied row as “the record has the fields”, never as “the system computes what it says it computes”.",
  "",
  "## 2. Depth is uneven, and here is the shape of it",
  "",
  "Three quarters of the shipped duties are presence checks, and presence is not adequacy: a reason field that is filled in is not a reason that is sufficient.",
  "",
  "## 3. A rung is not a grade",
  "",
  "The lattice ranks how a conclusion was reached and not what it was reached about, so a report full of proved verdicts is not a better report than one full of observed verdicts.",
  "",
  "## 4. The strongest results need a system that exposes its inference, and most do not",
  "",
  "A system that is only a decision log reaches observed and no further, whatever the pack asks — and most audited systems are only a decision log.",
].join("\n")

const STANDING_MARKDOWN =
  "And the standing one, on every report this tool prints: nothing here determines whether a legal " +
  "duty is discharged. It reports what a formal specification asks and how the verdict was reached."

export function Limits() {
  const t = useTheme()
  const report = useReport()

  return (
    <scrollbox
      flexGrow={1}
      minHeight={0}
      width="100%"
      paddingLeft={1}
      paddingRight={1}
      backgroundColor={t.color.bg}
      verticalScrollbarOptions={{
        showArrows: true,
        trackOptions: {
          foregroundColor: t.color.info,
          backgroundColor: t.color.surface,
        },
      }}
    >
      <box
        flexDirection="column"
        width="100%"
        borderStyle="rounded"
        borderColor={t.color.border}
        backgroundColor={t.color.surface}
        paddingLeft={1}
        paddingRight={1}
        title="Limits of this report"
        titleAlignment="left"
      >
        <text
          fg={t.color.text}
          attributes={t.attr.bold}
          wrapMode="none"
          content="LIMITS OF THIS REPORT"
        />
        <markdown
          content={report.report.limits}
          syntaxStyle={SYNTAX_STYLE}
          fg={t.color.textSecondary}
          bg={t.color.bg}
        />

        <text
          fg={t.color.text}
          attributes={t.attr.bold}
          wrapMode="none"
          content="WHAT THIS TOOL DOES NOT DO"
        />
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          content="quoted from docs/what-this-does-not-do.md"
        />
        <markdown
          content={CANNOT_MARKDOWN}
          syntaxStyle={SYNTAX_STYLE}
          fg={t.color.textSecondary}
          bg={t.color.bg}
        />

        <markdown
          content={STANDING_MARKDOWN}
          syntaxStyle={SYNTAX_STYLE}
          fg={t.color.textMuted}
          bg={t.color.bg}
        />
      </box>
    </scrollbox>
  )
}