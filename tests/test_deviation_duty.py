"""Tests for the duty that reads a declared deviation instead of a declared field.

What this module is for:
  `gdpr_recital71_error_risk_minimised` is the first shipped requirement whose verdict comes from
  a *value* a system declares about its own approximation error, not from the presence of a
  statement about it. These tests hold that duty to what `docs/semantics.md` says it claims: it is
  satisfied only when every declared deviation is no larger than the decision's own margin, it is
  violated when a declared deviation is larger than that margin, and it is never satisfied when
  the deviation is absent, undeclared or not a number.

What a reader must not break:
  - The requirement is loaded from the shipped pack, never re-written here. A test that authored
    its own spec would pass while the pack said something else.
  - No test here asserts that a satisfied verdict means the system computes what it claims. The
    duty reads a self-declaration and reasonsmith never verifies the number; the module docstring
    of `docs/semantics.md` §3 states the limit and these tests must not imply more.
"""

from __future__ import annotations

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

REQUIREMENT_ID = "gdpr_recital71_error_risk_minimised"

STATEMENT = "approximation: value deviates from the distribution semantics oracle it claims by"


def requirement():
    return load_pack("gdpr").get_requirement(REQUIREMENT_ID)


def record(deviation, margin, statement: str = STATEMENT) -> dict:
    return {
        "scope_statements_declared_deviation": deviation,
        "scope_statements_approximation_vs_guarantee": statement,
        "artifact_logs_decision_margin": margin,
    }


def test_the_deviation_duty_is_interpretive_and_not_class_limited():
    """A recital is not an obligation, and this one reaches a system of any declared class.

    Both halves matter: reported as binding it would overclaim what Recital 71 is, and limited to
    `high-risk` it would repeat the gap it exists to close — the one shipped duty that read the
    approximation statement was never reached on an unclassified system.
    """
    req = requirement()
    assert req.binding is False
    assert req.scope == ""
    assert req.formalism == "temporal"
    assert "scope_statements_approximation_vs_guarantee" in req.requires


def test_a_declared_deviation_below_the_decision_margin_is_satisfied():
    """A declared error too small to have moved any decision is what this duty asks for."""
    req = requirement()
    sut = BaseSUT(set(req.requires))
    records = [
        record(0.0, 0.4, "guarantee: value equals the oracle it claims on this input"),
        record(0.0, 0.0, "guarantee: value equals the oracle it claims on this input"),
        record(0.09, 0.3),
    ]
    result = ObservedEngine.evaluate(req, sut, records)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_declared_deviation_exactly_equal_to_the_margin_is_reported_satisfied():
    """Pin the observed engine's known exact-tie limit rather than endorse that boundary."""
    req = requirement()
    sut = BaseSUT(set(req.requires))
    records = [record(0.01, 0.4), record(0.1, 0.1)]
    result = ObservedEngine.evaluate(req, sut, records)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_declared_deviation_that_could_have_moved_a_decision_is_violated():
    """The number the system declares about itself is read, and it decides the verdict."""
    req = requirement()
    sut = BaseSUT(set(req.requires))
    records = [record(0.01, 0.4), record(0.470679, 0.12), record(0.02, 0.3)]
    result = ObservedEngine.evaluate(req, sut, records)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED
    assert result.details["violation_step_indices"] == [1]


def test_an_undeclared_deviation_is_unattainable_never_satisfied():
    """Silence is not compliance: a system that declares no deviation discharges nothing."""
    req = requirement()
    sut = BaseSUT(set(req.requires) - {"scope_statements_declared_deviation"})
    result = evaluate_requirement(req, sut, [record(0.9, 0.01)])
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert "scope_statements_declared_deviation" in result.signals_missing


def test_an_unparseable_deviation_is_not_evaluated_never_satisfied():
    """A statement that names no number is a statement, not a measurement."""
    req = requirement()
    sut = BaseSUT(set(req.requires))
    records = [
        record("approximation: unquantified", 0.4),
        record(0.01, 0.4),
    ]
    result = ObservedEngine.evaluate(req, sut, records)
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["signals_unmeasured_in_trace"] == {
        "scope_statements_declared_deviation": 1
    }
