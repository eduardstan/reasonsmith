"""Observed engine for reasonsmith v0.2.

What this module is for:
  Evaluates temporal properties (`formalism = "temporal"`) over decision traces using an rtamt
  discrete-time STL monitor. The property is written in the shared language of `rulelang.py`;
  `to_stl` renders it in rtamt's syntax. Each `present(x)` atom reaches rtamt through a synthetic
  flag whose trace is computed with `rulelang.is_present`, so presence has the same meaning here
  as it does in the record, replay and proof engines.

What a reader must not break:
  - If rtamt cannot express a formula or trace is shorter than `MINIMUM_TRACE_LENGTH`, report
    `NOT EVALUATED` (`verdict=INCONCLUSIVE`, `strength=None`), NEVER `satisfied`.
    Why this matters: STL monitors require sufficient trace points to establish time bounds; an
    unsupported formula or insufficient trace length cannot prove a temporal property.
  - Flag and magnitude roles must be read from the formula itself, never from what the trace
    happened to contain. Asking `var >= 0.5` (or `0.5 <= var`) is the one way a pack asks for a
    flag rather than a measured magnitude. A bare Boolean atom is a third role: the formula places
    it in a Boolean position, and every record must establish that role with `True` or `False`.
    False becomes -1.0 so its robustness is a breach. For an explicit flag, Booleans remain
    1.0/0.0, other present non-numeric values become 1.0, absent or non-finite values become 0.0,
    and finite numbers remain numeric. Every other comparison — against any other constant,
    against 0.5 under any other operator, or against another variable — is a magnitude on both
    sides: every record must carry a real number for it, and a record that carries none — absent,
    blank, a bool, the string "45", or a non-finite float — is reported as NOT EVALUATED rather
    than scored.
    Why this matters: Coercing those to 0.0 or 1.0 would let a 45-day notice, or a notice nobody
    ever sent, pass a `<= 30` deadline; NaN would too, since every robustness comparison against it
    is False. `json.loads` reads bare `NaN`/`Infinity` by default, so a producer that serialises a
    missing measurement that way reaches here as a float, and a flag valued NaN counts as absent.
"""

from __future__ import annotations

import math
import re
import sys
import types
import typing
from typing import Any

# antlr4-python3-runtime 4.7 (hard-pinned by rtamt) runs `from typing.io import TextIO`, and
# typing.io was removed in Python 3.13. That statement is resolved through sys.modules, not
# through an attribute on typing, so the shim has to be a registered module.
if "typing.io" not in sys.modules and not hasattr(typing, "io"):
    _typing_io = types.ModuleType("typing.io")
    _typing_io.IO = typing.IO  # type: ignore[attr-defined]
    _typing_io.TextIO = typing.TextIO  # type: ignore[attr-defined]
    _typing_io.BinaryIO = typing.BinaryIO  # type: ignore[attr-defined]
    sys.modules["typing.io"] = _typing_io

import rtamt

from reasonsmith.report import RequirementResult
from reasonsmith.rulelang import (
    FLAG_THRESHOLD,
    PRESENCE_CALL,
    UnsupportedConstructError,
    bare_boolean_names,
    is_present,
    parse_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

#: The threshold a pack uses to read a signal as a flag. Everything else a variable is compared
#: against is a quantity, and a quantity has to be measured.
PRESENCE_THRESHOLD = FLAG_THRESHOLD

#: rtamt's offline discrete-time evaluator reads the sampling period off the trace, so a
#: one-sample dataset raises out of its own internals. That is a limit of what was observed,
#: not a defect in the formula, and it is reported as one rather than blamed on the pack.
MINIMUM_TRACE_LENGTH = 2

_NUMBER = r"-?\d+(?:\.\d+)?"
_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
_OPERAND = rf"(?:{_NUMBER}|{_IDENT})"
_COMPARISON = re.compile(rf"({_OPERAND})\s*(<=|>=|<|>|==|!=)\s*({_OPERAND})")

_PRESENCE_CALL = re.compile(rf"\b{PRESENCE_CALL}\s*\(\s*({_IDENT})\s*\)")
_SYNTHETIC_PRESENCE_PREFIX = "__reasonsmith_present_"


def _render_stl(
    spec: str, reserved_names: set[str] | None = None
) -> tuple[str, dict[str, str]]:
    """Render a property for rtamt and map each synthetic presence flag to its signal."""
    used = set(re.findall(rf"\b{_IDENT}\b", spec)) | set(reserved_names or ())
    presence_signals: dict[str, str] = {}
    next_index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal next_index
        while f"{_SYNTHETIC_PRESENCE_PREFIX}{next_index}" in used:
            next_index += 1
        synthetic = f"{_SYNTHETIC_PRESENCE_PREFIX}{next_index}"
        next_index += 1
        used.add(synthetic)
        presence_signals[synthetic] = match.group(1)
        return f"({synthetic} >= {PRESENCE_THRESHOLD})"

    return _PRESENCE_CALL.sub(replace, spec), presence_signals


def to_stl(spec: str) -> str:
    """Return a requirement property in rtamt syntax.

    The synthetic flag named in the returned text is populated by `ObservedEngine`; callers that
    only need the rendered formula can use this public view without depending on that mapping.
    """
    return _render_stl(spec)[0]


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


def _number(token: str) -> float | None:
    """The token read as a numeric literal, or None when it is a variable name."""
    try:
        return float(token)
    except ValueError:
        return None


def _magnitude_vars(spec: str) -> set[str]:
    """The spec variables the formula treats as measured quantities.

    Every variable in a comparison is a quantity unless that comparison is the flag test
    `var >= 0.5`. Bounding a variable at 0.5 under any other operator, or against another
    variable, is a bound on a quantity — `drift <= 0.5` and `latency <= deadline` both have to
    be measured, and reading them as flags would score an unmeasured record 0.0 and let it pass
    the bound it never met.
    """
    magnitude: set[str] = set()
    for left, operator, right in _COMPARISON.findall(spec):
        for token, other, on_left in ((left, right, True), (right, left, False)):
            if _number(token) is not None:
                continue
            bound = _number(other)
            is_flag = bound == PRESENCE_THRESHOLD and operator == (">=" if on_left else "<=")
            if not is_flag:
                magnitude.add(token)
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

        if len(records) < MINIMUM_TRACE_LENGTH:
            reason = (
                "the decision trace is empty, so nothing was observed"
                if not records
                else (
                    f"the decision trace holds {len(records)} decision(s), and a discrete-time "
                    f"monitor needs at least {MINIMUM_TRACE_LENGTH} samples to establish the "
                    "sampling period it reasons over"
                )
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=f"Not evaluated: {reason}.",
                details={"records_observed": len(records)},
                binding=req.binding,
                scope=req.scope,
            )

        try:
            property_node = parse_property(req.spec)
            boolean_atoms = set(bare_boolean_names(property_node))
        except UnsupportedConstructError as exc:
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
                binding=req.binding,
                scope=req.scope,
            )

        stl_text, presence_signals = _render_stl(req.spec, set(req.requires))

        # Extract variable names from formula or req.requires
        var_names = set(req.requires)
        # Also extract identifiers from spec formula
        found_vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", stl_text))
        keywords = {
            "always", "eventually", "until", "then", "implies", "and", "or", "not",
            "true", "false", "historically", "once", "since", "rise", "fall", "prev"
        }
        formula_vars = found_vars - keywords
        spec_vars = formula_vars | var_names
        magnitude_vars = _magnitude_vars(stl_text)
        magnitude_vars.difference_update(presence_signals)

        # Build dataset for rtamt
        time_series: dict[str, list[float]] = {"time": list(range(len(records)))}
        unmeasured: dict[str, int] = {}
        non_boolean_atoms: dict[str, int] = {}
        for var in spec_vars:
            if var in presence_signals:
                source = presence_signals[var]
                time_series[var] = [
                    1.0 if is_present(rec.get(source)) else 0.0 for rec in records
                ]
                continue
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
                elif var in boolean_atoms:
                    if isinstance(val, bool):
                        values.append(1.0 if val else -1.0)
                    else:
                        not_measured += 1
                        values.append(0.0)
                elif isinstance(val, bool):
                    values.append(1.0 if val else 0.0)
                elif isinstance(val, (int, float)):
                    values.append(float(val) if math.isfinite(val) else 0.0)
                elif is_present(val):
                    # Categorical: carries something, so it counts as present
                    values.append(1.0)
                else:
                    values.append(0.0)
            if not_measured:
                if var in boolean_atoms and var not in magnitude_vars:
                    non_boolean_atoms[var] = not_measured
                else:
                    unmeasured[var] = not_measured
            time_series[var] = values

        if non_boolean_atoms:
            gaps = ", ".join(
                f"{var} in {count} of {len(records)} decision(s)"
                for var, count in sorted(non_boolean_atoms.items())
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: {req.spec!r} uses a bare Boolean atom whose kind the trace "
                    f"does not establish — no Boolean value for {gaps}. Every record must carry "
                    "True or False for a bare Boolean atom before the monitor can score it."
                ),
                details={
                    "signals_without_boolean_trace_kind": dict(
                        sorted(non_boolean_atoms.items())
                    )
                },
                binding=req.binding,
                scope=req.scope,
            )

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
                binding=req.binding,
                scope=req.scope,
            )

        # Construct rtamt STL specification
        try:
            spec_name = f"spec_{req.id.replace('-', '_')}"
            res = _monitor(stl_text, spec_name, spec_vars, time_series)
            always_body = _always_body(stl_text)
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
                binding=req.binding,
                scope=req.scope,
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
                f"Observed over {len(records)} decision(s): temporal monitor for {req.spec!r} "
                "satisfied across all time steps."
            ),
            details={"records_observed": len(records), "evaluation_scores": res},
            binding=req.binding,
            scope=req.scope,
        )
