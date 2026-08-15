"""Rule-system example exposing logic for a proved Seoul Commitment IV result."""

from __future__ import annotations

from dataclasses import replace

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

SIGNALS = {
    "artifact_logs_frontier_risk_score",
    "scope_statements_frontier_risk_threshold",
    "artifact_logs_mitigation_available",
    "artifact_logs_deployment_decision",
}

VARIABLES = {
    "frontier_capability_score": "real",
    "frontier_misuse_score": "real",
    "artifact_logs_frontier_risk_score": "real",
    "scope_statements_frontier_risk_threshold": "real",
    "artifact_logs_mitigation_available": "real",
    "artifact_logs_deployment_decision": "real",
}

RULES = [
    "artifact_logs_frontier_risk_score = frontier_capability_score + frontier_misuse_score",
    """if (
    artifact_logs_frontier_risk_score >= scope_statements_frontier_risk_threshold
    and artifact_logs_mitigation_available < 0.5
):
    artifact_logs_deployment_decision = 0.0
else:
    artifact_logs_deployment_decision = 1.0""",
]

TEST_INPUTS = [
    {
        "frontier_capability_score": 0.4,
        "frontier_misuse_score": 0.4,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 0.0,
    },
    {
        "frontier_capability_score": 0.39,
        "frontier_misuse_score": 0.4,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 0.0,
    },
    {
        "frontier_capability_score": 0.7,
        "frontier_misuse_score": 0.3,
        "scope_statements_frontier_risk_threshold": 0.8,
        "artifact_logs_mitigation_available": 1.0,
    },
]

REQUIREMENT_ID = "seoul_frontier_iv_no_deployment_above_threshold"


def system_under_test() -> RulesAdapter:
    system = RulesAdapter(
        RULES,
        variables=VARIABLES,
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
            system_under_test(), duty, system_name="frontier-risk (rules)"
        ).render_text()
    )


if __name__ == "__main__":
    main()
