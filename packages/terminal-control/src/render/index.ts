/** Renderer dispatch — turn a {@link Frame} into any supported output format. */
import type { Frame } from "../frame"
import { renderText, type TextOptions } from "./text"
import { renderAnsi, type AnsiOptions } from "./ansi"
import { renderJSON, toJSONFrame, type JSONFrame } from "./json"
import { renderSvg, svgLayers, svgGeometry, type SvgOptions } from "./svg"
import { renderPng, type PngOptions } from "./png"
import {
  renderAnimatedSvg,
  renderPngSequence,
  exportVideo,
  ffmpegAvailable,
  type AnimatedSvgOptions,
  type PngFrame,
  type VideoFormat,
  type ExportVideoOptions,
  type ExportVideoResult,
} from "./video"

export {
  renderText,
  renderAnsi,
  renderJSON,
  toJSONFrame,
  renderSvg,
  svgLayers,
  svgGeometry,
  renderPng,
  renderAnimatedSvg,
  renderPngSequence,
  exportVideo,
  ffmpegAvailable,
}
export type {
  TextOptions,
  AnsiOptions,
  JSONFrame,
  SvgOptions,
  PngOptions,
  AnimatedSvgOptions,
  PngFrame,
  VideoFormat,
  ExportVideoOptions,
  ExportVideoResult,
}

/** Text formats produce a string synchronously; `png` produces bytes asynchronously. */
export type TextFormat = "text" | "ansi" | "json" | "svg"
export type Format = TextFormat | "png"

/** Render to any of the synchronous (text-like) formats. */
export function renderString(frame: Frame, format: TextFormat, options?: SvgOptions): string {
  switch (format) {
    case "text":
      return renderText(frame, options as TextOptions)
    case "ansi":
      return renderAnsi(frame, options as AnsiOptions)
    case "json":
      return renderJSON(frame)
    case "svg":
      return renderSvg(frame, options)
  }
}

/** Whether a format yields binary (`png`) vs a string. */
export function isBinaryFormat(format: Format): format is "png" {
  return format === "png"
}
