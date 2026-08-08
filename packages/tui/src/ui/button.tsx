/**
 * Dialog button — mouse + keyboard dismiss, pointer cursor.
 */

import { TextAttributes } from "@opentui/core"
import { useTheme } from "../context/theme.tsx"
import { Clickable } from "./clickable.tsx"

export function Button(props: { label: string; onClick: () => void; primary?: boolean }) {
  const t = useTheme()
  return (
    <Clickable
      cursor="pointer"
      paddingLeft={3}
      paddingRight={3}
      onClick={props.onClick}
    >
      <box
        paddingLeft={3}
        paddingRight={3}
        backgroundColor={props.primary !== false ? t.color.info : t.color.surfaceRaised}
      >
        <text
          fg={props.primary !== false ? t.color.bg : t.color.text}
          attributes={TextAttributes.BOLD}
          wrapMode="none"
          content={props.label}
        />
      </box>
    </Clickable>
  )
}
