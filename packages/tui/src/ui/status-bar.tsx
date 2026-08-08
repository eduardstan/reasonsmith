/**
 * Enterprise status bar — verdict counters with mouse filter + ladder summary.
 */

import { For, Show } from "solid-js"
import { CATEGORY_LABELS } from "../types/audiences.ts"
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
  const violated = () => report.report.counts.violated ?? 0
  const activeFilter = () => report.categoryFilter()

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
      paddingLeft={1}
      paddingRight={1}
      gap={1}
      borderStyle="single"
      borderColor={t.color.borderSubtle}
      backgroundColor={t.color.surface}
    >
      <text fg={t.color.info} attributes={t.attr.bold} wrapMode="none" content="ENTERPRISE" />
      <text fg={t.color.borderSubtle} wrapMode="none" content="│" />
      <text fg={t.color.textSecondary} wrapMode="none">
        {total()} req
      </text>
      <Show when={violated() > 0}>
        <Clickable cursor="pointer" onClick={() => filterBy("violated")} active={activeFilter() === "violated"}>
          <text fg={t.color.bad} attributes={t.attr.bold} wrapMode="none">
            {violated()} violated
          </text>
        </Clickable>
      </Show>
      <text fg={t.color.borderSubtle} wrapMode="none" content="│" />
      <For each={counters()}>
        {(counter, index) => (
          <>
            <Clickable
              cursor="pointer"
              active={activeFilter() === counter.key}
              onClick={() => filterBy(counter.key)}
            >
              <text fg={t.color[counter.colorKey]} wrapMode="none">
                <b>{String(report.report.counts[counter.key] ?? 0)}</b>
                {" "}
                {counter.label}
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
            <text fg={t.color.warn} wrapMode="none" content={`filter: ${key()} ✕`} />
          </Clickable>
        )}
      </Show>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none">
        ladder: unattainable → observed → recounted → probed → proved
      </text>
    </box>
  )
}

function matchesCategory(
  result: { verdict: string; strength: string | null; basis: string },
  key: string,
): boolean {
  if (key === "violated") return result.verdict === "violated"
  if (key === "not_applicable") return result.verdict === "not_applicable"
  if (key === "unattainable") return result.strength === "unattainable"
  if (key === "not_evaluated")
    return (
      result.strength === null &&
      result.verdict !== "not_applicable" &&
      result.basis !== "assessment"
    )
  if (key === "on_an_assessment")
    return (
      result.strength === null &&
      result.verdict !== "not_applicable" &&
      result.basis === "assessment"
    )
  if (key === "inconclusive")
    return (
      result.verdict === "inconclusive" &&
      result.strength !== null &&
      result.strength !== "unattainable"
    )
  if (key === "proved" || key === "probed" || key === "recounted" || key === "observed")
    return result.verdict === "satisfied" && result.strength === key
  return false
}
