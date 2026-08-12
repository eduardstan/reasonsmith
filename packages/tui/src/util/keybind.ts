/**
 * Keybind utilities — OpenTUI `ParsedKey` shape, nikcli/opencode compatible.
 */

import type { KeyEvent, ParsedKey } from "@opentui/core"

export namespace Keybind {
  export type Info = Pick<ParsedKey, "name" | "ctrl" | "meta" | "shift" | "super"> & {
    leader: boolean
  }

  export function match(a: Info | undefined, b: Info): boolean {
    if (!a) return false
    return (
      a.name === b.name &&
      a.ctrl === b.ctrl &&
      a.meta === b.meta &&
      a.shift === b.shift &&
      (a.super ?? false) === (b.super ?? false) &&
      a.leader === b.leader
    )
  }

  export function fromParsedKey(key: ParsedKey | KeyEvent, leader = false): Info {
    return {
      name: key.name,
      ctrl: key.ctrl,
      meta: key.meta,
      shift: key.shift,
      super: key.super ?? false,
      leader,
    }
  }

  export function toString(info: Info | undefined): string {
    if (!info) return ""
    const parts: string[] = []
    if (info.ctrl) parts.push("ctrl")
    if (info.meta) parts.push("alt")
    if (info.super) parts.push("super")
    if (info.shift) parts.push("shift")
    if (info.name) {
      if (info.name === "delete") parts.push("del")
      else parts.push(info.name)
    }
    let result = parts.join("+")
    if (info.leader) result = result ? `leader ${result}` : "leader"
    return result
  }

  export function parse(key: string): Info[] {
    if (key === "none") return []
    return key.split(",").map((combo) => {
      const normalized = combo.replace(/leader/g, "leader+")
      const parts = normalized.toLowerCase().trim().split("+")
      const info: Info = {
        ctrl: false,
        meta: false,
        shift: false,
        leader: false,
        name: "",
      }
      for (const part of parts) {
        switch (part) {
          case "ctrl":
            info.ctrl = true
            break
          case "alt":
          case "meta":
          case "option":
            info.meta = true
            break
          case "super":
            info.super = true
            break
          case "shift":
            info.shift = true
            break
          case "leader":
            info.leader = true
            break
          case "esc":
            info.name = "escape"
            break
          default:
            info.name = part
            break
        }
      }
      return info
    })
  }

  /** Ignore key-repeat events except when explicitly wanted. */
  export function isRepeat(event: KeyEvent): boolean {
    return event.repeated === true || event.eventType === "repeat"
  }
}
