/**
 * Theme picker dialog — enterprise palette selection modal panel.
 */

import { For } from "solid-js"
import { useDialog } from "./dialog.tsx"
import { useTheme } from "../context/theme.tsx"
import type { PaletteId } from "../theme/palettes.ts"
import { Clickable } from "./clickable.tsx"
import { ModalPanel } from "./modal-panel.tsx"

export function DialogTheme() {
  const dialog = useDialog()
  const theme = useTheme()

  const select = (id: PaletteId) => {
    theme.setPalette(id)
    dialog.pop()
  }

  return (
    <ModalPanel title="Theme" subtitle="enterprise chrome palettes" stackDepth={dialog.stack().length} width={68}>
      <For each={theme.palettes()}>
        {(palette) => {
          const active = () => theme.paletteId() === palette.id
          return (
            <Clickable
              cursor="pointer"
              flexDirection="row"
              gap={1}
              paddingLeft={1}
              paddingRight={1}
              active={active()}
              onClick={() => select(palette.id)}
            >
              <text
                fg={active() ? theme.color.info : theme.color.textMuted}
                wrapMode="none"
                width={2}
                content={active() ? "●" : "○"}
              />
              <text
                fg={active() ? theme.color.text : theme.color.textSecondary}
                attributes={active() ? theme.attr.bold : theme.attr.none}
                wrapMode="none"
                width={18}
                content={palette.label}
              />
              <text
                fg={theme.color.textMuted}
                attributes={theme.attr.dim}
                wrapMode="none"
                flexGrow={1}
                content={palette.description}
              />
            </Clickable>
          )
        }}
      </For>
    </ModalPanel>
  )
}
