"""Slice-2 neural query compiler and witness-boundary checks."""

from __future__ import annotations

from dataclasses import replace

import pytest

onnx = pytest.importorskip("onnx")
from onnx import TensorProto, helper  # noqa: E402

from reasonsmith.neural import DeclaredInputSpace, OnnxArtifact  # noqa: E402
from reasonsmith.neural_queries import (  # noqa: E402
    FakeOracle,
    QueryShape,
    VerifierRun,
    _num,
    _numpy_dtype,
    _validate_vnnlib_text,
    check_witness,
    compile_counterfactual_query,
    compile_local_robustness_query,
    compile_monotonicity_query,
    validate_compiled_query,
    verify_query,
)


def _artifact(*, mode: str = "identity", tie: object = "yes", constraints=()):
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 2])
    if mode == "identity":
        nodes = [helper.make_node("Identity", ["x"], ["y"])]
    elif mode == "negative":
        nodes = [helper.make_node("Neg", ["x"], ["y"])]
    else:
        raise AssertionError(mode)
    model = helper.make_model(
        helper.make_graph(nodes, "tiny", [x], [y]), opset_imports=[helper.make_opsetid("", 13)]
    )
    space = DeclaredInputSpace(
        [
            {"signal": "feature", "type": "real", "lower": -1, "upper": 1},
            {
                "signal": "applicant_prohibited_basis",
                "type": "categorical",
                "lower": 0,
                "upper": 1,
                "values": [0, 1],
            },
        ],
        constraints=constraints,
    )
    return OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[{"name": "x", "signal_map": {"feature": 0, "applicant_prohibited_basis": 1}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"outcome": 0, "record": 1},
                "decoder": {
                    "outcome": {
                        "kind": "threshold",
                        "threshold": 0,
                        "low": "no",
                        "high": "yes",
                        "tie": tie,
                    },
                    "record": {
                        "kind": "threshold",
                        "threshold": 0.5,
                        "low": "no",
                        "high": "yes",
                        "tie": tie,
                    },
                },
            }
        ],
        input_space=space,
    )


def test_counterfactual_product_and_replay() -> None:
    query = compile_counterfactual_query(
        _artifact(), protected_signal="applicant_prohibited_basis", outcome_signal="record"
    )
    assert query.shape is QueryShape.COUNTERFACTUAL
    assert "x__a" in [
        value.name for value in onnx.load_model_from_string(query.product_model).graph.input
    ]
    assert "(= x_a_0 x_b_0)" in query.vnnlib
    assert "(= x_a_1 0)" in query.vnnlib and "(= x_a_1 1)" in query.vnnlib
    query.validate()
    assignment = {"x_a_0": 0, "x_a_1": 0, "x_b_0": 0, "x_b_1": 1}
    witness = check_witness(query, assignment)
    assert (
        witness.valid
        and witness.decoded["a"]["record"] == "no"
        and witness.decoded["b"]["record"] == "yes"
    )


def test_counterfactual_rejects_bad_witnesses_and_ties() -> None:
    query = compile_counterfactual_query(_artifact(), outcome_signal="record")
    cases = [
        ({"x_a_0": 0, "x_a_1": 0, "x_b_0": 0, "x_b_1": 0}, "protected"),
        ({"x_a_0": 0, "x_a_1": 0, "x_b_0": 0.1, "x_b_1": 1}, "held-equal"),
        ({"x_a_0": 2, "x_a_1": 0, "x_b_0": 2, "x_b_1": 1}, "bounds"),
    ]
    for assignment, reason in cases:
        result = check_witness(query, assignment)
        assert not result.valid and reason in (result.reason or "")
    tie_query = compile_counterfactual_query(_artifact(tie="tie"), outcome_signal="record")
    assert check_witness(tie_query, {"x_a_0": 0, "x_a_1": 0, "x_b_0": 0, "x_b_1": 1}).valid


def test_counterfactual_checks_categories_constraints_and_sut() -> None:
    query = compile_counterfactual_query(
        _artifact(constraints=({"signal": "feature", "op": ">=", "value": 0},)),
        outcome_signal="record",
    )
    assignment = {"x_a_0": 0.5, "x_a_1": 0, "x_b_0": 0.5, "x_b_1": 1}
    assert check_witness(query, assignment, sut_replay=lambda _: "wrong").valid is False
    assert "categorical" in (check_witness(query, {**assignment, "x_b_1": 0.5}).reason or "")
    assert "cross-input" in (check_witness(query, {**assignment, "x_a_0": -0.5}).reason or "")


def test_monotonicity_reversal_replays() -> None:
    query = compile_monotonicity_query(
        _artifact(mode="negative"), feature="feature", outcome_signal="outcome"
    )
    assert "(= x_a_1 x_b_1)" in query.vnnlib and "(<= x_a_0 x_b_0)" in query.vnnlib
    witness = check_witness(query, {"x_a_0": 0, "x_a_1": 0, "x_b_0": 1, "x_b_1": 0})
    assert witness.valid
    assert not check_witness(query, {"x_a_0": 1, "x_a_1": 0, "x_b_0": 0, "x_b_1": 0}).valid
    with pytest.raises(ValueError):
        compile_monotonicity_query(
            _artifact(), feature="feature", outcome_signal="outcome", direction="strict"
        )


def test_local_robustness_intersects_bounds_and_replays() -> None:
    query = compile_local_robustness_query(
        _artifact(),
        centre={"feature": 1, "applicant_prohibited_basis": 0},
        radius=1,
        outcome_signal="outcome",
    )
    assert "(>= x_b_0 0.0)" in query.vnnlib and "(<= x_b_0 1.0)" in query.vnnlib
    witness = check_witness(query, {"x_a_0": 1, "x_a_1": 0, "x_b_0": 0, "x_b_1": 1})
    assert witness.valid
    for metric in ("l1", "l2"):
        with pytest.raises(ValueError):
            compile_local_robustness_query(
                _artifact(),
                centre={"feature": 0, "applicant_prohibited_basis": 0},
                radius=1,
                outcome_signal="outcome",
                metric=metric,
            )
    with pytest.raises(ValueError):
        compile_local_robustness_query(
            _artifact(),
            centre={"feature": 0, "applicant_prohibited_basis": 0},
            radius=-1,
            outcome_signal="outcome",
        )


def test_query_mutants_and_fake_oracle_are_checked() -> None:
    query = compile_counterfactual_query(_artifact(), outcome_signal="record")
    mutant = replace(query, vnnlib=query.vnnlib.replace("(= x_a_0 x_b_0)", "(= x_a_0 x_b_1)"))
    with pytest.raises(ValueError):
        validate_compiled_query(mutant)
    for status in ("unsat", "unknown", "timeout", "error", "unsupported"):
        run = VerifierRun(status, diagnostic="controlled")
        assert (
            verify_query(
                compile_counterfactual_query(_artifact(), outcome_signal="record"), FakeOracle(run)
            ).run
            is run
        )
    assignment = {"x_a_0": 0, "x_a_1": 0, "x_b_0": 0, "x_b_1": 1}
    result = verify_query(
        compile_counterfactual_query(_artifact(), outcome_signal="record"),
        FakeOracle(VerifierRun("sat", assignment)),
    )
    assert result.witness is not None and result.witness.valid


def test_nested_assignments_and_replay_adapters_are_checked_against_onnx() -> None:
    query = compile_counterfactual_query(_artifact(), outcome_signal="record")
    assignment = {
        "a": {"feature": 0, "1": 0},
        "b": {"x_b_0": 0, "applicant_prohibited_basis": 1},
    }

    def replay(values):
        return {"record": "yes" if values["applicant_prohibited_basis"] else "no"}

    witness = check_witness(query, assignment, replay=replay)
    assert witness.valid
    assert witness.inputs["a"]["feature"] == 0
    assert witness.decoded["b"]["record"] == "yes"

    class Sut:
        def decide(self, values):
            return {"record": "yes" if values["applicant_prohibited_basis"] else "no"}

    assert check_witness(query, assignment, sut=Sut()).valid
    assert not check_witness(query, assignment, sut=object()).valid


def test_monotonicity_nonincreasing_and_local_numeric_tolerance_are_replayed() -> None:
    decreasing = compile_monotonicity_query(
        _artifact(mode="negative"),
        feature="feature",
        outcome_signal="outcome",
        direction="nonincreasing",
    )
    result = check_witness(
        decreasing, {"x_a_0": 0, "x_a_1": 0, "x_b_0": 1, "x_b_1": 0}
    )
    assert not result.valid
    assert "did not reproduce" in (result.reason or "")

    local = compile_local_robustness_query(
        _artifact(),
        centre={"feature": 0.5, "applicant_prohibited_basis": 0},
        radius={"feature": 0.2, "applicant_prohibited_basis": 0},
        outcome_signal="outcome",
        output_tolerance=0.05,
    )
    witness = check_witness(
        local, {"x_a_0": 0.5, "x_a_1": 0, "x_b_0": 0.6, "x_b_1": 0}
    )
    assert witness.valid


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"feature": "missing", "outcome_signal": "outcome"}, "unknown monotonicity feature"),
        ({"feature": "feature", "outcome_signal": "missing"}, "unknown decoded output"),
    ],
)
def test_query_compilers_reject_unknown_signals(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        compile_monotonicity_query(_artifact(), **kwargs)


def test_local_query_rejects_malformed_centres_radii_and_tolerance() -> None:
    base = {"feature": 0, "applicant_prohibited_basis": 0}
    with pytest.raises(ValueError, match="centre must be a mapping"):
        compile_local_robustness_query(_artifact(), centre=None, radius=1, outcome_signal="outcome")
    with pytest.raises(ValueError, match="missing"):
        compile_local_robustness_query(
            _artifact(), centre={"feature": 0}, radius=1, outcome_signal="outcome"
        )
    with pytest.raises(ValueError, match="outside bounds"):
        compile_local_robustness_query(
            _artifact(), centre={**base, "feature": 2}, radius=1, outcome_signal="outcome"
        )
    with pytest.raises(ValueError, match="cover exactly"):
        compile_local_robustness_query(
            _artifact(), centre=base, radius={"feature": 1}, outcome_signal="outcome"
        )
    with pytest.raises(ValueError, match="finite and non-negative"):
        compile_local_robustness_query(
            _artifact(),
            centre=base,
            radius={"feature": 1, "applicant_prohibited_basis": float("nan")},
            outcome_signal="outcome",
        )
    with pytest.raises(ValueError, match="output_tolerance"):
        compile_local_robustness_query(
            _artifact(), centre=base, radius=1, outcome_signal="outcome", output_tolerance=-1
        )


@pytest.mark.parametrize("onnx_dtype", [TensorProto.FLOAT16, TensorProto.BFLOAT16])
def test_witness_replay_refuses_unsupported_tensor_dtypes(onnx_dtype) -> None:
    x = helper.make_tensor_value_info("x", onnx_dtype, [1])
    y = helper.make_tensor_value_info("y", onnx_dtype, [1])
    model = helper.make_model(
        helper.make_graph([helper.make_node("Identity", ["x"], ["y"])], "dtype", [x], [y]),
        opset_imports=[helper.make_opsetid("", 13)],
    )
    artifact = OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[{"name": "x", "signal_map": {"feature": 0}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"out": 0},
                "decoder": {
                    "kind": "threshold",
                    "threshold": 0.5,
                    "low": "no",
                    "high": "yes",
                    "tie": "no",
                },
            }
        ],
        input_space=DeclaredInputSpace(
            [{"signal": "feature", "type": "real", "lower": 0, "upper": 1}]
        ),
    )
    query = compile_local_robustness_query(
        artifact, centre={"feature": 0.9}, radius=0.1, outcome_signal="out", output_tolerance=0.5
    )
    witness = check_witness(query, {"x_a_0": 0.9, "x_b_0": 1.0})
    assert not witness.valid
    assert "tensor dtype(s)" in (witness.reason or "")


def test_compiled_query_hashes_and_product_model_are_bound() -> None:
    query = compile_counterfactual_query(_artifact(), outcome_signal="record")
    with pytest.raises(ValueError, match="query_sha256"):
        validate_compiled_query(replace(query, query_sha256="0" * 64))
    with pytest.raises(ValueError, match="product_model"):
        validate_compiled_query(replace(query, product_model=query.artifact.model))
    other = _artifact(mode="negative")
    with pytest.raises(ValueError, match="model_sha256"):
        validate_compiled_query(replace(query, artifact=other))


def test_vnnlib_compiler_refuses_identifier_collisions_and_maps_smt_equality() -> None:
    x_dash = helper.make_tensor_value_info("x-a", TensorProto.FLOAT, [1])
    x_under = helper.make_tensor_value_info("x_a", TensorProto.FLOAT, [1])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1])
    model = helper.make_model(
        helper.make_graph(
            [helper.make_node("Identity", ["x-a"], ["y"])],
            "collision",
            [x_dash, x_under],
            [y],
        ),
        opset_imports=[helper.make_opsetid("", 13)],
    )
    space = DeclaredInputSpace(
        [
            {"signal": "left", "type": "real", "lower": 0, "upper": 1},
            {"signal": "right", "type": "real", "lower": 0, "upper": 1},
        ],
        constraints=({"signal": "left", "op": "==", "value": 0},),
    )
    artifact = OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[
            {"name": "x-a", "signal_map": {"left": 0}},
            {"name": "x_a", "signal_map": {"right": 0}},
        ],
        outputs=[
            {
                "name": "y",
                "signal_map": {"out": 0},
                "decoder": {
                    "kind": "threshold",
                    "threshold": 0,
                    "low": "no",
                    "high": "yes",
                    "tie": "no",
                },
            }
        ],
        input_space=space,
    )
    with pytest.raises(ValueError, match="colliding"):
        compile_monotonicity_query(artifact, feature="left", outcome_signal="out")

    query = compile_monotonicity_query(
        _artifact(constraints=({"signal": "feature", "op": "==", "value": 0},)),
        feature="feature",
        outcome_signal="outcome",
    )
    assert "(==" not in query.vnnlib
    assert "(= x_a_0 0)" in query.vnnlib


def test_neural_input_enum_types_are_not_smuggled_into_numeric_vnnlib() -> None:
    with pytest.raises(ValueError, match="string-enum values"):
        DeclaredInputSpace([{"signal": "x", "type": "string-enum", "values": [1]}])
    with pytest.raises(ValueError, match="boolean values"):
        DeclaredInputSpace([{"signal": "x", "type": "boolean", "values": [0, 1]}])


def test_vnnlib_preserves_finite_numeric_enum_domains() -> None:
    base = _artifact()
    artifact = OnnxArtifact(
        model=base.model,
        inputs=[{"name": "x", "signal_map": {"feature": 0, "applicant_prohibited_basis": 1}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"outcome": 0, "record": 1},
                "decoder": {
                    "outcome": {
                        "kind": "threshold",
                        "threshold": 0,
                        "low": "no",
                        "high": "yes",
                        "tie": "no",
                    },
                    "record": {
                        "kind": "threshold",
                        "threshold": 0.5,
                        "low": "no",
                        "high": "yes",
                        "tie": "no",
                    },
                },
            }
        ],
        input_space=DeclaredInputSpace(
            [
                {
                    "signal": "feature",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 2,
                    "values": [0, 2],
                },
                {
                    "signal": "applicant_prohibited_basis",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 1,
                    "values": [0, 1],
                },
            ]
        ),
    )
    query = compile_monotonicity_query(artifact, feature="feature", outcome_signal="outcome")
    assert "(or (= x_a_0 0) (= x_a_0 2))" in query.vnnlib
    witness = check_witness(query, {"x_a_0": 1, "x_a_1": 0, "x_b_0": 2, "x_b_1": 0})
    assert not witness.valid
    assert "categorical" in (witness.reason or "")


def test_string_enum_input_is_refused_before_numeric_vnnlib() -> None:
    base = _artifact()
    artifact = OnnxArtifact(
        model=base.model,
        inputs=[{"name": "x", "signal_map": {"feature": 0, "applicant_prohibited_basis": 1}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"outcome": 0, "record": 1},
                "decoder": {
                    "outcome": {
                        "kind": "threshold",
                        "threshold": 0,
                        "low": "no",
                        "high": "yes",
                        "tie": "no",
                    },
                    "record": {
                        "kind": "threshold",
                        "threshold": 0.5,
                        "low": "no",
                        "high": "yes",
                        "tie": "no",
                    },
                },
            }
        ],
        input_space=DeclaredInputSpace(
            [
                {"signal": "feature", "type": "string-enum", "values": ["a"]},
                {
                    "signal": "applicant_prohibited_basis",
                    "type": "categorical",
                    "lower": 0,
                    "upper": 1,
                    "values": [0, 1],
                },
            ]
        ),
    )
    with pytest.raises(ValueError, match="cannot encode string-enum"):
        compile_monotonicity_query(artifact, feature="feature", outcome_signal="outcome")


@pytest.mark.parametrize(
    "text",
    [
        "(assert (= x 0))\n(check-sat)\n",
        "(declare-fun x () Real)\n(assert (== x 0))\n",
        "(declare-fun x () Real)\n(assert (>= x None))\n",
    ],
)
def test_vnnlib_shape_validator_rejects_malformed_literals(text) -> None:
    with pytest.raises(ValueError):
        _validate_vnnlib_text(text)


def test_numeric_vnnlib_helpers_reject_non_numeric_values() -> None:
    with pytest.raises(ValueError):
        _num(None)
    with pytest.raises(ValueError):
        _numpy_dtype("uint8")
