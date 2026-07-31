"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.2.

The SUT protocol is deliberately minimal so that black-box neural models, rule engines,
and log traces qualify equally.

Capabilities are DECLARED by the system, never inferred. The unattainable analysis
relies on the system explicitly stating what signals it can emit.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Protocol, runtime_checkable


@runtime_checkable
class SystemUnderTest(Protocol):
    """Protocol for a system under test in reasonsmith."""

    def capabilities(self) -> set[str]:
        """Return the set of signal names this system declares it can emit."""
        ...

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return an iterable of decision trace records."""
        ...


class BaseSUT:
    """Convenience base class or reference helper for SUT implementations."""

    def __init__(self, declared_capabilities: set[str] | Iterable[str]):
        self._capabilities = set(declared_capabilities)

    def capabilities(self) -> set[str]:
        return set(self._capabilities)

    def decisions(self) -> Iterable[dict[str, Any]]:
        return []


class FullCapabilitySUT(BaseSUT):
    """Reference SUT declaring full capabilities for all Table 7 requirements."""

    ALL_TABLE7_SIGNALS = {
        "model_and_data_version_ids",
        "extraction_timestamp",
        "dataset_snapshot_hash",
        "fidelity_coverage_metrics",
        "explanation_scope",
        "linkage_from_decision_to_artifact",
        "automatic_event_logs",
        "retention_schedule",
        "signer",
        "reasons",
        "feature_to_named_concept_mapping",
        "dpia_cross_reference",
        "model_version",
        "score_factors",
        "audit_ids",
        "retention_for_regulatory_lookback",
        "design_history_links",
        "verification_logs",
        "change_control",
        "continuous_monitoring_logs",
        "metric_thresholds_and_alerts",
        "reviews_and_sign_offs",
        "incident_tickets",
        "decision",
        "timestamp",
    }

    def __init__(self, extra_capabilities: Optional[set[str]] = None):
        super().__init__(self.ALL_TABLE7_SIGNALS | (extra_capabilities or set()))
        self.execution_count = 0

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.execution_count += 1
        return [
            {
                "decision": "approved",
                "timestamp": "2026-07-31T09:00:00Z",
                "reasons": ["credit_score_above_700"],
                "model_and_data_version_ids": "v1.0.0",
                "extraction_timestamp": "2026-07-31T09:00:00Z",
                "dataset_snapshot_hash": "abc123hash",
                "fidelity_coverage_metrics": "fidelity=0.98",
                "explanation_scope": "local",
                "linkage_from_decision_to_artifact": "link_123",
                "automatic_event_logs": "log_record_123",
                "retention_schedule": "7_years",
                "signer": "sys_signer",
                "feature_to_named_concept_mapping": "mapping_v1",
                "dpia_cross_reference": "dpia_ref_001",
                "model_version": "v1.0.0",
                "score_factors": "score=750",
                "audit_ids": "audit_001",
                "retention_for_regulatory_lookback": "true",
                "design_history_links": "dhl_001",
                "verification_logs": "ver_log_001",
                "change_control": "cc_001",
                "continuous_monitoring_logs": "mon_001",
                "metric_thresholds_and_alerts": "thresh_001",
                "reviews_and_sign_offs": "signoff_001",
                "incident_tickets": "inc_001",
            }
        ]


class NoReasonsSUT(BaseSUT):
    """Reference SUT declaring capabilities without any reason-giving signal ('reasons').

    Attempting to call decisions() raises an AssertionError, proving that the
    unattainable analysis never executes the system.
    """

    def __init__(self):
        no_reasons_capabilities = FullCapabilitySUT.ALL_TABLE7_SIGNALS - {"reasons"}
        super().__init__(no_reasons_capabilities)
        self.was_executed = False

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.was_executed = True
        raise AssertionError(
            "NoReasonsSUT.decisions() must never be executed for unattainable checks!"
        )
