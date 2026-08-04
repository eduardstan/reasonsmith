"""The inference-artefact protocol: what a reason can be measured from, and under what premise.

What this module is for:
  reasonsmith owns everything about a reason-adequacy verdict except the notion of a *reason*. The
  strength lattice, the property language, both applicability gates, the engine ladder and the
  audience projections are this package's own; the reason itself was whatever
  `certificate.certify` could enumerate out of one representation — a nesyarena ground program —
  because that representation was named in the only signature the certificate had. This module is
  the abstraction that was missing. `InferenceArtifact` says what a reason-bearing artefact is and
  what it must expose for the deletion probe to measure reasons from it, and
  `artifacts.ground_program.GroundProgramArtifact` is *one* family satisfying it and
  `artifacts.reason_trace.ReasonTraceArtifact` is the second. The knowledge graphs, extracted rule
  sets and decision trees of the paper's own taxonomy are further families: none of those is
  implemented here, and each is an adapter rather than a second special case in `certificate.py`.

  The load-bearing member is `monotone`. The deletion probe defines a reason as *a fact the answer
  would not have been reached without*, and measures it by switching facts off, one at a time. That
  definition is sound on an inference monotone in its facts and silently wrong on one that is not:
  on a system whose reasons can be **retracted** by an added fact — a policy exception evaluated
  after the underwriting rules fire, the ordinary shape of one — a lawfully withdrawn reason is
  indistinguishable from a dropped one, and the duty
  `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` reports a compliant creditor violated. So the
  artefact declares whether its inference is monotone, and where the declaration says no, or says
  nothing, or is refuted by the measurement, the reasons are **not measured** at all.

What a reader must not break:
  - **What the declaration is worth, and what it is not.** It is a claim the system makes about
    itself, of exactly the kind `capabilities()` and `logic()` already are, and §3 of
    `docs/semantics.md` (*The assumption all seven share*) governs it: reasonsmith checks what a
    system says against what a specification asks, and does not check whether the system was
    honest. What is new here is one direction of check. The declaration can be **refuted** by the
    measurement and never confirmed by it: a deletion that moves the engine's answer *up* is a
    fingerprint only a non-monotone inference leaves, so `monotone = True` beside such a probe is a
    declaration the run itself contradicts, and the run is refused. The absence of that fingerprint
    is not evidence of monotonicity — a defeater holding no fact of any enumerated reason is never
    switched off at all, which is the ordinary shape of an exception.
    Why this matters: a self-declared flag nothing checks is a second self-declaration wearing an
    engine's clothes. The precedent is `engines/counterfactual.py`, which consults the `computes`
    declaration to tell a system that provably ignores the protected variable from one that has no
    notion of it — and does not stop at trusting it, cross-checking the encoding with
    `is_definitely_assigned` and `scope.inputs` for the route the declaration cannot see. This is
    the same move one concept over, with the same obligation.
  - **Undeclared is refused, not assumed monotone.** An artefact whose `monotone` is None is
    reported *not evaluated*, naming the declaration.
    Why this matters: defaulting to monotone would leave the declaration worth nothing for exactly
    the population the finding is about — every system built before it existed. The fingerprint
    cannot stand in for it: on the ordinary exception, whose fact is in no rule body, nothing is
    ever switched off and no fingerprint is left. That is the counterfactual engine's
    no-declared-directions branch, asked one concept over.
  - **A family whose reason set is not exact reports one rung lower, and the rung is not optional.**
    An LLM reason trace is not a proof object: a certificate over one claims strictly less than a
    certificate over a ground program and must not report at the same strength. That used to be
    inexpressible, and this paragraph used to say so; `Strength.RECOUNTED` is the rung that says it
    and `report.RequirementResult._validate_reason_set` is the refusal that enforces it. A family
    says which it is with `reasons_are_exact`, and **silence claims the weaker rung** — the opposite
    of `monotone`, deliberately, because here the two answers are not both dangerous: an exact
    family reported `recounted` has understated itself, and understating is the direction this
    package is allowed to fail in.
    Why this matters: the cheap version of this module would take any object that can list something
    reason-shaped and hand its output the rung exact inference earned.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "DECLARATION_REFUTED",
    "DECLARED_NON_MONOTONE",
    "EXACT_REASONS_KEY",
    "MONOTONE_KEY",
    "RECOUNTED_REASONS",
    "UNDECLARED_MONOTONICITY",
    "InferenceArtifact",
    "default_label",
    "deletion_semantics_refusal",
    "reason_set_is_exact",
]

#: The name of the declaration, on an artefact object and in the mapping form of `artifact()`.
MONOTONE_KEY = "monotone"

#: The name of the exactness declaration, on an artefact object and in the mapping form.
EXACT_REASONS_KEY = "reasons_are_exact"


#: Said on every verdict measured from a reason set the system recounted, and the whole of what
#: separates `Strength.RECOUNTED` from `Strength.PROBED`. It is not a caveat on the probe — the
#: probe is the same one — it is a statement about what the probe was run against.
RECOUNTED_REASONS = (
    "the reason set this verdict is measured against is one the system recounted, not one "
    "enumerated from a model encoding, so the probe answers whether the system's own answer "
    "depends on the reasons it says it used and not whether those are all the reasons it had. A "
    "rationale can be complete, or can omit a reason the inference used, and no deletion probe "
    "over the rationale itself can tell the two apart"
)


def reason_set_is_exact(artifact: object) -> bool:
    """Whether this artefact's reasons were enumerated exactly, rather than recounted by the system.

    Read with `getattr` and defaulting to **False**: a family that does not say claims the weaker
    rung. See the module docstring — silence is refused for `monotone` and conceded here, because
    a wrong guess about monotonicity accuses a compliant system while a wrong guess here only
    understates one.
    """
    return bool(getattr(artifact, EXACT_REASONS_KEY, False))


#: Said where an artefact declares its inference non-monotone. The refusal is structural: there is
#: no weaker duty to fall back to and no bucket to hide it in, because the question the probe asks
#: is not the question this artefact can answer.
DECLARED_NON_MONOTONE = (
    "this artefact declares that its inference is not monotone in its facts — adding a fact can "
    "retract a reason that held without it — and the only definition of a reason this tool can "
    "measure is a one-directional deletion probe, which assumes it is. Under that definition a "
    "reason the system lawfully withdrew is indistinguishable from one it dropped by defect, so "
    "measuring here would report a system that stated its reasons correctly as one that did not. "
    "Nothing weaker stands in for the measurement: that the decision states some reason is a "
    "different property, and reporting it under this duty's name is the substitution this duty "
    "exists to refuse"
)

#: Said where an artefact declares nothing. Deliberately not read as monotone: see the module
#: docstring, *Undeclared is refused*.
UNDECLARED_MONOTONICITY = (
    "this artefact does not declare whether its inference is monotone in its facts, and the "
    "deletion probe that measures reasons here is sound only if it is. An artefact that can be "
    "retracted by an added fact and one that cannot produce the same probe and the same count, so "
    "answering either would be answering both. Declaring `monotone` on what `artifact()` returns "
    "is what tells them apart; assuming it would report a system whose reasons are defeasible "
    "violated for having stated its reasons correctly"
)

#: Said where the declaration is monotone and the probe found the fingerprint that contradicts it.
DECLARATION_REFUTED = (
    "this artefact declares its inference monotone in its facts, and the deletion probe measured "
    "the one thing that contradicts it: switching a fact off moved the system's answer *up*. A "
    "monotone inference cannot do that. The declaration is what the deletion definition of a "
    "reason rests on here, so a run that refuted it measures reasons under a definition that does "
    "not apply, and neither a satisfied nor a violated verdict may be read off it"
)


def deletion_semantics_refusal(
    monotone: bool | None, *, refuted_by_measurement: bool = False
) -> str | None:
    """Why the deletion definition of a reason does not apply to this artefact, or None if it does.

    The one place the three refusals are worded, for the reason
    `report.not_evaluated_for_unreachable_trigger` is the one place its own is: the certificate and
    the engine ask the same question about the same artefact, one before measuring and one after,
    and two wordings of it would drift.
    """
    if monotone is None:
        return UNDECLARED_MONOTONICITY
    if not monotone:
        return DECLARED_NON_MONOTONE
    if refuted_by_measurement:
        return DECLARATION_REFUTED
    return None


def default_label(reason: frozenset) -> str:
    """The name a reason carries when its artefact supplies none: the facts themselves."""
    return "{" + ", ".join(sorted(repr(fact) for fact in reason)) + "}"


@runtime_checkable
class InferenceArtifact(Protocol):
    """One decision's inference, in the form the reason-deletion certificate can measure.

    A reason is a set of *facts* — anything hashable and reproducibly `repr`-able, since the probe
    orders them by `repr` and the certificate names them by it. Nothing here is a nesyarena type:
    what a fact is belongs to the family, and the certificate only ever counts, sorts and switches
    them off.

    One member is **optional and deliberately not annotated below**: `reasons_are_exact: bool`, True
    where `reasons()` is an exact enumeration over a model encoding and absent or False where the
    system recounted the set instead. It is read through `reason_set_is_exact` and never off the
    attribute, and it is not a protocol member because a `runtime_checkable` protocol tests every
    annotated member with `hasattr` — declaring it here would make a family that does not mention it
    fail `isinstance`, which is the opposite of a default that claims the weaker rung.
    """

    #: Whether this artefact's inference is monotone in its facts: adding a fact never retracts a
    #: reason that held without it. None where the family cannot say — refused rather than assumed.
    monotone: bool | None


    #: The decision this artefact is the inference behind, named on the certificate.
    query: Any

    #: The engine whose answer is being compared against exact inference, and the semantics it
    #: claims. Both are printed on the certificate and neither is checked.
    engine_name: str
    claimed_semantics: str

    #: How this artefact's reason set was obtained, in the words the certificate prints — e.g.
    #: "bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model
    #: counting". A reader of a certificate cannot weigh it without knowing what enumerated it.
    exact_inference: str

    #: The bound on that enumeration where the family has one, else None. Carried because a
    #: verdict's summary names it as the usual cause of a decision whose reasons were never
    #: enumerated.
    exact_depth: int | None

    def reasons(self) -> tuple[frozenset, ...]:
        """Every reason exact inference finds behind `query`, each as its set of facts."""
        ...

    def label(self, reason: frozenset) -> str:
        """A human name for one reason — a reason code, say. `default_label` is the fallback."""
        ...

    def score(self, reason: frozenset) -> float:
        """This reason's own weight under the base interpretation, for score-ordered attribution."""
        ...

    def exact_value(self) -> float:
        """Exact inference's answer to `query`."""
        ...

    def engine_value(self) -> float:
        """The system's own engine's answer to `query`, on the same inputs."""
        ...

    def without(self, fact: Any) -> InferenceArtifact:
        """The same inference with one fact switched off, and the same reason set to score it over.

        The probe is one-directional by construction of this method: there is no `with_(fact)`, and
        adding one is the level-2 work no verdict here is authorised to rest on. The returned
        artefact must enumerate the *same* reasons — the perturbation is to the interpretation and
        never to what exact inference found — or the drop it reports is a comparison of two
        different questions.
        """
        ...
