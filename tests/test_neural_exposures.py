"""Slice-1 typed neural exposure validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

pytest.importorskip("onnx")
import onnx  # noqa: E402
from onnx import TensorProto, helper  # noqa: E402

import reasonsmith.neural as neural
from reasonsmith.artifacts.onnx import OnnxArtifact as ForwardedOnnxArtifact
from reasonsmith.neural import DeclaredInputSpace, InputSlot, OnnxArtifact, TemplateSpec
from reasonsmith.rulelang import UnsupportedConstructError, _normalize_tokens_for_read_whole
from reasonsmith.sut import NeuralExposures, SystemUnderTest


def _model(
    *,
    dynamic: bool = False,
    external: bool = False,
    extra_input: bool = False,
    extra_output: bool = False,
) -> bytes:
    dimension = "batch" if dynamic else 1
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [dimension, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [dimension, 2])
    inputs = [x]
    outputs = [y]
    nodes = [helper.make_node("Identity", ["x"], ["y"])]
    if extra_input:
        x2 = helper.make_tensor_value_info("x2", TensorProto.FLOAT, [dimension, 2])
        inputs.append(x2)
        nodes.append(helper.make_node("Identity", ["x2"], ["z"]))
    if extra_output:
        z = helper.make_tensor_value_info("z", TensorProto.FLOAT, [dimension, 2])
        outputs.append(z)
        nodes.append(helper.make_node("Identity", ["x"], ["z"]))
    graph = helper.make_graph(nodes, "model", inputs, outputs)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    if external:
        initializer = helper.make_tensor("weights", TensorProto.FLOAT, [1], [1.0])
        initializer.data_location = TensorProto.EXTERNAL
        initializer.external_data.add(key="location", value="weights.bin")
        model.graph.initializer.append(initializer)
    return model.SerializeToString()


def _space(**slot: object) -> DeclaredInputSpace:
    slots = [
        {"signal": "first", "type": "real", "lower": 0, "upper": 1},
        {"signal": "second", "type": "real", "lower": 0, "upper": 1},
    ]
    if slot:
        slots[0].update(slot)
    return DeclaredInputSpace(slots)


def _artifact(**overrides: object) -> OnnxArtifact:
    kwargs: dict[str, object] = {
        "model": _model(),
        "inputs": [{"name": "x", "signal_map": {"first": 0, "second": 1}}],
        "outputs": [
            {
                "name": "y",
                "signal_map": {"score": 0},
                "decoder": {
                    "kind": "threshold",
                    "threshold": 0.5,
                    "low": "no",
                    "high": "yes",
                    "tie": "yes",
                },
            }
        ],
        "input_space": _space(),
    }
    kwargs.update(overrides)
    return OnnxArtifact(**kwargs)


def test_valid_exposure_is_frozen_and_digest_is_derived() -> None:
    artifact = _artifact()
    assert artifact.family == "onnx-vnnlib"
    assert len(artifact.model_sha256) == 64
    assert isinstance(artifact.inputs, tuple)
    with pytest.raises(FrozenInstanceError):
        artifact.family = "other"  # type: ignore[misc]


@pytest.mark.parametrize("schema", [0, 2, "1"])
def test_unsupported_schema_versions_are_refused(schema: object) -> None:
    with pytest.raises(ValueError, match="schema version"):
        _artifact(schema_version=schema)
    with pytest.raises(ValueError, match="schema version"):
        DeclaredInputSpace([], schema_version=schema)  # type: ignore[arg-type]


def test_malformed_model_and_external_data_are_refused() -> None:
    with pytest.raises(ValueError, match="malformed ONNX"):
        _artifact(model=b"not an ONNX model")
    with pytest.raises(ValueError, match="external ONNX"):
        _artifact(model=_model(external=True))


def test_unknown_tensor_and_dynamic_dimensions_are_refused() -> None:
    with pytest.raises(ValueError, match="unknown ONNX input tensor"):
        _artifact(inputs=[{"name": "missing", "signal_map": {"first": 0, "second": 1}}])
    with pytest.raises(ValueError, match="dynamic query dimension"):
        _artifact(model=_model(dynamic=True))


@pytest.mark.parametrize(
    "slot",
    [
        {"lower": None},
        {"upper": None},
        {"lower": float("nan")},
        {"upper": float("inf")},
        {"lower": 2, "upper": 1},
    ],
)
def test_bad_bounds_are_refused(slot: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _space(**slot)


def test_categorical_codes_are_distinct_and_bounded() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        DeclaredInputSpace(
            [{"signal": "basis", "type": "categorical", "lower": 0, "upper": 1, "values": [0, 0]}]
        )
    with pytest.raises(ValueError, match="outside"):
        DeclaredInputSpace(
            [{"signal": "basis", "type": "categorical", "lower": 0, "upper": 1, "values": [0, 2]}]
        )


def test_partial_decoder_is_refused() -> None:
    with pytest.raises(ValueError, match="partial decoders"):
        _artifact(
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0, "other": 1},
                    "decoder": {
                        "score": {
                            "kind": "threshold",
                            "threshold": 0.5,
                            "low": "no",
                            "high": "yes",
                            "tie": "yes",
                        }
                    },
                }
            ]
        )


def test_template_rejects_undeclared_and_repeated_placeholders() -> None:
    with pytest.raises(ValueError, match="undeclared"):
        DeclaredInputSpace(
            [{"signal": "first", "type": "real", "lower": 0, "upper": 1}],
            template="first={first}; extra={unknown}",
        )
    with pytest.raises(ValueError, match="occurs"):
        DeclaredInputSpace(
            [{"signal": "first", "type": "real", "lower": 0, "upper": 1}],
            template="first={first} again={first}",
        )


def test_optional_hooks_remain_optional_and_protocol_is_additive() -> None:
    class Existing:
        def capabilities(self):
            return set()

        def decisions(self):
            return []

        def logic(self):
            return None

    class Neural(Existing):
        def artifact(self, decision=None):
            return artifact if decision is None else None

        def input_space(self):
            return artifact.input_space

    artifact = _artifact()
    assert isinstance(Existing(), SystemUnderTest)
    assert isinstance(Neural(), SystemUnderTest)
    assert isinstance(Neural(), NeuralExposures)
    assert Neural().artifact(None) is artifact


@pytest.mark.parametrize(
    "slot",
    [
        {"signal": "", "type": "real", "lower": 0, "upper": 1},
        {"signal": "x", "type": "wat", "lower": 0, "upper": 1},
        {"signal": "x", "type": "real", "lower": 0},
        {"signal": "x", "type": "integer", "lower": 0.5, "upper": 1.5},
        {"signal": "x", "type": "real", "lower": 0, "upper": 1, "values": [0]},
        {"signal": "x", "type": "boolean", "values": [True]},
        {"signal": "x", "type": "boolean", "lower": 2, "upper": 1},
        {"signal": "x", "type": "categorical", "lower": 0, "upper": 1},
        {"signal": "x", "type": "categorical", "lower": 0, "upper": 1, "values": [float("inf")]},
        {
            "signal": "x",
            "type": "categorical",
            "lower": 2,
            "upper": 1,
            "values": [0],
        },
        {
            "signal": "x",
            "type": "categorical",
            "lower": 0,
            "upper": 1,
            "values": [0, 2],
        },
        {"signal": "x", "type": "string-enum", "values": ["a"], "lower": 0, "upper": 1},
        {"signal": "x", "type": "string-enum", "values": []},
        {"signal": "x", "type": "real", "lower": 0, "upper": 1, "tokens": []},
    ],
)
def test_input_slot_validation_rejects_malformed_declarations(slot: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        DeclaredInputSpace([slot])


def test_input_space_constraints_outcomes_and_template_forms() -> None:
    with pytest.raises(ValueError):
        DeclaredInputSpace("not slots")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        DeclaredInputSpace([{"signal": "x", "type": "real", "lower": 0, "upper": 1}] * 2)
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            constraints=["bad"],
        )
    base = [{"signal": "x", "type": "real", "lower": 0, "upper": 1}]
    for constraint in (
        {"op": "<=", "value": 1},
        {"signal": "unknown", "op": "<=", "value": 1},
        {"signal": "x", "op": "<="},
        {"signal": "x", "op": "<=", "value": float("nan")},
        {"left": "unknown", "right": "x", "op": "<="},
        {"left": "x", "right": "x"},
    ):
        with pytest.raises(ValueError):
            DeclaredInputSpace(base, constraints=[constraint])
    space = DeclaredInputSpace(
        base,
        constraints=[{"signal": "x", "op": ">=", "value": 0}],
        outcomes={"decision": "artifact_logs_decision_record"},
    )
    assert space.outcomes["decision"] == "artifact_logs_decision_record"
    with pytest.raises(ValueError):
        DeclaredInputSpace(base, outcomes=["bad"])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        DeclaredInputSpace(base, outcomes={"": "field"})
    with pytest.raises(ValueError):
        DeclaredInputSpace(base, outcomes={"decision": ""})
    assert DeclaredInputSpace.from_value({"slots": base}).signals == ("x",)
    with pytest.raises(ValueError):
        DeclaredInputSpace.from_value("bad")
    with pytest.raises(KeyError):
        space.slot("missing")


def test_template_and_decoder_validation_branches() -> None:
    slot = [{"signal": "x", "type": "real", "lower": 0, "upper": 1}]
    bad_templates = [
        1,
        {},
        {"text": "x={x}", "identifier": "digest"},
        {"text": "x={x}", "escaping": "shell"},
        {"text": "x={x}", "repetitions": []},
        {"text": "x={x}", "repetitions": {"x": 0}},
        {"text": "x={x}", "placeholders": []},
        {"text": "x={x}", "placeholders": {"other": "x"}},
        {"text": "x={x}", "placeholders": {"x": "unknown"}},
        {"text": "x={x}{x}"},
        {"identifier": "digest"},
    ]
    for template in bad_templates:
        with pytest.raises(ValueError):
            DeclaredInputSpace(slot, template=template)
    identifier = DeclaredInputSpace(
        slot,
        template={"identifier": "sha256:abc", "placeholders": {"x": "x"}},
    )
    assert identifier.template is not None
    categorical = DeclaredInputSpace(
        [
            {
                "signal": "kind",
                "type": "categorical",
                "lower": 0,
                "upper": 1,
                "values": [0, 1],
                "value_to_token": {0: "zero", 1: "one"},
            }
        ],
        template="kind={kind}",
    )
    assert categorical.slot("kind").type == "categorical"
    for decoder in (
        None,
        {},
        {"kind": "threshold"},
        {"kind": "threshold", "threshold": float("nan"), "low": 0, "high": 1, "tie": 1},
        {"kind": "unknown"},
    ):
        with pytest.raises(ValueError):
            _artifact(outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": decoder}])
    with pytest.raises(ValueError):
        _artifact(
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0},
                    "decoder": {"other": {"kind": "argmax", "classes": ["a"], "tie": "a"}},
                }
            ]
        )
    with pytest.raises(ValueError):
        _artifact(
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0, "other": 1},
                    "decoder": {"kind": "threshold", "threshold": 0, "low": 0, "high": 1, "tie": 1},
                }
            ]
        )
    argmax = _artifact(
        outputs=[
            {
                "name": "y",
                "signal_map": {"score": 0},
                "decoder": {"kind": "argmax", "classes": ["a", "b"], "tie": "a"},
            }
        ]
    )
    assert argmax.outputs[0].decoders["score"].kind == "argmax"


def test_artifact_metadata_and_tensor_mapping_validation() -> None:
    for kwargs in (
        {"family": "other"},
        {"vnnlib_version": "2.0"},
        {"model": _model(), "model_bytes": _model()},
        {"model": None},
        {"model_sha256": "wrong"},
        {"onnx_ir_version": 999},
        {"opset_imports": [("", 12)]},
        {"inputs": []},
        {"outputs": []},
        {"inputs": ["bad"]},
        {"inputs": [{"name": "x", "shape": [2, 2], "signal_map": {"first": 0, "second": 1}}]},
        {"inputs": [{"name": "x", "dtype": "int64", "signal_map": {"first": 0, "second": 1}}]},
        {"inputs": [{"name": "x", "signal_map": {"first": 0, "second": 0}}]},
        {"inputs": [{"name": "x", "signal_map": {"first": [0], "second": [0, 1]}}]},
        {"inputs": [{"name": "x", "signal_map": {"first": 99, "second": 1}}]},
        {
            "inputs": [{"name": "x", "signal_map": {"first": 0, "second": 1}}],
            "input_space": DeclaredInputSpace(
                [{"signal": "only", "type": "real", "lower": 0, "upper": 1}]
            ),
        },
        {"outputs": [{"name": "y", "signal_map": {"score": 0}}]},
        {
            "outputs": [
                {
                    "name": "y",
                    "signal_map": {"score": 0},
                    "decoder": {
                        "score": {
                            "kind": "threshold",
                            "threshold": 0,
                            "low": 0,
                            "high": 1,
                            "tie": 1,
                        },
                        "other": {
                            "kind": "threshold",
                            "threshold": 0,
                            "low": 0,
                            "high": 1,
                            "tie": 1,
                        },
                    },
                }
            ]
        },
    ):
        with pytest.raises(ValueError):
            _artifact(**kwargs)
    with pytest.raises(ValueError):
        _artifact(
            inputs=[
                {"name": "x", "signal_map": {"first": 0, "second": 1}},
                {"name": "x", "signal_map": {"first": 0, "second": 1}},
            ]
        )
    with pytest.raises(ValueError):
        _artifact(
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0},
                    "decoder": {"kind": "threshold", "threshold": 0, "low": 0, "high": 1, "tie": 1},
                },
                {
                    "name": "y",
                    "signal_map": {"other": 0},
                    "decoder": {"kind": "threshold", "threshold": 0, "low": 0, "high": 1, "tie": 1},
                },
            ]
        )
    with pytest.raises(ValueError):
        _artifact(
            inputs=[{"name": "x", "signal_map": {"first": 0, "second": 1, "third": 0}}],
            input_space=_space(),
        )
    with pytest.raises(ValueError):
        _artifact(
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0, "other": 0},
                    "decoder": {
                        "score": {
                            "kind": "threshold",
                            "threshold": 0,
                            "low": 0,
                            "high": 1,
                            "tie": 1,
                        },
                        "other": {
                            "kind": "threshold",
                            "threshold": 0,
                            "low": 0,
                            "high": 1,
                            "tie": 1,
                        },
                    },
                }
            ]
        )


def test_remaining_neural_validation_paths_are_exercised() -> None:
    assert ForwardedOnnxArtifact is OnnxArtifact
    assert isinstance(DeclaredInputSpace([InputSlot("x", "real", 0, 1)]).slot("x"), InputSlot)
    for slot in (1, object()):
        with pytest.raises(ValueError):
            DeclaredInputSpace([slot])
    with pytest.raises(ValueError):
        DeclaredInputSpace([{"signal": "kind", "type": "categorical", "values": [0, 1]}])
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [
                {
                    "signal": "kind",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 1,
                    "values": [0, 1],
                    "value_to_token": {0: "zero"},
                }
            ]
        )
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [
                {
                    "signal": "kind",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 1,
                    "values": [0, 1],
                    "value_to_token": {0: "zero", 1: ""},
                }
            ]
        )
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [
                {
                    "signal": "kind",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 1,
                    "values": [0, 1],
                }
            ],
            template="kind={kind}",
        )
    frozen = _artifact(
        preprocessing={"steps": ["scale"], "flags": {"a"}},
        postprocessing={"steps": ("decode",)},
    )
    assert frozen.preprocessing["steps"] == ("scale",)
    assert frozen.preprocessing["flags"] == frozenset({"a"})
    with pytest.raises(ValueError):
        InputSlot.from_value(
            {
                "signal": "x",
                "type": "categorical",
                "lower": 0,
                "upper": 1,
                "values": [0],
                "template": "x",
            }
        )
    assert (
        InputSlot.from_value(
            {"signal": "x", "type": "real", "lower": 0, "upper": 1, "value_to_token": None}
        ).value_to_token
        == {}
    )
    with pytest.raises(ValueError):
        InputSlot.from_value(
            {"signal": "x", "type": "real", "lower": 0, "upper": 1, "value_to_token": {1: "x"}}
        )
    assert (
        InputSlot.from_value(
            {"signal": "x", "type": "real", "lower": 0, "upper": 1, "value_to_token": {}}
        ).value_to_token
        == {}
    )
    assert TemplateSpec.from_value(TemplateSpec("{x}", None, {"x": "x"}, {}, "literal"), {"x"})
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"text": "x={x}", "placeholders": {"x": "x", "y": "x"}},
        )
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"identifier": "digest", "placeholders": {"x": "x"}, "escaping": "bad"},
        )
    assert (
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"identifier": "digest", "placeholders": {"x": "x"}},
        ).template
        is not None
    )
    for decoder in (
        {"kind": "argmax", "classes": [], "tie": "a"},
        {"kind": "argmax", "classes": ["a"]},
        {"kind": "argmax", "classes": ["a", "a"], "tie": "a"},
    ):
        with pytest.raises(ValueError):
            _artifact(outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": decoder}])
    partial_output = {
        "name": "y",
        "signal_map": {"score": 0, "other": 1},
        "decoder": {
            "score": {
                "kind": "threshold",
                "threshold": 0,
                "low": 0,
                "high": 1,
                "tie": 1,
            }
        },
    }
    with pytest.raises(ValueError):
        _artifact(outputs=[partial_output])
    _artifact(outputs=[partial_output], postprocessing="included")
    for imports in (
        [("",)],
        [1],
        [{"domain": 1, "version": 13}],
        [{"domain": "", "version": True}],
        [{"domain": "", "version": None}],
    ):
        with pytest.raises(ValueError):
            _artifact(opset_imports=imports)
    _artifact(opset_imports=[{"domain": "", "version": 13}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal": "first"}, {"name": "x", "signal": "second"}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": 1}])
    with pytest.raises(ValueError):
        _artifact(model=_model(extra_input=True))
    with pytest.raises(ValueError):
        _artifact(model=_model(extra_output=True))
    with pytest.raises(ValueError):
        _artifact(
            model=_model(extra_input=True),
            inputs=[
                {"name": "x", "signal_map": {"first": 0, "second": 1}},
                {"name": "x2", "signal_map": {"first": 0, "second": 1}},
            ],
        )
    with pytest.raises(ValueError):
        _artifact(
            model=_model(extra_output=True),
            outputs=[
                {
                    "name": "y",
                    "signal_map": {"score": 0},
                    "decoder": {"kind": "threshold", "threshold": 0, "low": 0, "high": 1, "tie": 1},
                },
                {
                    "name": "z",
                    "signal_map": {"score": 0},
                    "decoder": {"kind": "threshold", "threshold": 0, "low": 0, "high": 1, "tie": 1},
                },
            ],
        )

    for shape in ([1, 0], [True, 1]):
        with pytest.raises(ValueError):
            _artifact(
                inputs=[{"name": "x", "shape": shape, "signal_map": {"first": 0, "second": 1}}]
            )
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": ["a", 0], "second": [0, 1]}}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": -1, "second": 1}}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": 0, "second": 1}}], outputs=["bad"])
    with pytest.raises(ValueError):
        _artifact(outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": {"score": 1}}])
    with pytest.raises(ValueError):
        _artifact(
            inputs=[{"name": "x", "signal_map": {"first": 0, "second": 1}}],
            input_space=DeclaredInputSpace([]),
        )
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": None}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": [0, 2], "second": [0, 1]}}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": "bad", "second": 1}}])
    assert neural._declared_coordinates({}, (1, 2), "input") == {}
    assert neural._declared_coordinates({"signal": "first"}, (1, 2), "input") == {"first": (0,)}
    with pytest.raises(ValueError):
        neural._declared_coordinates({"signal_map": {"first": [0, 2]}}, (1, 2), "input")
    with pytest.raises(ValueError):
        _artifact(outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": 1}])
    with pytest.raises(ValueError):
        _artifact(inputs=[{"name": "x", "signal_map": {"first": 0, "second": 1}, "decoder": 1}])
    with pytest.raises(ValueError):
        OnnxArtifact.from_value("bad")
    artifact = _artifact()
    assert OnnxArtifact.from_value(artifact) is artifact
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"text": "{x}{y}", "placeholders": {"x": "x"}},
        )
    with pytest.raises(ValueError):
        DeclaredInputSpace(
            [
                {"signal": "x", "type": "real", "lower": 0, "upper": 1},
                {"signal": "y", "type": "real", "lower": 0, "upper": 1},
            ],
            template="x={x}",
        )
    assert (
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"text": "{x}{x}", "repetitions": {"x": 2}},
        ).template
        is not None
    )
    assert (
        DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}],
            template={"text": "{x}", "repetitions": None},
        ).template
        is not None
    )


def test_onnx_mapping_and_declared_opset_paths() -> None:
    artifact = _artifact()
    output = artifact.outputs[0]
    decoder = output.decoders["score"]
    mapped = {
        "model": artifact.model,
        "inputs": [
            {
                "name": artifact.inputs[0].name,
                "shape": artifact.inputs[0].shape,
                "dtype": artifact.inputs[0].dtype,
                "signal_map": {
                    signal: coordinate[0]
                    for signal, coordinate in artifact.inputs[0].coordinates.items()
                },
            }
        ],
        "outputs": [
            {
                "name": output.name,
                "shape": output.shape,
                "dtype": output.dtype,
                "signal_map": {
                    signal: coordinate[0] for signal, coordinate in output.coordinates.items()
                },
                "decoder": {
                    "kind": decoder.kind,
                    "threshold": decoder.threshold,
                    "low": decoder.low,
                    "high": decoder.high,
                    "tie": decoder.tie,
                },
            }
        ],
        "input_space": artifact.input_space,
    }
    rebuilt = OnnxArtifact.from_value(mapped)
    assert rebuilt.model_sha256 == artifact.model_sha256

    no_opset = onnx.load_model_from_string(_model())
    no_opset.opset_import.clear()
    with pytest.raises(ValueError):
        _artifact(model=no_opset.SerializeToString())
    custom_opset = onnx.load_model_from_string(_model())
    custom_opset.opset_import.add(domain="com.example", version=1)
    with pytest.raises(ValueError):
        _artifact(model=custom_opset.SerializeToString())


def test_tokenizer_refuses_an_exception_instead_of_partial_tokens() -> None:
    with pytest.raises(UnsupportedConstructError, match="could not be tokenised whole"):
        _normalize_tokens_for_read_whole(1)  # type: ignore[arg-type]
