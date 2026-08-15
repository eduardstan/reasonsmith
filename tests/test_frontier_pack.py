"""Seoul pack, frontier applicability, and Commitment IV depth-anchor tests."""

from __future__ import annotations

from typing import Any

import pytest

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.examples.frontier_risk_rules import system_under_test as rules_system
from reasonsmith.examples.frontier_risk_scorer import system_under_test as scorer_system
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

PACK = load_pack("seoul_frontier_ai_safety_2024")
ALL_SIGNALS = {signal for req in PACK.requirements for signal in req.requires}


class CountingTarget:
    def __init__(self) -> None:
        self.calls = 0

    def decide(self, case: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {
            "artifact_logs_model_evaluation_results": "evaluation",
            "artifact_logs_training_and_testing_process": "training",
            "artifact_logs_systemic_risk_assessment": "assessment",
            "artifact_logs_systemic_risk_mitigation": "mitigation",
            "artifact_logs_corrective_measures": "corrective",
            "reviews_and_sign_offs": "review",
            "signer": "signer",
            "provenance_technical_documentation": "technical documentation",
            "scope_statements_capabilities_and_limitations": "limitations",
            "scope_statements_explanation_scope": "external involvement",
            "artifact_logs_frontier_risk_score": 0.8,
            "scope_statements_frontier_risk_threshold": 0.8,
            "artifact_logs_mitigation_available": 0.0,
            "artifact_logs_deployment_decision": 0.0,
        }


def _counting(status: str | None) -> tuple[CallableAdapter, CountingTarget]:
    target = CountingTarget()
    sut = CallableAdapter(
        target,
        declared_capabilities=ALL_SIGNALS,
        test_inputs=[{}],
        frontier_ai_status=status,
    )
    sut.system_scope = "general-purpose"
    return sut, target


def test_pack_has_immutable_frontier_gate_and_eight_commitments():
    assert PACK.frontier_trigger == "frontier_ai_status == frontier"
    assert len(PACK.requirements) == 8
    assert (
        PACK.get_requirement("seoul_frontier_iv_no_deployment_above_threshold").formalism
        == "logical"
    )


@pytest.mark.parametrize("status", [None, "not-frontier"])
def test_missing_or_not_frontier_is_not_applicable_without_running_system(status: str | None):
    sut, target = _counting(status)
    report = check_conformance(sut, PACK, system_scope="general-purpose")
    assert all(result.verdict is Verdict.NOT_APPLICABLE for result in report.results)
    assert all(result.strength is None for result in report.results)
    assert target.calls == 0
    if status is None:
        assert report.results[0].details["frontier_ai_status"] == "undeclared"
    else:
        assert report.results[0].details["frontier_ai_status"] == "not-frontier"
    assert "self-declares frontier_ai_status='frontier'" in report.results[0].evidence_summary


def test_frontier_system_reaches_the_pack_after_scope_gate():
    sut, target = _counting("frontier")
    report = check_conformance(sut, PACK, system_scope="general-purpose")
    assert target.calls > 0
    assert all(result.verdict is not Verdict.NOT_APPLICABLE for result in report.results)
    iv = report.results[3]
    assert iv.verdict is Verdict.SATISFIED
    assert iv.strength in {Strength.OBSERVED, Strength.PROBED}


def test_explicit_status_argument_overrides_adapter_attribute():
    sut, target = _counting("not-frontier")
    report = check_conformance(
        sut, PACK, system_scope="general-purpose", frontier_ai_status="frontier"
    )
    assert target.calls > 0
    assert report.results[3].strength in {Strength.OBSERVED, Strength.PROBED}


def test_the_two_depth_examples_reach_probed_and_proved():
    scorer = check_conformance(scorer_system(), PACK, system_scope="general-purpose")
    rules = check_conformance(rules_system(), PACK, system_scope="general-purpose")
    assert scorer.results[3].strength is Strength.PROBED
    assert rules.results[3].strength is Strength.PROVED
    assert scorer.results[3].verdict is Verdict.SATISFIED
    assert rules.results[3].verdict is Verdict.SATISFIED


def test_invalid_frontier_status_is_refused_before_execution():
    with pytest.raises(ValueError, match="frontier AI status"):
        _counting("maybe")


def test_frontier_status_normalizes_empty_and_refuses_non_string():
    sut, _target = _counting("")
    assert sut.frontier_ai_status is None
    with pytest.raises(TypeError, match="frontier AI status"):
        _counting(1)  # type: ignore[arg-type]



def test_direct_requirement_evaluation_keeps_the_loaded_pack_frontier_gate():
    sut, target = _counting(None)
    req = PACK.get_requirement("seoul_frontier_iv_no_deployment_above_threshold")
    result = evaluate_requirement(req, sut, system_scope="general-purpose")
    assert result.verdict is Verdict.NOT_APPLICABLE
    assert result.strength is None
    assert target.calls == 0


def test_pack_context_propagates_frontier_gate_to_manually_constructed_requirements():
    from dataclasses import replace

    from reasonsmith.spec import Pack

    req = replace(PACK.requirements[0], frontier_trigger="")
    pack = Pack(
        id="manual-frontier",
        title="manual",
        description="manual",
        requirements=(req,),
        frontier_trigger=PACK.frontier_trigger,
    )
    assert pack.requirements[0].frontier_trigger == PACK.frontier_trigger


def test_conflicting_frontier_context_cannot_disable_the_pack_gate():
    sut, target = _counting(None)
    req = PACK.get_requirement("seoul_frontier_iv_no_deployment_above_threshold")
    with pytest.raises(ValueError, match="unsupported frontier trigger"):
        evaluate_requirement(req, sut, frontier_trigger="other-gate")
    assert target.calls == 0
