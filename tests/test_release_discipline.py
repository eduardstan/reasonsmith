"""Tests enforcing the release discipline: linked references and a version that travels.

What this module is for:
  - Every bare `#NN` pull-request or issue reference in tracked markdown must be a link, so a
    reader can follow it. Commits are squash-merged with `(#NN)` subjects, so the reference
    class is wide and mechanical, and a bare reference is a merge that silently strands a link
    nobody can follow.
  - `version` in `pyproject.toml`, the topmost released heading in `CHANGELOG.md`,
    `__version__` in `src/reasonsmith/__init__.py` and `version` in `CITATION.cff` must agree:
    the changelog is the release record and the tree's version is the release number. One
    number kept in several places drifts by omission, and a drift is how a changelog describes
    a release the tree never was. `CITATION.cff` is the fourth place and was the one this guard
    originally missed — it was already stale when the first three were locked together.
  - README.md and AGENTS.md never name a `reasonsmith` release number: the publication claim
    lives once, in the README's *Dependencies & PyPI* paragraph, without a version (the PyPI
    project page names the current one), and AGENTS.md points at the README. A number written
    in either document goes stale at the next release — both once claimed 0.2.0 while 0.6.0
    was current.

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
  - `CITATION.cff` is read with a regex over its one top-level `version:` line, not a YAML
    parser: one field is not worth a dependency this package otherwise does not have. The
    pattern is anchored at column zero so `cff-version:` and the indented fields under
    `preferred-citation:` cannot match it.
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


#: A `reasonsmith` mention immediately followed by a release number — the shape of a stale
#: PyPI claim ("`reasonsmith` 0.2.0 is published on PyPI"). A `v` prefix is the same claim in
#: another shape ("`reasonsmith` v0.6.0") and is caught too. A pinned install like
#: ``reasonsmith==0.6.0`` is a different shape and not what this guards against.
_REASONS_MITH_VERSION_CLAIM = re.compile(r"reasonsmith`?\s*v?\d+\.\d+\.\d+")


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


def test_markdown_names_no_reasonsmith_release():
    """README.md and AGENTS.md never name a `reasonsmith` release number. The README's
    *Dependencies & PyPI* paragraph owns the publication claim and deliberately names no
    version (the PyPI page does); AGENTS.md points at the README rather than restating one.
    A number in either document goes stale at the next release, as the 0.2.0 both once
    claimed did by 0.6.0 — a `v` prefix is the same claim in another shape and is caught
    too."""
    offenders: list[str] = []
    for path in (REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _REASONS_MITH_VERSION_CLAIM.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "README.md/AGENTS.md must not name a reasonsmith release number — `pip install "
        "reasonsmith` and the PyPI project page carry that fact, and a version written here "
        "goes stale at the next release:\n" + "\n".join(offenders)
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


def _citation_version() -> str:
    """The one top-level `version:` in `CITATION.cff`, read without a YAML dependency."""
    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r'^version:\s*"?(\d+\.\d+\.\d+)"?\s*$', citation, re.MULTILINE)
    assert match, "CITATION.cff has no top-level `version:` line"
    return match.group(1)


def test_pyproject_changelog_and_package_version_agree():
    """The tree's version and the changelog's newest release are the same number, and so are
    the package's own `__version__` literal and `CITATION.cff` — four places, one number,
    nothing to drift."""
    pyproject_version = _pyproject_version()
    changelog_version = _topmost_released_version()
    assert pyproject_version == changelog_version, (
        f"pyproject.toml version {pyproject_version} disagrees with CHANGELOG.md's topmost "
        f"released heading [{changelog_version}]. Bump both in the same change."
    )
    import reasonsmith

    assert reasonsmith.__version__ == pyproject_version, (
        f"src/reasonsmith/__init__.py __version__ {reasonsmith.__version__} disagrees with "
        f"pyproject.toml version {pyproject_version}. Bump all four in the same change."
    )

    citation_version = _citation_version()
    assert citation_version == pyproject_version, (
        f"CITATION.cff version {citation_version} disagrees with pyproject.toml version "
        f"{pyproject_version}. Bump all four in the same change."
    )
