/**
 * Render a {@link Frame} to a PNG by rasterizing the SVG output. Requires the
 * optional `@resvg/resvg-js` dependency, imported lazily so it never costs
 * startup time and the rest of the package works without it installed.
 */
import type { Frame } from "../frame"
import { renderSvg, type SvgOptions } from "./svg"

export interface PngOptions extends SvgOptions {
  /** Optional output width in pixels; height scales proportionally. */
  readonly width?: number
}

let resvgModule: Promise<unknown> | undefined

async function loadResvg(): Promise<any> {
  if (!resvgModule) {
    resvgModule = import("@resvg/resvg-js").catch((cause) => {
      throw new Error(
        "PNG rendering requires the optional dependency '@resvg/resvg-js'. Install it to capture PNG frames.",
        { cause: cause as Error },
      )
    })
  }
  return resvgModule
}

export async function renderPng(frame: Frame, options: PngOptions = {}): Promise<Uint8Array> {
  const svg = renderSvg(frame, options)
  const { Resvg } = await loadResvg()
  const resvg = new Resvg(svg, {
    fitTo: options.width ? { mode: "width", value: options.width } : { mode: "original" },
    font: { loadSystemFonts: true },
  })
  const rendered = resvg.render()
  return rendered.asPng()
}
