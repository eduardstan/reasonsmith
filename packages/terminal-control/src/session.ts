/**
 * Session — a single PTY-backed terminal application whose output is parsed into
 * a live {@link Screen}. Provides input ({@link Session.send}), synchronization
 * ({@link Session.wait}), screen capture ({@link Session.snapshot}) and lifecycle.
 */
import { spawn, type IPty } from "bun-pty"
import stripAnsi from "strip-ansi"
import type { Frame } from "./frame"
import { Screen } from "./vt/screen"
import { translateKeys } from "./keys"
import { renderText } from "./render/text"
import { Recorder, type RecordingData, type RecordingMarker } from "./recording"

const RAW_LOG_LIMIT = 2 * 1024 * 1024 // 2 MB, matching nikcli's Pty buffer cap.

export type SessionStatus = "running" | "exited"

export interface SessionInfo {
  readonly name: string
  readonly command: string
  readonly args: ReadonlyArray<string>
  readonly cwd: string
  readonly cols: number
  readonly rows: number
  readonly pid: number
  readonly status: SessionStatus
  readonly exitCode?: number
  readonly title?: string
}

export interface SessionOptions {
  readonly name: string
  readonly command: string
  readonly args?: ReadonlyArray<string>
  readonly cwd?: string
  readonly cols?: number
  readonly rows?: number
  readonly env?: Record<string, string>
}

export type SendMode = "text" | "keys"

export type WaitCondition =
  | { readonly type: "text"; readonly value: string; readonly timeout?: number }
  | { readonly type: "stable"; readonly ms?: number; readonly timeout?: number }
  | { readonly type: "timeout"; readonly ms: number }

export interface WaitResult {
  readonly satisfied: boolean
  readonly reason: "matched" | "stable" | "timeout"
  readonly frame: Frame
}

export class Session {
  readonly name: string
  readonly command: string
  readonly args: string[]
  readonly cwd: string

  private readonly pty: IPty
  private readonly screen: Screen
  private rawLog = ""
  private status: SessionStatus = "running"
  private exitCode: number | undefined
  private lastDataAt = Date.now()
  private readonly listeners = new Set<() => void>()
  private recorder: Recorder | null = null

  constructor(options: SessionOptions) {
    this.name = options.name
    this.command = options.command
    this.args = [...(options.args ?? [])]
    const cols = options.cols ?? 80
    const rows = options.rows ?? 24
    this.cwd = options.cwd ?? process.cwd()
    this.screen = new Screen(cols, rows)

    const env = {
      ...process.env,
      ...options.env,
      TERM: "xterm-256color",
      NIKCLI_TERMINAL: "1",
    } as Record<string, string>

    this.pty = spawn(this.command, this.args, {
      name: "xterm-256color",
      cols,
      rows,
      cwd: this.cwd,
      env,
    })

    this.pty.onData((data) => {
      this.screen.write(data)
      this.recorder?.record(data)
      this.rawLog += data
      if (this.rawLog.length > RAW_LOG_LIMIT) this.rawLog = this.rawLog.slice(-RAW_LOG_LIMIT)
      this.lastDataAt = Date.now()
      this.notify()
    })

    this.pty.onExit(({ exitCode }) => {
      this.status = "exited"
      this.exitCode = exitCode
      this.recorder?.stop()
      this.notify()
    })
  }

  get pid(): number {
    return this.pty.pid
  }

  info(): SessionInfo {
    const frame = this.screen.snapshot()
    return {
      name: this.name,
      command: this.command,
      args: this.args,
      cwd: this.cwd,
      cols: this.screen.cols,
      rows: this.screen.rows,
      pid: this.pid,
      status: this.status,
      ...(this.exitCode !== undefined ? { exitCode: this.exitCode } : {}),
      ...(frame.title !== undefined ? { title: frame.title } : {}),
    }
  }

  snapshot(): Frame {
    return this.screen.snapshot()
  }

  /** Current raw, un-emulated output buffer (capped). */
  rawOutput(lines?: number): string {
    if (lines === undefined) return this.rawLog
    const parts = this.rawLog.split("\n")
    return parts.slice(-lines).join("\n")
  }

  /** Plain-text rendering of the current screen. */
  text(): string {
    return renderText(this.screen.snapshot())
  }

  /** Send input to the application. `text` writes verbatim; `keys` translates key names. */
  send(input: string, mode: SendMode = "text"): void {
    if (this.status !== "running") return
    const data = mode === "keys" ? translateKeys(input) : input
    this.pty.write(data)
  }

  resize(cols: number, rows: number): void {
    if (this.status === "running") {
      this.pty.resize(cols, rows)
    }
    this.screen.resize(cols, rows)
  }

  // --- Recording --------------------------------------------------------

  /** Begin recording the output timeline. Replaces any in-progress recording. */
  startRecording(): void {
    const info = this.info()
    this.recorder = new Recorder({
      width: this.screen.cols,
      height: this.screen.rows,
      command: this.command,
      args: this.args,
      title: info.title,
    })
  }

  /** Add a named marker to the active recording. Returns it, or undefined if not recording. */
  marker(name: string): RecordingMarker | undefined {
    return this.recorder?.marker(name)
  }

  /** Stop recording and return the captured timeline. */
  stopRecording(): RecordingData | null {
    if (!this.recorder) return null
    const data = this.recorder.stop()
    this.recorder = null
    return data
  }

  /** Current recording timeline without stopping, or null if not recording. */
  recordingData(): RecordingData | null {
    return this.recorder ? this.recorder.data() : null
  }

  isRecording(): boolean {
    return this.recorder !== null && this.recorder.active
  }

  stop(signal?: string): void {
    this.recorder?.stop()
    if (this.status === "running") {
      try {
        this.pty.kill(signal)
      } catch {
        // already gone
      }
    }
  }

  isRunning(): boolean {
    return this.status === "running"
  }

  private notify(): void {
    for (const fn of this.listeners) fn()
  }

  /**
   * Wait until a condition is met. Resolves with the screen frame at satisfaction
   * (or at timeout). Never rejects.
   */
  async wait(condition: WaitCondition): Promise<WaitResult> {
    if (condition.type === "timeout") {
      await delay(condition.ms)
      return { satisfied: true, reason: "timeout", frame: this.snapshot() }
    }

    if (condition.type === "text") {
      const timeout = condition.timeout ?? 10_000
      const deadline = Date.now() + timeout
      const matches = () => stripAnsi(this.text()).includes(condition.value)
      if (matches()) return { satisfied: true, reason: "matched", frame: this.snapshot() }
      return new Promise<WaitResult>((resolve) => {
        const finish = (satisfied: boolean) => {
          this.listeners.delete(check)
          clearInterval(timer)
          resolve({
            satisfied,
            reason: satisfied ? "matched" : "timeout",
            frame: this.snapshot(),
          })
        }
        const check = () => {
          if (matches()) finish(true)
          else if (Date.now() >= deadline || !this.isRunning()) finish(matches())
        }
        this.listeners.add(check)
        const timer = setInterval(check, 50)
      })
    }

    // stable: resolve once no new output has arrived for `ms`.
    const quietMs = condition.ms ?? 500
    const timeout = condition.timeout ?? 10_000
    const deadline = Date.now() + timeout
    return new Promise<WaitResult>((resolve) => {
      const finish = (reason: "stable" | "timeout") => {
        this.listeners.delete(onData)
        clearInterval(timer)
        resolve({ satisfied: true, reason, frame: this.snapshot() })
      }
      const onData = () => {}
      this.listeners.add(onData)
      const timer = setInterval(() => {
        if (Date.now() - this.lastDataAt >= quietMs) finish("stable")
        else if (Date.now() >= deadline) finish("timeout")
      }, 50)
    })
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
