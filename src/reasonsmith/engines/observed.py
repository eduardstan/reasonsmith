"""Observed engine for reasonsmith v0.2.

Evaluates temporal properties over decision traces using rtamt STL/MTL monitors.
Requirements with formalism = "temporal" become discrete-time monitors.

Behavior:
- Trace records are converted to discrete time series dataset for rtamt.
- A violation returns the offending trace segment in details and summary.
- If rtamt cannot express a formula, the requirement is reported as NOT EVALUATED
  with the reason (verdict=INCONCLUSIVE, strength=None) — never as satisfied.
- Whether a signal is a magnitude or a flag is read from the requirement's own formula, never
  from what the trace happened to contain. A variable compared against the presence threshold
  (`>= 0.5`) is a flag and keeps the 1.0/0.0 encoding, so an absent one still fails the check
  that asks for it. A variable compared against any other constant is a magnitude: every record
  must carry a real number for it, and a record that carries none — absent, blank, a bool, the
  string "45", or a non-finite float — is reported as NOT EVALUATED rather than scored.
  Coercing those to 0.0 or 1.0 would let a 45-day notice, or a notice nobody ever sent, pass a
  `<= 30` deadline; NaN would too, since every robustness comparison against it is False.
  `json.loads` reads bare `NaN`/`Infinity` by default, so a producer that serialises a missing
  measurement that way reaches here as a float, and a flag valued NaN counts as absent.
"""

from __future__ import annotations

import math
import re
from typing import Any

import rtamt

from reasonsmith.report import RequirementResult, _is_present
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict


#: The threshold a pack uses to ask whether a signal is present at all. Everything else a
#: variable is compared against is a quantity, and a quantity has to be measured.
PRESENCE_THRESHOLD = 0.5

_NUMBER = r"-?\d+(?:\.\d+)?"
_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
_COMPARISONS = (
    re.compile(rf"({_IDENT})\s*(?:<=|>=|<|>|==|!=)\s*({_NUMBER})"),
    re.compile(rf"({_NUMBER})\s*(?:<=|>=|<|>|==|!=)\s*({_IDENT})"),
)


def _is_real_number(value: Any) -> bool:
    """True for a value that can stand for a measured quantity.

    A bool is a flag wearing a number's clothes, and NaN or ±Infinity is the absence of a
    measurement written as a float — neither is a quantity a bound can be checked against.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


_ALWAYS = re.compile(r"^\s*always\s*\((.*)\)\s*$", re.DOTALL)


def _always_body(spec: str) -> str | None:
    """The body of a spec that is a single unbounded `always(...)`, else None.

    The robustness of `always` at step t is the minimum over the whole suffix, so every step
    before a breach inherits the breach's negative score. Naming the steps that actually breach
    the duty means monitoring the body on its own.
    """
    match = _ALWAYS.match(spec)
    if match is None:
        return None
    body = match.group(1)
    depth = 0
    for char in body:
        depth += (char == "(") - (char == ")")
        if depth < 0:
            return None  # the paren we stripped closed something else, e.g. always(a) and b
    return body if depth == 0 else None


def _monitor(spec_text: str, name: str, spec_vars: set[str], time_series: dict) -> list:
    """Robustness of `spec_text` at every time step of `time_series`."""
    spec = rtamt.StlDiscreteTimeSpecification()
    spec.name = name
    for var in spec_vars:
        spec.declare_var(var, "float")
    spec.spec = spec_text
    spec.parse()
    return spec.evaluate(time_series)


def _magnitude_vars(spec: str) -> set[str]:
    """The spec variables compared against something other than the presence threshold."""
    magnitude: set[str] = set()
    for pattern, var_first in zip(_COMPARISONS, (True, False)):
        for left, right in pattern.findall(spec):
            var, constant = (left, right) if var_first else (right, left)
            if float(constant) != PRESENCE_THRESHOLD:
                magnitude.add(var)
    return magnitude


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
        magnitude_vars = _magnitude_vars(req.spec)

        # Build dataset for rtamt
        time_series: dict[str, list[float]] = {"time": list(range(len(records)))}
        unmeasured: dict[str, int] = {}
        for var in spec_vars:
            values: list[float] = []
            not_measured = 0
            for rec in records:
                val = rec.get(var)
                if var in magnitude_vars:
                    if _is_real_number(val):
                        values.append(float(val))
                    else:
                        not_measured += 1
                        values.append(0.0)
                elif isinstance(val, bool):
                    values.append(1.0 if val else 0.0)
                elif isinstance(val, (int, float)):
                    values.append(float(val) if math.isfinite(val) else 0.0)
                elif _is_present(val):
                    # Categorical: carries something, so it counts as present
                    values.append(1.0)
                else:
                    values.append(0.0)
            if not_measured:
                unmeasured[var] = not_measured
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
                    f"Not evaluated: {req.spec!r} compares a magnitude the trace does not "
                    f"measure — no numeric value for {gaps}. An absent, blank or non-numeric "
                    "value is not a measurement, so the monitor was not run over this trace."
                ),
                details={"signals_unmeasured_in_trace": dict(sorted(unmeasured.items()))},
            )

        # Construct rtamt STL specification
        try:
            spec_name = f"spec_{req.id.replace('-', '_')}"
            res = _monitor(req.spec, spec_name, spec_vars, time_series)
            always_body = _always_body(req.spec)
            violation_res = (
                _monitor(always_body, f"{spec_name}_body", spec_vars, time_series)
                if always_body is not None
                else res
            )
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
        # For a top-level `always`, use its body's robustness to identify the records that
        # actually breach the duty; the outer formula's suffix minimum also makes earlier,
        # compliant records negative.
        violation_indices = [int(t) for t, rob in violation_res if rob < 0]

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
