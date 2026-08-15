"""Slice-3 Marabou subprocess boundary tests."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import fields, replace

import pytest

onxx = pytest.importorskip("onnx")
from onnx import TensorProto, helper  # noqa: E402

from reasonsmith.neural import DeclaredInputSpace, OnnxArtifact  # noqa: E402
from reasonsmith.neural_queries import (  # noqa: E402
    compile_counterfactual_query,
    verify_query,
)
from reasonsmith.neural_verifiers.marabou import (  # noqa: E402
    COMPLETE_MODE,
    MarabouVerifier,
    ResourceLimits,
)


def _query(*, constant: bool = False):
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 2])
    if constant:
        value = helper.make_tensor("constant", TensorProto.FLOAT, [1, 2], [0, 0])
        nodes = [helper.make_node("Constant", [], ["y"], value=value)]
    else:
        nodes = [helper.make_node("Identity", ["x"], ["y"])]
    model = helper.make_model(
        helper.make_graph(nodes, "tiny", [x], [y]),
        opset_imports=[helper.make_opsetid("", 13)],
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
        ]
    )
    artifact = OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[{"name": "x", "signal_map": {"feature": 0, "applicant_prohibited_basis": 1}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"outcome": 0, "record": 1},
                "decoder": {
                    "outcome": {"threshold": 0, "low": "no", "high": "yes", "tie": "no"},
                    "record": {"threshold": 0.5, "low": "no", "high": "yes", "tie": "no"},
                },
            }
        ],
        input_space=space,
    )
    return compile_counterfactual_query(artifact, outcome_signal="record")


class _Process:
    def __init__(
        self, stdout: str = "", stderr: str = "", returncode: int = 0, timeout: bool = False
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.timeout = timeout
        self.pid = 1234
        self.killed = False

    def communicate(self, timeout=None):
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired(["marabou"], timeout)
        return self.stdout, self.stderr

    def kill(self):
        self.killed = True


def _patch_process(monkeypatch, *processes):
    queue = list(processes)

    def popen(*args, **kwargs):
        return queue.pop(0)

    monkeypatch.setattr("reasonsmith.neural_verifiers.marabou.subprocess.Popen", popen)


def test_sat_requires_replay_and_records_provenance(monkeypatch):
    query = _query()
    _patch_process(
        monkeypatch,
        _Process("Marabou 2.0.0\n"),
        _Process("sat\nx_a_0 = 0\n x_a_1 = 0\n x_b_0 = 0\n x_b_1 = 1\n"),
    )
    verifier = MarabouVerifier(resource_limits=ResourceLimits(cpu_seconds=2, memory_bytes=1000))
    result = verify_query(query, verifier, timeout=3)
    assert result.run.status == "sat"
    assert result.witness is not None and result.witness.valid
    assert result.run.provenance["tool"] == "marabou"
    assert result.run.provenance["vnnlib_version"] == "1.0"
    assert result.run.provenance["hashes"]["query_sha256"] == query.query_sha256
    assert result.run.provenance["resource_limits"]["wall_seconds"] == 3


@pytest.mark.parametrize(
    ("output", "status", "failure"),
    [
        ("", "error", "malformed_output"),
        ("sat\n", "error", "malformed_assignment"),
        ("unknown\n", "unknown", None),
        ("timeout\n", "timeout", None),
        ("unsat\n", "unsat", None),
    ],
)
def test_subprocess_taxonomy_never_produces_a_witness(monkeypatch, output, status, failure):
    query = _query()
    _patch_process(monkeypatch, _Process("Marabou 2.0.0\n"), _Process(output))
    result = verify_query(query, MarabouVerifier(), timeout=2)
    assert result.run.status == status
    assert result.witness is None
    if failure is not None:
        assert result.run.provenance["failure"] == failure
    if status == "unsat":
        assert result.run.provenance["verdict_eligible"] is False
        assert "provenance-only" in result.run.provenance["unsat_semantics"]


def test_version_drift_is_unsupported(monkeypatch):
    query = _query()
    _patch_process(monkeypatch, _Process("Marabou 9.9.9\n"))
    result = MarabouVerifier().verify(query)
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "version_drift"


def test_complete_mode_is_refused_before_process(monkeypatch):
    query = _query()
    called = False

    def fail(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("complete mode must not invoke Marabou in slice 3")

    monkeypatch.setattr("reasonsmith.neural_verifiers.marabou.subprocess.Popen", fail)
    result = MarabouVerifier(check_version=False).verify(query, mode=COMPLETE_MODE)
    assert result.status == "unsupported"
    assert not called


def test_unsupported_operator_is_refused(monkeypatch):
    query = _query()
    verifier = MarabouVerifier(check_version=False, supported_operators=())
    called = False

    def fail(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("unsupported graph must not invoke Marabou")

    monkeypatch.setattr("reasonsmith.neural_verifiers.marabou.subprocess.Popen", fail)
    result = verifier.verify(query)
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "unsupported_operator"
    assert not called


def test_timeout_is_not_a_verdict(monkeypatch):
    query = _query()
    _patch_process(monkeypatch, _Process("Marabou 2.0.0\n"), _Process(timeout=True))
    result = MarabouVerifier().verify(query, timeout=0.1)
    assert result.status == "timeout"
    assert result.provenance["failure"] == "timeout"


def _marabou_is_installed() -> bool:
    executable = shutil.which("marabou")
    if executable is None:
        return False
    try:
        completed = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and "2.0.0" in (completed.stdout + completed.stderr)


@pytest.mark.skipif(not _marabou_is_installed(), reason="Marabou 2.0.0 CLI is not installed")
def test_real_marabou_known_sat_fixture() -> None:
    result = MarabouVerifier().verify(_query(), timeout=30)
    assert result.status == "sat"
    assert result.assignment is not None


@pytest.mark.skipif(not _marabou_is_installed(), reason="Marabou 2.0.0 CLI is not installed")
def test_real_marabou_known_unsat_fixture() -> None:
    # The bounded adapter records UNSAT but deliberately does not turn it into a verdict claim.
    result = MarabouVerifier().verify(_query(constant=True), timeout=30)
    assert result.status == "unsat"
    assert result.provenance["verdict_eligible"] is False


def test_resource_limits_are_serialized_and_validate_values() -> None:
    limits = ResourceLimits(cpu_seconds=2, memory_bytes=4096, gpu="cuda:0")
    details = limits.as_dict(1.5)
    assert details["wall_seconds"] == 1.5
    assert details["enforcement"]["gpu"] == "declaration-only"
    assert details["enforcement"]["cpu"] == "RLIMIT_CPU"
    for kwargs in (
        {"cpu_seconds": 0},
        {"memory_bytes": 0},
        {"gpu": ""},
    ):
        with pytest.raises(ValueError):
            ResourceLimits(**kwargs)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeouts_never_start_the_onnx_verifier(monkeypatch, timeout) -> None:
    query = _query()
    monkeypatch.setattr(
        "reasonsmith.neural_verifiers.marabou.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("invalid timeout started a child"),
    )
    result = MarabouVerifier(check_version=False).verify(query, timeout=timeout)
    assert result.status == "error"
    assert result.provenance["failure"] == "invalid_timeout"


def _artifact_with_metadata(artifact, **changes):
    clone = object.__new__(type(artifact))
    for field in fields(artifact):
        object.__setattr__(
            clone, field.name, changes.get(field.name, getattr(artifact, field.name))
        )
    return clone


def test_unsupported_artifact_metadata_is_refused_before_process(monkeypatch) -> None:
    query = _query()
    cases = [
        (
            _artifact_with_metadata(query.artifact, schema_version=99),
            "unsupported_artifact_schema",
        ),
        (
            _artifact_with_metadata(query.artifact, vnnlib_version="2.0"),
            "unsupported_vnnlib_version",
        ),
        (_artifact_with_metadata(query.artifact, onnx_ir_version=99), "unsupported_onnx_ir"),
        (
            _artifact_with_metadata(query.artifact, opset_imports=(("", 99),)),
            "unsupported_onnx_opset",
        ),
    ]

    def fail(*args, **kwargs):
        pytest.fail("metadata refusal started a child")

    monkeypatch.setattr("reasonsmith.neural_verifiers.marabou.subprocess.Popen", fail)
    for artifact, failure in cases:
        result = MarabouVerifier(check_version=False).verify(replace(query, artifact=artifact))
        assert result.status == "unsupported"
        assert result.provenance["failure"] == failure

    binding = replace(query.artifact.inputs[0], dtype="uint8")
    result = MarabouVerifier(check_version=False).verify(
        replace(query, artifact=_artifact_with_metadata(query.artifact, inputs=(binding,)))
    )
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "unsupported_dtype"


def test_malformed_query_is_refused_and_process_failures_are_errors(monkeypatch) -> None:
    query = _query()
    mutant = replace(
        query,
        vnnlib=query.vnnlib.replace(f"(assert {query.required_assertions[0]})\n", "", 1),
    )
    result = MarabouVerifier(check_version=False).verify(mutant)
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "unsupported_query"

    verifier = MarabouVerifier(executable="/no/such/marabou", check_version=False)
    result = verifier.verify(query)
    assert result.status == "error"
    assert result.provenance["failure"] == "crash"

    _patch_process(monkeypatch, _Process("", "fatal", returncode=3))
    result = MarabouVerifier(check_version=False).verify(query)
    assert result.status == "error"
    assert result.provenance["failure"] == "crash"
    assert result.diagnostic == "fatal"


@pytest.mark.parametrize(
    "output",
    [
        "sat\nx_a_0 = nan\n",
        "sat\nx_a_0 = 0\nx_a_0 = 1\n",
    ],
)
def test_sat_nonfinite_or_conflicting_assignments_are_rejected(monkeypatch, output) -> None:
    _patch_process(monkeypatch, _Process("Marabou 2.0.0\n"), _Process(output))
    result = MarabouVerifier().verify(_query())
    assert result.status == "error"
    assert result.provenance["failure"] == "malformed_assignment"
    assert result.assignment is None
