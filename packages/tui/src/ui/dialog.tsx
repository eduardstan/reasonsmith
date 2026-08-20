/**
 * The dialog overlay system — stacked modal panels (nikcli / opencode shape).
 *
 * API:
 *   push()    — stack a modal (command palette → theme picker → …)
 *   replace() — clear stack and open one modal
 *   pop()     — close the top modal (escape, backdrop)
 *   clear()   — dismiss entire stack
 */

import { type JSX, type ParentProps, Show, createContext, useContext } from "solid-js"
import { createStore } from "solid-js/store"
import { useKeyboard } from "@opentui/solid"
import { createSimpleContext } from "../context/helper.tsx"
import { useTheme } from "../context/theme.tsx"
import { GlassBorder } from "./border.ts"

export type DialogSize = "small" | "medium" | "large" | "full"

interface DialogEntry {
  element: JSX.Element | (() => JSX.Element)
  size: DialogSize
  onClose?: () => void
}

export interface DialogContext {
  readonly stack: () => readonly DialogEntry[]
  readonly isOpen: () => boolean
  // eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- JSX elements are immutable dialog entries.
  push(input: JSX.Element | (() => JSX.Element), options?: { size?: DialogSize; onClose?: () => void }): void
  // eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- JSX elements are immutable dialog entries.
  replace(input: JSX.Element | (() => JSX.Element), options?: { size?: DialogSize; onClose?: () => void }): void
  pop(): void
  clear(): void
}

const DialogCtx = createContext<DialogContext>()

export const { use: useDialog, provider: DialogProvider } = createSimpleContext({
  name: "Dialog",
  init: () => {
    const [store, setStore] = createStore<{ stack: DialogEntry[] }>({ stack: [] })

    function pop() {
      const top = store.stack.at(-1)
      if (!top) return
      setStore("stack", store.stack.slice(0, -1))
      top.onClose?.()
    }

    useKeyboard((evt) => {
      if (store.stack.length === 0) return
      if (evt.name === "escape") {
        evt.preventDefault()
        evt.stopPropagation()
        pop()
        return
      }
      if (evt.ctrl && evt.name === "c") {
        evt.preventDefault()
        evt.stopPropagation()
        setStore("stack", [])
      }
    })

    return {
      get stack() {
        return () => store.stack
      },
      isOpen: () => store.stack.length > 0,
      push(input, options) {
        const entry: DialogEntry = {
          element: input,
          size: options?.size ?? "medium",
          onClose: options?.onClose,
        }
        setStore("stack", [...store.stack, entry])
      },
      replace(input, options) {
        const entry: DialogEntry = {
          element: input,
          size: options?.size ?? "medium",
          onClose: options?.onClose,
        }
        setStore("stack", [entry])
      },
      pop,
      clear() {
        for (const entry of [...store.stack].reverse()) entry.onClose?.()
        setStore("stack", [])
      },
    } satisfies DialogContext as DialogContext
  },
})

function panelWidth(size: DialogSize): number | "100%" {
  switch (size) {
    case "full":
      return "100%"
    case "large":
      return 80
    case "small":
      return 40
    default:
      return 64
  }
}

// eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- Solid JSX children are immutable at the component boundary.
function Overlay(props: Readonly<{
  children: JSX.Element
  size: DialogSize
  depth: number
  onBackdropClick: () => void
}>) {
  const t = useTheme()

  return (
    <box
      position="absolute"
      top={0}
      left={0}
      width="100%"
      height="100%"
      alignItems="center"
      justifyContent="center"
      backgroundColor={t.color.bg}
      onMouseUp={props.onBackdropClick}
    >
      <box
        width={panelWidth(props.size)}
        flexDirection="column"
        backgroundColor={t.color.surface}
        paddingLeft={1}
        paddingRight={1}
        paddingTop={1}
        paddingBottom={1}
        border={[...GlassBorder.border]}
        customBorderChars={GlassBorder.customBorderChars}
        onMouseUp={(event) => event.stopPropagation()}
      >
        <Show when={props.depth > 1}>
          <box flexDirection="row" justifyContent="flex-end" height={1}>
            <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none">
              {`modal ${props.depth}`}
            </text>
          </box>
        </Show>
        {props.children}
      </box>
    </box>
  )
}

// eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- Solid ParentProps are immutable at the component boundary.
export function DialogProviderWithOverlay(props: Readonly<ParentProps>) {
  return (
    <DialogProvider>
      <DialogConsumers>{props.children}</DialogConsumers>
    </DialogProvider>
  )
}

// eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- Solid JSX children are immutable at the component boundary.
function DialogConsumers(props: Readonly<{ children: JSX.Element }>) {
  const value = useDialog()
  const top = () => value.stack().at(-1)

  return (
    <>
      {props.children}
      <Show when={top()}>
        {(entry) => {
          const e = entry()
          const node = e.element
          const rendered: JSX.Element =
            typeof node === "function" ? (node as () => JSX.Element)() : node
          return (
            <Overlay
              size={e.size}
              depth={value.stack().length}
              onBackdropClick={() => value.pop()}
            >
              {rendered}
            </Overlay>
          )
        }}
      </Show>
    </>
  )
}
