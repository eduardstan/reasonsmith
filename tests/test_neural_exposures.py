"""Slice-1 typed neural exposure validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

pytest.importorskip("onnx")
from onnx import TensorProto, helper  # noqa: E402

from reasonsmith.neural import DeclaredInputSpace, OnnxArtifact
from reasonsmith.sut import NeuralExposures, SystemUnderTest


def _model(*, dynamic: bool = False, external: bool = False) -> bytes:
    dimension = "batch" if dynamic else 1
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [dimension, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [dimension, 2])
    node = helper.make_node("Identity", ["x"], ["y"])
    graph = helper.make_graph([node], "model", [x], [y])
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
