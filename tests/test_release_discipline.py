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
  - The counts the README and ROADMAP state for what this tree ships — the README's pack and
    engine counts, ROADMAP's "Current state, for scale" line, and the same claims where the
    prose restates them spelled out ("Five packs", "Seven engines", "twenty-eight shipped
    requirements", `docs/what-this-does-not-do.md`'s "Five packs ship, with 28 requirements
    between them") — are held to what the package actually ships. A count in prose rots
    silently: the README once claimed "four packs" and "four engines" while five and seven
    shipped, and ROADMAP's scale line went stale twice in one day before anyone noticed. The
    number is matched as the sentence writes it — digits or spelled out — so a digit-only test
    would miss the spelled half of that drift.

What a reader must not break:
  - The markdown sweep reads the tracked set from `git ls-files`, never a hand-copied list — the
    same discipline as the pack-derived lists elsewhere in the suite. A new markdown file is
    covered the day it is added.
  - The counts are derived at test time, never restated: packs from `spec.list_packs()`, the
    same list `validate-pack` reads; engines from the modules under `engines/` — never
    `BUILTIN_ENGINE_NAMES` alone, which once missed a shipped entry, and the two are asserted
    to agree; requirements from the packs' own requirement lists.
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
from typing import NamedTuple

from reasonsmith.plugins import BUILTIN_ENGINE_NAMES
from reasonsmith.spec import list_packs, load_pack

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


# ---------------------------------------------------------------------------
# Prose counts held to the shipped tree
# ---------------------------------------------------------------------------

_ONES = ("", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_TEENS = (
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def _cardinal_word(number: int) -> str:
    if number < 10:
        return _ONES[number]
    if number < 20:
        return _TEENS[number - 10]
    tens, unit = divmod(number, 10)
    return _TENS[tens] if unit == 0 else f"{_TENS[tens]}-{_ONES[unit]}"


#: Number words for 1..99, both directions, so a count claim is matched as the sentence writes it
#: — spelled out or in digits. A digit-only test would have missed the spelled "four packs" and
#: "four engines" both documents once claimed.
_CARDINAL_VALUE = {_cardinal_word(n): n for n in range(1, 100)}
_CARDINAL_ALT = "|".join(_CARDINAL_VALUE)


#: A count claim in prose: a number (cardinal word or digits), an optional "shipped", and one of
#: the countable nouns the documents state counts for. Plural only, on purpose: "one engine at a
#: time" and "one row per requirement" are the singular phrases of these documents and are not
#: claims about the shipped tree, while every count pinned here is written in the plural.
_COUNTED_CLAIM = re.compile(
    rf"\b(?P<number>{_CARDINAL_ALT}|\d+)\s+(?:shipped\s+)?"
    r"(?P<noun>packs|engines|requirements)\b",
    re.IGNORECASE,
)

#: `docs/what-this-does-not-do.md`'s one inventory sentence — "Five packs ship, with 28
#: requirements between them" — which restates the shipped pack and requirement counts and would
#: rot the same way the README's did. The document's other "N packs" mentions ("three packs")
#: describe the nesyarena runs, which genuinely use three packs, so only this sentence is pinned.
_SHIPPED_INVENTORY = re.compile(
    rf"\b(?P<packs>{_CARDINAL_ALT}|\d+)\s+packs\s+ship,?\s+with\s+"
    rf"(?P<reqs>{_CARDINAL_ALT}|\d+)\s+requirements\b",
    re.IGNORECASE,
)


class _Claim(NamedTuple):
    line: int
    number: int
    noun: str
    as_written: str


def _claim_number(token: str) -> int:
    token = token.lower()
    return _CARDINAL_VALUE[token] if token in _CARDINAL_VALUE else int(token)


def _counted_claims(text: str) -> list[_Claim]:
    """Every plural count claim in `text`, with its number read as written (digits or words)."""
    claims: list[_Claim] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _COUNTED_CLAIM.finditer(line):
            claims.append(
                _Claim(
                    lineno,
                    _claim_number(match.group("number")),
                    match.group("noun"),
                    match.group(0),
                )
            )
    return claims


def _shipped_pack_names() -> list[str]:
    """The shipped pack names, read from the packs directory exactly as `validate-pack` reads
    them — never restated here."""
    return list_packs()


def _shipped_engine_modules() -> set[str]:
    """The engine modules under `src/reasonsmith/engines/`, the ground truth for how many engines
    ship. `BUILTIN_ENGINE_NAMES` once missed an entry of its own, so the directory — not the
    tuple — decides how many engines the documents may claim."""
    engines_dir = REPO_ROOT / "src" / "reasonsmith" / "engines"
    return {p.stem for p in engines_dir.glob("*.py") if p.stem != "__init__"}


def _shipped_counts() -> dict[str, tuple[int, str]]:
    """Per countable noun, (count, names) derived from the shipped tree."""
    packs = _shipped_pack_names()
    engines = sorted(_shipped_engine_modules())
    per_pack = [f"{name}: {len(load_pack(name).requirements)}" for name in packs]
    return {
        "packs": (len(packs), ", ".join(packs)),
        "engines": (len(engines), ", ".join(engines)),
        "requirements": (
            sum(len(load_pack(name).requirements) for name in packs),
            ", ".join(per_pack),
        ),
    }


def _count_offenders(
    path: Path,
    expected: dict[str, tuple[int, str]],
    shipped_only: tuple[str, ...] = (),
) -> list[str]:
    """One message per count claim in `path` that disagrees with the shipped tree, plus one if a
    noun `expected` knows is never claimed at all.

    A claim is only an offender when its noun is in `expected` and, for a noun in `shipped_only`,
    the claim explicitly says "shipped": a demo transcript's per-run counts ("5 requirements")
    are not claims about the shipped tree, while "twenty-eight shipped requirements" is one.
    """
    text = path.read_text(encoding="utf-8")
    claims = _counted_claims(text)
    offenders: list[str] = []
    for noun, (count, names) in expected.items():
        if not any(
            c.noun == noun and (noun not in shipped_only or "shipped" in c.as_written)
            for c in claims
        ):
            offenders.append(
                f"{path.relative_to(REPO_ROOT)} states no {noun} count for the shipped tree — "
                f"restore the sentence stating {count} {noun}: {names}"
            )
    for claim in claims:
        if claim.noun not in expected:
            continue
        if claim.noun in shipped_only and "shipped" not in claim.as_written:
            continue
        count, names = expected[claim.noun]
        if claim.number != count:
            offenders.append(
                f"{path.relative_to(REPO_ROOT)}:{claim.line} claims {claim.as_written!r} — that "
                f"is {claim.number} {claim.noun}, but the tree ships {count}: {names}"
            )
    return offenders


def test_builtin_engine_names_cover_every_shipped_engine_module():
    """`plugins.BUILTIN_ENGINE_NAMES` — the names an installed plug-in may not shadow — is
    exactly the set of modules under `engines/`. The tuple once silently missed a shipped entry;
    the directory is the ground truth, so the two must agree in both directions: a reserved name
    with no module would reserve nothing real, and a module with no reserved name would be a
    shipped engine no plug-in is refused on."""
    modules = _shipped_engine_modules()
    builtins = set(BUILTIN_ENGINE_NAMES)
    assert builtins == modules, (
        f"plugins.BUILTIN_ENGINE_NAMES {sorted(builtins)} disagrees with the modules shipped "
        f"under src/reasonsmith/engines/ {sorted(modules)} — change the tuple in the same "
        "change as the module."
    )


def test_readme_pack_count_matches_the_shipped_packs():
    """README's pack counts — "Five packs ship", "all five packs", "one of the five shipped
    packs" — are held to `spec.list_packs()`, the same list `validate-pack` reads. The number is
    matched as the sentence writes it, spelled out or in digits, so a drift like the "four packs"
    the README once claimed is caught either way."""
    expected = {"packs": _shipped_counts()["packs"]}
    offenders = _count_offenders(REPO_ROOT / "README.md", expected)
    assert not offenders, (
        "README.md states a pack count that disagrees with what ships — the count is derived "
        "from src/reasonsmith/packs/ at test time, never restated:\n" + "\n".join(offenders)
    )


def test_readme_engine_count_matches_the_shipped_engines():
    """README's "Seven engines ship here" is held to the modules under `engines/` — not to
    `BUILTIN_ENGINE_NAMES` alone, which once missed an entry of its own; the agreement test above
    pins the tuple to the modules, and this test pins the prose to the same ground truth."""
    expected = {"engines": _shipped_counts()["engines"]}
    offenders = _count_offenders(REPO_ROOT / "README.md", expected)
    assert not offenders, (
        "README.md states an engine count that disagrees with what ships — the count is derived "
        "from src/reasonsmith/engines/ at test time, never restated:\n" + "\n".join(offenders)
    )


def test_roadmap_scale_line_matches_the_shipped_tree():
    """ROADMAP's "Current state, for scale" line — "5 packs, 28 requirements, 7 engines" — tells
    a reader what this project currently is, and it went stale twice in one day before anyone
    noticed. All three numbers are held to the shipped tree, spelled out or in digits as the line
    writes them; the same claims where ROADMAP restates them ("Five packs now ship",
    "twenty-eight shipped requirements") are guarded too."""
    offenders = _count_offenders(REPO_ROOT / "ROADMAP.md", _shipped_counts())
    assert not offenders, (
        "ROADMAP.md states a count that disagrees with what ships — the scale line is derived "
        "from the packs and engines at test time, never restated:\n" + "\n".join(offenders)
    )


def test_readme_shipped_requirement_count_matches_the_packs():
    """README's one shipped-requirement claim — "twenty-eight shipped requirements" — is held to
    the total across the packs. The rest of README's requirement counts ("5 requirements",
    "6 requirements") are per-run transcript numbers, not claims about the shipped tree, and are
    deliberately not pinned here."""
    expected = {"requirements": _shipped_counts()["requirements"]}
    offenders = _count_offenders(
        REPO_ROOT / "README.md", expected, shipped_only=("requirements",)
    )
    assert not offenders, (
        "README.md states a shipped-requirement count that disagrees with what ships — the total "
        "is derived from the packs at test time, never restated:\n" + "\n".join(offenders)
    )


def test_what_this_does_not_do_inventory_matches_the_shipped_packs():
    """`docs/what-this-does-not-do.md`'s inventory sentence — "Five packs ship, with 28
    requirements between them" — restates the same shipped counts as the README and ROADMAP and
    is held to the same derived numbers. The document's other "N packs" mentions ("three packs")
    describe the nesyarena runs, which genuinely use three packs, so only the inventory sentence
    is pinned."""
    doc = (REPO_ROOT / "docs" / "what-this-does-not-do.md").read_text(encoding="utf-8")
    shipped = _shipped_counts()
    real_packs = shipped["packs"][0]
    real_reqs, per_pack = shipped["requirements"]
    offenders: list[str] = []
    for lineno, line in enumerate(doc.splitlines(), start=1):
        for match in _SHIPPED_INVENTORY.finditer(line):
            claimed_packs = _claim_number(match.group("packs"))
            claimed_reqs = _claim_number(match.group("reqs"))
            if (claimed_packs, claimed_reqs) != (real_packs, real_reqs):
                offenders.append(
                    f"docs/what-this-does-not-do.md:{lineno} claims {claimed_packs} packs with "
                    f"{claimed_reqs} requirements, but the tree ships {real_packs} packs with "
                    f"{real_reqs} requirements ({per_pack})"
                )
    if not any(_SHIPPED_INVENTORY.search(line) for line in doc.splitlines()):
        offenders.append(
            "docs/what-this-does-not-do.md states no pack-and-requirement inventory sentence "
            f"— restore the sentence stating {real_packs} packs with {real_reqs} requirements"
        )
    assert not offenders, (
        "docs/what-this-does-not-do.md states a count that disagrees with what ships — the "
        "inventory is derived from the packs at test time, never restated:\n"
        + "\n".join(offenders)
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
