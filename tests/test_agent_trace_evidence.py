"""Issue #273: only an external recorder may establish the Article 50 disclosure pair."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.examples.agent_trace import (
    AgentTraceSUT,
    SelfReportingSUT,
    omitted_disclosure_sut,
    recorder_sut,
)
from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.sut import (
    AGENT_TRACE_COMPLETE_KEY,
    AGENT_TRACE_EVENTS_KEY,
    AGENT_TRACE_KEY,
    AGENT_TRACE_SCHEMA_VERSION_KEY,
    AGENT_TRACE_TIME_DOMAIN_KEY,
    EVENT_SOURCE_KEY,
    EVENT_SOURCE_KIND_KEY,
    EVENT_TIME,
    ExecutionRecordError,
    read_execution_record,
    read_time_domain,
    validate_recorder_attestation,
)
from reasonsmith.verdict import Strength, Verdict

REQUIREMENT = next(
    requirement
    for requirement in load_pack("eu_ai_act").requirements
    if requirement.id == "eu_ai_act_art50_5_disclosure_timing"
)


def _result(sut: Any, records: list[dict[str, Any]] | None = None):
    return evaluate_requirement(REQUIREMENT, sut, records=records)


def test_complete_boundary_pair_reaches_observed() -> None:
    result = _result(recorder_sut())
    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.OBSERVED)


def test_omitted_disclosure_is_a_refusal_not_a_temporal_violation() -> None:
    result = _result(omitted_disclosure_sut())
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "execution_record_refusal" in result.details
    assert "ai_disclosure" in result.evidence_summary
    assert result.verdict is not Verdict.SATISFIED
    assert result.verdict is not Verdict.VIOLATED


def test_self_reported_disclosure_field_cannot_reach_observed() -> None:
    result = _result(SelfReportingSUT())
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "self-reported disclosure field" in result.evidence_summary


def test_renaming_the_self_report_does_not_bypass_the_boundary() -> None:
    renamed = replace(
        REQUIREMENT,
        id="article_50_renamed_disclosure",
        spec="always(present(disclosure_delivered))",
        requires=("disclosure_delivered",),
    )
    result = evaluate_requirement(renamed, SelfReportingSUT())
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "self-reported disclosure field" in result.evidence_summary


def test_direct_observed_engine_keeps_the_same_boundary() -> None:
    records = SelfReportingSUT().decisions()
    result = ObservedEngine.evaluate(REQUIREMENT, SelfReportingSUT(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None


def test_complete_trace_exposes_version_clock_ids_and_sources() -> None:
    records = recorder_sut().decisions()
    envelope = read_execution_record(records)
    assert envelope.schema_version == 1
    assert envelope.execution_id == "synthetic-execution-1"
    assert envelope.complete is True
    assert envelope.time_domain.kind == EVENT_TIME
    assert len(envelope.events) == 2
    assert {event[EVENT_SOURCE_KEY][EVENT_SOURCE_KIND_KEY] for event in envelope.events} == {
        "boundary_recorder"
    }
    assert envelope.events[0]["correlation_id"] == envelope.events[1]["correlation_id"]


def test_read_time_domain_uses_the_existing_event_clock() -> None:
    records = recorder_sut().decisions()
    domain = read_time_domain(records)
    assert domain.kind == EVENT_TIME
    assert domain.events[0]["ai_disclosure"] == "2026-08-17T09:00:00Z"


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            lambda record: record[AGENT_TRACE_KEY].pop(AGENT_TRACE_COMPLETE_KEY),
            "completeness",
        ),
        (
            lambda record: record[AGENT_TRACE_KEY].__setitem__(
                AGENT_TRACE_SCHEMA_VERSION_KEY, 99
            ),
            "schema version",
        ),
        (
            lambda record: record[AGENT_TRACE_KEY].__setitem__(
                AGENT_TRACE_TIME_DOMAIN_KEY, "ordinal"
            ),
            "time_domain",
        ),
    ],
)
def test_missing_or_wrong_envelope_declarations_refuse(edit, message: str) -> None:
    records = recorder_sut().decisions()
    edit(records[0])
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert message in result.evidence_summary


def test_agent_source_is_not_boundary_attestation() -> None:
    records = recorder_sut().decisions()
    source = records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][1][EVENT_SOURCE_KEY]
    source[EVENT_SOURCE_KIND_KEY] = "agent"
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "not the boundary recorder" in result.evidence_summary


def test_correlated_pair_is_required() -> None:
    records = recorder_sut().decisions()
    disclosure = records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][1]
    disclosure["correlation_id"] = "other-interaction"
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "correlation identifier" in result.evidence_summary


def test_event_clock_and_event_timestamp_must_agree() -> None:
    records = recorder_sut().decisions()
    records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][0]["timestamp"] = (
        "2026-08-17T09:01:00Z"
    )
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "disagrees with the event clock" in result.evidence_summary


def test_event_fields_are_materialized_by_the_recorder_not_only_metadata() -> None:
    records = recorder_sut().decisions()
    records[0].pop("artifact_logs_ai_disclosure")
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "not materialized" in result.evidence_summary


def test_non_attested_event_is_refused() -> None:
    records = recorder_sut().decisions()
    source = records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][1][EVENT_SOURCE_KEY]
    source["attested"] = False
    result = _result(recorder_sut(), records)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "not recorder-attested" in result.evidence_summary


def test_schema_reader_rejects_empty_trace() -> None:
    with pytest.raises(ExecutionRecordError, match="empty"):
        read_execution_record([])


def test_schema_reader_rejects_missing_event_list() -> None:
    records = recorder_sut().decisions()
    records[0][AGENT_TRACE_KEY].pop(AGENT_TRACE_EVENTS_KEY)
    with pytest.raises(ExecutionRecordError, match="events list"):
        read_execution_record(records)


def test_schema_reader_rejects_event_without_source() -> None:
    records = recorder_sut().decisions()
    records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][0].pop(EVENT_SOURCE_KEY)
    with pytest.raises(ExecutionRecordError, match="source/provenance"):
        read_execution_record(records)


def test_schema_reader_requires_consistent_execution_envelopes() -> None:
    records = recorder_sut().decisions()
    records[1][AGENT_TRACE_KEY]["execution_id"] = "another-execution"
    with pytest.raises(ExecutionRecordError, match="disagrees"):
        read_execution_record(records)


def test_recorder_validator_rejects_ambiguous_event_occurrence() -> None:
    records = recorder_sut().decisions()
    duplicate = deepcopy(records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY][1])
    duplicate["event_id"] = "synthetic-event-disclosure-duplicate"
    records[0][AGENT_TRACE_KEY][AGENT_TRACE_EVENTS_KEY].append(duplicate)
    with pytest.raises(ExecutionRecordError, match="missing or ambiguous"):
        validate_recorder_attestation(
            records,
            {
                "artifact_logs_natural_person_interaction": "natural_person_interaction",
                "artifact_logs_ai_disclosure": "ai_disclosure",
            },
            REQUIREMENT.requires,
        )


def test_recorder_validator_accepts_a_generator() -> None:
    records = recorder_sut().decisions()
    envelope = validate_recorder_attestation(
        (record for record in records),
        {
            "artifact_logs_natural_person_interaction": "natural_person_interaction",
            "artifact_logs_ai_disclosure": "ai_disclosure",
        },
        REQUIREMENT.requires,
    )
    assert envelope.execution_id == "synthetic-execution-1"


def test_non_article_signals_do_not_acquire_recorder_contract() -> None:
    assert read_execution_record is not None
    assert AgentTraceSUT().capabilities() == {
        "artifact_logs_natural_person_interaction",
        "artifact_logs_ai_disclosure",
    }
