"""Tests for Stage 3 of the v0.2 overhaul: the proved engine and RulesAdapter.

What this module is for:
  Verifies formal logic proof generation via Z3, counterexample extraction and reproduction,
  unsupported construct handling, timeout handling, and report rendering for proved results.
"""

from __future__ import annotations

import pytest
import z3

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.rulelang import UnsupportedConstructError, preprocess_spec
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


def test_reassignment_is_executed_in_order_not_treated_as_a_contradiction():
    """A rule that reassigns a name means what it means when executed, not `x == x + 10`."""
    rules = ["score = base", "score = score + 10", "approved = score >= 50"]
    variables = {"base": "int", "score": "int", "approved": "bool"}
    sut = RulesAdapter(rules=rules, variables=variables)

    # The system does not approve everyone, and the solver must agree with its own decide().
    res = evaluate_requirement(
        _logical_req(spec="approved == True", requires=("base", "approved")), sut
    )
    assert res.verdict == Verdict.VIOLATED
    assert sut.decide(res.details["counterexample"])["approved"] is False

    # What the rules do establish is proved.
    res = evaluate_requirement(
        _logical_req(spec="base >= 40 implies approved == True", requires=("base", "approved")),
        sut,
    )
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED


def test_unsatisfiable_premises_are_not_a_proof():
    """Constraints no input can satisfy make every property vacuously unsat: report no evidence."""
    sut = RulesAdapter(
        rules=["approved = income >= 30000"],
        variables={"income": "real", "approved": "bool"},
        constraints=["income > 10", "income < 5"],
    )

    res = evaluate_requirement(
        _logical_req(spec="approved == True", requires=("income", "approved")), sut
    )
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert res.details["result"] == "unsatisfiable_premises"


def test_non_boolean_spec_degrades_instead_of_aborting_the_run():
    """A spec that is not a property is one not-evaluated requirement, not a dead run."""
    sut = RulesAdapter(
        rules=["approved = income >= 30000"],
        variables={"income": "real", "approved": "bool"},
    )
    req_bad = _logical_req(req_id="r_bad", spec="income + 1", requires=("income",))
    req_good = _logical_req(
        req_id="r_good", spec="income >= 30000 implies approved == True",
        requires=("income", "approved"),
    )

    report = check_conformance(sut, Pack("p", "P", "", (req_bad, req_good)))
    by_id = {r.requirement_id: r for r in report.results}
    assert by_id["r_bad"].verdict == Verdict.INCONCLUSIVE
    assert by_id["r_bad"].strength is None
    assert by_id["r_good"].verdict == Verdict.SATISFIED


def test_nested_and_augmented_statements_are_modelled_or_refused_by_both_sides():
    """Neither the encoder nor the interpreter may skip a statement it does not model."""
    nested = RulesAdapter(
        rules=["if x > 0:\n    y = 1\n    if x > 5:\n        y = 99\nelse:\n    y = 0"],
        variables={"x": "int", "y": "int"},
    )
    res = evaluate_requirement(_logical_req(spec="y <= 1", requires=("x", "y")), nested)
    assert res.verdict == Verdict.VIOLATED
    assert nested.decide(res.details["counterexample"])["y"] == 99
    assert evaluate_requirement(
        _logical_req(spec="y <= 99", requires=("x", "y")), nested
    ).verdict == Verdict.SATISFIED

    augmented = RulesAdapter(rules=["y = 1", "y += 5"], variables={"y": "int"})
    with pytest.raises(UnsupportedConstructError):
        augmented.decide({})
    assert evaluate_requirement(
        _logical_req(spec="y <= 1", requires=("y",)), augmented
    ).verdict == Verdict.INCONCLUSIVE


def test_arrow_rewriting_respects_parentheses_and_precedence():
    """Operator rewriting must not silently produce a different property."""
    assert "==" in preprocess_spec("approved <=> income >= 30000")

    equivalence = RulesAdapter(
        rules=["approved = income >= 30000"],
        variables={"income": "real", "approved": "bool"},
    )
    res = evaluate_requirement(
        _logical_req(spec="approved <=> income >= 30000", requires=("income", "approved")),
        equivalence,
    )
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED

    # A parenthesised implication is usable, and binds tighter than the surrounding `and`.
    grouped = RulesAdapter(
        rules=["b = a", "c = True"], variables={"a": "bool", "b": "bool", "c": "bool"}
    )
    res = evaluate_requirement(
        _logical_req(spec="(a -> b) and c", requires=("a", "b", "c")), grouped
    )
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED


def test_pack_text_is_never_executed_as_python():
    """Rule and spec text is data: a construct outside the whitelist is refused, not run."""
    escape = "().__class__.__base__.__subclasses__()"
    sut = RulesAdapter(rules=[f"y = len({escape})"], variables={"y": "int"})

    with pytest.raises(UnsupportedConstructError):
        sut.decide({})

    res = evaluate_requirement(_logical_req(spec="y >= 0", requires=("y",)), sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None


def test_unverified_counterexample_is_not_rendered_as_a_violation(monkeypatch):
    """A not-evaluated result must never render the red violation callout."""
    sut = RulesAdapter(
        rules=["approved = income >= 30000"],
        variables={"income": "real", "approved": "bool"},
    )
    monkeypatch.setattr(sut, "decide", lambda case: {"income": 35000, "approved": False})
    req = _logical_req(spec="approved == False", requires=("income", "approved"))

    report = check_conformance(sut, Pack("p", "P", "", (req,)))
    assert report.results[0].verdict == Verdict.INCONCLUSIVE
    assert "VIOLATED — Formal Counterexample Input" not in report.render_html()


def test_declared_capabilities_exclude_callee_and_module_names():
    """Callee names are not signals the system claims it can emit."""
    sut = RulesAdapter(rules=["y = abs(x) + math.pi"])
    assert sut.capabilities() == {"x", "y"}


def test_capability_discovery_reads_constraints_the_way_the_engine_does():
    """A constraint written with an arrow still contributes its variables to the capability set."""
    sut = RulesAdapter(rules=["approved = flagged"], constraints=["reviewed -> flagged"])
    assert {"reviewed", "flagged", "approved"} <= sut.capabilities()

    # The signal exists, so the requirement must not be dismissed as unattainable as built.
    res = evaluate_requirement(
        _logical_req(spec="approved == flagged", requires=("reviewed", "approved")), sut
    )
    assert res.strength is not Strength.UNATTAINABLE
    assert not res.signals_missing


def test_bare_expression_rules_are_refused_by_both_sides():
    """An expression asserts nothing to one side and everything to the other: refuse it."""
    asserted = RulesAdapter(
        rules=["approved = income >= 30000", "income > 100"],
        variables={"income": "real", "approved": "bool"},
    )
    res = evaluate_requirement(
        _logical_req(spec="income > 100", requires=("income", "approved")), asserted
    )
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    with pytest.raises(UnsupportedConstructError):
        asserted.decide({"income": 5})

    in_branch = RulesAdapter(
        rules=["if x > 0:\n    x > 100\nelse:\n    y = 0"], variables={"x": "int", "y": "int"}
    )
    res = evaluate_requirement(_logical_req(spec="x > 100", requires=("x", "y")), in_branch)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None


def test_declared_sorts_never_become_hidden_input_constraints():
    """A declared sort describes the system; it may not be satisfied by narrowing the inputs."""
    widened = RulesAdapter(
        rules=["half = x * 0.5"], variables={"x": "int", "half": "int"}
    )
    res = evaluate_requirement(_logical_req(spec="x % 2 == 0", requires=("x", "half")), widened)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert widened.decide({"x": 3})["half"] == 1.5

    divided = RulesAdapter(
        rules=["half = x / 2"], variables={"x": "int", "half": "int"}, constraints=["x == 5"]
    )
    res = evaluate_requirement(_logical_req(spec="half == 2", requires=("x", "half")), divided)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert divided.decide({"x": 5})["half"] == 2.5


def test_encoding_disagreeing_with_the_interpreter_is_not_a_proof():
    """Z3 and Python disagree on `%` with a negative divisor; the witness check must catch it."""
    sut = RulesAdapter(
        rules=["y = x % -3"], variables={"x": "int", "y": "int"}, constraints=["x == 7"]
    )

    res = evaluate_requirement(_logical_req(spec="y == 1", requires=("x", "y")), sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "does not agree with the declared logic" in res.evidence_summary
    assert sut.decide({"x": 7})["y"] == -2


def test_division_is_true_division_on_both_sides():
    """`/` means the same thing to the solver and to the interpreter."""
    sut = RulesAdapter(
        rules=["half = x / 2"],
        variables={"x": "int", "half": "real"},
        constraints=["x == 5"],
    )
    res = evaluate_requirement(_logical_req(spec="half == 2.5", requires=("x", "half")), sut)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert sut.decide({"x": 5})["half"] == 2.5


def test_arrow_rewriting_leaves_string_literals_alone():
    """An arrow inside a string literal is data, not an operator."""
    assert preprocess_spec('note == "a -> b"') == 'note == "a -> b"'

    sut = RulesAdapter(
        rules=['flagged = note == "a -> b"'],
        variables={"note": "str", "flagged": "bool"},
    )
    res = evaluate_requirement(
        _logical_req(
            spec='Implies(note == "a -> b", flagged == True)',
            requires=("note", "flagged"),
        ),
        sut,
    )
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED


def test_counterexample_replayed_on_declared_logic_says_so():
    """A system exposing only logic() is replayed through it, and the report says so."""
    class LogicOnlySUT(BaseSUT):
        def logic(self):
            return {
                "variables": {"income": "real", "approved": "bool"},
                "rules": ["approved = income >= 30000"],
                "constraints": [],
            }

    sut = LogicOnlySUT(declared_capabilities={"income", "approved"})
    res = evaluate_requirement(
        _logical_req(spec="approved == True", requires=("income", "approved")), sut
    )
    assert res.verdict == Verdict.VIOLATED
    assert "declared logic from sut.logic()" in res.evidence_summary
    assert "exposes no decide()" in res.evidence_summary
