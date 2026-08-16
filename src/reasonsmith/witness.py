"""Witness re-checking for results produced by installed engine plug-ins.

The checkers here deliberately use only the shared reference interpreter and the system's own
replay surface.  A missing or uncheckable witness remains at the plug-in's trusted ceiling; only a
witness that the checker refutes demotes a result to not evaluated.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from reasonsmith.rulelang import (
    BINARY_TEMPORAL_OPERATORS,
    UnsupportedConstructError,
    counterfactual_atom,
    eval_expression,
    eval_temporal_trace,
    is_present,
    is_unknown,
    kleene_value,
    parse_property,
    presence_atoms,
)
from reasonsmith.verdict import Verdict

_CONFIRMED = "confirmed"
_UNCHECKABLE = "uncheckable"
_REFUTED = "refuted"


def decision_runner(sut: Any, logic_data: Any) -> tuple[Any, str] | None:
    """Public lift of the proved engine's system replay surface."""
    from reasonsmith.engines.proved import decision_runner as _decision_runner

    return _decision_runner(sut, logic_data)


def verify_counterexample(
    sut: Any, req: Any, inputs: dict[str, Any], logic_data: Any
) -> tuple[bool, str]:
    """Public lift of the proved engine's counterexample replay check."""
    from reasonsmith.engines.proved import _verify_counterexample

    return _verify_counterexample(sut, req, inputs, logic_data)


def _trace_payload(result: Any, kind: str) -> Any:
    details = result.details
    if kind == "presence_absence":
        return {
            "indices": details.get("violation_step_indices", []),
            "signals": details.get("signals_absent_from_trace", []),
        }
    return {"indices": details.get("violation_step_indices", [])}


def _witness(result: Any, formalism: str) -> tuple[str, Any, bool] | None:
    """Return kind/payload and whether the result carried an explicit witness marker."""
    explicit = result.details.get("witness")
    if isinstance(explicit, Mapping):
        return str(explicit.get("kind", "")), explicit.get("payload"), True
    details = result.details
    if formalism == "record" and details.get("violation_step_indices") is not None:
        return "presence_absence", _trace_payload(result, "presence_absence"), False
    if formalism in ("logical", "temporal"):
        if details.get("counterexample") is not None:
            return "input_valuation", details["counterexample"], False
        if details.get("violation_step_indices") is not None:
            return "trace_position", _trace_payload(result, "trace_position"), False
    if formalism == "counterfactual":
        if details.get("counterexample_pair") is not None:
            payload = {"pair": details["counterexample_pair"]}
            if details.get("counterexample_outcomes") is not None:
                payload["outcomes"] = details["counterexample_outcomes"]
            return "execution_pair", payload, False
    return None


def _indices(payload: Any) -> list[int] | None:
    if isinstance(payload, Mapping):
        value = payload.get("indices", payload.get("index", payload.get("position")))
    else:
        value = payload
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            return list(value)
        if len(value) == 2 and isinstance(value[0], int) and not isinstance(value[0], bool):
            return [value[0]]
    return None


def _record_for_index(records: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if index < 0 or index >= len(records):
        return None
    return dict(records[index])


def _prefix_parts(
    payload: Any, records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[int]] | None:
    """Read a temporal prefix witness and its claimed run-out positions.

    A plug-in may send the prefix itself (the useful, portable witness) or just positions, in
    which case the prefix is taken from the trace the plug-in was given.  In both cases the
    checker insists that the witness is an actual prefix of that trace; otherwise an engine could
    manufacture a failing trace instead of witnessing its answer.
    """
    prefix: Any = None
    positions: Any = None
    if isinstance(payload, Mapping):
        for key in ("trace", "prefix", "trace_prefix", "records"):
            if key in payload:
                prefix = payload[key]
                break
        positions = payload.get(
            "positions", payload.get("indices", payload.get("position", payload.get("index")))
        )
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        # A bare list of records is a convenient explicit prefix shape.
        if all(isinstance(item, Mapping) for item in payload):
            prefix = payload

    if prefix is None:
        indices = _indices(positions)
        if not indices:
            return None
        end = max(indices) + 1
        prefix = records[:end]
    if not isinstance(prefix, Sequence) or isinstance(prefix, (str, bytes)):
        return None
    if not prefix or not all(isinstance(item, Mapping) for item in prefix):
        return None
    prefix_records = [dict(item) for item in prefix]
    if prefix_records != records[: len(prefix_records)]:
        return None

    if positions is None:
        positions_list = [len(prefix_records) - 1]
    else:
        parsed_positions = _indices(positions)
        if not parsed_positions:
            return None
        positions_list = parsed_positions
    if any(index < 0 or index >= len(prefix_records) for index in positions_list):
        return None
    return prefix_records, positions_list


def _trace_prefix_check(req: Any, records: list[dict[str, Any]], payload: Any) -> tuple[str, str]:
    """Re-evaluate a finite temporal prefix with the shared reference interpreter."""
    parts = _prefix_parts(payload, records)
    if parts is None:
        return _REFUTED, "the temporal witness did not name a prefix of the supplied trace"
    prefix, positions = parts
    try:
        node = parse_property(req.spec)
    except Exception as exc:
        return (
            _UNCHECKABLE,
            f"reference temporal interpreter refused the property: {type(exc).__name__}: {exc}",
        )
    if not any(
        isinstance(current, ast.Call)
        and isinstance(current.func, ast.Name)
        and current.func.id in BINARY_TEMPORAL_OPERATORS
        for current in ast.walk(node)
    ):
        return _REFUTED, "a trace-prefix witness requires an until or since property"
    try:
        values = eval_temporal_trace(node, prefix)
    except Exception as exc:
        return (
            _UNCHECKABLE,
            f"reference temporal interpreter refused the prefix: {type(exc).__name__}: {exc}",
        )
    if not values:
        return _REFUTED, "the temporal witness named an empty prefix"
    root = kleene_value(values[0])
    if is_unknown(root):
        return _UNCHECKABLE, "reference temporal interpreter returned UNKNOWN for the prefix"
    if root is not False:
        return _REFUTED, f"reference temporal interpreter returned {values[0]!r} at trace start"
    for position in positions:
        value = kleene_value(values[position])
        if is_unknown(value):
            return _UNCHECKABLE, (
                f"reference temporal interpreter returned UNKNOWN at run-out position {position}"
            )
        if value is not False:
            return _REFUTED, (
                f"reference temporal interpreter returned {values[position]!r} at run-out "
                f"position {position}"
            )
    return _CONFIRMED, (
        f"reference temporal interpreter confirmed the prefix through positions {positions}"
    )


def _trace_check(
    req: Any, records: list[dict[str, Any]], kind: str, payload: Any
) -> tuple[str, str]:
    indices = _indices(payload)
    if not indices:
        return _REFUTED, "the witness did not name a trace position"
    try:
        node = parse_property(_state_spec(req))
    except Exception as exc:  # pragma: no cover - loaded requirements already passed this gate
        return _UNCHECKABLE, f"the property could not be parsed: {type(exc).__name__}: {exc}"
    if kind == "presence_absence":
        atoms = presence_atoms(node)
        if isinstance(payload, Mapping):
            signals = payload.get("signals", payload.get("signals_absent", ()))
        elif (
            isinstance(payload, Sequence)
            and not isinstance(payload, (str, bytes))
            and len(payload) == 2
            and isinstance(payload[0], int)
        ):
            indices = [payload[0]]
            signals = payload[1]
        else:
            signals = ()
        if atoms is None or not isinstance(signals, Sequence) or isinstance(signals, (str, bytes)):
            return _REFUTED, "the presence witness does not name a presence conjunction and signals"
        if not set(signals).issubset(set(atoms)):
            return _REFUTED, "the presence witness names a signal outside the property"
        from reasonsmith.report import _is_present

        for index in indices:
            record = _record_for_index(records, index)
            if record is None:
                return _REFUTED, f"the witness names trace position {index}, outside the trace"
            if not any(not _is_present(record.get(signal)) for signal in signals):
                return _REFUTED, f"no named signal is absent at trace position {index}"
        return _CONFIRMED, f"reference presence interpreter confirmed positions {indices}"
    if kind != "trace_position":
        return _UNCHECKABLE, f"the {kind!r} witness is not a trace-position witness"
    for index in indices:
        record = _record_for_index(records, index)
        if record is None:
            return _REFUTED, f"the witness names trace position {index}, outside the trace"
        try:
            value = eval_expression(node, record)
        except Exception as exc:
            return (
                _UNCHECKABLE,
                f"reference interpreter refused the record: {type(exc).__name__}: {exc}",
            )
        if kleene_value(value) is not False:
            return _REFUTED, f"reference interpreter returned {value!r} at trace position {index}"
    return _CONFIRMED, f"reference interpreter confirmed positions {indices}"


def _state_spec(req: Any) -> str:
    if req.formalism == "temporal":
        from reasonsmith.engines.temporal import state_property_under_always

        inner = state_property_under_always(req.spec)
        if inner is not None:
            return inner
    return req.spec


def _declared_input_partition(logic_data: Any) -> tuple[set[str], set[str]] | tuple[None, str]:
    """Read the exact input/output split a declared logic exposes to replay."""
    try:
        from reasonsmith.engines.proved import read_declared_logic

        _rules, variables, _constraints, computes = read_declared_logic(logic_data)
    except Exception as exc:
        return None, (
            "the declared input/output directions could not be read: "
            f"{type(exc).__name__}: {exc}"
        )
    if computes is None:
        return None, (
            "the system declared no computes directions, so the witness checker cannot distinguish "
            "inputs from computed outputs"
        )
    if not isinstance(variables, Mapping):
        return None, "sut.logic() declared variables in a non-mapping form"
    if any(not isinstance(name, str) for name in variables):
        return None, "sut.logic() declared a non-string variable name"
    variable_names = set(variables)
    computed_names = set(computes)
    unknown = computed_names - variable_names
    if unknown:
        return None, f"sut.logic() computes undeclared names: {sorted(unknown)!r}"
    return variable_names - computed_names, computed_names


def _valuation_check(req: Any, sut: Any, payload: Any) -> tuple[str, str]:
    if not isinstance(payload, Mapping):
        return _REFUTED, "the input-valuation witness is not a mapping"
    try:
        parse_property(_state_spec(req))
    except Exception as exc:
        return _UNCHECKABLE, (
            "reference interpreter refused the property: "
            f"{type(exc).__name__}: {exc}"
        )
    try:
        logic_data = sut.logic() if callable(getattr(sut, "logic", None)) else None
    except Exception as exc:
        return _UNCHECKABLE, f"sut.logic() raised {type(exc).__name__}: {exc}"
    partition = _declared_input_partition(logic_data)
    if partition[0] is None:
        return _UNCHECKABLE, partition[1]
    input_names, _computed_names = partition
    if any(not isinstance(name, str) for name in payload):
        return _REFUTED, "the input-valuation witness contains a non-string name"
    supplied = set(payload)
    if supplied != input_names:
        extra = sorted(supplied - input_names)
        missing = sorted(input_names - supplied)
        pieces = []
        if extra:
            pieces.append(f"names not declared as inputs: {extra!r}")
        if missing:
            pieces.append(f"missing declared inputs: {missing!r}")
        return _REFUTED, "the witness is not a complete input valuation (" + "; ".join(pieces) + ")"
    admitted, reason = _admissible(logic_data, payload)
    if not admitted:
        return _REFUTED, f"the witness valuation is inadmissible: {reason}"
    runner = decision_runner(sut, logic_data)
    if runner is None:
        return _UNCHECKABLE, "the system exposes no decide() or declared rule replay surface"
    decide, ran_against = runner
    try:
        record = decide(dict(payload))
    except Exception as exc:
        return (
            _REFUTED,
            f"replaying the witness against {ran_against} raised {type(exc).__name__}: {exc}",
        )
    if not isinstance(record, Mapping):
        return _REFUTED, f"replay returned {type(record).__name__}, not a decision record"
    try:
        value = eval_expression(parse_property(_state_spec(req)), dict(record))
    except Exception as exc:
        return (
            _UNCHECKABLE,
            f"reference interpreter refused the replay: {type(exc).__name__}: {exc}",
        )
    if kleene_value(value) is False:
        return _CONFIRMED, f"reference interpreter confirmed the replay against {ran_against}"
    return _REFUTED, f"replayed decision satisfies the property with value {value!r}"


def _admissible(logic_data: Any, values: Mapping[str, Any]) -> tuple[bool, str]:
    """Ask the proved domain encoding whether one concrete valuation is admitted."""
    try:
        import z3

        from reasonsmith.engines.proved import encode_logic_domain

        scope, solver, _rules, _computes = encode_logic_domain(logic_data)
        for name, value in values.items():
            const = scope.inputs.get(name)
            if const is None:
                return False, f"{name!r} is not a declared input"
            sort = const.sort()
            if z3.is_bool_sort(sort):
                term = z3.BoolVal(bool(value))
            elif z3.is_int_sort(sort):
                term = z3.IntVal(value)
            elif z3.is_real_sort(sort):
                term = z3.RealVal(str(value))
            elif z3.is_string_sort(sort):
                term = z3.StringVal(str(value))
            else:
                return False, f"{name!r} has unsupported declared sort {sort}"
            solver.add(const == term)
        status = solver.check()
        return status == z3.sat, f"declared input constraints returned {status}"
    except Exception as exc:
        return False, f"the declared input domain could not be checked: {type(exc).__name__}: {exc}"


def _pair_payload(payload: Any) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    if isinstance(payload, Mapping):
        pair = payload.get("pair")
        if isinstance(pair, Sequence) and not isinstance(pair, (str, bytes)) and len(pair) == 2:
            left, right = pair
        else:
            left, right = payload.get("left"), payload.get("right")
    elif (
        isinstance(payload, Sequence)
        and not isinstance(payload, (str, bytes))
        and len(payload) == 2
    ):
        left, right = payload
    else:
        return None
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left, right
    return None


def _pair_check(req: Any, sut: Any, payload: Any) -> tuple[str, str]:
    pair = _pair_payload(payload)
    atom = counterfactual_atom(parse_property(req.spec))
    if pair is None or atom is None:
        return _REFUTED, "the execution-pair witness is not a pair of valuations for the atom"
    left, right = pair
    outcome, protected = atom
    if any(not isinstance(name, str) for name in (*left, *right)):
        return _REFUTED, "the execution-pair witness contains a non-string name"
    raw_names = (set(left) | set(right)) - {outcome}
    raw_changed = {name for name in raw_names if left.get(name) != right.get(name)}
    if raw_changed != {protected}:
        return _REFUTED, f"the pair changes {sorted(raw_changed)}, not only {protected!r}"
    try:
        logic_data = sut.logic() if callable(getattr(sut, "logic", None)) else None
    except Exception as exc:
        return _UNCHECKABLE, f"sut.logic() raised {type(exc).__name__}: {exc}"
    partition = _declared_input_partition(logic_data)
    if partition[0] is None:
        return _UNCHECKABLE, partition[1]
    input_names, computed_names = partition
    if protected not in input_names:
        return _REFUTED, f"protected variable {protected!r} is not a declared input"
    if outcome not in computed_names:
        return _REFUTED, f"outcome {outcome!r} is not a declared computed output"
    expected_keys = input_names | {outcome}
    for side, values in (("left", left), ("right", right)):
        extras = set(values) - expected_keys
        missing = input_names - set(values)
        if extras or missing:
            pieces = []
            if extras:
                pieces.append(f"names not inputs or outcome: {sorted(extras)!r}")
            if missing:
                pieces.append(f"missing declared inputs: {sorted(missing)!r}")
            return _REFUTED, (
                f"the {side} witness is not a complete input valuation ("
                + "; ".join(pieces)
                + ")"
            )
    left_values = {name: value for name, value in left.items() if name != outcome}
    right_values = {name: value for name, value in right.items() if name != outcome}
    for side, values in (("left", left_values), ("right", right_values)):
        admitted, reason = _admissible(logic_data, values)
        if not admitted:
            return _REFUTED, f"the {side} witness valuation is inadmissible: {reason}"
    runner = decision_runner(sut, logic_data)
    if runner is None:
        return _UNCHECKABLE, "the system exposes no replay surface"
    decide, ran_against = runner
    try:
        left_record = decide(dict(left_values))
        right_record = decide(dict(right_values))
    except Exception as exc:
        return (
            _REFUTED,
            f"replaying the pair against {ran_against} raised {type(exc).__name__}: {exc}",
        )
    if not isinstance(left_record, Mapping) or not isinstance(right_record, Mapping):
        return _REFUTED, "replaying the pair did not produce two decision records"
    if outcome not in left_record or outcome not in right_record:
        return _UNCHECKABLE, f"replayed records do not expose outcome {outcome!r}"
    if left_record[outcome] == right_record[outcome]:
        return _REFUTED, "replayed pair outcomes did not differ"
    return _CONFIRMED, f"replayed pair differed only in {protected!r} and changed {outcome!r}"


_EVENT_PAIR_FIELDS = (
    "case_id",
    "anchor_timestamp",
    "end_timestamp",
    "bound",
    "anchor_record_index",
    "end_record_index",
)


def _event_pair_check(
    req: Any, records: list[dict[str, Any]], payload: Any
) -> tuple[str, str]:
    """Re-derive a claimed bounded-response breach from the duty and the trace.

    Nothing here is taken on the plug-in's word. The two event names and the deadline come from
    `req.spec`, the two instants come from the records the payload names, the two records must be
    one case with one occurrence of each event under `observed.correlation_key` and
    `observed.case_occurrences` — the rules the metric evaluator itself correlates by, imported
    rather than restated so a plug-in cannot be confirmed on a pair the built-in engine declines
    to measure — and the arithmetic is `event_time.measure_pair`, the checker that engine already
    names. A plug-in therefore cannot pick its own deadline, cannot cite an instant the log does
    not record, cannot claim a deadline started at a record whose anchor predicate is absent,
    cannot run one across two cases, and cannot choose which of a case's duplicate occurrences to
    measure from, which is the same rule `_prefix_parts` applies to a trace prefix. A payload this
    checker cannot read is uncheckable and keeps the plug-in's ceiling; a payload it reads and
    disagrees with is refuted.
    """
    from reasonsmith.engines.observed import case_label, case_occurrences, correlation_key
    from reasonsmith.event_time import (
        EventTimeError,
        format_timestamp,
        measure_pair,
        parse_duration,
        parse_timestamp,
    )
    from reasonsmith.rulelang import bounded_response_arguments, bounded_response_calls
    from reasonsmith.sut import read_time_domain

    if not isinstance(payload, Mapping):
        return _UNCHECKABLE, "the event-pair witness is not a mapping"
    missing = [name for name in _EVENT_PAIR_FIELDS if name not in payload]
    if missing:
        return _UNCHECKABLE, f"the event-pair witness omits {', '.join(missing)}"
    try:
        call = next(iter(bounded_response_calls(parse_property(req.spec))), None)
        if call is None:
            return _UNCHECKABLE, (
                f"{req.spec!r} states no bounded response, so an event pair witnesses nothing "
                "about it"
            )
        anchor_event, endpoint_event, duration_text = bounded_response_arguments(call)
        bound = parse_duration(duration_text)
    except (UnsupportedConstructError, EventTimeError) as exc:
        return _UNCHECKABLE, f"the duty's own bounded response could not be read: {exc}"

    try:
        anchor_index = int(payload["anchor_record_index"])
        end_index = int(payload["end_record_index"])
    except (TypeError, ValueError):
        return _UNCHECKABLE, "the event-pair witness does not name two record indices"
    out_of_range = [
        index for index in (anchor_index, end_index) if not 0 <= index < len(records)
    ]
    if out_of_range:
        return _REFUTED, (
            f"the event-pair witness names record {out_of_range[0]}, which is outside the "
            f"{len(records)}-record trace"
        )

    try:
        claimed_bound = parse_duration(payload["bound"])
        claimed_anchor = parse_timestamp(payload["anchor_timestamp"])
        claimed_end = parse_timestamp(payload["end_timestamp"])
    except EventTimeError as exc:
        return _UNCHECKABLE, f"the event-pair witness cannot be read: {exc}"
    if claimed_bound != bound:
        return _REFUTED, (
            f"the event-pair witness measures against a {claimed_bound.text} bound and "
            f"{req.spec!r} states {bound.text}"
        )

    try:
        anchor_key = correlation_key(records[anchor_index], anchor_index)
        end_key = correlation_key(records[end_index], end_index)
    except ValueError as exc:
        return _REFUTED, f"the trace does not correlate the witnessed records: {exc}"
    if anchor_key != end_key:
        return _REFUTED, (
            f"records {anchor_index} and {end_index} are case {case_label(anchor_key)!r} and "
            f"case {case_label(end_key)!r}, so no deadline runs from one to the other"
        )
    if str(payload["case_id"]) != case_label(anchor_key):
        return _REFUTED, (
            f"the event-pair witness names case {payload['case_id']!r} and the trace makes those "
            f"records case {case_label(anchor_key)!r}"
        )
    try:
        occurrences = {
            role: case_occurrences(records, anchor_key, event_name)
            for role, event_name in (("anchor", anchor_event), ("endpoint", endpoint_event))
        }
    except ValueError as exc:
        return _REFUTED, f"the trace does not correlate the witnessed records: {exc}"
    for role, event_name, index in (
        ("anchor", anchor_event, anchor_index),
        ("endpoint", endpoint_event, end_index),
    ):
        found = occurrences[role]
        if found != [index]:
            return _REFUTED, (
                f"case {case_label(anchor_key)!r} makes {event_name!r} present in "
                f"{len(found)} record(s) {found}, and the witness measures from record {index}; "
                "exactly one occurrence is required"
            )

    try:
        stated = read_time_domain(records)
    except (TypeError, ValueError) as exc:
        return _UNCHECKABLE, f"the trace states no readable event clock: {exc}"
    instants = stated.instants
    measured: dict[str, Any] = {}
    for role, field, event_name, index, claimed in (
        ("anchor", "anchor_timestamp", anchor_event, anchor_index, claimed_anchor),
        ("endpoint", "end_timestamp", endpoint_event, end_index, claimed_end),
    ):
        record = records[index]
        if not is_present(record.get(event_name)):
            return _REFUTED, (
                f"record {index} does not make {event_name!r} present, so it is no {role} of a "
                "bounded response"
            )
        stamps = instants[index] if index < len(instants) else None
        recorded = stamps.get(event_name) if isinstance(stamps, Mapping) else None
        if recorded is None:
            return _REFUTED, (
                f"record {index} records no timestamp for {event_name!r}, so the witness's "
                f"{role} instant is not in the trace"
            )
        if recorded != claimed:
            return _REFUTED, (
                f"the event-pair witness states a {role} of {payload[field]!r} and record "
                f"{index} states {format_timestamp(recorded)}"
            )
        measured[role] = recorded

    try:
        pair = measure_pair(
            case_label(anchor_key),
            measured["anchor"],
            measured["endpoint"],
            bound,
            anchor_record_index=anchor_index,
            end_record_index=end_index,
        )
    except EventTimeError as exc:
        return _REFUTED, f"the claimed pair is not a measurable one: {exc}"
    if pair.within_bound:
        return _REFUTED, (
            f"re-measuring the pair puts {pair.delta_seconds}s inside the {bound.text} bound, "
            "so it witnesses no breach of the deadline"
        )
    for field, derived in (
        ("delta_seconds", pair.delta_seconds),
        ("deadline_timestamp", format_timestamp(pair.deadline_timestamp)),
        ("within_bound", pair.within_bound),
    ):
        if field in payload and payload[field] != derived:
            return _REFUTED, (
                f"the event-pair witness states {field}={payload[field]!r} and re-measuring it "
                f"gives {derived!r}"
            )
    return _CONFIRMED, (
        f"re-measured the trace's own {anchor_event}/{endpoint_event} instants at "
        f"{pair.delta_seconds}s, past the {bound.text} deadline at "
        f"{format_timestamp(pair.deadline_timestamp)}"
    )


def _check(
    req: Any, sut: Any, records: list[dict[str, Any]], kind: str, payload: Any
) -> tuple[str, str, str]:
    if kind in ("trace_position", "presence_absence"):
        status, reason = _trace_check(req, records, kind, payload)
        return status, reason, "reasonsmith.witness._trace_check"
    if kind == "trace_prefix":
        status, reason = _trace_prefix_check(req, records, payload)
        return status, reason, "reasonsmith.witness._trace_prefix_check"
    if kind == "input_valuation":
        status, reason = _valuation_check(req, sut, payload)
        return status, reason, "reasonsmith.witness._valuation_check"
    if kind == "execution_pair":
        status, reason = _pair_check(req, sut, payload)
        return status, reason, "reasonsmith.witness._pair_check"
    if kind == "event_pair":
        status, reason = _event_pair_check(req, records, payload)
        return status, reason, "reasonsmith.witness._event_pair_check"
    return (
        _UNCHECKABLE,
        f"the {kind!r} witness is reserved for a checker not shipped in slice 1",
        ("reasonsmith.witness._uncheckable"),
    )


def _trusted_result(result: Any) -> Any:
    """Remove plug-in authority to claim that the core checked its witness."""
    witness = result.details.get("witness")
    if not isinstance(witness, Mapping):
        return result
    sanitized = dict(witness)
    sanitized["provenance"] = "trusted-ceiling"
    sanitized.pop("checker", None)
    if "payload" not in sanitized:
        sanitized["payload"] = sanitized.get("unverified_payload")
    details = dict(result.details)
    details["witness"] = sanitized
    return replace(result, details=details)


def check_plugin_result(req: Any, sut: Any, records: list[dict[str, Any]], result: Any) -> Any:
    """Attach core-owned provenance, or demote a plug-in result whose witness is refuted."""
    if result.verdict is not Verdict.VIOLATED or result.strength is None:
        return _trusted_result(result)
    basis = getattr(result, "basis", None)
    if getattr(basis, "value", None) == "artifact":
        return _trusted_result(result)
    witness = _witness(result, req.formalism)
    if witness is None:
        return _trusted_result(result)
    kind, payload, _explicit = witness
    status, reason, checker = _check(req, sut, records, kind, payload)
    if status == _REFUTED:
        details = {
            key: value
            for key, value in result.details.items()
            if key
            not in {
                "counterexample",
                "counterexample_pair",
                "counterexample_outcomes",
                "offending_trace_segment",
                "violation_step_indices",
                "signals_absent_from_trace",
            }
        }
        details["witness"] = {
            "kind": kind,
            "provenance": "refuted",
            "failure": reason,
            "unverified_payload": payload,
        }
        return replace(
            result,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            evidence_summary=(
                f"Not evaluated: the engine plug-in supplied a {kind} witness, but the core "
                f"re-check refuted it — {reason}. The result is not a violation."
            ),
            details=details,
        )
    details = dict(result.details)
    details["witness"] = {
        "kind": kind,
        "provenance": "witness-checked" if status == _CONFIRMED else "trusted-ceiling",
        "checker": checker,
        "payload": payload,
    }
    checked = replace(result, details=details)
    return checked if status == _CONFIRMED else _trusted_result(checked)
