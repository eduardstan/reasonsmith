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
  - Every backend adapter certifies that it consumed the whole rendered formula and produced
    exactly one property, or the requirement is reported `not evaluated`. For rtamt, `_monitor`
    installs a strict lexer (F1) to raise on bad tokens and asserts `len(spec.ast.specs) == 1` (F2)
    after parsing.
  - If rtamt cannot express a formula or trace is shorter than `MINIMUM_TRACE_LENGTH`, report
    `NOT EVALUATED` (`verdict=INCONCLUSIVE`, `strength=None`), NEVER `satisfied`.
    Why this matters: STL monitors require sufficient trace points to establish time bounds; an
    unsupported formula or insufficient trace length cannot prove a temporal property.
  - A shape rtamt parses and reads under a different semantics from the one
    `docs/theory/03-semantics.md`; it is refused in the rendering
    (`_refuse_shapes_the_monitor_misreads`), so the duty is
    reported `NOT EVALUATED` naming the construct, never answered.
    Why this matters: rtamt raises for nearly everything it does not support — `!=`, `min`, `max`,
    `Implies(...)`, `<=>` — so `spec.parse()` raising was this engine's whole protection, and three
    shapes fall outside it. A `%` is the sharp one: ANTLR error-recovers by dropping the token and
    `parse()` does not raise, so the monitor answers about a formula nobody wrote.
    `test_rtamt_still_behaves_the_way_the_refusals_assume` fails if a version bump moves any
    admitted construct between raising, agreeing and misreading.
  - Where the property's antecedent evaluated false or unknown at every position,
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
from collections.abc import Mapping
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

from reasonsmith.event_time import (
    CALENDAR_POLICY,
    TIMEZONE_POLICY,
    EventTimeError,
    measure_pair,
    parse_duration,
)
from reasonsmith.report import RequirementResult, not_evaluated_for_unreachable_trigger
from reasonsmith.rulelang import (
    BINARY_TEMPORAL_OPERATORS,
    CONTAINS_CALL,
    EQUIVALENCE_CALL,
    FLAG_THRESHOLD,
    PRESENCE_CALL,
    UnsupportedConstructError,
    bare_boolean_names,
    bounded_response_arguments,
    bounded_response_calls,
    contains_literal,
    eval_temporal_trace,
    has_bounded_response,
    has_temporal_operator,
    implication_antecedent,
    is_present,
    is_unknown,
    kleene_and,
    kleene_value,
    parse_property,
    string_literal_mask,
    validate_temporal_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import (
    EVENT_DOMAIN,
    EVENT_TIME,
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


def _has_prefix_temporal_shape(node: ast.AST) -> bool:
    """Whether a formula contains a genuine finite-trace obligation (`until` or `since`)."""
    return any(
        isinstance(current, ast.Call)
        and isinstance(current.func, ast.Name)
        and current.func.id in BINARY_TEMPORAL_OPERATORS
        for current in ast.walk(node)
    )


def _prefix_witness(property_node: ast.AST, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the shortest trace prefix whose reference semantics reproduces the violation."""
    if not _has_prefix_temporal_shape(property_node):
        return None
    for end in range(1, len(records) + 1):
        prefix = records[:end]
        values = eval_temporal_trace(property_node, prefix)
        if not values or kleene_value(values[0]) is not False:
            continue
        positions = [index for index, value in enumerate(values) if kleene_value(value) is False]
        return {
            "trace": [dict(record) for record in prefix],
            "positions": positions,
            "position": end - 1,
        }
    return None


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

    rendered = _render_binary_temporal(_ATOM_CALL.sub(replace, spec))
    return rendered, presence_signals, contains_signals


_BINARY_TEMPORAL = re.compile(rf"\b({'|'.join(sorted(BINARY_TEMPORAL_OPERATORS))})\s*\(")


def _render_binary_temporal(text: str) -> str:
    """Rewrite `until(a, b)` and `since(a, b)` into the infix form rtamt parses.

    The property language writes them as prefix calls because it parses through Python's `ast`;
    rtamt has had both as infix operators all along. This is the whole of the mapping between the
    two spellings — no temporal semantics is implemented here or anywhere else in this package.

    Rewriting is textual for the reason the atom rewriting above is: `req.spec` reaches rtamt as
    written, arrows included, so an AST round-trip would spell `->` as `Implies(...)`, which rtamt
    does not read. A call head a `contains()` phrase merely quotes is skipped for the same reason.
    """
    mask = string_literal_mask(text)
    for match in _BINARY_TEMPORAL.finditer(text):
        if mask[match.start()]:
            continue
        depth = 0
        comma = close = -1
        for i in range(match.end() - 1, len(text)):
            if mask[i]:
                continue
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    close = i
                    break
            elif text[i] == "," and depth == 1 and comma < 0:
                comma = i
        if close < 0 or comma < 0:
            raise UnsupportedConstructError(
                f"{match.group(1)}() takes two operands: {text!r}"
            )
        left = _render_binary_temporal(text[match.end() : comma])
        right = _render_binary_temporal(text[comma + 1 : close])
        tail = _render_binary_temporal(text[close + 1 :])
        return f"{text[: match.start()]}(({left}) {match.group(1)} ({right})){tail}"
    return text


#: The shapes the language admits and rtamt reads differently, each named as the refusal names it.
#: `docs/theory/03-semantics.md` Remark 3.3 quotes a witness and a robustness value for every one,
#: and says why the
#: definition is what moves nothing: three other encodings agree with it, so one backend disagreeing
#: is a defect in that backend. The refusal below is what keeps a duty using one of these *not
#: evaluated* rather than answered off a formula rtamt read differently.
_MISREAD_SHAPES = {
    "remainder": (
        "the remainder operator `%`: rtamt's lexer has no `%` and ANTLR error-recovers by "
        "dropping the token instead of raising, so the monitor would answer about a formula "
        "nobody wrote"
    ),
    "chain": (
        "a chained comparison: the language reads `a < b < c` as the conjunction of its pairs, "
        "and rtamt left-associates it over robustness, comparing a margin against `c`"
    ),
    "equivalence": (
        "an equivalence: rtamt's `iff` scores `-|p(left) - p(right)|`, which is negative "
        "whenever the two margins differ, including where both sides are false and the "
        "equivalence therefore holds"
    ),
}


class MisreadShapeError(UnsupportedConstructError):
    """A shape rtamt parses and reads differently from the way the property language defines it.

    Its own class because the refusal it earns is worded differently from every other one here: the
    others say rtamt cannot read the formula, and these three say rtamt reads it and reads it wrong.
    """


def _refuse_shapes_the_monitor_misreads(node: ast.AST) -> None:
    """Raise for a formula rtamt parses and reads differently from the way §2 defines it.

    rtamt *raises* for nearly every construct it does not support — `!=`, `min`, `max`,
    `Implies(...)`, `<=>` — which is why `spec.parse()` raising was this engine's whole protection
    against an unrenderable formula for as long as it was enough. These three are the shapes where
    that protection does not hold: two rtamt parses and reads under a different semantics, and one
    it silently drops. `test_rtamt_still_behaves_the_way_the_refusals_assume` is the standing probe
    that fails if a version bump moves any admitted construct between those cases.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Mod):
            raise MisreadShapeError(_MISREAD_SHAPES["remainder"])
        if isinstance(child, ast.Compare) and len(child.ops) > 1:
            raise MisreadShapeError(_MISREAD_SHAPES["chain"])
        # Both spellings of the connective reach here as `Iff`, so `<->` and `<=>` are refused
        # alike; before this they parted company, the first monitored and misread and the second
        # rejected by rtamt's grammar.
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == EQUIVALENCE_CALL
        ):
            raise MisreadShapeError(_MISREAD_SHAPES["equivalence"])


def to_stl(spec: str) -> str:
    """Return a requirement property in rtamt syntax, or refuse event-time metric semantics.

    The synthetic flags named in the returned text are populated by `ObservedEngine`; callers that
    only need the rendered formula can use this public view without depending on those mappings.
    ``within_after`` is deliberately not rendered: its timestamps are read by the event-time
    evaluator, never converted into an rtamt positional axis.
    """
    parsed = parse_property(spec)
    if has_bounded_response(parsed):
        raise UnsupportedConstructError(
            "within_after() requires the observed event-time metric evaluator and has no ordinal "
            "rtamt rendering"
        )
    _refuse_shapes_the_monitor_misreads(parsed)
    return _render_stl(spec)[0]


def _is_real_number(value: Any) -> bool:
    """True for a value that can stand for a measured quantity.

    A bool is a flag wearing a number's clothes, and NaN or ±Infinity is the absence of a
    measurement written as a float — neither is a quantity a bound can be checked against.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _monitor(spec_text: str, name: str, spec_vars: set[str], time_series: dict) -> list:
    """Robustness of `spec_text` at every time step of `time_series`."""
    spec = rtamt.StlDiscreteTimeSpecification()

    # Backend adapter contract: Every backend adapter certifies that it consumed the whole
    # rendered formula and produced exactly one property, or the requirement is reported
    # `not evaluated`.
    # F1 — supply a strict lexer: install rtamt's raising error listener on the lexer.
    BaseLexer = spec.ast.antrlLexerType
    ErrorListener = spec.ast.parserErrorListenerType

    class StrictLexer(BaseLexer):
        def __init__(self, input_stream):
            super().__init__(input_stream)
            self._listeners = [ErrorListener()]

    spec.ast.antrlLexerType = StrictLexer

    spec.name = name
    for var in spec_vars:
        spec.declare_var(var, "float")
    spec.spec = spec_text
    spec.parse()

    # F2 — assert the postcondition: backend parser produced exactly one statement.
    if len(spec.ast.specs) != 1:
        raise ValueError(
            f"Expected backend parser to produce exactly 1 statement, got {len(spec.ast.specs)}"
        )

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


def _case_label(key: tuple[str, object]) -> str:
    """The reader-facing name of a correlation key, which is not the key itself."""
    return str(key[1]) if key[0] == "case" else f"record-{key[1]}"


def _event_metric_result(
    req: Requirement,
    records: list[dict[str, Any]],
    property_node: ast.AST,
    stated: TimeDomain,
) -> RequirementResult:
    """Evaluate the one event-time metric operator without constructing an ordinal monitor."""
    clause = f"{req.source_document} {req.article_clause}"
    call = next(iter(bounded_response_calls(property_node)), None)
    if call is None:
        raise ValueError("event metric evaluation requires a within_after() call")
    anchor, endpoint, duration_text = bounded_response_arguments(call)
    duration = parse_duration(duration_text)
    common: dict[str, Any] = {
        "time_domain_required": EVENT_TIME,
        "time_domain_stated_by_trace": EVENT_TIME,
        "timezone_policy": TIMEZONE_POLICY,
        "calendar_policy": CALENDAR_POLICY,
        "anchor_event": anchor,
        "endpoint_event": endpoint,
        "bound": duration.text,
        "bound_kind": "calendar" if duration.is_calendar else "elapsed",
        "records_observed": len(records),
        "required_anchor_present": False,
        "required_endpoint_present": False,
        "all_required_anchors_present": False,
    }

    def inconclusive(reason: str, details: Mapping[str, Any] | None = None) -> RequirementResult:
        payload = dict(common)
        if details:
            payload.update(details)
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=f"Not evaluated: {reason}",
            details=payload,
            binding=req.binding,
            scope=req.scope,
        )

    # A trace record is one case unless it explicitly names a case shared by several event
    # records.  Records without an id are intentionally never merged, so they are keyed in a
    # keyspace disjoint from the author-supplied ids: equal event names in two records are not
    # evidence that they belong to one incident, and neither is a supplied id that happens to
    # spell the name this function would have given an anonymous record.
    #
    # The instants are the ones `read_time_domain` already parsed off this same trace.  Parsing
    # them a second time here would be a second contract that could drift from the one the caller
    # refused a malformed trace against.
    cases: dict[tuple[str, object], dict[str, list[tuple[int, Any, dict[str, Any]]]]] = {}
    missing_event_timestamps: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        raw_case = record.get("case_id")
        if raw_case is None:
            key: tuple[str, object] = ("record", index)
        elif not isinstance(raw_case, str) or not raw_case.strip():
            return inconclusive(
                f"record {index} has an empty or non-string case_id; event correlation is ambiguous"
            )
        else:
            key = ("case", raw_case.strip())
        bucket = cases.setdefault(key, {"anchor": [], "endpoint": []})
        stamps = stated.instants[index] if index < len(stated.instants) else None
        if stamps is None:
            unstamped = [name for name in (anchor, endpoint) if is_present(record.get(name))]
            if unstamped:
                missing_event_timestamps.append(
                    {"record_index": index, "events": unstamped}
                )
            continue
        for role, event_name in (("anchor", anchor), ("endpoint", endpoint)):
            if not is_present(record.get(event_name)):
                continue
            instant = stamps.get(event_name)
            if instant is None:
                missing_event_timestamps.append(
                    {"record_index": index, "events": [event_name]}
                )
            else:
                bucket[role].append((index, instant, record))

    common["required_anchor_present"] = any(bucket["anchor"] for bucket in cases.values())
    common["required_endpoint_present"] = any(bucket["endpoint"] for bucket in cases.values())
    common["all_required_anchors_present"] = not missing_event_timestamps and bool(
        common["required_anchor_present"]
    )
    common["missing_event_timestamps"] = missing_event_timestamps

    if missing_event_timestamps:
        return inconclusive(
            "a named event predicate was present without its timestamp; the pair cannot be checked",
            {"missing_event_timestamps": missing_event_timestamps},
        )

    anchors = [item for bucket in cases.values() for item in bucket["anchor"]]
    if not anchors:
        # This is the same no-evidence rule as an implication whose trigger never fires.  It is
        # deliberately not a satisfied vacuity, and the details retain the metric contract.
        if isinstance(property_node, ast.Expression):
            body = property_node.body
        else:
            body = property_node
        if (
            isinstance(body, ast.Call)
            and isinstance(body.func, ast.Name)
            and body.func.id == "always"
            and body.args
            and isinstance(body.args[0], ast.Call)
            and isinstance(body.args[0].func, ast.Name)
            and body.args[0].func.id in {"implies", "Implies"}
        ):
            return not_evaluated_for_unreachable_trigger(
                req,
                ast.unparse(body.args[0].args[0]),
                f"the {len(records)} timestamped decision record(s)",
                common,
            )
        return inconclusive(
            f"no record made the anchor predicate present({anchor}) true; no deadline was triggered"
        )

    # Any endpoint that has no anchor in its own correlated case is an uncorrelated event, not a
    # candidate pass.  A case with no endpoint is likewise incomplete.  Duplicate occurrences are
    # ambiguous even when their timestamps happen to be equal.
    pairs = []
    problems: list[str] = []
    for key, bucket in cases.items():
        case_id = _case_label(key)
        case_anchors = bucket["anchor"]
        case_endpoints = bucket["endpoint"]
        if not case_anchors and case_endpoints:
            problems.append(f"case {case_id!r} has an endpoint but no anchor")
            continue
        if not case_anchors:
            continue
        if len(case_anchors) != 1:
            problems.append(
                f"case {case_id!r} has {len(case_anchors)} anchor events; exactly one is required"
            )
            continue
        if len(case_endpoints) != 1:
            if not case_endpoints:
                problems.append(f"case {case_id!r} has an anchor but no endpoint")
            else:
                problems.append(
                    f"case {case_id!r} has {len(case_endpoints)} endpoint events; "
                    "correlation is ambiguous"
                )
            continue
        anchor_item = case_anchors[0]
        endpoint_item = case_endpoints[0]
        try:
            pairs.append(
                measure_pair(
                    case_id,
                    anchor_item[1],
                    endpoint_item[1],
                    duration,
                    anchor_record_index=anchor_item[0],
                    end_record_index=endpoint_item[0],
                )
            )
        except EventTimeError as exc:
            problems.append(f"case {case_id!r}: {exc}")

    if problems or not pairs:
        return inconclusive(
            "event correlation was incomplete or out of order — " + "; ".join(problems),
            {"correlation_problems": problems},
        )

    common["event_pairs"] = [pair.payload(duration) for pair in pairs]
    violations = [pair for pair in pairs if not pair.within_bound]
    if violations:
        witness = violations[0].payload(duration)
        indices = [violations[0].anchor_record_index, violations[0].end_record_index]
        offending = [records[index] for index in indices]
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.VIOLATED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Observed event-time violation: {anchor} to {endpoint} took "
                f"{witness['delta_seconds']} seconds in case {witness['case_id']!r}, "
                f"outside the inclusive {duration.text} bound."
            ),
            details={
                **common,
                "offending_trace_segment": offending,
                "violation_step_indices": indices,
                "violation_event_pair": witness,
                "witness": {
                    "kind": "event_pair",
                    "provenance": "witness-checked",
                    "checker": "reasonsmith.event_time.measure_pair",
                    "payload": witness,
                },
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
            f"Observed event-time bounded response for {len(pairs)} case(s): every "
            f"{endpoint} followed {anchor} within the inclusive {duration.text} bound."
        ),
        details=common,
        binding=req.binding,
        scope=req.scope,
    )


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

        # A bounded-response property selects the event clock by its construct.  Passing an
        # ordinal domain explicitly is still a refusal: the operator must never be downgraded to
        # record positions or to a latency field.
        metric_node: ast.AST | None = None
        try:
            candidate = parse_property(req.spec)
            if bounded_response_calls(candidate):
                metric_node = candidate
        except UnsupportedConstructError:
            # The ordinary parser/refusal path below owns malformed non-metric properties.
            pass
        if metric_node is not None:
            metric_call = next(iter(bounded_response_calls(metric_node)))
            metric_anchor, metric_endpoint, metric_bound_text = bounded_response_arguments(
                metric_call
            )
            metric_bound = parse_duration(metric_bound_text)
            metric_contract: dict[str, Any] = {
                "time_domain_required": EVENT_TIME,
                "timezone_policy": TIMEZONE_POLICY,
                "calendar_policy": CALENDAR_POLICY,
                "anchor_event": metric_anchor,
                "endpoint_event": metric_endpoint,
                "bound": metric_bound.text,
                "bound_kind": "calendar" if metric_bound.is_calendar else "elapsed",
                "required_anchor_present": False,
                "required_endpoint_present": False,
                "all_required_anchors_present": False,
            }
            required = EVENT_DOMAIN if time_domain is None else time_domain
            if required.is_ordinal:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: {req.spec!r} is an event-time bounded-response property, "
                        "but it was asked for on the ordinal record-index domain. The metric clock "
                        "is explicit and is never replaced by record positions."
                    ),
                    details={
                        **metric_contract,
                        "time_domain_requested": required.kind,
                        "records_observed": len(records),
                    },
                    binding=req.binding,
                    scope=req.scope,
                )
            try:
                stated = read_time_domain(records)
            except (TypeError, ValueError) as exc:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: {req.spec!r} requires a valid event-time clock, but the "
                        f"trace timestamp contract was refused: {exc}"
                    ),
                    details={
                        **metric_contract,
                        "time_domain_stated_by_trace": EVENT_TIME,
                        "records_observed": len(records),
                        "timestamp_error": str(exc),
                    },
                    binding=req.binding,
                    scope=req.scope,
                )
            if stated.is_ordinal:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: {req.spec!r} requires the event-time metric clock, "
                        "but this "
                        "trace records no event timestamps. No ordinal fallback is permitted."
                    ),
                    details={
                        **metric_contract,
                        "time_domain_stated_by_trace": stated.kind,
                        "records_observed": len(records),
                    },
                    binding=req.binding,
                    scope=req.scope,
                )
            return _event_metric_result(req, records, metric_node, stated)

        # The domain the duty is to be counted on is a stated input, not a convention of this
        # function. It defaults to `ORDINAL_DOMAIN` — the record index, which is what every
        # shipped duty is asked for and what a caller passing nothing keeps getting — so a trace
        # that gained event timestamps does not thereby lose a verdict it used to have.
        required = ORDINAL_DOMAIN if time_domain is None else time_domain
        if not required.is_ordinal:
            # The trace's own clock contract is read, never assumed. A trace that states event
            # time badly is refused here for the same reason the metric path refuses it: an
            # invalid instant is evidence this engine has no clock to count on, not an exception
            # a caller meets as an aborted run.
            try:
                stated = read_time_domain(records)
            except (TypeError, ValueError) as exc:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: {req.spec!r} was asked for on the {required.kind!r} time "
                        f"domain, and the trace timestamp contract was refused: {exc}"
                    ),
                    details={
                        "time_domain_required": required.kind,
                        "time_domain_stated_by_trace": EVENT_TIME,
                        "records_observed": len(records),
                        "timestamp_error": str(exc),
                    },
                    binding=req.binding,
                    scope=req.scope,
                )
            missing = (
                "this trace records no event times at all, so there is no clock to count on"
                if stated.is_ordinal
                else (
                    "this trace records event times, but this property carries no bounded-response "
                    "operator to read them with, and the monitor's only time axis is the record "
                    "index"
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
            _refuse_shapes_the_monitor_misreads(property_node)
            boolean_atoms = set(bare_boolean_names(property_node))
        except UnsupportedConstructError as exc:
            wording = (
                (
                    f"Not evaluated: rtamt reads {_property_noun(req)} {req.spec!r} differently "
                    f"from the way the property language defines it, because it uses {exc}"
                )
                if isinstance(exc, MisreadShapeError)
                else (
                    "Not evaluated: rtamt cannot express or parse "
                    f"{_property_noun(req)} {req.spec!r}: {exc}"
                )
            )
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=wording,
                details={"error": str(exc)},
                binding=req.binding,
                scope=req.scope,
            )

        stl_text, presence_signals, contains_signals = _render_stl(
            req.spec, set(req.requires)
        )

        # The property's antecedent, evaluated under Kleene 3-valued logic over the finite trace.
        antecedent_node = implication_antecedent(property_node)

        # Extract variable names from formula or req.requires
        var_names = set(req.requires)
        # Also extract identifiers from spec formula
        monitored_text = stl_text
        found_vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", monitored_text))
        keywords = {
            "always", "eventually", "until", "then", "implies", "and", "or", "not",
            "true", "false", "historically", "once", "since", "rise", "fall", "prev"
        }
        formula_vars = found_vars - keywords
        spec_vars = formula_vars | var_names
        # The names a decision record could carry a value for. `spec_vars` also holds the
        # synthetic `present()`/`contains()` flags `_render_stl` mints for rtamt, which are never
        # record keys and would therefore be reported absent from every trace.
        record_vars = spec_vars - set(presence_signals) - set(contains_signals)
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


        # Construct rtamt STL specification
        spec_name = f"spec_{req.id.replace('-', '_')}"
        try:
            res = _monitor(stl_text, spec_name, spec_vars, time_series)
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
        # Compute the 3-valued verdict under Kleene 3-valued logic over the finite trace.
        # Robustness scores (res) remain reported as the quantitative margin in evaluation_scores.
        boolean_trace = eval_temporal_trace(property_node, records)
        trace_val = (
            boolean_trace[0]
            if has_temporal_operator(property_node)
            else kleene_and(boolean_trace)
        )

        if trace_val is False:
            body_ast = (
                property_node.body
                if isinstance(property_node, ast.Expression)
                else property_node
            )
            if (
                isinstance(body_ast, ast.Call)
                and isinstance(body_ast.func, ast.Name)
                and body_ast.func.id == "always"
                and len(body_ast.args) == 1
            ):
                step_bools = eval_temporal_trace(body_ast.args[0], records)
                violation_indices = [t for t, b in enumerate(step_bools) if b is False]
            else:
                violation_indices = [t for t, b in enumerate(boolean_trace) if b is False]
            if not violation_indices:
                violation_indices = [0]

            offending_segment = [records[t] for t in violation_indices]
            details: dict[str, Any] = {
                "offending_trace_segment": offending_segment,
                "violation_step_indices": violation_indices,
                "evaluation_scores": res,
            }
            prefix = _prefix_witness(property_node, records)
            if prefix is not None:
                # The boolean verdict above already came from the reference interpreter. Keep
                # that independently re-checkable prefix explicit for consumers of the result.
                details["witness"] = {
                    "kind": "trace_prefix",
                    "provenance": "witness-checked",
                    "checker": "reasonsmith.witness._trace_prefix_check",
                    "payload": prefix,
                }
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
                details=details,
                binding=req.binding,
                scope=req.scope,
            )

        if is_unknown(trace_val):
            absent_vars = sorted(
                [v for v in record_vars if any(v not in rec or rec[v] is None for rec in records)]
            )
            gaps = ", ".join(absent_vars) if absent_vars else "a required signal"
            details_dict: dict[str, Any] = {"signals_absent_in_trace": absent_vars}
            if unmeasured:
                details_dict["signals_unmeasured_in_trace"] = dict(sorted(unmeasured.items()))
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: {req.spec!r} depends on signal(s) absent from the trace — "
                    f"no value for {gaps}. The requirement evaluates to UNKNOWN under Kleene "
                    "3-valued logic."
                ),
                details=details_dict,
                binding=req.binding,
                scope=req.scope,
            )

        # No step breached the duty — but a duty triggered nowhere is not breached by any trace,
        # and an antecedent evaluated false at every position is an unreachable trigger.
        # The antecedent is evaluated under Kleene 3-valued logic over the trace.
        if antecedent_node is not None:
            antecedent_bools = eval_temporal_trace(antecedent_node, records)
            if all(b is False for b in antecedent_bools):
                return not_evaluated_for_unreachable_trigger(
                    req,
                    ast.unparse(antecedent_node),
                    f"the {len(records)} decision(s) of this trace",
                    {"records_observed": len(records), "antecedent_evaluations": antecedent_bools},
                )
            if any(is_unknown(b) for b in antecedent_bools) and not any(
                b is True for b in antecedent_bools
            ):
                absent_vars = sorted(
                    [
                        v
                        for v in record_vars
                        if any(v not in rec or rec[v] is None for rec in records)
                    ]
                )
                gaps = ", ".join(absent_vars) if absent_vars else "a required signal"
                details_dict: dict[str, Any] = {"records_observed": len(records)}
                if absent_vars:
                    details_dict["signals_absent_in_trace"] = absent_vars
                if unmeasured:
                    details_dict["signals_unmeasured_in_trace"] = dict(sorted(unmeasured.items()))
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.INCONCLUSIVE,
                    strength=None,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Not evaluated: {req.spec!r} is an implication, and its antecedent "
                        f"{ast.unparse(antecedent_node)!r} evaluates to UNKNOWN under Kleene "
                        "3-valued logic and was never true in the trace — "
                        f"no value for {gaps}. A duty whose trigger cannot be settled is reported "
                        "as no evidence rather than as a clean verdict."
                    ),
                    details=details_dict,
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
                f"Observed over {len(records)} decision(s): "
                f"{_property_noun(req, 'monitor')} for "
                f"{req.spec!r} satisfied at every decision step."
            ),
            details={"records_observed": len(records), "evaluation_scores": res},
            binding=req.binding,
            scope=req.scope,
        )
