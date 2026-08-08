/**
 * The verdict chip: the mark, the verdict, and — separately — the rung.
 *
 * The separation is the point. `mark` and `label` carry the *verdict* and take the verdict's colour;
 * the rung is printed beside them as a muted word and never tinted, because the lattice ranks how a
 * conclusion was reached and not how good it is (`docs/what-this-does-not-do.md` §3, *A rung is not a
 * grade*). A chip that coloured `proved` differently from `observed` would rank them by eye.
 *
 * What a reader must not break: `showStrength` is the audience projection's own flag, passed in
 * rather than decided here. The `affected-individual` projection sets it false, and being told a duty
 * is `probed` hands that reader this tool's evidence model instead of an answer.
 */

import { Show } from "solid-js"
import { useTheme } from "../context/theme.tsx"

export function VerdictChip(props: {
  verdict: string
  strength: string | null
  showStrength: boolean
  bold?: boolean
}) {
  const t = useTheme()
  const tone = () => t.resultTone(props.verdict, props.strength)

  return (
    <box flexDirection="row" gap={1} flexShrink={0}>
      <text fg={tone().color} wrapMode="none" width={MARK_WIDTH}>
        <span>{props.bold ? <b>{tone().mark}</b> : tone().mark}</span>
      </text>
      <Show when={props.showStrength}>
        {/*
          A fixed column, so the requirement ids beside it line up and a long rung name cannot run
          into the id. `not evaluated` is the longest word this column ever holds.
        */}
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          width={STRENGTH_WIDTH}
          content={t.strengthWord(props.strength)}
        />
      </Show>
    </box>
  )
}

/** `PASS` / `FAIL` / `n/a ` / `----`, all four cells wide. */
export const MARK_WIDTH = 4

/** Wide enough for `not evaluated`, the longest rung word. */
export const STRENGTH_WIDTH = 13
