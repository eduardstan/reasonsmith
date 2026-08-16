"""Tests for the HTML conformance report renderer in reasonsmith v0.10.2.

What this module is for:
  Verifies that `ConformanceReport.render_html()` produces a self-contained, offline HTML report
  that presents the exact same counts, verdicts, strengths, and limits as `to_dict()` and
  `render_text()`, without computing anything differently or altering presentation of statutory
  duties.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.cli import main as cli_main
from reasonsmith.demo import render_key_finding_html
from reasonsmith.examples import SAMPLE_LOG
from reasonsmith.report import (
    PROBE_BUDGET_KEY,
    ConformanceReport,
    RequirementResult,
    check_conformance,
)
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

ROOT = Path(__file__).resolve().parents[1]
DOCS_INDEX = ROOT / "docs" / "report.html"


def _load_build_example():
    """The committed page's build script, loaded as written: `docs/` is not an import package.

    Loading it is what keeps this test honest. Re-implementing the composition here would let the
    committed page, the provenance command it prints and this test drift apart in three places.
    """
    spec = importlib.util.spec_from_file_location(
        "build_example", ROOT / "docs" / "build_example.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_example = _load_build_example()


def _fake_git(
    status_out: str = "",
    status_rc: int = 0,
    head_out: str = "",
    head_rc: int = 0,
    tracked_rc: int = 0,
):
    """A `subprocess.run` stand-in answering the git calls `_source_checkout` makes."""

    def run(argv, **kwargs):
        if "ls-files" in argv:
            return subprocess.CompletedProcess(argv, tracked_rc, "", "")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, status_rc, status_out, "")
        return subprocess.CompletedProcess(argv, head_rc, head_out, "")

    return run


def _minimal_report():
    """One real run, for the tests that inspect the stylesheet rather than the content."""
    return check_conformance(
        JSONLAdapter(str(SAMPLE_LOG)),
        load_pack("table7"),
        system_name="TestSystem",
        system_scope="high-risk",
    )


def test_html_renderer_presents_exact_same_counts_and_verdicts():
    """Rule: The renderer presents; it never decides. Counts and verdicts must match counts."""
    pack = load_pack("table7")
    sut = JSONLAdapter(str(SAMPLE_LOG))
    report = check_conformance(sut, pack, system_name="TestSystem", system_scope="high-risk")

    html = report.render_html()

    # Self-contained check: no external network resources; the two canonical landing links are
    # navigation, not fetched resources, and intentionally point at the live front door.
    assert "http://" not in html
    assert html.count('href="https://reasonsmith.dev/"') == 2

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


def test_report_for_an_arbitrary_system_carries_no_narrative_it_did_not_measure():
    """A report is read as being about its own system, so nothing else may ride along in it.

    The demonstration's key finding belongs to case `APP-1042` and to the committed example page.
    A user checking their own decision log must get their own findings and no one else's: a
    hardcoded evidence record badged COMPLETE, above their results, in a document handed to an
    auditor, is the false completeness this package exists to refuse.
    """
    report = ConformanceReport(
        pack_id="test_pack",
        system_name="SomeoneElsesSystem",
        results=(
            RequirementResult(
                requirement_id="req_a",
                source_clause="GDPR Art. 22",
                verdict=Verdict.SATISFIED,
                strength=Strength.OBSERVED,
                signals_required=("signal_a",),
                evidence_summary="Observed over 3 decisions",
                binding=True,
            ),
        ),
    )

    html = report.render_html()

    for narrative in (
        "KEY FINDING",
        "key-finding-section",
        "APP-1042",
        "AAN-2026-0731-1042",
        "Reason-Deletion Certificate",
        "Form Completeness Does Not Imply Reason Fidelity",
        "25 months from notice date, per lender policy",
    ):
        assert narrative not in html, f"{narrative!r} leaked into an unrelated system's report"

    # The example page is the one place it is composed in, and it is composed by the caller.
    assert "KEY FINDING" in report.render_html(extra_section_html=render_key_finding_html())


def test_witness_table_is_capped_and_says_how_many_it_elided():
    """A record duty no record discharges makes every record offending: the table must not be
    the whole decision log, and what it drops must be counted on the page, never dropped
    silently."""
    records = [{"step": i} for i in range(75)]
    report = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(
            RequirementResult(
                requirement_id="req_violated",
                source_clause="GDPR Art. 22",
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=("signal_a",),
                evidence_summary="Violated over 75 decisions",
                details={
                    "offending_trace_segment": records,
                    "violation_step_indices": list(range(75)),
                },
                binding=True,
            ),
        ),
    )

    html = report.render_html()

    assert html.count("<tr><td>Step ") == 20
    assert "showing the first 20 of 75 offending records" in html
    assert "Step 19</td>" in html
    assert "Step 20</td>" not in html


def test_text_finding_names_the_offending_decision_record():
    """A violated finding in the text report identifies the record, not only a bare index.

    The JSON (`details.offending_trace_segment`) and HTML (witness table) renderings already
    name the offending record; the text default is the odd surface out, and it is what a
    first-time user meets. The text follows the same convention — the record's own
    `decision_id` — and falls back to the step index only when a record carries no identifier,
    so a reader is never handed an empty name and the index stays available for mapping back to
    the JSON's `violation_step_indices` / HTML's "Step N".
    """
    report = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(
            RequirementResult(
                requirement_id="req_violated",
                source_clause="GDPR Art. 22",
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=("signal_a",),
                evidence_summary="Violated over 2 decisions",
                details={
                    "offending_trace_segment": [
                        {"decision_id": "dec-1024", "result": "no"},
                        {"decision_id": "dec-1025", "result": "no"},
                    ],
                    "violation_step_indices": [3, 5],
                },
                binding=True,
            ),
        ),
    )
    text = report.render_text()
    assert (
        "offending records: decision dec-1024 (step 3), decision dec-1025 (step 5)" in text
    ), "the text finding must name the decision records it came from"

    # A record that carries no `decision_id` falls back to the step index: the output stays
    # useful rather than printing an empty name, and the index remains available.
    unnamed = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(
            RequirementResult(
                requirement_id="req_unnamed",
                source_clause="GDPR Art. 22",
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=("signal_a",),
                evidence_summary="Violated over 3 decisions",
                details={
                    "offending_trace_segment": [{"result": "no"}],
                    "violation_step_indices": [1],
                },
                binding=True,
            ),
        ),
    )
    unnamed_text = unnamed.render_text()
    assert "offending record: step 1" in unnamed_text

    # The JSON and HTML renderings are untouched: the identification is a text-surface concern
    # on top of details the run already produced, and its phrasing appears nowhere else.
    assert "offending records:" not in report.render_html()
    assert "offending records:" not in json.dumps(report.to_dict())


def test_text_finding_never_names_a_record_it_was_not_given():
    """No offending-record line without an offending segment to back it.

    A violated verdict that carries no `offending_trace_segment` (e.g. one the solver proved
    with a counterexample) keeps exactly the text it had: the line is drawn from the record
    evidence, never invented.
    """
    report = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(
            RequirementResult(
                requirement_id="req_violated",
                source_clause="GDPR Art. 22",
                verdict=Verdict.VIOLATED,
                strength=Strength.PROBED,
                signals_required=("signal_a",),
                evidence_summary="Violated on a counterexample input",
                details={
                    "counterexample": {"credit_score": 601},
                    PROBE_BUDGET_KEY: {
                        "trials": 8,
                        "strategy": "seeded perturbation",
                        "seed": 0,
                        "input_space": {"credit_score": 601},
                    },
                },
                binding=True,
            ),
        ),
    )
    text = report.render_text()
    assert "offending record" not in text


def test_witness_table_below_the_cap_states_it_is_complete():
    """Under the cap nothing is elided, and the page says so rather than leaving it open."""
    report = ConformanceReport(
        pack_id="test_pack",
        system_name="TestSystem",
        results=(
            RequirementResult(
                requirement_id="req_violated",
                source_clause="GDPR Art. 22",
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=("signal_a",),
                evidence_summary="Violated over 2 decisions",
                details={
                    "offending_trace_segment": [{"step": 0}, {"step": 1}],
                    "violation_step_indices": [0, 1],
                },
                binding=True,
            ),
        ),
    )

    html = report.render_html()

    assert "all 2 offending records" in html
    assert "Witness truncated for display" not in html


def test_cli_html_export():
    """Test generating HTML report via CLI --html flag with explicit UTF-8 encoding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "report.html"
        ret = cli_main(
            [
                "check",
                "--system",
                str(SAMPLE_LOG),
                "--pack",
                "ecoa",
                "--system-name",
                "CLITestSystem",
                "--html",
                str(out_file),
            ]
        )
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
        ret = cli_main(
            [
                "check",
                "--system",
                str(SAMPLE_LOG),
                "--pack",
                "ecoa",
                "--json",
                "--html",
                str(out_file),
            ]
        )
        assert ret == 0
        assert out_file.exists()
        assert json.loads(capsys.readouterr().out)["pack_id"] == "ecoa"


def test_cli_refuses_json_and_html_on_the_same_stream(capsys):
    """Both to stdout would silently lose one, so it is a usage error, not a quiet drop."""
    ret = cli_main(
        [
            "check",
            "--system",
            str(SAMPLE_LOG),
            "--pack",
            "ecoa",
            "--json",
            "--html",
            "-",
        ]
    )
    assert ret == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_unwritable_html_path_is_an_input_error(capsys):
    """A bad --html path exits 1 with a message, never an unhandled OSError traceback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ret = cli_main(
            [
                "check",
                "--system",
                str(SAMPLE_LOG),
                "--pack",
                "ecoa",
                "--html",
                str(Path(tmpdir) / "no-such-dir" / "report.html"),
            ]
        )
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


def test_enclosing_repo_that_does_not_track_this_module_names_no_commit(monkeypatch):
    """Installed inside an unrelated project's checkout: that project's HEAD is not provenance.

    An ignored install path is absent from `status --porcelain`, so the host tree reads clean
    and would otherwise hand back a commit containing none of the code that ran.
    """
    monkeypatch.setattr(subprocess, "run", _fake_git(tracked_rc=1, head_out="dead" * 10))

    html = _docs_report().render_html(command="reasonsmith check")

    assert "from commit" not in html
    assert "Generated without an identified source commit." in html


def test_clean_checkout_names_its_commit(monkeypatch):
    """The one case a commit may be named: git describes the checkout and it is clean."""
    monkeypatch.setattr(subprocess, "run", _fake_git(head_out="0123456789abcdef\n"))

    html = _docs_report().render_html()

    assert "from commit <code>0123456</code>" in html


def test_a_provenance_note_is_the_callers_claim_and_is_escaped():
    """The bar carries a caller's origin claim verbatim, and nothing when there is none."""
    report = _docs_report()

    assert "Command:" not in report.render_html(commit_hash="")
    injected = report.render_html(
        commit_hash="", provenance_note="<script>alert(1)</script>"
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in injected
    assert "<script>alert(1)</script>" not in injected
    assert "reproduces itself" in report.render_html(
        commit_hash="", provenance_note="reproduces itself"
    )


def test_the_page_states_the_guarantee_it_carries_instead_of_a_commit():
    """A page committed into this repository cannot name the commit that carries it.

    That commit does not exist while the page is rendered, so the page names the check that
    holds it to its build command instead — the property a hash was wanted for, and one a
    reader with a checkout can run. Renaming that test means rewording this claim.
    """
    page = DOCS_INDEX.read_text(encoding="utf-8")

    assert build_example.PROVENANCE_NOTE in page
    assert "test_docs_index_html_matches_the_renderer" in build_example.PROVENANCE_NOTE


def test_docs_index_html_matches_the_renderer():
    """The committed demo page is generated, not hand-maintained: it must match its build script.

    Regenerate it with `python docs/build_example.py`, the command the page itself names.
    """
    assert DOCS_INDEX.read_text(encoding="utf-8") == build_example.render()


def test_the_page_names_a_provenance_command_that_reproduces_it():
    """A command line the report cannot be reproduced from is not provenance, it is decoration.

    The page carries the key finding, which the CLI never renders, so the CLI command that once
    stood in this line wrote a byte-different file. The claim and the producer must be the same
    thing.
    """
    page = DOCS_INDEX.read_text(encoding="utf-8")

    assert f"Command: <code>{build_example.BUILD_COMMAND}</code>" in page
    assert "python -m reasonsmith.cli" not in page

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "index.html"
        ret = cli_main(
            [
                "check",
                "--system",
                str(SAMPLE_LOG),
                "--pack",
                "table7",
                "--system-name",
                "CreditScoringPipeline",
                "--system-scope",
                "high-risk",
                "--html",
                str(out_file),
            ]
        )
        assert ret in (0, 2)
        assert out_file.read_text(encoding="utf-8") != page


def _docs_report() -> ConformanceReport:
    return build_example.example_report()


def test_the_dark_scheme_is_screen_only_so_print_stays_light():
    """The dark tokens must not follow the page onto paper.

    The `@media print` block below them overrides a handful of declarations and otherwise assumes
    the light token values, so a dark override that also matched print media would print white
    text on a white sheet. Scoping the dark block to `screen` is what keeps the two apart, and it
    is one word — exactly the kind of word a later edit drops without noticing.
    """
    html = _minimal_report().render_html()

    dark = "@media screen and (prefers-color-scheme: dark)"

    assert dark in html
    assert "@media (prefers-color-scheme: dark)" not in html
    assert html.index(dark) < html.index("@media print {")


def test_a_requirement_identifier_never_renders_under_its_badges():
    """The card header must reflow before it collides, at every width above the mobile block.

    The header is one flex row: the identifier and its citation on the left, the badges on the
    right. Given a zero flex basis and a floor narrower than an identifier, that left item was
    handed less width than its own content between roughly 768px and 1000px — the desktop row
    still applied, and there was no room for a long identifier beside three badges — so the
    identifier overflowed *under* the badges and the reader saw them overprinted. A tablet, a
    half-width desktop window and every frame in `docs/audiences.html` are in that band.

    Two declarations keep it apart and neither is visible in a screenshot of a wide window, so
    both are pinned here. The basis is the width below which the row is not worth keeping: with
    it, the badge group drops to its own line before anything can overlap. `overflow-wrap` is
    the backstop for a width no reflow can rescue — an identifier is a single unbreakable token,
    so on a phone it must be allowed to break rather than run out of the card.
    """
    html = _minimal_report().render_html()

    assert ".req-title-group { flex: 1 1 26rem; min-width: 0; }" in html

    req_id = html[html.index(".req-id {") : html.index(".req-clause {")]
    assert "overflow-wrap: anywhere;" in req_id


def test_both_schemes_keep_the_verdict_colours_apart():
    """Satisfied-green and violated-red carry meaning here, so both schemes must separate them.

    The check is on the hue channel of the two foreground tokens, in both token blocks: a dark
    scheme that reached for one muted grey-red and one muted grey-green would still pass a
    contrast check against the background and would still have destroyed the distinction the
    reader uses. `--ok` is a green hue and `--accent-deep` is a red one, twice.
    """
    html = _minimal_report().render_html()
    hues = re.findall(r"--(ok|accent-deep): oklch\([\d.]+% [\d.]+ (\d+)\)", html)

    assert len(hues) == 4, "each token is defined once in the light block and once in the dark one"
    for token, hue in hues:
        expected = (140, 170) if token == "ok" else (10, 40)
        assert expected[0] <= int(hue) <= expected[1], f"--{token} left its hue range at {hue}"


def test_the_dark_page_is_still_self_contained():
    """A dark scheme is the classic excuse for a first external asset. There must not be one.

    The page's one inline script is not at issue — it has always been there and fetches nothing.
    What this refuses is a stylesheet, font or script pulled off a host at read time.
    """
    html = _minimal_report().render_html()

    assert "http://" not in html
    assert html.count('href="https://reasonsmith.dev/"') == 2
    assert "@import" not in html
    assert "src=" not in html
    assert "<link" not in html
