"""Tests for the pinned slice-4 Marabou soundness corpus and closed gate."""

from __future__ import annotations

from neural_soundness_corpus import (
    COMPLETE_MODE,
    CORPUS_VERSION,
    MARABOU_COMMIT,
    MARABOU_VERSION,
    VNNLIB_VERSION,
    _mutant,
    corpus_cases,
    corpus_manifest,
    run_complete_corpus,
)

from reasonsmith.neural_verifiers.marabou import MarabouVerifier


def test_corpus_has_finite_reference_cases_for_each_query_shape():
    cases = corpus_cases()
    assert {case.query.shape.value for case in cases} == {
        "counterfactual_invariance",
        "monotonicity",
        "local_robustness",
    }
    assert {case.expected for case in cases} == {"sat", "unsat"}
    assert all(case.expected == case.finite_reference for case in cases)


def test_semantically_equivalent_assertion_order_mutants_validate():
    for case in corpus_cases():
        mutant = _mutant(case.query)
        assert mutant.query_sha256 != case.query.query_sha256
        mutant.validate()


def test_corpus_manifest_pins_release_and_model_query_hashes():
    manifest = corpus_manifest()
    assert manifest["corpus_version"] == CORPUS_VERSION
    assert manifest["marabou_version"] == MARABOU_VERSION == "2.0.0"
    assert len(MARABOU_COMMIT) == 40
    assert manifest["vnnlib_version"] == VNNLIB_VERSION == "1.0"
    assert len(manifest["cases"]) == 6
    assert all(len(case["model_sha256"]) == 64 for case in manifest["cases"])
    assert all(len(case["query_sha256"]) == 64 for case in manifest["cases"])


def test_closed_complete_gate_refuses_every_corpus_case_before_a_child():
    verifier = MarabouVerifier(executable="/no/such/marabou", check_version=False)
    for case in corpus_cases():
        result = verifier.verify(case.query, mode=COMPLETE_MODE)
        assert result.status == "unsupported"
        assert result.provenance["failure"] == "complete_mode_not_admitted"


def test_corpus_runner_records_refusal_as_a_failed_gate_not_a_clean_pass():
    report = run_complete_corpus(executable="/no/such/marabou")
    assert report["complete_mode_admitted"] is False
    assert report["clean"] is False
    assert len(report["results"]) == 12
    assert {row["status"] for row in report["results"]} == {"unsupported"}
    assert {row["failure"] for row in report["results"]} == {"complete_mode_not_admitted"}
