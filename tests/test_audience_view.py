"""Tests holding the audience projections to the three things they may never do.

What this module is for:
  One conformance run, five readers, five artefacts. `reasonsmith.render.AUDIENCES` decides what
  each reader is shown, and the whole design rests on that being a *projection over data the run
  already produced* rather than a second, per-reader computation. These tests pin the three
  properties that make the projection safe to hand to a stranger, and the one property that makes
  it worth having at all.

What a reader must not break:
  - No audience sees a verdict another audience does not see. The projection changes what is
    shown, never what is claimed, so the requirement-to-verdict map read back out of every
    rendering is the same map (`test_no_audience_sees_a_different_verdict_from_another`).
    Why this matters: five artefacts that disagree about an outcome are five reports, not five
    views of one, and a reader shown the kinder one has been misled by the tool itself.
  - Every audience keeps `report.limits`. A projection may drop anything else and may drop
    nothing of that (`test_every_audience_keeps_the_limits`).
    Why this matters: the reader most likely to over-read a clean result is the one least
    equipped to notice the statement of what was not determined going missing.
  - The affected-individual rendering carries no system internals. Asserted as an *exclusion*
    over the run's own data — every signal name, every evidence summary, every probe budget,
    every counterexample value — never as an inclusion list, which a later leak would pass
    (`test_the_affected_individual_view_leaks_no_system_internals`).
    Why this matters: an inclusion test is satisfied by a page that also contains everything
    else. Only naming what must be absent fails when something new appears.
  - Two audiences differ by content, not framing, asserted on the emitted structure
    (`test_two_audiences_differ_by_content_not_framing`).
    Why this matters: an implementation that renders one body under five titles would satisfy
    every other test here, and would be exactly the relabelling this feature is not.
"""

from __future__ import annotations

import re

import pytest

from reasonsmith.render import _FULL, AUDIENCES, render_html, render_text
from reasonsmith.report import (
    PROBE_BUDGET_KEY,
    UNDECLARED_DOMAIN_KEY,
    ConformanceReport,
    RequirementResult,
)
from reasonsmith.verdict import Strength, Verdict

#: The five audiences the CLI offers. Written out rather than derived from `AUDIENCES` so that
#: adding a sixth without deciding what it may see fails here instead of passing silently.
FIVE = ("affected-individual", "auditor", "deployer", "developer", "regulator")


def _run() -> ConformanceReport:
    """One fixed run, carrying every kind of detail a projection has to decide about.

    Hand-built rather than driven through an engine: these tests are about the renderings, and a
    fixture that exercises every branch of them is worth more here than a realistic one that
    exercises three.
    """
    return ConformanceReport(
        pack_id="ecoa",
        system_name="log-only creditor",
        system_scope="high-risk",
        system_domains=("consumer-credit",),
        results=(
            RequirementResult(
                requirement_id="unattainable_duty",
                source_clause="12 CFR 1002.9(a)(1)",
                verdict=Verdict.INCONCLUSIVE,
                strength=Strength.UNATTAINABLE,
                signals_required=("artifact_logs_decision_record", "provenance_model_version"),
                signals_missing=("artifact_logs_decision_record",),
                evidence_summary=(
                    "Unattainable as built: the system declares no capability to emit "
                    "artifact_logs_decision_record."
                ),
                scope="high-risk",
                domains=("consumer-credit",),
            ),
            RequirementResult(
                requirement_id="violated_duty",
                source_clause="12 CFR 1002.9(b)(2)",
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=("artifact_logs_reason_explanation",),
                evidence_summary="Observed: the trace breaches the property at step 1.",
                details={
                    "signals_absent_from_trace": ["scope_statements_local_vs_global"],
                    "offending_trace_segment": [
                        {"applicant_id": "APP-1042", "reason": "internal standards"}
                    ],
                    "violation_step_indices": [1],
                    "counterexample": {"credit_score": 601},
                },
                binding=True,
                scope="high-risk",
                domains=("consumer-credit",),
            ),
            RequirementResult(
                requirement_id="probed_duty",
                source_clause="12 CFR 1002.9(b)(2)",
                verdict=Verdict.SATISFIED,
                strength=Strength.PROBED,
                signals_required=("artifact_logs_reason_explanation",),
                evidence_summary="Probed: no counterexample in 200 replayed inputs.",
                details={
                    PROBE_BUDGET_KEY: {
                        "trials": 200,
                        "strategy": "seeded perturbation of recorded decisions",
                        "seed": 0,
                        "input_space": {"credit_score": 11},
                    }
                },
                binding=False,
            ),
            RequirementResult(
                requirement_id="not_applicable_duty",
                source_clause="EU AI Act Art. 13",
                verdict=Verdict.NOT_APPLICABLE,
                strength=None,
                signals_required=("provenance_model_version",),
                evidence_summary="Not applicable: the duty is limited to another domain.",
                domains=("healthcare",),
            ),
        ),
    )


#: `  [TIER] [INTERPRETIVE] requirement_id (clause): verdict`, with the tier and the tag optional
#: exactly as a projection may make them. Used to read a rendering back as data.
_FINDING = re.compile(
    r"^ {2}(?:\[(?P<tier>[A-Z ]+)\] )?(?:\[INTERPRETIVE\] )?"
    r"(?P<req>\S+) \((?P<clause>.+)\): (?P<verdict>\S+)$",
    re.MULTILINE,
)


def _findings(text: str) -> dict[str, str]:
    """The requirement-to-verdict map a text rendering actually emits."""
    found = {m.group("req"): m.group("verdict") for m in _FINDING.finditer(text)}
    assert found, "no finding line parsed out of the rendering"
    return found


def _tiers(text: str) -> dict[str, str | None]:
    return {m.group("req"): m.group("tier") for m in _FINDING.finditer(text)}


def _body(page: str) -> str:
    """The rendered body of an HTML page, with the stylesheet cut off.

    The `<head>` names every CSS class the page *can* draw whatever it actually draws, and it
    carries numbers of its own (`minmax(200px, 1fr)`). The reveal script at the foot is the same
    kind of fixed furniture. An exclusion asserted over the whole file would be answering
    questions about the stylesheet, not about what a reader is shown.
    """
    return page[page.index("<body>") : page.index("<script>")]


def _detail_lines(text: str) -> set[str]:
    """Every per-requirement detail line, which is where a projection's content lives.

    Deliberately *not* the whole rendering: a comparison including titles and headings would be
    satisfied by two identical bodies under different banners, which is the failure mode the
    acceptance test exists to catch.
    """
    return {line for line in text.splitlines() if line.startswith("    ")}


def test_the_five_audiences_all_render():
    report = _run()
    for audience in FIVE:
        assert audience in AUDIENCES
        text = render_text(report, audience=audience)
        page = render_html(report, commit_hash="", audience=audience)
        assert text.startswith("CONFORMANCE REPORT")
        assert page.startswith("<!DOCTYPE html>")
        assert page.rstrip().endswith("</html>")


def test_the_default_rendering_is_the_full_report_and_the_auditors():
    """No flag renders everything, and the auditor projection *is* that same object.

    The no-flag rendering is pinned byte-for-byte by every generated document under `docs/`; this
    states the relationship those pins depend on in one place.
    """
    report = _run()
    assert AUDIENCES["auditor"] is _FULL
    assert render_text(report) == render_text(report, audience="auditor")
    assert render_html(report, commit_hash="") == render_html(
        report, commit_hash="", audience="auditor"
    )


def test_an_unknown_audience_is_refused_rather_than_widened():
    """A typo must not hand an affected individual the full solver output."""
    report = _run()
    with pytest.raises(ValueError, match="unknown audience"):
        render_text(report, audience="affected individual")
    with pytest.raises(ValueError, match="unknown audience"):
        render_html(report, commit_hash="", audience="reglator")


# --- Rule 1: no audience sees a verdict that differs from another audience's ------------------


def test_no_audience_sees_a_different_verdict_from_another():
    report = _run()
    truth = {r.requirement_id: r.verdict.value for r in report.results}
    seen = {a: _findings(render_text(report, audience=a)) for a in FIVE}

    for audience, found in seen.items():
        assert found == truth, f"{audience} renders a verdict map the run does not carry"

    # And the strength, where a projection shows one, is the run's strength and not another's.
    for audience in FIVE:
        for req_id, tier in _tiers(render_text(report, audience=audience)).items():
            if tier is None:
                continue
            result = next(r for r in report.results if r.requirement_id == req_id)
            expected = (
                "NOT APPLICABLE"
                if result.verdict == Verdict.NOT_APPLICABLE
                else (result.strength.value.upper() if result.strength else "NOT EVALUATED")
            )
            assert tier == expected, f"{audience} shows {req_id} at a strength it does not have"

    # The HTML says the same thing: every audience's page names every requirement and its verdict.
    for audience in FIVE:
        page = render_html(report, commit_hash="", audience=audience)
        for result in report.results:
            assert result.requirement_id in page
            assert result.verdict.value.replace("_", " ").upper() in page.upper()


# --- Rule 2: every audience keeps the limits ---------------------------------------------------


def test_every_audience_keeps_the_limits():
    report = _run()
    import html as html_module

    for audience in (None, *FIVE):
        text = render_text(report, audience=audience)
        assert "LIMITS OF THIS REPORT" in text, f"{audience} dropped the limits heading"
        assert report.limits in text, f"{audience} dropped the limits statement"

        page = render_html(report, commit_hash="", audience=audience)
        assert "Limits of this report" in page, f"{audience} dropped the limits card"
        assert html_module.escape(report.limits) in page, f"{audience} dropped the limits text"


def test_every_audience_keeps_the_notice_that_duties_went_unchecked():
    """The other thing a projection may not drop: duties nothing looked at."""
    base = _run()
    undeclared = ConformanceReport(
        pack_id=base.pack_id,
        system_name=base.system_name,
        results=(
            RequirementResult(
                requirement_id="skipped_duty",
                source_clause="12 CFR 1002.9(a)(1)",
                verdict=Verdict.NOT_APPLICABLE,
                strength=None,
                signals_required=("artifact_logs_decision_record",),
                evidence_summary="Not applicable: no decision domain declared.",
                domains=("consumer-credit",),
                details={UNDECLARED_DOMAIN_KEY: True},
            ),
        ),
    )
    notice = undeclared.undeclared_domain_notice
    assert notice, "fixture does not raise the notice this test is about"
    for audience in (None, *FIVE):
        assert notice in render_text(undeclared, audience=audience)


# --- Rule 3: the affected-individual view leaks no system internals ----------------------------


def _internals(report: ConformanceReport) -> dict[str, list[str]]:
    """Every string in this run that is a system internal, grouped by what kind it is.

    Read off the run rather than written down, so a new detail key a later engine emits is
    covered by the exclusion the moment the fixture carries it.
    """
    signal_names: list[str] = []
    summaries: list[str] = []
    budget_bits: list[str] = []
    witness_values: list[str] = []
    for r in report.results:
        signal_names += [*r.signals_required, *r.signals_missing]
        signal_names += list(r.details.get("signals_absent_from_trace", ()))
        if r.evidence_summary:
            summaries.append(r.evidence_summary)
        budget = r.details.get(PROBE_BUDGET_KEY)
        if budget:
            budget_bits += [str(budget["trials"]), str(budget["strategy"])]
            budget_bits += list(budget["input_space"])
        for record in r.details.get("offending_trace_segment", ()):
            witness_values += [str(v) for v in record.values()]
        for value in (r.details.get("counterexample") or {}).values():
            witness_values.append(str(value))
    return {
        "signal name": signal_names,
        "evidence summary": summaries,
        "probe budget": budget_bits,
        "counterexample value": witness_values,
    }


def test_the_affected_individual_view_leaks_no_system_internals():
    report = _run()
    internals = _internals(report)
    assert all(internals.values()), "the fixture must carry every kind of internal to exclude"

    text = render_text(report, audience="affected-individual")
    page = _body(render_html(report, commit_hash="", audience="affected-individual"))

    for kind, values in internals.items():
        for value in values:
            assert value not in text, f"the affected-individual text leaks a {kind}: {value!r}"
            assert value not in page, f"the affected-individual page leaks a {kind}: {value!r}"

    # Solver and lattice vocabulary is an internal too: a person told a duty is "probed" has been
    # handed this tool's evidence model, not an answer. The page's stylesheet names the lattice
    # classes whatever is rendered, so the text is where this is asserted.
    for rung in Strength:
        assert rung.value.upper() not in text
    assert "probe budget:" not in text
    assert "requires:" not in text
    assert "MISSING SIGNALS" not in text
    assert "ABSENT FROM TRACE" not in text
    assert "Strength Lattice" not in page
    assert '<table class="witness-table">' not in page

    # What it does carry: the clause, the verdict, and the limits.
    for result in report.results:
        assert result.source_clause in text
    assert report.limits in text


# --- The acceptance test: content, not framing -------------------------------------------------


def test_two_audiences_differ_by_content_not_framing():
    """Two audiences emit different *data*, asserted on structure a relabelling cannot fake.

    The comparison is over the set of per-requirement detail lines — the body, with every title,
    heading and banner excluded — and it is two-sided: each of the two carries a datum the other
    does not. An implementation rendering one body under five headings emits the same detail-line
    set for both and fails on the first assertion; one that merely re-words a heading fails on
    the two `difference` assertions that follow.
    """
    report = _run()
    dev = _detail_lines(render_text(report, audience="developer"))
    reg = _detail_lines(render_text(report, audience="regulator"))

    assert dev != reg, "two audiences emitted the same body; only the framing can have changed"
    assert dev - reg, "the developer view adds no content the regulator view lacks"
    assert reg - dev, "the regulator view adds no content the developer view lacks"

    # Named, so the difference cannot drift into an accident of formatting: the developer is shown
    # which signal is missing and where, the regulator how far the duty reaches.
    assert any("requires: artifact_logs_reason_explanation" in line for line in dev)
    assert not any("requires:" in line for line in reg)
    assert any("domain limit: consumer-credit" in line for line in reg)
    assert not any("domain limit:" in line for line in dev)

    # The same two audiences differ in the HTML too, and by more than a class name.
    dev_page = _body(render_html(report, commit_hash="", audience="developer"))
    reg_page = _body(render_html(report, commit_hash="", audience="regulator"))
    witness = '<table class="witness-table">'
    assert witness in dev_page and witness not in reg_page
    assert "Requires Signals" in dev_page and "Requires Signals" not in reg_page
    assert "badge-scope" in reg_page and "badge-scope" not in dev_page

    # And no two of the five collapse onto one artefact.
    bodies = {audience: render_text(report, audience=audience) for audience in FIVE}
    assert len({body for name, body in bodies.items() if name != "auditor"}) == 4


def test_the_cli_offers_the_five_audiences_and_refuses_a_sixth(tmp_path, capsys):
    """The flag reaches the renderer; an unknown name is a usage error, not a full report."""
    from reasonsmith.cli import main

    log = tmp_path / "decisions.jsonl"
    log.write_text(
        '{"applicant_id": "A-1", "artifact_logs_reason_explanation": "credit score too low"}\n',
        encoding="utf-8",
    )
    argv = ["check", "--system", str(log), "--pack", "ecoa", "--system-domain", "consumer-credit"]

    with pytest.raises(SystemExit) as refused:
        main([*argv, "--audience", "nobody"])
    assert refused.value.code == 2
    assert "invalid choice" in capsys.readouterr().err

    seen = {}
    for audience in FIVE:
        capsys.readouterr()
        main([*argv, "--audience", audience])
        seen[audience] = capsys.readouterr().out
    assert "requires:" in seen["developer"]
    assert "requires:" not in seen["affected-individual"]
