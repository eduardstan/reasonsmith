import { describe, expect, test } from "bun:test"
import { Screen } from "../src/vt/screen"
import { renderText } from "../src/render/text"

function textOf(screen: Screen): string {
  return renderText(screen.snapshot())
}

describe("Screen — printing & control", () => {
  test("writes plain text at the cursor", () => {
    const s = new Screen(20, 5)
    s.write("hello")
    expect(textOf(s)).toBe("hello")
    const frame = s.snapshot()
    expect(frame.cursor.x).toBe(5)
    expect(frame.cursor.y).toBe(0)
  })

  test("CR + LF move to start of next line", () => {
    const s = new Screen(20, 5)
    s.write("ab\r\ncd")
    expect(textOf(s)).toBe("ab\ncd")
  })

  test("autowrap to the next line at the right margin", () => {
    const s = new Screen(3, 3)
    s.write("abcd")
    const frame = s.snapshot()
    expect(frame.cells[0].map((c) => c.char).join("")).toBe("abc")
    expect(frame.cells[1][0].char).toBe("d")
  })

  test("backspace moves cursor left without erasing", () => {
    const s = new Screen(10, 2)
    s.write("abc\b\bX")
    expect(textOf(s)).toBe("aXc")
  })
})

describe("Screen — cursor positioning", () => {
  test("CUP positions the cursor (1-based)", () => {
    const s = new Screen(10, 5)
    s.write("\x1b[3;5HX")
    const frame = s.snapshot()
    expect(frame.cells[2][4].char).toBe("X")
  })

  test("CUF/CUB/CUU/CUD move relatively", () => {
    const s = new Screen(10, 5)
    s.write("\x1b[2;2H") // row2,col2
    s.write("\x1b[3C") // forward 3 -> col5
    s.write("\x1b[1B") // down 1 -> row3
    s.write("Z")
    const frame = s.snapshot()
    expect(frame.cells[2][4].char).toBe("Z")
  })
})

describe("Screen — erasing", () => {
  test("EL mode 0 erases from cursor to end of line", () => {
    const s = new Screen(10, 2)
    s.write("abcdef")
    s.write("\x1b[1;4H") // col 4 (the 'd')
    s.write("\x1b[K")
    expect(textOf(s)).toBe("abc")
  })

  test("ED mode 2 clears the whole screen", () => {
    const s = new Screen(10, 3)
    s.write("line1\r\nline2")
    s.write("\x1b[2J")
    expect(textOf(s)).toBe("")
  })
})

describe("Screen — SGR attributes", () => {
  test("applies foreground color and bold", () => {
    const s = new Screen(10, 2)
    s.write("\x1b[1;31mR\x1b[0mN")
    const frame = s.snapshot()
    const r = frame.cells[0][0]
    const n = frame.cells[0][1]
    expect(r.bold).toBe(true)
    expect(r.fg).toEqual({ type: "indexed", index: 1 })
    expect(n.bold).toBe(false)
    expect(n.fg).toEqual({ type: "default" })
  })

  test("256-color and truecolor", () => {
    const s = new Screen(10, 2)
    s.write("\x1b[38;5;200mA")
    s.write("\x1b[38;2;10;20;30mB")
    const frame = s.snapshot()
    expect(frame.cells[0][0].fg).toEqual({ type: "indexed", index: 200 })
    expect(frame.cells[0][1].fg).toEqual({ type: "rgb", r: 10, g: 20, b: 30 })
  })
})

describe("Screen — scrolling & title", () => {
  test("LF at the bottom scrolls the screen up", () => {
    const s = new Screen(5, 2)
    s.write("aaa\r\nbbb\r\nccc")
    // 2-row screen: after scroll, top line is "bbb", bottom "ccc".
    expect(textOf(s)).toBe("bbb\nccc")
  })

  test("OSC 2 sets the window title", () => {
    const s = new Screen(10, 2)
    s.write("\x1b]2;my title\x07")
    expect(s.snapshot().title).toBe("my title")
  })

  test("cursor visibility via DECTCEM", () => {
    const s = new Screen(5, 2)
    s.write("\x1b[?25l")
    expect(s.snapshot().cursor.visible).toBe(false)
    s.write("\x1b[?25h")
    expect(s.snapshot().cursor.visible).toBe(true)
  })
})

describe("Screen — robustness", () => {
  test("ignores unknown sequences without throwing", () => {
    const s = new Screen(10, 2)
    expect(() => s.write("\x1b[?2004h\x1b[>1;2cok")).not.toThrow()
    expect(textOf(s)).toContain("ok")
  })

  test("handles a sequence split across writes", () => {
    const s = new Screen(10, 2)
    s.write("\x1b[")
    s.write("31m")
    s.write("X")
    expect(s.snapshot().cells[0][0].fg).toEqual({ type: "indexed", index: 1 })
  })
})
