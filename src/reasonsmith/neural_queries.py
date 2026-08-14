"""Core-owned neural query compilation and witness checking.

The module is deliberately an oracle boundary, not an engine.  It turns a validated
:class:`~reasonsmith.neural.OnnxArtifact` into a product ONNX graph and a VNN-LIB 1.0
property, and checks SAT assignments by replaying the original graph before exposing a
finding.  Verifier implementations are intentionally absent; ``FakeNeuralVerifier`` is
only a deterministic test double.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from reasonsmith.neural import OnnxArtifact, OutputDecoder, TensorBinding, _freeze

try:  # Optional neural extra; importing the base package must remain possible.
    import numpy as np
    import onnx
    from onnx import TensorProto, helper
except ImportError:  # pragma: no cover - exercised in a dependency-less install.
    np = None  # type: ignore[assignment]
    onnx = None  # type: ignore[assignment]
    TensorProto = None  # type: ignore[assignment,misc]
    helper = None  # type: ignore[assignment]


class VerifierStatus(str, Enum):
    SAT = "sat"
    UNSAT = "unsat"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


VERIFIER_STATUSES = frozenset(item.value for item in VerifierStatus)


class QueryShape(str, Enum):
    COUNTERFACTUAL = "counterfactual_invariance"
    MONOTONICITY = "monotonicity"
    LOCAL_ROBUSTNESS = "local_robustness"


@dataclass(frozen=True, slots=True)
class VerifierRun:
    """The typed, policy-free result returned by a neural verifier."""

    status: str
    assignment: Mapping[str, Any] | None = None
    verifier: str = "fake"
    version: str = "test"
    diagnostic: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = str(self.status).lower()
        if status not in VERIFIER_STATUSES:
            raise ValueError(f"unsupported verifier status {self.status!r}")
        object.__setattr__(self, "status", status)
        if self.assignment is not None and not isinstance(self.assignment, Mapping):
            raise ValueError("verifier assignment must be a mapping")
        if self.assignment is not None:
            object.__setattr__(self, "assignment", _freeze(dict(self.assignment)))
        if not isinstance(self.provenance, Mapping):
            raise ValueError("verifier provenance must be a mapping")
        object.__setattr__(self, "provenance", _freeze(dict(self.provenance)))
        if not isinstance(self.verifier, str) or not self.verifier:
            raise ValueError("verifier name must be non-empty")
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("verifier version must be non-empty")


class NeuralVerifier(Protocol):
    def verify(
        self,
        query: "CompiledNeuralQuery",
        *,
        timeout: float | None = None,
        mode: str = "bounded-search",
    ) -> VerifierRun: ...


class FakeNeuralVerifier:
    """A deterministic oracle for compiler and witness-boundary tests."""

    def __init__(self, runs: VerifierRun | Mapping[str, Any] | Sequence[Any]):
        if isinstance(runs, (VerifierRun, Mapping)):
            runs = [runs]
        self._runs = [run if isinstance(run, VerifierRun) else VerifierRun(**run) for run in runs]
        if not self._runs:
            raise ValueError("fake verifier needs at least one controlled run")
        self.calls: list[tuple["CompiledNeuralQuery", float | None, str]] = []

    def verify(
        self,
        query: "CompiledNeuralQuery",
        *,
        timeout: float | None = None,
        mode: str = "bounded-search",
    ) -> VerifierRun:
        self.calls.append((query, timeout, mode))
        return self._runs.pop(0) if len(self._runs) > 1 else self._runs[0]


# Friendly short alias used by test fixtures and examples.
FakeVerifier = FakeNeuralVerifier
FakeOracle = FakeNeuralVerifier


@dataclass(frozen=True, slots=True)
class WitnessCheck:
    valid: bool
    reason: str | None = None
    inputs: Mapping[str, Mapping[str, Any]] | None = None
    outputs: Mapping[str, Mapping[str, Any]] | None = None
    decoded: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class OracleCheck:
    """Raw oracle response plus optional replay result; no verdict or evidence rung."""

    run: VerifierRun
    witness: WitnessCheck | None = None

    @property
    def inconclusive(self) -> bool:
        return self.run.status != "sat" or self.witness is None or not self.witness.valid


@dataclass(frozen=True, slots=True)
class CompiledNeuralQuery:
    shape: QueryShape
    artifact: OnnxArtifact
    product_model: bytes
    vnnlib: str
    model_sha256: str
    query_sha256: str
    metadata: Mapping[str, Any]
    required_assertions: tuple[str, ...]

    @property
    def model(self) -> bytes:
        return self.product_model

    @property
    def query(self) -> str:
        return self.vnnlib

    def validate(self) -> "CompiledNeuralQuery":
        validate_compiled_query(self)
        return self


@dataclass(frozen=True, slots=True)
class _Coordinate:
    signal: str
    tensor: str
    coordinate: tuple[int, ...]
    flat: int
    lower: Any
    upper: Any


_IDENT = re.compile(r"[^A-Za-z0-9_]")


def _require_onnx() -> None:
    if onnx is None or helper is None or np is None:
        raise ValueError("neural query compilation requires reasonsmith[neural]")


def _safe_name(value: str) -> str:
    result = _IDENT.sub("_", value).strip("_") or "v"
    if result[0].isdigit():
        result = "v_" + result
    return result


def _num(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    value = float(value) if isinstance(value, float) else value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("query values must be finite")
        text = format(value, ".17g")
        return text if "." in text or "e" in text.lower() else text + ".0"
    return str(value)


def _flat_coordinate(coordinate: tuple[int, ...], shape: tuple[int, ...]) -> int:
    if len(coordinate) == 1:
        flat = coordinate[0]
        if flat < 0 or flat >= math.prod(shape):
            raise ValueError("declared coordinate is outside tensor shape")
        return flat
    flat = 0
    for item, extent in zip(coordinate, shape, strict=True):
        flat = flat * extent + item
    return flat


def _coordinates(artifact: OnnxArtifact) -> tuple[_Coordinate, ...]:
    slots = {slot.signal: slot for slot in artifact.input_space.slots}
    result: list[_Coordinate] = []
    seen: set[tuple[str, int]] = set()
    for binding in artifact.inputs:
        covered: set[int] = set()
        for signal, coordinate in binding.coordinates.items():
            slot = slots.get(signal)
            if slot is None:
                raise ValueError(f"input coordinate {signal!r} is not in the input space")
            flat = _flat_coordinate(coordinate, binding.shape)
            covered.add(flat)
            key = (binding.name, flat)
            if key in seen:
                raise ValueError("input coordinate map is not injective")
            seen.add(key)
            result.append(
                _Coordinate(signal, binding.name, coordinate, flat, slot.lower, slot.upper)
            )
        if covered != set(range(math.prod(binding.shape))):
            raise ValueError("every product-network input coordinate needs a declared signal/bound")
    return tuple(result)


def _output_binding(
    artifact: OnnxArtifact, signal: str
) -> tuple[TensorBinding, tuple[int, ...], OutputDecoder]:
    for binding in artifact.outputs:
        if signal in binding.coordinates:
            decoder = binding.decoders.get(signal)
            if decoder is None:
                raise ValueError(f"output signal {signal!r} has no total decoder")
            return binding, binding.coordinates[signal], decoder
    raise ValueError(f"unknown decoded output signal {signal!r}")


def _copy_product_model(artifact: OnnxArtifact) -> bytes:
    _require_onnx()
    original = onnx.load_model_from_string(artifact.model)
    initializers = {item.name for item in original.graph.initializer}
    # Every graph value is renamed per half. Initializers remain shared constants.
    values = {value.name for value in original.graph.input}
    values.update(value.name for value in original.graph.output)
    values.update(value.name for value in original.graph.value_info)
    for node in original.graph.node:
        values.update(name for name in node.output if name)
        values.update(name for name in node.input if name and name not in initializers)

    def rename(name: str, suffix: str) -> str:
        return name if not name or name in initializers else f"{name}__{suffix}"

    graph_inputs = []
    graph_outputs = []
    nodes = []
    value_infos = []
    for suffix in ("a", "b"):
        for item in original.graph.input:
            if item.name not in initializers:
                clone = copy.deepcopy(item)
                clone.name = rename(item.name, suffix)
                graph_inputs.append(clone)
        for item in original.graph.output:
            clone = copy.deepcopy(item)
            clone.name = rename(item.name, suffix)
            graph_outputs.append(clone)
        for item in original.graph.value_info:
            clone = copy.deepcopy(item)
            clone.name = rename(item.name, suffix)
            value_infos.append(clone)
        for node in original.graph.node:
            clone = copy.deepcopy(node)
            clone.name = f"{node.name or 'node'}__{suffix}"
            clone.input[:] = [rename(name, suffix) for name in node.input]
            clone.output[:] = [rename(name, suffix) for name in node.output]
            nodes.append(clone)
    graph = helper.make_graph(
        nodes,
        f"{original.graph.name or 'model'}__product",
        graph_inputs,
        graph_outputs,
        [copy.deepcopy(item) for item in original.graph.initializer],
        value_info=value_infos,
    )
    product = helper.make_model(graph)
    product.ir_version = original.ir_version
    del product.opset_import[:]
    for item in original.opset_import:
        product.opset_import.add(domain=item.domain, version=item.version)
    product.producer_name = "reasonsmith"
    product.producer_version = "neural-query-1"
    return product.SerializeToString()


def _variable_map(artifact: OnnxArtifact, suffix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for coordinate in _coordinates(artifact):
        result[f"{coordinate.tensor}:{coordinate.flat}:{suffix}"] = (
            f"{_safe_name(coordinate.tensor)}_{suffix}_{coordinate.flat}"
        )
    return result


def _var(c: _Coordinate, suffix: str) -> str:
    return f"{_safe_name(c.tensor)}_{suffix}_{c.flat}"


def _input_assertions(artifact: OnnxArtifact, coordinates: Sequence[_Coordinate]) -> list[str]:
    assertions: list[str] = []
    for suffix in ("a", "b"):
        for c in coordinates:
            assertions.append(f"(>= {_var(c, suffix)} {_num(c.lower)})")
            assertions.append(f"(<= {_var(c, suffix)} {_num(c.upper)})")
        for constraint in artifact.input_space.constraints:
            if "signal" in constraint:
                c = next(item for item in coordinates if item.signal == constraint["signal"])
                left = _var(c, suffix)
                right = _num(constraint["value"])
            else:
                left_c = next(item for item in coordinates if item.signal == constraint["left"])
                left = _var(left_c, suffix)
                right_c = next(item for item in coordinates if item.signal == constraint["right"])
                right = _var(right_c, suffix)
            assertions.append(f"({constraint['op']} {left} {right})")
    return assertions


def _assignment_satisfies_input_space(artifact: OnnxArtifact, values: Mapping[str, Any]) -> bool:
    slots = {slot.signal: slot for slot in artifact.input_space.slots}
    for signal, value in values.items():
        slot = slots[signal]
        if slot.kind in ("categorical", "string-enum") and value not in slot.values:
            return False
        if slot.kind == "boolean" and value not in (False, True):
            return False
        if slot.kind == "integer" and float(value).is_integer() is False:
            return False
    for constraint in artifact.input_space.constraints:
        if "signal" in constraint:
            left = values[constraint["signal"]]
            right = constraint["value"]
        else:
            left = values[constraint["left"]]
            right = values[constraint["right"]]
        op = constraint["op"]
        if not {
            "<": left < right,
            "<=": left <= right,
            "=": left == right,
            "==": left == right,
            ">=": left >= right,
            ">": left > right,
        }[op]:
            return False
    return True


def _decoder_predicate(value: str, decoder: OutputDecoder, label: Any) -> str:
    if decoder.kind != "threshold":
        raise ValueError("VNN-LIB profile currently supports threshold output decoders only")
    threshold = _num(decoder.threshold)
    if label == decoder.low:
        op = "<=" if decoder.tie == decoder.low else "<"
        return f"({op} {value} {threshold})"
    if label == decoder.high:
        op = ">=" if decoder.tie == decoder.high else ">"
        return f"({op} {value} {threshold})"
    if label == decoder.tie:
        return f"(= {value} {threshold})"
    raise ValueError("unknown decoder label")


def _decoded_different(left: str, right: str, decoder: OutputDecoder) -> str:
    labels = [decoder.low, decoder.high]
    if decoder.tie != decoder.low and decoder.tie != decoder.high:
        labels.append(decoder.tie)
    terms: list[str] = []
    for left_label in labels:
        for right_label in labels:
            if left_label != right_label:
                terms.append(
                    f"(and {_decoder_predicate(left, decoder, left_label)} "
                    f"{_decoder_predicate(right, decoder, right_label)})"
                )
    if not terms:
        raise ValueError("decoder low and high outcomes must differ")
    return terms[0] if len(terms) == 1 else f"(or {' '.join(terms)})"


def _query_text(variables: Sequence[str], assertions: Sequence[str], unsafe: str) -> str:
    lines = ["; reasonsmith VNN-LIB 1.0", "; query describes the unsafe region"]
    lines.extend(f"(declare-fun {name} () Real)" for name in variables)
    lines.extend(f"(assert {assertion})" for assertion in assertions)
    lines.append(f"(assert {unsafe})")
    lines.append("(check-sat)")
    lines.append("(get-value (" + " ".join(variables) + "))")
    return "\n".join(lines) + "\n"


def _make_query(
    artifact: OnnxArtifact,
    shape: QueryShape,
    unsafe: str,
    assertions: list[str],
    metadata: Mapping[str, Any],
) -> CompiledNeuralQuery:
    product = _copy_product_model(artifact)
    coordinates = _coordinates(artifact)
    variables = [_var(c, suffix) for suffix in ("a", "b") for c in coordinates]
    output_variables: list[str] = []
    for binding in artifact.outputs:
        for coordinate in range(math.prod(binding.shape)):
            for suffix in ("a", "b"):
                output_variables.append(f"{_safe_name(binding.name)}_{suffix}_{coordinate}")
    text = _query_text(variables + output_variables, assertions, unsafe)
    required = tuple(assertions)
    return CompiledNeuralQuery(
        shape,
        artifact,
        product,
        text,
        artifact.model_sha256,
        hashlib.sha256(text.encode()).hexdigest(),
        {**metadata, "product_model_sha256": hashlib.sha256(product).hexdigest()},
        required,
    )


def compile_counterfactual_query(
    artifact: OnnxArtifact,
    *,
    protected_signal: str = "applicant_prohibited_basis",
    outcome_signal: str = "artifact_logs_decision_record",
) -> CompiledNeuralQuery:
    """Compile exact ECOA-style invariance into one product-network query."""
    coordinates = _coordinates(artifact)
    protected = next((c for c in coordinates if c.signal == protected_signal), None)
    if protected is None:
        raise ValueError(f"unknown protected input signal {protected_signal!r}")
    slot = artifact.input_space.slot(protected_signal)
    values = slot.values or ((False, True) if slot.kind == "boolean" else ())
    if slot.kind == "integer" and not values:
        raise ValueError("counterfactual protected integer needs finite categorical values")
    if not values or len(values) < 2:
        raise ValueError("counterfactual protected signal needs at least two finite values")
    _, out_coord, decoder = _output_binding(artifact, outcome_signal)
    out_binding, _, _ = _output_binding(artifact, outcome_signal)
    output_flat = _flat_coordinate(out_coord, out_binding.shape)
    left_out = f"{_safe_name(out_binding.name)}_a_{output_flat}"
    right_out = f"{_safe_name(out_binding.name)}_b_{output_flat}"
    assertions = _input_assertions(artifact, coordinates)
    pairs: list[str] = []
    for left in values:
        for right in values:
            if left == right:
                continue
            pairs.append(
                "(and (= "
                f"{_var(protected, 'a')} {_num(left)}) "
                f"(= {_var(protected, 'b')} {_num(right)}))"
            )
    equalities = [
        f"(= {_var(c, 'a')} {_var(c, 'b')})" for c in coordinates if c.signal != protected_signal
    ]
    assertions.extend(equalities)
    unsafe = f"(and (or {' '.join(pairs)}) {_decoded_different(left_out, right_out, decoder)})"
    return _make_query(
        artifact,
        QueryShape.COUNTERFACTUAL,
        unsafe,
        assertions,
        {
            "protected_signal": protected_signal,
            "outcome_signal": outcome_signal,
            "protected_values": tuple(values),
            "held_equal_signals": tuple(
                c.signal for c in coordinates if c.signal != protected_signal
            ),
        },
    )


def compile_monotonicity_query(
    artifact: OnnxArtifact, *, feature: str, outcome_signal: str, direction: str = "nondecreasing"
) -> CompiledNeuralQuery:
    """Compile a two-execution monotonicity reversal query."""
    coordinates = _coordinates(artifact)
    feature_coord = next((c for c in coordinates if c.signal == feature), None)
    if feature_coord is None:
        raise ValueError(f"unknown monotonicity feature {feature!r}")
    if direction not in ("nondecreasing", "nonincreasing"):
        raise ValueError("direction must be nondecreasing or nonincreasing")
    out_binding, out_coord, _ = _output_binding(artifact, outcome_signal)
    output_flat = _flat_coordinate(out_coord, out_binding.shape)
    left = f"{_safe_name(out_binding.name)}_a_{output_flat}"
    right = f"{_safe_name(out_binding.name)}_b_{output_flat}"
    assertions = _input_assertions(artifact, coordinates)
    assertions.extend(
        f"(= {_var(c, 'a')} {_var(c, 'b')})" for c in coordinates if c.signal != feature
    )
    assertions.append(f"(<= {_var(feature_coord, 'a')} {_var(feature_coord, 'b')})")
    unsafe = f"(> {left} {right})" if direction == "nondecreasing" else f"(< {left} {right})"
    return _make_query(
        artifact,
        QueryShape.MONOTONICITY,
        unsafe,
        assertions,
        {
            "feature": feature,
            "outcome_signal": outcome_signal,
            "direction": direction,
            "held_equal_signals": tuple(c.signal for c in coordinates if c.signal != feature),
        },
    )


def compile_local_robustness_query(
    artifact: OnnxArtifact,
    *,
    centre: Mapping[str, Any],
    radius: float | Mapping[str, float],
    outcome_signal: str,
    output_tolerance: float = 0.0,
    metric: str = "linf",
) -> CompiledNeuralQuery:
    """Compile an exact L-infinity local-robustness unsafe region."""
    if metric.lower() not in ("linf", "l-infinity", "l_inf"):
        raise ValueError("only L-infinity local robustness is supported")
    if not isinstance(centre, Mapping):
        raise ValueError("local-robustness centre must be a mapping")
    if output_tolerance < 0 or not math.isfinite(float(output_tolerance)):
        raise ValueError("output_tolerance must be finite and non-negative")
    coordinates = _coordinates(artifact)
    centre_values: dict[str, Any] = {}
    for c in coordinates:
        if c.signal not in centre:
            raise ValueError(f"local-robustness centre is missing {c.signal!r}")
        value = centre[c.signal]
        if value < c.lower or value > c.upper:
            raise ValueError(f"local-robustness centre is outside bounds for {c.signal!r}")
        centre_values[c.signal] = value
    radii = (
        {signal: radius for signal in centre_values}
        if isinstance(radius, (int, float))
        else dict(radius)
    )
    if set(radii) != set(centre_values):
        raise ValueError("L-infinity radius must cover exactly the declared input signals")
    assertions = _input_assertions(artifact, coordinates)
    for c in coordinates:
        assertions.append(f"(= {_var(c, 'a')} {_num(centre_values[c.signal])})")
        r = radii[c.signal]
        if r < 0 or not math.isfinite(float(r)):
            raise ValueError("L-infinity radii must be finite and non-negative")
        lo = max(float(c.lower), float(centre_values[c.signal]) - float(r))
        hi = min(float(c.upper), float(centre_values[c.signal]) + float(r))
        assertions.extend((f"(>= {_var(c, 'b')} {_num(lo)})", f"(<= {_var(c, 'b')} {_num(hi)})"))
    out_binding, out_coord, decoder = _output_binding(artifact, outcome_signal)
    output_flat = _flat_coordinate(out_coord, out_binding.shape)
    left = f"{_safe_name(out_binding.name)}_a_{output_flat}"
    right = f"{_safe_name(out_binding.name)}_b_{output_flat}"
    changed = _decoded_different(left, right, decoder)
    tolerance = (
        f"(or (> {right} (+ {left} {_num(output_tolerance)})) "
        f"(< {right} (- {left} {_num(output_tolerance)})))"
    )
    unsafe = f"(or {changed} {tolerance})"
    return _make_query(
        artifact,
        QueryShape.LOCAL_ROBUSTNESS,
        unsafe,
        assertions,
        {
            "centre": dict(centre_values),
            "radius": dict(radii),
            "metric": "linf",
            "outcome_signal": outcome_signal,
            "output_tolerance": output_tolerance,
        },
    )


def validate_compiled_query(query: CompiledNeuralQuery) -> None:
    """Reject query text mutants that drop equalities or widen declared bounds."""
    for assertion in query.required_assertions:
        if f"(assert {assertion})" not in query.vnnlib:
            raise ValueError("compiled query lost a required declaration assertion")
    for c in _coordinates(query.artifact):
        for suffix in ("a", "b"):
            for assertion in (
                f"(>= {_var(c, suffix)} {_num(c.lower)})",
                f"(<= {_var(c, suffix)} {_num(c.upper)})",
            ):
                if f"(assert {assertion})" not in query.vnnlib:
                    raise ValueError("compiled query widened or dropped an input bound")
    if query.shape == QueryShape.COUNTERFACTUAL:
        protected = query.metadata["protected_signal"]
        coords = _coordinates(query.artifact)
        protected_c = next(c for c in coords if c.signal == protected)
        if not any(
            f"(= {_var(protected_c, 'a')} {_num(value)})" in query.vnnlib
            for value in query.metadata["protected_values"]
        ):
            raise ValueError("compiled counterfactual query lost protected-value constraints")
        for c in coords:
            if c.signal != protected and f"(= {_var(c, 'a')} {_var(c, 'b')})" not in query.vnnlib:
                raise ValueError("compiled counterfactual query lost a held-equal coordinate")


def _normalise_assignment(
    query: CompiledNeuralQuery, assignment: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(assignment, Mapping):
        raise ValueError("witness assignment must be a mapping")
    if isinstance(assignment.get("a"), Mapping) and isinstance(assignment.get("b"), Mapping):
        raw_a, raw_b = assignment["a"], assignment["b"]

        def half(raw: Mapping[str, Any], suffix: str) -> dict[str, Any]:
            result = {}
            for c in _coordinates(query.artifact):
                key = _var(c, suffix)
                result[c.signal] = raw.get(c.signal, raw.get(key, raw.get(str(c.flat))))
            return result

        return half(raw_a, "a"), half(raw_b, "b")
    result_a: dict[str, Any] = {}
    result_b: dict[str, Any] = {}
    for c in _coordinates(query.artifact):
        result_a[c.signal] = assignment.get(
            _var(c, "a"), assignment.get(f"a.{c.signal}", assignment.get(c.signal))
        )
        result_b[c.signal] = assignment.get(
            _var(c, "b"), assignment.get(f"b.{c.signal}", assignment.get(c.signal))
        )
    return result_a, result_b


def _decode(value: float, decoder: OutputDecoder) -> Any:
    if decoder.kind != "threshold":
        raise ValueError("reference replay supports threshold decoders only")
    if value < float(decoder.threshold):
        return decoder.low
    if value > float(decoder.threshold):
        return decoder.high
    return decoder.tie


def _reference_replay(
    artifact: OnnxArtifact, values: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_onnx()
    model = onnx.load_model_from_string(artifact.model)
    from onnx.reference import ReferenceEvaluator

    feeds: dict[str, Any] = {}
    for binding in artifact.inputs:
        dtype = (
            np.float32
            if binding.dtype == "float32"
            else np.float64
            if binding.dtype == "float64"
            else np.int64
        )
        array = np.zeros(binding.shape, dtype=dtype)
        for signal, coordinate in binding.coordinates.items():
            flat = _flat_coordinate(coordinate, binding.shape)
            array.reshape(-1)[flat] = values[signal]
        feeds[binding.name] = array
    names = [binding.name for binding in artifact.outputs]
    raw_values = ReferenceEvaluator(model).run(names, feeds)
    raw: dict[str, Any] = {}
    decoded: dict[str, Any] = {}
    for binding, output in zip(artifact.outputs, raw_values, strict=True):
        flat_output = np.asarray(output).reshape(-1)
        for signal, coordinate in binding.coordinates.items():
            flat = _flat_coordinate(coordinate, binding.shape)
            value = float(flat_output[flat])
            raw[signal] = value
            decoder = binding.decoders.get(signal)
            if decoder is not None:
                decoded[signal] = _decode(value, decoder)
    return raw, decoded


def check_witness(
    query: CompiledNeuralQuery,
    assignment: Mapping[str, Any],
    *,
    replay: Callable[[Mapping[str, Any]], Any] | None = None,
    sut_replay: Callable[[Mapping[str, Any]], Any] | None = None,
    sut: Any = None,
) -> WitnessCheck:
    """Replay and validate a verifier assignment; invalid witnesses never become findings."""
    try:
        left, right = _normalise_assignment(query, assignment)
        coordinates = _coordinates(query.artifact)
        for values in (left, right):
            for c in coordinates:
                value = values.get(c.signal)
                if (
                    value is None
                    or not math.isfinite(float(value))
                    or value < c.lower
                    or value > c.upper
                ):
                    return WitnessCheck(
                        False, f"assignment for {c.signal!r} is outside declared bounds"
                    )
            if not _assignment_satisfies_input_space(query.artifact, values):
                return WitnessCheck(
                    False, "assignment violates categorical values or cross-input constraints"
                )
        if query.shape == QueryShape.COUNTERFACTUAL:
            protected = query.metadata["protected_signal"]
            if left[protected] == right[protected]:
                return WitnessCheck(False, "protected coordinate did not change")
            for c in coordinates:
                if c.signal != protected and left[c.signal] != right[c.signal]:
                    return WitnessCheck(False, f"held-equal coordinate {c.signal!r} changed")
        if query.shape == QueryShape.MONOTONICITY:
            feature = query.metadata["feature"]
            if left[feature] > right[feature]:
                return WitnessCheck(False, "monotonicity feature order is reversed")
        if query.shape == QueryShape.LOCAL_ROBUSTNESS:
            centre = query.metadata["centre"]
            for signal, value in centre.items():
                if left[signal] != value:
                    return WitnessCheck(False, "local-robustness centre was not held fixed")
                radius = query.metadata["radius"][signal]
                if abs(float(right[signal]) - float(value)) > float(radius) + 1e-12:
                    return WitnessCheck(False, f"assignment for {signal!r} exceeds local radius")
        left_raw, left_decoded = _reference_replay(query.artifact, left)
        right_raw, right_decoded = _reference_replay(query.artifact, right)
        outcome = query.metadata.get("outcome_signal")
        if query.shape == QueryShape.COUNTERFACTUAL:
            violated = left_decoded.get(outcome) != right_decoded.get(outcome)
        elif query.shape == QueryShape.MONOTONICITY:
            violated = (
                (left_raw[outcome] > right_raw[outcome])
                if query.metadata["direction"] == "nondecreasing"
                else (left_raw[outcome] < right_raw[outcome])
            )
        else:
            violated = (
                left_decoded.get(outcome) != right_decoded.get(outcome)
                or abs(right_raw[outcome] - left_raw[outcome]) > query.metadata["output_tolerance"]
            )
        if not violated:
            return WitnessCheck(False, "ONNX replay did not reproduce the queried violation")
        if replay is not None:
            for values, expected in ((left, left_decoded), (right, right_decoded)):
                returned = replay(dict(values))
                observed = returned.get(outcome) if isinstance(returned, Mapping) else returned
                if observed != expected.get(outcome, observed):
                    return WitnessCheck(False, "SUT replay did not reproduce the decoded outcome")
        if sut_replay is not None:
            for values, expected in ((left, left_decoded), (right, right_decoded)):
                returned = sut_replay(dict(values))
                observed = returned.get(outcome) if isinstance(returned, Mapping) else returned
                if observed != expected.get(outcome, observed):
                    return WitnessCheck(False, "SUT replay did not reproduce the decoded outcome")
        if sut is not None:
            decide = sut if callable(sut) else getattr(sut, "decide", None)
            if not callable(decide):
                return WitnessCheck(False, "SUT has no callable decide replay")
            for values, expected in ((left, left_decoded), (right, right_decoded)):
                returned = decide(dict(values))
                observed = returned.get(outcome) if isinstance(returned, Mapping) else returned
                if observed != expected.get(outcome, observed):
                    return WitnessCheck(False, "SUT replay did not reproduce the decoded outcome")
        return WitnessCheck(
            True,
            inputs={"a": left, "b": right},
            outputs={"a": left_raw, "b": right_raw},
            decoded={"a": left_decoded, "b": right_decoded},
        )
    except Exception as exc:
        return WitnessCheck(False, f"witness replay failed: {exc}")


def verify_query(
    query: CompiledNeuralQuery,
    verifier: NeuralVerifier,
    *,
    timeout: float | None = None,
    mode: str = "bounded-search",
    replay: Callable[[Mapping[str, Any]], Any] | None = None,
    sut_replay: Callable[[Mapping[str, Any]], Any] | None = None,
) -> OracleCheck:
    """Ask an injected oracle and replay SAT assignments; never create a verdict."""
    try:
        query.validate()
        run = verifier.verify(query, timeout=timeout, mode=mode)
    except Exception as exc:
        run = VerifierRun("error", diagnostic=str(exc))
        return OracleCheck(run)
    if run.status != "sat" or run.assignment is None:
        return OracleCheck(run)
    return OracleCheck(
        run, check_witness(query, run.assignment, replay=replay, sut_replay=sut_replay)
    )


# Alternate names make the narrow boundary easy to discover without creating a second API.
CompiledQuery = CompiledNeuralQuery
OracleResult = OracleCheck
compile_ecoa_counterfactual_query = compile_counterfactual_query
compile_linf_robustness_query = compile_local_robustness_query
run_neural_query = verify_query
check_neural_witness = check_witness

__all__ = [
    "VERIFIER_STATUSES",
    "VerifierStatus",
    "QueryShape",
    "VerifierRun",
    "NeuralVerifier",
    "FakeNeuralVerifier",
    "FakeVerifier",
    "FakeOracle",
    "WitnessCheck",
    "OracleCheck",
    "CompiledNeuralQuery",
    "CompiledQuery",
    "OracleResult",
    "compile_counterfactual_query",
    "compile_ecoa_counterfactual_query",
    "compile_monotonicity_query",
    "compile_local_robustness_query",
    "compile_linf_robustness_query",
    "validate_compiled_query",
    "check_witness",
    "check_neural_witness",
    "verify_query",
    "run_neural_query",
]
