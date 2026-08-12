/**
 * Frame — the immutable, rendered screen state captured from a terminal stream.
 *
 * A Frame is a 2D grid of styled {@link Cell}s plus cursor and title metadata.
 * It is what {@link Screen.snapshot} produces and what every renderer consumes.
 */

/** A terminal color. `default` means "use the renderer's default fg/bg". */
export type Color =
  | { readonly type: "default" }
  /** Palette index 0–255 (0–15 = the 16 ANSI colors, 16–255 = the 256-color cube/grayscale). */
  | { readonly type: "indexed"; readonly index: number }
  /** 24-bit truecolor. */
  | { readonly type: "rgb"; readonly r: number; readonly g: number; readonly b: number }

export const DEFAULT_COLOR: Color = { type: "default" }

/** Visual attributes applied to a cell. */
export interface Attributes {
  readonly fg: Color
  readonly bg: Color
  readonly bold: boolean
  readonly dim: boolean
  readonly italic: boolean
  readonly underline: boolean
  readonly inverse: boolean
  readonly strikethrough: boolean
}

export const DEFAULT_ATTRIBUTES: Attributes = {
  fg: DEFAULT_COLOR,
  bg: DEFAULT_COLOR,
  bold: false,
  dim: false,
  italic: false,
  underline: false,
  inverse: false,
  strikethrough: false,
}

/** A single character cell on the grid. */
export interface Cell extends Attributes {
  /** Exactly one rendered character (may be a wide grapheme); empty string is treated as a space. */
  readonly char: string
}

export const BLANK_CELL: Cell = { char: " ", ...DEFAULT_ATTRIBUTES }

export interface Cursor {
  readonly x: number
  readonly y: number
  readonly visible: boolean
}

export interface Frame {
  readonly cols: number
  readonly rows: number
  readonly cursor: Cursor
  /** `rows` arrays of `cols` cells each. */
  readonly cells: ReadonlyArray<ReadonlyArray<Cell>>
  /** Window title set via OSC 0/2, if any. */
  readonly title?: string
}

export function blankCell(): Cell {
  return BLANK_CELL
}

export function emptyFrame(cols: number, rows: number): Frame {
  const cells: Cell[][] = []
  for (let y = 0; y < rows; y++) {
    const row: Cell[] = []
    for (let x = 0; x < cols; x++) row.push(BLANK_CELL)
    cells.push(row)
  }
  return { cols, rows, cursor: { x: 0, y: 0, visible: true }, cells }
}

export function colorsEqual(a: Color, b: Color): boolean {
  if (a.type !== b.type) return false
  if (a.type === "indexed" && b.type === "indexed") return a.index === b.index
  if (a.type === "rgb" && b.type === "rgb") return a.r === b.r && a.g === b.g && a.b === b.b
  return true
}

export function attributesEqual(a: Attributes, b: Attributes): boolean {
  return (
    a.bold === b.bold &&
    a.dim === b.dim &&
    a.italic === b.italic &&
    a.underline === b.underline &&
    a.inverse === b.inverse &&
    a.strikethrough === b.strikethrough &&
    colorsEqual(a.fg, b.fg) &&
    colorsEqual(a.bg, b.bg)
  )
}

/** Coordinates of cells that differ between two same-sized frames. */
export function diffFrames(a: Frame, b: Frame): Array<{ x: number; y: number }> {
  const diffs: Array<{ x: number; y: number }> = []
  const rows = Math.min(a.rows, b.rows)
  const cols = Math.min(a.cols, b.cols)
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const ca = a.cells[y]![x]!
      const cb = b.cells[y]![x]!
      if (ca.char !== cb.char || !attributesEqual(ca, cb)) diffs.push({ x, y })
    }
  }
  return diffs
}
