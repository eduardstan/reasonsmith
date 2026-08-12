# @nikcli-ai/terminal-control

Control, inspect, capture and test real terminal applications (TUIs) — a
custom-built, dependency-light terminal-control engine for nikcli, inspired by
[kitlangton/terminal-control](https://github.com/kitlangton/terminal-control)
but written in TypeScript/Bun.

For agent-driven TUI verification, the package also exposes the upstream native
driver through `TerminalControl` and ships a `terminal-control` evidence CLI.
This path provides OpenTUI negotiation, byte-accurate VT state, deterministic
waits, process-tree cleanup and versioned recordings.

It spawns a PTY-backed program, parses its ANSI/VT output into a **screen grid**
(a `Frame` — a 2D array of styled cells via a hand-rolled VT100/xterm emulator),
and renders that frame to **text / ansi / json / svg / png**.

## Usage

```ts
import { SessionManager, renderText, renderSvg } from "@nikcli-ai/terminal-control"

const manager = new SessionManager()

// Start a TUI.
manager.start({ name: "top", command: "top", cols: 100, rows: 30 })

// Wait until it has drawn something recognizable.
await manager.wait("top", { type: "text", value: "PID", timeout: 5000 })

// Capture the rendered screen.
console.log(renderText(manager.snapshot("top")))
const svg = renderSvg(manager.snapshot("top"))

// Drive it, then stop.
manager.send("top", "q", "keys")
manager.stop("top")
```

## API surface

- `SessionManager` — `start / list / get / send / wait / resize / snapshot / text / rawOutput / stop / restart / closeAll` plus recording: `startRecording / marker / stopRecording / recordingData / isRecording`.
- `Session` — a single PTY app: `send(input, "text"|"keys")`, `wait(condition)`, `snapshot()`, `resize()`, `stop()`, `startRecording()`, `marker(name)`, `stopRecording()`.
- `Screen` / `Parser` — the VT emulator (usable standalone to parse any ANSI stream).
- `renderText / renderAnsi / renderJSON / renderSvg / renderPng` and the `renderString(frame, format)` dispatcher.

`wait` conditions: `{ type: "text", value, timeout? }`, `{ type: "stable", ms?, timeout? }`, `{ type: "timeout", ms }`.

PNG rendering uses the optional `@resvg/resvg-js` dependency, imported lazily.

## Recording & video (v2)

Capture a session's output timeline and replay or export it.

```ts
manager.startRecording("top")
manager.marker("top", "after-load")
// ... drive the session ...
const rec = manager.stopRecording("top")! // RecordingData (versioned, serializable)
```

- `frameAt(rec, ms)` / `finalFrame(rec)` — reconstruct the screen at any moment.
- `sampleFrames(rec, { fps })` — evenly spaced frames (incremental replay, O(events + frames)).
- `clipBetweenMarkers(rec, "a", "b")` / `clip(rec, from, to)` — extract a sub-recording.
- `toAsciicast(rec)` — export to the standard **asciinema v2** cast format.
- `renderAnimatedSvg(rec, { fps, speed })` — a **self-contained animated SVG** (zero dependencies).
- `renderPngSequence(rec, { fps })` — a sequence of PNG frames (needs `@resvg/resvg-js`).
- `exportVideo(rec, { format: "mp4" | "gif", outPath, fps, speed })` — assembled via the
  `ffmpeg` binary if present; `ffmpegAvailable()` reports availability (falls back to `svganim`).

## Scope

Full session/frame/render core **and** v2 timeline recording, replay, asciicast,
animated SVG, PNG-sequence and ffmpeg-based mp4/gif export.

## Agent-driven TUI verification

Register the bundled skill once in the current workspace, then restart nikcli:

```bash
bun run --cwd packages/terminal-control install-skill
```

The command creates an idempotent relative link at
`.agents/skills/terminal-control`, which nikcli discovers without changes to its
source. Then use the native driver to operate a named recorded session. When
developing from this monorepo, invoke the package-local command as
`bun run --cwd packages/terminal-control control --`. Installed distributions
expose the shorter `terminal-control` binary used below.

```bash
terminal-control start tui-check --host opentui --cols 112 --rows 34 \
  --record /tmp/tui-check.termctrl -- env NIKCLI_TERMINAL=1 my-tui
terminal-control wait tui-check "Ready" --timeout 20000
terminal-control send tui-check text:hello enter
terminal-control wait tui-check "Done" --timeout 60000
terminal-control stop tui-check
```

Create evidence suitable for a pull request:

```bash
terminal-control bundle \
  --recording /tmp/tui-check.termctrl \
  --out artifacts/tui/tui-check \
  --link-base artifacts/tui/tui-check \
  --include-recording \
  --result passed \
  --summary "The tested terminal interaction completed successfully."
```

The bundle includes the final visible screen as text/JSON/SVG/PNG, an MP4,
an inline GIF preview, the native `recording.termctrl`, a hash-bearing
`manifest.json`, and `pr.md`. Raw recordings can contain typed secrets and are
copied only with the explicit `--include-recording` flag. Its
agent-facing output includes an absolute `file://` Markdown image so nikcli can
show the preview in the conversation; `pr.md` remains repository/public-link
oriented and never contains that local URL.

The repository GitHub runner discovers completed bundles under
`artifacts/tui/**/manifest.json`. It verifies artifact sizes and SHA-256 values,
requires GIF, MP4, and raw `.termctrl` evidence when a `/nikcli` comment asks to
test a TUI, and publishes immutable commit-addressed links in the PR body.
