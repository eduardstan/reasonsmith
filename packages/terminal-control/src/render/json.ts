/** Render a {@link Frame} to a structured, JSON-serializable object. */
import type { Cell, Color, Frame } from "../frame"

export interface JSONCell {
  char: string
  fg?: Color
  bg?: Color
  bold?: true
  dim?: true
  italic?: true
  underline?: true
  inverse?: true
  strikethrough?: true
}

export interface JSONFrame {
  cols: number
  rows: number
  cursor: { x: number; y: number; visible: boolean }
  title?: string
  /** One string of compact cells per row. */
  rows_cells: JSONCell[][]
}

function compactCell(cell: Cell): JSONCell {
  const out: JSONCell = { char: cell.char }
  if (cell.fg.type !== "default") out.fg = cell.fg
  if (cell.bg.type !== "default") out.bg = cell.bg
  if (cell.bold) out.bold = true
  if (cell.dim) out.dim = true
  if (cell.italic) out.italic = true
  if (cell.underline) out.underline = true
  if (cell.inverse) out.inverse = true
  if (cell.strikethrough) out.strikethrough = true
  return out
}

export function toJSONFrame(frame: Frame): JSONFrame {
  return {
    cols: frame.cols,
    rows: frame.rows,
    cursor: { x: frame.cursor.x, y: frame.cursor.y, visible: frame.cursor.visible },
    ...(frame.title !== undefined ? { title: frame.title } : {}),
    rows_cells: frame.cells.map((row) => row.map(compactCell)),
  }
}

export function renderJSON(frame: Frame, pretty = true): string {
  return JSON.stringify(toJSONFrame(frame), null, pretty ? 2 : undefined)
}
