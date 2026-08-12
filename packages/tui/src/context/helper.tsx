/**
 * The context factory every provider in this TUI is built from.
 *
 * Lifted from nikcli's `src/cli/cmd/tui/context/helper.tsx`, which is the shape the rest of this
 * package's providers assume: `init` runs once inside the provider, its return value is the context,
 * and `use()` throws rather than handing back `undefined` if a component reaches for a provider that
 * is not above it.
 *
 * What a reader must not break: `use()` throws. A context that silently returned `undefined` would
 * turn a mis-ordered provider stack into a blank panel at runtime instead of a crash at mount, and a
 * blank panel in this UI reads as *there is nothing to report*, which is the one thing every
 * rendering here is forbidden to imply.
 */

import { createContext, type ParentProps, useContext } from "solid-js"

export function createSimpleContext<T, Props extends Record<string, unknown>>(input: {
  name: string
  init: (props: Props) => T
}) {
  const ctx = createContext<T>()

  return {
    provider: (props: ParentProps<Props>) => {
      const value = input.init(props as unknown as Props)
      return <ctx.Provider value={value}>{props.children}</ctx.Provider>
    },
    use(): T {
      const value = useContext(ctx)
      if (value === undefined) {
        throw new Error(`${input.name} context must be used within its provider`)
      }
      return value
    },
  }
}
