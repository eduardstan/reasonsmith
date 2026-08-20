/**
 * Modal panel frame — nikcli/opencode dialog chrome with title bar and stack depth.
 */

import { Show, type JSX } from "solid-js"
import { useTheme } from "../context/theme.tsx"
import { GlassBorder } from "./border.ts"

export interface ModalPanelProps {
  readonly title: string
  readonly subtitle?: string
  readonly stackDepth?: number
  readonly width?: number
  readonly children: JSX.Element
  readonly footer?: JSX.Element
}

// eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- OpenTUI JSX props are immutable at the component boundary.
export function ModalPanel(props: ModalPanelProps) {
  const t = useTheme()
  const width = () => props.width ?? 64

  return (
    <box flexDirection="column" width={width()} gap={1}>
      <box flexDirection="row" justifyContent="space-between" width="100%">
        <box flexDirection="column">
          <text fg={t.color.text} attributes={t.attr.bold} wrapMode="none" content={props.title} />
          <Show when={props.subtitle}>
            {(sub) => (
              <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={sub()} />
            )}
          </Show>
        </box>
        <box flexDirection="row" gap={1}>
          <Show when={Boolean(props.stackDepth && props.stackDepth > 1)}>
            <text fg={t.color.warn} wrapMode="none" content={`${props.stackDepth}`} />
          </Show>
          <text fg={t.color.textMuted} wrapMode="none" content="esc" />
        </box>
      </box>
      <box
        flexDirection="column"
        width="100%"
        border={[...GlassBorder.border]}
        customBorderChars={GlassBorder.customBorderChars}
        backgroundColor={t.color.surface}
        paddingLeft={1}
        paddingRight={1}
        paddingTop={1}
        paddingBottom={1}
      >
        {props.children}
      </box>
      <Show when={props.footer}>{props.footer}</Show>
    </box>
  )
}
