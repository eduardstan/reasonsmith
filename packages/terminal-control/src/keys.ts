/**
 * Translate human-friendly key names into the byte sequences a terminal app
 * expects. Used by `Session.send(..., { mode: "keys" })`.
 *
 * A key spec is a token like `enter`, `tab`, `up`, `f5`, `ctrl+c`, `alt+x`,
 * `ctrl+shift+a`. Multiple keys can be separated by whitespace.
 */

const NAMED: Record<string, string> = {
  enter: "\r",
  return: "\r",
  ret: "\r",
  tab: "\t",
  esc: "\x1b",
  escape: "\x1b",
  space: " ",
  backspace: "\x7f",
  bs: "\x7f",
  delete: "\x1b[3~",
  del: "\x1b[3~",
  up: "\x1b[A",
  down: "\x1b[B",
  right: "\x1b[C",
  left: "\x1b[D",
  home: "\x1b[H",
  end: "\x1b[F",
  pageup: "\x1b[5~",
  pagedown: "\x1b[6~",
  insert: "\x1b[2~",
  f1: "\x1bOP",
  f2: "\x1bOQ",
  f3: "\x1bOR",
  f4: "\x1bOS",
  f5: "\x1b[15~",
  f6: "\x1b[17~",
  f7: "\x1b[18~",
  f8: "\x1b[19~",
  f9: "\x1b[20~",
  f10: "\x1b[21~",
  f11: "\x1b[23~",
  f12: "\x1b[24~",
}

function ctrlByte(ch: string): string | undefined {
  const c = ch.toLowerCase()
  if (c.length !== 1) return undefined
  const code = c.charCodeAt(0)
  // Ctrl-A..Ctrl-Z -> 0x01..0x1a
  if (code >= 97 && code <= 122) return String.fromCharCode(code - 96)
  // A few common control symbols.
  const map: Record<string, string> = {
    "[": "\x1b",
    "\\": "\x1c",
    "]": "\x1d",
    " ": "\x00",
    "@": "\x00",
  }
  return map[c]
}

/** Translate a single key token to its escape sequence. Returns `null` if unknown. */
export function translateKey(token: string): string | null {
  const raw = token.trim()
  if (raw.length === 0) return null

  // Plain named key.
  const named = NAMED[raw.toLowerCase()]
  if (named !== undefined) return named

  // Modifier chains: ctrl+/alt+/shift+ ... base
  if (raw.includes("+") || raw.includes("-")) {
    const parts = raw.split(/[+\-]/).filter(Boolean)
    if (parts.length >= 2) {
      const mods = parts.slice(0, -1).map((m) => m.toLowerCase())
      const base = parts[parts.length - 1]
      let seq = NAMED[base.toLowerCase()] ?? base
      if (mods.includes("ctrl") || mods.includes("c")) {
        const cb = ctrlByte(base)
        if (cb !== undefined) seq = cb
      }
      if (mods.includes("alt") || mods.includes("meta") || mods.includes("m")) {
        seq = "\x1b" + seq
      }
      return seq
    }
  }

  // Single printable character.
  if (raw.length === 1) return raw

  return null
}

/** Translate a whitespace-separated list of key tokens into a byte string. */
export function translateKeys(input: string): string {
  const tokens = input.split(/\s+/).filter(Boolean)
  let out = ""
  for (const token of tokens) {
    const seq = translateKey(token)
    // Unknown tokens are sent literally so e.g. `send "hello"` still works in keys mode.
    out += seq ?? token
  }
  return out
}
