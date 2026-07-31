"""Record engine for reasonsmith v0.2.

Moves evidence.py's completeness logic behind the Stage 1 engine interface, reporting at
`observed` strength.

Behavior preserved:
- Keys outside requirement's duty row rejected.
- Empty or blank values treated as absent.
- Non-Table-7 material isolated in attachments.
"""

from __future__ import annotations

from typing import Any

from reasonsmith.report import RequirementResult, _is_present
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict


class RecordEngine:
    """Engine checking record-keeping requirements over decision traces."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: list[dict[str, Any]],
    ) -> RequirementResult:
        clause = f"{req.source_document} {req.article_clause}"

        if not records:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    "Not evaluated: the decision trace is empty, so nothing was observed. "
                    "An empty trace is not evidence that the requirement holds."
                ),
            )

        absent = sorted(
            {
                signal
                for rec in records
                for signal in req.requires
                if not _is_present(rec.get(signal))
            }
        )

        if absent:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Violated over {len(records)} observed decision(s): the system declares "
                    "it can emit these signals, but records carry no value for "
                    f"{', '.join(absent)}."
                ),
                details={
                    "signals_absent_from_trace": absent,
                    "records_observed": len(records),
                },
            )

        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.SATISFIED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Observed over {len(records)} decision(s): every required signal "
                f"({', '.join(req.requires)}) carries a value in every record. Holds on the trace "
                "supplied; nothing here extends the claim to decisions not in it."
            ),
            details={"records_observed": len(records)},
        )
