/**
 * Command palette — searchable modal command panel (nikcli / opencode shape).
 */

import { For, Show, createMemo, createSignal } from "solid-js"
import { useKeyboard, useRenderer } from "@opentui/solid"
import { useDialog } from "./dialog.tsx"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"
import { ModalPanel } from "./modal-panel.tsx"
import { Clickable } from "./clickable.tsx"
import { type Command, buildCommands, filterCommands, runCommand } from "./commands.ts"
import { DialogHelp } from "./dialog-help.tsx"
import { DialogSettings } from "./dialog-settings.tsx"
import { DialogTheme } from "./dialog-theme.tsx"

const GROUP_ORDER = ["navigation", "audience", "theme", "report", "system"] as const
const GROUP_LABELS: Record<string, string> = {
  navigation: "Navigation",
  audience: "Audience",
  theme: "Theme",
  report: "Report",
  system: "System",
}

export function DialogCommandPalette() {
  const dialog = useDialog()
  const renderer = useRenderer()
  const theme = useTheme()
  const report = useReport()
  const route = useRoute()
  const [query, setQuery] = createSignal("")
  const [selected, setSelected] = createSignal(0)

  const ctx = () => ({
    navigate: (type: "findings" | "detail" | "limits" | "settings") => route.navigate({ type }),
    cycleAudience: report.cycleAudience,
    setAudience: report.setAudience,
    cyclePalette: theme.cyclePalette,
    setPalette: theme.setPalette,
    clearCategoryFilter: report.clearCategoryFilter,
    openHelp: () => dialog.push(() => <DialogHelp />, { size: "large" }),
    openTheme: () => dialog.push(() => <DialogTheme />),
    openSettings: () => dialog.push(() => <DialogSettings />, { size: "large" }),
    openCommandPalette: () => {},
    quit: () => renderer.stop(),
  })

  const filtered = createMemo(() => filterCommands(buildCommands(ctx()), query()))
  const depth = () => dialog.stack().length

  const clamp = (index: number) => {
    const max = filtered().length - 1
    if (max < 0) return 0
    return Math.min(Math.max(index, 0), max)
  }

  const execute = (cmd: Command) => {
    dialog.pop()
    runCommand(cmd.id, ctx())
  }

  useKeyboard((evt) => {
    if (evt.name === "escape") {
      evt.preventDefault()
      evt.stopPropagation()
      dialog.pop()
      return
    }
    if (evt.name === "return" || evt.name === "enter") {
      const cmd = filtered()[selected()]
      if (cmd) {
        evt.preventDefault()
        evt.stopPropagation()
        execute(cmd)
      }
      return
    }
    switch (evt.name) {
      case "j":
      case "down":
        setSelected((i) => clamp(i + 1))
        return
      case "k":
      case "up":
        setSelected((i) => clamp(i - 1))
        return
      case "home":
        setSelected(0)
        return
      case "end":
        setSelected(clamp(filtered().length - 1))
        return
    }
  })

  const byGroup = createMemo(() => {
    const map = new Map<string, Command[]>()
    for (const cmd of filtered()) {
      const list = map.get(cmd.group) ?? []
      list.push(cmd)
      map.set(cmd.group, list)
    }
    return GROUP_ORDER.filter((g) => map.has(g)).map((g) => ({ group: g, items: map.get(g)! }))
  })

  const indexOf = (cmd: Command) => filtered().indexOf(cmd)

  return (
    <ModalPanel
      title="Command palette"
      subtitle="type to filter · enter to run · esc to close"
      stackDepth={depth()}
      width={72}
    >
      <box flexDirection="row" gap={1} flexShrink={0} width="100%" marginBottom={1}>
        <text fg={theme.color.info} wrapMode="none" content=">" />
        <input
          flexGrow={1}
          minWidth={0}
          placeholder="search commands…"
          backgroundColor={theme.color.surfaceRaised}
          focusedBackgroundColor={theme.color.surfaceRaised}
          textColor={theme.color.text}
          cursorColor={theme.color.info}
          value={query()}
          onInput={(value) => {
            setQuery(value)
            setSelected(0)
          }}
        />
      </box>
      <scrollbox flexGrow={1} minHeight={0} maxHeight={18} width="100%" backgroundColor={theme.color.bg}>
        <Show
          when={filtered().length > 0}
          fallback={
            <text
              fg={theme.color.textMuted}
              attributes={theme.attr.dim}
              wrapMode="none"
              content="no matching commands"
            />
          }
        >
          <For each={byGroup()}>
            {(section) => (
              <box flexDirection="column" width="100%">
                <text
                  fg={theme.color.info}
                  attributes={theme.attr.bold}
                  wrapMode="none"
                  content={GROUP_LABELS[section.group] ?? section.group}
                />
                <For each={section.items}>
                  {(cmd) => {
                    const index = () => indexOf(cmd)
                    const active = () => selected() === index()
                    return (
                      <Clickable
                        cursor="pointer"
                        flexDirection="row"
                        gap={2}
                        height={1}
                        width="100%"
                        active={active()}
                        onClick={() => execute(cmd)}
                        onHover={() => setSelected(index())}
                      >
                        <text
                          fg={active() ? theme.color.text : theme.color.textSecondary}
                          wrapMode="none"
                          flexGrow={1}
                          minWidth={0}
                          content={cmd.label}
                        />
                        <Show when={cmd.keys}>
                          <text
                            fg={theme.color.textMuted}
                            attributes={theme.attr.dim}
                            wrapMode="none"
                            content={cmd.keys!}
                          />
                        </Show>
                      </Clickable>
                    )
                  }}
                </For>
              </box>
            )}
          </For>
        </Show>
      </scrollbox>
    </ModalPanel>
  )
}
