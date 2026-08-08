/**
 * SessionManager — an in-memory registry of named {@link Session}s. Framework
 * agnostic; nikcli wraps this in an Effect service for per-instance lifecycle.
 */
import {
  Session,
  type SessionInfo,
  type SessionOptions,
  type SendMode,
  type WaitCondition,
  type WaitResult,
} from "./session"
import type { Frame } from "./frame"
import type { RecordingData, RecordingMarker } from "./recording"

export class SessionManager {
  private readonly sessions = new Map<string, Session>()
  private counter = 0

  /** Start a new session. If `name` is omitted, one is generated. Replaces an existing same-named session. */
  start(options: Omit<SessionOptions, "name"> & { name?: string }): SessionInfo {
    const name = options.name && options.name.length > 0 ? options.name : this.generateName()
    const existing = this.sessions.get(name)
    if (existing) existing.stop()
    const session = new Session({ ...options, name })
    this.sessions.set(name, session)
    return session.info()
  }

  private generateName(): string {
    this.counter++
    return `term-${this.counter}`
  }

  has(name: string): boolean {
    return this.sessions.has(name)
  }

  get(name: string): Session | undefined {
    return this.sessions.get(name)
  }

  private require(name: string): Session {
    const session = this.sessions.get(name)
    if (!session) throw new Error(`No terminal session named "${name}". Use action "list" to see active sessions.`)
    return session
  }

  list(): SessionInfo[] {
    return Array.from(this.sessions.values()).map((s) => s.info())
  }

  send(name: string, input: string, mode: SendMode = "text"): void {
    this.require(name).send(input, mode)
  }

  wait(name: string, condition: WaitCondition): Promise<WaitResult> {
    return this.require(name).wait(condition)
  }

  resize(name: string, cols: number, rows: number): SessionInfo {
    const session = this.require(name)
    session.resize(cols, rows)
    return session.info()
  }

  snapshot(name: string): Frame {
    return this.require(name).snapshot()
  }

  text(name: string): string {
    return this.require(name).text()
  }

  rawOutput(name: string, lines?: number): string {
    return this.require(name).rawOutput(lines)
  }

  info(name: string): SessionInfo {
    return this.require(name).info()
  }

  stop(name: string): void {
    const session = this.sessions.get(name)
    if (!session) return
    session.stop()
    this.sessions.delete(name)
  }

  /** Restart a session with the same command/args/cwd/size. */
  restart(name: string): SessionInfo {
    const session = this.require(name)
    const prev = session.info()
    session.stop()
    this.sessions.delete(name)
    return this.start({
      name,
      command: prev.command,
      args: [...prev.args],
      cwd: prev.cwd,
      cols: prev.cols,
      rows: prev.rows,
    })
  }

  // --- Recording --------------------------------------------------------

  startRecording(name: string): void {
    this.require(name).startRecording()
  }

  marker(name: string, markerName: string): RecordingMarker | undefined {
    return this.require(name).marker(markerName)
  }

  stopRecording(name: string): RecordingData | null {
    return this.require(name).stopRecording()
  }

  recordingData(name: string): RecordingData | null {
    return this.require(name).recordingData()
  }

  isRecording(name: string): boolean {
    return this.require(name).isRecording()
  }

  /** Kill every session and clear the registry. */
  closeAll(): void {
    for (const session of this.sessions.values()) {
      session.stop()
    }
    this.sessions.clear()
  }
}
