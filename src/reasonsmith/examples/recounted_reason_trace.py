"""A synthetic notice generator that recounts the reasons behind one decision.

What this module is for:
  This is the worked example for the ``recounted`` rung.  The notice generator can re-run its
  answer when reasonsmith suppresses a fact, but it exposes no model encoding from which the
  reasons could be enumerated.  Its reason trace is the generator's own account, so the deletion
  measurement reaches ``recounted`` rather than ``probed``.

  Run: ``python -m reasonsmith.examples.recounted_reason_trace``

What a reader must not break:
  - ``artifact()`` returns a :class:`ReasonTraceArtifact`, not a rule set or another enumerable
    encoding.  The two named reasons are only what this synthetic system says it used.
  - The deletion probe is still performed by reasonsmith.  ``answer`` is re-run with each named
    fact suppressed, so the result measures whether the answer depends on the reasons the system
    recounted.  It does not establish that the list is complete.
  - ``logic()`` remains ``None``.  Adding a hand-written encoding would change this example into
    the ``probed`` ground-program family and erase the distinction this module demonstrates.
  - The data and reason labels are frozen synthetic fixtures for documentation and tests only.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from reasonsmith.artifacts.reason_trace import ReasonTraceArtifact
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

REQUIREMENT_ID = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"
DECLARED_DOMAINS = ("consumer-credit",)
DELETED_REASON_COUNT = "artifact_logs_deleted_reason_count"

DECISION = {
    "decision_id": "RT-1001",
    "decision": "adverse_action",
    "artifact_logs_reason_explanation": (
        "R01 — debt-to-income ratio; R02 — recent delinquency"
    ),
    DELETED_REASON_COUNT: 2,
}

#: The system's own synthetic inference: both facts contribute to the decision score.
FACT_WEIGHTS = {"debt_to_income": 0.6, "recent_delinquency": 0.4}


def _answer(suppressed: frozenset) -> float:
    """Re-run the synthetic decision after withholding the supplied facts."""
    return sum(weight for fact, weight in FACT_WEIGHTS.items() if fact not in suppressed)


class RecountedNoticeSystem:
    """A replayable notice generator whose rationale is a self-reported reason trace only."""

    system_domains = DECLARED_DOMAINS

    def capabilities(self) -> set[str]:
        return {
            "decision_id",
            "decision",
            "artifact_logs_reason_explanation",
            DELETED_REASON_COUNT,
        }

    def decisions(self) -> list[dict[str, Any]]:
        return [dict(DECISION)]

    def logic(self) -> None:
        """This system has no exposed encoding for reasonsmith to enumerate."""
        return

    def artifact(self, decision: dict[str, Any]) -> ReasonTraceArtifact:
        """Return only the system's own account of the reasons for this decision."""
        if decision.get("decision_id") != DECISION["decision_id"]:
            raise ValueError(f"unknown decision {decision.get('decision_id')!r}")
        return ReasonTraceArtifact(
            decision["decision_id"],
            {
                "R01 — debt-to-income ratio": frozenset({"debt_to_income"}),
                "R02 — recent delinquency": frozenset({"recent_delinquency"}),
            },
            _answer,
            engine_name="synthetic-notice-generator",
            claimed_semantics="free-text rationale",
            monotone=True,
            recounted_by="the notice generator",
        )


def system_under_test() -> RecountedNoticeSystem:
    """The synthetic system as reasonsmith sees it: trace plus a recounted rationale."""
    return RecountedNoticeSystem()


def main() -> None:
    pack = load_pack("ecoa")
    one_duty = replace(
        pack,
        id=f"{pack.id}:{REQUIREMENT_ID}",
        requirements=(pack.get_requirement(REQUIREMENT_ID),),
    )
    report = check_conformance(
        system_under_test(),
        one_duty,
        system_name="recounted-notice (synthetic reason trace)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
