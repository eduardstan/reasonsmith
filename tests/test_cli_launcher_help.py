"""The TypeScript launcher's help must advertise the command surface the Python CLI really has.

What this module is for:
  - `packages/cli/src/index.ts` tells the user that the Python `reasonsmith` CLI "carries the
    full command surface" and lists the commands by name. That list once advertised
    `list-packs` and `serve`, which the installed parser rejects with `invalid choice` — a
    user who trusted the help was sent straight into an error (issue #257). Deleting the two
    stale names fixes the day; this test fixes the class: the advertised set is held equal to
    the parser's real subcommand choices, so the two cannot drift apart silently again.
  - The real set is read from the parser's own `--help` output — the `{init,check,...}`
    metavar argparse prints in the usage line — never from a hand-copied list, so a command
    added to or removed from `src/reasonsmith/cli.py` is covered the day it lands.

What a reader must not break:
  - The advertised set is extracted only from the HELP text's "full command surface (...)"
    parenthetical, matched across the string-literal joins the launcher source wraps it in.
    The module docstring of `index.ts` names the same commands as prose; the HELP text is
    what the user is shown, so it is what this guard holds.
  - The compiled launcher binary is built from this same source by `bun build --compile`, so
    holding the source HELP to the parser holds the compiled launcher's help to it too —
    there is no second copy of the list to guard.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from reasonsmith import cli

LAUNCHER_SOURCE = (
    Path(__file__).resolve().parent.parent / "packages" / "cli" / "src" / "index.ts"
)


def _real_command_surface(capsys: pytest.CaptureFixture[str]) -> set[str]:
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    match = re.search(r"\{([^}]*)\}", out)
    assert match is not None, "argparse printed no {cmd,...} metavar in --help"
    return set(match.group(1).split(","))


def _advertised_command_surface() -> set[str]:
    text = LAUNCHER_SOURCE.read_text(encoding="utf-8")
    match = re.search(r"full command surface \(([^)]*)\)", text)
    assert match is not None, "launcher HELP no longer names the command surface"
    return set(re.findall(r"`([^`]+)`", match.group(1)))


def test_launcher_help_matches_the_real_command_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _advertised_command_surface() == _real_command_surface(capsys)
