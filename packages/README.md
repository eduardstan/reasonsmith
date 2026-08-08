# reasonsmith, in TypeScript

A renderer and a recording harness, not a re-implementation. The conformance engine — every pack,
every rung, every engine, every reason-deletion certificate — is the Python package in
`src/reasonsmith/`. The TypeScript tree here renders what the Python produces, and records itself
producing it. **There is exactly one place a duty is defined, and it is the Python.**

```
packages/
  tui/               the OpenTUI renderer; reads one JSON record over a subprocess
  terminal-control/  the recording harness; produces the .termctrl evidence files
  cli/               a thin launcher that starts the TUI binary
```

Install and run:

```sh
bun install
bun run typecheck   # turbo, every package
bun test            # turbo, every package
```

## What this build does

The TUI is one process. It spawns `python -m reasonsmith.cli check ... --json`, parses the record,
and renders it. There is no second copy of a pack, no second copy of an engine, no second copy of a
verdict: every box on the screen is something the Python said, over stdout, in a single call.

The recording harness (`terminal-control`) captures a TUI session into a `.termctrl` file and renders
it back to screenshots, GIFs, video, and a structured screen.json. The shipped `artifacts/tui/`
directory holds the recording, not its rendered outputs — those are release assets.

## What this build does not have

**Engines.** All four rungs the Python can reach (`proved`, `probed`, `recounted`, `observed`)
belong to the Python. The TUI never asks an engine a question. A run that the Python reports at
`proved` arrives at the TUI as `proved`; the TUI does not re-derive it.

**Packs.** No `.toml` is loaded in the TypeScript process. The TUI's report header carries whatever
the Python's run printed, and the active pack appears in the settings panel as `pack_id`.

**Systems.** No system under test is built in this build. A user supplies `--system <path.jsonl>`
or `--system-module <module:attr>` and the Python loads it.

**Audiences.** Five audience projections (`developer`, `deployer`, `auditor`, `regulator`,
`affected-individual`) are declared in `packages/tui/src/types/audiences.ts`. They are the same five
the Python ships, with the same flags, and they are passed to the Python through `--audience`. The
TUI does not implement its own projection logic for an audience it does not pass through; the
Python owns the projection and emits the projected report.

## The data contract

`reasonsmith check --json` emits the contract. One subprocess call, one parse, one render. The full
shape is documented in `packages/tui/src/types/schema.ts`, and the parser refuses anything whose
`schema_version` does not match. The fields it does not carry today (`verbatim_text`, the per-decision
deletion certificate identity) are listed in `packages/tui/src/types/detail-keys.ts` and stubbed in
the detail panel; the issues for them are on the Python side and the TUI will read them when they
land.

## What a reader must not break

- **No duty, rung, verdict, or spec is defined in TypeScript.** `rg -l "packs|Strength|verdict"
  packages/` returns nothing outside `packages/tui/src/types/`.
- **No statutory text lives in this repository twice.** `grep -rn "12 CFR\|GDPR Art\|Regulation B"
  packages/` returns nothing.
- **The TUI's only data path is the subprocess.** `runReasonsmith()` in
  `packages/tui/src/subprocess.ts` is the one place a Python interpreter is spawned.
- **A run that reports `not evaluated` renders visibly differently from one that reports
  `satisfied`.** The status bar, the verdict chip, and the detail page all carry that distinction,
  and the test in `packages/tui/src/index.test.ts` pins it.
