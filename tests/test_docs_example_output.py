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
  - The header's line count and `md5sum` are checked against the demo block and against RESULTS.md.
    Regenerating a transcript without updating them is what makes the two files stop matching.
  - The header names the reasonsmith version the file was produced with, and
    `test_doc_names_the_version_it_was_generated_with` holds that note to
    `reasonsmith.__version__` the way the transcripts are held to real stdout. A reader who
    installed a release must be able to tell a stale page from a broken install; a note that
    named a stale number would be the same defect in another shape.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_OUTPUT = REPO_ROOT / "docs" / "example-output.md"
RESULTS = REPO_ROOT / "RESULTS.md"

PAIR_RE = re.compile(r"```sh\n(.*?)\n```\n\n```text\n(.*?)```\n", re.DOTALL)
HEADER_RE = re.compile(r"\*\*Demo transcript:\*\* (\d+) lines, `md5sum` `([0-9a-f]{32})`")


def test_doc_names_the_version_it_was_generated_with():
    """The file says which reasonsmith produced it, and the pin holds that to `__version__`.

    Every command on the page runs against an installed release, while these transcripts were
    generated from this tree — which is ahead of the last release. The note exists so a reader
    whose output differs can tell a stale page from a broken install, so the number in it is
    only worth anything while it is the version the tree actually is. It is asserted rather
    than trusted, the same way each transcript below is asserted rather than trusted.
    """
    from reasonsmith import __version__

    text = EXAMPLE_OUTPUT.read_text(encoding="utf-8")
    assert f"reasonsmith `{__version__}`" in text, (
        "docs/example-output.md must state it was produced with reasonsmith "
        f"`{__version__}`; regenerate the note when the version changes"
    )


def test_committed_transcripts_are_the_real_stdout():
    text = EXAMPLE_OUTPUT.read_text(encoding="utf-8")
    pairs = PAIR_RE.findall(text)
    assert len(pairs) == 3, "expected three command/transcript pairs in docs/example-output.md"

    header = HEADER_RE.search(text)
    assert header, "docs/example-output.md header no longer states the demo line count and md5sum"
    demo = pairs[0][1]
    demo_md5 = hashlib.md5(demo.encode("utf-8")).hexdigest()
    assert int(header[1]) == len(demo.splitlines()), "header line count is stale"
    assert header[2] == demo_md5, "header md5sum is stale"
    results = RESULTS.read_text(encoding="utf-8")
    assert demo_md5 in results, "RESULTS.md no longer reports the demo transcript's md5sum"
    assert f"{len(demo.splitlines())} lines" in results, "RESULTS.md line count is stale"

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    for command, transcript in pairs:
        run = subprocess.run(
            command.replace("python ", f"{sys.executable} ", 1),
            shell=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        assert run.returncode == 0, f"{command} exited {run.returncode}: {run.stderr}"
        assert (
            run.stdout.replace("\r\n", "\n") == transcript.replace("\r\n", "\n")
        ), f"transcript for `{command}` is stale"
