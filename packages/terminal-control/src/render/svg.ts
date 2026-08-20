/**
 * Render a {@link Frame} to a self-contained SVG using a monospace grid.
 * Pure string generation — no dependencies. Background spans are merged into
 * rects and same-style character runs are merged into `<text>` elements.
 */
import type { Attributes, Cell, Frame } from "../frame"
import { resolveColor, rgbToHex, DEFAULT_RESOLVE, type ResolveOptions } from "../vt/color"

export interface SvgOptions {
  readonly fontFamily?: string
  readonly fontSize?: number
  readonly cellWidth?: number
  readonly cellHeight?: number
  readonly padding?: number
  readonly resolve?: ResolveOptions
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
}

function effectiveColors(cell: Cell, resolve: ResolveOptions) {
  let fg = resolveColor(cell.fg, "fg", resolve)
  let bg = resolveColor(cell.bg, "bg", resolve)
  if (cell.inverse) {
    const tmp = fg
    fg = bg
    bg = tmp
  }
  return { fg, bg }
}

function styleAttrs(cell: Attributes): string {
  const parts: string[] = []
  if (cell.bold) parts.push('font-weight="bold"')
  if (cell.italic) parts.push('font-style="italic"')
  const deco: string[] = []
  if (cell.underline) deco.push("underline")
  if (cell.strikethrough) deco.push("line-through")
  if (deco.length) parts.push(`text-decoration="${deco.join(" ")}"`)
  return parts.join(" ")
}

export interface SvgGeometry {
  readonly fontFamily: string
  readonly fontSize: number
  readonly cellW: number
  readonly cellH: number
  readonly padding: number
  readonly width: number
  readonly height: number
  readonly pageBg: string
}

export interface SvgLayers extends SvgGeometry {
  /** Background `<rect>` elements (excluding the page background). */
  readonly rects: string[]
  /** Foreground `<text>` elements. */
  readonly texts: string[]
}

export function svgGeometry(frame: Frame, options: SvgOptions = {}): SvgGeometry {
  const fontFamily =
    options.fontFamily ?? "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
  const fontSize = options.fontSize ?? 14
  const cellW = options.cellWidth ?? fontSize * 0.6
  const cellH = options.cellHeight ?? fontSize * 1.2
  const padding = options.padding ?? 8
  const resolve = options.resolve ?? DEFAULT_RESOLVE
  return {
    fontFamily,
    fontSize,
    cellW,
    cellH,
    padding,
    width: Math.ceil(frame.cols * cellW + padding * 2),
    height: Math.ceil(frame.rows * cellH + padding * 2),
    pageBg: rgbToHex(resolve.defaultBg),
  }
}

/** Build the background-rect and foreground-text layers for a single frame. */
export function svgLayers(frame: Frame, options: SvgOptions = {}): SvgLayers {
  const geom = svgGeometry(frame, options)
  const resolve = options.resolve ?? DEFAULT_RESOLVE
  const { cellW, cellH, padding, pageBg } = geom

  const rects: string[] = []
  const texts: string[] = []

  for (let y = 0; y < frame.rows; y++) {
    const row = frame.cells[y] as Cell[]
    // Background rects — merge horizontally adjacent cells with identical bg.
    let runStart = 0
    let runBg = effectiveColors(row[0], resolve).bg
    const flushRect = (endX: number) => {
      const hex = rgbToHex(runBg)
      if (hex !== pageBg) {
        const x = padding + runStart * cellW
        const w = (endX - runStart) * cellW
        rects.push(
          `<rect x="${x.toFixed(2)}" y="${(padding + y * cellH).toFixed(2)}" width="${w.toFixed(2)}" height="${cellH.toFixed(2)}" fill="${hex}"/>`,
        )
      }
    }
    for (let x = 1; x < frame.cols; x++) {
      const bg = effectiveColors(row[x], resolve).bg
      if (rgbToHex(bg) !== rgbToHex(runBg)) {
        flushRect(x)
        runStart = x
        runBg = bg
      }
    }
    flushRect(frame.cols)

    // Text runs — merge adjacent cells with identical fg + style.
    const baseline = padding + y * cellH + cellH * 0.78
    let tx = 0
    while (tx < frame.cols) {
      const cell = row[tx]
      const ch = cell.char || " "
      if (ch === " " && !cell.underline && !cell.strikethrough) {
        tx++
        continue
      }
      const { fg } = effectiveColors(cell, resolve)
      const style = styleAttrs(cell)
      let run = ""
      const startX = tx
      while (tx < frame.cols) {
        const c = row[tx]
        const cc = effectiveColors(c, resolve)
        if (rgbToHex(cc.fg) !== rgbToHex(fg) || styleAttrs(c) !== style) break
        run += c.char || " "
        tx++
      }
      const trimmed = run.replace(/\s+$/u, "")
      if (trimmed.length === 0) continue
      const x = padding + startX * cellW
      texts.push(
        `<text x="${x.toFixed(2)}" y="${baseline.toFixed(2)}" fill="${rgbToHex(fg)}" ${style} xml:space="preserve">${escapeXml(run)}</text>`,
      )
    }
  }

  return { ...geom, rects, texts }
}

export function renderSvg(frame: Frame, options: SvgOptions = {}): string {
  const { width, height, fontFamily, fontSize, pageBg, rects, texts } = svgLayers(frame, options)
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="${fontFamily}" font-size="${fontSize}">`,
    `<rect width="100%" height="100%" fill="${pageBg}"/>`,
    `<g>${rects.join("")}</g>`,
    `<g>${texts.join("")}</g>`,
    `</svg>`,
  ].join("\n")
}

export { escapeXml }
