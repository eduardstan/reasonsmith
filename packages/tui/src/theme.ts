/**
 * The colour tokens, and the one function that maps a result to a colour.
 *
 * The tokens live apart from the components because in this UI a colour is a *claim*, not a
 * decoration: green says satisfied and red says violated, and a reader who learns that reads every
 * screen through it. `resultTone` is the only place that mapping is made.
 *
 * Three things a reader must not break, each of them a rule this repository states elsewhere and
 * this module is bound by:
 *
 *   - **Satisfied is always green and violated is always red, at every rung.** The colour carries
 *     the verdict and nothing else.
 *   - **The rung is never a colour ramp.** `docs/what-this-does-not-do.md` §3 is titled *A rung is
 *     not a grade*: the lattice ranks how a conclusion was reached, never how much to believe it, and
 *     "a report full of `proved` verdicts is not a better report than one full of `observed`
 *     verdicts". A palette that shaded `observed` amber and `proved` blue would teach the opposite in
 *     a glance and no caption could undo it, so the rung is rendered as a *word* and never as a hue.
 *   - **The third family is neither.** `not evaluated`, `unattainable` and `not applicable` are not
 *     weak passes and not soft failures; they are the absence of a verdict. They get a muted family
 *     of their own so a reader can never mistake one for a clean result — which is the whole reason
 *     the result model keeps `strength = null` distinct from a low rung.
 *
 * `satisfied` and `violated` are also kept apart on the *hue* channel and not only on lightness, so a
 * terminal palette that desaturates both toward a common grey still shows them as different colours.
 */

import { RGBA, TextAttributes } from "@opentui/core"

export type Color = RGBA

const hex = {
  bg: "#080b10",
  surface: "#111821",
  surfaceRaised: "#16202c",
  border: "#263344",
  borderSubtle: "#1a2532",
  borderFocus: "#6bb8ff",
  text: "#edf4fb",
  textSecondary: "#b9c7d6",
  textMuted: "#6f7f90",
  /** A verdict of `satisfied`. Kept green at every rung. */
  ok: "#52d273",
  /** A verdict of `violated`. Kept apart from `ok` on the hue channel, not merely on lightness. */
  bad: "#ff6b6b",
  /** The third family: no verdict was reached. Never green, never red. */
  none: "#8291a3",
  /** Unattainable — still the third family, distinguished from plain not-evaluated. */
  unattainable: "#c8a7ff",
  info: "#6bb8ff",
  warn: "#e6b450",
} as const

export const c = {
  bg: RGBA.fromHex(hex.bg),
  surface: RGBA.fromHex(hex.surface),
  surfaceRaised: RGBA.fromHex(hex.surfaceRaised),
  border: RGBA.fromHex(hex.border),
  borderSubtle: RGBA.fromHex(hex.borderSubtle),
  borderFocus: RGBA.fromHex(hex.borderFocus),
  text: RGBA.fromHex(hex.text),
  textSecondary: RGBA.fromHex(hex.textSecondary),
  textMuted: RGBA.fromHex(hex.textMuted),
  ok: RGBA.fromHex(hex.ok),
  bad: RGBA.fromHex(hex.bad),
  none: RGBA.fromHex(hex.none),
  unattainable: RGBA.fromHex(hex.unattainable),
  info: RGBA.fromHex(hex.info),
  warn: RGBA.fromHex(hex.warn),
} as const

export const A = {
  none: TextAttributes.NONE,
  bold: TextAttributes.BOLD,
  dim: TextAttributes.DIM,
  italic: TextAttributes.ITALIC,
  underline: TextAttributes.UNDERLINE,
} as const

/** The three families a result can fall in. A rung is not one of them. */
export type Tone = "satisfied" | "violated" | "no-verdict"

export interface ResultTone {
  readonly tone: Tone
  readonly color: Color
  /** The four-cell mark, matching `render.ts`'s text rendering so the two surfaces agree. */
  readonly mark: string
  /** What the verdict is, in a word. Never the rung — the rung is rendered separately. */
  readonly label: string
}

/**
 * The colour and mark for one result. The marks are `render.ts`'s own, so a reader moving between
 * `reasonsmith check` and this TUI sees the same four glyphs mean the same four things.
 */
export function resultTone(verdict: string, strength: string | null): ResultTone {
  if (verdict === "satisfied") {
    return { tone: "satisfied", color: c.ok, mark: "PASS", label: "satisfied" }
  }
  if (verdict === "violated") {
    return { tone: "violated", color: c.bad, mark: "FAIL", label: "violated" }
  }
  if (verdict === "not_applicable") {
    return { tone: "no-verdict", color: c.none, mark: "n/a ", label: "not applicable" }
  }
  // Everything left is `inconclusive`, which splits into two things a reader must not conflate:
  // a duty the system cannot discharge at all, and a duty this run established nothing about.
  if (strength === "unattainable") {
    return { tone: "no-verdict", color: c.unattainable, mark: "----", label: "unattainable" }
  }
  if (strength === null) {
    return { tone: "no-verdict", color: c.none, mark: "----", label: "not evaluated" }
  }
  return { tone: "no-verdict", color: c.none, mark: "----", label: "inconclusive" }
}

/**
 * How a rung is worded. `null` is *not evaluated* and never an empty string or a dash on its own:
 * a blank where a rung would go reads as a rung the renderer forgot, and the result model keeps the
 * two apart precisely so a rendering can.
 */
export function strengthWord(strength: string | null): string {
  return strength ?? "not evaluated"
}

/**
 * Greedy wrap, shared by every panel that prints a sentence.
 *
 * A word longer than the measure is hard-split rather than left to overflow. In a terminal an
 * over-long line is not clipped, it wraps into the row beneath and shears everything below it down
 * a line, so one unbroken token — a requirement id, a signal name, a URL in a limits paragraph —
 * silently corrupts the layout of the whole panel. Splitting is the lesser damage and the visible
 * one.
 */
export function wrap(text: string, width: number): string[] {
  const measure = Math.max(1, Math.floor(width))
  const lines: string[] = []
  let line = ""
  for (const word of text.split(/\s+/).filter(Boolean)) {
    let token = word
    // A token that cannot fit on a line of its own is broken across as many as it needs.
    while (token.length > measure) {
      if (line) {
        lines.push(line)
        line = ""
      }
      lines.push(token.slice(0, measure))
      token = token.slice(measure)
    }
    if (line && line.length + 1 + token.length > measure) {
      lines.push(line)
      line = token
    } else {
      line = line ? `${line} ${token}` : token
    }
  }
  if (line) lines.push(line)
  return lines
}
