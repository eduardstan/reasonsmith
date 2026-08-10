"""Model-free verification gates for hand-written autoformalisation candidates.

The proposer is intentionally absent.  This module only parses a candidate, compares it with the
requirement's shipped property using the solver helpers in :mod:`reasonsmith.analysis`, and runs it
against the requirement's lawyer-readable gold challenge cases.  It never evaluates a system,
constructs a conformance result object, calls an engine, or produces a verdict.

A candidate is ready for a human only when both ``round_trip_check`` and ``check_challenges`` pass.
Human approval is a separate record in ``docs/refinement.md``; ``signoff`` reports that record but
never treats a pending sign-off as approval.
"""

from __future__ import annotations

import ast
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import z3

from reasonsmith.analysis import _ast_to_z3, _pack_scope, _PackScope
from reasonsmith.rulelang import (
    bare_boolean_names,
    classify_fragment,
    contains_literal,
    is_present,
    measured_magnitude_names,
    parse_property,
)
from reasonsmith.spec import Requirement, list_packs, load_pack

CHALLENGES_DIR = Path(__file__).parent / "challenges"
EXPECTED_LABELS = frozenset({"satisfied", "violated"})
ROUND_TRIP_STATUSES = frozenset({"equivalent", "stronger", "weaker", "incomparable", "refused"})
CHALLENGE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ChallengeCase:
    """One concrete, lawyer-readable record and its expected formula classification."""

    id: str
    kind: Literal["satisfied", "violated", "near-miss"]
    expected: Literal["satisfied", "violated"]
    description: str
    signals: dict[str, Any]


@dataclass(frozen=True)
class ChallengeSet:
    """The gold cases claimed by one requirement."""

    requirement_id: str
    rationale: str
    cases: tuple[ChallengeCase, ...]
    path: Path


@dataclass(frozen=True)
class CaseCheck:
    case_id: str
    expected: str
    actual: str | None
    passed: bool
    error: str = ""


@dataclass(frozen=True)
class ChallengeCheck:
    requirement_id: str
    candidate: str
    cases: tuple[CaseCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.cases) and all(case.passed for case in self.cases)

    @property
    def failures(self) -> tuple[CaseCheck, ...]:
        return tuple(case for case in self.cases if not case.passed)


@dataclass(frozen=True)
class RoundTripCheck:
    requirement_id: str
    baseline: str
    candidate: str
    status: Literal["equivalent", "stronger", "weaker", "incomparable", "refused"]
    witness: str = ""
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "equivalent"

    @property
    def repair_message(self) -> str:
        if self.passed:
            return "candidate is equivalent to the shipped property"
        if self.status == "refused":
            return f"candidate cannot be compared: {self.reason}"
        direction = {
            "stronger": (
                "candidate is stricter than the shipped property; it rejects a case "
                "the baseline accepts"
            ),
            "weaker": (
                "candidate is weaker than the shipped property; it accepts a case "
                "the baseline rejects"
            ),
            "incomparable": "candidate and shipped property disagree in both directions",
        }[self.status]
        suffix = f" Counterexample: {self.witness}." if self.witness else ""
        return direction + suffix


@dataclass(frozen=True)
class SignOff:
    requirement_id: str
    status: str
    record: str

    @property
    def signed(self) -> bool:
        return self.status == "signed-off"




@dataclass(frozen=True)
class CandidateVerification:
    """The three gate records for one candidate; no conformance result is represented."""

    round_trip: RoundTripCheck
    challenges: ChallengeCheck
    signoff: SignOff

    @property
    def machine_passed(self) -> bool:
        return self.round_trip.passed and self.challenges.passed

    @property
    def acceptable(self) -> bool:
        return self.machine_passed and self.signoff.signed


class _ChallengeScope(_PackScope):
    """The analysis scope with every input pinned to one challenge record."""

    def __init__(self, var_types: dict[str, str], signals: dict[str, Any]):
        super().__init__(var_types)
        self.signals = signals

    def read(self, name: str) -> Any:
        if name not in self.signals:
            raise ValueError(
                f"challenge case does not provide a value for bare signal {name!r}; "
                "add it to [case.signals]"
            )
        value = self.signals[name]
        kind = str(self.var_types.get(name, "real")).lower()
        if kind in {"bool", "boolean"}:
            if not isinstance(value, bool):
                raise ValueError(f"challenge signal {name!r} must be true or false")
            return z3.BoolVal(value)
        if kind in {"int", "integer"}:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"challenge signal {name!r} must be an integer")
            return z3.IntVal(value)
        if kind in {"str", "string"}:
            if not isinstance(value, str):
                raise ValueError(f"challenge signal {name!r} must be text")
            return z3.StringVal(value)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"challenge signal {name!r} must be numeric")
        return z3.RealVal(value)

    def present(self, name: str) -> Any:
        return z3.BoolVal(name in self.signals and is_present(self.signals[name]))

    def contains(self, signal: str, phrase: str) -> Any:
        value = self.signals.get(signal)
        return z3.BoolVal(contains_literal(value, phrase) if signal in self.signals else False)


def _requirement_index() -> dict[str, Requirement]:
    requirements = [req for name in list_packs() for req in load_pack(name).requirements]
    result: dict[str, Requirement] = {}
    for req in requirements:
        if req.id in result:
            raise ValueError(f"duplicate shipped requirement id {req.id!r}")
        result[req.id] = req
    return result


def _load_file(path: Path) -> ChallengeSet:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    allowed = {"requirement", "rationale", "case"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"{path}: unknown top-level field(s): {', '.join(sorted(extra))}")
    req_id = raw.get("requirement")
    rationale = raw.get("rationale")
    if not isinstance(req_id, str) or not req_id:
        raise ValueError(f"{path}: requirement must be a non-empty string")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError(f"{path}: rationale must explain the lawyer-facing case design")
    raw_cases = raw.get("case", [])
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError(f"{path}: challenge set must contain at least one [[case]]")
    cases: list[ChallengeCase] = []
    ids: set[str] = set()
    for index, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: case {index + 1} is not a table")
        required = {"id", "kind", "expected", "description", "signals"}
        missing = required - set(item)
        extra_case = set(item) - required
        if missing or extra_case:
            raise ValueError(
                f"{path}: case {index + 1} fields mismatch; missing {sorted(missing)}, "
                f"unknown {sorted(extra_case)}"
            )
        case_id = item["id"]
        kind = item["kind"]
        expected = item["expected"]
        description = item["description"]
        signals = item["signals"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError(f"{path}: case ids must be unique non-empty strings")
        if kind not in {"satisfied", "violated", "near-miss"}:
            raise ValueError(f"{path}: {case_id}: kind must be satisfied, violated, or near-miss")
        if expected not in EXPECTED_LABELS:
            raise ValueError(f"{path}: {case_id}: expected must be satisfied or violated")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"{path}: {case_id}: description is required for legal readability")
        if not isinstance(signals, dict):
            raise ValueError(f"{path}: {case_id}: signals must be a table")
        ids.add(case_id)
        cases.append(ChallengeCase(case_id, kind, expected, description, dict(signals)))
    kinds = {case.kind for case in cases}
    if not {"satisfied", "violated"} <= kinds:
        raise ValueError(f"{path}: include both satisfied and violated challenge cases")
    if "near-miss" not in kinds:
        raise ValueError(f"{path}: include at least one near-miss case")
    return ChallengeSet(req_id, rationale, tuple(cases), path)


def load_challenge_sets(directory: Path | None = None) -> dict[str, ChallengeSet]:
    """Load and validate every shipped gold challenge set.

    The two-way requirement check is deliberate: an orphan set is as dangerous as an absent one.
    """
    directory = directory or CHALLENGES_DIR
    paths = sorted(directory.glob("*.toml")) if directory.is_dir() else []
    manifest_path = directory / "manifest.toml"
    manifest_ids: set[str] | None = None
    if manifest_path.is_file():
        with manifest_path.open("rb") as stream:
            manifest = tomllib.load(stream)
        if set(manifest) != {"schema_version", "requirements"}:
            raise ValueError(f"{manifest_path}: fields must be schema_version and requirements")
        if manifest["schema_version"] != CHALLENGE_SCHEMA_VERSION:
            raise ValueError(f"{manifest_path}: unsupported schema version")
        if not isinstance(manifest["requirements"], list) or not all(
            isinstance(item, str) and item for item in manifest["requirements"]
        ):
            raise ValueError(f"{manifest_path}: requirements must be a list of ids")
        manifest_ids = set(manifest["requirements"])
        if len(manifest_ids) != len(manifest["requirements"]):
            raise ValueError(f"{manifest_path}: duplicate requirement id")
    sets: dict[str, ChallengeSet] = {}
    requirements = _requirement_index()
    for path in paths:
        if path.name == "manifest.toml":
            continue
        challenge = _load_file(path)
        if challenge.requirement_id not in requirements:
            raise ValueError(f"{path}: no shipped requirement claims {challenge.requirement_id!r}")
        if challenge.requirement_id in sets:
            raise ValueError(f"multiple challenge sets claim {challenge.requirement_id!r}")
        if manifest_ids is not None and challenge.requirement_id not in manifest_ids:
            raise ValueError(
                f"{path}: requirement {challenge.requirement_id!r} is not listed in manifest.toml"
            )
        sets[challenge.requirement_id] = challenge
    if manifest_ids is not None:
        missing = sorted(manifest_ids - set(sets))
        if missing:
            raise ValueError(
                "manifest.toml claims requirement(s) with no challenge set: " + ", ".join(missing)
            )
        orphan = sorted(set(sets) - manifest_ids)
        if orphan:
            raise ValueError(
                "challenge set(s) are not listed in manifest.toml: " + ", ".join(orphan)
            )
    return sets


def challenge_requirements() -> frozenset[str]:
    """Requirement ids with an executable gold set."""
    return frozenset(load_challenge_sets())


def _node(formula: str) -> ast.Expression:
    return parse_property(formula)


def _formula(scope: _PackScope, node: ast.Expression) -> Any:
    value = _ast_to_z3(node, scope)
    if not z3.is_bool(value):
        raise ValueError(f"{ast.unparse(node)!r} is not a Boolean property")
    return value


def _model_witness(model: z3.ModelRef, scope: _PackScope) -> str:
    values: list[str] = []
    for label, atom in getattr(scope, "_atoms", {}).items():
        values.append(f"{label}={model.eval(atom, model_completion=True)}")
    for name, atom in scope.current.items():
        if not any(name == label for label in getattr(scope, "_atoms", {})):
            values.append(f"{name}={model.eval(atom, model_completion=True)}")
    return ", ".join(values) or "a solver assignment"


def _direction(
    assertions: list[Any], formula: Any, scope: _PackScope, timeout_ms: int
) -> tuple[bool | None, str]:
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(*assertions, formula)
    result = solver.check()
    if result == z3.unsat:
        return True, ""
    if result == z3.unknown:
        return None, "solver returned unknown"
    return False, _model_witness(solver.model(), scope)


def _challenge_result(candidate: str, case: ChallengeCase) -> str:
    node = _node(candidate)
    var_types: dict[str, str] = {name: "bool" for name in bare_boolean_names(node)}
    var_types.update({name: "real" for name in measured_magnitude_names(node)})
    scope = _ChallengeScope(var_types, case.signals)
    value = _formula(scope, node)
    solver = z3.Solver()
    solver.add(value)
    result = solver.check()
    return "satisfied" if result == z3.sat else "violated"


def check_challenges(
    requirement: Requirement | str, candidate: str, *, directory: Path | None = None
) -> ChallengeCheck:
    """Run a candidate against its requirement's gold cases, without a system or a verdict."""
    req = _requirement_index()[requirement] if isinstance(requirement, str) else requirement
    sets = load_challenge_sets(directory)
    challenge = sets.get(req.id)
    if challenge is None:
        raise ValueError(f"{req.id}: no gold challenge set is claimed")
    try:
        _node(candidate)
        actual_fragment = classify_fragment(candidate)
        if actual_fragment != req.formalism:
            raise ValueError(
                f"candidate fragment {actual_fragment!r} does not match requirement "
                f"fragment {req.formalism!r}"
            )
    except Exception as exc:
        return ChallengeCheck(req.id, candidate, tuple(
            CaseCheck(case.id, case.expected, None, False, str(exc)) for case in challenge.cases
        ))
    checks: list[CaseCheck] = []
    for case in challenge.cases:
        try:
            actual = _challenge_result(candidate, case)
            checks.append(CaseCheck(case.id, case.expected, actual, actual == case.expected))
        except Exception as exc:
            checks.append(CaseCheck(case.id, case.expected, None, False, str(exc)))
    return ChallengeCheck(req.id, candidate, tuple(checks))


def round_trip_check(
    requirement: Requirement | str,
    candidate: str,
    *,
    timeout_ms: int = 5000,
) -> RoundTripCheck:
    """Compare a candidate with the shipped property using the existing solver encoding.

    ``equivalent`` is the only passing relation.  Stronger, weaker and incomparable candidates are
    returned with a solver witness so a proposer or human can repair the text explicitly; nothing
    is rewritten here.  Temporal formulas use the existing optional LTLf adapter and therefore
    refuse clearly when that backend is unavailable.
    """
    req = _requirement_index()[requirement] if isinstance(requirement, str) else requirement
    baseline = req.spec
    try:
        candidate_node = _node(candidate)
        actual_fragment = classify_fragment(candidate)
        if actual_fragment != req.formalism:
            raise ValueError(
                f"candidate fragment {actual_fragment!r} does not match requirement "
                f"fragment {req.formalism!r}"
            )
        if req.formalism == "temporal":
            from reasonsmith.ltlf import Abstraction, available, entails, to_ltlf

            if not available():
                raise ValueError("LTLf round-trip requires the optional BLACK solver")
            abstraction = Abstraction()
            left = to_ltlf(baseline, abstraction)
            right = to_ltlf(candidate, abstraction)
            left_to_right = entails(left, right, abstraction)
            right_to_left = entails(right, left, abstraction)
        else:
            base_node = _node(baseline)
            scope = _pack_scope([base_node, candidate_node])
            base_value = _formula(scope, base_node)
            candidate_value = _formula(scope, candidate_node)
            assertions = list(scope.axioms)
            base_to_candidate, witness_bc = _direction(
                assertions, z3.And(base_value, z3.Not(candidate_value)), scope, timeout_ms
            )
            candidate_to_base, witness_cb = _direction(
                assertions, z3.And(candidate_value, z3.Not(base_value)), scope, timeout_ms
            )
            if base_to_candidate is None or candidate_to_base is None:
                raise ValueError(
                    base_to_candidate or candidate_to_base or "solver returned unknown"
                )
            left_to_right = base_to_candidate
            right_to_left = candidate_to_base
            witness_bc, witness_cb = witness_bc, witness_cb
            if left_to_right and right_to_left:
                return RoundTripCheck(req.id, baseline, candidate, "equivalent")
            if right_to_left:
                return RoundTripCheck(req.id, baseline, candidate, "stronger", witness_bc)
            if left_to_right:
                return RoundTripCheck(req.id, baseline, candidate, "weaker", witness_cb)
            return RoundTripCheck(
                req.id, baseline, candidate, "incomparable", witness_bc or witness_cb
            )
        if left_to_right and right_to_left:
            return RoundTripCheck(req.id, baseline, candidate, "equivalent")
        if right_to_left:
            return RoundTripCheck(req.id, baseline, candidate, "stronger")
        if left_to_right:
            return RoundTripCheck(req.id, baseline, candidate, "weaker")
        return RoundTripCheck(req.id, baseline, candidate, "incomparable")
    except Exception as exc:
        return RoundTripCheck(req.id, baseline, candidate, "refused", reason=str(exc))


def signoff(requirement: Requirement | str, refinement: Path | None = None) -> SignOff:
    """Read the explicit human sign-off marker on the requirement's refinement row."""
    req = _requirement_index()[requirement] if isinstance(requirement, str) else requirement
    path = refinement or Path(__file__).resolve().parents[2] / "docs" / "refinement.md"
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("|") and len(line.split("|")) > 1 and f"`{req.id}`" in line.split("|")[1]
    ]
    if len(lines) != 1:
        return SignOff(req.id, "missing", "no unique refinement row")
    line = lines[0]
    marker = "human sign-off:"
    lower = line.lower()
    if marker not in lower:
        return SignOff(req.id, "missing", line)
    record = line[lower.index(marker) + len(marker):].strip()
    status = record.split()[0].strip("*._,:;()[]").lower() if record else "missing"
    return SignOff(req.id, status, record)


def verify_candidate(
    requirement: Requirement | str, candidate: str, *, refinement: Path | None = None
) -> CandidateVerification:
    """Run both machine gates and read the independent human sign-off record."""
    return CandidateVerification(
        round_trip_check(requirement, candidate),
        check_challenges(requirement, candidate),
        signoff(requirement, refinement),
    )


def candidate_ready(requirement: Requirement | str, candidate: str) -> bool:
    """Whether both machine gates pass; human sign-off remains a separate, explicit gate."""
    return verify_candidate(requirement, candidate).machine_passed


def candidate_acceptable(
    requirement: Requirement | str, candidate: str, *, refinement: Path | None = None
) -> bool:
    """Whether all three gates pass, including an explicit human sign-off row."""
    return verify_candidate(requirement, candidate, refinement=refinement).acceptable


__all__ = [
    "CHALLENGE_SCHEMA_VERSION",
    "CandidateVerification",
    "CaseCheck",
    "ChallengeCase",
    "ChallengeCheck",
    "ChallengeSet",
    "RoundTripCheck",
    "SignOff",
    "candidate_ready",
    "candidate_acceptable",
    "verify_candidate",
    "challenge_requirements",
    "check_challenges",
    "load_challenge_sets",
    "round_trip_check",
    "signoff",
]
