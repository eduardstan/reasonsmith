"""Holds `docs/nesyarena-conformance-report.md` to the run it claims to be.

What this module is for:
  The report says it was produced by `python docs/build_nesyarena_report.py`. This test is what
  makes that a checked claim: it runs the builder and compares its output to the committed file
  byte-for-byte, so a stranger cloning the repository reproduces exactly the report they read.

What a reader must not break:
  - Compare verbatim. Normalising or matching on substrings would let a stale report pass, which
    is the one failure this test exists to catch. Anything that moves the output — a wording
    change in `report.render_text`, a different nesyarena version, a moved threshold — must be
    followed by regenerating the report.
  - The builder is loaded from its path rather than re-composed here: `docs/` is not an import
    package, and a second copy of the composition would let the test and the committed file
    agree with each other while both disagree with the script the report names.
  - This is the whole provenance check, and it deliberately asserts nothing about a commit hash.
    An earlier version of this file also checked that a `SOURCE_COMMIT` literal in the builder
    named a commit containing that builder. That check cannot hold: writing the hash into the
    artifact changes the file and therefore the commit, so the self-reference never closes, and
    naming the preceding commit instead is unverifiable in the shallow clone CI checks out.
    Reproducing the report from the committed builder is the stronger claim anyway, because it
    is checked rather than asserted. Do not add a hash back.
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
