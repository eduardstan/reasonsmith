"""Optional model-facing autoformalisation proposer.

The proposer is deliberately a thin model boundary.  It asks a configured model for one
``rulelang`` formula, then hands that text to :mod:`reasonsmith.autoformalize`.  The model never
produces a conformance result: a machine-cleared candidate is only a proposal for the independent
human sign-off recorded in ``docs/refinement.md``.

The optional ``proposer`` extra has no Python dependency, just as the ``ltlf`` extra has no Python
dependency: the default transport is the separately installed Ollama service.  Absence of a
configured model or service is returned as a first-class refusal.  A caller may supply a callable
instead, which keeps the boundary useful for another model provider and for deterministic tests.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal, Protocol

from reasonsmith.autoformalize import (
    CandidateVerification,
    challenge_requirements,
    load_challenge_sets,
    verify_candidate,
)
from reasonsmith.rulelang import classify_fragment, parse_property
from reasonsmith.spec import Requirement, list_packs, load_pack

PROPOSER_EXTRA = "proposer"
PROPOSER_MODEL_ENV = "REASONSMITH_PROPOSER_MODEL"
PROPOSER_URL_ENV = "REASONSMITH_PROPOSER_URL"
PROPOSER_COMMAND_ENV = "REASONSMITH_PROPOSER_COMMAND"
DEFAULT_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_ATTEMPTS = 3
UNAVAILABLE_NOTE = (
    "model proposer unavailable: configure REASONSMITH_PROPOSER_MODEL and an Ollama service "
    "(or supply a model callable); no candidate was guessed"
)


class Model(Protocol):
    def __call__(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class ProposalAttempt:
    """One model response and the evidence returned by the existing verification gates."""

    number: int
    prompt: str
    candidate: str | None
    verification: CandidateVerification | None
    refusal: str = ""

    @property
    def machine_passed(self) -> bool:
        return self.verification is not None and self.verification.machine_passed


@dataclass(frozen=True)
class Proposal:
    """The bounded proposal conversation, never a conformance or engine result."""

    requirement_id: str
    attempts: tuple[ProposalAttempt, ...]
    attempt_budget: int
    status: Literal["proposed", "refused", "unavailable", "budget-exhausted"]
    refusal: str = ""

    @property
    def machine_passed(self) -> bool:
        return any(attempt.machine_passed for attempt in self.attempts)

    @property
    def candidate(self) -> str | None:
        for attempt in self.attempts:
            if attempt.machine_passed:
                return attempt.candidate
        return None


@dataclass(frozen=True)
class AgreementRow:
    requirement_id: str
    status: str
    candidate: str | None
    attempts: int
    refusal: str = ""


@dataclass(frozen=True)
class AgreementMeasurement:
    """Agreement against the shipped property over the complete challenge-set sample."""

    rows: tuple[AgreementRow, ...]
    model: str
    attempt_budget: int

    @property
    def sample_size(self) -> int:
        return len(self.rows)

    @property
    def agreements(self) -> int:
        return sum(row.status == "agreed" for row in self.rows)

    @property
    def rate(self) -> float:
        return self.agreements / self.sample_size if self.sample_size else 0.0


class CommandModel:
    """Callable provider adapter for any configured command reading a prompt on stdin."""

    def __init__(self, command: str, *, timeout: float = 120.0):
        self.command = command.strip()
        if not self.command:
            raise ValueError("provider command must be non-empty")
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        try:
            result = subprocess.run(
                shlex.split(self.command),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ModelUnavailable(str(exc)) from exc
        if result.returncode:
            message = result.stderr.strip() or f"provider exited with {result.returncode}"
            raise ModelUnavailable(message)
        return result.stdout


class OllamaModel:
    """Callable Ollama ``/api/generate`` transport; model selection is caller configuration."""

    def __init__(self, model: str, *, url: str = DEFAULT_URL, timeout: float = 120.0):
        if not model.strip():
            raise ValueError("model name must be non-empty")
        self.model = model
        self.url = url
        self.timeout = timeout

    def __call__(self, prompt: str) -> str:
        body = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise ModelUnavailable(str(exc)) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
            raise ModelUnavailable("model response was not an Ollama response with text")
        return payload["response"]


class ModelUnavailable(RuntimeError):
    """The configured model boundary could not be reached."""


def model_from_environment(*, timeout: float = 120.0) -> tuple[Model | None, str, str]:
    """Build the configured model transport without selecting a model in source code."""
    command = os.getenv(PROPOSER_COMMAND_ENV, "").strip()
    model = os.getenv(PROPOSER_MODEL_ENV, "").strip()
    if command:
        return CommandModel(command, timeout=timeout), model or command, ""
    if not model:
        return None, "", UNAVAILABLE_NOTE
    url = os.getenv(PROPOSER_URL_ENV, DEFAULT_URL)
    return OllamaModel(model, url=url, timeout=timeout), model, ""


def _requirements() -> dict[str, Requirement]:
    result: dict[str, Requirement] = {}
    for pack_name in list_packs():
        for requirement in load_pack(pack_name).requirements:
            if requirement.id in result:
                raise ValueError(f"duplicate shipped requirement id {requirement.id!r}")
            result[requirement.id] = requirement
    return result


def _challenge_prompt(requirement: Requirement) -> str:
    challenge = load_challenge_sets()[requirement.id]
    signals = sorted({name for case in challenge.cases for name in case.signals})
    cases = "\n".join(
        f"- {case.id}: {case.description}; signals={json.dumps(case.signals, sort_keys=True)}"
        for case in challenge.cases
    )
    return f"""You propose a formal property for a human reviewer. Return ONLY one formula
accepted by
reasonsmith.rulelang.parse_property: no Markdown, explanation, quotation marks, or code fence.
Do not return a verdict. Requirement id: {requirement.id}
The required fragment is {requirement.formalism!r}.
Clause: {requirement.verbatim_text}
Rationale: {requirement.rationale}
Available signal names: {', '.join(signals)}
Gold challenge records (their labels are withheld from you):
{cases}
"""


def _repair_prompt(
    requirement: Requirement, previous: str, verification: CandidateVerification
) -> str:
    failures = "\n".join(
        f"- {case.case_id}: expected {case.expected}, got {case.actual}; {case.error}"
        for case in verification.challenges.failures
    ) or "- no challenge evidence"
    return f"""Repair your previous proposed formula for the same requirement. Return ONLY one
complete
formula accepted by reasonsmith.rulelang.parse_property; do not explain it and do not rewrite it
outside the repository's language. Requirement id: {requirement.id}
The required fragment is {requirement.formalism!r}.
Previous candidate: {previous}
Round-trip evidence: {verification.round_trip.repair_message}
Gold-case failures:
{failures}
Clause: {requirement.verbatim_text}
Rationale: {requirement.rationale}
"""


def _strict_candidate(text: object, requirement: Requirement) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("model response was not a non-empty formula string")
    candidate = text.strip()
    parse_property(candidate)
    fragment = classify_fragment(candidate)
    if fragment != requirement.formalism:
        raise ValueError(
            f"candidate fragment {fragment!r} does not match requirement fragment "
            f"{requirement.formalism!r}"
        )
    return candidate


def propose(
    requirement: Requirement | str,
    *,
    model: Model | None = None,
    model_name: str | None = None,
    max_attempts: int = DEFAULT_ATTEMPTS,
) -> Proposal:
    """Ask a configured model for a candidate and boundedly repair failed candidates.

    Verification evidence, not a harness rewrite, is the only repair instruction.  ``proposed``
    means both machine gates passed; it does not mean a human accepted the formalisation.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    req = _requirements()[requirement] if isinstance(requirement, str) else requirement
    selected_name = model_name or os.getenv(PROPOSER_MODEL_ENV, "").strip()
    if model is None:
        command = os.getenv(PROPOSER_COMMAND_ENV, "").strip()
        if command:
            model = CommandModel(command)
            selected_name = selected_name or command
        elif not selected_name:
            return Proposal(req.id, (), max_attempts, "unavailable", UNAVAILABLE_NOTE)
        else:
            model = OllamaModel(
                selected_name,
                url=os.getenv(PROPOSER_URL_ENV, DEFAULT_URL),
            )
    elif not selected_name:
        selected_name = getattr(model, "model", "callable-model")

    prompt = _challenge_prompt(req)
    attempts: list[ProposalAttempt] = []
    for number in range(1, max_attempts + 1):
        try:
            raw = model(prompt)
            candidate = _strict_candidate(raw, req)
        except ModelUnavailable as exc:
            return Proposal(req.id, tuple(attempts), max_attempts, "unavailable", str(exc))
        except Exception as exc:
            attempts.append(ProposalAttempt(number, prompt, None, None, str(exc)))
            prompt = (
                f"The previous response was refused: {exc}. Return only one complete formula in "
                f"the {req.formalism} fragment for this requirement.\n{prompt}"
            )
            continue
        verification = verify_candidate(req, candidate)
        attempts.append(ProposalAttempt(number, prompt, candidate, verification))
        if verification.machine_passed:
            return Proposal(req.id, tuple(attempts), max_attempts, "proposed")
        prompt = _repair_prompt(req, candidate, verification)
    if attempts and all(attempt.candidate is None for attempt in attempts):
        return Proposal(req.id, tuple(attempts), max_attempts, "refused", attempts[-1].refusal)
    return Proposal(
        req.id, tuple(attempts), max_attempts, "budget-exhausted", "attempt budget exhausted"
    )


def measure_agreement(
    *,
    model: Model | None = None,
    model_name: str | None = None,
    max_attempts: int = DEFAULT_ATTEMPTS,
) -> AgreementMeasurement:
    """Measure machine-cleared agreement for every shipped gold challenge set."""
    rows: list[AgreementRow] = []
    for requirement_id in sorted(challenge_requirements()):
        result = propose(
            requirement_id, model=model, model_name=model_name, max_attempts=max_attempts
        )
        rows.append(
            AgreementRow(
                requirement_id,
                "agreed" if result.machine_passed else result.status,
                result.candidate,
                len(result.attempts),
                result.refusal,
            )
        )
    selected = model_name or os.getenv(PROPOSER_MODEL_ENV, "") or "unconfigured"
    return AgreementMeasurement(tuple(rows), selected, max_attempts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="measure model proposals against gold challenge sets"
    )
    parser.add_argument("--model", default=None, help=f"Ollama model (or {PROPOSER_MODEL_ENV})")
    parser.add_argument("--url", default=None, help=f"Ollama endpoint (or {PROPOSER_URL_ENV})")
    parser.add_argument(
        "--command",
        default=None,
        help=f"provider command reading prompt on stdin (or {PROPOSER_COMMAND_ENV})",
    )
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    args = parser.parse_args(argv)
    if args.model:
        os.environ[PROPOSER_MODEL_ENV] = args.model
    if args.url:
        os.environ[PROPOSER_URL_ENV] = args.url
    if args.command:
        os.environ[PROPOSER_COMMAND_ENV] = args.command
    measurement = measure_agreement(model_name=args.model, max_attempts=args.attempts)
    print(json.dumps({
        "model": measurement.model,
        "attempt_budget": measurement.attempt_budget,
        "sample_size": measurement.sample_size,
        "agreements": measurement.agreements,
        "agreement_rate": measurement.rate,
        "rows": [row.__dict__ for row in measurement.rows],
    }, indent=2, sort_keys=True))
    return 0 if measurement.sample_size and measurement.agreements == measurement.sample_size else 1


__all__ = [
    "AgreementMeasurement",
    "AgreementRow",
    "CommandModel",
    "DEFAULT_ATTEMPTS",
    "ModelUnavailable",
    "OllamaModel",
    "PROPOSER_EXTRA", "Proposal", "ProposalAttempt", "UNAVAILABLE_NOTE", "measure_agreement",
    "model_from_environment", "propose",
]

if __name__ == "__main__":
    raise SystemExit(main())
