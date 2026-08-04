"""The clock a decision trace states, and what a duty needing one gets when the trace states none.

What this module is for:
  A deadline duty today reads a latency number the system computes about itself, and which event
  that number was counted from is that system's own claim (`docs/refinement.md`, the
  `ecoa_reg_b_1002_9_a_1_timing_of_notice` row). `sut.TIME_DOMAIN_KEY` is where that missing fact
  goes — the events a decision record can timestamp — and `TimeDomain` is the axis a monitor is
  fed. These tests pin the three things that must not drift.

What a reader must not break:
  - A log that says nothing about time acquires no clock by having been read.
    Why this matters: silently promoting a timeless log to a real time domain would let a bound
    written in days be answered by record indices, which is the defect this shape exists to make
    impossible rather than to introduce.
  - The record-index behaviour is what every caller passing no domain still gets, on a clocked log
    as much as on a timeless one.
    Why this matters: a system that started recording when things happened must not thereby lose
    a verdict it had. Richer evidence never costs an answer.
  - A duty asked for on any other domain is not evaluated, and never satisfied.
    Why this matters: no metric or interval semantics exists here. Answering such a duty off the
    record index would be a verdict about decisions presented as a verdict about days.
"""

from __future__ import annotations

import pytest

from reasonsmith import demo
from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.report import check_conformance
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.sut import (
    ECOA_1002_9_A_1_EVENTS,
    EVENT_TIME,
    ORDINAL_DOMAIN,
    ORDINAL_TIME,
    TIME_DOMAIN_KEY,
    BaseSUT,
    TimeDomain,
    read_time_domain,
)
from reasonsmith.verdict import Strength, Verdict

#: A duty over a trace, with no clock of its own — the shape every shipped temporal duty has.
_TIMING = Requirement(
    id="clocked_duty",
    source_document="Test",
    article_clause="§1",
    verbatim_text="A notice shall be given within thirty days.",
    stakeholder="affected individual",
    formalism="temporal",
    spec="always(latency_days <= 30)",
    rationale="Every decision the log records was notified within thirty days.",
    requires=("latency_days",),
    binding=True,
    scope="",
    domains=(),
    deontic_type="obligation",
    defeasibility="strict",
)


def _timeless_trace() -> list[dict[str, object]]:
    return [{"latency_days": 3}, {"latency_days": 5}]


def _clocked_trace() -> list[dict[str, object]]:
    """The same two decisions, each recording which event its clock started at."""
    return [
        {
            "latency_days": 3,
            TIME_DOMAIN_KEY: {
                "completed_application_received": "2026-06-01T09:00:00Z",
                "applicant_notified": "2026-06-04T09:00:00Z",
            },
        },
        {
            "latency_days": 5,
            TIME_DOMAIN_KEY: {
                "adverse_action_on_existing_account": "2026-06-10T09:00:00Z",
                "applicant_notified": "2026-06-15T09:00:00Z",
            },
        },
    ]


# --- What a trace states ----------------------------------------------------------------------


def test_a_log_without_event_times_states_no_time_domain() -> None:
    """The backwards-compatible answer: no clock is acquired by having been read."""
    domain = read_time_domain(_timeless_trace())
    assert domain is ORDINAL_DOMAIN
    assert domain.kind == ORDINAL_TIME
    assert domain.events == ()


def test_an_unread_or_empty_trace_states_no_time_domain() -> None:
    assert read_time_domain([]) is ORDINAL_DOMAIN


def test_a_record_may_carry_event_timestamps_and_event_kinds() -> None:
    domain = read_time_domain(_clocked_trace())
    assert domain.kind == EVENT_TIME
    assert len(domain.events) == 2
    assert domain.events[0]["applicant_notified"] == "2026-06-04T09:00:00Z"


def test_the_three_events_the_clause_counts_from_are_distinguishable() -> None:
    """12 CFR 1002.9(a)(1) is the worked case: each paragraph starts its clock somewhere else."""
    records = [
        {
            TIME_DOMAIN_KEY: {
                kind: "2026-06-01T09:00:00Z",
                "applicant_notified": "2026-07-01T09:00:00Z",
            }
        }
        for kind in ECOA_1002_9_A_1_EVENTS[:3]
    ]
    domain = read_time_domain(records)
    started_at = [sorted(set(events) - {"applicant_notified"})[0] for events in domain.events]
    assert started_at == list(ECOA_1002_9_A_1_EVENTS[:3])
    assert len(set(started_at)) == 3


def test_one_clocked_record_is_enough_to_state_the_domain() -> None:
    """A partly-clocked log is a clocked log, and the records without a clock say so as None."""
    records = _timeless_trace()
    records[1][TIME_DOMAIN_KEY] = {"applicant_notified": "2026-06-15T09:00:00Z"}
    domain = read_time_domain(records)
    assert domain.kind == EVENT_TIME
    assert domain.events[0] is None


def test_a_malformed_clock_is_refused_rather_than_read() -> None:
    with pytest.raises(TypeError, match="event-kind name"):
        read_time_domain([{TIME_DOMAIN_KEY: "2026-06-01T09:00:00Z"}])
    with pytest.raises(ValueError, match="non-empty name"):
        read_time_domain([{TIME_DOMAIN_KEY: {"  ": "2026-06-01T09:00:00Z"}}])
    with pytest.raises(ValueError, match="must carry a timestamp"):
        read_time_domain([{TIME_DOMAIN_KEY: {"applicant_notified": None}}])


def test_only_the_ordinal_domain_has_a_time_axis() -> None:
    """The seam: a metric semantics is a new kind and a new branch, not a relabelling."""
    assert ORDINAL_DOMAIN.ticks(3) == [0, 1, 2]
    with pytest.raises(ValueError, match="counts decisions, not seconds"):
        TimeDomain(EVENT_TIME).ticks(3)


# --- What the monitor is fed ------------------------------------------------------------------


def test_a_timeless_log_still_gets_the_record_index() -> None:
    """The stated default is the old convention, so nothing that worked stops working."""
    result = ObservedEngine.evaluate(_TIMING, BaseSUT(set(_TIMING.requires)), _timeless_trace())
    assert result.verdict is Verdict.SATISFIED
    assert result.strength is Strength.OBSERVED
    assert result.details["evaluation_scores"][0][0] == 0


def test_passing_the_ordinal_domain_is_the_same_run_as_passing_nothing() -> None:
    sut = BaseSUT(set(_TIMING.requires))
    stated = ObservedEngine.evaluate(_TIMING, sut, _timeless_trace(), time_domain=ORDINAL_DOMAIN)
    implied = ObservedEngine.evaluate(_TIMING, sut, _timeless_trace())
    assert stated.verdict is implied.verdict is Verdict.SATISFIED
    assert stated.details["evaluation_scores"] == implied.details["evaluation_scores"]


def test_a_clocked_log_keeps_the_verdict_a_timeless_one_would_have_had() -> None:
    """Recording when things happened must never cost a system an answer it already had."""
    result = ObservedEngine.evaluate(_TIMING, BaseSUT(set(_TIMING.requires)), _clocked_trace())
    assert result.verdict is Verdict.SATISFIED
    assert result.strength is Strength.OBSERVED


# --- What a duty needing a real clock gets ----------------------------------------------------


@pytest.mark.parametrize("records", [_timeless_trace(), _clocked_trace()])
def test_a_duty_needing_a_clock_is_not_evaluated_and_never_satisfied(
    records: list[dict[str, object]],
) -> None:
    result = ObservedEngine.evaluate(
        _TIMING, BaseSUT(set(_TIMING.requires)), records, time_domain=TimeDomain(EVENT_TIME)
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.verdict is not Verdict.SATISFIED
    assert result.strength is None
    assert result.evidence_summary.startswith("Not evaluated:")
    assert result.details["time_domain_required"] == EVENT_TIME


def test_the_refusal_says_which_of_the_two_gaps_it_hit() -> None:
    """A log with no clock and a log with a clock nothing reads are different facts."""
    sut = BaseSUT(set(_TIMING.requires))
    timeless = ObservedEngine.evaluate(
        _TIMING, sut, _timeless_trace(), time_domain=TimeDomain(EVENT_TIME)
    )
    clocked = ObservedEngine.evaluate(
        _TIMING, sut, _clocked_trace(), time_domain=TimeDomain(EVENT_TIME)
    )
    assert timeless.details["time_domain_stated_by_trace"] == ORDINAL_TIME
    assert "no event times at all" in timeless.evidence_summary
    assert clocked.details["time_domain_stated_by_trace"] == EVENT_TIME
    assert "no metric or interval semantics reads them yet" in clocked.evidence_summary


# --- What the envelope says -------------------------------------------------------------------


def test_the_report_states_the_clock_the_trace_stated() -> None:
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    assert report.to_dict()["time_domain"] == ORDINAL_TIME
