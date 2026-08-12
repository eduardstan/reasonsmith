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
 *   - **A category filter answers with the rows that number counted, and no others.** The counters
 *     it is driven from are the record's unprefixed counts, which are binding-only; the membership
 *     test is `types/categories.ts` and lives there once, for the bar and this list together. The
 *     filter chip says `binding` out loud, so the narrowing is on screen rather than inferred from a
 *     shorter list.
 *   - **The undeclared-domain notice is not tucked away.** A run that skipped domain-limited duties
 *     exits exactly as a clean run does, so the report has to carry what the exit code cannot; the
 *     header prints it in full whenever it is present.
 */

import { For, Show, createMemo, createSignal } from "solid-js"
import type { RequirementResult } from "../types/schema.ts"
import { matchesCategory } from "../types/categories.ts"
import { useLayout } from "../context/layout.tsx"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"
import { VerdictChip } from "../ui/verdict-chip.tsx"
import { Clickable } from "../ui/clickable.tsx"

export function Findings() {
  const t = useTheme()
  const report = useReport()
  const route = useRoute()
  const layout = useLayout()
  const [filter, setFilter] = createSignal("")

  const filtered = createMemo(() => {
    const query = filter().trim().toLowerCase()
    const category = report.categoryFilter()
    let rows = report.results()
    if (query !== "") {
      rows = rows.filter((r) => r.requirement_id.toLowerCase().includes(query))
    }
    if (category) {
      rows = rows.filter((r) => matchesCategory(r, category))
    }
    return rows
  })

  // Name whichever filter emptied the list. A category filter that matched nothing used to report
  // `no requirement matches ""`, which reads as a broken search rather than as an empty category.
  const emptyMessage = () => {
    const query = filter().trim()
    const category = report.categoryFilter()
    if (category && query) {
      return `no binding requirement is ${category.replace(/_/g, " ")} with "${query}" in its id`
    }
    if (category) return `no binding requirement is ${category.replace(/_/g, " ")}`
    return `no requirement matches "${query}"`
  }

  // The panel frame carries the count, and says when it is showing fewer than all of them — a title
  // reading `Findings (18)` over eleven rows is the frame contradicting its own contents.
  const panelTitle = () => {
    const shown = filtered().length
    const all = report.results().length
    return shown === all ? `Findings (${all})` : `Findings (${shown} of ${all})`
  }

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
      title={panelTitle()}
      titleAlignment="left"
    >
      <box
        flexDirection="row"
        flexShrink={0}
        width="100%"
        paddingLeft={layout.pad()}
        paddingRight={layout.pad()}
        paddingTop={layout.gap()}
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
        paddingLeft={layout.pad()}
        paddingRight={layout.pad()}
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
              content={emptyMessage()}
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
  const layout = useLayout()

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
      {/*
        The classification column is dropped on a narrow terminal rather than truncated. `binding`
        and `interpretive` share no prefix, so a clipped column would read `bindin` / `interpr` and
        cost a reader more attention than it returns; the same fact is on the detail screen in full.
      */}
      <Show when={report.view().classification && layout.showCounterLabels()}>
        {/*
          Two leading spaces inside the text, not a gap: the row's gap does not apply between these
          children, so a long requirement id was drawn hard against the word after it —
          `..._timing_of_notice binding` with a single cell between them, at the width where the id
          is longest.
        */}
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          flexShrink={0}
          width={14}
        >
          {`  ${props.result.binding ? "binding" : "interpretive"}`}
        </text>
      </Show>
    </Clickable>
  )
}