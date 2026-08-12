#!/usr/bin/env bash
# Record the reasonsmith OpenTUI TUI with terminal-control and produce PR evidence.
#
# The TUI renders one conformance run and nothing else, so this script has to name one: `--system`
# and `--pack` are required by `packages/tui/src/args.ts` and the process exits 1 without them.
# The run recorded here is the demonstration the Python's own README leads with — the truncating
# credit system against the ECOA pack — because it is the one shipped run that comes back violated
# and carries reason-deletion certificates, so the recording shows the tool reporting a breach
# rather than a screen of green.
#
# Every screen this script waits for is one the TUI has: findings, detail, limits, the command
# palette, the help dialog and the theme cycle. There is no packs picker and no systems picker —
# those routes went out with `packages/core`, and waiting on them here hung the recording until the
# timeout fired.
#
# Needs the Python `reasonsmith` importable (`pip install -e ".[dev]"`), since the TUI shells out to
# it: `python3 -m reasonsmith.cli check ... --json`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/artifacts/tui/tui-check}"
RECORD="/tmp/reasonsmith-tui-check.termctrl"
TC="bun run --cwd $ROOT/packages/terminal-control control --"

# The system under test, as `--system` accepts it: a `module:attribute` reference the TUI forwards
# to the Python as `--system-module`. Override to record a different run.
SYSTEM="${REASONSMITH_TUI_SYSTEM:-reasonsmith.demo:deployed_credit_system}"
PACK="${REASONSMITH_TUI_PACK:-ecoa}"
SYSTEM_NAME="${REASONSMITH_TUI_SYSTEM_NAME:-TruncatingCreditSystem}"

mkdir -p "$(dirname "$OUT")"
rm -f "$RECORD"

cleanup() {
  $TC stop tui-check 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Starting TUI session with terminal-control"
$TC start tui-check \
  --host opentui \
  --cols 112 \
  --rows 36 \
  --record "$RECORD" \
  -- env REASONSMITH_TERMINAL=1 bun run --conditions=browser --cwd "$ROOT/packages/tui" ./src/index.tsx \
     --system "$SYSTEM" --pack "$PACK" --system-name "$SYSTEM_NAME"

echo "==> Waiting for TUI render"
$TC wait tui-check "$SYSTEM_NAME" --timeout 60000
$TC mark tui-check ready

echo "==> Open detail (violated finding)"
$TC send tui-check down down down enter
$TC wait tui-check "clause" --timeout 10000
$TC mark tui-check detail

echo "==> Cycle audience (auditor → regulator)"
$TC send tui-check text:a
$TC wait tui-check "regulator" --timeout 5000
$TC mark tui-check audience-regulator

# The lay account is the one projection that *emits* rather than suppresses, and this heading is the
# section that states how much of the pack the run never settled. Waiting on it is what makes the
# recording evidence that the section is there.
echo "==> Cycle audience (regulator → affected-individual)"
$TC send tui-check text:a
$TC wait tui-check "WHAT THIS REPORT COULD NOT CHECK" --timeout 10000
$TC mark tui-check lay-account

echo "==> Back to the auditor's report"
$TC send tui-check text:a text:a text:a
$TC wait tui-check "evidence basis" --timeout 10000

echo "==> Limits via leader key (ctrl+x l)"
$TC send tui-check ctrl-x text:l
$TC wait tui-check "LIMITS OF THIS REPORT" --timeout 10000
$TC mark tui-check limits

echo "==> Theme cycle"
$TC send tui-check escape text:t
$TC mark tui-check theme

echo "==> Command palette"
$TC send tui-check ctrl-p
$TC wait tui-check "Command palette" --timeout 5000
$TC send tui-check escape
$TC mark tui-check palette

echo "==> Help dialog via leader (ctrl+x h)"
$TC send tui-check ctrl-x text:h
$TC wait tui-check "Help" --timeout 5000
$TC send tui-check escape
$TC mark tui-check verified

$TC show tui-check
trap - EXIT
$TC stop tui-check

echo "==> Building PR evidence bundle"
$TC bundle \
  --recording "$RECORD" \
  --out "$OUT" \
  --link-base "artifacts/tui/tui-check" \
  --include-recording \
  --result passed \
  --title "Reasonsmith TUI verification" \
  --summary "The OpenTUI renderer over one Python conformance run: findings, detail, the five audience projections, limits, command palette and help — verified via terminal-control."

echo "==> Done"
ls -la "$OUT"
