/**
 * Command registry — every action the command palette and leader key can dispatch.
 */

import type { Audience } from "../types/audiences.ts"
import { AUDIENCE_LABELS } from "./audiences.ts"
import type { PaletteId } from "../theme/palettes.ts"
import { PALETTE_IDS, getPalette } from "../theme/palettes.ts"

export type CommandGroup = "navigation" | "audience" | "theme" | "report" | "system"

export interface Command {
  readonly id: string
  readonly label: string
  readonly description: string
  readonly group: CommandGroup
  readonly keys?: string
  readonly keywords?: readonly string[]
}

export interface CommandContext {
  navigate: (route: "findings" | "detail" | "limits" | "settings") => void
  cycleAudience: () => void
  setAudience: (audience: Audience) => void
  cyclePalette: () => void
  setPalette: (id: PaletteId) => void
  clearCategoryFilter: () => void
  openHelp: () => void
  openTheme: () => void
  openSettings: () => void
  openCommandPalette: () => void
  quit: () => void
}

const ROUTES = [
  { id: "go-findings", route: "findings" as const, label: "Go to Findings", keys: "esc" },
  { id: "go-detail", route: "detail" as const, label: "Go to Detail", keys: "enter" },
  { id: "go-limits", route: "limits" as const, label: "Go to Limits", keys: "L" },
  { id: "go-settings", route: "settings" as const, label: "Go to Settings", keys: "ctrl+x , settings" },
]

export function buildCommands(ctx: CommandContext): readonly Command[] {
  const commands: Command[] = [
    ...ROUTES.map((r) => ({
      id: r.id,
      label: r.label,
      description: `Navigate to the ${r.route} route`,
      group: "navigation" as const,
      keys: r.keys,
      keywords: [r.route, "go", "open", "navigate"],
    })),
    {
      id: "command-palette",
      label: "Command palette",
      description: "Open this palette",
      group: "system",
      keys: "ctrl+p",
      keywords: ["palette", "commands", "search"],
    },
    {
      id: "help",
      label: "Help",
      description: "Keybindings and audiences",
      group: "system",
      keys: "?",
      keywords: ["help", "keys", "shortcuts"],
    },
    {
      id: "settings-modal",
      label: "Settings panel",
      description: "Open settings as a modal panel",
      group: "system",
      keys: "ctrl+,",
      keywords: ["settings", "config", "preferences"],
    },
    {
      id: "theme-picker",
      label: "Theme picker",
      description: "Choose an enterprise palette",
      group: "theme",
      keys: "ctrl+x t",
      keywords: ["theme", "palette", "colors"],
    },
    {
      id: "theme-cycle",
      label: "Cycle theme",
      description: "Switch to the next enterprise palette",
      group: "theme",
      keys: "t",
      keywords: ["theme", "palette", "dark", "light"],
    },
    ...PALETTE_IDS.map((id) => ({
      id: `theme-${id}`,
      label: `Theme: ${getPalette(id).label}`,
      description: getPalette(id).description,
      group: "theme" as const,
      keywords: [id, "theme", "palette"],
    })),
    {
      id: "audience-cycle",
      label: "Cycle audience",
      description: "Switch to the next projection",
      group: "audience",
      keys: "a",
      keywords: ["audience", "projection", "view"],
    },
    {
      id: "filter-clear",
      label: "Clear verdict filter",
      description: "Remove the active status-bar category filter",
      group: "report",
      keywords: ["filter", "clear", "reset"],
    },
    {
      id: "quit",
      label: "Quit",
      description: "Exit the TUI and restore the terminal",
      group: "system",
      keys: "q",
      keywords: ["quit", "exit", "close"],
    },
  ]

  for (const audience of Object.keys(AUDIENCE_LABELS) as Audience[]) {
    commands.push({
      id: `audience-${audience}`,
      label: `Audience: ${AUDIENCE_LABELS[audience]}`,
      description: `Show the report for ${audience}`,
      group: "audience",
      keywords: [audience, "audience", "projection"],
    })
  }

  return commands
}

export function runCommand(id: string, ctx: CommandContext): boolean {
  if (id.startsWith("go-")) {
    const route = id.slice(3) as "findings" | "detail" | "limits" | "settings"
    ctx.navigate(route)
    return true
  }
  if (id.startsWith("theme-") && id !== "theme-picker" && id !== "theme-cycle") {
    ctx.setPalette(id.slice(6) as PaletteId)
    return true
  }
  if (id.startsWith("audience-") && id !== "audience-cycle") {
    ctx.setAudience(id.slice(9) as Audience)
    return true
  }
  switch (id) {
    case "command-palette":
      ctx.openCommandPalette()
      return true
    case "help":
      ctx.openHelp()
      return true
    case "settings-modal":
      ctx.openSettings()
      return true
    case "theme-picker":
      ctx.openTheme()
      return true
    case "theme-cycle":
      ctx.cyclePalette()
      return true
    case "audience-cycle":
      ctx.cycleAudience()
      return true
    case "filter-clear":
      ctx.clearCategoryFilter()
      return true
    case "quit":
      ctx.quit()
      return true
    default:
      return false
  }
}

export function filterCommands(commands: readonly Command[], query: string): Command[] {
  const q = query.trim().toLowerCase()
  if (q === "") return [...commands]
  return commands.filter((cmd) => {
    if (cmd.label.toLowerCase().includes(q)) return true
    if (cmd.description.toLowerCase().includes(q)) return true
    if (cmd.id.toLowerCase().includes(q)) return true
    return cmd.keywords?.some((k) => k.includes(q)) ?? false
  })
}
