/** Render a {@link Frame} to plain text (no escape codes). */
import type { Frame } from "../frame"

export interface TextOptions {
  /** Strip trailing whitespace on each line. Default true. */
  readonly trimTrailing?: boolean
  /** Drop trailing fully-blank lines. Default true. */
  readonly trimEmptyLines?: boolean
}

export function renderText(frame: Frame, options: TextOptions = {}): string {
  const trimTrailing = options.trimTrailing ?? true
  const trimEmptyLines = options.trimEmptyLines ?? true

  const lines: string[] = []
  for (const row of frame.cells) {
    let line = ""
    for (const cell of row) line += cell.char || " "
    if (trimTrailing) line = line.replace(/\s+$/u, "")
    lines.push(line)
  }

  if (trimEmptyLines) {
    while (lines.length > 0 && lines[lines.length - 1].length === 0) lines.pop()
  }

  return lines.join("\n")
}
