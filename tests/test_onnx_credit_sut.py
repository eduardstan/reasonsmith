"""Behavioural contract for the packaged ONNX-backed SUT example."""

from __future__ import annotations

from dataclasses import replace

from reasonsmith.examples.onnx_credit_scorer import (
    MODEL_SHA256,
    QUERY_SHA256,
    compile_pack_query,
    system_under_test,
    verify_pack_duty,
)
from reasonsmith.neural import OnnxArtifact
from reasonsmith.neural_queries import FakeNeuralVerifier, VerifierRun
from reasonsmith.spec import load_pack


def test_example_reproduces_records_artifact_and_query_hashes():
    first = system_under_test()
    second = system_under_test()

    assert list(first.decisions()) == list(second.decisions())
    artifact = first.artifact(None)
    assert isinstance(artifact, OnnxArtifact)
    assert artifact.model_sha256 == MODEL_SHA256
    assert first.input_space() is artifact.input_space

    query = compile_pack_query(first)
    repeated = compile_pack_query(second)
    assert query.model_sha256 == repeated.model_sha256
    assert query.query_sha256 == repeated.query_sha256
    assert query.query_sha256 == QUERY_SHA256
    assert load_pack("ecoa").get_requirement(query.metadata["requirement_id"]).formalism == (
        "counterfactual"
    )


def test_external_verifier_sat_is_replayed_against_the_artifact_and_sut():
    sut = system_under_test()
    query = compile_pack_query(sut)
    # The compiled query names each product input deterministically.  Ask the fake external
    # verifier for the real discriminatory pair: identical score input, changed protected basis.
    variables = [
        line.split()[1]
        for line in query.vnnlib.splitlines()
        if line.startswith("(declare-fun features_")
    ]
    assignment = {
        variables[0]: 0.0,
        variables[1]: 0.0,
        variables[2]: 0.0,
        variables[3]: 1.0,
    }
    check = verify_pack_duty(sut, FakeNeuralVerifier(VerifierRun("sat", assignment)))

    assert check.run.status == "sat"
    assert check.witness is not None and check.witness.valid
    assert check.witness.decoded["a"]["artifact_logs_decision_record"] == "approved"
    assert check.witness.decoded["b"]["artifact_logs_decision_record"] == "adverse_action"


def test_external_verifier_refusals_never_become_observed_results():
    sut = system_under_test()
    unsupported = verify_pack_duty(sut, FakeNeuralVerifier(VerifierRun("unsupported")))
    assert unsupported.run.status == "unsupported"
    assert unsupported.witness is None

    no_artifact = replace(sut, _artifact=None)
    unavailable = verify_pack_duty(no_artifact, FakeNeuralVerifier(VerifierRun("sat", {})))
    assert unavailable.run.status == "error"
    assert unavailable.witness is None
    assert "artifact" in (unavailable.run.diagnostic or "").lower()
