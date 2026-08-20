import { describe, expect, test } from "bun:test"
import { Screen } from "../src/vt/screen"
import { renderText } from "../src/render/text"
import { renderAnsi } from "../src/render/ansi"
import { renderJSON, toJSONFrame } from "../src/render/json"
import { renderSvg } from "../src/render/svg"

function screenWith(input: string, cols = 20, rows = 4): Screen {
  const s = new Screen(cols, rows)
  s.write(input)
  return s
}

describe("renderText", () => {
  test("trims trailing whitespace and blank lines", () => {
    const s = screenWith("hi   \r\n\r\n")
    expect(renderText(s.snapshot())).toBe("hi")
  })
})

describe("renderAnsi", () => {
  test("re-emits SGR for colored text and ends with reset", () => {
    const s = screenWith("\x1b[31mred\x1b[0m")
    const out = renderAnsi(s.snapshot())
    expect(out).toContain("\x1b[")
    expect(out).toContain("31")
    expect(out).toContain("red")
    expect(out.endsWith("\x1b[0m")).toBe(true)
  })
})

describe("renderJSON", () => {
  test("produces structured cells with size and cursor", () => {
    const s = screenWith("\x1b[1mAB\x1b[0m")
    const json = toJSONFrame(s.snapshot())
    expect(json.cols).toBe(20)
    expect(json.rows).toBe(4)
    expect(json.rows_cells[0][0]).toMatchObject({ char: "A", bold: true })
    // Round-trips through JSON.stringify.
    expect(() => JSON.parse(renderJSON(s.snapshot()))).not.toThrow()
  })
})

describe("renderSvg", () => {
  test("emits an svg containing the glyphs", () => {
    const s = screenWith("Hello")
    const svg = renderSvg(s.snapshot())
    expect(svg.startsWith("<svg")).toBe(true)
    expect(svg).toContain("Hello")
    expect(svg).toContain("</svg>")
  })

  test("escapes XML-special characters", () => {
    const s = screenWith("a<b>&")
    const svg = renderSvg(s.snapshot())
    expect(svg).toContain("a&lt;b&gt;&amp;")
  })
})
