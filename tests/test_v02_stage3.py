"""Tests for Stage 3 of the v0.2 overhaul: the proved engine and RulesAdapter.

What this module is for:
  Verifies formal logic proof generation via Z3, counterexample extraction and reproduction,
  unsupported construct handling, timeout handling, and report rendering for proved results.
"""

from __future__ import annotations

import z3

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.spec import Pack, Requirement
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict


def _logical_req(
    req_id: str = "logic_r1",
    spec: str = "income >= 30000 and age >= 18 implies approved == True",
    requires: tuple[str, ...] = ("income", "age", "approved"),
    binding: bool = True,
    scope: str = "",
) -> Requirement:
    return Requirement(
        id=req_id,
        source_document="Internal Policy",
        article_clause="Section 1.1",
        verbatim_text="Eligible applicants must be approved.",
        stakeholder="Compliance",
        formalism="logical",
        spec=spec,
        requires=requires,
        binding=binding,
        scope=scope,
    )


def test_property_holds_for_all_inputs_proved():
    """A property that genuinely holds for all inputs under system logic is proved."""
    rules = [
        "eligible = age >= 18 and income >= 25000",
        "approved = eligible and credit_score >= 650",
    ]
    variables = {
        "age": "int",
        "income": "real",
        "credit_score": "int",
        "eligible": "bool",
        "approved": "bool",
    }
    constraints = ["age >= 0", "income >= 0", "credit_score >= 0"]

    sut = RulesAdapter(rules=rules, variables=variables, constraints=constraints)

    req = _logical_req(
        spec="income >= 30000 and age >= 18 and credit_score >= 700 implies approved == True",
        requires=("income", "age", "credit_score", "approved"),
    )

    res = evaluate_requirement(req, sut)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert "Proved for all inputs" in res.evidence_summary
    assert res.details["result"] == "unsat"


def test_property_fails_with_verified_counterexample():
    """A property that fails produces a verified counterexample reproduced on the SUT."""
    rules = [
        "eligible = age >= 18 and income >= 25000",
        "approved = eligible and credit_score >= 650",
    ]
    variables = {
        "age": "int",
        "income": "real",
        "credit_score": "int",
        "eligible": "bool",
        "approved": "bool",
    }
    constraints = ["age >= 0", "income >= 0", "credit_score >= 0"]

    sut = RulesAdapter(rules=rules, variables=variables, constraints=constraints)

    # Claim that anyone with income >= 30000 gets approved (regardless of age/credit)
    req = _logical_req(
        spec="income >= 30000 implies approved == True",
        requires=("income", "approved"),
    )

    res = evaluate_requirement(req, sut)
    assert res.verdict == Verdict.VIOLATED
    assert res.strength == Strength.PROVED
    assert "counterexample" in res.details
    ce = res.details["counterexample"]
    assert ce["income"] >= 30000

    # Feeding that exact counterexample back through SUT must reproduce the violation
    sut_output = sut.decide(ce)
    assert sut_output["income"] >= 30000
    assert sut_output["approved"] is False


def test_unsupported_construct_reported_not_evaluated():
    """A logic or spec using an unsupported construct is reported not evaluated, never proved."""
    rules = [
        "y = math.sin(x)",  # math.sin is unsupported
    ]
    variables = {"x": "real", "y": "real"}

    sut = RulesAdapter(rules=rules, variables=variables)
    req = _logical_req(spec="y <= 1.0", requires=("x", "y"))

    res = evaluate_requirement(req, sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "unsupported construct" in res.evidence_summary.lower()


def test_solver_timeout_reported_not_evaluated(monkeypatch):
    """A solver timeout path is reported as not evaluated with a reason stated."""
    rules = [
        "approved = True",
    ]
    variables = {"approved": "bool"}
    sut = RulesAdapter(rules=rules, variables=variables)
    req = _logical_req(spec="approved == True", requires=("approved",))

    monkeypatch.setattr(z3.Solver, "check", lambda self: z3.unknown)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda self: "timeout")

    res = ProvedEngine.evaluate(req, sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "timeout" in res.evidence_summary


def test_system_without_logic_reported_not_evaluated():
    """A system exposing no logic (sut.logic() is None) is reported not evaluated."""
    class NoLogicSUT(BaseSUT):
        def logic(self):
            return None

    sut = NoLogicSUT(declared_capabilities={"income", "approved"})
    req = _logical_req(
        spec="income >= 30000 implies approved == True",
        requires=("income", "approved"),
    )

    res = evaluate_requirement(req, sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "no decision logic exposed" in res.evidence_summary


def test_counterexample_verification_failure_reported_not_evaluated(monkeypatch):
    """If solver finds a model but SUT verification fails, report not evaluated."""
    rules = ["approved = (income >= 30000)"]
    variables = {"income": "real", "approved": "bool"}
    sut = RulesAdapter(rules=rules, variables=variables)

    # Monkeypatch decide on sut to return something where spec actually holds
    monkeypatch.setattr(sut, "decide", lambda case: {"income": 35000, "approved": False})

    # Fake a solver output sat by passing a failing spec
    req_failing = _logical_req(spec="approved == False", requires=("income", "approved"))

    res = evaluate_requirement(req_failing, sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "Never report proved from unverified evidence" in res.evidence_summary


def test_conformance_report_rendering_proved_agrees():
    """Text and HTML renderers agree on proved results and counts."""
    rules = [
        "eligible = age >= 18 and income >= 25000",
        "approved = eligible and credit_score >= 650",
    ]
    variables = {
        "age": "int",
        "income": "real",
        "credit_score": "int",
        "eligible": "bool",
        "approved": "bool",
    }
    constraints = ["age >= 0", "income >= 0", "credit_score >= 0"]
    sut = RulesAdapter(rules=rules, variables=variables, constraints=constraints)

    req1 = _logical_req(
        req_id="r1_proved",
        spec="income >= 30000 and age >= 18 and credit_score >= 700 implies approved == True",
        requires=("income", "age", "credit_score", "approved"),
    )
    req2 = _logical_req(
        req_id="r2_violated",
        spec="income >= 30000 implies approved == True",
        requires=("income", "approved"),
    )

    pack = Pack("test_proved_pack", "Test Proved Pack", "", (req1, req2))
    report = check_conformance(sut, pack, system_name="CreditRuleSystem")

    # Headline counts
    assert report.counts["proved"] == 1
    assert report.counts["violated"] == 1
    assert "1 proved, 1 violated" in report.headline

    # Text rendering
    text = report.render_text()
    assert "[PROVED] r1_proved" in text
    assert "satisfied" in text
    assert "violated" in text

    # HTML rendering
    html = report.render_html()
    assert "active-proved" in html
    assert "r1_proved" in html
    assert "r2_violated" in html
    assert "VIOLATED — Formal Counterexample Input" in html
