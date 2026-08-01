"""Holds `docs/nesyarena-conformance-report.md` to the run it claims to be.

What this module is for:
  The report says it was produced by `python docs/build_nesyarena_report.py`. This test is what
  makes that a checked claim: it runs the builder and compares its output to the committed file
  byte-for-byte, so a stranger cloning the repository reproduces exactly the report they read.

What a reader must not break:
  - Compare verbatim. Normalising or matching on substrings would let a stale report pass, which
    is the one failure this test exists to catch. Anything that moves the output — a wording
    change in `report.render_text`, a different nesyarena version, a moved threshold — must be
    followed by regenerating the report and moving `SOURCE_COMMIT` with it.
  - The builder is loaded from its path rather than re-composed here: `docs/` is not an import
    package, and a second copy of the composition would let the test and the committed file
    agree with each other while both disagree with the script the report names.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "nesyarena-conformance-report.md"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_nesyarena_report", ROOT / "docs" / "build_nesyarena_report.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


def test_nesyarena_report_matches_the_builder():
    """The committed report is what the command it names writes, byte-for-byte."""
    assert REPORT.read_text(encoding="utf-8") == builder.render()


def test_builder_names_the_commit_that_produced_the_report():
    """A provenance line naming nothing checkable is not provenance."""
    assert len(builder.SOURCE_COMMIT) == 40
    assert all(c in "0123456789abcdef" for c in builder.SOURCE_COMMIT)
    assert builder.SOURCE_COMMIT in REPORT.read_text(encoding="utf-8")
