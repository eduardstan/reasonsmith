"""Record engine for reasonsmith v0.2.

What this module is for:
  Evaluates record-keeping requirements (`formalism = "record"`) over decision traces.

What a reader must not break:
  - An empty trace is reported as NOT EVALUATED (`strength=None`), never satisfied.
    Why this matters: Having observed zero decisions provides no empirical evidence that required
    fields are kept.
  - A missing value in an observed record is an observed violation (`VIOLATED`, `OBSERVED`).
    Why this matters: Every observed decision record must carry every required signal to satisfy
    record-keeping duties.
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
                binding=req.binding,
                scope=req.scope,
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
            violation_indices = [
                idx
                for idx, rec in enumerate(records)
                if any(not _is_present(rec.get(sig)) for sig in absent)
            ]
            offending_segment = [records[idx] for idx in violation_indices]
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
                    "offending_trace_segment": offending_segment,
                    "violation_step_indices": violation_indices,
                },
                binding=req.binding,
                scope=req.scope,
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
            binding=req.binding,
            scope=req.scope,
        )
