"""Tests for the HTML conformance report renderer in reasonsmith v0.2.

What this module is for:
  Verifies that `ConformanceReport.render_html()` produces a self-contained, offline HTML report
  that presents the exact same counts, verdicts, strengths, and limits as `to_dict()` and
  `render_text()`, without computing anything differently or altering presentation of statutory
  duties.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.cli import main as cli_main
from reasonsmith.report import ConformanceReport, RequirementResult, check_conformance
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_LOG = ROOT / "docs" / "sample_decisions.jsonl"
DOCS_INDEX = ROOT / "docs" / "index.html"

#: The command the committed demo page reports, and the one that regenerates it.
DOCS_COMMAND = (
    "python -m reasonsmith.cli check --system docs/sample_decisions.jsonl --pack table7 "
    "--system-name CreditScoringPipeline --html docs/index.html"
)


def _fake_git(status_out: str = "", status_rc: int = 0, head_out: str = "", head_rc: int = 0):
    """A `subprocess.run` stand-in answering the two git calls `_source_checkout` makes."""

    def run(argv, **kwargs):
        if "status" in argv:
            return subprocess.CompletedProcess(argv, status_rc, status_out, "")
        return subprocess.CompletedProcess(argv, head_rc, head_out, "")

    return run


def test_html_renderer_presents_exact_same_counts_and_verdicts():
    """Rule: The renderer presents; it never decides. Counts and verdicts must match counts."""
    pack = load_pack("table7")
    sut = JSONLAdapter(str(SAMPLE_LOG))
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
            "--system", str(SAMPLE_LOG),
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
        assert "Report Provenance:" in content


def test_cli_json_is_not_dropped_when_html_goes_to_a_file(capsys):
    """`--json --html FILE` writes the page and still prints the JSON it was asked for."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "report.html"
        ret = cli_main([
            "check",
            "--system", str(SAMPLE_LOG),
            "--pack", "ecoa",
            "--json",
            "--html", str(out_file),
        ])
        assert ret == 0
        assert out_file.exists()
        assert json.loads(capsys.readouterr().out)["pack_id"] == "ecoa"


def test_cli_refuses_json_and_html_on_the_same_stream(capsys):
    """Both to stdout would silently lose one, so it is a usage error, not a quiet drop."""
    ret = cli_main([
        "check", "--system", str(SAMPLE_LOG), "--pack", "ecoa", "--json", "--html", "-",
    ])
    assert ret == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_unwritable_html_path_is_an_input_error(capsys):
    """A bad --html path exits 1 with a message, never an unhandled OSError traceback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ret = cli_main([
            "check",
            "--system", str(SAMPLE_LOG),
            "--pack", "ecoa",
            "--html", str(Path(tmpdir) / "no-such-dir" / "report.html"),
        ])
        assert ret == 1
        assert "Error writing HTML report" in capsys.readouterr().err


def test_modified_working_tree_makes_no_commit_claim(monkeypatch):
    """A dirty tree is not identified by any commit, so the report must not name one."""
    monkeypatch.setattr(subprocess, "run", _fake_git(status_out=" M src/reasonsmith/report.py"))

    html = _docs_report().render_html(command="reasonsmith check")

    assert "from commit" not in html
    assert "from a modified working tree, which no commit identifies" in html


def test_unidentifiable_checkout_says_so_rather_than_guessing(monkeypatch):
    """No git, no checkout, no claim — and never a command invented from sys.argv."""

    def boom(*args, **kwargs):
        raise OSError("git not found")

    monkeypatch.setattr(subprocess, "run", boom)

    html = _docs_report().render_html()

    assert "from commit" not in html
    assert "Generated without an identified source commit." in html
    assert "Command:" not in html


def test_clean_checkout_names_its_commit(monkeypatch):
    """The one case a commit may be named: git describes the checkout and it is clean."""
    monkeypatch.setattr(subprocess, "run", _fake_git(head_out="0123456789abcdef\n"))

    html = _docs_report().render_html()

    assert "from commit <code>0123456</code>" in html


def test_docs_index_html_matches_the_renderer():
    """The committed demo page is generated, not hand-maintained: it must match the renderer.

    It is rendered with an empty `commit_hash` because a page committed into the tree it
    describes cannot name the commit that contains it. Regenerate it with:

        PYTHONPATH=src:tests python -c \
"from test_html_report import regenerate_docs_index; regenerate_docs_index()"
    """
    assert DOCS_INDEX.read_text(encoding="utf-8") == _render_docs_index()


def _docs_report() -> ConformanceReport:
    return check_conformance(
        JSONLAdapter(str(SAMPLE_LOG)), load_pack("table7"), system_name="CreditScoringPipeline"
    )


def _render_docs_index() -> str:
    return _docs_report().render_html(commit_hash="", command=DOCS_COMMAND)


def regenerate_docs_index() -> None:
    DOCS_INDEX.write_text(_render_docs_index(), encoding="utf-8")
