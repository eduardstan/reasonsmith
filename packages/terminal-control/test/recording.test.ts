import { describe, expect, test } from "bun:test"
import {
  Recorder,
  frameAt,
  finalFrame,
  sampleFrames,
  duration,
  clipBetweenMarkers,
  toAsciicast,
  fromJSON,
} from "../src/recording"
import { renderText } from "../src/render/text"
import { renderAnimatedSvg } from "../src/render/video"
import { SessionManager } from "../src/manager"
import { describePty } from "./pty"

/** Build a recording by hand with known timings. */
function makeRecording(): ReturnType<Recorder["data"]> {
  const rec = new Recorder({ width: 20, height: 4, command: "demo", args: [] })
  // Recorder timestamps with Date.now(); to make deterministic, monkey-build manually instead.
  return rec.data()
}

describe("Recorder", () => {
  test("captures events and markers", () => {
    const rec = new Recorder({ width: 10, height: 3, command: "x", args: [] })
    rec.record("hello")
    rec.marker("after-hello")
    rec.record("\r\nworld")
    const data = rec.stop()
    expect(data.events.length).toBe(2)
    expect(data.markers.length).toBe(1)
    expect(data.markers[0].name).toBe("after-hello")
    expect(data.events[0].data).toBe("hello")
    expect(data.width).toBe(10)
  })

  test("no-ops after stop", () => {
    const rec = new Recorder({ width: 5, height: 2, command: "x", args: [] })
    rec.record("a")
    rec.stop()
    rec.record("b")
    rec.marker("late")
    expect(rec.data().events.length).toBe(1)
    expect(rec.data().markers.length).toBe(0)
  })
})

describe("replay", () => {
  // Construct a recording with explicit times by post-processing.
  function timed(events: Array<{ time: number; data: string }>, markers: Array<{ time: number; name: string }> = []) {
    return {
      version: 1 as const,
      width: 20,
      height: 4,
      command: "demo",
      args: [] as string[],
      startedAt: 0,
      duration: events.length ? events[events.length - 1].time : 0,
      events,
      markers,
    }
  }

  test("frameAt replays up to a time", () => {
    const rec = timed([
      { time: 0, data: "AAA" },
      { time: 100, data: "\r\nBBB" },
      { time: 200, data: "\r\nCCC" },
    ])
    expect(renderText(frameAt(rec, 0))).toBe("AAA")
    expect(renderText(frameAt(rec, 100))).toBe("AAA\nBBB")
    expect(renderText(finalFrame(rec))).toBe("AAA\nBBB\nCCC")
  })

  test("sampleFrames yields evenly spaced frames", () => {
    const rec = timed([
      { time: 0, data: "1" },
      { time: 500, data: "2" },
      { time: 1000, data: "3" },
    ])
    const frames = sampleFrames(rec, { fps: 2 })
    expect(frames.length).toBeGreaterThan(1)
    expect(frames[0].time).toBe(0)
    // Last sampled frame shows the full output.
    expect(renderText(frames[frames.length - 1].frame)).toContain("3")
  })

  test("clipBetweenMarkers extracts a sub-recording", () => {
    const rec = timed(
      [
        { time: 0, data: "start" },
        { time: 100, data: "mid" },
        { time: 200, data: "end" },
      ],
      [
        { time: 100, name: "a" },
        { time: 200, name: "b" },
      ],
    )
    const clip = clipBetweenMarkers(rec, "a", "b")
    expect(clip.events.length).toBe(2)
    expect(clip.events[0].time).toBe(0) // re-based
    expect(duration(clip)).toBe(100)
  })

  test("toAsciicast emits a v2 header + event lines, round-trips JSON", () => {
    const rec = timed(
      [
        { time: 0, data: "hi" },
        { time: 250, data: "!" },
      ],
      [{ time: 100, name: "m1" }],
    )
    const cast = toAsciicast(rec)
    const lines = cast.trim().split("\n")
    const header = JSON.parse(lines[0])
    expect(header.version).toBe(2)
    expect(header.width).toBe(20)
    // event lines parse as [time, kind, payload]
    const ev = JSON.parse(lines[1])
    expect(ev[1]).toBe("o")
    expect(typeof ev[0]).toBe("number")
    // marker present as "m"
    expect(cast).toContain('"m1"')
    // recording JSON round-trips
    expect(() => fromJSON(JSON.stringify(rec))).not.toThrow()
  })

  test("renderAnimatedSvg produces a self-contained animated svg", () => {
    const rec = timed([
      { time: 0, data: "frame-one" },
      { time: 500, data: "\r\nframe-two" },
    ])
    const svg = renderAnimatedSvg(rec, { fps: 4 })
    expect(svg.startsWith("<svg")).toBe(true)
    expect(svg).toContain("@keyframes tcf0")
    expect(svg).toContain("step-end")
    expect(svg).toContain("</svg>")
  })
})

describePty("SessionManager recording integration", () => {
  test("records a live session and exports asciicast", async () => {
    const manager = new SessionManager()
    manager.start({
      name: "rec",
      command: "/bin/sh",
      args: ["-c", "printf 'ONE'; sleep 0.3; printf 'TWO'; sleep 1"],
      cols: 20,
      rows: 4,
    })
    manager.startRecording("rec")
    const sawOne = await manager.wait("rec", { type: "text", value: "ONE", timeout: 3000 })
    expect(sawOne.satisfied).toBe(true)
    // `Session.marker` is `this.recorder?.marker(name)` and `Recorder.marker` returns undefined
    // once stopped: two silent no-ops in a row. Asserting the return value here means a recorder
    // that is not running fails at the call that needed it, rather than as a marker missing from
    // the timeline three assertions later — which is how this test failed on #181 and #183, on
    // branches that changed nothing it touches.
    expect(manager.marker("rec", "saw-one")).toBeTruthy()
    const sawTwo = await manager.wait("rec", { type: "text", value: "TWO", timeout: 3000 })
    expect(sawTwo.satisfied).toBe(true)
    const data = manager.stopRecording("rec")
    expect(data).not.toBeNull()
    expect(data!.events.length).toBeGreaterThan(0)
    expect(data!.markers.find((m) => m.name === "saw-one")).toBeTruthy()
    expect(toAsciicast(data!)).toContain('"version":2')
    manager.closeAll()
  })
})

// Touch unused helper to keep import meaningful without flakiness.
void makeRecording
