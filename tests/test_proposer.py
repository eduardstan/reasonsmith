"""Tests for the optional model-facing proposer boundary."""

from __future__ import annotations

from reasonsmith.proposer import measure_agreement, propose
from reasonsmith.spec import list_packs, load_pack


def _requirements():
    return {
        req.id: req
        for pack_name in list_packs()
        for req in load_pack(pack_name).requirements
    }


def test_unconfigured_model_is_a_first_class_refusal(monkeypatch):
    monkeypatch.delenv("REASONSMITH_PROPOSER_MODEL", raising=False)
    result = propose("eu_ai_act_art12_1_automatic_logging")
    assert result.status == "unavailable"
    assert result.attempts == ()
    assert "configure" in result.refusal


def test_invalid_model_text_is_refused_and_repaired_with_evidence():
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]
    responses = iter(("not a formula", req.spec))
    prompts = []

    def model(prompt):
        prompts.append(prompt)
        return next(responses)

    result = propose(req, model=model, max_attempts=2)
    assert result.machine_passed
    assert result.attempts[0].refusal
    assert result.candidate == req.spec
    assert "previous response was refused" in prompts[1]


def test_failed_candidate_is_repaired_from_round_trip_and_gold_evidence():
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]
    responses = iter(("present(artifact_logs_event_log)", req.spec))
    prompts = []

    def model(prompt):
        prompts.append(prompt)
        return next(responses)

    result = propose(req, model=model, max_attempts=2)
    assert result.machine_passed
    assert "weaker" in prompts[1]
    assert "blank-provenance-near-miss" in prompts[1]


def test_measurement_uses_all_gold_sets_and_reports_machine_agreement():
    requirements = _requirements()

    def model(prompt):
        for req in requirements.values():
            if f"Requirement id: {req.id}" in prompt:
                return req.spec
        raise AssertionError("unknown requirement prompt")

    measurement = measure_agreement(model=model, model_name="test-model", max_attempts=1)
    assert measurement.sample_size == 3
    assert measurement.agreements == 3
    assert measurement.rate == 1.0
    assert measurement.model == "test-model"
