/**
 * A streaming VT/ANSI parser. Feed it raw terminal output in arbitrary chunks
 * (as they arrive from a PTY) and it dispatches structured events to a {@link ParserSink}.
 *
 * Modeled loosely on Paul Williams' VT500 state machine, trimmed to the subset
 * needed to faithfully render real-world TUIs. Anything it doesn't understand is
 * consumed and dropped — the parser never throws on malformed input.
 */

export interface ParserSink {
  /** A run of printable characters to write at the cursor. */
  print(text: string): void
  /** A C0 control byte (e.g. BEL 0x07, BS 0x08, HT 0x09, LF 0x0a, CR 0x0d). */
  execute(byte: number): void
  /** A CSI sequence: `ESC [ params... final`. `final` is a single char. */
  csiDispatch(params: number[], intermediates: string, final: string, isPrivate: boolean): void
  /** An ESC sequence with no CSI (e.g. `ESC 7`, `ESC M`, `ESC ( B`). */
  escDispatch(intermediates: string, final: string): void
  /** An OSC string: `ESC ] data BEL` or `ESC ] data ST`. */
  oscDispatch(data: string): void
}

const enum State {
  Ground,
  Escape,
  CsiEntry,
  CsiParam,
  CsiIntermediate,
  OscString,
  // Consume a DCS/SOS/PM/APC string until ST; we don't act on these.
  StringConsume,
}

const BEL = 0x07
const ESC = 0x1b
const CAN = 0x18
const SUB = 0x1a
const ST_C1 = 0x9c

export class Parser {
  private state: State = State.Ground
  private params: number[] = []
  private currentParam = ""
  private intermediates = ""
  private isPrivate = false
  private oscBuffer = ""
  private printBuffer = ""

  constructor(private readonly sink: ParserSink) {}

  /** Feed a chunk of terminal output. Safe to call repeatedly; state persists. */
  write(chunk: string): void {
    for (let i = 0; i < chunk.length; i++) {
      this.consume(chunk.charCodeAt(i), chunk[i])
    }
    this.flushPrint()
  }

  private flushPrint(): void {
    if (this.printBuffer.length > 0) {
      this.sink.print(this.printBuffer)
      this.printBuffer = ""
    }
  }

  private consume(code: number, ch: string): void {
    switch (this.state) {
      case State.Ground:
        this.ground(code, ch)
        break
      case State.Escape:
        this.escape(code, ch)
        break
      case State.CsiEntry:
      case State.CsiParam:
      case State.CsiIntermediate:
        this.csi(code, ch)
        break
      case State.OscString:
        this.osc(code, ch)
        break
      case State.StringConsume:
        this.stringConsume(code)
        break
    }
  }

  private ground(code: number, ch: string): void {
    if (code === ESC) {
      this.flushPrint()
      this.enterEscape()
      return
    }
    // C0 controls (excluding ESC) are executed, not printed.
    if (code < 0x20) {
      this.flushPrint()
      this.sink.execute(code)
      return
    }
    if (code === 0x7f) return // DEL — ignore
    this.printBuffer += ch
  }

  private enterEscape(): void {
    this.state = State.Escape
    this.intermediates = ""
  }

  private escape(code: number, ch: string): void {
    if (code === ESC) return // stay; new escape
    if (code === 0x5b) {
      // '['
      this.enterCsi()
      return
    }
    if (code === 0x5d) {
      // ']'
      this.state = State.OscString
      this.oscBuffer = ""
      return
    }
    if (code === 0x50 || code === 0x58 || code === 0x5e || code === 0x5f) {
      // DCS 'P', SOS 'X', PM '^', APC '_' — consume until ST.
      this.state = State.StringConsume
      return
    }
    // Intermediate bytes (0x20–0x2f) accumulate, e.g. ESC ( B.
    if (code >= 0x20 && code <= 0x2f) {
      this.intermediates += ch
      return
    }
    // Final byte (0x30–0x7e): dispatch a plain ESC sequence.
    if (code >= 0x30 && code <= 0x7e) {
      this.sink.escDispatch(this.intermediates, ch)
      this.state = State.Ground
      return
    }
    // Anything else (control char) — abort the sequence.
    this.state = State.Ground
  }

  private enterCsi(): void {
    this.state = State.CsiEntry
    this.params = []
    this.currentParam = ""
    this.intermediates = ""
    this.isPrivate = false
  }

  private csi(code: number, ch: string): void {
    if (code === ESC) {
      this.enterEscape()
      return
    }
    if (code === CAN || code === SUB) {
      this.state = State.Ground
      return
    }
    // Private marker (?, >, =, <) only valid right after CSI.
    if (this.state === State.CsiEntry && code >= 0x3c && code <= 0x3f) {
      this.isPrivate = true
      this.state = State.CsiParam
      return
    }
    // Parameter digits.
    if (code >= 0x30 && code <= 0x39) {
      this.currentParam += ch
      this.state = State.CsiParam
      return
    }
    // Parameter separator.
    if (code === 0x3b) {
      this.pushParam()
      this.state = State.CsiParam
      return
    }
    // Sub-parameter separator (':') — treat like ';' for our purposes.
    if (code === 0x3a) {
      this.pushParam()
      this.state = State.CsiParam
      return
    }
    // Intermediate bytes.
    if (code >= 0x20 && code <= 0x2f) {
      this.intermediates += ch
      this.state = State.CsiIntermediate
      return
    }
    // Final byte — dispatch.
    if (code >= 0x40 && code <= 0x7e) {
      this.pushParam()
      this.sink.csiDispatch(this.params, this.intermediates, ch, this.isPrivate)
      this.state = State.Ground
      return
    }
    // C0 controls embedded inside CSI are executed in place.
    if (code < 0x20) {
      this.sink.execute(code)
      return
    }
  }

  private pushParam(): void {
    if (this.currentParam === "") {
      // Empty param defaults to 0 only if there are already params or a separator
      // was seen; the consumer applies command-specific defaults.
      this.params.push(0)
    } else {
      this.params.push(parseInt(this.currentParam, 10) || 0)
    }
    this.currentParam = ""
  }

  private osc(code: number, ch: string): void {
    if (code === BEL || code === ST_C1) {
      this.sink.oscDispatch(this.oscBuffer)
      this.state = State.Ground
      return
    }
    if (code === ESC) {
      // Possible ST (ESC \). Peek handled by escape state: enter escape and let
      // a following '\' terminate. Simpler: flush here and re-enter escape.
      this.sink.oscDispatch(this.oscBuffer)
      this.enterEscape()
      return
    }
    if (code === CAN || code === SUB) {
      this.state = State.Ground
      return
    }
    this.oscBuffer += ch
  }

  private stringConsume(code: number): void {
    if (code === BEL || code === ST_C1) {
      this.state = State.Ground
      return
    }
    if (code === ESC) {
      this.enterEscape()
      return
    }
    // Otherwise consume silently.
  }
}
