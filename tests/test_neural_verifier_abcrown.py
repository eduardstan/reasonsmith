"""Slice-6 alpha-beta-CROWN status and differential contract tests."""

from __future__ import annotations

import pytest

from reasonsmith.neural_queries import VerifierRun
from reasonsmith.neural_verifiers.abcrown import (
    ABCROWN_NATIVE_STATUSES,
    COMPLETE_MODE,
    ABCROWNVerifier,
    map_abcrown_status,
    parse_abcrown_status,
)
from reasonsmith.neural_verifiers.differential import compare_runs


@pytest.mark.parametrize(
    "native", ("unsafe-pgd", "unsafe-bab", "safe-incomplete", "complete-safe", "timeout", "unknown")
)
def test_native_statuses_are_explicitly_distinct(native: str) -> None:
    assert native in ABCROWN_NATIVE_STATUSES
    assert parse_abcrown_status(f"Result: {native}\n") == native


def test_status_mapping_keeps_safe_incomplete_below_proof() -> None:
    assert map_abcrown_status("safe-incomplete") == ("unsat", False, "incomplete-bound")
    assert map_abcrown_status("complete-safe")[1] is True


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

    def __init__(self, stdout: str):
        self.stdout = stdout
        self.stderr = ""

    def communicate(self, timeout=None):
        return self.stdout, self.stderr


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
