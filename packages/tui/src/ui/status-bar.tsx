/**
 * The status bar — the record's category counts, each one a filter, and the ladder.
 *
 * Every number here is `ConformanceReport.counts` read straight off the JSON. The bar counts
 * nothing itself, and the membership test behind each filter is `types/categories.ts`, shared with
 * the list the filter narrows: these counters are the *only* way into that list, so a bar with its
 * own copy of the test is a bar that can disagree with what clicking it shows. It had one, and the
 * two copies had already drifted.
 *
 * The counts are the unprefixed ones, which cover the binding requirements alone — so the filter
 * chip on the right says so rather than leaving the reader to work out why the list got shorter.
 *
 * **This bar carries no border.** It is one row tall, and a bordered box one row tall has no room
 * left for its own contents: the frame takes the row and every counter is drawn into the border
 * line and clipped mid-word — `3 observe·`, `2 unattainabl`. A border here would cost two further
 * rows to be legible, which on a status bar is two rows of findings spent on a rectangle. The
 * surface colour is the separation, and the header's own frame sits directly above it.
 */

import { For, Show } from "solid-js"
import { CATEGORY_LABELS } from "../types/audiences.ts"
import { matchesCategory } from "../types/categories.ts"
import { useLayout } from "../context/layout.tsx"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"
import { Clickable } from "./clickable.tsx"

interface CounterSpec {
  readonly key: string
  readonly label: string
  readonly colorKey: "textMuted" | "bad" | "ok" | "unattainable"
}

export function StatusBar() {
  const t = useTheme()
  const report = useReport()
  const route = useRoute()
  const layout = useLayout()

  const counters = (): CounterSpec[] => {
    const c = report.report.counts
    const specs: CounterSpec[] = []
    for (const [key, label] of CATEGORY_LABELS) {
      const count = c[key] ?? 0
      if (count === 0) continue
      let colorKey: CounterSpec["colorKey"] = "textMuted"
      if (key === "violated") colorKey = "bad"
      else if (key === "proved" || key === "probed" || key === "recounted" || key === "observed")
        colorKey = "ok"
      else if (key === "unattainable") colorKey = "unattainable"
      specs.push({ key, label, colorKey })
    }
    return specs
  }

  const total = () => report.report.counts.total ?? report.results().length
  const activeFilter = () => report.categoryFilter()

  const LADDER = "ladder: unattainable → observed → recounted → probed → proved"

  /**
   * Roughly how many columns the counts occupy, so the ladder caption is shown only where there is
   * room left for it rather than wherever the terminal happens to be wider than a fixed threshold.
   *
   * A fixed threshold was wrong in the way this kind of threshold always is: the bar's own content
   * grows with the pack, so at 112 columns a six-requirement run cleared it and the caption was
   * drawn straight into the last counter — `2 unattainableladder: …` — and then clipped mid-arrow.
   * The estimate is deliberately generous; being one column pessimistic hides a caption, being one
   * column optimistic corrupts the row.
   */
  const countsWidth = () => {
    const digits = (n: number) => String(n).length
    const counted = counters().reduce((sum, spec) => {
      const value = report.report.counts[spec.key] ?? 0
      const label = layout.showCounterLabels() ? spec.label.length + 1 : 0
      return sum + digits(value) + label + 3
    }, 0)
    const chip = activeFilter() ? activeFilter()!.length + 12 : 0
    return `${total()} req`.length + 2 + counted + chip
  }

  const filterBy = (key: string) => {
    report.setCategoryFilter(activeFilter() === key ? null : key)
    route.navigate({ type: "findings" })
    const index = report.results().findIndex((r) => matchesCategory(r, key))
    if (index >= 0) report.select(index)
  }

  return (
    <box
      flexDirection="row"
      width="100%"
      height={1}
      flexShrink={0}
      paddingLeft={layout.pad()}
      paddingRight={layout.pad()}
      gap={1}
      backgroundColor={t.color.surface}
    >
      {/*
        This row used to open with the word ENTERPRISE, in the accent colour and bold — ten columns
        of brand adjective, held at the highest emphasis on the screen, in front of the counts it
        pushed rightward. It said nothing about the run and outranked everything that did.
      */}
      <text fg={t.color.textSecondary} wrapMode="none">
        {total()} req
      </text>
      {/*
        The violated count had a chip of its own here, ahead of the separator, *and* an entry in the
        loop below — so a run with one breach printed `1 violated` twice, three cells apart, and a
        reader counting them read two. It is one counter among the others now, and it keeps the
        violation colour there.
      */}
      <text fg={t.color.borderSubtle} wrapMode="none" content="│" />
      <For each={counters()}>
        {(counter, index) => (
          <>
            <Clickable
              cursor="pointer"
              active={activeFilter() === counter.key}
              onClick={() => filterBy(counter.key)}
            >
              {/*
                The number is never dropped and never abbreviated; the word beside it is, on a
                terminal too narrow to carry both. A count with no word is still a count a reader can
                click, and the filter chip on the right names the category they landed in.
              */}
              <text fg={t.color[counter.colorKey]} wrapMode="none">
                <b>{String(report.report.counts[counter.key] ?? 0)}</b>
                <Show when={layout.showCounterLabels()}>
                  {" "}
                  {counter.label}
                </Show>
              </text>
            </Clickable>
            <Show when={index() < counters().length - 1}>
              <text fg={t.color.borderSubtle} wrapMode="none" content="·" />
            </Show>
          </>
        )}
      </For>
      <box flexGrow={1} />
      <Show when={activeFilter()}>
        {(key) => (
          <Clickable cursor="pointer" onClick={() => report.clearCategoryFilter()}>
            <text fg={t.color.warn} wrapMode="none" content={`filter: ${key()} · binding ✕`} />
          </Clickable>
        )}
      </Show>
      {/* A caption, and the last thing on this row that is not a number. It goes first. */}
      <Show when={layout.cols() - countsWidth() >= LADDER.length + 2}>
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          content={LADDER}
        />
      </Show>
    </box>
  )
}
