"""Tests enforcing the release discipline: linked references and a version that travels.

What this module is for:
  - Every bare `#NN` pull-request or issue reference in tracked markdown must be a link, so a
    reader can follow it. Commits are squash-merged with `(#NN)` subjects, so the reference
    class is wide and mechanical, and a bare reference is a merge that silently strands a link
    nobody can follow.
  - `version` in `pyproject.toml`, the topmost released heading in `CHANGELOG.md`, and
    `__version__` in `src/reasonsmith/__init__.py` must agree: the changelog is the release
    record and the tree's version is the release number. One number kept in several places
    drifts by omission, and a drift is how a changelog describes a release the tree never was.

What a reader must not break:
  - The markdown sweep reads the tracked set from `git ls-files`, never a hand-copied list — the
    same discipline as the pack-derived lists elsewhere in the suite. A new markdown file is
    covered the day it is added.
  - The version comparison reads the number from the TOML with `tomllib` (standard library on
    3.11+, the project's floor), skips `[Unreleased]`, and holds `__version__` in
    `src/reasonsmith/__init__.py` to the same value. `__version__` is a literal guarded here
    rather than derived from installed metadata: deriving would report whatever distribution
    happens to be installed — a stale PyPI release, or none at all in the no-install import
    setup `tests/conftest.py` exists for — instead of the tree's own number.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A fenced code block, stripped whole so `#NN` inside it is not read as a reference, while
#: keeping the newlines so reported line numbers stay true.
_FENCED_BLOCK = re.compile(r"```.*?```", re.DOTALL)
#: An inline code span, likewise not a reference.
_INLINE_CODE = re.compile(r"`[^`]*`")
#: A bare `#NN` — not inside a link label `[#NN](...)`, not an anchor `](#NN-something)`, and
#: not a hex colour like `#1a2b3c` (the digits must end at a non-word boundary).
_BARE_REFERENCE = re.compile(r"(?<!\[)(?<!\]\()#(\d+)(?!\w)")


def _tracked_markdown_files() -> list[Path]:
    """Every markdown file git tracks, so a new file is covered the day it lands."""
    listing = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / name for name in listing.stdout.splitlines()]


def _bare_references(text: str) -> list[tuple[int, str]]:
    """(line, number) pairs for bare `#NN` outside code blocks, inline code and link labels."""
    text = _FENCED_BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    text = _INLINE_CODE.sub("", text)
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _BARE_REFERENCE.finditer(line):
            found.append((lineno, match.group(1)))
    return found


def test_no_bare_reference_in_tracked_markdown():
    """A bare `#NN` outside code and link labels is a reference nobody can follow."""
    offenders: list[str] = []
    for path in _tracked_markdown_files():
        for lineno, number in _bare_references(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: #{number}")
    assert not offenders, (
        "tracked markdown has bare pull-request/issue reference(s) — link them as "
        "[#N](https://github.com/eduardstan/reasonsmith/pull/N):\n" + "\n".join(offenders)
    )


def _pyproject_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def _topmost_released_version() -> str:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for line in changelog.splitlines():
        match = re.match(r"^## \[(\d+\.\d+\.\d+)\]", line)
        if match:
            return match.group(1)
    raise AssertionError("CHANGELOG.md has no released (non-[Unreleased]) version heading")


def test_pyproject_changelog_and_package_version_agree():
    """The tree's version and the changelog's newest release are the same number, and so is
    the package's own `__version__` literal — three places, one number, nothing to drift."""
    pyproject_version = _pyproject_version()
    changelog_version = _topmost_released_version()
    assert pyproject_version == changelog_version, (
        f"pyproject.toml version {pyproject_version} disagrees with CHANGELOG.md's topmost "
        f"released heading [{changelog_version}]. Bump both in the same change."
    )
    import reasonsmith

    assert reasonsmith.__version__ == pyproject_version, (
        f"src/reasonsmith/__init__.py __version__ {reasonsmith.__version__} disagrees with "
        f"pyproject.toml version {pyproject_version}. Bump all three in the same change."
    )
