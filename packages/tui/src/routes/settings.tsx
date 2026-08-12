/**
 * The settings route — settings body in a route panel.
 */

import { useTheme } from "../context/theme.tsx"
import { SettingsBody } from "./settings-body.tsx"

export function Settings() {
  const theme = useTheme()
  return (
    <box flexDirection="column" flexGrow={1} minHeight={0} width="100%">
      <box
        flexDirection="column"
        flexGrow={1}
        minHeight={0}
        width="100%"
        borderStyle="rounded"
        borderColor={theme.color.border}
        backgroundColor={theme.color.surface}
        paddingLeft={1}
        paddingRight={1}
        title="Settings"
        titleAlignment="left"
      >
        <SettingsBody />
      </box>
    </box>
  )
}
