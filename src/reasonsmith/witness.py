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
    counterfactual_atom,
    eval_expression,
    eval_temporal_trace,
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


def _valuation_check(req: Any, sut: Any, payload: Any) -> tuple[str, str]:
    if not isinstance(payload, Mapping):
        return _REFUTED, "the input-valuation witness is not a mapping"
    logic_data = None
    try:
        logic_data = sut.logic() if callable(getattr(sut, "logic", None)) else None
    except Exception as exc:
        return _UNCHECKABLE, f"sut.logic() raised {type(exc).__name__}: {exc}"
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
    names = set(left) | set(right)
    if outcome in names:
        names.remove(outcome)
    changed = {name for name in names if left.get(name) != right.get(name)}
    if changed != {protected}:
        return _REFUTED, f"the pair changes {sorted(changed)}, not only {protected!r}"
    try:
        logic_data = sut.logic() if callable(getattr(sut, "logic", None)) else None
    except Exception as exc:
        return _UNCHECKABLE, f"sut.logic() raised {type(exc).__name__}: {exc}"
    if logic_data is None:
        return _UNCHECKABLE, "the system exposes no declared input domain"
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
