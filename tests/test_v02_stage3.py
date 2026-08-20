"""Tests for Stage 3 of the v0.2 overhaul: the proved engine and RulesAdapter.

What this module is for:
  Verifies formal logic proof generation via Z3, counterexample extraction and reproduction,
  unsupported construct handling, timeout handling, and report rendering for proved results.
"""

from __future__ import annotations

import ast

import pytest
import z3

from reasonsmith import report as report_module
from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines import proved
from reasonsmith.engines import temporal as temporal_engine
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
    is_present,
    parse_expression,
    parse_property,
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
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
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


def test_system_without_logic_or_a_trace_is_not_evaluated():
    """No logic and no decisions is no evidence, and the report names what was actually missing.

    What changed, and why: this used to assert the summary said *no decision logic exposed*, on the
    strength of that being the only rung a `logical` duty had. Now such a duty also admits a trace
    rung, and `_NO_LOGIC_TO_REASON_OVER` does what it has always done — a proof rung that never had
    any logic to reason over says nothing about this evaluation, so a lower rung's account of the
    evidence the system did supply displaces it. With no trace either, that account is the empty
    trace, which is the more useful thing to tell a reader holding a system that exposes neither.
    The claim being pinned is unchanged: not evaluated, `strength=None`, never satisfied.
    """
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
    assert "trace is empty" in res.evidence_summary


def test_the_proof_rung_still_names_the_missing_logic_when_it_is_asked_directly():
    """The message did not disappear; it stopped being the whole run's only account.

    `ProvedEngine` is what knows which interface was missing, and it still says so. Pinning it here
    keeps the diagnostic from being quietly lost while the ladder prefers a rung with evidence.
    """
    class NoLogicSUT(BaseSUT):
        def logic(self):
            return None

    req = _logical_req(
        spec="income >= 30000 implies approved == True",
        requires=("income", "approved"),
    )
    res = ProvedEngine.evaluate(req, NoLogicSUT(declared_capabilities={"income", "approved"}))
    assert res.strength is None
    assert "no decision logic exposed" in res.evidence_summary


def test_a_logical_duty_is_answered_from_a_trace_when_there_is_nothing_to_reason_over():
    """The point of the change: evidence that is right there is read rather than declined.

    A `logical` property is a property of one decision record — that is what puts it in
    `STATE_FRAGMENTS` — so a trace of decision records is evidence about it. Refusing to read one
    reported *not evaluated* because of the label on the fragment rather than because of the
    evidence, which is the defect fragment classification exists to prevent
    (`docs/semantics.md` §3.5).
    """
    class TraceOnlySUT(BaseSUT):
        def logic(self):
            return None

        def decisions(self):
            return [{"income": 41000, "approved": True}, {"income": 12000, "approved": False}]

    req = _logical_req(
        spec="income >= 30000 implies approved",
        requires=("income", "approved"),
    )
    res = evaluate_requirement(req, TraceOnlySUT(declared_capabilities={"income", "approved"}))
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.OBSERVED

    class BreachingSUT(TraceOnlySUT):
        def decisions(self):
            return [{"income": 41000, "approved": True}, {"income": 55000, "approved": False}]

    breach = evaluate_requirement(req, BreachingSUT(declared_capabilities={"income", "approved"}))
    assert breach.verdict == Verdict.VIOLATED
    assert breach.strength == Strength.OBSERVED
    assert breach.details["violation_step_indices"] == [1]


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
    # `Iff(...)` and never `==`: see `test_equivalence_connective.py` for why the distinction is
    # load-bearing, and for the pin that fails if the rewriter ever collapses it again.
    assert preprocess_spec("approved <=> income >= 30000").lstrip().startswith("Iff(")

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


def test_gdpr_art22_without_exposed_logic_is_never_proved_on_the_strength_of_a_sample():
    """The universal prohibition is not answered *for all inputs* by a log, and never was.

    What changed, and why: this used to assert not evaluated, because a system exposing no logic
    reached no engine at all. The intent behind that was never "refuse to look" — it was *do not
    report a universal prohibition satisfied on the strength of a sample*. That intent is now
    carried by the **strength label**, which is where it belongs. `observed` denotes "on the records
    supplied, and nothing here establishes they are representative" (`docs/semantics.md` §3, §4), so
    an `observed` verdict is not a claim about every input and cannot be read as one. What must
    never happen is this duty reaching `proved` without exposed logic, and that is what is pinned.

    An empty-trace system still has nothing to look at and is still not evaluated, which is the
    second half below.
    """
    req = _art22_requirement()

    class OpaqueSUT(BaseSUT):
        def logic(self):
            return None

        def decisions(self):
            # Every atom of the property is a bare Boolean, so every record must establish that
            # kind. These two are lawful: automated and significant, but on an Article 22(2)(b)
            # basis, which is the one branch that does not require the intervention route.
            lawful = dict.fromkeys(req.requires, False)
            lawful["artifact_logs_solely_automated"] = True
            lawful["artifact_logs_significant_effect"] = True
            lawful["provenance_basis_union_or_member_state_law"] = True
            return [dict(lawful), dict(lawful)]

    res = evaluate_requirement(req, OpaqueSUT(declared_capabilities=set(req.requires)))

    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.OBSERVED
    assert res.strength < Strength.PROVED
    assert "decision(s)" in res.evidence_summary

    class NoTraceSUT(BaseSUT):
        def logic(self):
            return None

    silent = evaluate_requirement(req, NoTraceSUT(declared_capabilities=set(req.requires)))
    assert silent.verdict == Verdict.INCONCLUSIVE
    assert silent.strength is None


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
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
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


def test_a_logical_duty_survives_a_system_whose_logic_raises():
    """A broken optional interface must not cost a logical duty the evidence it does have.

    What changed, and why: this used to assert the summary named the `RuntimeError`, because the
    proof rung was the only rung a logical duty had, so its failure was the whole account. Now such
    a duty also admits a trace rung, and the duty lands on it — which is exactly what
    `test_a_record_duty_survives_a_system_whose_logic_raises` has always asserted one rung over. The
    enduring claim is the one in the name: the exception is absorbed, never propagated, and the duty
    still reaches the strongest rung that produced evidence.

    Where no rung produces any, the failure is still named, and
    `test_a_logic_failure_is_named_when_no_rung_produced_evidence` pins that.
    """
    req = _logical_req(
        spec="present(artifact_logs_reason_explanation)",
        requires=("artifact_logs_reason_explanation",),
    )

    class _BrokenLogicTraceSUT(_BrokenLogicSUT):
        def decisions(self):
            return [
                {"artifact_logs_reason_explanation": "approved on score"},
                {"artifact_logs_reason_explanation": "length of credit history"},
            ]

    sut = _BrokenLogicTraceSUT()
    result = evaluate_requirement(req, sut)

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED
    assert sut.logic_calls == 1


def test_a_logic_failure_is_named_when_no_rung_produced_evidence():
    """The `RuntimeError` is still reachable; it stopped displacing a rung that had an answer."""
    req = _logical_req(
        spec="present(artifact_logs_reason_explanation)",
        requires=("artifact_logs_reason_explanation",),
    )
    sut = _BrokenLogicSUT()
    result = report_module._run_proof_rung(
        req, sut, None, report_module._EvaluationResources(sut)
    )

    assert result.strength is None
    assert "RuntimeError" in result.evidence_summary
    assert "logic export is broken" in result.evidence_summary


def test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow():
    """A stated limit with a sharp edge, found while giving the state fragment its trace rung.

    `preprocess_spec` rewrites `->` into `Implies(...)` before *parsing*, so the two spellings are
    the same property — this asserts that, rather than trusting it. But `to_stl` renders the spec
    text as the pack wrote it, and rtamt has infix `->` and no prefix `Implies`. So a `logical` duty
    spelled with the prefix form keeps its solver and replay rungs and is *not evaluated* against a
    trace, purely because of how it was typed.

    That is sound — never satisfied, never violated — and it is arbitrary, so the shipped Article 22
    duty is spelled with the arrow and this test is where the next pack author finds out. Teaching
    the renderer to lower the prefix form is a different and larger change than the ladder rung it
    was found under; it is recorded in `docs/semantics.md` §2 rather than smuggled in here.
    """
    equivalent = (
        "Implies(a and b, c)",
        "(a and b) -> c",
    )
    parsed = [ast.dump(parse_property(text)) for text in equivalent]
    assert parsed[0] == parsed[1], "the two spellings must remain the same property"

    class TraceSUT(BaseSUT):
        def logic(self):
            return None

        def decisions(self):
            return [{"a": True, "b": True, "c": True}] * 2

    prefix = evaluate_requirement(
        _logical_req(spec=equivalent[0], requires=("a", "b", "c")),
        TraceSUT(declared_capabilities={"a", "b", "c"}),
    )
    assert prefix.verdict == Verdict.INCONCLUSIVE
    assert prefix.strength is None

    arrow = evaluate_requirement(
        _logical_req(spec=equivalent[1], requires=("a", "b", "c")),
        TraceSUT(declared_capabilities={"a", "b", "c"}),
    )
    assert arrow.verdict == Verdict.SATISFIED
    assert arrow.strength == Strength.OBSERVED

    shipped = load_pack("gdpr").get_requirement(ART22_REQUIREMENT_ID)
    assert "Implies(" not in shipped.spec


def test_the_trace_rung_does_not_reach_every_logical_shape_and_says_so():
    """A stated limit of the trace rung, not a silent one.

    rtamt scores real-valued signals, and `validate_temporal_property` refuses the shapes it cannot
    render soundly — a comparison against a Boolean constant among them, which the `logical`
    fragment otherwise permits (`docs/semantics.md` §2). Such a duty keeps its solver and replay
    rungs and is reported *not evaluated* against a trace, never satisfied. Widening the monitor to
    cover it is a different change; reporting a verdict it did not establish would be the overclaim.
    """
    class TraceOnlySUT(BaseSUT):
        def logic(self):
            return None

        def decisions(self):
            return [{"approved": True}, {"approved": True}]

    req = _logical_req(spec="approved == True", requires=("approved",))
    result = evaluate_requirement(req, TraceOnlySUT(declared_capabilities={"approved"}))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "unsupported" in result.evidence_summary.lower()


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


def _temporal_req(
    spec: str = "always(present(artifact_logs_reason_explanation))",
    req_id: str = "temporal_r1",
    requires: tuple[str, ...] = ("artifact_logs_reason_explanation",),
) -> Requirement:
    return Requirement(
        id=req_id,
        source_document="Internal Policy",
        article_clause="Section 4.1",
        verbatim_text="A reason must accompany every decision, always.",
        stakeholder="affected individual",
        formalism="temporal",
        spec=spec,
        rationale="At every step of the log, a reason was recorded.",
        requires=requires,
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )


def _reason_sut(rules: list[str] | None = None) -> RulesAdapter:
    return RulesAdapter(
        rules=rules if rules is not None else _REASON_RULES,
        variables=_REASON_VARIABLES,
        declared_capabilities={"artifact_logs_reason_explanation"},
        test_inputs=[{"credit_score": 700}, {"credit_score": 500}],
    )


def test_only_always_reaches_the_temporal_proof_rung():
    """The replacement ceiling: `always(f)` proves, and every other temporal shape does not.

    This is what became of `test_a_temporal_duty_never_rises_above_observed`. The old ceiling was
    "no temporal duty ever rises above `observed`"; the new one is narrower and has to be checked
    from both sides, because a ceiling only stated for the case that passes is not a ceiling.
    `always(f)` reduces exactly — over a finite trace it holds iff `f` holds at every position, and
    every position is a decision the exposed logic admits — so it reaches `proved`. `eventually(f)`
    does not reduce: it asserts that some position *exists*, which is a fact about the trace a
    system emitted and not about the decisions its logic admits, so it stays where it was.
    """
    sut = _reason_sut()

    always = evaluate_requirement(_temporal_req(), sut)
    assert always.verdict == Verdict.SATISFIED
    assert always.strength == Strength.PROVED
    assert always.details["reduction"] == "always"

    eventually = evaluate_requirement(
        _temporal_req(spec="eventually(present(artifact_logs_reason_explanation))"), sut
    )
    assert eventually.verdict == Verdict.SATISFIED
    assert eventually.strength == Strength.OBSERVED


def test_a_nested_temporal_operator_does_not_reduce():
    """`always(eventually(f))` is not `always` over a state property, so the solver is not asked.

    The operand of the `always` has to be a property of one decision, or what the solver decides is
    not what the duty says. A shape check that only looked at the outermost call would hand Z3 an
    `eventually` it has no encoding for and read the refusal as an ordinary unsupported construct.
    """
    assert (
        temporal_engine.state_property_under_always(
            "always(eventually(present(artifact_logs_reason_explanation)))"
        )
        is None
    )
    result = evaluate_requirement(
        _temporal_req(spec="always(eventually(present(artifact_logs_reason_explanation)))"),
        _reason_sut(),
    )
    assert result.strength == Strength.OBSERVED


def test_a_temporal_violation_names_the_trace_it_is_and_is_not_about():
    """A `proved` temporal violation is existential, and the verdict has to say so.

    Satisfied quantifies universally and covers every trace the system can emit. Violated does not:
    the solver found one admissible input whose decision breaches the property, so *some* trace the
    system admits breaches the duty — which is a finding about the system as built, not about the
    trace this run read. Both halves of that asymmetry travel on the result, or a reader takes the
    two verdicts to be mirror images.
    """
    rules = [
        "approved = credit_score >= 650",
        "if approved:\n"
        '    artifact_logs_reason_explanation = "approved on score"\n'
        "else:\n"
        '    artifact_logs_reason_explanation = ""\n',
    ]
    result = evaluate_requirement(_temporal_req(), _reason_sut(rules))

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED
    assert "counterexample" in result.details
    assert result.details["trace_semantics"] == temporal_engine.TRACE_SEMANTICS
    assert "not a finding about the trace supplied here" in result.evidence_summary


#: The system's whole variable table: a score it is handed and an approval it computes. The
#: deviation signals are deliberately absent from it, which is the declaration that this system has
#: no notion of them — it emits values under those names into a record (below) without any variable
#: standing behind them, which is exactly the shape the defect was found in.
_UNCOMPUTED_MAGNITUDE_VARIABLES = {
    "score": "int",
    "approved": "bool",
}
_UNCOMPUTED_MAGNITUDE_SIGNALS = {
    "scope_statements_declared_deviation",
    "artifact_logs_decision_margin",
    "scope_statements_approximation_vs_guarantee",
}


#: The duty these tests were written against, in the shape it had before it moved to the artefact
#: basis. It is built here rather than loaded from the pack, and that is a deliberate exception to
#: this repository's rule that a duty test reads the shipped duty: what every test below exercises
#: is `engines/proved.py`'s guard on magnitudes the declared rules never compute, and the guard
#: needs a property comparing two of them. `gdpr_recital71_error_risk_minimised` was that property
#: until its left-hand side became a measurement (`engines.certificate.SEMANTICS_VALUE_GAP`), which
#: gives it a one-rung ladder and takes it off the proof rung entirely. No shipped duty has the
#: shape now, so the fixture carries it; the day one does, load that one instead.
def _magnitude_duty() -> Requirement:
    return Requirement(
        id="fixture_two_declared_magnitudes",
        source_document="Fixture",
        article_clause="Article 1",
        verbatim_text="A fixture clause, quoted from nothing.",
        stakeholder="fixture",
        formalism="temporal",
        spec="always(scope_statements_declared_deviation <= artifact_logs_decision_margin)",
        rationale="Two magnitudes compared, so the proof rung's direction guard has something "
                  "to refuse.",
        requires=(
            "scope_statements_declared_deviation",
            "scope_statements_approximation_vs_guarantee",
            "artifact_logs_decision_margin",
        ),
        binding=False,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="trigger-unmodelled",
        algebra="",
    )


def _deviation_sut(test_inputs: list[dict]) -> RulesAdapter:
    """A system deciding on a score alone, declaring the deviation signals and computing none."""
    return RulesAdapter(
        rules=["approved = score >= 650"],
        variables=_UNCOMPUTED_MAGNITUDE_VARIABLES,
        constraints=["score >= 0", "score <= 1000"],
        test_inputs=test_inputs,
        declared_capabilities=set(_UNCOMPUTED_MAGNITUDE_SIGNALS),
    )


def test_a_magnitude_the_rules_never_compute_is_not_proved_violated():
    """No proof verdict from arithmetic over two names no rule assigns.

    `_magnitude_duty` compares a declared deviation with a decision's own
    margin. A system that decides on a score alone computes neither, so both are free constants of
    the solver's encoding, and the solver will happily pick `deviation = 1, margin = 0`. The
    counterexample verification does not catch it: the reference interpreter is handed the same
    free inputs, so the "violation" reproduces. Left unguarded, a clean system was reported
    `violated` at `proved` — the one verdict that exits non-zero — on numbers nobody computed.

    Both halves are the fix. The duty must not reach a proof rung on such a system, and it must
    fall to the engine that reads the trace, which measures the magnitudes when the decisions
    carry them and reports them unmeasured when they do not.

    The refusal now comes from the direction declaration rather than from the sort heuristic:
    `RulesAdapter` declares `computes`, and neither magnitude is in this system's variable table at
    all, so the engine can say plainly that the system has no notion of them. The heuristic answers
    the same case for logic that declares no directions —
    `test_logic_that_declares_no_directions_keeps_the_sort_heuristic`.
    """
    req = _magnitude_duty()

    unmeasured = evaluate_requirement(
        req, _deviation_sut([{"score": 700}, {"score": 300}])
    )
    assert unmeasured.strength is None
    assert unmeasured.verdict == Verdict.INCONCLUSIVE
    assert "gives the system no notion of" in unmeasured.evidence_summary

    measured = evaluate_requirement(
        req,
        _deviation_sut(
            [
                {
                    "score": 700,
                    "scope_statements_declared_deviation": 2.0,
                    "artifact_logs_decision_margin": 50.0,
                    "scope_statements_approximation_vs_guarantee": True,
                },
                {
                    "score": 300,
                    "scope_statements_declared_deviation": 2.0,
                    "artifact_logs_decision_margin": 350.0,
                    "scope_statements_approximation_vs_guarantee": True,
                },
            ]
        ),
    )
    assert measured.verdict == Verdict.SATISFIED
    assert measured.strength == Strength.OBSERVED


class _UndeclaredDirectionsSUT(BaseSUT):
    """Logic exposed the way it was before directions existed: no `computes` key at all.

    Stands for every adapter written against the old contract, including one outside this
    repository. It exists so the path where the sort heuristic is the *only* guard keeps a test of
    its own: every `RulesAdapter` declares directions, so on one the heuristic runs beside
    `_check_declared_directions` and cannot be seen answering alone.
    """

    def __init__(self):
        super().__init__(set(_UNCOMPUTED_MAGNITUDE_SIGNALS))

    def logic(self):
        return {
            "variables": {
                "score": "int",
                "approved": "bool",
                "scope_statements_declared_deviation": "real",
                "artifact_logs_decision_margin": "real",
            },
            "rules": ["approved = score >= 650"],
            "constraints": ["score >= 0", "score <= 1000"],
        }


def test_logic_that_declares_no_directions_keeps_the_sort_heuristic():
    """An adapter declaring no directions gets the answer it has today, and never a wider one.

    Directions are the right joint, but logic that declares none cannot be *read* as declaring
    every variable an input: that reading is exactly what reported `violated` at `proved` on
    numbers nobody computed. So `_check_magnitudes_are_computed` runs over every logic, declared or
    not, and this system — whose variable table lists both magnitudes and whose rules assign
    neither — is refused a proof by the heuristic with no declaration guard beside it.
    """
    req = _magnitude_duty()

    result = evaluate_requirement(req, _UndeclaredDirectionsSUT())

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "reads nothing the declared rules assign" in result.evidence_summary


def test_a_declared_output_the_rules_never_settle_is_refused_a_proof():
    """Declaring an output does not conjure the logic that produces it.

    The other half of the direction guard. This system says it computes the decision margin — the
    name is in `variables` and in `computes` — but the rules it exposed assign it on no path, so
    the constant standing in for it in the encoding is free after all. A proof read off that
    constant would be a proof about the declaration and not about the system.
    """
    req = _magnitude_duty()
    sut = RulesAdapter(
        rules=["approved = score >= 650"],
        variables={
            "score": "int",
            "approved": "bool",
            "scope_statements_declared_deviation": "real",
            "artifact_logs_decision_margin": "real",
        },
        constraints=["score >= 0", "score <= 1000"],
        computes={
            "approved",
            "scope_statements_declared_deviation",
            "artifact_logs_decision_margin",
        },
        declared_capabilities=set(_UNCOMPUTED_MAGNITUDE_SIGNALS),
    )

    result = evaluate_requirement(req, sut)

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "declares it computes" in result.evidence_summary
    assert "do not assign it on every path" in result.evidence_summary


def test_a_logged_magnitude_is_not_an_input_because_the_type_table_names_it():
    """A name in `variables` alone is not a declared input, and cannot carry a `proved` violation.

    `variables` is a type table: its job is sorts. A caller listing the two Recital 71 magnitudes
    there is doing what the field asks — naming a signal its system deals with, here one it merely
    logs — and is not thereby saying the decision situation supplies them. Reading it as though it
    were made `computes` widen what reaches the solver, and this system, which decides on a score
    alone, was reported `violated` at `proved` on the solver's own `deviation = 1, margin = 0`.

    Which is the verdict class `_check_magnitudes_are_computed` exists to stop, so it runs as an
    additional filter over every logic and not as an alternative to the declaration. The duty falls
    to the engine that reads the trace, where an unmeasured magnitude is reported unmeasured.
    """
    req = _magnitude_duty()
    sut = RulesAdapter(
        rules=["approved = score >= 650"],
        variables={
            "score": "int",
            "approved": "bool",
            "scope_statements_declared_deviation": "real",
            "artifact_logs_decision_margin": "real",
        },
        constraints=["score >= 0", "score <= 1000"],
        declared_capabilities=set(_UNCOMPUTED_MAGNITUDE_SIGNALS),
    )
    assert sut.logic()["computes"] == ["approved"]

    result = evaluate_requirement(req, sut)

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "reads nothing the declared rules assign" in result.evidence_summary


def test_a_constraint_restating_the_duty_cannot_prove_the_system_satisfies_it():
    """The other direction of the same defect: a system asserting the duty about itself.

    One constraint naming the two magnitudes is enough to make the negated property unsatisfiable,
    so the same system that was reported `violated` above is reported `satisfied` at `proved` —
    on the strength of its own assertion, which no rendering names. `docs/semantics.md` §3 refuses
    a self-declared verdict everywhere else, and it must not arrive at the top rung through a
    constraint. The property still reads no name the rules assign, so the same filter answers both
    directions.
    """
    req = _magnitude_duty()
    sut = RulesAdapter(
        rules=["approved = score >= 650"],
        variables={
            "score": "int",
            "approved": "bool",
            "scope_statements_declared_deviation": "real",
            "artifact_logs_decision_margin": "real",
        },
        constraints=[
            "score >= 0",
            "score <= 1000",
            "scope_statements_declared_deviation <= artifact_logs_decision_margin",
        ],
        declared_capabilities=set(_UNCOMPUTED_MAGNITUDE_SIGNALS),
    )
    assert sut.logic()["computes"] == ["approved"]

    result = evaluate_requirement(req, sut)

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "reads nothing the declared rules assign" in result.evidence_summary


def test_computes_is_derived_from_the_rules_and_must_name_declared_variables():
    """No RulesAdapter is undeclared by accident, and no declaration names a variable-less name.

    The derivation is not a guess: this adapter's premise is that `rules` *is* the decision
    procedure, so its assignment targets are what the system computes. A name written on one
    branch is still computed — whether every path writes it is the proof engine's separate
    question — so `_assigned_names` collects any-path targets.
    """
    branching = RulesAdapter(
        rules=[
            "approved = score >= 650",
            'if approved:\n    reason = "ok"\nelse:\n    pass\n',
        ],
        variables={"score": "int", "approved": "bool", "reason": "str"},
    )
    assert branching.logic()["computes"] == ["approved", "reason"]

    with pytest.raises(ValueError, match="computes must name declared variables"):
        RulesAdapter(
            rules=["approved = score >= 650"],
            variables={"score": "int", "approved": "bool"},
            computes={"approved", "artifact_logs_decision_margin"},
        )


def test_a_computes_that_is_not_a_collection_of_names_is_named_at_the_adapter():
    """The misdeclaration is answered where it was made, not per character or as a parse error.

    `set("approved")` and `set(True)` are a character soup and a `TypeError` respectively, and
    both used to surface as something else — a variable-table complaint about `'a'`, `'d'`, `'e'`
    …, or the engine's generic "error parsing decision logic or property". The engine refuses
    both too (`ProvedEngine.evaluate`), because no adapter outside this repository goes through
    here.
    """
    with pytest.raises(ValueError, match="computes must be a collection of names"):
        RulesAdapter(
            rules=["approved = score >= 650"],
            variables={"score": "int", "approved": "bool"},
            computes="approved",
        )

    with pytest.raises(TypeError, match="cannot be iterated"):
        RulesAdapter(
            rules=["approved = score >= 650"],
            variables={"score": "int", "approved": "bool"},
            computes=True,
        )


class _ComputesOutsideTheTypeTableSUT(BaseSUT):
    """Third-party logic declaring a computed name the type table does not repeat.

    `RulesAdapter` keeps `computes` inside `variables`, but no adapter outside this repository is
    bound by that: the protocol asks for the names the system produces and never says the type
    table must list them too. The rules here assign the margin, so it is an output at the default
    sort and not a name this system has no notion of.
    """

    def __init__(self):
        super().__init__(set(_UNCOMPUTED_MAGNITUDE_SIGNALS))

    def logic(self):
        return {
            "variables": {
                "score": "int",
                "approved": "bool",
                "scope_statements_declared_deviation": "real",
            },
            "computes": ["approved", "artifact_logs_decision_margin"],
            "rules": ["approved = score >= 650", "artifact_logs_decision_margin = 100"],
            "constraints": ["score >= 0", "score <= 1000"],
        }


def test_a_computed_name_outside_the_type_table_is_an_output_not_an_unknown():
    """The outer boundary is both declarations, not `variables` alone.

    Reading `variables` as the only boundary would answer a system about a name it said in as many
    words that it computes with "you have no notion of this" — and refuse a proof the rules
    genuinely establish. The margin is assigned on every path, the deviation is a declared input,
    and the duty is decided rather than refused.
    """
    req = _magnitude_duty()

    result = evaluate_requirement(req, _ComputesOutsideTheTypeTableSUT())

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED


class _StringComputesSUT(_ComputesOutsideTheTypeTableSUT):
    """The misdeclaration that reads as its own characters."""

    def logic(self):
        data = super().logic()
        data["computes"] = "approved"
        return data


def test_computes_declared_as_a_string_is_refused_rather_than_read_as_characters():
    """A bare string is iterable, and taking it silently widens every proof.

    `set("approved")` is six characters naming nothing the system computes, so the declaration
    guard would find no output to check and every declared variable would read as an input — the
    reading `docs/semantics.md` §3.5 says hands back the `violated`-at-`proved` verdict the
    declaration exists to stop. Refused at the misdeclaration, before any solver call.
    """
    req = _magnitude_duty()

    result = evaluate_requirement(req, _StringComputesSUT())

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "declares `computes` as a string" in result.evidence_summary


class _UniterableComputesSUT(_ComputesOutsideTheTypeTableSUT):
    """A declaration that is not a collection at all."""

    def logic(self):
        data = super().logic()
        data["computes"] = True
        return data


class _NonNameComputesSUT(_ComputesOutsideTheTypeTableSUT):
    """A collection whose entries name no variable."""

    def logic(self):
        data = super().logic()
        data["computes"] = ["approved", 3]
        return data


@pytest.mark.parametrize(
    ("sut", "expected"),
    [
        (_UniterableComputesSUT(), "not a collection of names at all"),
        (_NonNameComputesSUT(), "entries that are not variable names"),
    ],
)
def test_a_computes_that_cannot_be_read_as_names_is_refused_by_the_engine(sut, expected):
    """The string guard's two neighbours, refused for the same reason and named as themselves.

    Both are declarations the engine cannot read: a non-iterable used to reach `set()` inside the
    encoding block and be reported as an error parsing the property, and an entry that is not a
    name matches nothing in a property, so the output it was meant to declare would quietly read
    as an input the situation supplies — the widening `docs/semantics.md` §3.5 says the
    declaration exists to stop.
    """
    req = _magnitude_duty()

    result = evaluate_requirement(req, sut)

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert expected in result.evidence_summary


def test_article_22_still_quantifies_over_flags_the_rules_never_assign():
    """The reading neither guard may silence.

    `gdpr_art22_1_no_prohibited_decision_for_any_input` asks whether *any* admissible input yields
    a decision that is solely automated and significantly affecting without an Article 22(2) basis.
    Its flags are free inputs of the exposed rules on purpose — quantifying over them is the whole
    duty — so a guard that refused every unassigned name would turn this proof into silence. This
    SUT is a `RulesAdapter`, so it declares `computes` and both guards run: the flags are in
    `variables` and not in `computes`, which is the declaration for an input the situation supplies,
    and the sort heuristic beside the declaration guard refuses only free *magnitudes*, so free
    flags pass it. An input is quantified over.
    """
    req = load_pack("gdpr").get_requirement("gdpr_art22_1_no_prohibited_decision_for_any_input")
    flags = (
        "artifact_logs_solely_automated",
        "artifact_logs_significant_effect",
        "artifact_logs_human_intervention_route",
        "provenance_basis_contract",
        "provenance_basis_union_or_member_state_law",
        "provenance_basis_explicit_consent",
    )
    sut = RulesAdapter(
        rules=["approved = score >= 650"],
        variables={"score": "int", "approved": "bool", **dict.fromkeys(flags, "bool")},
        constraints=["score >= 0", "score <= 1000"],
        test_inputs=[{"score": 700}, {"score": 300}],
        declared_capabilities=set(flags),
    )

    result = evaluate_requirement(req, sut)

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED
    assert result.details["counterexample"]["artifact_logs_solely_automated"] is True


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
