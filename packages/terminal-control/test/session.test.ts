import { describe, expect, test } from "bun:test"
import { SessionManager } from "../src/manager"
import { translateKeys } from "../src/keys"
import { describePty } from "./pty"

describe("translateKeys", () => {
  test("named keys and modifiers", () => {
    expect(translateKeys("enter")).toBe("\r")
    expect(translateKeys("tab")).toBe("\t")
    expect(translateKeys("up")).toBe("\x1b[A")
    expect(translateKeys("ctrl+c")).toBe("\x03")
    expect(translateKeys("alt+x")).toBe("\x1bx")
  })

  test("sequences of keys", () => {
    expect(translateKeys("h i enter")).toBe("hienter".replace("enter", "\r"))
  })
})

describePty("SessionManager — lifecycle", () => {
  test("runs a command, captures output, and stops", async () => {
    const manager = new SessionManager()
    manager.start({
      name: "echo",
      command: "/bin/sh",
      args: ["-c", "printf 'READY-MARKER'; sleep 2"],
      cols: 40,
      rows: 6,
    })

    const result = await manager.wait("echo", { type: "text", value: "READY-MARKER", timeout: 4000 })
    expect(result.satisfied).toBe(true)
    expect(manager.text("echo")).toContain("READY-MARKER")

    const list = manager.list()
    expect(list.find((s) => s.name === "echo")?.status).toBe("running")

    manager.stop("echo")
    expect(manager.has("echo")).toBe(false)
  })

  test("generates a name when none is given", () => {
    const manager = new SessionManager()
    const info = manager.start({ command: "/bin/sh", args: ["-c", "sleep 1"] })
    expect(info.name).toMatch(/^term-\d+$/)
    manager.closeAll()
  })

  test("wait stable resolves after output settles", async () => {
    const manager = new SessionManager()
    manager.start({ name: "q", command: "/bin/sh", args: ["-c", "printf 'x'; sleep 2"], cols: 20, rows: 4 })
    const result = await manager.wait("q", { type: "stable", ms: 300, timeout: 4000 })
    expect(result.reason).toBe("stable")
    manager.closeAll()
  })
})
