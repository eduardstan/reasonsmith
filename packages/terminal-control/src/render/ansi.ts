/**
 * Render a {@link Frame} back to an ANSI string, re-emitting SGR codes so the
 * captured screen can be printed to a real terminal with its original styling.
 */
import type { Attributes, Cell, Color, Frame } from "../frame"
import { DEFAULT_ATTRIBUTES, attributesEqual } from "../frame"

function colorSGR(color: Color, role: "fg" | "bg"): number[] {
  const base = role === "fg" ? 38 : 48
  switch (color.type) {
    case "default":
      return [role === "fg" ? 39 : 49]
    case "indexed":
      if (color.index < 8) return [(role === "fg" ? 30 : 40) + color.index]
      if (color.index < 16) return [(role === "fg" ? 90 : 100) + (color.index - 8)]
      return [base, 5, color.index]
    case "rgb":
      return [base, 2, color.r, color.g, color.b]
  }
}

function sgrFor(attrs: Attributes): string {
  const params: number[] = [0]
  if (attrs.bold) params.push(1)
  if (attrs.dim) params.push(2)
  if (attrs.italic) params.push(3)
  if (attrs.underline) params.push(4)
  if (attrs.inverse) params.push(7)
  if (attrs.strikethrough) params.push(9)
  if (attrs.fg.type !== "default") params.push(...colorSGR(attrs.fg, "fg"))
  if (attrs.bg.type !== "default") params.push(...colorSGR(attrs.bg, "bg"))
  return `\x1b[${params.join(";")}m`
}

export interface AnsiOptions {
  /** Append a reset (`\x1b[0m`) after each line. Default true. */
  readonly resetEachLine?: boolean
  /** Drop trailing fully-blank lines. Default true. */
  readonly trimEmptyLines?: boolean
}

export function renderAnsi(frame: Frame, options: AnsiOptions = {}): string {
  const resetEachLine = options.resetEachLine ?? true
  const trimEmptyLines = options.trimEmptyLines ?? true

  const lines: string[] = []
  for (const row of frame.cells) {
    let line = ""
    let current: Attributes = DEFAULT_ATTRIBUTES
    let dirty = false
    for (const cell of row as Cell[]) {
      if (!attributesEqual(cell, current)) {
        line += sgrFor(cell)
        current = cell
        dirty = dirty || !attributesEqual(cell, DEFAULT_ATTRIBUTES)
      }
      line += cell.char || " "
    }
    if (dirty || resetEachLine) line += "\x1b[0m"
    lines.push(line)
  }

  if (trimEmptyLines) {
    while (lines.length > 0) {
      const lastLine = lines[lines.length - 1]
      if (lastLine !== "" && lastLine !== "\x1b[0m") break
      lines.pop()
    }
  }

  return lines.join("\n")
}
