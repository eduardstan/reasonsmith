"""Tests for the HTML conformance report renderer in reasonsmith v0.2.

What this module is for:
  Verifies that `ConformanceReport.render_html()` produces a self-contained, offline HTML report
  that presents the exact same counts, verdicts, strengths, and limits as `to_dict()` and
  `render_text()`, without computing anything differently or altering presentation of statutory
  duties.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.cli import main as cli_main
from reasonsmith.report import ConformanceReport, RequirementResult, check_conformance
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict


def test_html_renderer_presents_exact_same_counts_and_verdicts():
    """Rule: The renderer presents; it never decides. Counts and verdicts must match counts."""
    pack = load_pack("table7")
    sut = JSONLAdapter("docs/sample_decisions.jsonl")
    report = check_conformance(sut, pack, system_name="TestSystem", system_scope="high-risk")

    html = report.render_html()

    # Self-contained check: no external network resources
    assert "http://" not in html
    assert "https://" not in html

    # Limits check
    assert report.limits in html

    # Counts & Headline check
    assert report.headline in html
    assert f"{report.counts['binding_total']} total" in html
    assert f"{report.counts['interpretive_total']} total" in html

    # Every requirement ID, source clause, and verdict must appear in HTML
    for r in report.results:
        assert r.requirement_id in html
        assert r.source_clause in html
        if r.strength == Strength.UNATTAINABLE:
            assert "UNATTAINABLE" in html
        elif r.verdict == Verdict.SATISFIED:
            assert "SATISFIED" in html
        elif r.verdict == Verdict.VIOLATED:
            assert "VIOLATED" in html
        elif r.verdict == Verdict.NOT_APPLICABLE:
            assert "NOT APPLICABLE" in html


def test_html_distinguishes_unattainable_from_violated():
    """Unattainable (missing signals) must be visually distinct from Violated (trace breach)."""
    # Create an unattainable result
    r_unattainable = RequirementResult(
        requirement_id="req_unattainable",
        source_clause="EU AI Act Art. 12",
        verdict=Verdict.INCONCLUSIVE,
        strength=Strength.UNATTAINABLE,
        signals_required=("signal_a", "signal_b"),
        signals_missing=("signal_b",),
        evidence_summary="Unattainable as built",
        binding=True,
    )

    # Create a violated result
    r_violated = RequirementResult(
        requirement_id="req_violated",
        source_clause="GDPR Art. 22",
        verdict=Verdict.VIOLATED,
        strength=Strength.OBSERVED,
        signals_required=("signal_a",),
        evidence_summary="Violated over 3 decisions",
        details={"signals_absent_from_trace": ["signal_a"]},
        binding=True,
    )

    report = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(r_unattainable, r_violated),
    )

    html = report.render_html()

    # Check distinct visual classes and callouts
    assert "verdict-unattainable" in html
    assert "UNATTAINABLE AS BUILT — Missing Capability Signals" in html
    assert "verdict-violated" in html
    assert "VIOLATED IN TRACE — Required Signals Absent from Decision Log" in html


def test_cli_html_export():
    """Test generating HTML report via CLI --html flag with explicit UTF-8 encoding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "report.html"
        ret = cli_main([
            "check",
            "--system", "docs/sample_decisions.jsonl",
            "--pack", "ecoa",
            "--system-name", "CLITestSystem",
            "--html", str(out_file),
        ])
        assert ret == 0
        assert out_file.exists()

        content = out_file.read_text(encoding="utf-8")
        assert "CLITestSystem" in content
        assert "ecoa" in content
        assert "Strength Lattice" in content
