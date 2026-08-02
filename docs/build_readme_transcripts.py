"""Regenerates the command transcripts committed in `README.md`.

What this module is for:
  The README's conformance-check block is CLI stdout pasted unedited, and it went stale once
  already. The ad-hoc helper that produced it located its target by matching the command text; the
  command later gained a `--system-domain` flag, the pattern matched nothing, and the substitution
  reported success having changed nothing. A regenerator that reports success when it substituted
  nothing is worse than the stale paragraph it leaves behind, because the next person believes it.
  This one raises instead, and writes nothing when it does.

  Run: `python docs/build_readme_transcripts.py`

What a reader must not break:
  - Every command in `TRANSCRIPTS` must match exactly one ```sh``` block followed by exactly one
    ```text``` block, and the substitutions must number exactly as many as `TRANSCRIPTS` does.
    Anything else raises and the README is left untouched.
    Why this matters: this is the defect the script exists to make impossible. A silent no-op
    leaves the project's front page showing a verdict the tool no longer prints, with the command
    that disproves it printed directly above.
  - A transcript is the CLI's own stdout for the command as the README writes it, captured and not
    edited afterwards.
    Why this matters: the command beside the block is a claim any reader can run. Adjusting a line
    by hand makes the block a description of the output rather than the output.
  - This script regenerates; it does not pin. `README.md` is deliberately not held byte-for-byte
    the way `test_docs_example_output.py` holds `docs/example-output.md`.
"""

from __future__ import annotations

import io
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reasonsmith.cli import main as cli_main  # noqa: E402

#: The command that reproduces the README's transcripts.
BUILD_COMMAND = "python docs/build_readme_transcripts.py"

README = ROOT / "README.md"

#: Every README command whose stdout is committed beneath it, spelled as the README spells it.
TRANSCRIPTS = (
    "reasonsmith check --system-module reasonsmith.demo:deployed_credit_system --pack ecoa "
    "--system-name TruncatingCreditSystem",
    "reasonsmith check --system docs/sample_decisions.jsonl --pack ecoa "
    "--system-name CreditScoringPipeline --system-domain consumer-credit",
)

#: 0 is a clean run and 2 is a run reporting a violation; both are transcripts worth committing.
REPORTING_EXIT_CODES = (0, 2)


def stdout_of(command: str) -> str:
    """The CLI's own stdout for `command`, run in-process from the repository root."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_main(command.split()[1:])
    if exit_code not in REPORTING_EXIT_CODES:
        raise RuntimeError(
            f"{command!r} exited {exit_code}, which is a usage or input error rather than a "
            "report, so no transcript was regenerated"
        )
    return buffer.getvalue().rstrip("\n")


def regenerate(text: str) -> str:
    """Return `text` with every command's transcript replaced by that command's own stdout."""
    substitutions = 0
    for command in TRANSCRIPTS:
        pattern = re.compile(
            "(?P<head>```sh\n" + re.escape(command) + "\n```\n\n```text\n)"
            ".*?(?P<tail>\n```\n)",
            re.DOTALL,
        )
        transcript = stdout_of(command)
        text, replaced = pattern.subn(
            lambda match, body=transcript: match.group("head") + body + match.group("tail"), text
        )
        if replaced != 1:
            raise RuntimeError(
                f"{command!r} matches {replaced} transcript block(s) in {README.name}, not 1. "
                "The command in the document and the command named here must be the same string, "
                "or the substitution silently changes nothing"
            )
        substitutions += replaced
    if substitutions != len(TRANSCRIPTS):
        raise RuntimeError(
            f"{substitutions} block(s) regenerated for {len(TRANSCRIPTS)} declared command(s)"
        )
    return text


def main() -> None:
    os.chdir(ROOT)
    README.write_text(regenerate(README.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
