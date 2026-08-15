"""Replayable example for Seoul Commitment IV's four-signal depth anchor."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

SIGNALS = {
    "artifact_logs_frontier_risk_score",
    "scope_statements_frontier_risk_threshold",
    "artifact_logs_mitigation_available",
    "artifact_logs_deployment_decision",
}


class FrontierRiskScorer:
    """Deterministic scorer whose deployment policy matches Commitment IV."""

    def decide(self, case: dict[str, Any]) -> dict[str, Any]:
        score = float(case["frontier_capability_score"]) + float(case["frontier_misuse_score"])
        threshold = float(case["scope_statements_frontier_risk_threshold"])
        mitigation = float(case["artifact_logs_mitigation_available"])
        deployment = 0.0 if score >= threshold and mitigation < 0.5 else 1.0
        return {
            **case,
            "artifact_logs_frontier_risk_score": score,
            "scope_statements_frontier_risk_threshold": threshold,
            "artifact_logs_mitigation_available": mitigation,
            "artifact_logs_deployment_decision": deployment,
        }


TEST_INPUTS = [
    # At threshold, no mitigation: no deployment satisfies the implication.
    {
        "frontier_capability_score": 0.4,
        "frontier_misuse_score": 0.4,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 0.0,
    },
    # Just below threshold: deployment is permitted.
    {
        "frontier_capability_score": 0.39,
        "frontier_misuse_score": 0.4,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 0.0,
    },
    # Mitigation available: deployment is permitted despite a high score.
    {
        "frontier_capability_score": 0.7,
        "frontier_misuse_score": 0.3,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 1.0,
    },
    {
        "frontier_capability_score": 0.2,
        "frontier_misuse_score": 0.2,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 0.0,
    },
]


REQUIREMENT_ID = "seoul_frontier_iv_no_deployment_above_threshold"


def system_under_test() -> CallableAdapter:
    system = CallableAdapter(
        FrontierRiskScorer(),
        declared_capabilities=SIGNALS,
        test_inputs=TEST_INPUTS,
        frontier_ai_status="frontier",
    )
    system.system_scope = "general-purpose"
    return system


system = system_under_test()


def main() -> None:
    pack = load_pack("seoul_frontier_ai_safety_2024")
    duty = replace(
        pack, id=f"{pack.id}:{REQUIREMENT_ID}", requirements=(pack.get_requirement(REQUIREMENT_ID),)
    )
    print(
        check_conformance(
            system_under_test(), duty, system_name="frontier-risk (replayable)"
        ).render_text()
    )


if __name__ == "__main__":
    main()
