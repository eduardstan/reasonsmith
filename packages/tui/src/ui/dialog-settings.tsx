/**
 * Settings modal panel — the settings route content as a stacked dialog.
 */

import { useDialog } from "./dialog.tsx"
import { ModalPanel } from "./modal-panel.tsx"
import { SettingsBody } from "../routes/settings-body.tsx"

export function DialogSettings() {
  const dialog = useDialog()
  const depth = () => dialog.stack().length

  return (
    <ModalPanel title="Settings" subtitle="enterprise configuration" stackDepth={depth()} width={70}>
      <SettingsBody compact />
    </ModalPanel>
  )
}
