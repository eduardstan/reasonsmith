/**
 * The findings route: every requirement result, one row each.
 *
 * A row carries the verdict mark, the rung, whether the duty is binding, and the requirement id.
 * Everything else is the detail route's job — a list that tried to show an evidence summary stops
 * being scannable, and scanning is what this screen is for.
 *
 * What a reader must not break:
 *
 *   - **The rung is shown only where the projection allows it.** `view.strength` is false for the
 *     `affected-individual` projection, and the chip takes the flag rather than deciding for itself.
 *   - **`binding` vs `interpretive` is shown.** A recital informs how a duty is read but creates no
 *     obligation of its own, and `ConformanceReport.counts` keeps the two halves apart precisely so
 *     neither number can be read as the other. A list that flattened them would undo that.
 *   - **The undeclared-domain notice is not tucked away.** A run that skipped domain-limited duties
 *     exits exactly as a clean run does, so the report has to carry what the exit code cannot; the
 *     header prints it in full whenever it is present.
 */

import { For, Show, createMemo, createSignal } from "solid-js"
import type { RequirementResult } from "../types/schema.ts"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"
import { ReportHeader } from "../ui/header.tsx"
import { VerdictChip } from "../ui/verdict-chip.tsx"
import { Clickable } from "../ui/clickable.tsx"

function matchesCategoryFilter(
  result: RequirementResult,
  key: string,
): boolean {
  if (key === "violated") return result.verdict === "violated"
  if (key === "not_applicable") return result.verdict === "not_applicable"
  if (key === "unattainable") return result.strength === "unattainable"
  if (key === "not_evaluated")
    return (
      result.strength === null && result.verdict !== "not_applicable" && result.basis !== "assessment"
    )
  if (key === "on_an_assessment")
    return (
      result.strength === null && result.verdict !== "not_applicable" && result.basis === "assessment"
    )
  if (key === "inconclusive")
    return (
      result.verdict === "inconclusive" &&
      result.strength !== null &&
      result.strength !== "unattainable"
    )
  if (key === "proved" || key === "probed" || key === "recounted" || key === "observed")
    return result.verdict === "satisfied" && result.strength === key
  return true
}

export function Findings() {
  const t = useTheme()
  const report = useReport()
  const route = useRoute()
  const [filter, setFilter] = createSignal("")

  const filtered = createMemo(() => {
    const query = filter().trim().toLowerCase()
    const category = report.categoryFilter()
    let rows = report.results()
    if (query !== "") {
      rows = rows.filter((r) => r.requirement_id.toLowerCase().includes(query))
    }
    if (category) {
      rows = rows.filter((r) => matchesCategoryFilter(r, category))
    }
    return rows
  })

  return (
    <box
      flexDirection="column"
      flexGrow={1}
      minHeight={0}
      width="100%"
      borderStyle="rounded"
      borderColor={t.color.border}
      backgroundColor={t.color.surface}
      paddingLeft={1}
      paddingRight={1}
      title={`Findings (${report.results().length})`}
      titleAlignment="left"
    >
      <ReportHeader />
      <box
        flexDirection="row"
        flexShrink={0}
        width="100%"
        paddingLeft={1}
        paddingRight={1}
        paddingTop={1}
        gap={1}
      >
        <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content="filter:" />
        <input
          flexGrow={1}
          minWidth={0}
          placeholder="requirement id substring…"
          backgroundColor={t.color.surface}
          focusedBackgroundColor={t.color.surfaceRaised}
          textColor={t.color.text}
          cursorColor={t.color.info}
          value={filter()}
          onInput={(value) => setFilter(value)}
        />
      </box>
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
        scrollbarOptions={{
          showArrows: true,
          trackOptions: {
            foregroundColor: t.color.info,
            backgroundColor: t.color.surface,
          },
        }}
      >
        <Show
          when={filtered().length > 0}
          fallback={
            <text
              fg={t.color.textMuted}
              attributes={t.attr.dim}
              wrapMode="none"
              content={`no requirement matches "${filter()}"`}
            />
          }
        >
          <For each={filtered()}>
            {(result, index) => (
              <Row
                result={result}
                selected={report.results().indexOf(result) === report.selected()}
                onHover={() => report.select(report.results().indexOf(result))}
                onOpen={() => {
                  report.select(report.results().indexOf(result))
                  route.navigate({ type: "detail" })
                }}
              />
            )}
          </For>
        </Show>
      </scrollbox>
    </box>
  )
}

function Row(props: { result: RequirementResult; selected: boolean; onHover: () => void; onOpen: () => void }) {
  const t = useTheme()
  const report = useReport()

  return (
    <Clickable
      cursor="pointer"
      flexDirection="row"
      gap={1}
      height={1}
      width="100%"
      active={props.selected}
      onClick={props.onHover}
      onDoubleClick={props.onOpen}
    >
      <text
        fg={props.selected ? t.color.info : t.color.borderSubtle}
        wrapMode="none"
        content={props.selected ? "▌" : " "}
      />
      <VerdictChip
        verdict={props.result.verdict}
        strength={props.result.strength}
        showStrength={report.view().strength}
        bold={props.selected}
      />
      <text
        fg={props.selected ? t.color.text : t.color.textSecondary}
        wrapMode="none"
        flexGrow={1}
        minWidth={0}
      >
        <span>
          {props.selected ? <b>{props.result.requirement_id}</b> : props.result.requirement_id}
        </span>
      </text>
      <Show when={report.view().classification}>
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          flexShrink={0}
          width={12}
          content={props.result.binding ? "binding" : "interpretive"}
        />
      </Show>
    </Clickable>
  )
}