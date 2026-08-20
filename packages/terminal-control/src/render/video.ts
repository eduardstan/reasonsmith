/**
 * Video export — turn a {@link RecordingData} timeline into watchable output.
 *
 * Three tiers, from zero-dependency to external-tool:
 *  - {@link renderAnimatedSvg}: a single self-contained animated SVG (no deps).
 *  - {@link renderPngSequence}: a sequence of PNG frames (needs `@resvg/resvg-js`).
 *  - {@link exportVideo}: an MP4/GIF assembled from PNG frames via the `ffmpeg`
 *    binary if it is available on PATH.
 */
import type { RecordingData } from "../recording"
import { sampleFrames, duration, type SampleOptions } from "../recording"
import { svgLayers, escapeXml, type SvgOptions } from "./svg"
import { renderPng, type PngOptions } from "./png"

export interface AnimatedSvgOptions extends SvgOptions, SampleOptions {
  /** Playback speed multiplier (>1 = faster). Default 1. */
  readonly speed?: number
}

/**
 * Build a self-contained animated SVG that cycles through the recorded frames.
 * Each frame is a layer toggled with a `step-end` CSS animation, so playback is
 * crisp and the file plays in any modern browser with no dependencies.
 */
export function renderAnimatedSvg(rec: RecordingData, options: AnimatedSvgOptions = {}): string {
  const speed = options.speed && options.speed > 0 ? options.speed : 1
  const frames = sampleFrames(rec, { fps: options.fps ?? 8, maxFrames: options.maxFrames ?? 240, ...options })
  const total = Math.max(1, duration(rec)) / speed / 1000 // seconds

  if (frames.length === 0) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>`
  }

  const geom = svgLayers(frames[0].frame, options)
  const { width, height, fontFamily, fontSize, pageBg } = geom

  const styles: string[] = []
  const groups: string[] = []
  const n = frames.length

  for (let i = 0; i < n; i++) {
    const { rects, texts } = svgLayers(frames[i].frame, options)
    const p0 = ((i / n) * 100).toFixed(3)
    const p1 = (((i + 1) / n) * 100).toFixed(3)
    // step-end holds each value until the next stop: 0 before p0, 1 from p0, 0 from p1.
    styles.push(
      `@keyframes tcf${i}{0%{opacity:0}${p0}%{opacity:1}${p1}%{opacity:0}100%{opacity:0}}` +
        `.tcf${i}{opacity:0;animation:tcf${i} ${total.toFixed(3)}s step-end infinite}`,
    )
    groups.push(`<g class="tcf${i}"><g>${rects.join("")}</g><g>${texts.join("")}</g></g>`)
  }

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="${fontFamily}" font-size="${fontSize}">`,
    `<style>${styles.join("")}</style>`,
    `<rect width="100%" height="100%" fill="${pageBg}"/>`,
    groups.join(""),
    `<title>${escapeXml(rec.title ?? [rec.command, ...rec.args].join(" ").trim())}</title>`,
    `</svg>`,
  ].join("\n")
}

export interface PngFrame {
  readonly time: number
  readonly png: Uint8Array
}

/** Render the recording to a sequence of PNG frames (one per sampled moment). */
export async function renderPngSequence(
  rec: RecordingData,
  options: PngOptions & SampleOptions = {},
): Promise<PngFrame[]> {
  const sampled = sampleFrames(rec, { fps: options.fps ?? 8, maxFrames: options.maxFrames ?? 240, ...options })
  const out: PngFrame[] = []
  for (const { time, frame } of sampled) {
    out.push({ time, png: await renderPng(frame, options) })
  }
  return out
}

export type VideoFormat = "mp4" | "gif"

export interface ExportVideoOptions extends PngOptions, SampleOptions {
  readonly format?: VideoFormat
  /** Absolute path for the output file. */
  readonly outPath: string
  /** Playback speed multiplier (>1 = faster). Default 1. */
  readonly speed?: number
}

export interface ExportVideoResult {
  readonly path: string
  readonly format: VideoFormat
  readonly frames: number
  readonly fps: number
}

/** True if the `ffmpeg` binary is available on PATH. */
export function ffmpegAvailable(): boolean {
  return Bun.which("ffmpeg") !== null
}

/**
 * Assemble the recording into an MP4 or GIF using `ffmpeg`. Renders PNG frames,
 * pipes them to ffmpeg via the image2pipe demuxer. Throws a clear error if
 * ffmpeg or `@resvg/resvg-js` is unavailable.
 */
export async function exportVideo(rec: RecordingData, options: ExportVideoOptions): Promise<ExportVideoResult> {
  if (!ffmpegAvailable()) {
    throw new Error(
      "Video export requires the 'ffmpeg' binary on PATH. Use format 'svganim' for a dependency-free alternative.",
    )
  }
  const format = options.format ?? "mp4"
  const fps = Math.max(1, options.fps ?? 8)
  const speed = options.speed && options.speed > 0 ? options.speed : 1
  const effectiveFps = fps * speed

  const sequence = await renderPngSequence(rec, { ...options, fps })
  if (sequence.length === 0) throw new Error("Recording has no frames to export.")

  const args =
    format === "gif"
      ? [
          "-y",
          "-f",
          "image2pipe",
          "-framerate",
          String(effectiveFps),
          "-i",
          "-",
          "-vf",
          "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
          options.outPath,
        ]
      : [
          "-y",
          "-f",
          "image2pipe",
          "-framerate",
          String(effectiveFps),
          "-i",
          "-",
          "-c:v",
          "libx264",
          "-pix_fmt",
          "yuv420p",
          // h264 requires even dimensions.
          "-vf",
          "pad=ceil(iw/2)*2:ceil(ih/2)*2",
          options.outPath,
        ]

  const proc = Bun.spawn(["ffmpeg", ...args], { stdin: "pipe", stdout: "ignore", stderr: "pipe" })
  const writer = proc.stdin
  for (const frame of sequence) {
    writer.write(frame.png)
  }
  await writer.end()
  const code = await proc.exited
  if (code !== 0) {
    const stderr = await new Response(proc.stderr).text()
    throw new Error(`ffmpeg exited with code ${code}: ${stderr.slice(-500)}`)
  }

  return { path: options.outPath, format, frames: sequence.length, fps: effectiveFps }
}
