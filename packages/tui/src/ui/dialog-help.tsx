/**
 * Help dialog — keybindings and audiences in a modal panel.
 */

import { For, Show, createMemo } from "solid-js"
import { TextAttributes } from "@opentui/core"
import type { Audience } from "../types/audiences.ts"
import { useDialog } from "./dialog.tsx"
import { useKeybind } from "../context/keybind.tsx"
import { useReport } from "../context/report.tsx"
import { useTheme } from "../context/theme.tsx"
import { AUDIENCE_HELP, AUDIENCE_LABELS } from "./audiences.ts"
import { Button } from "./button.tsx"
import { Clickable } from "./clickable.tsx"
import { ModalPanel } from "./modal-panel.tsx"

const SHORTCUT_BINDINGS = ["commands", "move", "open", "back", "audience", "limits", "quit"] as const

export function DialogHelp() {
  const dialog = useDialog()
  const keybind = useKeybind()
  const report = useReport()
  const t = useTheme()

  const shortcutRows = createMemo(() =>
    SHORTCUT_BINDINGS.map((action) => {
      const keys = keybind.printFor(action)
      const binding = keybind.bindings.find((b) => b.label === action)
      return { keys, label: binding?.label ?? action }
    }).filter((row) => row.keys !== ""),
  )

  const audienceRows = createMemo(() =>
    report.audiences.map((a) => ({
      audience: a,
      name: AUDIENCE_LABELS[a] ?? a,
      description: AUDIENCE_HELP[a] ?? "",
    })),
  )

  return (
    <ModalPanel title="Help" subtitle="shortcuts and audience projections" stackDepth={dialog.stack().length} width={78}>
      <box flexDirection="row" gap={3} paddingTop={1}>
        <box flexDirection="column" gap={1} flexGrow={1}>
          <text fg={t.color.info} attributes={t.attr.bold} wrapMode="none" content="Shortcuts" />
          <For each={shortcutRows()}>
            {(row) => (
              <box flexDirection="row" gap={1}>
                <text fg={t.color.text} attributes={TextAttributes.BOLD} wrapMode="none" width={14} content={row.keys} />
                <text fg={t.color.textMuted} wrapMode="none" content={row.label} />
              </box>
            )}
          </For>
          <text fg={t.color.info} attributes={t.attr.bold} wrapMode="none" content="Leader (ctrl+x)" />
          <text fg={t.color.textMuted} wrapMode="none" content="h help · t theme · a audience · l limits · q quit" />
        </box>

        <box flexDirection="column" gap={1} flexGrow={1}>
          <text fg={t.color.info} attributes={t.attr.bold} wrapMode="none" content="Audiences" />
          <For each={audienceRows()}>
            {(row) => (
              <Clickable
                cursor="pointer"
                flexDirection="column"
                onClick={() => report.setAudience(row.audience)}
              >
                <text fg={t.color.text} attributes={TextAttributes.BOLD} wrapMode="none" content={row.name} />
                <text fg={t.color.textMuted} wrapMode="none" content={row.description} />
              </Clickable>
            )}
          </For>
        </box>
      </box>

      <box flexDirection="row" justifyContent="flex-end" paddingTop={1}>
        <Button label="OK" onClick={() => dialog.pop()} />
      </box>
    </ModalPanel>
  )
}
