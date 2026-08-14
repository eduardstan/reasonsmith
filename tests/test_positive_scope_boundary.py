"""Positive findings carry their run-specific scope at the point of belief."""

from reasonsmith import demo
from reasonsmith.report import (
    RequirementResult,
    check_conformance,
    rationale_names_formalized_subset,
)
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict


def _result(strength, details):
    return RequirementResult(
        requirement_id="r",
        source_clause="clause",
        verdict=Verdict.SATISFIED,
        strength=strength,
        signals_required=("signal",),
        details=details,
    )


def test_observed_scope_names_supplied_records_and_limits():
    result = _result(Strength.OBSERVED, {"records_observed": 2})
    assert result.scope_boundary == (
        "Scope of this positive result: this formal property was satisfied only on the supplied "
        "2 decision records at the observed evidence rung; this run did not establish that the "
        "trace is complete, representative, or unfiltered, and it did not determine legal "
        "adequacy or compliance outside those records."
    )


def test_probed_scope_carries_the_search_budget():
    result = _result(
        Strength.PROBED,
        {
            "probe_budget": {
                "trials": 12,
                "seed": 7,
                "strategy": "grid",
                "input_space": {"income": 4},
            }
        },
    )
    assert "bounded search" in result.scope_boundary
    assert "12 input(s) replayed" in result.scope_boundary
    assert "seed 7" in result.scope_boundary
    assert "strategy: grid" in result.scope_boundary


def test_proved_scope_names_declared_assumptions():
    result = _result(Strength.PROVED, {"solver": "z3"})
    assert (
        "all inputs admitted by the system's declared logic and constraints"
        in result.scope_boundary
    )
    assert "match production or the world" in result.scope_boundary


def test_scope_fields_are_additive_machine_record_fields():
    result = _result(Strength.OBSERVED, {"records_observed": 1})
    payload = result.to_dict()
    assert payload["scope_boundary"] == result.scope_boundary
    assert payload["formalized_subset_only"] is False
    assert payload["formalized_subset_note"] is None


def test_rationale_subset_marker_is_conservative():
    assert rationale_names_formalized_subset(
        "Nothing here decides whether another statement is specific."
    )
    assert not rationale_names_formalized_subset("The clause names a decision and a reason.")


def test_shipped_explain_limit_reaches_positive_surfaces():
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    result = next(
        item
        for item in report.results
        if item.requirement_id == "ecoa_reg_b_1002_9_b_2_specific_reasons"
    )
    assert result.verdict is Verdict.SATISFIED
    assert result.formalized_subset_note == (
        "Formalized subset only — see explain "
        "ecoa_reg_b_1002_9_b_2_specific_reasons rationale."
    )
    record = result.to_dict()
    assert record["scope_boundary"] == result.scope_boundary
    assert record["formalized_subset_note"] == result.formalized_subset_note
    text = report.render_text()
    html = report.render_html(commit_hash="")
    assert result.scope_boundary in text
    assert result.formalized_subset_note in text
    assert result.scope_boundary in html
    assert result.formalized_subset_note in html
