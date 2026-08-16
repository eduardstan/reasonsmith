"""Record engine for reasonsmith v0.10.2.

What this module is for:
  Evaluates record-keeping requirements (`formalism = "record"`) over decision traces. The
  property is the requirement's own `spec`: a conjunction of `present(signal)` atoms, parsed by
  `rulelang` and walked here conjunct by conjunct.

What a reader must not break:
  - An empty trace is reported as NOT EVALUATED (`strength=None`), never satisfied.
    Why this matters: Having observed zero decisions provides no empirical evidence that required
    fields are kept.
  - A missing value in an observed record is an observed violation (`VIOLATED`, `OBSERVED`).
    Why this matters: Every observed decision record must carry every required signal to satisfy
    record-keeping duties.
  - The conjunction is walked directly. A presence property must never be routed through the
    rtamt robustness monitor of `engines/observed.py` to gain uniformity with the temporal
    fragment.
    Why this matters: robustness is one number for the whole formula. It cannot say *which*
    conjunct failed, and this engine's entire diagnostic value is naming which signal was missing
    from which record index. Losing that to make two engines look alike is a bad trade.
  - A spec this engine cannot walk as a conjunction of presence atoms is reported NOT EVALUATED,
    never satisfied.
    Why this matters: the pack loader classifies the fragment and refuses a mismatch, so reaching
    here with anything else means a caller built the requirement by hand. Guessing at what it
    meant would answer a duty nobody wrote.
"""

from __future__ import annotations

from typing import Any

from reasonsmith.report import RequirementResult, _is_present
from reasonsmith.rulelang import UnsupportedConstructError, parse_property, presence_atoms
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

        try:
            signals = presence_atoms(parse_property(req.spec))
        except UnsupportedConstructError as exc:
            signals = None
            why = str(exc)
        else:
            why = (
                f"{req.spec!r} is not a conjunction of present(signal) atoms, which is the only "
                "shape this engine can name a failing conjunct in"
            )
        if not signals:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=f"Not evaluated: {why}.",
                details={"reason": "spec_not_a_presence_conjunction"},
                binding=req.binding,
                scope=req.scope,
            )

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

        # Walked conjunct by conjunct, in the order the property states them, so the finding can
        # name which `present(signal)` atom failed and in which record.
        absent = sorted(
            {
                signal
                for rec in records
                for signal in signals
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
                f"({', '.join(signals)}) carries a value in every record. Holds on the trace "
                "supplied; nothing here extends the claim to decisions not in it."
            ),
            details={"records_observed": len(records)},
            binding=req.binding,
            scope=req.scope,
        )
