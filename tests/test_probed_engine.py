"""Tests for the probed engine: active falsification against a system's own decide().

What this module is for:
  Holds the probed engine to the discipline the rung exists for — a counterexample is verified
  before it is reported, a budget is inseparable from a probed verdict, absent evidence is never
  a pass, and probed never rounds up to proved.
"""

from __future__ import annotations

import json

import pytest

from reasonsmith.engines.probed import DEFAULT_TRIALS, ProbedEngine, plan_inputs
from reasonsmith.report import (
    PROBE_BUDGET_KEY,
    ConformanceReport,
    RequirementResult,
    evaluate_requirement,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

#: The trace every opaque system below has already produced. Two decisions, so the search has
#: something to perturb around and the value pools hold more than one value per field.
TRACE = (
    {"income": 30000, "age": 30, "approved": True, "reason": "income above threshold"},
    {"income": 20000, "age": 40, "approved": False, "reason": "income below threshold"},
)


def _req(
    req_id: str = "probe_r1",
    spec: str = "income >= 30000 implies approved == True",
    requires: tuple[str, ...] = ("income", "age", "approved"),
) -> Requirement:
    return Requirement(
        id=req_id,
        source_document="Internal Policy",
        article_clause="Section 2.1",
        verbatim_text="An applicant over the income threshold must be approved.",
        stakeholder="Compliance",
        formalism="logical",
        spec=spec,
        requires=requires,
        binding=True,
        scope="",
    )


class OpaqueSUT(BaseSUT):
    """A black box: it answers and it logs, but it exposes no decision logic to reason over."""

    def __init__(self, trace=TRACE):
        super().__init__({"income", "age", "approved", "reason"})
        self._trace = [dict(rec) for rec in trace]

    def decisions(self):
        return [dict(rec) for rec in self._trace]


class AgeCappedSUT(OpaqueSUT):
    """Approves on income, except that nobody over 65 is ever approved. The trace never shows it."""

    def decide(self, case):
        approved = case.get("income", 0) >= 30000 and case.get("age", 0) <= 65
        return {**case, "approved": approved, "reason": "scored"}


class HonestSUT(OpaqueSUT):
    """Approves exactly on the income threshold, with no hidden second condition."""

    def decide(self, case):
        return {**case, "approved": case.get("income", 0) >= 30000, "reason": "scored"}


class FlakySUT(OpaqueSUT):
    """Answers differently on the same input: the first replay fails, the verification passes."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def decide(self, case):
        self.calls += 1
        return {**case, "approved": self.calls % 2 == 0, "reason": "coin"}


def test_a_genuine_counterexample_is_reported_violated_with_the_input():
    """The hidden age cap breaks the property, and the report carries the input that broke it."""
    sut = AgeCappedSUT()
    res = ProbedEngine.evaluate(_req(), sut)

    assert res.verdict == Verdict.VIOLATED
    assert res.strength == Strength.PROBED
    counterexample = res.details["counterexample"]
    assert counterexample["income"] >= 30000
    assert counterexample["age"] > 65
    # The reported input really does break the property on the system itself.
    assert sut.decide(counterexample)["approved"] is False
    assert str(counterexample) in res.evidence_summary


def test_no_counterexample_in_budget_is_probed_and_every_rendering_carries_the_budget():
    """`probed` is a claim about a bounded search, so text, JSON and HTML all state the bound."""
    res = ProbedEngine.evaluate(_req(), HonestSUT(), trials=50, seed=7)

    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROBED
    budget = res.details[PROBE_BUDGET_KEY]
    assert budget["trials"] == 50
    assert budget["seed"] == 7
    assert budget["input_space"]

    report = ConformanceReport(pack_id="p", system_name="s", results=(res,))

    text = report.render_text()
    assert "probe budget: 50 input(s) replayed, seed 7" in text
    assert "input space:" in text

    payload = json.loads(report.to_json())
    assert payload["results"][0]["details"][PROBE_BUDGET_KEY]["trials"] == 50
    assert payload["results"][0]["details"][PROBE_BUDGET_KEY]["seed"] == 7

    html = report.render_html()
    assert "PROBED — What Was Searched" in html
    assert "50 input(s) replayed, seed 7" in html


def test_a_counterexample_that_does_not_reproduce_is_not_evaluated():
    """A candidate that fails once and passes on replay is a defect in the search, not a breach."""
    res = ProbedEngine.evaluate(_req(spec="approved == True", requires=("approved",)), FlakySUT())

    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert res.details["reason"] == "counterexample_did_not_reproduce"
    assert "unverified_counterexample" in res.details
    assert "counterexample" not in res.details


def test_a_system_without_decide_is_not_evaluated_never_satisfied():
    """No decide() means nothing was replayed, in the engine and through the report alike."""
    class NoDecideSUT(OpaqueSUT):
        pass

    sut = NoDecideSUT()
    direct = ProbedEngine.evaluate(_req(), sut)
    assert direct.verdict == Verdict.INCONCLUSIVE
    assert direct.strength is None
    assert direct.details["reason"] == "no_decide"

    routed = evaluate_requirement(_req(), sut)
    assert routed.verdict == Verdict.INCONCLUSIVE
    assert routed.strength is None


def test_an_empty_trace_gives_the_search_nothing_to_probe_around():
    """No decision to perturb is not evaluated, not a pass."""
    res = ProbedEngine.evaluate(_req(), AgeCappedSUT(trace=()))
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert res.details["reason"] == "no_seed_decisions"


def test_the_same_seed_searches_the_same_space():
    """A budget nobody can re-derive attests to nothing, so the plan is a function of its seed."""
    records = [dict(rec) for rec in TRACE]
    first = plan_inputs(_req(), records, trials=40, seed=3)
    second = plan_inputs(_req(), records, trials=40, seed=3)
    other = plan_inputs(_req(), records, trials=40, seed=4)

    assert first == second
    assert first != other
    assert len(first) == 40
    # The recorded decisions are replayed first, unperturbed.
    assert first[: len(records)] == records


def test_the_engine_replays_exactly_the_planned_inputs():
    """What the budget counts is what the system was actually run on."""
    seen = []

    class RecordingSUT(HonestSUT):
        def decide(self, case):
            seen.append(dict(case))
            return super().decide(case)

    res = ProbedEngine.evaluate(_req(), RecordingSUT(), trials=25, seed=11)
    assert seen == plan_inputs(_req(), [dict(r) for r in TRACE], trials=25, seed=11)
    assert res.details[PROBE_BUDGET_KEY]["trials"] == len(seen)


def test_a_probed_result_cannot_be_constructed_without_its_budget():
    """The budget is a construction-time invariant, not a rendering convention."""
    base = {
        "requirement_id": "r1",
        "source_clause": "Doc Art. 1",
        "verdict": Verdict.SATISFIED,
        "strength": Strength.PROBED,
        "signals_required": ("a",),
    }

    with pytest.raises(ValueError, match="must carry its search budget"):
        RequirementResult(**base)

    with pytest.raises(ValueError, match="missing seed, input_space"):
        RequirementResult(**base, details={PROBE_BUDGET_KEY: {"trials": 5, "strategy": "x"}})

    ok = RequirementResult(
        **base,
        details={
            PROBE_BUDGET_KEY: {"trials": 5, "strategy": "x", "seed": 0, "input_space": {"a": 2}}
        },
    )
    assert ok.strength == Strength.PROBED


def test_probed_never_rounds_up_to_proved():
    """No rendering, count or headline turns a bounded search into a proof."""
    res = ProbedEngine.evaluate(_req(), HonestSUT())
    assert res.details[PROBE_BUDGET_KEY]["trials"] == DEFAULT_TRIALS
    report = ConformanceReport(pack_id="p", system_name="s", results=(res,))

    counts = report.counts
    assert counts["probed"] == 1
    assert counts["proved"] == 0
    assert "1 probed" in report.headline
    assert "proved" not in report.headline

    text = report.render_text()
    assert "[PROBED]" in text
    assert "[PROVED]" not in text

    html = report.render_html()
    # The lattice rung the card marks active, not the stylesheet that names every rung.
    assert '<span class="lattice-step active-probed">' in html
    assert '<span class="lattice-step active-proved">' not in html
    assert "Formal Counterexample" not in html


def test_an_opaque_system_reaches_probed_through_the_report():
    """The routing is the point: `logic()` gets the proved engine, `decide()` alone gets probed."""
    satisfied = evaluate_requirement(_req(), HonestSUT())
    assert satisfied.verdict == Verdict.SATISFIED
    assert satisfied.strength == Strength.PROBED

    violated = evaluate_requirement(_req(), AgeCappedSUT())
    assert violated.verdict == Verdict.VIOLATED
    assert violated.strength == Strength.PROBED
    assert violated.details["counterexample"]["age"] > 65
