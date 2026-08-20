/**
 * The footer hint bar, in nikcli's shape: a key in bold, its label dimmed, `·` between.
 *
 * The hints are read out of `BINDINGS` in the keybind context rather than written here, so a key
 * that works and a key that is advertised cannot drift apart — which is the same reason nikcli's
 * `FooterHintAction` looks its keybind up instead of taking a string.
 *
 * The current audience is shown here too, because it changes what every other panel withholds, and a
 * reader who cannot see which projection they are in cannot tell a field that is absent from a field
 * that was suppressed.
 *
 * **No border, for the reason the status bar has none.** This row is one cell tall, and a bordered
 * box one cell tall spends that cell on its own frame: every hint was drawn into the border line
 * and clipped to nothing — `enteope`, `aaudien`, `qqui`, a `keys` title over a row with no room to
 * say a key. The surface colour separates it from the panel above.
 */

import { For, Show } from "solid-js"

/** Width of the `  +N (?)` overflow chip, reserved before the hints are fitted. */
const OVERFLOW_CHIP_WIDTH = 9

import { useKeybind } from "../context/keybind.tsx"
import { useLayout } from "../context/layout.tsx"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"

export function FooterHints() {
  const t = useTheme()
  const keybind = useKeybind()
  const route = useRoute()
  const report = useReport()
  const layout = useLayout()

  const forRoute = () => keybind.bindings.filter((b) => b.on.includes(route.route().type))

  /** `  for: <audience>`, the one thing on this row that is never dropped. */
  const tailWidth = () => `  for: ${report.audience()}`.length

  /** Cells one hint costs, plus the `  ·  ` that precedes it when it is not the first. */
  const hintWidth = (binding: Readonly<{ keys: string; label: string }>, first: boolean) =>
    binding.keys.length + 1 + binding.label.length + (first ? 0 : 5)

  /**
   * As many hints as actually fit, measured rather than guessed.
   *
   * This was a count per breakpoint — three at `xs`, five at `sm`, and everything at `lg`. A count
   * cannot know how wide the hints are: at 112 columns the nine bindings of the findings route came
   * to more than the row, and the thing pushed off the end was the audience, which is the one field
   * here that changes what every other panel withholds. So the budget is columns, the audience is
   * subtracted first, and the hints take what is left.
   *
   * Room for the overflow chip is reserved up front when not everything can fit, so adding the chip
   * cannot itself push a hint off the row it was counting.
   */
  const shown = () => {
    const all = forRoute()
    const full = all.reduce((sum, b, i) => sum + hintWidth(b, i === 0), 0)
    let budget = layout.cols() - layout.pad() * 2 - tailWidth()
    if (full > budget) budget -= OVERFLOW_CHIP_WIDTH
    const fitted: typeof all = []
    let used = 0
    for (const binding of all) {
      const width = hintWidth(binding, fitted.length === 0)
      if (used + width > budget) break
      fitted.push(binding)
      used += width
    }
    return fitted
  }

  const hidden = () => forRoute().length - shown().length

  return (
    <box
      flexDirection="row"
      width="100%"
      height={1}
      paddingLeft={layout.pad()}
      paddingRight={layout.pad()}
      gap={0}
      backgroundColor={t.color.surface}
    >
      {/*
        Each hint carries no padding of its own: the row's `gap` already separates them, and padding
        on top of it spent three cells per hint on nothing — which is a whole hint every four.
      */}
      {/*
        The whole hint row is **one** `text`, with every space written into its children.

        Three arrangements were tried against a real terminal before this one, and each failed the
        same way: spacing that is not a character does not survive. Two sibling `text` elements with
        a `gap` between them rendered `ctrl+pcommands`; a separator element beside them rendered the
        dot hard against the label, because `gap` does not apply between the children of a fragment
        inside a `For`; and a `content` prop of `" · "` lost both its spaces, because `content` is
        trimmed at each end. Interior text in JSX children is not trimmed, so that is where the
        spacing has to live — and it can only live there if the row is a single element.

        The cost is per-hint mouse clicks, which is the right thing to spend: every hint on this row
        names the key that does the same job, and a hint bar that cannot be read is worth less than
        one that cannot be clicked.
      */}
      <text fg={t.color.textMuted} wrapMode="none">
        <For each={shown()}>
          {(binding, index) => (
            <>
              <b>{binding.keys}</b>
              {` ${binding.label}${index() < shown().length - 1 ? "  ·  " : ""}`}
            </>
          )}
        </For>
      </text>
      <Show when={hidden() > 0}>
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          content={`  +${hidden()} (?)`}
        />
      </Show>
      <box flexGrow={1} />
      <Show when={keybind.leader()}>
        <text fg={t.color.warn} attributes={t.attr.bold} wrapMode="none" content="LEADER " />
      </Show>
      {/*
        The audience stays at every width. It decides what every other panel withholds, and a reader
        who cannot see which projection they are in cannot tell a field that is absent from a field
        that was suppressed — which is the distinction this whole tool is built to keep.
      */}
      <text fg={t.color.info} wrapMode="none">
        {"  "}for: <b>{report.audience()}</b>
      </text>
    </box>
  )
}
