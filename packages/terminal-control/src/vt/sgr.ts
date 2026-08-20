/**
 * SGR (Select Graphic Rendition) — applies `CSI ... m` parameters to a mutable
 * attribute state. Supports the standard 16 colors, bright colors, 256-color
 * (`38;5;n` / `48;5;n`), truecolor (`38;2;r;g;b` / `48;2;r;g;b`) and text styles.
 */
import type { Color } from "../frame"
import { DEFAULT_COLOR } from "../frame"

/** Mutable mirror of {@link Attributes} used while applying SGR sequences. */
export interface MutableAttributes {
  fg: Color
  bg: Color
  bold: boolean
  dim: boolean
  italic: boolean
  underline: boolean
  inverse: boolean
  strikethrough: boolean
}

export function defaultMutableAttributes(): MutableAttributes {
  return {
    fg: DEFAULT_COLOR,
    bg: DEFAULT_COLOR,
    bold: false,
    dim: false,
    italic: false,
    underline: false,
    inverse: false,
    strikethrough: false,
  }
}

export function resetAttributes(attrs: MutableAttributes): void {
  attrs.fg = DEFAULT_COLOR
  attrs.bg = DEFAULT_COLOR
  attrs.bold = false
  attrs.dim = false
  attrs.italic = false
  attrs.underline = false
  attrs.inverse = false
  attrs.strikethrough = false
}

/**
 * Apply a list of SGR params to `attrs`. An empty list resets (per VT spec,
 * `CSI m` == `CSI 0 m`).
 */
export function applySGR(attrs: MutableAttributes, params: number[]): void {
  if (params.length === 0) {
    resetAttributes(attrs)
    return
  }

  for (let i = 0; i < params.length; i++) {
    const p = params[i]
    switch (true) {
      case p === 0:
        resetAttributes(attrs)
        break
      case p === 1:
        attrs.bold = true
        break
      case p === 2:
        attrs.dim = true
        break
      case p === 3:
        attrs.italic = true
        break
      case p === 4:
        attrs.underline = true
        break
      case p === 7:
        attrs.inverse = true
        break
      case p === 9:
        attrs.strikethrough = true
        break
      case p === 21 || p === 22:
        attrs.bold = false
        attrs.dim = false
        break
      case p === 23:
        attrs.italic = false
        break
      case p === 24:
        attrs.underline = false
        break
      case p === 27:
        attrs.inverse = false
        break
      case p === 29:
        attrs.strikethrough = false
        break
      // Foreground: standard (30–37) and bright (90–97).
      case p >= 30 && p <= 37:
        attrs.fg = { type: "indexed", index: p - 30 }
        break
      case p >= 90 && p <= 97:
        attrs.fg = { type: "indexed", index: p - 90 + 8 }
        break
      case p === 39:
        attrs.fg = DEFAULT_COLOR
        break
      // Background: standard (40–47) and bright (100–107).
      case p >= 40 && p <= 47:
        attrs.bg = { type: "indexed", index: p - 40 }
        break
      case p >= 100 && p <= 107:
        attrs.bg = { type: "indexed", index: p - 100 + 8 }
        break
      case p === 49:
        attrs.bg = DEFAULT_COLOR
        break
      // Extended color: 38 (fg) / 48 (bg).
      case p === 38 || p === 48: {
        const role = p === 38 ? "fg" : "bg"
        const mode = params[i + 1]
        if (mode === 5) {
          const idx = params[i + 2]
          if (idx !== undefined) attrs[role] = { type: "indexed", index: clamp(idx, 0, 255) }
          i += 2
        } else if (mode === 2) {
          const r = params[i + 2]
          const g = params[i + 3]
          const b = params[i + 4]
          if (r !== undefined && g !== undefined && b !== undefined) {
            attrs[role] = { type: "rgb", r: clamp(r, 0, 255), g: clamp(g, 0, 255), b: clamp(b, 0, 255) }
          }
          i += 4
        }
        break
      }
      default:
        // Unknown/unsupported SGR — ignore.
        break
    }
  }
}

function clamp(n: number, lo: number, hi: number): number {
  return n < lo ? lo : n > hi ? hi : n
}
