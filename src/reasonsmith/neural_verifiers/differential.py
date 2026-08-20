"""Differential checks for independent neural verifiers.

This is a diagnostic boundary, not a voting system.  A semantic disagreement blocks any stronger
claim until the witness, query, or configuration explains it.  Every unsafe result still requires
the normal ``verify_query`` witness replay before it can be used.
"""

from __future__ import annotations

from dataclasses import dataclass

from reasonsmith.neural_queries import OracleCheck, VerifierRun


@dataclass(frozen=True, slots=True)
class DifferentialResult:
    left: VerifierRun
    right: VerifierRun
    agreement: bool
    stronger_allowed: bool
    diagnostic: str | None = None

    @property
    def disagreement(self) -> bool:
        return not self.agreement


def _semantic(run: VerifierRun) -> str:
    native = str(run.provenance.get("semantic_status", "")).lower()
    if native in {"attack-witness", "branch-and-bound-witness"} or run.status == "sat":
        return "unsafe"
    if native in {"incomplete-bound", "complete-proof-candidate"} or run.status == "unsat":
        return "safe"
    if run.status == "timeout":
        return "timeout"
    if run.status == "unknown":
        return "unknown"
    return "inconclusive"


def compare_runs(left: VerifierRun, right: VerifierRun) -> DifferentialResult:
    """Compare two raw runs without selecting a winner.

    A pair is stronger only when both runs agree semantically and both are independently eligible.
    In particular, a safe-incomplete result cannot be promoted because another verifier says safe.
    """
    left_kind, right_kind = _semantic(left), _semantic(right)
    agreement = left_kind == right_kind
    eligible = bool(left.provenance.get("verdict_eligible")) and bool(
        right.provenance.get("verdict_eligible")
    )
    diagnostic = None
    if not agreement:
        diagnostic = (
            "independent verifier disagreement: "
            f"{left.verifier}={left.provenance.get('native_status', left.status)} vs "
            f"{right.verifier}={right.provenance.get('native_status', right.status)}; "
            "reproduce the witness or explain the query/configuration before strengthening"
        )
    elif not eligible:
        diagnostic = (
            "agreement does not establish a stronger result: at least one run "
            "is not verdict-eligible"
        )
    return DifferentialResult(left, right, agreement, agreement and eligible, diagnostic)


def compare_checks(left: OracleCheck, right: OracleCheck) -> DifferentialResult:
    """Compare verifier checks, retaining witness failures as a blocking diagnostic."""
    result = compare_runs(left.run, right.run)
    if left.run.status == "sat" and (left.witness is None or not left.witness.valid):
        return DifferentialResult(
            result.left, result.right, result.agreement, False, "left SAT witness failed replay"
        )
    if right.run.status == "sat" and (right.witness is None or not right.witness.valid):
        return DifferentialResult(
            result.left, result.right, result.agreement, False, "right SAT witness failed replay"
        )
    return result


__all__ = ["DifferentialResult", "compare_checks", "compare_runs"]
