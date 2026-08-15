"""Slice-6 alpha-beta-CROWN status and differential contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from reasonsmith.neural_queries import OracleCheck, VerifierRun, WitnessCheck
from reasonsmith.neural_verifiers.abcrown import (
    ABCROWN_NATIVE_STATUSES,
    COMPLETE_MODE,
    ABCROWNResourceLimits,
    ABCROWNVerifier,
    _assignment_from_output,
    _limit_child,
    map_abcrown_status,
    parse_abcrown_status,
)
from reasonsmith.neural_verifiers.differential import compare_checks, compare_runs


@pytest.mark.parametrize(
    "native", ("unsafe-pgd", "unsafe-bab", "safe-incomplete", "complete-safe", "timeout", "unknown")
)
def test_native_statuses_are_explicitly_distinct(native: str) -> None:
    assert native in ABCROWN_NATIVE_STATUSES
    assert parse_abcrown_status(f"Result: {native}\n") == native


def test_status_mapping_keeps_safe_incomplete_below_proof() -> None:
    assert map_abcrown_status("safe-incomplete") == ("unsat", False, "incomplete-bound")
    assert map_abcrown_status("complete-safe")[1] is True
    assert parse_abcrown_status("Result: safe-complete\n") == "complete-safe"
    assert parse_abcrown_status("complete\n") == "complete-safe"
    assert parse_abcrown_status("safe\n") == "safe"
    assert parse_abcrown_status("diagnostic only") is None
    with pytest.raises(ValueError):
        map_abcrown_status("not-a-status")


def test_complete_mode_is_closed_until_gate(monkeypatch) -> None:
    from test_neural_verifier_marabou import _query

    verifier = ABCROWNVerifier(executable="/no/such/python", check_version=False)
    monkeypatch.setattr(verifier, "modes", frozenset(("bounded-search",)))
    result = verifier.verify(_query(), mode=COMPLETE_MODE)
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "complete_mode_not_admitted"


def _run(status: str, *, native: str, eligible: bool) -> VerifierRun:
    return VerifierRun(
        status,
        verifier=native,
        provenance={
            "native_status": native,
            "semantic_status": "unsafe" if status == "sat" else "safe",
            "verdict_eligible": eligible,
        },
    )


def test_differential_disagreement_blocks_stronger_result() -> None:
    result = compare_runs(
        _run("sat", native="unsafe-bab", eligible=False),
        _run("unsat", native="safe", eligible=True),
    )
    assert result.disagreement
    assert not result.stronger_allowed
    assert "disagreement" in (result.diagnostic or "")


def test_differential_agreement_still_requires_both_eligible() -> None:
    result = compare_runs(
        _run("unsat", native="safe-incomplete", eligible=False),
        _run("unsat", native="complete-safe", eligible=True),
    )
    assert result.agreement
    assert not result.stronger_allowed


class _Process:
    pid = 1234
    returncode = 0

    def __init__(
        self, stdout: str = "", stderr: str = "", returncode: int = 0, timeout: bool = False
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.timeout = timeout
        self.killed = False

    def communicate(self, timeout=None):
        if self.timeout and not self.killed:
            import subprocess

            raise subprocess.TimeoutExpired(["abcrown"], timeout)
        return self.stdout, self.stderr

    def kill(self):
        self.killed = True


def test_mocked_subprocess_preserves_native_status_and_hashes(monkeypatch) -> None:
    from test_neural_verifier_marabou import _query

    query = _query()
    queue = [
        _Process("0.7.0\n"),
        _Process("Result: unsafe-pgd\nx_a_0 = 0\nx_a_1 = 0\nx_b_0 = 0\nx_b_1 = 1\n"),
    ]
    monkeypatch.setattr(
        "reasonsmith.neural_verifiers.abcrown.subprocess.Popen",
        lambda *args, **kwargs: queue.pop(0),
    )
    run = ABCROWNVerifier().verify(query, timeout=2)
    assert run.status == "sat"
    assert run.provenance["native_status"] == "unsafe-pgd"
    assert run.provenance["verdict_eligible"] is False
    assert run.provenance["hashes"]["query_sha256"] == query.query_sha256


def _query():
    from test_neural_verifier_marabou import _query as make_query

    return make_query()


def _patch_processes(monkeypatch, *processes):
    queue = list(processes)
    monkeypatch.setattr(
        "reasonsmith.neural_verifiers.abcrown.subprocess.Popen",
        lambda *args, **kwargs: queue.pop(0),
    )


def test_resource_limits_and_proprietary_configuration_are_enforced() -> None:
    limits = ABCROWNResourceLimits(cpu_seconds=2, memory_bytes=4096, gpu="cuda:0")
    details = limits.as_dict(3)
    assert details["wall_seconds"] == 3
    assert details["enforcement"]["gpu"] == "declaration-only"
    for kwargs in ({"cpu_seconds": 0}, {"memory_bytes": 0}, {"gpu": ""}):
        with pytest.raises(ValueError):
            ABCROWNResourceLimits(**kwargs)
    with pytest.raises(ValueError, match="gurobi"):
        ABCROWNVerifier(configuration={"solver": "gurobi", "use": True})
    with pytest.raises(ValueError, match="cplex"):
        ABCROWNVerifier(extra_args=("--cplex", "true"))


def test_assignment_parser_rejects_bad_and_missing_witnesses() -> None:
    assert _assignment_from_output("x = nan", {"x"})[1] == "non-finite assignment for 'x'"
    assert _assignment_from_output("x = 1\nx = 2", {"x"})[1] == "conflicting assignments for 'x'"
    assert (
        _assignment_from_output("x = 1", {"y"})[1]
        == "unsafe output did not contain a declared assignment"
    )
    assert _assignment_from_output("x = tensor(1)", {"x"})[0] == {"x": 1.0}


def test_verify_rejects_timeout_and_unsupported_operator_before_child(monkeypatch) -> None:
    query = _query()
    verifier = ABCROWNVerifier(check_version=False)
    monkeypatch.setattr(
        "reasonsmith.neural_verifiers.abcrown.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("child must not start"),
    )
    assert verifier.verify(query, timeout=0).provenance["failure"] == "invalid_timeout"
    unsupported = ABCROWNVerifier(check_version=False, supported_operators=())
    result = unsupported.verify(query)
    assert result.status == "unsupported"
    assert result.provenance["failure"] == "unsupported_operator"


def test_verify_records_safe_incomplete_and_effective_configuration(monkeypatch) -> None:
    query = _query()
    _patch_processes(monkeypatch, _Process("Result: safe-incomplete\n"))
    result = ABCROWNVerifier(
        check_version=False, resource_limits=ABCROWNResourceLimits(cpu_seconds=1)
    ).verify(query)
    assert result.status == "unsat"
    assert result.provenance["native_status"] == "safe-incomplete"
    assert result.provenance["verdict_eligible"] is False
    assert result.provenance["configuration"]["effective_config"]["general"]["device"] == "cpu"
    assert len(result.provenance["hashes"]["config_sha256"]) == 64


def test_verify_complete_safe_can_be_admitted_only_explicitly(monkeypatch) -> None:
    query = _query()
    _patch_processes(monkeypatch, _Process("Result: safe\n"))
    verifier = ABCROWNVerifier(check_version=False, admit_complete=True)
    result = verifier.verify(query, mode=COMPLETE_MODE)
    assert result.status == "unsat"
    assert result.provenance["verdict_eligible"] is True
    assert (
        result.provenance["configuration"]["effective_config"]["general"][
            "enable_incomplete_verification"
        ]
        is False
    )


def test_verify_failure_taxonomy_and_version_drift(monkeypatch) -> None:
    query = _query()
    _patch_processes(monkeypatch, _Process("0.7.0\n"), _Process(timeout=True))
    assert ABCROWNVerifier().verify(query, timeout=1).status == "timeout"
    _patch_processes(monkeypatch, _Process("0.7.0\n"), _Process("fatal", "boom", returncode=2))
    crashed = ABCROWNVerifier().verify(query)
    assert crashed.status == "error" and crashed.provenance["failure"] == "crash"
    _patch_processes(monkeypatch, _Process("9.9.9\n"))
    drift = ABCROWNVerifier().verify(query)
    assert drift.status == "unsupported" and drift.provenance["failure"] == "version_drift"
    _patch_processes(monkeypatch, _Process("0.7.0\n"), _Process("garbage"))
    malformed = ABCROWNVerifier().verify(query)
    assert malformed.provenance["failure"] == "malformed_output"


def test_unsafe_status_without_assignment_is_not_a_witness(monkeypatch) -> None:
    _patch_processes(monkeypatch, _Process("Result: unsafe-bab\n"))
    result = ABCROWNVerifier(check_version=False).verify(_query())
    assert result.status == "error"
    assert result.provenance["failure"] == "malformed_assignment"


def test_differential_replay_failures_also_block(monkeypatch) -> None:
    left = OracleCheck(_run("sat", native="unsafe-pgd", eligible=False), WitnessCheck(False, "bad"))
    right = OracleCheck(_run("sat", native="unsafe-bab", eligible=False), WitnessCheck(True))
    result = compare_checks(left, right)
    assert not result.stronger_allowed
    assert result.diagnostic == "left SAT witness failed replay"
    right_bad = OracleCheck(_run("sat", native="unsafe-bab", eligible=False), None)
    result = compare_checks(right, right_bad)
    assert result.diagnostic == "right SAT witness failed replay"


def test_compatibility_module_exports_adapter() -> None:
    from reasonsmith.neural_verifiers.alpha_beta_crown import AlphaBetaCrownVerifier

    assert AlphaBetaCrownVerifier is ABCROWNVerifier


def test_resource_limit_child_serializes_without_changing_parent_limits(monkeypatch) -> None:
    import resource

    calls = []
    monkeypatch.setattr(resource, "setrlimit", lambda *args: calls.append(args))
    _limit_child(ABCROWNResourceLimits(cpu_seconds=2, memory_bytes=4096))
    assert len(calls) == 2


def test_constructor_and_process_start_failures_are_nonverdict(monkeypatch) -> None:
    with pytest.raises(ValueError, match="executable"):
        ABCROWNVerifier(executable=[])
    with pytest.raises(ValueError, match="script"):
        ABCROWNVerifier(script="")
    verifier = ABCROWNVerifier(check_version=False)
    _, _, _, failure = verifier._run_command(["/no/such/abcrown"], Path("."), None)
    assert failure == "crash"
    monkeypatch.setattr(
        "reasonsmith.neural_verifiers.abcrown.subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("broken")),
    )
    _, stderr, _, failure = verifier._run_command(["abcrown"], Path("."), None)
    assert failure == "crash" and "broken" in stderr


def test_differential_valid_checks_return_the_raw_comparison() -> None:
    left = OracleCheck(_run("unsat", native="safe", eligible=True), None)
    right = OracleCheck(_run("unsat", native="safe", eligible=True), None)
    result = compare_checks(left, right)
    assert result.agreement and result.stronger_allowed
