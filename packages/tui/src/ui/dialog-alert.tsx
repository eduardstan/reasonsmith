/**
 * Alert dialog — promise-based modal confirmation panel.
 */

import { TextAttributes } from "@opentui/core"
import { useKeyboard } from "@opentui/solid"
import { useDialog, type DialogContext } from "./dialog.tsx"
import { useTheme } from "../context/theme.tsx"
import { Button } from "./button.tsx"
import { ModalPanel } from "./modal-panel.tsx"

export interface DialogAlertProps {
  readonly title: string
  readonly message: string
  readonly onConfirm?: () => void
}

export function DialogAlert(props: DialogAlertProps) {
  const dialog = useDialog()
  const t = useTheme()

  function confirm() {
    props.onConfirm?.()
    dialog.pop()
  }

  useKeyboard((evt) => {
    if (evt.name === "return") {
      evt.preventDefault()
      confirm()
    }
  })

  return (
    <ModalPanel title={props.title} stackDepth={dialog.stack().length} width={52}>
      <text fg={t.color.textSecondary} wrapMode="none" content={props.message} />
      <box flexDirection="row" justifyContent="flex-end" paddingTop={1}>
        <Button label="OK" onClick={confirm} />
      </box>
    </ModalPanel>
  )
}

DialogAlert.show = (dialog: Readonly<DialogContext>, title: string, message: string): Promise<void> => {
  return new Promise<void>((resolve) => {
    dialog.push(() => <DialogAlert title={title} message={message} onConfirm={() => resolve()} />)
  })
}
