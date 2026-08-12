/**
 * Color palette resolution: turns a {@link Color} into concrete RGB for rendering,
 * and provides the canonical xterm 256-color palette.
 */
import type { Color } from "../frame"

export interface RGB {
  readonly r: number
  readonly g: number
  readonly b: number
}

/** The 16 standard ANSI colors (xterm defaults). Indices 0–15. */
const ANSI_16: RGB[] = [
  { r: 0, g: 0, b: 0 }, // 0 black
  { r: 205, g: 0, b: 0 }, // 1 red
  { r: 0, g: 205, b: 0 }, // 2 green
  { r: 205, g: 205, b: 0 }, // 3 yellow
  { r: 0, g: 0, b: 238 }, // 4 blue
  { r: 205, g: 0, b: 205 }, // 5 magenta
  { r: 0, g: 205, b: 205 }, // 6 cyan
  { r: 229, g: 229, b: 229 }, // 7 white
  { r: 127, g: 127, b: 127 }, // 8 bright black
  { r: 255, g: 0, b: 0 }, // 9 bright red
  { r: 0, g: 255, b: 0 }, // 10 bright green
  { r: 255, g: 255, b: 0 }, // 11 bright yellow
  { r: 92, g: 92, b: 255 }, // 12 bright blue
  { r: 255, g: 0, b: 255 }, // 13 bright magenta
  { r: 0, g: 255, b: 255 }, // 14 bright cyan
  { r: 255, g: 255, b: 255 }, // 15 bright white
]

const CUBE_STEPS = [0, 95, 135, 175, 215, 255]

/** Resolve an xterm palette index (0–255) to RGB. */
export function indexedToRGB(index: number): RGB {
  if (index < 16) return ANSI_16[index] ?? ANSI_16[0]!
  if (index < 232) {
    const i = index - 16
    const r = CUBE_STEPS[Math.floor(i / 36) % 6]!
    const g = CUBE_STEPS[Math.floor(i / 6) % 6]!
    const b = CUBE_STEPS[i % 6]!
    return { r, g, b }
  }
  // 232–255: 24-step grayscale ramp.
  const level = 8 + (index - 232) * 10
  return { r: level, g: level, b: level }
}

export interface ResolveOptions {
  readonly defaultFg: RGB
  readonly defaultBg: RGB
}

export const DEFAULT_RESOLVE: ResolveOptions = {
  defaultFg: { r: 229, g: 229, b: 229 },
  defaultBg: { r: 0, g: 0, b: 0 },
}

/** Resolve a {@link Color} to concrete RGB, honoring `default` fg/bg. */
export function resolveColor(color: Color, role: "fg" | "bg", opts: ResolveOptions = DEFAULT_RESOLVE): RGB {
  switch (color.type) {
    case "default":
      return role === "fg" ? opts.defaultFg : opts.defaultBg
    case "indexed":
      return indexedToRGB(color.index)
    case "rgb":
      return { r: color.r, g: color.g, b: color.b }
  }
}

export function rgbToHex({ r, g, b }: RGB): string {
  const h = (n: number) => n.toString(16).padStart(2, "0")
  return `#${h(r)}${h(g)}${h(b)}`
}
