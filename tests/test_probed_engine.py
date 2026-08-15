"""Tests for the probed engine: active falsification against a system's own decide().

What this module is for:
  Holds the probed engine to the discipline the rung exists for — a counterexample is verified
  before it is reported, a budget is inseparable from a probed verdict, absent evidence is never
  a pass, and probed never rounds up to proved.
"""

from __future__ import annotations

import ast
import json

import pytest

from reasonsmith.engines import probed
from reasonsmith.engines.probed import DEFAULT_TRIALS, STRATEGY, ProbedEngine, plan_inputs
from reasonsmith.render import _budget_line
from reasonsmith.report import (
    PROBE_BUDGET_KEY,
    ConformanceReport,
    RequirementResult,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.rulelang import UnsupportedConstructError
from reasonsmith.spec import Pack, Requirement
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
    rationale: str = "Why this duty exists, in English.",
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
        rationale=rationale,
        requires=requires,
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
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


def test_an_input_the_system_cannot_decide_is_counted_not_read_as_a_pass():
    """`probed` quantifies over the replayed inputs that produced a decision, and counts the rest.

    An input the system raises on yields no decision the property can be read over. Counting it
    as a pass would let a system that refuses most of the search space look thoroughly probed, so
    the budget carries how many inputs produced nothing — and, since a satisfaction needs complete
    evidence, the run is not evaluated rather than satisfied over the part that answered.
    """

    class RefusingSUT(HonestSUT):
        """Raises on any applicant under 25 rather than deciding."""

        def decide(self, case):
            if case.get("age", 0) < 25:
                raise ValueError("age below the system's minimum")
            return super().decide(case)

    res = ProbedEngine.evaluate(_req(), RefusingSUT(), trials=60, seed=5)

    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    budget = res.details[PROBE_BUDGET_KEY]
    # Some inputs produced no decision, and the count of them is on the result rather than lost.
    assert 0 < budget["inputs_errored"] < budget["trials"]


def test_an_input_whose_property_cannot_be_evaluated_is_counted_not_read_as_a_pass():
    """A decision can exist while the property is undefined; that input is still errored."""

    class EchoSUT(OpaqueSUT):
        def __init__(self):
            super().__init__(trace=({"denominator": 0}, {"denominator": 1}))

        def decide(self, case):
            return dict(case)

    req = _req(spec="1 / denominator == 1 / denominator", requires=("denominator",))
    res = ProbedEngine.evaluate(req, EchoSUT(), trials=20, seed=5)

    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    budget = res.details[PROBE_BUDGET_KEY]
    assert 0 < budget["inputs_errored"] < budget["trials"]


class BandedSUT(BaseSUT):
    """A lender correct up to 40000 and raising above it.

    The shape the unreachable-antecedent guard does not mask: the inputs it refuses are not a
    random sample of the search space, they are the band its author put outside what the system
    answers for, which is exactly where `income >= 30000 -> approved` is most at risk.
    """

    def __init__(self):
        super().__init__({"income", "approved"})

    def decisions(self):
        return [
            {"income": 20000, "approved": False},
            {"income": 35000, "approved": True},
        ]

    def decide(self, case):
        income = case.get("income", 0)
        if income > 40000:
            raise ValueError(f"income {income} is outside the scored band")
        return {**case, "approved": income >= 30000}


def test_a_satisfaction_over_a_partly_unmeasurable_domain_is_not_a_satisfaction():
    """A violation needs one witness; a satisfaction needs complete evidence.

    `engines/certificate.py` states the rule and every other rung keeps it by construction. This
    is the rung that did not: it reported `satisfied` over a domain part of which it could not
    measure, and the summary said so in no way a reader or a `--json` consumer could see.
    """
    res = ProbedEngine.evaluate(
        _req(spec="income >= 30000 -> approved", requires=("income", "approved")),
        BandedSUT(),
    )

    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert res.details["reason"] == "inputs_unmeasured"
    budget = res.details[PROBE_BUDGET_KEY]
    assert budget["inputs_errored"] > 0
    # The refusal names both halves of what it could and could not measure, and the count it
    # claims to have searched is the measured one, never the planned one.
    measured = budget["trials"] - budget["inputs_errored"]
    assert f"{budget['inputs_errored']} of the {budget['trials']} input(s)" in res.evidence_summary
    assert f"the other {measured}" in res.evidence_summary


def test_a_system_that_errors_on_nothing_still_earns_its_satisfaction():
    """The control: the guard above must cost an unaffected system nothing.

    Same property, same trace, same budget — only the refusal band removed. A guard that also
    withheld this verdict would have traded one false claim for a useless engine.
    """

    class UnbandedSUT(BandedSUT):
        def decide(self, case):
            return {**case, "approved": case.get("income", 0) >= 30000}

    req = _req(spec="income >= 30000 -> approved", requires=("income", "approved"))
    res = ProbedEngine.evaluate(req, UnbandedSUT())

    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.PROBED
    budget = res.details[PROBE_BUDGET_KEY]
    assert budget["inputs_errored"] == 0
    # The count in the summary is the measured count, and here it equals the planned one.
    assert f"in {budget['trials']} input(s) replayed" in res.evidence_summary


def test_no_summary_or_budget_line_states_more_replays_than_were_measured():
    """3b: the overstatement was in `evidence_summary`, so it travelled into every consumer.

    Two numbers about one search were printed four lines apart — the guard's domain string
    subtracting the errored inputs and the budget line not. They must name the same search.
    """
    res = ProbedEngine.evaluate(
        _req(spec="income >= 30000 -> approved", requires=("income", "approved")),
        BandedSUT(),
    )
    budget = res.details[PROBE_BUDGET_KEY]
    errored = budget["inputs_errored"]
    measured = budget["trials"] - errored
    assert errored > 0

    line = _budget_line(budget)
    assert f"{errored} of which raised rather than producing a decision" in line
    assert f"leaving {measured} measured" in line
    # No rendering of this search claims the property was read over more inputs than it was.
    assert f"{budget['trials']} input(s) replayed," in line
    assert f"in {budget['trials']} input(s) replayed" not in res.evidence_summary


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


def test_probe_plan_deduplicates_seed_records_and_obeys_trial_cap():
    records = [{"x": 1}, {"x": 1}, {"x": 2}, {"x": 3}]
    req = _req(spec="x == x", requires=("x",))

    assert plan_inputs(req, records, trials=2, seed=0) == [{"x": 1}, {"x": 2}]


def test_probe_candidate_pools_and_budget_counts_are_exact():
    records = [
        {"flag": True, "number": 2, "text": "x", "fixed": {"nested": 1}},
        {"flag": False, "number": 4, "text": "y", "fixed": {"nested": 2}},
    ]
    req = _req(spec="number - 10 == number - 10", requires=("number",))
    pools = probed._pools(req, records)

    assert set(pools) == {"flag", "number", "text"}
    assert set(pools["flag"]) == {True, False}
    assert set(pools["number"]) == {-4, -2, 0, 1, 2, 3, 4, 5, 8, 9, 10, 11}
    assert set(pools["text"]) == {"", "x", "y"}

    class EchoSUT(OpaqueSUT):
        def __init__(self):
            super().__init__(trace=records)

        def decide(self, case):
            return dict(case)

    result = ProbedEngine.evaluate(req, EchoSUT(), trials=20, seed=3)

    assert result.verdict == Verdict.SATISFIED
    assert result.details[PROBE_BUDGET_KEY]["input_space"] == {
        "flag": 2,
        "number": 12,
        "text": 3,
    }


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
    """The budget invariant is enforced at construction and every rendering boundary."""
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

    del ok.details[PROBE_BUDGET_KEY]
    report = ConformanceReport(pack_id="p", system_name="s", results=(ok,))
    for render in (ok.to_dict, report.render_text, report.to_json, report.render_html):
        with pytest.raises(ValueError, match="must carry its search budget"):
            render()


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


def test_conformance_shares_one_trace_across_probed_requirements():
    class CountingTraceSUT(HonestSUT):
        def __init__(self):
            super().__init__()
            self.trace_reads = 0

        def decisions(self):
            self.trace_reads += 1
            return super().decisions()

    sut = CountingTraceSUT()
    pack = Pack("p", "P", "", (_req("r1"), _req("r2")))

    report = check_conformance(sut, pack)

    assert sut.trace_reads == 1
    assert all(result.strength == Strength.PROBED for result in report.results)


def test_trace_and_planning_failures_are_not_evaluated(monkeypatch):
    """This engine's own contract, plus what a whole run does with a trace it cannot read.

    What changed, and why: a `logical` duty used to reach this engine and no other, so a trace this
    engine had wrapped into a verdict was the only account a whole run ever gave of one. Now that a
    state fragment also admits a trace rung, a `logical` duty is answered the way a `record` one
    always was — and a trace that cannot be read at all raises and names the system, for every
    fragment alike (`docs/semantics.md` §3.5, `test_a_trace_of_the_wrong_shape_names_the_system`).
    That is the tool becoming consistent rather than this engine changing: the direct call below is
    unchanged, because wrapping the provider it was handed is exactly what this engine promises.
    The routed half now pins the uniform behaviour, and still pins that the trace is read once.
    """
    class BrokenTraceSUT(HonestSUT):
        def __init__(self):
            super().__init__()
            self.trace_reads = 0

        def decisions(self):
            self.trace_reads += 1
            raise RuntimeError("trace service unavailable")

    direct = ProbedEngine.evaluate(_req(), BrokenTraceSUT())
    assert direct.verdict == Verdict.INCONCLUSIVE
    assert direct.strength is None
    assert direct.details["reason"] == "trace_acquisition_failed"
    assert "trace service unavailable" in direct.evidence_summary

    routed_sut = BrokenTraceSUT()
    with pytest.raises(RuntimeError, match="trace service unavailable"):
        check_conformance(routed_sut, Pack("p", "P", "", (_req("r1"), _req("r2"))))
    assert routed_sut.trace_reads == 1

    def fail_plan(*args, **kwargs):
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr(probed, "plan_inputs", fail_plan)
    planning = ProbedEngine.evaluate(_req(), HonestSUT())
    assert planning.verdict == Verdict.INCONCLUSIVE
    assert planning.strength is None
    assert planning.details["reason"] == "input_planning_failed"
    assert "planner unavailable" in planning.evidence_summary


def test_nonpositive_trial_budget_is_not_confused_with_an_empty_trace():
    result = ProbedEngine.evaluate(_req(), HonestSUT(), trials=0)

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["reason"] == "invalid_trial_budget"
    assert result.details["trials_requested"] == 0


@pytest.mark.parametrize(
    ("spec", "refusal"),
    [
        ("True or unsupported(income)", "unsupported function call"),
        ("income + 1", "not a boolean property"),
        ("True < 1", "incompatible established kinds boolean and number"),
    ],
)
def test_the_complete_property_must_be_expressible_and_boolean(spec, refusal):
    class SearchTrackingSUT(HonestSUT):
        def __init__(self):
            super().__init__()
            self.replays = 0

        def decide(self, case):
            self.replays += 1
            return super().decide(case)

    sut = SearchTrackingSUT()
    result = ProbedEngine.evaluate(_req(spec=spec), sut)

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["reason"] == "property_not_expressible"
    assert refusal in result.evidence_summary.lower()
    assert sut.replays == 0


def test_nested_mutation_cannot_change_the_verification_input_or_witness():
    class MutatingSUT(OpaqueSUT):
        def __init__(self):
            super().__init__(
                trace=(
                    {
                        "income": 30000,
                        "age": 70,
                        "approved": True,
                        "reason": "seed",
                        "profile": {"age": 70},
                    },
                )
            )
            self.received_ages = []

        def decide(self, case):
            self.received_ages.append(case["profile"]["age"])
            case["profile"]["age"] = -1
            return {**case, "approved": False}

    sut = MutatingSUT()
    result = ProbedEngine.evaluate(
        _req(spec="approved == True", requires=("approved",)),
        sut,
        trials=1,
    )

    assert result.verdict == Verdict.VIOLATED
    assert sut.received_ages == [70, 70]
    assert result.details["counterexample"]["profile"]["age"] == 70


def test_uncloneable_probe_input_is_not_evaluated():
    class Uncloneable:
        def __deepcopy__(self, memo):
            raise RuntimeError("cannot clone token")

    class UncloneableSUT(OpaqueSUT):
        def __init__(self):
            super().__init__(trace=({"approved": True, "token": Uncloneable()},))
            self.replays = 0

        def decide(self, case):
            self.replays += 1
            return case

    sut = UncloneableSUT()
    result = ProbedEngine.evaluate(
        _req(spec="approved == True", requires=("approved",)),
        sut,
        trials=1,
    )

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["reason"] == "input_clone_failed"
    assert "cannot clone token" in result.evidence_summary
    assert sut.replays == 0


def test_trace_established_numeric_name_is_refused_in_boolean_position():
    class SearchTrackingSUT(HonestSUT):
        def __init__(self):
            super().__init__()
            self.replays = 0

        def decide(self, case):
            self.replays += 1
            return super().decide(case)

    sut = SearchTrackingSUT()
    result = ProbedEngine.evaluate(_req(spec="not income", requires=("income",)), sut)

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["reason"] == "property_not_expressible"
    assert "income" in result.evidence_summary
    assert "number" in result.evidence_summary
    assert sut.replays == 0


def test_trace_established_kind_propagates_through_arithmetic_operands():
    class SearchTrackingSUT(HonestSUT):
        def __init__(self):
            super().__init__()
            self.replays = 0

        def decide(self, case):
            self.replays += 1
            return super().decide(case)

    sut = SearchTrackingSUT()
    result = ProbedEngine.evaluate(
        _req(spec="approved or (reason + 1 > 0)", requires=("approved", "reason")),
        sut,
    )

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.verdict != Verdict.SATISFIED
    assert result.strength is None
    assert result.details["reason"] == "property_not_expressible"
    assert "reason" in result.evidence_summary
    assert "string" in result.evidence_summary
    assert "+" in result.evidence_summary
    assert sut.replays == 0


def test_unestablished_property_kind_remains_permissive_and_is_disclosed():
    class AddsRiskScoreSUT(OpaqueSUT):
        def decide(self, case):
            return {**case, "risk_score": 1}

    result = ProbedEngine.evaluate(
        _req(spec="risk_score >= 0", requires=("risk_score",)),
        AddsRiskScoreSUT(),
        trials=5,
    )

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    budget = result.details[PROBE_BUDGET_KEY]
    assert budget["property_kinds_unestablished"] == ["risk_score"]
    assert "risk_score" in result.evidence_summary
    report = ConformanceReport(pack_id="p", system_name="s", results=(result,))
    assert "Property field kind(s) not established by trace: risk_score" in report.render_text()


def test_recorded_strategy_distinguishes_seed_replays_from_perturbations():
    result = ProbedEngine.evaluate(_req(), HonestSUT(), trials=10)
    strategy = result.details[PROBE_BUDGET_KEY]["strategy"]

    assert strategy == STRATEGY
    assert "first unmodified" in strategy
    assert "remaining inputs" in strategy


# Coverage boundary cases for this subject.
def test_probed_trace_kind_validation_catches_boolean_and_arithmetic_conflicts():
    assert probed._trace_operand_kind(
        ast.parse("-income", mode="eval").body, {"income": "number"}
    ) == ("number", (("income", "number"),))
    assert (
        probed._trace_operand_kind(ast.parse("income + 1", mode="eval").body, {"income": "number"})[
            0
        ]
        == "number"
    )
    assert (
        probed._trace_operand_kind(
            ast.parse("abs(income)", mode="eval").body, {"income": "number"}
        )[0]
        == "number"
    )
    with pytest.raises(UnsupportedConstructError, match="Boolean operation"):
        probed._validate_trace_kinds(
            ast.parse("approved and income", mode="eval"),
            {"approved": "number", "income": "number"},
        )
    with pytest.raises(UnsupportedConstructError, match="arithmetic operation"):
        probed._trace_operand_kind(
            ast.parse("-approved", mode="eval").body, {"approved": "boolean"}
        )


def test_probed_shared_mutable_path_checks_nested_containers_and_slots():
    shared = []
    assert probed._shared_mutable_path(shared, shared) == "input"
    assert probed._shared_mutable_path({"x": shared}, {"x": shared}) == "input['x']"
    assert probed._shared_mutable_path([1, 2], [1, 2]) is None
    assert probed._shared_mutable_path({1, 2}, {1, 2}) is None
    assert probed._spec_numbers("income >= 10 and age < 2.5") == {10, 2.5}
    assert probed._spec_numbers("not valid ???") == set()


def test_probed_operand_calls_and_shared_object_shapes():
    assert (
        probed._trace_operand_kind(
            ast.parse("min(income, 2)", mode="eval").body, {"income": "number"}
        )[0]
        == "number"
    )
    with pytest.raises(UnsupportedConstructError, match="arithmetic operation"):
        probed._trace_operand_kind(
            ast.parse("max(approved, 2)", mode="eval").body, {"approved": "boolean"}
        )

    class Slotted:
        __slots__ = ("items",)

        def __init__(self, items):
            self.items = items

    original = Slotted([])
    clone = Slotted(original.items)
    assert probed._shared_mutable_path(original, clone) == "input.items"
    assert probed._shared_mutable_path({"a": [1]}, {"a": [1]}) is None
    assert probed._shared_mutable_path({1}, {1}) is None


def test_probed_shared_path_handles_identity_and_object_containers():
    item = []
    assert probed._shared_mutable_path([item], [item]) == "input[0]"

    class HashableMutable:
        __hash__ = object.__hash__

    member = HashableMutable()
    assert probed._shared_mutable_path({member}, {member}) == f"input{{{member!r}}}.__dict__"

    class Dynamic:
        pass

    obj = Dynamic()
    clone = Dynamic()
    obj.value = []
    clone.value = obj.value
    assert probed._shared_mutable_path(obj, clone) == "input.__dict__['value']"

    class StringSlot:
        __slots__ = "value"

    left = StringSlot()
    right = StringSlot()
    left.value = []
    right.value = left.value
    assert probed._shared_mutable_path(left, right) == "input.value"
    assert probed._shared_mutable_path(left, left) == "input.value"


def test_probed_kind_refusal_reports_established_comparison_evidence(monkeypatch):
    assert probed._trace_operand_kind(ast.parse("mystery", mode="eval").body, {}) == (
        "unknown",
        (),
    )
    with pytest.raises(UnsupportedConstructError, match="Trace-established field kind"):
        probed._validate_trace_kinds(
            ast.parse("approved < income", mode="eval"),
            {"approved": "boolean", "income": "number"},
        )
    monkeypatch.setattr(probed.copy, "deepcopy", lambda value: value)
    with pytest.raises(TypeError, match="deep copy"):
        probed._clone_case({"nested": []})


def test_probed_replay_record_and_empty_plan_boundaries():
    assert probed._as_record({"x": 1}, "approved") == {"x": 1, "decision": "approved"}
    assert probed._as_record({"x": 1}, {"decision": "approved"}) == {"decision": "approved"}
    req = _req()
    assert probed.plan_inputs(req, [], trials=10) == []
    assert probed.plan_inputs(req, [{"signal": True}], trials=0) == []


def test_probed_trace_validation_handles_boolean_name_and_cycles():
    probed._validate_trace_kinds(ast.parse("approved", mode="eval"), {"approved": "boolean"})
    cyclic = {}
    cyclic["self"] = cyclic
    assert probed._shared_mutable_path(cyclic, cyclic) == "input"
    key = []
    assert probed._shared_mutable_path({"k": key}, {"k": key}) == "input['k']"


@pytest.mark.parametrize(
    "budget",
    [
        {"trials": 0, "strategy": "search", "seed": 0, "input_space": "x"},
        {"trials": -1, "strategy": "search", "seed": 0, "input_space": "x"},
        {"trials": True, "strategy": "search", "seed": 0, "input_space": "x"},
        {"trials": 1, "strategy": "", "seed": 0, "input_space": "x"},
        {"trials": 1, "strategy": 7, "seed": 0, "input_space": "x"},
        {"trials": 1, "strategy": "search", "seed": None, "input_space": "x"},
        {"trials": 1, "strategy": "search", "seed": object(), "input_space": "x"},
        {"trials": 1, "strategy": "search", "seed": float("nan"), "input_space": "x"},
        {"trials": 1, "strategy": "search", "seed": 0, "input_space": None},
        {"trials": 1, "strategy": "search", "seed": 0, "input_space": []},
    ],
)
def test_probed_result_refuses_invalid_search_budget(budget):
    with pytest.raises(ValueError):
        RequirementResult(
            requirement_id="budget",
            source_clause="source clause",
            verdict=Verdict.SATISFIED,
            strength=Strength.PROBED,
            signals_required=("signal",),
            details={PROBE_BUDGET_KEY: budget},
        )
