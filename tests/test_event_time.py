"""Soundness pins for the explicit-offset event clock and bounded-response operator."""

from __future__ import annotations

from datetime import timezone

import pytest

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.event_time import (
    EventTimeError,
    add_calendar_months,
    deadline_for,
    measure_pair,
    parse_duration,
    parse_timestamp,
)
from reasonsmith.render import render_html, render_text
from reasonsmith.report import ConformanceReport
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    classify_fragment,
    parse_property,
)
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.sut import EVENT_DOMAIN, TIME_DOMAIN_KEY, BaseSUT
from reasonsmith.verdict import Strength, Verdict


def _req(
    spec: str = (
        'always(implies(present(aware), within_after(present(aware), present(report), "24h")))'
    ),
) -> Requirement:
    return Requirement(
        id="event_deadline",
        source_document="Test",
        article_clause="§1",
        verbatim_text="A report follows awareness.",
        stakeholder="regulator",
        formalism="temporal",
        spec=spec,
        rationale="Formalized subset only: this test checks the explicit clock bound.",
        requires=("aware", "report"),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="trigger-unmodelled",
    )


def _trace(start: str, end: str, *, case_id: str = "case-1") -> list[dict[str, object]]:
    return [
        {"case_id": case_id, "aware": True, TIME_DOMAIN_KEY: {"aware": start}},
        {"case_id": case_id, "report": True, TIME_DOMAIN_KEY: {"report": end}},
    ]


def _evaluate(records: list[dict[str, object]]):
    return ObservedEngine.evaluate(_req(), BaseSUT({"aware", "report"}), records)


def test_exactly_at_the_closed_24_hour_boundary_is_satisfied() -> None:
    result = _evaluate(_trace("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"))
    assert result.verdict is Verdict.SATISFIED
    assert result.strength is Strength.OBSERVED
    assert result.details["event_pairs"][0]["delta_seconds"] == 86400.0
    assert result.details["event_pairs"][0]["bound"] == "24h"


def test_just_over_the_boundary_is_a_recheckable_violation() -> None:
    result = _evaluate(_trace("2026-01-01T00:00:00Z", "2026-01-02T00:00:01Z"))
    assert result.verdict is Verdict.VIOLATED
    pair = result.details["witness"]["payload"]
    assert pair["delta_seconds"] == 86401.0
    checked = measure_pair(
        pair["case_id"],
        parse_timestamp(pair["anchor_timestamp"]),
        parse_timestamp(pair["end_timestamp"]),
        parse_duration(pair["bound"]),
        anchor_record_index=pair["anchor_record_index"],
        end_record_index=pair["end_record_index"],
    )
    assert checked.within_bound is False


def test_offsets_are_normalised_before_subtraction_including_a_dst_transition() -> None:
    result = _evaluate(_trace("2026-03-08T01:30:00-05:00", "2026-03-09T02:30:00-04:00"))
    assert result.verdict is Verdict.SATISFIED
    assert result.details["event_pairs"][0]["delta_seconds"] == 86400.0
    assert parse_timestamp("2026-03-08T01:30:00-05:00").tzinfo is timezone.utc


def test_leap_day_is_an_actual_elapsed_day() -> None:
    result = _evaluate(_trace("2028-02-29T12:00:00Z", "2028-03-01T12:00:00Z"))
    assert result.verdict is Verdict.SATISFIED


def test_calendar_month_end_clamps_instead_of_guessing_thirty_days() -> None:
    start = parse_timestamp("2026-01-31T12:00:00Z")
    assert deadline_for(start, parse_duration("1mo")) == parse_timestamp("2026-02-28T12:00:00Z")
    assert add_calendar_months(parse_timestamp("2028-01-31T12:00:00Z"), 1) == parse_timestamp(
        "2028-02-29T12:00:00Z"
    )


def test_event_metric_uses_calendar_month_deadline_without_day_guessing() -> None:
    req = _req(
        'always(implies(present(aware), within_after(present(aware), present(report), "1mo")))'
    )
    result = ObservedEngine.evaluate(
        req,
        BaseSUT({"aware", "report"}),
        _trace("2026-01-31T12:00:00Z", "2026-02-28T12:00:00Z"),
    )
    assert result.verdict is Verdict.SATISFIED
    assert result.details["event_pairs"][0]["deadline_timestamp"] == "2026-02-28T12:00:00Z"


@pytest.mark.parametrize(
    "records",
    [
        [{"case_id": "c", "aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}}],
        [{"case_id": "c", "report": True, TIME_DOMAIN_KEY: {"report": "2026-01-01T00:00:00Z"}}],
        [
            {"case_id": "c", "aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
            {"case_id": "c", "aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T01:00:00Z"}},
            {"case_id": "c", "report": True, TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:00Z"}},
        ],
        [{"case_id": "c", "aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00"}}],
        [
            {"aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
            {"report": True, TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:00Z"}},
        ],
    ],
)
def test_incomplete_or_ambiguous_event_evidence_is_not_evaluated(records) -> None:
    result = _evaluate(records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None


def test_the_missing_timestamp_diagnostic_names_only_the_events_the_record_claimed() -> None:
    """A record is told it lacks a timestamp for what it asserted, never for what it never did."""
    result = _evaluate(
        [
            {"case_id": "c", "aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
            {"case_id": "c", "report": True},
        ]
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.details["missing_event_timestamps"] == [
        {"record_index": 1, "events": ["report"]}
    ]


def test_no_trigger_is_not_a_false_pass() -> None:
    result = _evaluate([{"case_id": "c", TIME_DOMAIN_KEY: {}}])
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "vacuous_trigger" in result.details


def test_event_operator_never_falls_back_to_ordinal_or_logged_latency() -> None:
    result = ObservedEngine.evaluate(
        _req(),
        BaseSUT({"aware", "report"}),
        [{"aware": True, "report": True, "latency": 0}],
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["time_domain_required"] == "event"


def test_explicit_ordinal_request_is_refused_for_metric_property() -> None:
    result = ObservedEngine.evaluate(
        _req(),
        BaseSUT({"aware", "report"}),
        _trace("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        time_domain=EVENT_DOMAIN.__class__("ordinal"),
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None


def test_existing_ordinal_property_is_unchanged_when_timestamps_are_added() -> None:
    req = Requirement(
        id="ordinal", source_document="Test", article_clause="§2", verbatim_text="x",
        stakeholder="s", formalism="temporal", spec="always(latency <= 30)",
        rationale="A positional latency check.", requires=("latency",), binding=True, scope="",
        domains=(), deontic_type="obligation", defeasibility="strict",
    )
    records = [{"latency": 3}, {"latency": 5}]
    clocked = [
        {**records[0], TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
        {**records[1], TIME_DOMAIN_KEY: {"report": "2026-01-01T00:01:00Z"}},
    ]
    plain = ObservedEngine.evaluate(req, BaseSUT({"latency"}), records)
    enriched = ObservedEngine.evaluate(req, BaseSUT({"latency"}), clocked)
    assert (plain.verdict, plain.strength) == (enriched.verdict, enriched.strength)
    assert plain.details["evaluation_scores"] == enriched.details["evaluation_scores"]


def test_cra_pack_lands_the_event_time_duty() -> None:
    req = load_pack("cra").requirements[0]
    assert req.article_clause == "Article 14(2)(a)"
    assert classify_fragment(req.spec) == "temporal"
    anchor, endpoint = req.requires
    sut = BaseSUT(set(req.requires))

    on_the_boundary = ObservedEngine.evaluate(
        req,
        sut,
        [
            {"case_id": "v-1", anchor: True, TIME_DOMAIN_KEY: {anchor: "2026-01-01T00:00:00Z"}},
            {"case_id": "v-1", endpoint: True, TIME_DOMAIN_KEY: {endpoint: "2026-01-02T00:00:00Z"}},
        ],
    )
    assert on_the_boundary.verdict is Verdict.SATISFIED
    assert on_the_boundary.strength is Strength.OBSERVED
    assert on_the_boundary.details["event_pairs"][0]["delta_seconds"] == 86400.0

    one_second_late = ObservedEngine.evaluate(
        req,
        sut,
        [
            {"case_id": "v-1", anchor: True, TIME_DOMAIN_KEY: {anchor: "2026-01-01T00:00:00Z"}},
            {"case_id": "v-1", endpoint: True, TIME_DOMAIN_KEY: {endpoint: "2026-01-02T00:00:01Z"}},
        ],
    )
    assert one_second_late.verdict is Verdict.VIOLATED


def test_a_metric_violation_names_its_offending_records_in_both_renderings() -> None:
    """A witness that reaches only the JSON is a witness no reader of a report ever sees."""
    anchor_record = {
        "case_id": "v-1",
        "decision_id": "d-aware",
        "aware": True,
        TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"},
    }
    endpoint_record = {
        "case_id": "v-1",
        "decision_id": "d-notify",
        "report": True,
        TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:01Z"},
    }
    result = _evaluate([anchor_record, endpoint_record])
    assert result.verdict is Verdict.VIOLATED
    assert result.details["violation_step_indices"] == [0, 1]

    report = ConformanceReport(
        pack_id="test",
        system_name="SUT",
        system_scope=None,
        system_domains=(),
        results=(result,),
        time_domain="event",
    )
    text = render_text(report)
    assert "offending records: decision d-aware (step 0), decision d-notify (step 1)" in text
    assert "d-notify" in render_html(report)


def test_an_unnamed_record_never_merges_with_a_case_spelled_like_its_index() -> None:
    result = _evaluate(
        [
            {"aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
            {
                "case_id": "record-0",
                "report": True,
                TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:00Z"},
            },
        ]
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "event_pairs" not in result.details


def test_a_bound_naming_an_unrepresentable_instant_is_refused_not_raised() -> None:
    with pytest.raises(EventTimeError):
        deadline_for(parse_timestamp("2026-01-01T00:00:00Z"), parse_duration("1000000000d"))
    with pytest.raises(EventTimeError):
        deadline_for(parse_timestamp("2026-01-01T00:00:00Z"), parse_duration("999999mo"))

    result = ObservedEngine.evaluate(
        _req(
            'always(implies(present(aware), '
            'within_after(present(aware), present(report), "1000000000d")))'
        ),
        BaseSUT({"aware", "report"}),
        _trace("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"),
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None


def test_an_enclosing_trigger_that_is_not_the_anchor_is_refused_at_load() -> None:
    with pytest.raises(UnsupportedConstructError):
        parse_property(
            'always(implies(present(other), '
            'within_after(present(aware), present(report), "24h")))'
        )
    assert (
        classify_fragment(
            'always(implies(present(aware), '
            'within_after(present(aware), present(report), "24h")))'
        )
        == "temporal"
    )


def test_a_malformed_clock_is_refused_rather_than_raised_on_a_positional_duty() -> None:
    req = Requirement(
        id="ordinal", source_document="Test", article_clause="§2", verbatim_text="x",
        stakeholder="s", formalism="temporal", spec="always(latency <= 30)",
        rationale="A positional latency check.", requires=("latency",), binding=True, scope="",
        domains=(), deontic_type="obligation", defeasibility="strict",
    )
    result = ObservedEngine.evaluate(
        req,
        BaseSUT({"latency"}),
        [{"latency": 3, TIME_DOMAIN_KEY: {"aware": "2026-01-01"}}],
        time_domain=EVENT_DOMAIN,
    )
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None


def test_timestamp_and_duration_refuse_naive_or_invalid_values() -> None:
    with pytest.raises(EventTimeError):
        parse_timestamp("2026-01-01T00:00:00")
    with pytest.raises(EventTimeError):
        parse_timestamp("2026-02-30T00:00:00Z")
    with pytest.raises(EventTimeError):
        parse_duration("1y")


def test_an_uncorrelated_record_cannot_be_named_by_a_case_id() -> None:
    """The reader-facing case name is disjoint the way the correlation key already is."""
    unnamed = _evaluate(
        [
            {"aware": True, TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"}},
            {"report": True, TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:00Z"}},
        ]
    )
    assert unnamed.verdict is Verdict.INCONCLUSIVE
    assert [
        problem for problem in unnamed.details["correlation_problems"]
        if "<unnamed record 0>" in problem
    ]

    reserved = _evaluate(
        [
            {
                "case_id": "<unnamed record 0>",
                "aware": True,
                TIME_DOMAIN_KEY: {"aware": "2026-01-01T00:00:00Z"},
            },
            {
                "case_id": "<unnamed record 0>",
                "report": True,
                TIME_DOMAIN_KEY: {"report": "2026-01-02T00:00:00Z"},
            },
        ]
    )
    assert reserved.verdict is Verdict.INCONCLUSIVE
    assert "reserved" in reserved.evidence_summary
    assert "event_pairs" not in reserved.details
