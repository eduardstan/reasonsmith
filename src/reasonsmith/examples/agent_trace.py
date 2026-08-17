"""Synthetic, recorder-outside-the-agent trace fixture for issue #273.

The ``SyntheticAgent`` returns a self-report, but ``BoundaryRecorder`` never uses that field as
proof. It records ingress and the user-visible response as separate, recorder-attested events.
The fixture is intentionally local, deterministic, and contains no real interaction or personal
data; it is evidence-shape scaffolding, not an agent implementation or a compliance claim.
"""

from __future__ import annotations

from typing import Any

from reasonsmith.sut import (
    AGENT_TRACE_COMPLETE_KEY,
    AGENT_TRACE_EVENTS_KEY,
    AGENT_TRACE_EXECUTION_ID_KEY,
    AGENT_TRACE_KEY,
    AGENT_TRACE_SCHEMA_VERSION,
    AGENT_TRACE_SCHEMA_VERSION_KEY,
    AGENT_TRACE_TIME_DOMAIN_KEY,
    BOUNDARY_RECORDER_SOURCE,
    EVENT_CORRELATION_ID_KEY,
    EVENT_ID_KEY,
    EVENT_KIND_KEY,
    EVENT_SOURCE_ATTESTED_KEY,
    EVENT_SOURCE_ID_KEY,
    EVENT_SOURCE_KEY,
    EVENT_SOURCE_KIND_KEY,
    EVENT_SOURCE_PROVENANCE_KEY,
    EVENT_TIME,
    EVENT_TIMESTAMP_KEY,
    TIME_DOMAIN_KEY,
    BaseSUT,
)

INTERACTION_TIMESTAMP = "2026-08-17T09:00:00Z"
DISCLOSURE_TIMESTAMP = "2026-08-17T09:00:00Z"
EXECUTION_ID = "synthetic-execution-1"
CORRELATION_ID = "synthetic-interaction-1"
DISCLOSURE_TEXT = "You are interacting with an AI assistant."
ARTICLE_50_SIGNALS = {
    "artifact_logs_natural_person_interaction",
    "artifact_logs_ai_disclosure",
}


def _source(provenance: str) -> dict[str, Any]:
    return {
        EVENT_SOURCE_KIND_KEY: BOUNDARY_RECORDER_SOURCE,
        EVENT_SOURCE_ID_KEY: "synthetic-boundary-recorder",
        EVENT_SOURCE_PROVENANCE_KEY: provenance,
        EVENT_SOURCE_ATTESTED_KEY: True,
    }


class SyntheticAgent:
    """A deterministic subject that includes a self-report in its response payload."""

    def first_response(self, prompt: str) -> dict[str, Any]:
        return {
            "prompt": prompt,
            "visible_text": DISCLOSURE_TEXT,
            # This value is deliberately not consumed by BoundaryRecorder.
            "disclosure_delivered": True,
        }


class BoundaryRecorder:
    """Capture one interaction at the boundary, independently of the agent's self-report."""

    def __init__(self, *, include_disclosure: bool = True) -> None:
        self.include_disclosure = include_disclosure

    def capture(self) -> list[dict[str, Any]]:
        agent = SyntheticAgent()
        response = agent.first_response("Synthetic first interaction")
        events: list[dict[str, Any]] = [
            {
                EVENT_ID_KEY: "synthetic-event-interaction",
                EVENT_KIND_KEY: "natural_person_interaction",
                EVENT_TIMESTAMP_KEY: INTERACTION_TIMESTAMP,
                EVENT_CORRELATION_ID_KEY: CORRELATION_ID,
                EVENT_SOURCE_KEY: _source("recorder observed synthetic ingress"),
            }
        ]
        timestamps: dict[str, str] = {
            "natural_person_interaction": INTERACTION_TIMESTAMP,
        }
        first: dict[str, Any] = {
            AGENT_TRACE_KEY: {
                AGENT_TRACE_SCHEMA_VERSION_KEY: AGENT_TRACE_SCHEMA_VERSION,
                AGENT_TRACE_EXECUTION_ID_KEY: EXECUTION_ID,
                AGENT_TRACE_COMPLETE_KEY: True,
                AGENT_TRACE_TIME_DOMAIN_KEY: EVENT_TIME,
                AGENT_TRACE_EVENTS_KEY: events,
            },
            TIME_DOMAIN_KEY: timestamps,
            "artifact_logs_natural_person_interaction": "recorder observed ingress",
            # Kept in the fixture to make the independence test visible. The schema validator
            # never treats this subject-authored field as the disclosure event.
            "disclosure_delivered": response["disclosure_delivered"],
        }
        if self.include_disclosure:
            events.append(
                {
                    EVENT_ID_KEY: "synthetic-event-disclosure",
                    EVENT_KIND_KEY: "ai_disclosure",
                    EVENT_TIMESTAMP_KEY: DISCLOSURE_TIMESTAMP,
                    EVENT_CORRELATION_ID_KEY: CORRELATION_ID,
                    EVENT_SOURCE_KEY: _source("recorder observed user-visible egress"),
                }
            )
            timestamps["ai_disclosure"] = DISCLOSURE_TIMESTAMP
            first["artifact_logs_ai_disclosure"] = response["visible_text"]

        # A second trace position gives the existing discrete monitor its normal two-sample
        # input. It carries the same declared execution boundary but no additional interaction.
        end = {
            AGENT_TRACE_KEY: {
                AGENT_TRACE_SCHEMA_VERSION_KEY: AGENT_TRACE_SCHEMA_VERSION,
                AGENT_TRACE_EXECUTION_ID_KEY: EXECUTION_ID,
                AGENT_TRACE_COMPLETE_KEY: True,
                AGENT_TRACE_TIME_DOMAIN_KEY: EVENT_TIME,
                AGENT_TRACE_EVENTS_KEY: [],
            },
            TIME_DOMAIN_KEY: {},
            "execution_boundary": "synthetic recorder closed",
        }
        return [first, end]


class AgentTraceSUT(BaseSUT):
    """A limited-risk SUT exposing only the recorder fixture's two Article 50 signals."""

    system_scope = "limited-risk"
    system_domains: tuple[str, ...] = ()

    def __init__(self, *, include_disclosure: bool = True) -> None:
        super().__init__(ARTICLE_50_SIGNALS)
        self.include_disclosure = include_disclosure

    def decisions(self) -> list[dict[str, Any]]:
        return BoundaryRecorder(include_disclosure=self.include_disclosure).capture()


def recorder_sut() -> AgentTraceSUT:
    """The complete positive recorder trace."""
    return AgentTraceSUT(include_disclosure=True)


def omitted_disclosure_sut() -> AgentTraceSUT:
    """The negative trace: the recorder deliberately captured no disclosure event."""
    return AgentTraceSUT(include_disclosure=False)


class SelfReportingSUT(BaseSUT):
    """A deliberately unsafe subject-authored trace used to pin the acceptance boundary."""

    system_scope = "limited-risk"
    system_domains: tuple[str, ...] = ()

    def __init__(self) -> None:
        super().__init__(ARTICLE_50_SIGNALS | {"disclosure_delivered"})

    def decisions(self) -> list[dict[str, Any]]:
        return [
            {
                "artifact_logs_natural_person_interaction": "agent says interaction happened",
                "artifact_logs_ai_disclosure": "agent says disclosure delivered",
                "disclosure_delivered": True,
            },
            {"execution_boundary": "agent says trace is complete"},
        ]


system_under_test = recorder_sut
