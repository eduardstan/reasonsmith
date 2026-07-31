"""Observed engine for reasonsmith v0.2.

Evaluates temporal properties over decision traces using rtamt STL/MTL monitors.
Requirements with formalism = "temporal" become discrete-time monitors.

Behavior:
- Trace records are converted to discrete time series dataset for rtamt.
- A violation returns the offending trace segment in details and summary.
- If rtamt cannot express a formula, the requirement is reported as NOT EVALUATED
  with the reason (verdict=INCONCLUSIVE, strength=None) — never as satisfied.
"""

from __future__ import annotations

import re
from typing import Any

import rtamt

from reasonsmith.report import RequirementResult, _is_present
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict


class ObservedEngine:
    """Temporal monitor engine powered by rtamt."""

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
                    "Not evaluated: the decision trace is empty, so nothing was observed."
                ),
            )

        # Extract variable names from formula or req.requires
        var_names = set(req.requires)
        # Also extract identifiers from spec formula
        found_vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", req.spec))
        keywords = {
            "always", "eventually", "until", "then", "implies", "and", "or", "not",
            "true", "false", "historically", "once", "since", "rise", "fall", "prev"
        }
        spec_vars = (found_vars - keywords) | var_names

        # Build dataset for rtamt
        time_series: dict[str, list[float]] = {"time": list(range(len(records)))}
        for var in spec_vars:
            values: list[float] = []
            for rec in records:
                val = rec.get(var)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    values.append(float(val))
                elif isinstance(val, bool):
                    values.append(1.0 if val else 0.0)
                else:
                    # Categorical or presence check
                    values.append(1.0 if _is_present(val) else 0.0)
            time_series[var] = values

        # Construct rtamt STL specification
        try:
            spec = rtamt.StlDiscreteTimeSpecification()
            spec.name = f"spec_{req.id.replace('-', '_')}"
            for var in spec_vars:
                spec.declare_var(var, "float")
            spec.spec = req.spec
            spec.parse()
            res = spec.evaluate(time_series)
        except Exception as exc:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    "Not evaluated: rtamt cannot express or parse temporal property "
                    f"{req.spec!r}: {exc}"
                ),
                details={"error": str(exc)},
            )

        # Check evaluations for violations (robustness < 0)
        # res is a list of [time, robustness_score] pairs
        violation_indices = [int(t) for t, rob in res if rob < 0]

        if violation_indices:
            offending_segment = [records[t] for t in violation_indices]
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.VIOLATED,
                strength=Strength.OBSERVED,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Violated over {len(records)} decision(s): temporal property {req.spec!r} "
                    f"failed at decision step(s) {violation_indices}."
                ),
                details={
                    "offending_trace_segment": offending_segment,
                    "violation_step_indices": violation_indices,
                    "evaluation_scores": res,
                },
            )

        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.SATISFIED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Observed over {len(records)} decision(s): temporal monitor for {req.spec!r} "
                "satisfied across all time steps."
            ),
            details={"records_observed": len(records), "evaluation_scores": res},
        )
