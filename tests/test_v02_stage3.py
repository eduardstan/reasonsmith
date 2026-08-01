"""Tests for Stage 3 of the v0.2 overhaul: the proved engine and RulesAdapter.

What this module is for:
  Verifies formal logic proof generation via Z3, counterexample extraction and reproduction,
  unsupported construct handling, timeout handling, and report rendering for proved results.
"""

from __future__ import annotations

import pytest
import z3

from reasonsmith import report as report_module
from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines import proved
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
    is_present,
    parse_expression,
    preprocess_spec,
)
from reasonsmith.spec import Pack, Requirement, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict


def _logical_req(
    req_id: str = "logic_r1",
    spec: str = "income >= 30000 and age >= 18 implies approved == True",
    rationale: str = "Why this duty exists, in English.",
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
        rationale=rationale,
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
        rationale="Why this duty exists, in English.",
        requires=("income", "age", "credit_score", "approved"),
    )

    res = evaluate_requirement(req, sut)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert "Proved for all inputs" in res.evidence_summary
    assert res.details["result"] == "unsat"


def test_a_logical_boolean_constant_comparison_still_reaches_proved():
    sut = RulesAdapter(
        rules=["approved = True"],
        variables={"approved": "bool"},
    )
    req = _logical_req(spec="approved == True", requires=("approved",))

    res = evaluate_requirement(req, sut)

    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
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
        rationale="Why this duty exists, in English.",
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
        rationale="Why this duty exists, in English.",
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
        rationale="Why this duty exists, in English.",
        requires=("income", "age", "credit_score", "approved"),
    )
    req2 = _logical_req(
        req_id="r2_violated",
        spec="income >= 30000 implies approved == True",
        rationale="Why this duty exists, in English.",
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


def test_conformance_acquires_logic_once_for_all_proved_requirements():
    class CountingRulesAdapter(RulesAdapter):
        def __init__(self):
            super().__init__(rules=["approved = True"], variables={"approved": "bool"})
            self.logic_reads = 0

        def logic(self):
            self.logic_reads += 1
            return super().logic()

    sut = CountingRulesAdapter()
    req1 = _logical_req(req_id="r1", spec="approved == True", requires=("approved",))
    req2 = _logical_req(req_id="r2", spec="approved == True", requires=("approved",))

    report = check_conformance(sut, Pack("p", "P", "", (req1, req2)))

    assert sut.logic_reads == 1
    assert all(result.strength == Strength.PROVED for result in report.results)


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


def test_modulo_follows_python_semantics_for_any_divisor():
    """Z3's `mod` is non-negative; Python's `%` takes the sign of the divisor. Encode Python's."""
    literal = RulesAdapter(rules=["r = x % -3"], variables={"x": "int", "r": "int"})
    res = evaluate_requirement(_logical_req(spec="r >= 0", requires=("x", "r")), literal)
    assert res.verdict == Verdict.VIOLATED
    assert literal.decide({"x": 1})["r"] == -2
    assert literal.decide(res.details["counterexample"])["r"] < 0

    variable = RulesAdapter(
        rules=["r = x % y"],
        variables={"x": "int", "y": "int", "r": "int"},
        constraints=["y < 0"],
    )
    res = evaluate_requirement(_logical_req(spec="r >= 0", requires=("x", "y", "r")), variable)
    assert res.verdict != Verdict.SATISFIED
    assert variable.decide({"x": 1, "y": -3})["r"] == -2

    positive = RulesAdapter(
        rules=["r = x % 3"], variables={"x": "int", "r": "int"}, constraints=["x >= 0"]
    )
    res = evaluate_requirement(_logical_req(spec="r >= 0 and r < 3", requires=("x", "r")), positive)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED


def test_encoding_disagreeing_with_the_interpreter_is_not_a_proof(monkeypatch):
    """If the two implementations of the language ever part ways, no verdict may be read off."""
    sut = RulesAdapter(rules=["y = x + 1"], variables={"x": "int", "y": "int"})

    def wrong_interpreter(stmts, env):
        env["y"] = 999

    monkeypatch.setattr(proved, "execute_statements", wrong_interpreter)

    res = evaluate_requirement(_logical_req(spec="y > x", requires=("x", "y")), sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "does not agree with the declared logic" in res.evidence_summary
    assert "encoding_mismatch" in res.details


def test_a_proof_over_reals_says_it_is_a_proof_over_the_rationals():
    """`real` is exact to the solver and float64 to the system; the verdict must name that gap."""
    reals = RulesAdapter(
        rules=["t = a + b", "d = t - b"],
        variables={"a": "real", "b": "real", "t": "real", "d": "real"},
    )

    res = evaluate_requirement(_logical_req(spec="d == a", requires=("a", "b", "d")), reals)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert res.details["limits"] == proved.REAL_ARITHMETIC_LIMIT
    assert proved.REAL_ARITHMETIC_LIMIT in res.evidence_summary
    # The limit is not decoration: the system's own float64 arithmetic falsifies the property.
    decided = reals.decide({"a": 0.1, "b": 0.2})
    assert decided["d"] != decided["a"]

    # A proof with no real arithmetic in it carries no such limit.
    integers = RulesAdapter(
        rules=["total = x + y"], variables={"x": "int", "y": "int", "total": "int"}
    )
    res = evaluate_requirement(
        _logical_req(spec="total - y == x", requires=("x", "y", "total")), integers
    )
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert "limits" not in res.details


def test_rules_undefined_on_the_witness_are_named_as_such():
    """A divisor the solver may zero is a missing constraint, not an encoding disagreement."""
    sut = RulesAdapter(
        rules=["ratio = a / b"], variables={"a": "real", "b": "real", "ratio": "real"}
    )

    res = evaluate_requirement(_logical_req(spec="ratio == ratio", requires=("a", "b")), sut)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "rules_undefined_on_witness" in res.details
    assert "does not agree with the declared logic" not in res.evidence_summary
    assert "`constraints`" in res.evidence_summary

    guarded = RulesAdapter(
        rules=["ratio = a / b"],
        variables={"a": "real", "b": "real", "ratio": "real"},
        constraints=["b >= 1", "a >= 0"],
    )
    res = evaluate_requirement(_logical_req(spec="ratio >= 0", requires=("a", "b")), guarded)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED


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
            rationale="Why this duty exists, in English.",
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


# --------------------------------------------------------------------------------------
# GDPR Article 22 — the first `logical` duty in a shipped pack, exercised on statute.
#
# The systems below are small on purpose. What matters is that the property comes from
# `src/reasonsmith/packs/gdpr.toml` unchanged, not from a spec written to suit the test.
# --------------------------------------------------------------------------------------

#: Every signal the Article 22 proof duty reasons over, at the sort the rules use.
ART22_VARIABLES = {
    "artifact_logs_solely_automated": "bool",
    "artifact_logs_significant_effect": "bool",
    "artifact_logs_human_intervention_route": "bool",
    "provenance_basis_contract": "bool",
    "provenance_basis_union_or_member_state_law": "bool",
    "provenance_basis_explicit_consent": "bool",
    "provenance_basis_present": "bool",
}

#: A router that will not decide alone where the decision bites and no Article 22(2) basis is
#: present, and that opens the Article 22(3) route wherever point (a) or (c) is the basis.
ART22_CONFORMING_RULES = [
    "provenance_basis_present = provenance_basis_contract "
    "or provenance_basis_union_or_member_state_law or provenance_basis_explicit_consent",
    "artifact_logs_solely_automated = "
    "not (artifact_logs_significant_effect and not provenance_basis_present)",
    "artifact_logs_human_intervention_route = "
    "provenance_basis_contract or provenance_basis_explicit_consent",
]

#: The same router with Article 22(3) implemented and Article 22(1) not: it always decides
#: alone, so a significant decision with no basis at all is reachable.
ART22_VIOLATING_RULES = [
    "artifact_logs_solely_automated = True",
    "artifact_logs_human_intervention_route = "
    "provenance_basis_contract or provenance_basis_explicit_consent",
]

ART22_REQUIREMENT_ID = "gdpr_art22_1_no_prohibited_decision_for_any_input"


def _art22_requirement() -> Requirement:
    return load_pack("gdpr").get_requirement(ART22_REQUIREMENT_ID)


def _art22_system(rules: list[str]) -> RulesAdapter:
    return RulesAdapter(rules=rules, variables=ART22_VARIABLES, constraints=[])


def test_gdpr_art22_holds_for_every_input_is_proved():
    """The shipped Article 22 duty reaches `proved` on a system whose rules cannot breach it."""
    req = _art22_requirement()
    assert req.formalism == "logical"

    res = evaluate_requirement(req, _art22_system(ART22_CONFORMING_RULES))

    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROVED
    assert res.details["result"] == "unsat"
    # No real arithmetic is involved, so the rational/float64 limit does not attach here.
    assert "limits" not in res.details


def test_gdpr_art22_violation_reports_a_counterexample_that_reproduces():
    """A system missing the Article 22(2) gate is violated; the input is reported and replays."""
    req = _art22_requirement()
    sut = _art22_system(ART22_VIOLATING_RULES)

    res = evaluate_requirement(req, sut)

    assert res.verdict == Verdict.VIOLATED
    assert res.strength == Strength.PROVED
    counterexample = res.details["counterexample"]
    assert counterexample["artifact_logs_significant_effect"] is True
    assert not any(
        counterexample[basis]
        for basis in (
            "provenance_basis_contract",
            "provenance_basis_union_or_member_state_law",
            "provenance_basis_explicit_consent",
        )
    )

    # Replayed through the system's own decide(), the same input fails the same property.
    decision = sut.decide(counterexample)
    assert decision["artifact_logs_solely_automated"] is True
    assert eval_expression(parse_expression(req.spec), dict(decision)) is False
    assert "the system's own decide()" in res.evidence_summary


def test_gdpr_art22_without_exposed_logic_is_not_evaluated_never_satisfied():
    """A system that can emit every signal but exposes no logic proves nothing, and says so."""
    class OpaqueSUT(BaseSUT):
        def logic(self):
            return None

    req = _art22_requirement()
    res = evaluate_requirement(req, OpaqueSUT(declared_capabilities=set(req.requires)))

    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "no decision logic exposed" in res.evidence_summary


def test_gdpr_art22_record_duties_are_untouched_by_the_proof_duty():
    """The two Article 22 record duties still read `requires` off a trace, exactly as before."""
    pack = load_pack("gdpr")
    trace = [
        {
            "artifact_logs_decision_record": {"id": "dec-1"},
            "provenance_active_exceptions": ["none"],
            "scope_statements_local_vs_global": "local",
        }
    ]

    class RecordSUT(BaseSUT):
        def decisions(self):
            return trace

    sut = RecordSUT(declared_capabilities={s for r in pack.requirements for s in r.requires})

    for req_id, signals in (
        ("gdpr_art22_1_automated_decision_prohibition",
         ("artifact_logs_decision_record", "provenance_active_exceptions")),
        ("gdpr_art22_3_safeguards_human_intervention",
         ("artifact_logs_decision_record", "scope_statements_local_vs_global")),
    ):
        req = pack.get_requirement(req_id)
        assert req.formalism == "record"
        assert req.requires == signals
        res = evaluate_requirement(req, sut)
        assert res.verdict == Verdict.SATISFIED, req_id
        assert res.strength == Strength.OBSERVED, req_id


# --------------------------------------------------------------------------------------
# A requirement's fragment says what the property is; the system says how strongly it can
# be discharged. These are the tests that make that separation falsifiable.
# --------------------------------------------------------------------------------------


def _record_req(spec: str, requires: tuple[str, ...], req_id: str = "rec_r1") -> Requirement:
    return Requirement(
        id=req_id,
        source_document="Internal Policy",
        article_clause="Section 3.1",
        verbatim_text="Every decision must be given a reason.",
        stakeholder="affected individual",
        formalism="record",
        spec=spec,
        rationale="Every decision carries a reason a person can read.",
        requires=requires,
        binding=True,
        scope="",
    )


#: A rule engine that always writes a reason, whatever the input. The reason is a string, which
#: is the realistic case: this is what an auditor means by "it can prove it always gives one".
_REASON_RULES = [
    "approved = credit_score >= 650",
    'if approved:\n'
    '    artifact_logs_reason_explanation = "approved on score"\n'
    'else:\n'
    '    artifact_logs_reason_explanation = "declined on score"\n',
]
_REASON_VARIABLES = {
    "credit_score": "int",
    "approved": "bool",
    "artifact_logs_reason_explanation": "str",
}


def test_a_record_duty_reaches_proved_when_the_system_exposes_its_logic():
    """The same presence property is `observed` off a trace and `proved` against `logic()`.

    This is the whole point of separating what a requirement *says* from what discharges it. The
    duty is a record-keeping duty either way; nothing about it changed. What changed is that a
    system exposing rules that always assign the reason can have the property established for
    every input the constraints admit, instead of for the decisions it happened to log.
    """
    req = _record_req(
        "present(artifact_logs_reason_explanation)", ("artifact_logs_reason_explanation",)
    )

    exposed = RulesAdapter(
        rules=_REASON_RULES,
        variables=_REASON_VARIABLES,
        declared_capabilities={"artifact_logs_reason_explanation"},
        test_inputs=[{"credit_score": 700}, {"credit_score": 500}],
    )
    proved_result = evaluate_requirement(req, exposed)
    assert proved_result.verdict == Verdict.SATISFIED
    assert proved_result.strength == Strength.PROVED

    class TraceOnlySUT(BaseSUT):
        """The same decisions, from a system that exposes nothing but its log."""

        def decisions(self):
            return [
                {"artifact_logs_reason_explanation": "approved on score"},
                {"artifact_logs_reason_explanation": "declined on score"},
            ]

    observed_result = evaluate_requirement(
        req, TraceOnlySUT(declared_capabilities={"artifact_logs_reason_explanation"})
    )
    assert observed_result.verdict == Verdict.SATISFIED
    assert observed_result.strength == Strength.OBSERVED


def test_a_record_duty_reaches_probed_when_the_system_can_only_be_re_run():
    """`decide()` without `logic()` puts a record duty on the probe rung, never on the proof one."""
    req = _record_req(
        "present(artifact_logs_reason_explanation)", ("artifact_logs_reason_explanation",)
    )

    class OpaqueButRunnable(BaseSUT):
        def __init__(self):
            super().__init__({"artifact_logs_reason_explanation"})

        def decisions(self):
            return [{"credit_score": 700, "artifact_logs_reason_explanation": "approved"}]

        def decide(self, case):
            reason = "approved" if case.get("credit_score", 0) >= 650 else "declined"
            return {**case, "artifact_logs_reason_explanation": reason}

    result = evaluate_requirement(req, OpaqueButRunnable())
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    assert result.details["probe_budget"]["trials"] > 1


def test_a_record_duty_the_solver_cannot_reach_falls_to_the_engine_that_can():
    """The ladder is a search for evidence, not a commitment to the strongest engine.

    Here the rules read the signal and never write it, so `present()` is not something the
    exposed logic establishes and the proved engine says nothing. The duty must land on the
    strongest rung that *did* produce evidence — not lose its verdict to the engine that could
    not answer.
    """
    req = _record_req("present(artifact_logs_event_log)", ("artifact_logs_event_log",))
    sut = RulesAdapter(
        rules=["approved = artifact_logs_event_log >= 1"],
        variables={"artifact_logs_event_log": "int", "approved": "bool"},
        declared_capabilities={"artifact_logs_event_log"},
        test_inputs=[{"artifact_logs_event_log": 3}, {"artifact_logs_event_log": 0}],
    )
    assert sut.logic() is not None

    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED


def test_presence_is_not_proved_when_only_one_branch_assigns_the_signal():
    req = _record_req("present(artifact_logs_event_log)", ("artifact_logs_event_log",))
    sut = RulesAdapter(
        rules=["if condition:\n    artifact_logs_event_log = 1"],
        variables={"condition": "bool", "artifact_logs_event_log": "int"},
        declared_capabilities={"artifact_logs_event_log"},
        test_inputs=[{"condition": True}, {"condition": False}],
    )
    assert "artifact_logs_event_log" not in sut.decide({"condition": False})

    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROBED


class _BrokenLogicSUT(BaseSUT):
    """A system whose optional `logic()` is present but broken, and whose trace is fine."""

    def __init__(self):
        super().__init__({"artifact_logs_reason_explanation"})
        self.logic_calls = 0

    def decisions(self):
        return [{"artifact_logs_reason_explanation": "approved on score"}]

    def logic(self):
        self.logic_calls += 1
        raise RuntimeError("logic export is broken")


def test_a_record_duty_survives_a_system_whose_logic_raises():
    """A broken optional interface must not cost a duty the evidence it does have.

    `logic()` raising establishes nothing, which is what `strength=None` means, so the search
    continues to the rung that can answer. Before the ladder read the callable surface instead
    of invoking it, this duty lost its verdict to an interface it never needed.
    """
    req = _record_req(
        "present(artifact_logs_reason_explanation)", ("artifact_logs_reason_explanation",)
    )
    sut = _BrokenLogicSUT()

    result = evaluate_requirement(req, sut)

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED
    assert sut.logic_calls == 1


def test_a_logical_duty_names_the_logic_failure_rather_than_propagating_it():
    req = _logical_req(
        spec="present(artifact_logs_reason_explanation)",
        requires=("artifact_logs_reason_explanation",),
    )
    sut = _BrokenLogicSUT()

    result = evaluate_requirement(req, sut)

    assert result.strength is None
    assert "RuntimeError" in result.evidence_summary
    assert "logic export is broken" in result.evidence_summary


def test_building_the_ladder_never_executes_the_system():
    """Selecting a rung is a question about the surface, never a call into the system."""
    req = _record_req(
        "present(artifact_logs_reason_explanation)", ("artifact_logs_reason_explanation",)
    )
    sut = _BrokenLogicSUT()
    resources = report_module._EvaluationResources(sut)

    ladder = report_module._engine_ladder(req, sut, None, resources)

    assert sut.logic_calls == 0
    assert [strength for strength, _ in ladder] == [Strength.PROVED, Strength.OBSERVED]


def test_a_raising_logic_is_attempted_once_per_evaluation():
    """The failure is cached like the trace's: the second reader gets it, not a second call."""
    sut = _BrokenLogicSUT()
    resources = report_module._EvaluationResources(sut)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            resources.logic()

    assert sut.logic_calls == 1


def test_a_temporal_duty_never_rises_above_observed():
    """No engine in this build reasons about a formula quantified over a trace.

    A system exposing `logic()` and `decide()` still gets `observed` for a temporal duty, because
    inventing a stronger rung for a claim no engine established is the overclaim this package
    exists to refuse.
    """
    req = Requirement(
        id="temporal_r1",
        source_document="Internal Policy",
        article_clause="Section 4.1",
        verbatim_text="A reason must accompany every decision, always.",
        stakeholder="affected individual",
        formalism="temporal",
        spec="always(present(artifact_logs_reason_explanation))",
        rationale="At every step of the log, a reason was recorded.",
        requires=("artifact_logs_reason_explanation",),
        binding=True,
        scope="",
    )
    sut = RulesAdapter(
        rules=_REASON_RULES,
        variables=_REASON_VARIABLES,
        declared_capabilities={"artifact_logs_reason_explanation"},
        test_inputs=[{"credit_score": 700}, {"credit_score": 500}],
    )
    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_the_solvers_blank_string_is_pythons_blank_string():
    """`present()` over a string must mean the same thing to Z3 as it does to the interpreter.

    `is_present` calls a string absent when `strip()` leaves nothing. The solver encodes that as
    "not in the language of blanks", so the two agree only while `BLANK_CHARACTERS` is exactly the
    set `str.strip()` removes. Approximating it with `x != ""` would prove presence for a value
    the trace semantics call absent — a proof of the wrong property, at the strongest rung.
    """
    assert set(proved.BLANK_CHARACTERS) == {
        chr(code) for code in range(0x110000) if chr(code).isspace()
    }
    for blank in ("", " ", "\t\n", "\xa0", " "):
        assert not is_present(blank)
    for carried in ("x", " x ", "0"):
        assert is_present(carried)


def test_a_presence_proof_refuses_the_blank_string_the_solver_could_choose():
    """A system whose rules can write a blank reason is not proved to have written one."""
    req = _record_req(
        "present(artifact_logs_reason_explanation)", ("artifact_logs_reason_explanation",)
    )
    sut = RulesAdapter(
        rules=[
            "approved = credit_score >= 650",
            'if approved:\n'
            '    artifact_logs_reason_explanation = "approved on score"\n'
            'else:\n'
            '    artifact_logs_reason_explanation = "  "\n',
        ],
        variables=_REASON_VARIABLES,
        declared_capabilities={"artifact_logs_reason_explanation"},
        test_inputs=[{"credit_score": 700}],
    )
    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED
