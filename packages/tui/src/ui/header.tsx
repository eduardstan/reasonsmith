/**
 * The top bar — the masthead, in nikcli's tab-bar shape.
 *
 * Two rows in a single dark band:
 *   1. The brand mark + a row of tabs (Findings, Limits, Settings) — each tab is a
 *      `div` with `onMouseOver`/`onMouseUp` so the reader can browse the surface with the mouse.
 *   2. The breadcrumb: the system name + pack id + the active audience + a hairline.
 *
 * The masthead is the one surface every route shares. It never reacts to nothing — even the loading
 * screen shows the masthead, so a reader who landed here knows they are in the right tool.
 *
 * The tabs are the same component ("tab") with three states (default / hover / active). The same
 * component is reused across the row, the same way nikcli's `TabBar` uses one element and switches
 * its background/foreground by state.
 */

import { For, Show, createSignal } from "solid-js"
import { useLayout } from "../context/layout.tsx"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useKeybind } from "../context/keybind.tsx"
import { useTheme } from "../context/theme.tsx"
import { wrap } from "../theme.ts"
import { Clickable } from "./clickable.tsx"

const TABS = [
  { type: "findings", label: "Findings" },
  { type: "limits", label: "Limits" },
  { type: "settings", label: "Settings" },
] as const

export function ReportHeader() {
  const t = useTheme()
  const route = useRoute()
  const report = useReport()
  const keybind = useKeybind()
  const layout = useLayout()
  // Read, never re-derived: the sentence is the Python's, and the record carries it whole.
  const notice = () => report.report.undeclared_domain_notice
  const [hovered, setHovered] = createSignal<string | null>(null)

  /**
   * The breadcrumb's parts, measured against the row they share.
   *
   * `flexGrow` cannot save a row that is already over budget: once the contents exceed the width the
   * spacer collapses to nothing and the two halves are drawn touching — `6 requirementsctrl+p`. So
   * the optional parts are dropped by measurement, in the order they are least missed, and what
   * remains is what fits.
   */
  // The header's own frame (two border cells) and padding (two), plus two cells so the two halves
  // of the row are visibly apart rather than merely not overlapping.
  const BREADCRUMB_CHROME = 6

  const breadcrumbTail = () => `ctrl+p · for: ${report.audience()}`
  const breadcrumbHead = () => `${report.report.system_name}  ·  pack ${report.report.pack_id}`
  const requirementsPart = () => `  ·  ${report.report.results.length} requirements`
  const showRequirements = () =>
    breadcrumbHead().length + requirementsPart().length + breadcrumbTail().length +
    BREADCRUMB_CHROME <=
    layout.cols()
  const showPaletteHint = () =>
    breadcrumbHead().length + breadcrumbTail().length + BREADCRUMB_CHROME <= layout.cols()

  /** A headline that does not fit is clipped mid-count, which reads as a wrong number. */
  const showHeadline = () =>
    report.view().headline &&
    layout.showHeadline() &&
    report.report.headline.length + 2 <= layout.cols()

  return (
    <box
      flexDirection="column"
      width="100%"
      flexShrink={0}
      backgroundColor={t.color.surface}
      borderStyle="single"
      borderColor={t.color.borderSubtle}
      paddingLeft={1}
      paddingRight={1}
    >
      {/*
        Three rows where the masthead fits, one where it does not. `tiny` is the smallest ASCII art
        font OpenTUI ships and it still needs three rows and roughly a third of an 88-column
        terminal; below that the brand mark is the first thing to go, because it is the only element
        in this header that tells a reader nothing about their run.
      */}
      <box flexDirection="row" height={layout.showMasthead() ? 3 : 1} width="100%">
        <Show
          when={layout.showMasthead()}
          fallback={
            <text fg={t.color.info} attributes={t.attr.bold} wrapMode="none" content="reasonsmith" />
          }
        >
          <ascii_font text="REASONSMITH" font="tiny" color={t.color.info} />
        </Show>
        <text fg={t.color.borderSubtle} wrapMode="none">
          {"  "}
          {SEPARATOR.vertical}
          {"  "}
        </text>
        <For each={TABS}>
          {(tab) => (
            <Tab
              label={tab.label}
              active={route.route().type === tab.type}
              hovered={hovered() === tab.type}
              onHover={() => setHovered(tab.type)}
              onLeave={() => setHovered((cur) => (cur === tab.type ? null : cur))}
              onClick={() => route.navigate({ type: tab.type })}
            />
          )}
        </For>
        {/*
          There was a second `+ settings` tab pinned to the right of this row, in the accent colour,
          navigating to the route the `Settings` tab three cells to the left already navigates to.
          Two controls for one destination is not a shortcut, it is a reader wondering what the
          difference is.
        */}
        <box flexGrow={1} />
      </box>

      <box flexDirection="row" height={1} width="100%">
        <text fg={t.color.textSecondary} wrapMode="none">
          {report.report.system_name}
        </text>
        <text fg={t.color.borderSubtle} wrapMode="none">
          {"  "}
          {SEPARATOR.dot}
          {"  "}
        </text>
        <text fg={t.color.textMuted} wrapMode="none" attributes={t.attr.dim}>
          pack {report.report.pack_id}
        </text>
        {/*
          The requirement count and the palette hint are the two things on this row a reader can get
          elsewhere — the count from the findings panel's own frame, the hint from the footer — so
          they are what the breadcrumb sheds first. The system name, the pack and the audience stay
          at every width: they are what the report is *of*, and a screen that cannot say which run it
          is showing is not a smaller screen, it is an unattributed one.
        */}
        <Show when={showRequirements()}>
          <text fg={t.color.borderSubtle} wrapMode="none">
            {"  "}
            {SEPARATOR.dot}
            {"  "}
          </text>
          <text fg={t.color.textMuted} wrapMode="none" attributes={t.attr.dim}>
            {report.report.results.length} requirements
          </text>
        </Show>
        <box flexGrow={1} />
        <Show when={showPaletteHint()}>
          <Clickable cursor="pointer" onClick={() => keybind.openCommandPalette()}>
            <text fg={t.color.textMuted} wrapMode="none" content="ctrl+p" />
          </Clickable>
          <text fg={t.color.borderSubtle} wrapMode="none" content=" · " />
        </Show>
        <Clickable cursor="pointer" onClick={() => report.cycleAudience()}>
          <text fg={t.color.info} wrapMode="none">
            for: <b>{report.audience()}</b>
          </text>
        </Clickable>
      </box>

      {/*
        The headline is a summary of counts the status bar shows individually one row below, so on a
        short terminal it is the row that buys the most and costs the least.
      */}
      <Show when={showHeadline()}>
        <box flexDirection="row" height={1}>
          <text fg={t.color.textSecondary} wrapMode="none">
            {report.report.headline}
          </text>
        </box>
      </Show>

      {/*
        Never behind a breakpoint, at any width or height. A run that skipped domain-limited duties
        exits exactly as a clean run does, so this sentence is what the exit code cannot carry — and
        a layout that dropped it to fit would turn a rendering decision into a compliance one. It
        wraps to the terminal's own width, which is what it failed to do when it wrapped to 96 in an
        80-column window and tore across the rows beneath it.
      */}
      <Show when={notice()}>
        {(text) => (
          <box flexDirection="column" marginTop={0} marginBottom={layout.gap()}>
            <For each={wrap(text(), Math.max(layout.cols() - 4, 24))}>
              {(line) => <text fg={t.color.warn} wrapMode="none" content={line} />}
            </For>
          </box>
        )}
      </Show>
    </box>
  )
}

const SEPARATOR = {
  horizontal: "─",
  vertical: "│",
  dot: "·",
} as const

function Tab(props: {
  label: string
  active: boolean
  hovered: boolean
  onHover: () => void
  onLeave: () => void
  onClick: () => void
  accent?: boolean
}) {
  const t = useTheme()
  const fg = () => {
    if (props.active) return t.color.text
    if (props.hovered) return t.color.textSecondary
    return props.accent ? t.color.info : t.color.textMuted
  }
  return (
    <Clickable
      cursor="pointer"
      paddingLeft={1}
      paddingRight={1}
      active={props.active}
      onClick={props.onClick}
      onHover={props.onHover}
      onLeave={props.onLeave}
    >
      <text
        fg={fg()}
        attributes={props.active ? t.attr.bold : t.attr.none}
        wrapMode="none"
      >
        {props.label}
      </text>
    </Clickable>
  )
}