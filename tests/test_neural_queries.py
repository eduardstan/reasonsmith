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
