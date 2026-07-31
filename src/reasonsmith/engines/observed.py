"""Observed engine for reasonsmith v0.2.

Evaluates temporal properties over decision traces using rtamt STL/MTL monitors.
Requirements with formalism = "temporal" become discrete-time monitors.

Behavior:
- Trace records are converted to discrete time series dataset for rtamt.
- A violation returns the offending trace segment in details and summary.
- If rtamt cannot express a formula, the requirement is reported as NOT EVALUATED
  with the reason (verdict=INCONCLUSIVE, strength=None) — never as satisfied.
- A signal the trace measures numerically is a magnitude, not a flag: a record that carries
  no value for it has no measurement, and encoding that absence as the numeral 0.0 would let
  a decision nobody was notified about pass a `<= 30` deadline. Such a gap is reported as NOT
  EVALUATED. A signal only ever checked for presence keeps the 1.0/0.0 encoding, so an absent
  one still fails the check that asks for it.
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
        formula_vars = found_vars - keywords
        spec_vars = formula_vars | var_names

        # Build dataset for rtamt
        time_series: dict[str, list[float]] = {"time": list(range(len(records)))}
        unmeasured: dict[str, int] = {}
        for var in spec_vars:
            values: list[float] = []
            measured_numerically = False
            absent = 0
            for rec in records:
                val = rec.get(var)
                if isinstance(val, bool):
                    values.append(1.0 if val else 0.0)
                elif isinstance(val, (int, float)):
                    measured_numerically = True
                    values.append(float(val))
                elif _is_present(val):
                    # Categorical: carries something, so it counts as present
                    values.append(1.0)
                else:
                    absent += 1
                    values.append(0.0)
            if measured_numerically and absent and var in formula_vars:
                unmeasured[var] = absent
            time_series[var] = values

        if unmeasured:
            gaps = ", ".join(
                f"{var} in {count} of {len(records)} decision(s)"
                for var, count in sorted(unmeasured.items())
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    "Not evaluated: the trace carries no measurement for "
                    f"{gaps}, and an absent measurement is not a measurement of zero. "
                    f"The monitor for {req.spec!r} was not run over this trace."
                ),
                details={"signals_unmeasured_in_trace": dict(sorted(unmeasured.items()))},
            )

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
