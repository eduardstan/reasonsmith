"""Laws that refute a false `claimed_semantics`, from the system's own answers and nothing else.

What this module is for:
  An artefact carries a `claimed_semantics` string; `docs/theory/07-explanation.md`
  states what it is worth
  today: it is printed on the certificate and it is not checked. The claim it makes is universally
  quantified — that the black box `E` *is* the function that semantics names, at every
  interpretation and not only at the one the decision was taken at — so nothing on this evidence
  model establishes it. What can be established is its **refutation**, and this module is that and
  only that.

  The shape is intensional: no reference implementation is computed anywhere in this loop. A
  semantics is characterised by **laws** relating `E` at several interpretations, reasonsmith picks
  the interpretations, the system's own engine answers, and a law that fails is a witness that `E`
  is not the claimed function. Two laws are checked, both consequences of
  `⟦P, β, q⟧ = Pr_β[φ_q]` for the one semantics named here:

    L2 (multilinearity)  E(β) = β(a)·E(β[a↦1]) + (1−β(a))·E(β[a↦0])   for every fact a
    L3 (monotonicity)    E(β[a↦0]) ≤ E(β) ≤ E(β[a↦1])                 for every fact a

  `Pr_β[ψ]` is affine in each fact probability for **every** propositional `ψ` — that is Shannon
  expansion, and it needs no assumption about which facts `ψ` mentions — so L2 refutes without a
  premise about the artefact's enumeration being complete. L3 needs one premise and it is a premise
  this repository already has: the supports are positive, so `φ_q` is monotone and `Pr_β[φ_q]` is
  non-decreasing in each fact.

  `docs/theory/07-explanation.md` §7.7 is the soundness statement in the repository's one notation.

What a reader must not break:
  - **Nothing here is a verdict, a rung or a duty.** This module returns no `RequirementResult`,
    reaches no engine ladder, and is deliberately not under `engines/` — the same standing `ltlf.py`
    has. No shipped pack reads it, so no verdict in this repository moves with it.
    Why this matters: a law set is hand-authored, and a wrong law is a false-accusation machine.
    The two here were argued from the definition of `Pr_β` above and measured against a battery
    (`tests/test_semantic_laws.py`), which is evidence that they discriminate and *not* a proof
    that they never accuse a compliant system. Until that gap is closed, nothing may read this into
    a conformance verdict.
  - **Refutation only, and never the affirmative.** A `LawReport` with no violation says the laws
    were not violated over the probes the report counts, and `LIMITS` says exactly that. It is not
    agreement: refutation is a lower bound on deviation, and the battery measures the gap — one
    provenance deviates on 16 instances and is refuted on 12.
    Why this matters: this is the same asymmetry `docs/theory/07-explanation.md`
    states for the certificate,
    and it is the whole reason a measurement this cheap is allowed to exist at all.
  - **Two vocabularies, and they are not the same set.** `spec.CLAIMED_SEMANTICS` is what an
    artefact may *claim* — closed, and refused at the artefact and certificate boundaries by
    `spec.normalize_claimed_semantics`, so a declaration outside it never reaches this module at
    all. `SEMANTICS_WITH_LAWS` is what this module can *refute*, and it is one of those three
    members. A claim that is admitted and unlawed — `weighted sum`, `free-text rationale` — is
    *not evaluated* naming the claim (`NO_LAWS_FOR_SEMANTICS`), which is about **this tool's** reach
    and not about the system. The subset is derived from `CLAIMED_SEMANTICS` rather than retyped.
    Why this matters: collapsing the two would make an admitted-but-unlawed claim look like a
    refused one, and running the laws of one semantics against the claim of another would refute a
    system for implementing exactly what it said it implements. The reference side of the
    certificate is hard-wired to exact WMC whatever an artefact claims, so a system that honestly
    documents its truncation already measures a value gap; that is the same false accusation one
    layer down.
  - **The perturbation this needs is the widened one and there is no cheaper substitute.**
    A family exposing only `without` reports `NO_INTERPRETATION` — measured, not assumed: neither
    one-directional variant of the triple refutes a top-`k` engine on the battery, because a top-`k`
    engine's kept-proof set is locally constant and the kink only appears where the ranking changes.
    Why this matters: `artifacts/__init__.py` records the reversal this module is the reason for,
    and a substitute that fits inside the old refusal would make that reversal unearned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reasonsmith.artifacts import (
    NO_INTERPRETATION,
    InferenceArtifact,
    admits_interpretation,
)
from reasonsmith.spec import CLAIMED_SEMANTICS, normalize_claimed_semantics

__all__ = [
    "DISTRIBUTION_SEMANTICS",
    "LIMITS",
    "MONOTONICITY",
    "MULTILINEARITY",
    "NO_LAWS_FOR_SEMANTICS",
    "SEMANTICS_WITH_LAWS",
    "LawReport",
    "LawViolation",
    "check_laws",
    "law_refusal",
]

DISTRIBUTION_SEMANTICS = "distribution semantics"

#: The members of `spec.CLAIMED_SEMANTICS` this module has laws for, which is **one** of the three.
#: Two different sets are at work here and collapsing them would be the defect: `CLAIMED_SEMANTICS`
#: is what an artefact may *claim*, closed and refused at the artefact and certificate boundaries;
#: this is what this tool can *refute*, and it stays one member until someone states the laws of a
#: second and shows they refute nobody who implements it. Derived by intersection rather than
#: retyped, so a member renamed there cannot leave a dangling one here
#: (`test_the_law_sets_name_a_subset_of_the_shipped_vocabulary`).
SEMANTICS_WITH_LAWS = tuple(s for s in CLAIMED_SEMANTICS if s == DISTRIBUTION_SEMANTICS)

MULTILINEARITY = "multilinearity"
MONOTONICITY = "monotonicity"

#: Said where the artefact claims a semantics inside the shipped vocabulary that no law here
#: characterises — `weighted sum` and `free-text rationale` today. *Not evaluated* in the sense
#: `docs/semantics.md` §4 gives it: the gap is in this tool. A claim *outside* the vocabulary never
#: reaches this wording, because `spec.normalize_claimed_semantics` refuses it at the artefact and
#: certificate boundaries first.
NO_LAWS_FOR_SEMANTICS = (
    "this artefact claims {claimed!r}, which is a declaration this tool admits and has no law for. "
    "The semantics with laws here is {with_laws}. The gap is in this tool and not in the system, "
    "and a law written for one semantics run against a claim of another would refute a system for "
    "implementing exactly what it said it implements"
)

#: Carried on every report, for the reason `certificate.LIMITS` is.
LIMITS = (
    "These laws can refute the claimed semantics and can never confirm it. A report with no "
    "violation says only that no law failed over the probes it counts, at one decision and one "
    "base interpretation: refutation is a lower bound on deviation, so a system whose answer does "
    "differ from the semantics it claims can still pass here. The probes move one fact at a time "
    "across the whole of [0, 1] and hold every other fact where the decision left it, so a "
    "disagreement that needs two facts moved together is not looked for. And this is a measurement "
    "and not a verdict: no requirement in this repository reads it, and the laws are hand-authored "
    "rather than derived, so a failure is evidence about the engine and not a finding about a duty."
)


@dataclass(frozen=True)
class LawViolation:
    """One law, one fact, and the three answers that failed it."""

    law: str
    fact: Any
    detail: str


@dataclass(frozen=True)
class LawReport:
    """What the battery measured at one decision. `refuted` needs one witness; nothing needs all."""

    claimed_semantics: str
    probes: int
    facts: int
    violations: tuple[LawViolation, ...]
    limits: str = field(default=LIMITS)

    @property
    def refuted(self) -> bool:
        return bool(self.violations)


def law_refusal(artifact: InferenceArtifact) -> str | None:
    """Why these laws cannot be checked against this artefact, or None if they can."""
    if not admits_interpretation(artifact):
        return NO_INTERPRETATION
    raw = getattr(artifact, "claimed_semantics", None)
    claimed = "" if raw is None else normalize_claimed_semantics(raw)
    if claimed not in SEMANTICS_WITH_LAWS:
        return NO_LAWS_FOR_SEMANTICS.format(
            claimed=claimed, with_laws=", ".join(repr(s) for s in SEMANTICS_WITH_LAWS)
        )
    return None


def check_laws(artifact: InferenceArtifact, *, tol: float = 1e-9) -> LawReport | None:
    """Check the laws of the artefact's claimed semantics against the system's own engine.

    Returns None where `law_refusal` gives a reason — call that first if the reason is wanted.
    Costs `2·|F_q| + 1` engine probes, where `F_q` is the union of the artefact's reasons: the
    facts the decision was reached through are the facts the laws are stated over.
    """
    if law_refusal(artifact) is not None:
        return None

    facts = sorted({fact for reason in artifact.reasons() for fact in reason}, key=repr)
    base = artifact.engine_value()
    violations: list[LawViolation] = []
    for fact in facts:
        probability = artifact.probability(fact)
        off = artifact.at(fact, 0.0).engine_value()
        on = artifact.at(fact, 1.0).engine_value()

        expected = probability * on + (1.0 - probability) * off
        if abs(base - expected) > tol:
            violations.append(
                LawViolation(
                    MULTILINEARITY,
                    fact,
                    f"E(base) = {base!r}, but Shannon expansion over this fact at "
                    f"p = {probability!r} gives {expected!r} from E(p:=1) = {on!r} and "
                    f"E(p:=0) = {off!r}. Pr_b[phi] is affine in every fact probability, so this "
                    f"engine is not computing one",
                )
            )
        if off > base + tol or base > on + tol:
            violations.append(
                LawViolation(
                    MONOTONICITY,
                    fact,
                    f"E(p:=0) = {off!r}, E(base) = {base!r}, E(p:=1) = {on!r}, which is not "
                    f"non-decreasing. Pr_b[phi] is non-decreasing in every fact of a positive "
                    f"support, so this engine is not computing one",
                )
            )

    return LawReport(
        claimed_semantics=normalize_claimed_semantics(artifact.claimed_semantics),
        probes=2 * len(facts) + 1,
        facts=len(facts),
        violations=tuple(violations),
    )
