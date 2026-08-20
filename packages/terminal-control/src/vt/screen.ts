/**
 * Screen — a terminal emulator's display buffer. It implements {@link ParserSink},
 * consuming events from {@link Parser} and maintaining a grid of cells, the cursor,
 * the scroll region, text attributes, an alternate screen buffer, and the window
 * title. {@link Screen.snapshot} produces an immutable {@link Frame}.
 */
import type { Cell, Cursor, Frame } from "../frame"
import { Parser, type ParserSink } from "./parser"
import { applySGR, defaultMutableAttributes, resetAttributes, type MutableAttributes } from "./sgr"

interface MCell extends MutableAttributes {
  char: string
}

function blankMCell(): MCell {
  return { char: " ", ...defaultMutableAttributes() }
}

function makeGrid(cols: number, rows: number): MCell[][] {
  const grid: MCell[][] = []
  for (let y = 0; y < rows; y++) {
    const row: MCell[] = []
    for (let x = 0; x < cols; x++) row.push(blankMCell())
    grid.push(row)
  }
  return grid
}

const BS = 0x08
const HT = 0x09
const LF = 0x0a
const VT = 0x0b
const FF = 0x0c
const CR = 0x0d

export class Screen implements ParserSink {
  cols: number
  rows: number

  private grid: MCell[][]
  /** Alternate screen buffer (allocated lazily on first switch). */
  private altGrid: MCell[][] | null = null
  private inAlt = false

  private cursorX = 0
  private cursorY = 0
  private cursorVisible = true
  private pendingWrap = false

  private savedCursor: { x: number; y: number } | null = null

  private scrollTop: number
  private scrollBottom: number

  private attrs: MutableAttributes = defaultMutableAttributes()
  private title: string | undefined

  private readonly parser: Parser

  constructor(cols: number, rows: number) {
    this.cols = Math.max(1, cols)
    this.rows = Math.max(1, rows)
    this.grid = makeGrid(this.cols, this.rows)
    this.scrollTop = 0
    this.scrollBottom = this.rows - 1
    this.parser = new Parser(this)
  }

  /** Feed raw terminal output. */
  write(data: string): void {
    this.parser.write(data)
  }

  resize(cols: number, rows: number): void {
    cols = Math.max(1, cols)
    rows = Math.max(1, rows)
    this.grid = this.resizeGrid(this.grid, cols, rows)
    if (this.altGrid) this.altGrid = this.resizeGrid(this.altGrid, cols, rows)
    this.cols = cols
    this.rows = rows
    this.scrollTop = 0
    this.scrollBottom = rows - 1
    this.cursorX = Math.min(this.cursorX, cols - 1)
    this.cursorY = Math.min(this.cursorY, rows - 1)
    this.pendingWrap = false
  }

  private resizeGrid(grid: MCell[][], cols: number, rows: number): MCell[][] {
    const next = makeGrid(cols, rows)
    const copyRows = Math.min(rows, grid.length)
    for (let y = 0; y < copyRows; y++) {
      const copyCols = Math.min(cols, grid[y].length)
      for (let x = 0; x < copyCols; x++) next[y][x] = grid[y][x]!
    }
    return next
  }

  /** Produce an immutable snapshot of the current visible screen. */
  snapshot(): Frame {
    const cells: Cell[][] = []
    for (let y = 0; y < this.rows; y++) {
      const row: Cell[] = []
      const src = this.grid[y]
      for (let x = 0; x < this.cols; x++) {
        const c = src[x]
        row.push({
          char: c.char,
          fg: c.fg,
          bg: c.bg,
          bold: c.bold,
          dim: c.dim,
          italic: c.italic,
          underline: c.underline,
          inverse: c.inverse,
          strikethrough: c.strikethrough,
        })
      }
      cells.push(row)
    }
    const cursor: Cursor = {
      x: Math.min(this.cursorX, this.cols - 1),
      y: Math.min(this.cursorY, this.rows - 1),
      visible: this.cursorVisible,
    }
    return { cols: this.cols, rows: this.rows, cursor, cells, title: this.title }
  }

  // --- ParserSink implementation ----------------------------------------

  print(text: string): void {
    for (const ch of text) {
      this.putChar(ch)
    }
  }

  private putChar(ch: string): void {
    if (this.pendingWrap) {
      this.cursorX = 0
      this.lineFeed()
      this.pendingWrap = false
    }
    const cell = this.grid[this.cursorY][this.cursorX]
    cell.char = ch === "" ? " " : ch
    this.copyAttrsInto(cell)
    if (this.cursorX >= this.cols - 1) {
      this.pendingWrap = true
    } else {
      this.cursorX++
    }
  }

  private copyAttrsInto(cell: MCell): void {
    cell.fg = this.attrs.fg
    cell.bg = this.attrs.bg
    cell.bold = this.attrs.bold
    cell.dim = this.attrs.dim
    cell.italic = this.attrs.italic
    cell.underline = this.attrs.underline
    cell.inverse = this.attrs.inverse
    cell.strikethrough = this.attrs.strikethrough
  }

  execute(byte: number): void {
    switch (byte) {
      case BS:
        this.pendingWrap = false
        if (this.cursorX > 0) this.cursorX--
        break
      case HT:
        this.tab()
        break
      case LF:
      case VT:
      case FF:
        this.pendingWrap = false
        this.lineFeed()
        break
      case CR:
        this.pendingWrap = false
        this.cursorX = 0
        break
      default:
        break
    }
  }

  private tab(): void {
    this.pendingWrap = false
    const next = Math.floor(this.cursorX / 8) * 8 + 8
    this.cursorX = Math.min(next, this.cols - 1)
  }

  private lineFeed(): void {
    if (this.cursorY === this.scrollBottom) {
      this.scrollUp(1)
    } else if (this.cursorY < this.rows - 1) {
      this.cursorY++
    }
  }

  private reverseLineFeed(): void {
    if (this.cursorY === this.scrollTop) {
      this.scrollDown(1)
    } else if (this.cursorY > 0) {
      this.cursorY--
    }
  }

  private scrollUp(n: number): void {
    for (let i = 0; i < n; i++) {
      const removed = this.grid.splice(this.scrollTop, 1)[0]
      this.clearRow(removed)
      this.grid.splice(this.scrollBottom, 0, removed)
    }
  }

  private scrollDown(n: number): void {
    for (let i = 0; i < n; i++) {
      const removed = this.grid.splice(this.scrollBottom, 1)[0]
      this.clearRow(removed)
      this.grid.splice(this.scrollTop, 0, removed)
    }
  }

  private clearRow(row: MCell[]): void {
    for (let x = 0; x < row.length; x++) row[x] = blankMCell()
  }

  escDispatch(intermediates: string, final: string): void {
    if (intermediates.length > 0) return // charset designators etc — ignore
    switch (final) {
      case "7": // DECSC — save cursor
        this.savedCursor = { x: this.cursorX, y: this.cursorY }
        break
      case "8": // DECRC — restore cursor
        if (this.savedCursor) {
          this.cursorX = this.savedCursor.x
          this.cursorY = this.savedCursor.y
        }
        break
      case "D": // IND — index (down, scroll if needed)
        this.pendingWrap = false
        this.lineFeed()
        break
      case "M": // RI — reverse index
        this.pendingWrap = false
        this.reverseLineFeed()
        break
      case "E": // NEL — next line
        this.pendingWrap = false
        this.cursorX = 0
        this.lineFeed()
        break
      case "c": // RIS — full reset
        this.fullReset()
        break
      default:
        break
    }
  }

  private fullReset(): void {
    this.grid = makeGrid(this.cols, this.rows)
    this.altGrid = null
    this.inAlt = false
    this.cursorX = 0
    this.cursorY = 0
    this.cursorVisible = true
    this.pendingWrap = false
    this.savedCursor = null
    this.scrollTop = 0
    this.scrollBottom = this.rows - 1
    resetAttributes(this.attrs)
    this.title = undefined
  }

  csiDispatch(params: number[], intermediates: string, final: string, isPrivate: boolean): void {
    if (isPrivate) {
      this.privateMode(params, final)
      return
    }
    // Default first param to 1 (treating 0 as 1) for movement-style commands.
    const p1 = (i = 0, def = 1) => {
      const v = params[i]
      return v === undefined || v === 0 ? def : v
    }
    // Raw param defaulting to 0 (for erase commands).
    const p0 = (i = 0, def = 0) => params[i] ?? def

    switch (final) {
      case "A": // CUU — up
        this.pendingWrap = false
        this.cursorY = Math.max(this.cursorY >= this.scrollTop ? this.scrollTop : 0, this.cursorY - p1())
        break
      case "B": // CUD — down
        this.pendingWrap = false
        this.cursorY = Math.min(this.rows - 1, this.cursorY + p1())
        break
      case "C": // CUF — forward
        this.pendingWrap = false
        this.cursorX = Math.min(this.cols - 1, this.cursorX + p1())
        break
      case "D": // CUB — back
        this.pendingWrap = false
        this.cursorX = Math.max(0, this.cursorX - p1())
        break
      case "E": // CNL — cursor next line
        this.pendingWrap = false
        this.cursorX = 0
        this.cursorY = Math.min(this.rows - 1, this.cursorY + p1())
        break
      case "F": // CPL — cursor previous line
        this.pendingWrap = false
        this.cursorX = 0
        this.cursorY = Math.max(0, this.cursorY - p1())
        break
      case "G": // CHA — column absolute
      case "`": // HPA
        this.pendingWrap = false
        this.cursorX = Math.min(this.cols - 1, Math.max(0, p1() - 1))
        break
      case "d": // VPA — line absolute
        this.pendingWrap = false
        this.cursorY = Math.min(this.rows - 1, Math.max(0, p1() - 1))
        break
      case "H": // CUP
      case "f": // HVP
        this.pendingWrap = false
        this.cursorY = Math.min(this.rows - 1, Math.max(0, p1(0) - 1))
        this.cursorX = Math.min(this.cols - 1, Math.max(0, p1(1) - 1))
        break
      case "J": // ED — erase in display
        this.eraseDisplay(p0())
        break
      case "K": // EL — erase in line
        this.eraseLine(p0())
        break
      case "L": // IL — insert lines
        this.insertLines(p1())
        break
      case "M": // DL — delete lines
        this.deleteLines(p1())
        break
      case "P": // DCH — delete chars
        this.deleteChars(p1())
        break
      case "@": // ICH — insert blanks
        this.insertChars(p1())
        break
      case "X": // ECH — erase chars
        this.eraseChars(p1())
        break
      case "S": // SU — scroll up
        this.scrollUp(p1())
        break
      case "T": // SD — scroll down
        this.scrollDown(p1())
        break
      case "r": // DECSTBM — set scroll region
        this.setScrollRegion(params)
        break
      case "m": // SGR
        applySGR(this.attrs, params.length === 1 && params[0] === 0 ? [] : params)
        break
      case "s": // save cursor (ANSI.SYS)
        this.savedCursor = { x: this.cursorX, y: this.cursorY }
        break
      case "u": // restore cursor (ANSI.SYS)
        if (this.savedCursor) {
          this.cursorX = this.savedCursor.x
          this.cursorY = this.savedCursor.y
        }
        break
      default:
        break
    }
    void intermediates
  }

  private setScrollRegion(params: number[]): void {
    const top = (params[0] ?? 1) - 1
    const bottom = (params[1] ?? this.rows) - 1
    if (top >= 0 && bottom < this.rows && top < bottom) {
      this.scrollTop = top
      this.scrollBottom = bottom
    } else {
      this.scrollTop = 0
      this.scrollBottom = this.rows - 1
    }
    this.cursorX = 0
    this.cursorY = this.scrollTop
    this.pendingWrap = false
  }

  private eraseDisplay(mode: number): void {
    this.pendingWrap = false
    if (mode === 0) {
      // cursor to end
      this.eraseLineRange(this.cursorY, this.cursorX, this.cols)
      for (let y = this.cursorY + 1; y < this.rows; y++) this.clearRow(this.grid[y])
    } else if (mode === 1) {
      // start to cursor
      for (let y = 0; y < this.cursorY; y++) this.clearRow(this.grid[y])
      this.eraseLineRange(this.cursorY, 0, this.cursorX + 1)
    } else {
      // entire display (2 and 3)
      for (let y = 0; y < this.rows; y++) this.clearRow(this.grid[y])
    }
  }

  private eraseLine(mode: number): void {
    this.pendingWrap = false
    if (mode === 0) this.eraseLineRange(this.cursorY, this.cursorX, this.cols)
    else if (mode === 1) this.eraseLineRange(this.cursorY, 0, this.cursorX + 1)
    else this.eraseLineRange(this.cursorY, 0, this.cols)
  }

  private eraseLineRange(y: number, from: number, to: number): void {
    const row = this.grid[y]
    if (!row) return
    for (let x = from; x < to && x < this.cols; x++) row[x] = blankMCell()
  }

  private eraseChars(n: number): void {
    this.pendingWrap = false
    this.eraseLineRange(this.cursorY, this.cursorX, this.cursorX + n)
  }

  private insertChars(n: number): void {
    this.pendingWrap = false
    const row = this.grid[this.cursorY]
    for (let i = 0; i < n; i++) {
      row.splice(this.cols - 1, 1)
      row.splice(this.cursorX, 0, blankMCell())
    }
  }

  private deleteChars(n: number): void {
    this.pendingWrap = false
    const row = this.grid[this.cursorY]
    for (let i = 0; i < n; i++) {
      row.splice(this.cursorX, 1)
      row.push(blankMCell())
    }
  }

  private insertLines(n: number): void {
    if (this.cursorY < this.scrollTop || this.cursorY > this.scrollBottom) return
    this.pendingWrap = false
    for (let i = 0; i < n; i++) {
      this.grid.splice(this.scrollBottom, 1)
      this.grid.splice(this.cursorY, 0, makeGrid(this.cols, 1)[0])
    }
  }

  private deleteLines(n: number): void {
    if (this.cursorY < this.scrollTop || this.cursorY > this.scrollBottom) return
    this.pendingWrap = false
    for (let i = 0; i < n; i++) {
      this.grid.splice(this.cursorY, 1)
      this.grid.splice(this.scrollBottom, 0, makeGrid(this.cols, 1)[0])
    }
  }

  private privateMode(params: number[], final: string): void {
    const set = final === "h"
    for (const code of params) {
      switch (code) {
        case 25: // DECTCEM — cursor visibility
          this.cursorVisible = set
          break
        case 47:
        case 1047:
        case 1049:
          this.switchAltBuffer(set)
          break
        default:
          break
      }
    }
  }

  private switchAltBuffer(toAlt: boolean): void {
    if (toAlt && !this.inAlt) {
      this.savedCursor = { x: this.cursorX, y: this.cursorY }
      if (!this.altGrid) this.altGrid = makeGrid(this.cols, this.rows)
      const primary = this.grid
      this.grid = this.altGrid
      this.altGrid = primary
      this.inAlt = true
      // Clear the alt screen on entry.
      for (let y = 0; y < this.rows; y++) this.clearRow(this.grid[y])
      this.cursorX = 0
      this.cursorY = 0
      this.pendingWrap = false
    } else if (!toAlt && this.inAlt) {
      const alt = this.grid
      this.grid = this.altGrid!
      this.altGrid = alt
      this.inAlt = false
      if (this.savedCursor) {
        this.cursorX = this.savedCursor.x
        this.cursorY = this.savedCursor.y
      }
      this.pendingWrap = false
    }
  }

  oscDispatch(data: string): void {
    // OSC 0 (icon+title) and OSC 2 (title): "0;text" / "2;text".
    const sep = data.indexOf(";")
    if (sep === -1) return
    const code = data.slice(0, sep)
    if (code === "0" || code === "2") {
      this.title = data.slice(sep + 1)
    }
  }
}
