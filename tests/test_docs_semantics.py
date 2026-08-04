"""Tests holding `docs/semantics.md` to the code and to its own claim-to-test map.

What this module is for:
  `docs/semantics.md` states what a reasonsmith verdict means, and every soundness claim in it
  names the test that fails if the claim becomes false. That discipline is worth nothing if the
  named tests can quietly disappear or be renamed, so the mapping is checked here rather than
  trusted: a test named in the document that no longer exists fails the build, which is what makes
  the document verifiable instead of aspirational.

What a reader must not break:
  - Every `test_*` name the document mentions must resolve to a test in this suite.
    Why this matters: a soundness claim whose enforcing test has been renamed away is a claim
    nothing checks, which is exactly the vague statement the document exists to avoid.
  - The lattice sentence in the document is compared against the order `Strength` defines.
    Why this matters: the ordering is the document's central claim about strength, and a reader
    must not have to check it against the code by eye.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from reasonsmith.report import _CATEGORY_LABELS
from reasonsmith.verdict import Strength

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
SEMANTICS = REPO_ROOT / "docs" / "semantics.md"

#: A `test_...` identifier as the document writes them, in backticks or bare. A name followed by
#: `.py` is a module the document is pointing at, not a claim's enforcing test.
_TEST_NAME = re.compile(r"\btest_[a-z0-9_]+\b(?!\.py)")


def _document() -> str:
    assert SEMANTICS.is_file(), f"{SEMANTICS} does not exist"
    return SEMANTICS.read_text(encoding="utf-8")


def _defined_test_names() -> set[str]:
    """Every test function name this suite defines, read from the sources rather than collected.

    Reading the files keeps this test independent of how pytest was invoked: a name check that
    only holds for the subset of the suite the current run collected would pass while the
    document pointed at a test nobody can run.
    """
    names: set[str] = set()
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                names.add(node.name)
    return names


def test_semantics_doc_is_linked_from_the_readmes():
    """A document nobody can find answers nobody's question."""
    assert SEMANTICS.is_file()
    assert "docs/semantics.md" in (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "semantics.md" in (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")


def test_every_test_named_in_the_semantics_doc_exists():
    """The claim-to-test map is the document's warrant; a dangling name voids it."""
    named = set(_TEST_NAME.findall(_document()))
    assert named, "the document names no test, so nothing in it is enforced"

    defined = _defined_test_names()
    missing = sorted(named - defined)
    assert not missing, (
        "docs/semantics.md names test(s) that do not exist in tests/: "
        + ", ".join(missing)
        + ". Rename the claim's test back, or cut the claim."
    )


def test_semantics_doc_states_the_lattice_the_code_defines():
    """The document's ordering sentence is generated from `Strength`, not written from memory."""
    ladder = " < ".join(s.value for s in sorted(Strength))
    assert ladder == "unattainable < observed < recounted < probed < proved"
    assert ladder in _document()


def test_the_four_unresolved_outcomes_are_four_distinct_report_categories():
    """`not applicable`, `unattainable`, `not evaluated` and `violated` may never be collapsed.

    Each sends a reader somewhere different — change the system, fix the evidence, declare the
    class, or accept the duty does not reach here — so the report must be able to tell them apart
    at all, which means four distinct categories rather than one bucket of "not satisfied".
    """
    keys = [key for key, _ in _CATEGORY_LABELS]
    labels = {key: label for key, label in _CATEGORY_LABELS}
    four = ("not_applicable", "unattainable", "not_evaluated", "violated")

    assert len(set(keys)) == len(keys), "a duplicated category key would merge two outcomes"
    for key in four:
        assert key in labels, f"{key} is not a report category"
    assert len({labels[key] for key in four}) == 4, "two of the four outcomes render alike"

    document = _document()
    for key in four:
        assert labels[key] in document, f"the document does not name the {labels[key]!r} outcome"
