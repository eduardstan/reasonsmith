"""Tests holding `docs/refinement.md` to the packs it claims to cover.

What this module is for:
  `docs/refinement.md` is the record of how each shipped requirement was refined from a clause of
  law into a formal property, and of what that refinement deliberately did not capture. A record
  that silently falls behind the packs is worse than none: a reader would take the absence of a
  caveat for the absence of a gap. So the coverage is checked against the packs rather than
  trusted.

What a reader must not break:
  - The requirement set is read from `packs/*.toml` at test time, never restated here — the same
    discipline as `sut._table7_signals`. A hand-copied list would drift the moment a pack changed,
    which is precisely the drift this test exists to catch.
    Why this matters: a pack that gains a requirement must fail the build until the refinement
    record names it.
  - Coverage is checked in both directions. A row naming an id no pack ships is a caveat about a
    requirement nobody runs.
"""

from __future__ import annotations

import re
from pathlib import Path

from reasonsmith.spec import list_packs, load_pack

REPO_ROOT = Path(__file__).resolve().parent.parent
REFINEMENT = REPO_ROOT / "docs" / "refinement.md"

#: A backticked token in a table cell, e.g. ``gdpr_art22_1_automated_decision_prohibition``.
_CODE_SPAN = re.compile(r"`([^`]+)`")


def _document() -> str:
    assert REFINEMENT.is_file(), f"{REFINEMENT} does not exist"
    return REFINEMENT.read_text(encoding="utf-8")


def _shipped_requirement_ids() -> set[str]:
    """Every requirement id in every shipped pack, read from the packs themselves."""
    ids: list[str] = [req.id for name in list_packs() for req in load_pack(name).requirements]
    assert len(set(ids)) == len(ids), (
        "two shipped packs use the same requirement id, so one row of the refinement record "
        "would stand for both: " + ", ".join(sorted(i for i in ids if ids.count(i) > 1))
    )
    return set(ids)


def _documented_requirement_ids() -> set[str]:
    """The ids the record names, read from the first cell of each of its table rows.

    The first column is "the clause", and by convention it carries the requirement id as its only
    code span, so the mapping from row to requirement is machine-checkable rather than eyeballed.
    """
    documented: set[str] = set()
    for line in _document().splitlines():
        if not line.startswith("|"):
            continue
        first_cell = line.split("|")[1]
        documented.update(_CODE_SPAN.findall(first_cell))
    return documented


def test_the_refinement_record_covers_every_shipped_requirement():
    """A duty with no refinement row is an unrecorded leap from a clause to a formula."""
    shipped = _shipped_requirement_ids()
    documented = _documented_requirement_ids()

    missing = sorted(shipped - documented)
    assert not missing, (
        "docs/refinement.md does not cover shipped requirement(s): "
        + ", ".join(missing)
        + ". Add a row naming the clause, the duty, the property, and what it does not capture."
    )

    invented = sorted(documented - shipped)
    assert not invented, (
        "docs/refinement.md names requirement id(s) no pack ships: "
        + ", ".join(invented)
        + ". Remove the row, or restore the requirement."
    )


def test_the_refinement_record_names_the_decision_domain_gap():
    """The structural gap is the record's most load-bearing claim; it may not be dropped."""
    document = _document()
    assert "decision domain" in document
    assert "findings-nesyarena.md" in document


def test_the_refinement_record_is_linked_where_an_author_is_standing():
    """A record nobody finds does not change what anyone writes."""
    assert "docs/refinement.md" in (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_dir = REPO_ROOT / "docs"
    assert "refinement.md" in (docs_dir / "authoring-packs.md").read_text(encoding="utf-8")
    assert "refinement.md" in (docs_dir / "README.md").read_text(encoding="utf-8")
