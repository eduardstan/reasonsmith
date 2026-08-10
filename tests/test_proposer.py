"""Tests for the optional model-facing proposer boundary."""

from __future__ import annotations

import runpy
import sys
from types import SimpleNamespace

import pytest

import reasonsmith.proposer as proposer
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
    assert measurement.sample_size == 29
    assert measurement.agreements == 29
    assert measurement.rate == 1.0
    assert measurement.model == "test-model"


def test_ollama_transport_and_configuration(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{}'

    monkeypatch.setattr(
        proposer.urllib.request,
        "urlopen",
        lambda request, timeout: Response(),
    )
    monkeypatch.setattr(proposer.json, "load", lambda response: {"response": "x"})
    client = proposer.OllamaModel("configured", url="http://model")
    assert client("prompt") == "x"
    monkeypatch.setattr(
        proposer.urllib.request,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(OSError("offline")),
    )
    try:
        client("prompt")
    except proposer.ModelUnavailable as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("offline model should be refused")

    monkeypatch.setenv(proposer.PROPOSER_COMMAND_ENV, "provider --model x")
    configured_command, command_name, command_refusal = proposer.model_from_environment(timeout=1)
    assert isinstance(configured_command, proposer.CommandModel)
    assert command_name == "provider --model x" and not command_refusal
    monkeypatch.delenv(proposer.PROPOSER_COMMAND_ENV)
    monkeypatch.setenv(proposer.PROPOSER_MODEL_ENV, "other-model")
    monkeypatch.setenv(proposer.PROPOSER_URL_ENV, "http://other")
    configured, name, refusal = proposer.model_from_environment(timeout=1)
    assert isinstance(configured, proposer.OllamaModel)
    assert name == "other-model" and configured.url == "http://other" and not refusal
    monkeypatch.setattr(proposer.urllib.request, "urlopen", lambda request, timeout: Response())
    monkeypatch.setattr(proposer.json, "load", lambda response: {})
    with pytest.raises(proposer.ModelUnavailable, match="not an Ollama"):
        client("prompt")
    monkeypatch.delenv(proposer.PROPOSER_MODEL_ENV)
    absent, absent_name, absent_refusal = proposer.model_from_environment()
    assert absent is None and not absent_name and absent_refusal
    with pytest.raises(ValueError):
        proposer.OllamaModel(" ")


def test_strict_boundary_and_refusal_statuses():
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]
    with pytest.raises(ValueError):
        proposer._strict_candidate("", req)
    with pytest.raises(ValueError, match="fragment"):
        proposer._strict_candidate("artifact_logs_event_log", req)
    refused = propose(req, model=lambda prompt: "not a formula", max_attempts=1)
    assert refused.status == "refused" and refused.attempt_budget == 1
    exhausted = propose(
        req, model=lambda prompt: "present(artifact_logs_event_log)", max_attempts=1
    )
    assert exhausted.status == "budget-exhausted"
    unavailable = propose(
        req,
        model=lambda prompt: (_ for _ in ()).throw(proposer.ModelUnavailable("gone")),
        max_attempts=2,
    )
    assert unavailable.status == "unavailable" and "gone" in unavailable.refusal
    assert unavailable.candidate is None
    with pytest.raises(ValueError):
        propose(req, model=lambda prompt: req.spec, max_attempts=0)


def test_model_name_configures_default_transport_and_main(monkeypatch, capsys):
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]

    class FakeClient:
        def __init__(self, model, *, url):
            assert model == "named" and url == "http://configured"

        def __call__(self, prompt):
            return req.spec

    monkeypatch.setattr(proposer, "OllamaModel", FakeClient)
    monkeypatch.setenv(proposer.PROPOSER_URL_ENV, "http://configured")
    result = propose(req, model_name="named", max_attempts=1)
    assert result.machine_passed

    class EnvCommand:
        def __init__(self, command):
            assert command == "provider"

        def __call__(self, prompt):
            return req.spec

    monkeypatch.setattr(proposer, "CommandModel", EnvCommand)
    monkeypatch.setenv(proposer.PROPOSER_COMMAND_ENV, "provider")
    assert propose(req, max_attempts=1).machine_passed

    measurement = proposer.AgreementMeasurement(
        (proposer.AgreementRow("x", "agreed", "p", 1),), "m", 1
    )
    monkeypatch.setattr(proposer, "measure_agreement", lambda **kwargs: measurement)
    assert proposer.main(
        ["--model", "m", "--url", "http://configured", "--command", "provider", "--attempts", "1"]
    ) == 0
    assert '"agreement_rate": 1.0' in capsys.readouterr().out
    empty = proposer.AgreementMeasurement((), "m", 1)
    assert empty.rate == 0.0


def test_duplicate_requirement_index_is_refused(monkeypatch):
    monkeypatch.setattr(proposer, "list_packs", lambda: ["one", "two"])
    monkeypatch.setattr(
        proposer,
        "load_pack",
        lambda name: SimpleNamespace(requirements=[SimpleNamespace(id="duplicate")]),
    )
    with pytest.raises(ValueError, match="duplicate shipped requirement"):
        proposer._requirements()


def test_module_entrypoint_is_executable(monkeypatch, capsys):
    monkeypatch.delenv(proposer.PROPOSER_MODEL_ENV, raising=False)
    monkeypatch.setattr(sys, "argv", ["reasonsmith.proposer"])
    with pytest.raises(SystemExit):
        runpy.run_module("reasonsmith.proposer", run_name="__main__")
    assert "sample_size" in capsys.readouterr().out


def test_command_model_supports_provider_neutral_measurement(monkeypatch):
    class Completed:
        def __init__(self, returncode=0, stdout="candidate\n", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(
        proposer.subprocess,
        "run",
        lambda args, **kwargs: Completed(),
    )
    client = proposer.CommandModel("provider --model x", timeout=5)
    assert client("candidate") == "candidate\n"
    monkeypatch.setattr(
        proposer.subprocess,
        "run",
        lambda args, **kwargs: Completed(returncode=2, stderr="no"),
    )
    with pytest.raises(proposer.ModelUnavailable, match="no"):
        client("candidate")
    monkeypatch.setattr(
        proposer.subprocess,
        "run",
        lambda args, **kwargs: (_ for _ in ()).throw(
            proposer.subprocess.TimeoutExpired("provider", 1)
        ),
    )
    with pytest.raises(proposer.ModelUnavailable):
        client("candidate")
    with pytest.raises(ValueError, match="non-empty"):
        proposer.CommandModel(" ")


def test_prompt_presents_trace_and_pair_evidence_without_labels():
    temporal = proposer._challenge_prompt(_requirements()["ecoa_reg_b_1002_9_a_1_timing_of_notice"])
    counterfactual = proposer._challenge_prompt(
        _requirements()["ecoa_reg_b_1002_4_a_no_disparate_treatment"]
    )
    assert "trace=" in temporal and "artifact_logs_notification_latency_days" in temporal
    assert "pairs=" in counterfactual and "applicant_prohibited_basis" in counterfactual
    assert "expected" not in temporal and "expected" not in counterfactual
