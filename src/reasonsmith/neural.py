"""Typed, declarative exposures for neural and template-based systems.

This module deliberately stops at *validation*.  Slice 1 does not compile a query, call a
verifier, or route a requirement to an engine.  ``OnnxArtifact`` is a model-global exposure
returned by ``artifact(None)`` and ``DeclaredInputSpace`` is an independent description of a
finite, renderable input domain.

The declarations are still declarations.  Parsing an ONNX graph cannot establish that the graph,
pre/post-processing, coordinate map, bounds, decoder, or model identifier are the deployed system;
nor can this module establish floating-point fidelity or verifier soundness.  Those self-declaration
limits remain part of the later neural evidence contract.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

try:  # Importing reasonsmith should still work for users not constructing neural exposures.
    import onnx
    from onnx import TensorProto, checker
except ImportError:  # pragma: no cover - exercised only in a dependency-less source checkout.
    onnx = None  # type: ignore[assignment]
    TensorProto = None  # type: ignore[assignment,misc]
    checker = None  # type: ignore[assignment]


SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_VNNLIB_VERSIONS = ("1.0",)
SUPPORTED_OPSET_DOMAINS = frozenset(("", "ai.onnx"))
_SLOT_TYPES = frozenset(("real", "integer", "categorical", "boolean", "string-enum"))
_PLACEHOLDER = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_.-]*)\}(?!\})")


def _schema_version(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{label} must be integer schema version 1")
    if value != SUPPORTED_SCHEMA_VERSION:
        _fail(f"unsupported {label} {value!r}; supported version is 1")
    return value


def _fail(message: str) -> None:
    raise ValueError(message)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")
    return value


def _finite_number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{label} must be a finite number")
    if not math.isfinite(float(value)):
        _fail(f"{label} must be finite")
    return value


def _freeze(value: Any) -> Any:
    """Freeze declaration metadata while retaining ordinary JSON-shaped values."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _as_sequence(value: Any, label: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        _fail(f"{label} must be a sequence")
    return tuple(value)


def _unique(values: Sequence[Any], label: str) -> tuple[Any, ...]:
    result: list[Any] = []
    for value in values:
        if any(value == old for old in result):
            _fail(f"{label} contains duplicate value {value!r}")
        result.append(value)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class InputSlot:
    """One finite input-space slot.

    Mapping input is accepted by ``DeclaredInputSpace`` so adapters need not import this helper.
    ``kind`` is exposed as the ``type`` property as well, matching the design vocabulary.
    """

    signal: str
    kind: str
    lower: int | float | None = None
    upper: int | float | None = None
    values: tuple[Any, ...] = ()
    value_to_token: Mapping[Any, str] = field(default_factory=lambda: MappingProxyType({}))

    @property
    def type(self) -> str:
        return self.kind

    @classmethod
    def from_value(cls, value: Any) -> "InputSlot":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            _fail("each input-space slot must be a mapping or InputSlot")
        signal = _nonempty_string(value.get("signal"), "slot.signal")
        kind = value.get("type", value.get("kind"))
        kind = _nonempty_string(kind, f"slot {signal!r} type")
        if kind not in _SLOT_TYPES:
            _fail(f"slot {signal!r} has unsupported type {kind!r}")

        has_lower = "lower" in value or "min" in value
        has_upper = "upper" in value or "max" in value
        lower = value.get("lower", value.get("min"))
        upper = value.get("upper", value.get("max"))
        raw_values = value.get("values", value.get("codes", value.get("categories")))
        values: tuple[Any, ...] = ()
        if raw_values is not None:
            values = _unique(
                _as_sequence(raw_values, f"slot {signal!r} values"),
                f"slot {signal!r} categorical values",
            )

        if kind in ("real", "integer"):
            if not has_lower or not has_upper:
                _fail(f"slot {signal!r} requires both finite lower and upper bounds")
            lower = _finite_number(lower, f"slot {signal!r} lower bound")
            upper = _finite_number(upper, f"slot {signal!r} upper bound")
            if lower > upper:
                _fail(f"slot {signal!r} has reversed bounds: {lower!r} > {upper!r}")
            if kind == "integer" and (
                not float(lower).is_integer() or not float(upper).is_integer()
            ):
                _fail(f"slot {signal!r} integer bounds must be integers")
            if values:
                _fail(f"slot {signal!r} cannot declare categorical values for type {kind!r}")
        elif kind == "boolean":
            if values and set(values) != {False, True}:
                _fail(f"slot {signal!r} boolean values must be exactly false and true")
            values = (False, True)
            if has_lower or has_upper:
                lower = _finite_number(lower, f"slot {signal!r} lower bound")
                upper = _finite_number(upper, f"slot {signal!r} upper bound")
                if lower > upper:
                    _fail(f"slot {signal!r} has reversed bounds")
        else:
            if not values:
                _fail(f"slot {signal!r} requires a non-empty finite values list")
            if kind == "categorical":
                for code in values:
                    _finite_number(code, f"slot {signal!r} categorical code")
                if not has_lower or not has_upper:
                    _fail(
                        f"slot {signal!r} categorical values require finite lower and upper bounds"
                    )
                lower = _finite_number(lower, f"slot {signal!r} lower bound")
                upper = _finite_number(upper, f"slot {signal!r} upper bound")
                if lower > upper:
                    _fail(f"slot {signal!r} has reversed bounds")
                if any(code < lower or code > upper for code in values):
                    _fail(f"slot {signal!r} has a categorical code outside its bounds")
            if kind == "string-enum" and (has_lower or has_upper):
                _fail(f"slot {signal!r} string-enum cannot have numeric bounds")

        raw_tokens = value.get("value_to_token", value.get("tokens", {}))
        if raw_tokens is None:
            raw_tokens = {}
        if not isinstance(raw_tokens, Mapping):
            _fail(f"slot {signal!r} value_to_token must be a mapping")
        tokens = dict(raw_tokens)
        if tokens:
            if set(tokens) != set(values):
                _fail(f"slot {signal!r} value_to_token must cover every finite value exactly")
            for token in tokens.values():
                _nonempty_string(token, f"slot {signal!r} rendered token")
        elif values and "template" in value:
            _fail(f"slot {signal!r} has a template but no total value_to_token mapping")
        return cls(signal, kind, lower, upper, values, MappingProxyType(tokens))


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    """Immutable template metadata and its exact placeholder-to-slot map."""

    text: str | None
    identifier: str | None
    placeholders: Mapping[str, str]
    repetitions: Mapping[str, int]
    escaping: str

    @classmethod
    def from_value(cls, value: Any, signals: set[str]) -> "TemplateSpec":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            raw: Mapping[str, Any] = {"text": value}
        elif isinstance(value, Mapping):
            raw = value
        else:
            _fail("template must be text or a mapping")
        text = raw.get("text", raw.get("template"))
        identifier = raw.get("identifier", raw.get("digest"))
        if text is not None:
            text = _nonempty_string(text, "template text")
        if identifier is not None:
            identifier = _nonempty_string(identifier, "template identifier")
        if text is None and identifier is None:
            _fail("template requires immutable text or an identifier/digest")
        if text is not None and identifier is not None:
            _fail("template cannot provide both text and identifier")

        parsed = [match.group(1) for match in _PLACEHOLDER.finditer(text or "")]
        repetitions_raw = raw.get("repetitions", raw.get("repeat", {}))
        if repetitions_raw is None:
            repetitions_raw = {}
        if not isinstance(repetitions_raw, Mapping):
            _fail("template repetitions must be a mapping")
        repetitions: dict[str, int] = {}
        for placeholder, count in repetitions_raw.items():
            _nonempty_string(placeholder, "template repetition placeholder")
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                _fail(f"template repetition for {placeholder!r} must be a positive integer")
            repetitions[placeholder] = count

        explicit = raw.get("placeholders")
        if explicit is None:
            mapping = {name: name for name in parsed}
        else:
            if not isinstance(explicit, Mapping):
                _fail("template placeholders must be a mapping")
            mapping = {}
            for placeholder, signal in explicit.items():
                _nonempty_string(placeholder, "template placeholder")
                mapping[placeholder] = _nonempty_string(signal, "template placeholder signal")
        if set(mapping.values()) - signals:
            unknown = sorted(set(mapping.values()) - signals)
            _fail(f"template refers to undeclared input slot(s): {', '.join(unknown)}")
        if set(mapping) - set(parsed) and text is not None:
            _fail("template placeholder map contains a placeholder absent from template text")
        if text is not None:
            counts = {name: parsed.count(name) for name in set(parsed)}
            if set(counts) != set(mapping):
                missing = sorted(set(mapping) - set(counts))
                extra = sorted(set(counts) - set(mapping))
                _fail(
                    f"template placeholder map does not match text "
                    f"(missing={missing}, extra={extra})"
                )
            for placeholder, count in counts.items():
                expected = repetitions.get(placeholder, 1)
                if count != expected:
                    _fail(
                        f"template placeholder {placeholder!r} occurs {count} times; "
                        f"expected {expected}"
                    )
        elif not mapping:
            _fail("identifier-only template requires an explicit placeholder map")
        if set(mapping.values()) != signals:
            missing = sorted(signals - set(mapping.values()))
            _fail(f"template does not expose slot(s): {', '.join(missing)}")
        escaping = raw.get("escaping", "literal")
        if escaping not in ("literal", "json", "url"):
            _fail(f"unsupported template escaping mode {escaping!r}")
        return cls(
            text,
            identifier,
            MappingProxyType(mapping),
            MappingProxyType(repetitions),
            escaping,
        )


@dataclass(frozen=True, slots=True)
class DeclaredInputSpace:
    """A finite, typed, renderable domain for replayable inputs."""

    schema_version: int
    slots: tuple[InputSlot, ...]
    constraints: tuple[Mapping[str, Any], ...]
    template: TemplateSpec | None
    outcomes: Mapping[str, str]

    def __init__(
        self,
        slots: Sequence[Any],
        *,
        schema_version: int = SUPPORTED_SCHEMA_VERSION,
        constraints: Sequence[Any] = (),
        template: Any = None,
        outcomes: Mapping[str, str] | None = None,
    ):
        _schema_version(schema_version, "DeclaredInputSpace schema version")
        raw_slots = _as_sequence(slots, "input-space slots")
        normalized_slots = tuple(InputSlot.from_value(slot) for slot in raw_slots)
        names = [slot.signal for slot in normalized_slots]
        if len(set(names)) != len(names):
            _fail("input-space slots contain duplicate signal names")
        signal_names = set(names)
        normalized_constraints: list[Mapping[str, Any]] = []
        for constraint in _as_sequence(constraints, "input-space constraints"):
            if not isinstance(constraint, Mapping):
                _fail("each input-space constraint must be a mapping")
            op = constraint.get("op", constraint.get("operator"))
            if op not in ("<", "<=", "=", "==", ">=", ">"):
                _fail(f"unsupported input-space constraint operator {op!r}")
            if "signal" in constraint:
                signal = _nonempty_string(constraint.get("signal"), "constraint.signal")
                if signal not in signal_names:
                    _fail(f"constraint refers to undeclared input slot {signal!r}")
                if "value" not in constraint:
                    _fail("input-space constraint is missing value")
                value = _finite_number(constraint["value"], "constraint value")
                normalized = {"signal": signal, "op": op, "value": value}
            elif "left" in constraint and "right" in constraint:
                left = _nonempty_string(constraint["left"], "constraint.left")
                right = _nonempty_string(constraint["right"], "constraint.right")
                if left not in signal_names or right not in signal_names:
                    _fail("cross-input constraint refers to an undeclared input slot")
                normalized = {"left": left, "op": op, "right": right}
            else:
                _fail("input-space constraint needs signal/value or left/right")
            normalized_constraints.append(MappingProxyType(normalized))
        parsed_template = (
            None if template is None else TemplateSpec.from_value(template, signal_names)
        )
        if parsed_template is not None:
            for slot in normalized_slots:
                if (
                    slot.kind in ("categorical", "boolean", "string-enum")
                    and not slot.value_to_token
                ):
                    _fail(
                        f"slot {slot.signal!r} needs a total value_to_token mapping "
                        "for its template"
                    )
        raw_outcomes = {} if outcomes is None else outcomes
        if not isinstance(raw_outcomes, Mapping):
            _fail("input-space outcomes must be a mapping")
        normalized_outcomes: dict[str, str] = {}
        for signal, record_field in raw_outcomes.items():
            _nonempty_string(signal, "outcome signal")
            normalized_outcomes[signal] = _nonempty_string(record_field, "outcome record field")
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "slots", normalized_slots)
        object.__setattr__(self, "constraints", tuple(normalized_constraints))
        object.__setattr__(self, "template", parsed_template)
        object.__setattr__(self, "outcomes", MappingProxyType(normalized_outcomes))

    @classmethod
    def from_value(cls, value: Any) -> "DeclaredInputSpace":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            _fail("input_space must be a DeclaredInputSpace or mapping")
        payload = dict(value)
        return cls(**payload)

    @property
    def signals(self) -> tuple[str, ...]:
        return tuple(slot.signal for slot in self.slots)

    def slot(self, signal: str) -> InputSlot:
        for slot in self.slots:
            if slot.signal == signal:
                return slot
        raise KeyError(signal)


@dataclass(frozen=True, slots=True)
class OutputDecoder:
    """A total scalar decoder declaration used by an ONNX output binding."""

    kind: str
    threshold: float | None
    low: Any
    high: Any
    tie: Any
    classes: tuple[Any, ...]

    @classmethod
    def from_value(cls, value: Any, signal: str) -> "OutputDecoder":
        if not isinstance(value, Mapping):
            _fail(f"decoder for output signal {signal!r} must be a total mapping")
        kind = value.get("kind", "threshold")
        if kind == "threshold":
            for key in ("threshold", "low", "high", "tie"):
                if key not in value:
                    _fail(f"threshold decoder for {signal!r} is missing {key!r}")
            threshold = _finite_number(value["threshold"], f"decoder {signal!r} threshold")
            return cls(
                kind,
                float(threshold),
                _freeze(value["low"]),
                _freeze(value["high"]),
                _freeze(value["tie"]),
                (),
            )
        if kind == "argmax":
            classes = _unique(
                _as_sequence(value.get("classes"), f"decoder {signal!r} classes"),
                f"decoder {signal!r} classes",
            )
            if not classes or "tie" not in value:
                _fail(f"argmax decoder for {signal!r} must declare classes and tie behavior")
            return cls(kind, None, None, None, _freeze(value["tie"]), _freeze(classes))
        _fail(f"unsupported decoder kind {kind!r} for output signal {signal!r}")


def _dtype_name(elem_type: int) -> str:
    if TensorProto is None:
        return str(elem_type)
    name = TensorProto.DataType.Name(elem_type).lower()
    aliases = {
        "float": "float32",
        "double": "float64",
        "int32": "int32",
        "int64": "int64",
        "uint32": "uint32",
        "uint64": "uint64",
        "bool": "bool",
    }
    return aliases.get(name, name)


def _normalize_dtype(value: Any) -> str:
    value = _nonempty_string(value, "tensor dtype").lower()
    return {"float": "float32", "double": "float64", "int": "int32"}.get(value, value)


def _tensor_shape(value: Any, label: str) -> tuple[int, ...]:
    shape = _as_sequence(value, f"{label} shape")
    result: list[int] = []
    for index, dimension in enumerate(shape):
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0:
            _fail(f"{label} has dynamic or non-positive query dimension at index {index}")
        result.append(dimension)
    return tuple(result)


def _declared_coordinates(
    declaration: Mapping[str, Any], shape: tuple[int, ...], label: str
) -> dict[str, tuple[int, ...]]:
    raw = declaration.get("signal_map", declaration.get("signals", declaration.get("coordinates")))
    if raw is None and declaration.get("signal") is not None:
        raw = {declaration["signal"]: 0}
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        _fail(f"{label} signal_map must be a mapping")
    total = math.prod(shape) if shape else 1
    result: dict[str, tuple[int, ...]] = {}
    used: set[int] = set()
    for signal, coordinate in raw.items():
        signal = _nonempty_string(signal, f"{label} signal name")
        if isinstance(coordinate, int) and not isinstance(coordinate, bool):
            flat = coordinate
            coords = (coordinate,)
        else:
            coords = _as_sequence(coordinate, f"{label} coordinate for {signal!r}")
            if len(coords) != len(shape):
                _fail(f"{label} coordinate for {signal!r} has wrong rank")
            if any(isinstance(item, bool) or not isinstance(item, int) for item in coords):
                _fail(f"{label} coordinate for {signal!r} must contain integers")
            flat = 0
            for item, extent in zip(coords, shape, strict=True):
                if item < 0 or item >= extent:
                    _fail(f"{label} coordinate for {signal!r} is outside tensor shape")
                flat = flat * extent + item
        if flat < 0 or flat >= total:
            _fail(f"{label} coordinate for {signal!r} is outside tensor shape")
        if flat in used:
            _fail(f"{label} signal-to-coordinate map is not injective")
        used.add(flat)
        result[signal] = coords
    return result


@dataclass(frozen=True, slots=True)
class TensorBinding:
    name: str
    shape: tuple[int, ...]
    dtype: str
    coordinates: Mapping[str, tuple[int, ...]]
    decoders: Mapping[str, OutputDecoder]


@dataclass(frozen=True, slots=True)
class OnnxArtifact:
    """Validated, immutable, model-global ONNX exposure (schema version 1)."""

    family: str
    schema_version: int
    model: bytes
    model_sha256: str
    onnx_ir_version: int
    opset_imports: tuple[tuple[str, int], ...]
    inputs: tuple[TensorBinding, ...]
    outputs: tuple[TensorBinding, ...]
    input_space: DeclaredInputSpace
    vnnlib_version: str
    preprocessing: Any
    postprocessing: Any
    deployed_model_id: str | None

    def __init__(
        self,
        model: bytes | bytearray | memoryview | None = None,
        *,
        model_bytes: bytes | None = None,
        inputs: Sequence[Any],
        outputs: Sequence[Any],
        input_space: DeclaredInputSpace | Mapping[str, Any],
        family: str = "onnx-vnnlib",
        schema_version: int = SUPPORTED_SCHEMA_VERSION,
        model_sha256: str | None = None,
        onnx_ir_version: int | None = None,
        opset_imports: Sequence[Any] | None = None,
        vnnlib_version: str = "1.0",
        preprocessing: Any = "included",
        postprocessing: Any = "none",
        deployed_model_id: str | None = None,
    ):
        if family != "onnx-vnnlib":
            _fail(f"unsupported ONNX artifact family {family!r}")
        _schema_version(schema_version, "OnnxArtifact schema version")
        if vnnlib_version not in SUPPORTED_VNNLIB_VERSIONS:
            _fail(f"unsupported VNN-LIB version {vnnlib_version!r}")
        if model is not None and model_bytes is not None:
            _fail("provide model bytes once, not both model and model_bytes")
        raw_model = model if model is not None else model_bytes
        if not isinstance(raw_model, (bytes, bytearray, memoryview)):
            _fail("OnnxArtifact requires embedded model bytes; external model paths are refused")
        model_data = bytes(raw_model)
        if onnx is None or checker is None or TensorProto is None:
            _fail(
                "ONNX validation requires the onnx package; install it with "
                "pip install 'reasonsmith[neural]'"
            )
        try:
            parsed = onnx.load_model_from_string(model_data)
        except Exception as exc:
            _fail(f"malformed ONNX model: {exc}")

        def reject_external(tensor: Any) -> None:
            if tensor.data_location == TensorProto.EXTERNAL or tensor.external_data:
                _fail(
                    "external ONNX tensor data is refused; embed every initializer in model bytes"
                )

        for initializer in parsed.graph.initializer:
            reject_external(initializer)
        for sparse in parsed.graph.sparse_initializer:
            reject_external(sparse.values)
        for node in parsed.graph.node:
            for attribute in node.attribute:
                if attribute.HasField("t"):
                    reject_external(attribute.t)
                for tensor in attribute.tensors:
                    reject_external(tensor)
        try:
            checker.check_model(parsed, full_check=True)
        except Exception as exc:
            _fail(f"malformed ONNX model: {exc}")
        if not parsed.ir_version:
            _fail("ONNX model must declare an IR version")
        if not parsed.opset_import:
            _fail("ONNX model must declare at least one opset import")
        if any(node.domain not in SUPPORTED_OPSET_DOMAINS for node in parsed.graph.node):
            _fail("custom ONNX operator domains are not supported in schema version 1")
        actual_digest = hashlib.sha256(model_data).hexdigest()
        if model_sha256 is not None and model_sha256 != actual_digest:
            _fail("model_sha256 does not match embedded ONNX bytes")

        actual_ir = int(parsed.ir_version)
        if onnx_ir_version is not None and onnx_ir_version != actual_ir:
            _fail(f"declared ONNX IR version {onnx_ir_version} does not match model {actual_ir}")
        actual_opsets = tuple(
            sorted((item.domain, int(item.version)) for item in parsed.opset_import)
        )
        if any(domain not in SUPPORTED_OPSET_DOMAINS for domain, _ in actual_opsets):
            _fail("custom ONNX operator domains are not supported in schema version 1")
        if opset_imports is not None:
            supplied: list[tuple[str, int]] = []
            for item in opset_imports:
                if isinstance(item, Mapping):
                    domain = item.get("domain", "")
                    version = item.get("version")
                else:
                    pair = _as_sequence(item, "opset import")
                    if len(pair) != 2:
                        _fail("opset import must contain domain and version")
                    domain, version = pair
                if not isinstance(domain, str):
                    _fail("opset domain must be a string")
                if isinstance(version, bool) or not isinstance(version, int):
                    _fail("opset version must be an integer")
                supplied.append((domain, version))
            if tuple(sorted(supplied)) != actual_opsets:
                _fail("declared opset_imports do not match the ONNX model")

        graph_inputs = {value.name: value for value in parsed.graph.input}
        graph_outputs = {value.name: value for value in parsed.graph.output}
        raw_inputs = _as_sequence(inputs, "ONNX inputs")
        raw_outputs = _as_sequence(outputs, "ONNX outputs")
        if not raw_inputs or not raw_outputs:
            _fail("OnnxArtifact requires at least one declared input and output")

        def bind(raw: Any, graph: Mapping[str, Any], label: str, output: bool) -> TensorBinding:
            if not isinstance(raw, Mapping):
                _fail(f"each ONNX {label} declaration must be a mapping")
            name = _nonempty_string(
                raw.get("name", raw.get("tensor_name", raw.get("tensor"))),
                f"{label}.name",
            )
            if name not in graph:
                _fail(f"unknown ONNX {label} tensor name {name!r}")
            tensor = graph[name]
            try:
                tensor_type = tensor.type.tensor_type
                actual_shape: list[int] = []
                for index, dim in enumerate(tensor_type.shape.dim):
                    if dim.dim_value <= 0:
                        _fail(
                            f"{label} tensor {name!r} has dynamic query dimension at index {index}"
                        )
                    actual_shape.append(int(dim.dim_value))
                shape = tuple(actual_shape)
            except AttributeError:
                _fail(f"{label} tensor {name!r} is not a typed tensor")
            declared_shape = raw.get("shape", shape)
            if tuple(_tensor_shape(declared_shape, f"{label} {name!r}")) != shape:
                _fail(f"declared shape for {label} tensor {name!r} does not match ONNX")
            actual_dtype = _dtype_name(tensor_type.elem_type)
            dtype = _normalize_dtype(raw.get("dtype", actual_dtype))
            if dtype != actual_dtype:
                _fail(f"declared dtype for {label} tensor {name!r} does not match ONNX")
            coordinates = _declared_coordinates(raw, shape, f"{label} {name!r}")
            decoders: dict[str, OutputDecoder] = {}
            if output:
                raw_decoders = raw.get("decoders", raw.get("decoder", {})) or {}
                if not isinstance(raw_decoders, Mapping):
                    _fail(f"output {name!r} decoders must be a mapping")
                if "kind" in raw_decoders:
                    if len(coordinates) != 1:
                        _fail(
                            f"output {name!r} has a scalar decoder but does not declare "
                            "exactly one output signal"
                        )
                    only_signal = next(iter(coordinates))
                    raw_decoders = {only_signal: raw_decoders}
                for signal, decoder in raw_decoders.items():
                    if signal not in coordinates:
                        _fail(f"decoder for undeclared output signal {signal!r}")
                    decoders[signal] = OutputDecoder.from_value(decoder, signal)
                missing = set(coordinates) - set(decoders)
                if missing and postprocessing != "included":
                    _fail(f"output {name!r} has partial decoders; missing {sorted(missing)!r}")
                if coordinates and missing and postprocessing == "included":
                    # Included post-processing is the explicit escape hatch for a deterministic
                    # decoder represented by the graph rather than a Python declaration.
                    pass
            elif raw.get("decoder") is not None:
                _fail("decoders are valid only on output declarations")
            return TensorBinding(
                name,
                shape,
                dtype,
                MappingProxyType(coordinates),
                MappingProxyType(decoders),
            )

        normalized_inputs = tuple(bind(raw, graph_inputs, "input", False) for raw in raw_inputs)
        normalized_outputs = tuple(bind(raw, graph_outputs, "output", True) for raw in raw_outputs)
        if len({item.name for item in normalized_inputs}) != len(normalized_inputs):
            _fail("duplicate ONNX input tensor declaration")
        if len({item.name for item in normalized_outputs}) != len(normalized_outputs):
            _fail("duplicate ONNX output tensor declaration")
        initializer_names = {item.name for item in parsed.graph.initializer}
        if {item.name for item in normalized_inputs} != set(graph_inputs) - initializer_names:
            _fail("ONNX input declarations must cover every non-initializer graph input")
        if {item.name for item in normalized_outputs} != set(graph_outputs):
            _fail("ONNX output declarations must cover every graph output")
        space = DeclaredInputSpace.from_value(input_space)
        input_signals = [signal for item in normalized_inputs for signal in item.coordinates]
        if len(input_signals) != len(set(input_signals)):
            _fail("input signal-to-coordinate map is not injective across tensors")
        if set(input_signals) != set(space.signals):
            _fail("ONNX input coordinate map must cover exactly the DeclaredInputSpace signals")
        output_signals = [signal for item in normalized_outputs for signal in item.coordinates]
        if len(output_signals) != len(set(output_signals)):
            _fail("output signal-to-coordinate map is not injective across tensors")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "model", model_data)
        object.__setattr__(self, "model_sha256", actual_digest)
        object.__setattr__(self, "onnx_ir_version", actual_ir)
        object.__setattr__(self, "opset_imports", actual_opsets)
        object.__setattr__(self, "inputs", normalized_inputs)
        object.__setattr__(self, "outputs", normalized_outputs)
        object.__setattr__(self, "input_space", space)
        object.__setattr__(self, "vnnlib_version", vnnlib_version)
        object.__setattr__(self, "preprocessing", _freeze(preprocessing))
        object.__setattr__(self, "postprocessing", _freeze(postprocessing))
        object.__setattr__(
            self,
            "deployed_model_id",
            None
            if deployed_model_id is None
            else _nonempty_string(deployed_model_id, "deployed_model_id"),
        )

    @staticmethod
    def from_value(value: Any) -> "OnnxArtifact":
        if isinstance(value, OnnxArtifact):
            return value
        if not isinstance(value, Mapping):
            _fail("ONNX artifact exposure must be an OnnxArtifact or mapping")
        return OnnxArtifact(**value)


__all__ = [
    "SUPPORTED_SCHEMA_VERSION",
    "SUPPORTED_VNNLIB_VERSIONS",
    "InputSlot",
    "TemplateSpec",
    "DeclaredInputSpace",
    "OutputDecoder",
    "TensorBinding",
    "OnnxArtifact",
]
