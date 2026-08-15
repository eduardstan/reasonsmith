"""Pinned Marabou complete-mode soundness corpus.

This module is the executable corpus for the slice-4 admission gate.  It deliberately lives in
``tests`` rather than in the package: Marabou remains an optional, separately installed oracle.
Each case has a finite reference answer and assertion-order mutants whose semantics are unchanged.
The gate runner records the hashes and refuses to call an unadmitted complete mode as a pass.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any

import pytest

onnx = pytest.importorskip("onnx")
from onnx import TensorProto, helper  # noqa: E402

from reasonsmith.neural import DeclaredInputSpace, OnnxArtifact  # noqa: E402
from reasonsmith.neural_queries import (  # noqa: E402
    CompiledNeuralQuery,
    QueryShape,
    _reference_replay,
    compile_counterfactual_query,
    compile_local_robustness_query,
    compile_monotonicity_query,
)
from reasonsmith.neural_verifiers.differential import compare_runs  # noqa: E402
from reasonsmith.neural_verifiers.marabou import (  # noqa: E402
    BOUNDED_SEARCH_MODE,
    COMPLETE_MODE,
    MARABOU_VERSION,
    VNNLIB_VERSION,
    MarabouVerifier,
)

MARABOU_COMMIT = "d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d"
CORPUS_VERSION = 1


@dataclass(frozen=True)
class CorpusCase:
    name: str
    query: CompiledNeuralQuery
    expected: str
    finite_reference: str


def _space(*, protected: bool = False) -> DeclaredInputSpace:
    slots: list[dict[str, Any]] = [
        {"signal": "feature", "type": "real", "lower": -1, "upper": 1},
    ]
    if protected:
        slots.append(
            {
                "signal": "applicant_prohibited_basis",
                "type": "categorical",
                "lower": 0,
                "upper": 1,
                "values": [0, 1],
            }
        )
    return DeclaredInputSpace(slots)


def _artifact(
    *,
    operation: str = "identity",
    protected: bool = False,
) -> OnnxArtifact:
    width = 2 if protected else 1
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, width])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, width])
    if operation == "identity":
        nodes = [helper.make_node("Identity", ["x"], ["y"])]
    elif operation == "constant":
        value = helper.make_tensor("constant", TensorProto.FLOAT, [1, width], [0.0] * width)
        nodes = [helper.make_node("Constant", [], ["y"], value=value)]
    elif operation == "neg":
        nodes = [helper.make_node("Neg", ["x"], ["y"])]
    else:  # pragma: no cover - corpus construction error
        raise AssertionError(operation)
    model = helper.make_model(
        helper.make_graph(nodes, f"corpus-{operation}", [x], [y]),
        opset_imports=[helper.make_opsetid("", 13)],
    )
    input_map = {"feature": 0}
    output_map = {"score": 0}
    decoders = {"score": {"threshold": 0, "low": 0, "high": 1, "tie": 0}}
    if protected:
        input_map["applicant_prohibited_basis"] = 1
        output_map = {"score": 0, "artifact_logs_decision_record": 1}
        decoders["artifact_logs_decision_record"] = {
            "threshold": 0,
            "low": 0,
            "high": 1,
            "tie": 0,
        }
    return OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[{"name": "x", "signal_map": input_map}],
        outputs=[{"name": "y", "signal_map": output_map, "decoder": decoders}],
        input_space=_space(protected=protected),
    )


def _finite_reference(query: CompiledNeuralQuery) -> str:
    """Evaluate the tiny supported query over its explicit finite witness grid."""
    shape = query.shape
    if shape is QueryShape.COUNTERFACTUAL:
        protected = str(query.metadata["protected_signal"])
        outcome = str(query.metadata["outcome_signal"])
        left = {"feature": 0, protected: 0}
        for value in query.metadata["protected_values"]:
            right = {"feature": 0, protected: value}
            _, left_decoded = _reference_replay(query.artifact, left)
            _, right_decoded = _reference_replay(query.artifact, right)
            if left_decoded[outcome] != right_decoded[outcome]:
                return "sat"
        return "unsat"
    if shape is QueryShape.MONOTONICITY:
        feature = str(query.metadata["feature"])
        outcome = str(query.metadata["outcome_signal"])
        direction = str(query.metadata["direction"])
        points = (-1, 0, 1)
        for left_value in points:
            for right_value in points:
                if left_value > right_value:
                    continue
                left_raw, _ = _reference_replay(query.artifact, {feature: left_value})
                right_raw, _ = _reference_replay(query.artifact, {feature: right_value})
                reversal = left_raw[outcome] > right_raw[outcome]
                if direction == "nonincreasing":
                    reversal = left_raw[outcome] < right_raw[outcome]
                if reversal:
                    return "sat"
        return "unsat"
    if shape is QueryShape.LOCAL_ROBUSTNESS:
        centre = dict(query.metadata["centre"])
        radius = query.metadata["radius"]
        outcome = str(query.metadata["outcome_signal"])
        centre_raw, centre_decoded = _reference_replay(query.artifact, centre)
        feature = next(iter(centre))
        for value in (-float(radius[feature]), 0.0, float(radius[feature])):
            candidate = dict(centre)
            candidate[feature] = value
            raw, decoded = _reference_replay(query.artifact, candidate)
            if decoded.get(outcome) != centre_decoded.get(outcome):
                return "sat"
            if abs(raw[outcome] - centre_raw[outcome]) > float(query.metadata["output_tolerance"]):
                return "sat"
        return "unsat"
    raise AssertionError(shape)


def _cases() -> tuple[CorpusCase, ...]:
    discriminatory = _artifact(protected=True)
    constant_pair = _artifact(operation="constant", protected=True)
    decreasing = _artifact(operation="neg")
    increasing = _artifact()
    queries = (
        (
            "counterfactual-sat-discriminatory",
            compile_counterfactual_query(
                discriminatory, outcome_signal="artifact_logs_decision_record"
            ),
        ),
        (
            "counterfactual-unsat-constant",
            compile_counterfactual_query(
                constant_pair, outcome_signal="artifact_logs_decision_record"
            ),
        ),
        (
            "monotonicity-sat-decreasing",
            compile_monotonicity_query(decreasing, feature="feature", outcome_signal="score"),
        ),
        (
            "monotonicity-unsat-increasing",
            compile_monotonicity_query(increasing, feature="feature", outcome_signal="score"),
        ),
        (
            "linf-sat-identity",
            compile_local_robustness_query(
                increasing, centre={"feature": 0}, radius=1, outcome_signal="score"
            ),
        ),
        (
            "linf-unsat-constant",
            compile_local_robustness_query(
                _artifact(operation="constant"),
                centre={"feature": 0},
                radius=1,
                outcome_signal="score",
            ),
        ),
    )
    return tuple(
        CorpusCase(name, query, _finite_reference(query), _finite_reference(query))
        for name, query in queries
    )


def _mutant(query: CompiledNeuralQuery) -> CompiledNeuralQuery:
    """Reorder assertions and add a comment without changing any VNN-LIB semantics."""
    lines = query.vnnlib.splitlines()
    indices = [index for index, line in enumerate(lines) if line.startswith("(assert ")]
    assertions = [lines[index] for index in indices]
    for index, assertion in zip(indices, reversed(assertions), strict=True):
        lines[index] = assertion
    mutated = "; semantically equivalent assertion-order mutant\n" + "\n".join(lines) + "\n"
    return replace(query, vnnlib=mutated, query_sha256=hashlib.sha256(mutated.encode()).hexdigest())


def corpus_cases() -> tuple[CorpusCase, ...]:
    return _cases()


def corpus_manifest() -> dict[str, Any]:
    return {
        "corpus_version": CORPUS_VERSION,
        "marabou_version": MARABOU_VERSION,
        "marabou_commit": MARABOU_COMMIT,
        "vnnlib_version": VNNLIB_VERSION,
        "cases": [
            {
                "name": case.name,
                "expected": case.expected,
                "reference": case.finite_reference,
                "model_sha256": case.query.model_sha256,
                "query_sha256": case.query.query_sha256,
                "mutant_query_sha256": _mutant(case.query).query_sha256,
            }
            for case in _cases()
        ],
    }


def run_complete_corpus(*, executable: str = "marabou") -> dict[str, Any]:
    """Run every case and mutant in complete mode, preserving raw oracle outcomes.

    The current gate is intentionally closed: a ``complete_mode_not_admitted`` result is a gate
    refusal, not a clean corpus pass.  If a future release admits the mode, the same runner will
    compare each returned SAT/UNSAT status with the finite reference label.
    """
    verifier = MarabouVerifier(executable=executable)
    results: list[dict[str, Any]] = []
    for case in _cases():
        variants = (("original", case.query), ("assertion-order", _mutant(case.query)))
        for mutant_name, query in variants:
            run = verifier.verify(query, mode=COMPLETE_MODE, timeout=30)
            hashes = run.provenance.get("hashes", {})
            results.append(
                {
                    "case": case.name,
                    "variant": mutant_name,
                    "expected": case.expected,
                    "reference": case.finite_reference,
                    "status": run.status,
                    "diagnostic": run.diagnostic,
                    "failure": run.provenance.get("failure"),
                    "model_sha256": hashes.get("model_sha256", query.model_sha256),
                    "query_sha256": hashes.get("query_sha256", query.query_sha256),
                    "stdout_sha256": hashes.get("stdout_sha256", hashlib.sha256(b"").hexdigest()),
                    "stderr_sha256": hashes.get("stderr_sha256", hashlib.sha256(b"").hexdigest()),
                    "verdict_eligible": run.provenance.get("verdict_eligible", False),
                }
            )
    available = all(item["status"] in ("sat", "unsat") for item in results)
    agrees = available and all(item["status"] == item["expected"] for item in results)
    return {
        "corpus_version": CORPUS_VERSION,
        "marabou_version": MARABOU_VERSION,
        "marabou_commit": MARABOU_COMMIT,
        "vnnlib_version": VNNLIB_VERSION,
        "complete_mode_admitted": False,
        "available": available,
        "clean": agrees,
        "results": results,
    }


def run_differential_corpus(
    marabou_verifier: Any, abcrown_verifier: Any, *, mode: str = BOUNDED_SEARCH_MODE
) -> dict[str, Any]:
    """Run both optional adapters over exactly the same pinned cases and variants.

    This helper is diagnostic: it never selects a verifier's answer. ``stronger_allowed`` is true
    only when the two semantic outcomes agree and both raw runs explicitly mark themselves
    verdict-eligible. Callers must still use ``verify_query`` for SAT witness replay.
    """
    rows: list[dict[str, Any]] = []
    for case in _cases():
        for variant, query in (("original", case.query), ("assertion-order", _mutant(case.query))):
            left = marabou_verifier.verify(query, mode=mode, timeout=30)
            right = abcrown_verifier.verify(query, mode=mode, timeout=30)
            differential = compare_runs(left, right)
            rows.append(
                {
                    "case": case.name,
                    "variant": variant,
                    "model_sha256": query.model_sha256,
                    "query_sha256": query.query_sha256,
                    "marabou_status": left.status,
                    "abcrown_status": right.status,
                    "agreement": differential.agreement,
                    "stronger_allowed": differential.stronger_allowed,
                    "diagnostic": differential.diagnostic,
                }
            )
    return {
        "corpus_version": CORPUS_VERSION,
        "cases": rows,
        "all_agree": all(row["agreement"] for row in rows),
        "stronger_allowed": all(row["stronger_allowed"] for row in rows),
    }


if __name__ == "__main__":  # pragma: no cover - manually run gate command
    print(json.dumps(run_complete_corpus(), indent=2, sort_keys=True))
