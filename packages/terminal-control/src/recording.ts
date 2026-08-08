/**
 * Recording — a timeline of timestamped terminal output plus named markers.
 *
 * A {@link Recorder} captures the raw output stream of a {@link Session} as it
 * arrives. The resulting {@link RecordingData} is a versioned, serializable
 * document that can be replayed to reconstruct the screen at any moment
 * ({@link frameAt}), sampled into a sequence of frames ({@link sampleFrames}),
 * clipped between markers ({@link clipBetweenMarkers}), or exported to the
 * standard asciinema v2 cast format ({@link toAsciicast}).
 *
 * Times are milliseconds relative to the start of the recording.
 */
import type { Frame } from "./frame"
import { Screen } from "./vt/screen"

export const RECORDING_VERSION = 1 as const

export interface RecordingMarker {
  readonly time: number
  readonly name: string
}

export interface RecordingEvent {
  readonly time: number
  /** Raw terminal output chunk (still containing ANSI/VT control sequences). */
  readonly data: string
}

export interface RecordingMeta {
  readonly width: number
  readonly height: number
  readonly command: string
  readonly args: ReadonlyArray<string>
  readonly title?: string
}

export interface RecordingData extends RecordingMeta {
  readonly version: typeof RECORDING_VERSION
  /** Epoch milliseconds when recording started. */
  readonly startedAt: number
  /** Total duration in milliseconds. */
  readonly duration: number
  readonly events: ReadonlyArray<RecordingEvent>
  readonly markers: ReadonlyArray<RecordingMarker>
}

export class Recorder {
  private readonly events: RecordingEvent[] = []
  private readonly markers: RecordingMarker[] = []
  private readonly startedAt: number
  private readonly origin: number
  private stopped = false
  private stoppedAt = 0

  constructor(private readonly meta: RecordingMeta) {
    this.startedAt = Date.now()
    this.origin = this.startedAt
  }

  get active(): boolean {
    return !this.stopped
  }

  get eventCount(): number {
    return this.events.length
  }

  get markerCount(): number {
    return this.markers.length
  }

  /** Record a raw output chunk. No-op once stopped. */
  record(data: string): void {
    if (this.stopped || data.length === 0) return
    this.events.push({ time: Date.now() - this.origin, data })
  }

  /** Add a named marker at the current time. Returns the marker. No-op once stopped. */
  marker(name: string): RecordingMarker | undefined {
    if (this.stopped) return undefined
    const m = { time: Date.now() - this.origin, name }
    this.markers.push(m)
    return m
  }

  stop(): RecordingData {
    if (!this.stopped) {
      this.stopped = true
      this.stoppedAt = Date.now()
    }
    return this.data()
  }

  /** Snapshot the recording so far (does not stop it). */
  data(): RecordingData {
    const end = this.stopped ? this.stoppedAt : Date.now()
    return {
      version: RECORDING_VERSION,
      width: this.meta.width,
      height: this.meta.height,
      command: this.meta.command,
      args: this.meta.args,
      ...(this.meta.title !== undefined ? { title: this.meta.title } : {}),
      startedAt: this.startedAt,
      duration: end - this.origin,
      events: this.events.slice(),
      markers: this.markers.slice(),
    }
  }
}

/** Total duration of a recording in milliseconds. */
export function duration(rec: RecordingData): number {
  if (rec.duration > 0) return rec.duration
  const last = rec.events[rec.events.length - 1]
  return last ? last.time : 0
}

/** Replay every event up to and including `timeMs` and return the resulting frame. */
export function frameAt(rec: RecordingData, timeMs: number): Frame {
  const screen = new Screen(rec.width, rec.height)
  for (const event of rec.events) {
    if (event.time > timeMs) break
    screen.write(event.data)
  }
  return screen.snapshot()
}

/** The final frame of a recording. */
export function finalFrame(rec: RecordingData): Frame {
  return frameAt(rec, duration(rec))
}

export interface SampleOptions {
  /** Frames per second to sample. Default 8. */
  readonly fps?: number
  /** Start time (ms). Default 0. */
  readonly from?: number
  /** End time (ms). Default the recording duration. */
  readonly to?: number
  /** Hard cap on the number of frames produced. Default 600. */
  readonly maxFrames?: number
}

export interface SampledFrame {
  readonly time: number
  readonly frame: Frame
}

/**
 * Sample the recording into evenly spaced frames. Replays incrementally so the
 * cost is O(events + frames) rather than O(events × frames).
 */
export function sampleFrames(rec: RecordingData, options: SampleOptions = {}): SampledFrame[] {
  const fps = Math.max(1, options.fps ?? 8)
  const total = duration(rec)
  const from = Math.max(0, options.from ?? 0)
  const to = Math.min(total, options.to ?? total)
  const maxFrames = Math.max(1, options.maxFrames ?? 600)

  const step = 1000 / fps
  let count = Math.floor((to - from) / step) + 1
  if (count > maxFrames) count = maxFrames

  const screen = new Screen(rec.width, rec.height)
  const frames: SampledFrame[] = []
  let eventIdx = 0

  for (let i = 0; i < count; i++) {
    const t = i === count - 1 ? to : from + i * step
    while (eventIdx < rec.events.length && rec.events[eventIdx]!.time <= t) {
      screen.write(rec.events[eventIdx]!.data)
      eventIdx++
    }
    frames.push({ time: t, frame: screen.snapshot() })
  }
  return frames
}

/** Return a sub-recording spanning the two named markers (inclusive of output between them). */
export function clipBetweenMarkers(rec: RecordingData, startMarker: string, endMarker: string): RecordingData {
  const a = rec.markers.find((m) => m.name === startMarker)
  const b = rec.markers.find((m) => m.name === endMarker)
  if (!a || !b) throw new Error(`Markers "${startMarker}" and/or "${endMarker}" not found in recording.`)
  const from = Math.min(a.time, b.time)
  const to = Math.max(a.time, b.time)
  return clip(rec, from, to)
}

/** Return a sub-recording between two times (ms), re-based to start at 0. */
export function clip(rec: RecordingData, from: number, to: number): RecordingData {
  const events = rec.events
    .filter((e) => e.time >= from && e.time <= to)
    .map((e) => ({ time: e.time - from, data: e.data }))
  const markers = rec.markers
    .filter((m) => m.time >= from && m.time <= to)
    .map((m) => ({ time: m.time - from, name: m.name }))
  return {
    ...rec,
    startedAt: rec.startedAt + from,
    duration: to - from,
    events,
    markers,
  }
}

/**
 * Export to the asciinema v2 cast format: a header JSON object followed by one
 * JSON array per line (`[time_seconds, "o", data]`, `[time_seconds, "m", name]`).
 * Directly playable with the asciinema player.
 */
export function toAsciicast(rec: RecordingData): string {
  const header = {
    version: 2,
    width: rec.width,
    height: rec.height,
    timestamp: Math.floor(rec.startedAt / 1000),
    title: rec.title,
    command: [rec.command, ...rec.args].join(" ").trim() || undefined,
    env: { TERM: "xterm-256color" },
  }
  const lines: string[] = [JSON.stringify(header)]
  const stream: Array<{ time: number; kind: "o" | "m"; payload: string }> = [
    ...rec.events.map((e) => ({ time: e.time, kind: "o" as const, payload: e.data })),
    ...rec.markers.map((m) => ({ time: m.time, kind: "m" as const, payload: m.name })),
  ].sort((x, y) => x.time - y.time)
  for (const item of stream) {
    lines.push(JSON.stringify([item.time / 1000, item.kind, item.payload]))
  }
  return lines.join("\n") + "\n"
}

/** Parse a {@link RecordingData} previously produced by {@link Recorder.data}. */
export function fromJSON(json: string): RecordingData {
  const parsed = JSON.parse(json) as RecordingData
  if (parsed.version !== RECORDING_VERSION) {
    throw new Error(`Unsupported recording version ${parsed.version}; expected ${RECORDING_VERSION}.`)
  }
  return parsed
}
