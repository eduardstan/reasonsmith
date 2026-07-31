"""Holds the committed transcripts to the runs they claim to be.

What this module is for:
  `docs/example-output.md` says every block is stdout pasted unedited from a real run. This test is
  what makes that a checked claim: each ```sh command in the file is re-run and its stdout compared
  byte-for-byte against the ```text block underneath it.

What a reader must not break:
  - The pairing is positional: one ```sh block, then the ```text block it produced. Adding a text
    block with no command above it, or prose between the two fences, breaks the pairing rather than
    silently skipping a transcript.
  - Compare stdout verbatim. Normalising whitespace or matching on substrings would let a stale
    transcript pass, which is the one failure this test exists to catch.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_OUTPUT = REPO_ROOT / "docs" / "example-output.md"

PAIR_RE = re.compile(r"```sh\n(.*?)\n```\n\n```text\n(.*?)```\n", re.DOTALL)


def test_committed_transcripts_are_the_real_stdout():
    pairs = PAIR_RE.findall(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
    assert len(pairs) == 3, "expected three command/transcript pairs in docs/example-output.md"

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    for command, transcript in pairs:
        run = subprocess.run(
            command.replace("python ", f"{sys.executable} ", 1),
            shell=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        assert run.returncode == 0, f"{command} exited {run.returncode}: {run.stderr}"
        assert (
            run.stdout.replace("\r\n", "\n") == transcript.replace("\r\n", "\n")
        ), f"transcript for `{command}` is stale"
