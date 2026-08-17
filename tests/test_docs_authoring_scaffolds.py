"""Executes every command `docs/authoring-scaffolds.md` shows, in CI, on every platform.

What this module is for:
  `docs/authoring-scaffolds.md` is the walkthrough from `reasonsmith init` to an installed,
  entry-point-discovered pack and engine (issue #238). A walkthrough is only worth anything while
  the commands it prints are the commands that work, so each ```sh block on the page is run in a
  temporary directory and each ```text block is compared byte-for-byte against the real stdout —
  the same pairing `test_docs_adopting.py` uses for its page. The pack half ends in
  `validate-pack demo-pack` resolving through the installed `reasonsmith.packs` entry point, and
  the engine half in `verify-engine demo-engine` through `reasonsmith.engines`: the install and
  discovery steps the page exists to teach are the steps this module exercises.

What a reader must not break:
  - The pairing is positional: an ```sh block followed by a ```text block commits that text as the
    command's real stdout, compared byte-for-byte. The two `pip install -e` blocks are followed by
    no ```text block — pip's progress output is pip's own and varies by release, so the page says
    so in prose and this module asserts only their exit codes. Every other command's transcript is
    pinned.
  - The page's one ```toml block is the edited `pack.toml`, written over the scaffold's
    placeholder before the validation commands run — the same pattern as the ```jsonl blocks in
    `test_docs_adopting.py`, and for the same reason: a heredoc is a Unix construct and these
    commands must run on Windows too.
  - The installs are real `pip install -e` runs into the current environment, because
    entry-point discovery is the behaviour under test and a faked `.dist-info` would not prove the
    page's commands work. Both distributions are uninstalled in a `finally` so nothing outlives
    the test; `test_engine_plugins.py`'s dist-info pattern was rejected here precisely because the
    page's promise is that these commands, as printed, work.
  - Commands run with `PYTHONIOENCODING=utf-8`: the `verify-engine` transcript names Beyer &
    Strejček, and a cp1252 console turns that into a `UnicodeEncodeError` — the same Windows
    failure `test_docs_adopting.py` sets the variable for.
  - A ```text block may carry `<!-- ... -->` annotation lines (the citation-key registry in
    `test_docs_formal.py` splits on blank lines, so the key for a source the quoted output names
    must sit inside the transcript). Annotations are stripped before the byte-for-byte
    comparison; they are documentation markup, never part of the pinned stdout.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE = REPO_ROOT / "docs" / "authoring-scaffolds.md"

#: Every fenced block on the page, in order, as (language, body). A `toml` block is the edited
#: pack file the commands under it validate; an `sh` block is a command; a `text` block is the
#: pinned stdout of the `sh` block before it.
BLOCK_RE = re.compile(r"```(sh|text|toml)\n(.*?)```\n", re.DOTALL)

#: Documentation annotations embedded in a transcript — never part of the command's real stdout.
ANNOTATION_RE = re.compile(r"^<!-- .* -->\n", re.MULTILINE)

#: The page's block sequence: init, transcript, the edited pack, validate by path, transcript,
#: install (unpinned output), validate by name, transcript, then the same shape for the engine.
EXPECTED_LANGUAGES = [
    "sh", "text", "toml", "sh", "text", "sh", "sh", "text", "sh", "text", "sh", "sh", "text",
]


def _blocks() -> list[tuple[str, str]]:
    return BLOCK_RE.findall(PAGE.read_text(encoding="utf-8"))


def test_every_command_on_the_page_runs_and_every_transcript_is_real(tmp_path):
    blocks = _blocks()
    assert [lang for lang, _ in blocks] == EXPECTED_LANGUAGES, (
        "docs/authoring-scaffolds.md no longer reads as the command/transcript sequence this "
        "module executes"
    )

    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "PYTHONIOENCODING": "utf-8",
        # See test_docs_adopting.py: a coverage-measured subprocess in a temporary directory
        # finds no pyproject.toml without this and moves the project total.
        "COVERAGE_RCFILE": str(REPO_ROOT / "pyproject.toml"),
    }

    try:
        for index, (language, body) in enumerate(blocks):
            if language == "toml":
                edited = tmp_path / "demo-pack" / "src" / "demo_pack" / "pack.toml"
                edited.write_text(body, encoding="utf-8")
                continue
            if language != "sh":
                continue
            command = body.rstrip("\n")
            run = subprocess.run(
                command.replace("python ", f"{sys.executable} ", 1),
                shell=True,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
            )
            assert run.returncode == 0, f"{command} exited {run.returncode}: {run.stderr}"
            followed_by_text = (
                index + 1 < len(blocks) and blocks[index + 1][0] == "text"
            )
            if followed_by_text:
                transcript = ANNOTATION_RE.sub("", blocks[index + 1][1])
                assert (
                    run.stdout.replace("\r\n", "\n") == transcript.replace("\r\n", "\n")
                ), f"transcript for `{command}` is stale"
    finally:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "-q", "demo-pack", "demo-engine"],
            capture_output=True,
        )


def test_no_command_on_the_page_is_unix_only():
    """The walkthrough's commands run on Windows too — the same guard adopting.md's page has.

    A heredoc or a pipe in an ```sh block is a recipe that fails under cmd.exe; the page shows
    files the reader saves as fenced blocks instead. Stated on the constructs rather than the
    platform so it fails on the machine an author is actually using.
    """
    unix_only = ("<<", "cat ", "$(", "&&", "|", ";", "'", "export ")
    for language, body in _blocks():
        if language != "sh":
            continue
        for construct in unix_only:
            assert construct not in body, (
                f"docs/authoring-scaffolds.md runs `{body.strip()}`, which uses {construct!r} — "
                "a shell construct that does not run under cmd.exe. Every command on the page "
                "must be a plain invocation."
            )
