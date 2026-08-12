---
name: terminal-control
description: Autonomously control, inspect, test, and record real terminal applications through PTY sessions, retaining the native raw .termctrl stream and producing screenshots, GIF, MP4, a manifest, inline nikcli evidence, and PR-ready Markdown. Use whenever the user asks to test, check, exercise, or verify a TUI, OpenTUI application, REPL, interactive CLI, shell workflow, or terminal regression, including requests such as "testa il TUI", "registra il vero TUI", "registrazione grezza", or "includilo nella PR".
---

# Terminal Control

Operate the visible terminal state with `terminal-control`. Never infer a full-screen TUI from logs. Inside the nikcli monorepo, where the package binary is not installed globally, replace `terminal-control` with `bun run --cwd packages/terminal-control control --`.

## Handle Requests Autonomously

When the user asks to test a terminal interface, inspect the project to identify its real launch command and acceptance criteria, then run the recorded verification without asking for commands that are already discoverable. Translate the requested interactions into deterministic `wait`, `send`, `show`, and `mark` operations. Do not claim success unless the visible screen proves the expected result.

Restarted nikcli processes discover this skill through `.agents/skills/terminal-control`. If the skill is not registered in the current workspace, install it once from the worktree root:

```bash
bun run --cwd packages/terminal-control install-skill
```

## Run A Recorded Verification

Use a named session and enable the OpenTUI host profile for OpenTUI applications:

```bash
terminal-control start tui-check --host opentui --cols 112 --rows 34 --record /tmp/tui-check.termctrl -- my-tui
terminal-control wait tui-check "Ready" --timeout 20000
terminal-control show tui-check
terminal-control mark tui-check ready
terminal-control send tui-check text:hello enter
terminal-control wait tui-check "Done" --timeout 60000
terminal-control mark tui-check verified
terminal-control show tui-check
terminal-control stop tui-check
```

When testing nikcli or another Bun/OpenTUI application in a managed PTY, ensure the child inherits `NIKCLI_TERMINAL=1`. For example, launch nikcli from the repository root with:

```bash
terminal-control start tui-check \
  --host opentui \
  --cols 112 \
  --rows 34 \
  --record /tmp/tui-check.termctrl \
  -- env NIKCLI_TERMINAL=1 bun run --cwd packages/nikcli dev
```

Wait for a visible application-specific string such as `Ask anything` before sending input. Seeing only the Bun launcher line does not prove that OpenTUI rendered.

Use `wait` after input instead of fixed sleeps. Use `show` for the visible screen and `logs` only for normal-screen scrollback.

Always stop named sessions, including after failures. Treat recordings and terminal input as sensitive.

## Produce PR Evidence

After stopping the session, create the evidence bundle:

```bash
terminal-control bundle \
  --recording /tmp/tui-check.termctrl \
  --out artifacts/tui/tui-check \
  --link-base artifacts/tui/tui-check \
  --include-recording \
  --result passed \
  --title "TUI verification" \
  --summary "The tested interaction completed successfully."
```

The bundle contains `screen.txt`, `screen.json`, `screen.svg`, `screen.png`, `demo.mp4`, `preview.gif`, `recording.termctrl`, `manifest.json`, and `pr.md`.

Retain the native raw `.termctrl` recording for requested TUI verifications in this workspace. It must come directly from the real PTY session launched with `--record`; never substitute a fixture, reconstructed transcript, or synthetic shell demo for the application under test. Use `pr.md` as the PR section; it embeds the GIF preview and links the full MP4 and raw recording.

Treat `recording.termctrl` as sensitive because it contains terminal output and input. Inspect it for credentials, tokens, personal data, and pasted secrets before publishing. If it contains sensitive material, keep it local and state why it was omitted from the PR.

The bundle command also prints an absolute `file://` GIF Markdown line. Include that exact line in the final assistant response so nikcli can render the local preview inline. Treat it as local-only output and never paste the `file://` URL into a pull request.

When the user explicitly requests PR evidence or the task is already operating on a pull request:

1. Write the bundle under a stable repository path such as `artifacts/tui/<check-name>`.
2. Inspect `screen.txt`, the preview, and the manifest for secrets.
3. Commit and push the safe generated evidence, including `recording.termctrl` when requested and secret-free.
4. Use a public `--link-base` for the pushed artifact directory when available, then append the contents of `pr.md` to the existing PR description without discarding its current content.

If no pull request exists, leave `pr.md` ready and report its path instead of creating unrelated remote state.

Inside the `/nikcli` GitHub Actions runner, always write the bundle below `artifacts/tui/`. Do not paste local `file://` preview links into the response. The runner validates the manifest and artifact hashes, refuses to create a PR when GIF, MP4, or raw recording is missing, commits the bundle, and adds an idempotent commit-addressed evidence section to the PR body.

If the test fails, still retain the final screen and video with `--result failed`, describe the observed failure accurately, and never report it as passed.

## Refine Video Timing

For a focused demo, create an edit plan using recorded markers and pass it with `--edit`:

```json
{
  "clips": [
    {
      "from": "ready",
      "to": "verified",
      "caption": "Terminal interaction verified",
      "speed": 1,
      "hold_ms": 1000
    }
  ]
}
```

Keep important text readable. Prefer a short, deliberate clip over a sped-up full session.
