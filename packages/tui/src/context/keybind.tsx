/**
 * The keybind context — OpenTUI keyboard + leader key + command palette.
 */

import { createSignal } from "solid-js"
import type { KeyEvent } from "@opentui/core"
import { useKeyboard, useRenderer } from "@opentui/solid"
import { createSimpleContext } from "./helper.tsx"
import { useReport } from "./report.tsx"
import { useRoute } from "./route.tsx"
import { useTheme } from "./theme.tsx"
import { useDialog } from "../ui/dialog.tsx"
import { DialogCommandPalette } from "../ui/dialog-command-palette.tsx"
import { DialogHelp } from "../ui/dialog-help.tsx"
import { DialogSettings } from "../ui/dialog-settings.tsx"
import { DialogTheme } from "../ui/dialog-theme.tsx"
import { Keybind } from "../util/keybind.ts"

export interface Binding {
  readonly keys: string
  readonly label: string
  readonly on: ReadonlyArray<"findings" | "detail" | "limits" | "settings">
  readonly leader?: boolean
}

export const BINDINGS: readonly Binding[] = [
  { keys: "ctrl+p", label: "commands", on: ["findings", "detail", "limits", "settings"] },
  { keys: "j/k ↑↓", label: "move", on: ["findings"] },
  { keys: "enter", label: "open", on: ["findings"] },
  { keys: "esc", label: "back", on: ["detail", "limits", "settings"] },
  { keys: "a", label: "audience", on: ["findings", "detail", "limits", "settings"] },
  { keys: "L", label: "limits", on: ["findings", "detail", "settings"] },
  { keys: "t", label: "theme", on: ["findings", "detail", "limits", "settings"], leader: true },
  { keys: "h", label: "help", on: ["findings", "detail", "limits", "settings"], leader: true },
  { keys: "q", label: "quit", on: ["findings", "detail", "limits", "settings"] },
  { keys: "?", label: "help", on: ["findings", "detail", "limits", "settings"] },
]

export const { use: useKeybind, provider: KeybindProvider } = createSimpleContext({
  name: "Keybind",
  init: () => {
    const renderer = useRenderer()
    const report = useReport()
    const route = useRoute()
    const theme = useTheme()
    const dialog = useDialog()
    const [leader, setLeader] = createSignal(false)

    let leaderTimeout: ReturnType<typeof setTimeout> | undefined
    const LEADER_TIMEOUT_MS = 2000

    const openCommandPalette = () =>
      dialog.push(() => <DialogCommandPalette />, { size: "large" })
    const openHelp = () => dialog.push(() => <DialogHelp />, { size: "large" })
    const openTheme = () => dialog.push(() => <DialogTheme />)
    const openSettings = () => dialog.push(() => <DialogSettings />, { size: "large" })
    const quit = () => renderer.stop()

    const activateLeader = () => {
      setLeader(true)
      if (leaderTimeout) clearTimeout(leaderTimeout)
      leaderTimeout = setTimeout(() => setLeader(false), LEADER_TIMEOUT_MS)
    }

    const deactivateLeader = () => {
      setLeader(false)
      if (leaderTimeout) clearTimeout(leaderTimeout)
    }

    const dispatchLeader = (name: string) => {
      deactivateLeader()
      switch (name) {
        case "h":
          openHelp()
          return
        case "t":
          openTheme()
          return
        case "a":
          report.cycleAudience()
          return
        case "l":
          route.navigate({ type: "limits" })
          return
        case "q":
          quit()
          return
      }
    }

    const matches = (spec: string, event: KeyEvent, inLeader: boolean): boolean => {
      const parsed = Keybind.fromParsedKey(event, inLeader)
      return Keybind.parse(spec).some((candidate) => Keybind.match(candidate, parsed))
    }

    useKeyboard((event) => {
      if (Keybind.isRepeat(event)) return

      if (event.ctrl && event.name === ",") {
        openSettings()
        return
      }

      if (matches("ctrl+p", event, false)) {
        openCommandPalette()
        return
      }

      if (dialog.isOpen()) return

      if (matches("ctrl+c", event, false)) {
        quit()
        return
      }

      if (matches("ctrl+x", event, false) && !leader()) {
        activateLeader()
        return
      }

      if (leader() && event.name && !event.ctrl) {
        dispatchLeader(event.name)
        return
      }

      switch (event.name) {
        case "q":
          quit()
          return
        case "?":
          openHelp()
          return
        case "t":
          if (!event.ctrl) {
            theme.cyclePalette()
            return
          }
          break
        case "escape":
          if (leader()) {
            deactivateLeader()
            return
          }
          route.back()
          return
        case "a":
          report.cycleAudience()
          return
        case "l":
          if (event.shift) route.navigate({ type: "limits" })
          return
      }

      if (route.route().type !== "findings") return

      switch (event.name) {
        case "j":
        case "down":
          report.next()
          return
        case "k":
        case "up":
          report.previous()
          return
        case "g":
          if (event.shift) report.last()
          else report.first()
          return
        case "home":
          report.first()
          return
        case "end":
          report.last()
          return
        case "return":
        case "enter":
          route.navigate({ type: "detail" })
          return
      }
    })

    function click(action: string): void {
      switch (action) {
        case "commands":
          openCommandPalette()
          return
        case "quit":
          quit()
          return
        case "help":
          openHelp()
          return
        case "theme":
          openTheme()
          return
        case "back":
          route.back()
          return
        case "audience":
          report.cycleAudience()
          return
        case "limits":
          route.navigate({ type: "limits" })
          return
        case "open":
          route.navigate({ type: "detail" })
          return
        case "move":
          return
      }
    }

    return {
      bindings: BINDINGS,
      leader,
      printFor(action: string): string {
        const match = BINDINGS.find((b) => b.label === action)
        if (!match) return ""
        if (match.leader) return `ctrl+x ${match.keys.split(" ")[0] ?? match.keys}`
        return match.keys
      },
      quit,
      click,
      openCommandPalette,
      openHelp,
      openTheme,
      openSettings,
    }
  },
})
