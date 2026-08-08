#!/usr/bin/env bash
# Record the reasonsmith OpenTUI TUI with terminal-control and produce PR evidence.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/artifacts/tui/tui-check}"
RECORD="/tmp/reasonsmith-tui-check.termctrl"
TC="bun run --cwd $ROOT/packages/terminal-control control --"

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
  -- env REASONSMITH_TERMINAL=1 bun run --conditions=browser --cwd "$ROOT/packages/tui" ./src/index.tsx

echo "==> Waiting for TUI render"
$TC wait tui-check "TruncatingCreditSystem" --timeout 30000
$TC mark tui-check ready

echo "==> Open detail (violated finding)"
$TC send tui-check down down down enter
$TC wait tui-check "clause" --timeout 10000
$TC mark tui-check detail

echo "==> Cycle audience (auditor → regulator)"
$TC send tui-check text:a
$TC wait tui-check "regulator" --timeout 5000

echo "==> Limits via leader key (ctrl+x l)"
$TC send tui-check ctrl-x text:l
$TC wait tui-check "LIMITS OF THIS REPORT" --timeout 10000
$TC mark tui-check limits

echo "==> Packs picker"
$TC send tui-check escape text:p
$TC wait tui-check "Conformance packs" --timeout 5000
$TC send tui-check escape
$TC mark tui-check packs

echo "==> Theme cycle"
$TC send tui-check text:t
$TC mark tui-check theme

echo "==> Command palette"
$TC send tui-check ctrl-p
$TC wait tui-check "Command palette" --timeout 5000
$TC send tui-check text:theme enter
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
  --title "Reasonsmith enterprise TUI verification" \
  --summary "OpenTUI enterprise dashboard: leader key, palettes, status bar, mouse, keyboard (Kitty), full route navigation — verified via terminal-control."

echo "==> Done"
ls -la "$OUT"
