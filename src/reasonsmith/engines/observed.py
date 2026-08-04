"""Observed engine for reasonsmith v0.2.

What this module is for:
  Evaluates properties over decision traces using an rtamt discrete-time STL monitor: `temporal`
  formulas quantified over the trace, and `logical` state properties, which the monitor scores
  pointwise so that each record is checked on its own (`report._engine_ladder`, and
  `docs/semantics.md` §3.5 for why a state fragment admits a trace rung at all). A presence
  conjunction does *not* come here — it keeps the record engine, whose per-signal, per-record
  diagnostics this monitor cannot reproduce.

  The property is written in the shared language of `rulelang.py`; `to_stl` renders it in rtamt's
  syntax. Both atoms that read a *record* rather than a magnitude reach rtamt through a synthetic
  flag computed in Python — `present(x)` through `rulelang.is_present` and `contains(x, "p")`
  through `rulelang.contains_literal` — so each has the same meaning here as in the record, replay
  and proof engines rather than a second definition living inside an STL string.

What a reader must not break:
  - If rtamt cannot express a formula or trace is shorter than `MINIMUM_TRACE_LENGTH`, report
    `NOT EVALUATED` (`verdict=INCONCLUSIVE`, `strength=None`), NEVER `satisfied`.
    Why this matters: STL monitors require sufficient trace points to establish time bounds; an
    unsupported formula or insufficient trace length cannot prove a temporal property.
  - Where the property is an implication whose antecedent scored below zero at every position,
    report `NOT EVALUATED`, never `satisfied`.
    Why this matters: an implication holds at every step its trigger does not fire, so such a
    trace scores non-negative for every system alike and the monitor learned nothing about this
    one. This engine used to report it `satisfied` and the solver used to report the same formula
    `proved` — two rungs agreeing about the formula and disagreeing about the evidence. The rule
    is written once: `rulelang.implication_antecedent` names the subtree,
    `report.not_evaluated_for_unreachable_trigger` words the refusal, and every rung asks it of
    the domain it quantifies over.
  - The time domain the monitor counts on is a parameter of `evaluate`, defaulting to
    `sut.ORDINAL_DOMAIN`, and `TimeDomain.ticks` is the only source of the `time` series. A duty
    asked for on any other domain is reported `NOT EVALUATED`, never `satisfied`.
    Why this matters: the record index is what this engine has always counted, and a deadline duty
    that means days is currently answered by a latency number the system computes about itself. A
    trace that gained event timestamps must neither lose the verdict it had nor silently have its
    record indices relabelled as seconds; both are refused by making the domain something a caller
    states rather than something this function assumes.
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

import ast
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

from reasonsmith.report import RequirementResult, not_evaluated_for_unreachable_trigger
from reasonsmith.rulelang import (
    CONTAINS_CALL,
    FLAG_THRESHOLD,
    PRESENCE_CALL,
    UnsupportedConstructError,
    bare_boolean_names,
    contains_literal,
    implication_antecedent,
    is_present,
    parse_property,
    string_literal_mask,
    validate_temporal_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import (
    ORDINAL_DOMAIN,
    SystemUnderTest,
    TimeDomain,
    read_time_domain,
)
from reasonsmith.verdict import Strength, Verdict

#: The threshold a pack uses to read a signal as a flag. Everything else a variable is compared
#: against is a quantity, and a quantity has to be measured.
PRESENCE_THRESHOLD = FLAG_THRESHOLD

#: rtamt's offline discrete-time evaluator reads the sampling period off the trace, so a
#: one-sample dataset raises out of its own internals. That is a limit of what was observed,
#: not a defect in the formula, and it is reported as one rather than blamed on the pack.
MINIMUM_TRACE_LENGTH = 2


def _property_noun(req: Requirement, noun: str = "property") -> str:
    """What to call the property in a summary, so the wording matches the duty it answered.

    This engine reads two fragments now: a `temporal` formula quantified over the trace, and a
    `logical` state property scored per record (`report._engine_ladder`). Calling both a "temporal
    monitor" would tell a reader that a duty about one decision was checked across the trace, which
    is the sort of small mis-description that becomes a misread verdict on a front page.

    Summaries differ only in the noun they hang the adjective on, so the noun is the argument and
    the fragment-to-adjective decision is made once. A second copy of that decision is how a new
    fragment, or a rename, reintroduces exactly the mis-description this exists to prevent.
    """
    return f"{'temporal' if req.formalism == 'temporal' else 'state'} {noun}"


_NUMBER = r"-?\d+(?:\.\d+)?"
_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
_OPERAND = rf"(?:{_NUMBER}|{_IDENT})"
_COMPARISON = re.compile(rf"({_OPERAND})\s*(<=|>=|<|>|==|!=)\s*({_OPERAND})")

_STRING_LITERAL = r"(?:\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')"
_ATOM_CALL = re.compile(
    rf"\b(?:{PRESENCE_CALL}\s*\(\s*(?P<present>{_IDENT})\s*\)"
    rf"|{CONTAINS_CALL}\s*\(\s*(?P<signal>{_IDENT})\s*,\s*(?P<phrase>{_STRING_LITERAL})\s*\))"
)
_SYNTHETIC_PRESENCE_PREFIX = "__reasonsmith_present_"
_SYNTHETIC_CONTAINS_PREFIX = "__reasonsmith_contains_"


def _render_stl(
    spec: str, reserved_names: set[str] | None = None
) -> tuple[str, dict[str, str], dict[str, tuple[str, str]]]:
    """Render a property for rtamt, mapping each synthetic flag back to what computes it.

    rtamt reasons over real-valued signals and nothing else, so neither atom that reads a *record*
    rather than a magnitude can be handed to it directly. Both are therefore evaluated in Python,
    per record, and reach the monitor as a synthetic flag: `present(x)` through `is_present`, and
    `contains(x, "p")` through `contains_literal`. That is what keeps their meaning the one meaning
    every other engine uses, instead of a second definition living inside an STL string.

    Rewriting is textual, so a call head that a `contains()` phrase merely quotes is skipped:
    `contains(reason, "present(x)")` forbids a phrase, it does not ask a presence question.
    """
    used = set(re.findall(rf"\b{_IDENT}\b", spec)) | set(reserved_names or ())
    presence_signals: dict[str, str] = {}
    contains_signals: dict[str, tuple[str, str]] = {}
    in_string = string_literal_mask(spec)
    counter = 0

    def fresh(prefix: str) -> str:
        nonlocal counter
        while f"{prefix}{counter}" in used:
            counter += 1
        synthetic = f"{prefix}{counter}"
        counter += 1
        used.add(synthetic)
        return synthetic

    def replace(match: re.Match[str]) -> str:
        if in_string[match.start()]:
            return match.group(0)
        if match.group("present") is not None:
            synthetic = fresh(_SYNTHETIC_PRESENCE_PREFIX)
            presence_signals[synthetic] = match.group("present")
        else:
            synthetic = fresh(_SYNTHETIC_CONTAINS_PREFIX)
            contains_signals[synthetic] = (
                match.group("signal"),
                ast.literal_eval(match.group("phrase")),
            )
        return f"({synthetic} >= {PRESENCE_THRESHOLD})"

    return _ATOM_CALL.sub(replace, spec), presence_signals, contains_signals


def to_stl(spec: str) -> str:
    """Return a requirement property in rtamt syntax.

    The synthetic flags named in the returned text are populated by `ObservedEngine`; callers that
    only need the rendered formula can use this public view without depending on those mappings.
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
        time_domain: TimeDomain | None = None,
    ) -> RequirementResult:
        clause = f"{req.source_document} {req.article_clause}"

        # The domain the duty is to be counted on is a stated input, not a convention of this
        # function. It defaults to `ORDINAL_DOMAIN` — the record index, which is what every
        # shipped duty is asked for and what a caller passing nothing keeps getting — so a trace
        # that gained event timestamps does not thereby lose a verdict it used to have.
        required = ORDINAL_DOMAIN if time_domain is None else time_domain
        if not required.is_ordinal:
            stated = read_time_domain(records)
            missing = (
                "this trace records no event times at all, so there is no clock to count on"
                if stated.is_ordinal
                else (
                    "this trace records event times, but the monitor's only time axis is the "
                    "record index: no metric or interval semantics reads them yet"
                )
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: {req.spec!r} was asked for on the {required.kind!r} time "
                    f"domain, and {missing}. A duty needing a real clock is never reported "
                    "satisfied off a trace whose time is the record index."
                ),
                details={
                    "time_domain_required": required.kind,
                    "time_domain_stated_by_trace": stated.kind,
                    "records_observed": len(records),
                },
                binding=req.binding,
                scope=req.scope,
            )

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
            validate_temporal_property(property_node)
            boolean_atoms = set(bare_boolean_names(property_node))
        except UnsupportedConstructError as exc:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    "Not evaluated: rtamt cannot express or parse "
                    f"{_property_noun(req)} {req.spec!r}: {exc}"
                ),
                details={"error": str(exc)},
                binding=req.binding,
                scope=req.scope,
            )

        stl_text, presence_signals, contains_signals = _render_stl(
            req.spec, set(req.requires)
        )

        # The property's antecedent, rendered for the same monitor. It is a sub-formula of the
        # spec, so it introduces no signal the trace was not already read for; what it needs is
        # synthetic flags of its own, which is why the names already taken are reserved. Rendered
        # here rather than after the monitor runs, so its flags are populated by the one pass that
        # builds the time series. See the module docstring for what it is for.
        antecedent_node = implication_antecedent(property_node)
        antecedent_stl: str | None = None
        if antecedent_node is not None:
            antecedent_stl, extra_presence, extra_contains = _render_stl(
                ast.unparse(antecedent_node),
                set(req.requires) | set(presence_signals) | set(contains_signals),
            )
            presence_signals.update(extra_presence)
            contains_signals.update(extra_contains)

        # Extract variable names from formula or req.requires
        var_names = set(req.requires)
        # Also extract identifiers from spec formula
        monitored_text = stl_text if antecedent_stl is None else f"{stl_text} {antecedent_stl}"
        found_vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", monitored_text))
        keywords = {
            "always", "eventually", "until", "then", "implies", "and", "or", "not",
            "true", "false", "historically", "once", "since", "rise", "fall", "prev"
        }
        formula_vars = found_vars - keywords
        spec_vars = formula_vars | var_names
        magnitude_vars = _magnitude_vars(monitored_text)
        magnitude_vars.difference_update(presence_signals)
        magnitude_vars.difference_update(contains_signals)

        # Build dataset for rtamt. The time axis comes from the stated domain and nowhere else,
        # so a later metric semantics is a new `TimeDomain.kind` rather than an edit here.
        time_series: dict[str, list[float]] = {"time": required.ticks(len(records))}
        unmeasured: dict[str, int] = {}
        non_boolean_atoms: dict[str, int] = {}
        non_text_atoms: dict[str, int] = {}
        for var in spec_vars:
            if var in presence_signals:
                source = presence_signals[var]
                time_series[var] = [
                    1.0 if is_present(rec.get(source)) else 0.0 for rec in records
                ]
                continue
            if var in contains_signals:
                # A record that carries no value for the signal contains no phrase, which is what
                # lets an implication guarded by `present()` decide the duty. A record that carries
                # something that is not text is a kind the trace never established, exactly as an
                # unmeasured magnitude is, and it is counted rather than scored.
                source, phrase = contains_signals[var]
                found: list[float] = []
                not_text = 0
                for rec in records:
                    try:
                        found.append(1.0 if contains_literal(rec.get(source), phrase) else 0.0)
                    except UnsupportedConstructError:
                        not_text += 1
                        found.append(0.0)
                if not_text:
                    non_text_atoms[source] = max(non_text_atoms.get(source, 0), not_text)
                time_series[var] = found
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

        if non_text_atoms:
            gaps = ", ".join(
                f"{var} in {count} of {len(records)} decision(s)"
                for var, count in sorted(non_text_atoms.items())
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: {req.spec!r} asks what a statement says, but the trace "
                    f"records something that is not text — no textual value for {gaps}. A "
                    "non-text value is not evidence about the wording of a statement, so the "
                    "monitor was not run over this trace."
                ),
                details={"signals_without_text_in_trace": dict(sorted(non_text_atoms.items()))},
                binding=req.binding,
                scope=req.scope,
            )

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
        spec_name = f"spec_{req.id.replace('-', '_')}"
        try:
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
                    "Not evaluated: rtamt cannot express or parse "
                    f"{_property_noun(req)} {req.spec!r}: {exc}"
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
                    f"Violated over {len(records)} decision(s): "
                    f"{_property_noun(req)} {req.spec!r} "
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

        # No step breached the duty — but a duty triggered nowhere is not breached by any trace,
        # and the monitor scoring every step non-negative is then a fact about the antecedent.
        # The antecedent is read at the same threshold satisfaction is: robustness below zero is
        # the trigger not firing, exactly as it is the formula not holding.
        #
        # Monitored here, after the violation check and in a try of its own, so that an
        # antecedent rtamt cannot parse can only ever withhold a satisfied verdict. Sharing the
        # try above would let a sub-formula the monitor chokes on suppress a breach the monitor
        # had already scored.
        if antecedent_stl is not None:
            try:
                antecedent_res = _monitor(
                    antecedent_stl, f"{spec_name}_antecedent", spec_vars, time_series
                )
            except Exception as exc:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: no decision breached {req.spec!r}, but rtamt cannot "
                        f"express or parse its antecedent {ast.unparse(antecedent_node)!r}: "
                        f"{exc}. A duty whose trigger cannot be read is reported as no evidence "
                        "rather than as a clean verdict."
                    ),
                    details={"error": str(exc), "records_observed": len(records)},
                    binding=req.binding,
                    scope=req.scope,
                )
            if all(rob < 0 for _t, rob in antecedent_res):
                return not_evaluated_for_unreachable_trigger(
                    req,
                    ast.unparse(antecedent_node),
                    f"the {len(records)} decision(s) of this trace",
                    {"records_observed": len(records), "antecedent_scores": antecedent_res},
                )

        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.SATISFIED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Observed over {len(records)} decision(s): "
                f"{_property_noun(req, 'monitor')} for "
                f"{req.spec!r} satisfied at every decision step."
            ),
            details={"records_observed": len(records), "evaluation_scores": res},
            binding=req.binding,
            scope=req.scope,
        )
