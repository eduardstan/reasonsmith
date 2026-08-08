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
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useKeybind } from "../context/keybind.tsx"
import { useTheme } from "../context/theme.tsx"
import { wrap } from "../theme.ts"
import { Clickable } from "./clickable.tsx"
import { undeclaredDomainNotice } from "../types/schema.ts"

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
  const notice = () => undeclaredDomainNotice(report.report)
  const [hovered, setHovered] = createSignal<string | null>(null)

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
      <box flexDirection="row" height={3} width="100%">
        {/*
          `tiny` is the smallest ASCII art font OpenTUI ships. The user asked for "1Row" or "small";
          neither exists, so we use the smallest available. The masthead sits in a 3-row row so the
          font's vertical extent fits without clipping.
        */}
        <ascii_font text="REASONSMITH" font="tiny" color={t.color.info} />
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
        <box flexGrow={1} />
        <Tab
          label="+ settings"
          active={false}
          hovered={hovered() === "settings"}
          onHover={() => setHovered("settings")}
          onLeave={() => setHovered((cur) => (cur === "settings" ? null : cur))}
          onClick={() => route.navigate({ type: "settings" })}
          accent
        />
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
        <text fg={t.color.borderSubtle} wrapMode="none">
          {"  "}
          {SEPARATOR.dot}
          {"  "}
        </text>
        <text fg={t.color.textMuted} wrapMode="none" attributes={t.attr.dim}>
          {report.report.results.length} requirements
        </text>
        <box flexGrow={1} />
        <Clickable cursor="pointer" onClick={() => keybind.openCommandPalette()}>
          <text fg={t.color.textMuted} wrapMode="none" content="ctrl+p" />
        </Clickable>
        <text fg={t.color.borderSubtle} wrapMode="none" content=" · " />
        <Clickable cursor="pointer" onClick={() => report.cycleAudience()}>
          <text fg={t.color.info} wrapMode="none">
            for: <b>{report.audience()}</b>
          </text>
        </Clickable>
      </box>

      <Show when={report.view().headline}>
        <box flexDirection="row" height={1}>
          <text fg={t.color.textSecondary} wrapMode="none">
            {report.report.headline}
          </text>
        </box>
      </Show>

      <Show when={notice()}>
        {(text) => (
          <box flexDirection="column" marginTop={0} marginBottom={1}>
            <For each={wrap(text(), 96)}>
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