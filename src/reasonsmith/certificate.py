"""The reason-deletion certificate.

What this module is for:
  Compares an engine's output against exact inference ground truth. Using deletion probes, it tests
  whether disabling isolated facts changes engine output, attributing dropped reasons to proof
  truncation or inference settings.

  It reads its inputs through `artifacts.InferenceArtifact` and names no representation: what a
  fact is, what enumerated the reasons and what switching one off means all belong to the artefact.
  A nesyarena ground program is one such artefact (`artifacts/ground_program.py`) and `certify` is
  that family's entry point; `certify_artifact` is the protocol's.

  Deletion probe mechanism, in two passes:
    A reason r with a private fact (one no other exact reason uses) is switched off by asking the
    artefact for the same inference `without` that fact. Exact inference loses r's exclusive
    contribution. Every private fact of r is switched off, one at a time, and one that moves the
    engine settles r **live** — a contrastive set of size one, and sound on its own.

    A reason no such single deletion moves is *not* thereby deleted, and reporting it so was this
    instrument's sharpest defect: two reasons jointly necessary and individually removable each
    leave the engine's answer where it was, so both were reported deleted and a system was accused
    of omitting two reasons its inference demonstrably used. So a second pass asks the question the
    first one cannot: `explanations.contrastive_sets` enumerates the subset-minimal *joint*
    deletions the engine notices, and a reason is deleted only where that enumeration **terminated**
    and met no fact of it. `docs/sufficient-reasons.md` is the definition, with the lemmas and the
    published sources; this module is its measurement.

What a reader must not break:
  - The probe only ever switches a fact *off*. It never raises one and it never adds a fact — this
    module calls `without` and nothing else, and a family offering the wider `at(fact, probability)`
    is probed here exactly as one offering only `without` is
    (`test_the_deletion_probe_never_reaches_the_widened_perturbation`) — so `deleted` means "the
    engine's answer did not depend on this reason under this interpretation" and nothing stronger.
    Why this matters: on an engine whose reasons can be *retracted* by an added fact, a lawfully
    retracted reason is indistinguishable from a dropped one under this definition. That is why an
    artefact declares whether its inference is monotone, why a certificate over one that declares
    it is not carries no verdict (`Certificate.verdict`, `deletion_semantics_refusal`), and why
    `engines/certificate.py` refuses such an artefact before measuring it rather than after.
    The one fingerprint such an engine leaves is a deletion that moves its answer *up*, which is
    why the sign of `engine_drop` is kept rather than taken in absolute value, reported as
    `ReasonVerdict.non_monotone` / `Certificate.non_monotone` — and, where the artefact declared
    itself monotone, is the measurement that refutes the declaration.
  - Both independent checks must pass for a certificate to pass: the deletion probe
    (every reason live) and the value check against the exact oracle. Neither check
    subsumes the other.
    Why this matters: An engine that uses every reason but weights them wrongly passes the probe;
    the value check is what catches that. Conversely, an engine that drops a reason and
    compensates its value back onto the exact one passes the value check; the deletion probe is
    what catches that, and it names the reason that stopped mattering.
  - A reason with no private fact cannot be switched off alone (`unseparable`) and returns
    `INCONCLUSIVE`.
    Why this matters: Reasons sharing all facts cannot be probed in isolation, so dependency
    cannot be proven and is never assumed live.
  - The three not-certified states are kept apart. `unseparable` is a reason with no fact to
    attribute a movement to; `inconclusive` is a probe that carried no exact signal at all;
    `undetermined` is a reason the joint enumeration did not resolve — because its budget ran out,
    or because the only relevant fact it holds is shared with another reason. `uncertified` is
    still their union, because all three mean the same thing to a verdict.
    Why this matters: one bucket for three different facts about the evidence told a reader that a
    reason was not certified without telling them what was missing, and the budget-exhausted case
    would have been silent in it.
  - `deleted` is universal over the contrastive sets and is therefore claimed only on an
    `exhaustive` search; `live` is existential and one contrastive set establishes it.
    Why this matters: a shorter search must name *fewer* missing reasons and never more. There must
    be no setting of the budget at which this instrument accuses a system it would otherwise have
    cleared.
  - A probe whose exact-side drop is zero carries no signal and is reported `inconclusive`.
    Why this matters: Zero drop means the private fact already had zero probability, producing no
    measurable signal.
  - A query with no enumerated reasons is never a `PASS` (returns `INCONCLUSIVE` or `FAIL`).
    Why this matters: a zero value gap does not establish a deleted reason was measured; exact
    inference may have evaluated the query while finding no sufficient reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from reasonsmith.artifacts import (
    InferenceArtifact,
    deletion_semantics_refusal,
    reference_semantics,
)
from reasonsmith.explanations import (
    DEFAULT_PROBE_BUDGET,
    DeletionSearch,
    contrastive_sets,
)
from reasonsmith.spec import normalize_claimed_semantics

LIMITS = (
    "This certificate compares one engine's answer against exact inference on one ground program "
    "and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS "
    "means no reason was shown to be deleted and the engine's value matched the exact value on "
    "this input; it does not certify the engine on any other input, and it does not establish that "
    "the reasons themselves are correct, only that the engine used all of the ones exact inference "
    "found. The probe is one-directional: it only switches facts off, never on, so `deleted` means "
    "the engine's answer did not depend on this reason *under this interpretation*. On a system "
    "whose reasons can be retracted by an added fact — a policy exception evaluated after the "
    "rules fire — a lawfully retracted reason is reported deleted here exactly as a dropped one "
    "is, and can drive a violated verdict against a system that stated its reasons correctly. "
    "Which is why the artefact declares whether its inference is monotone, and a certificate over "
    "one that declares it is not, declares nothing, or is contradicted by the probe carries no "
    "verdict at all. Where a "
    "deletion moves the engine's answer up, that is reported as a possible non-monotonicity, and "
    "it is the only fingerprint of the condition this instrument can leave. A reason is reported "
    "deleted only where a bounded enumeration of the joint deletions this engine notices ran to "
    "exhaustion and met no fact of that reason; where the budget ran out first the reason is "
    "reported neither way, so a shorter search names fewer missing reasons and never more."
)


#: Said once, on the verdict and on the certificate, wherever a deletion moved the engine's answer
#: up. Deliberately a remark and not a bucket: the reason it is attached to was probed cleanly, and
#: burying it in an inconclusive bucket would lose the one signal that detects the condition.
NON_MONOTONE_REMARK = (
    "the engine's answer rose when a fact was removed; this engine may not be monotone in its "
    "inputs. Deletion probing assumes it is, so a reason this engine withdrew under the base "
    "interpretation — a policy exception firing, say — is reported deleted here exactly as a "
    "dropped one is."
)


@dataclass(frozen=True)
class ReasonVerdict:
    """One exact reason, and what the deletion probe found out about it."""

    reason: frozenset
    label: str
    score: float
    status: str  # live | deleted | unseparable | inconclusive | undetermined
    probe_fact: Any | None  # the fact whose probe settled this status
    exact_drop: float
    engine_drop: float
    detail: str
    #: Every private fact of this reason, each switched off alone. Empty for `unseparable`.
    probe_facts: tuple[Any, ...] = ()
    #: Engine re-runs this reason cost: one per probe that moved exact inference at all.
    engine_probes: int = 0
    #: A probe of this reason moved the engine's answer *up*. Not a fault of the reason — evidence
    #: that the engine is not monotone in its inputs, and that `deleted` may be reading a
    #: retraction. See `LIMITS`.
    non_monotone: bool = False
    #: The contrastive set that settled this reason live where no single deletion could: a
    #: subset-minimal group of facts whose *joint* removal moves the engine, one of them private to
    #: this reason. Empty for every reason a single deletion settled.
    joint_witness: tuple[Any, ...] = ()

    def to_dict(self) -> dict:
        return {
            "reason": [str(a) for a in sorted(self.reason, key=repr)],
            "label": self.label,
            "score": self.score,
            "status": self.status,
            "probe_fact": str(self.probe_fact) if self.probe_fact is not None else None,
            "probe_facts": [str(a) for a in self.probe_facts],
            "engine_probes": self.engine_probes,
            "joint_witness": [str(a) for a in self.joint_witness],
            "exact_drop": self.exact_drop,
            "engine_drop": self.engine_drop,
            "non_monotone": self.non_monotone,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Certificate:
    query: Any
    adapter_name: str
    claimed_semantics: str
    exact_depth: int | None
    exact_value: float
    engine_value: float
    tol: float
    verdicts: tuple[ReasonVerdict, ...]
    attribution: str
    #: How the artefact obtained its reason set, in its own words. A reader cannot weigh a
    #: certificate without it, and it is the one line of the rendering that names a representation.
    exact_inference: str = ""
    #: The artefact's monotonicity declaration, carried so a reader of one certificate can see the
    #: premise its verdict rests on. None where the caller supplied no artefact at all — a direct
    #: `certify(...)` measurement, which reaches no duty and therefore no verdict about a system.
    monotone: bool | None = None
    #: The joint-deletion search, or None where no reason survived the per-fact pass as a candidate
    #: for deletion and there was nothing for it to resolve. `docs/sufficient-reasons.md` §7.
    search: DeletionSearch | None = None
    #: Which semantics `exact_value` above *is* — the artefact family's own
    #: `artifacts.reference_semantics`, carried so a reader of a value gap can see what the engine
    #: was compared against, and so a duty can refuse to compare it with a claim it does not match.
    #: None where the family computes no reference at all.
    exact_semantics: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "claimed_semantics", normalize_claimed_semantics(self.claimed_semantics)
        )
        if self.exact_semantics is not None:
            object.__setattr__(self, "exact_semantics", reference_semantics(self))

    def _by(self, status: str) -> list[ReasonVerdict]:
        return [v for v in self.verdicts if v.status == status]

    @property
    def deleted(self) -> list[ReasonVerdict]:
        return self._by("deleted")

    @property
    def live(self) -> list[ReasonVerdict]:
        return self._by("live")

    @property
    def unseparable(self) -> list[ReasonVerdict]:
        """Reasons with no fact of their own, so no movement can be attributed to them alone."""
        return self._by("unseparable")

    @property
    def inconclusive(self) -> list[ReasonVerdict]:
        """Reasons whose every probe left exact inference where it was: no signal to read."""
        return self._by("inconclusive")

    @property
    def undetermined(self) -> list[ReasonVerdict]:
        """Reasons the joint enumeration did not resolve — its budget ran out, or the only relevant
        fact they hold is shared. Neither shown live nor shown deleted, and never counted as
        missing: a partial search must name fewer missing reasons than a complete one, never more.
        """
        return self._by("undetermined")

    @property
    def uncertified(self) -> list[ReasonVerdict]:
        """The three states above, together. They differ in what evidence is missing and agree in
        what they mean to a verdict: counted as deleted by nothing and as live by nothing."""
        return self.unseparable + self.inconclusive + self.undetermined

    @property
    def jointly_necessary(self) -> list[ReasonVerdict]:
        """Reasons no single deletion moved the engine on, which a joint deletion did. Each would
        have been reported deleted before `explanations.contrastive_sets` existed."""
        return [v for v in self.verdicts if v.joint_witness]

    @property
    def non_monotone(self) -> list[ReasonVerdict]:
        """Reasons a probe of which moved the engine's answer up. See `LIMITS`."""
        return [v for v in self.verdicts if v.non_monotone]

    @property
    def value_gap(self) -> float:
        return self.engine_value - self.exact_value

    @property
    def deletion_semantics_refusal(self) -> str | None:
        """Why this artefact's reasons cannot be read off a deletion probe, or None if they can.

        Asked of the *declaration* and of the *measurement* together: a declaration the probe
        contradicted is refused exactly as one that said no. An artefact that declared nothing at
        all is refused too — except where nothing was declared because nothing was asked, which is
        `monotone is None` on a direct `certify(...)` call and is not a state `artifact()` can
        reach: `engines/certificate.py` refuses an undeclared artefact before it is measured. So a
        certificate produced from a bare measurement still reports what it measured, and no verdict
        about a system is ever read off one.
        """
        if self.monotone is None:
            return None
        return deletion_semantics_refusal(
            self.monotone, refuted_by_measurement=bool(self.non_monotone)
        )

    @property
    def verdict(self) -> str:
        if self.deletion_semantics_refusal:
            return "INCONCLUSIVE"
        if self.deleted or abs(self.value_gap) > self.tol:
            return "FAIL"
        if not self.verdicts or self.uncertified:
            return "INCONCLUSIVE"
        return "PASS"

    def missing_reasons(self) -> list[str]:
        return [v.label for v in self.deleted]

    def render(self) -> str:
        out = [
            f"REASON-DELETION CERTIFICATE [{self.verdict}]",
            f"query: {self.query!r}",
            f"engine: {self.adapter_name}   claims: {self.claimed_semantics}",
            f"exact inference: {self.exact_inference}",
            f"exact value {self.exact_value:.6f}   engine value {self.engine_value:.6f}   "
            f"gap {self.value_gap:+.6f}   tolerance {self.tol:g}",
            f"reasons: {len(self.verdicts)} found by exact inference, {len(self.live)} used by the "
            f"engine, {len(self.deleted)} deleted, {len(self.uncertified)} not certifiable",
            "",
        ]
        for v in sorted(self.verdicts, key=lambda v: (-v.score, v.label)):
            mark = {"live": "used", "deleted": "DELETED", "unseparable": "not certifiable",
                    "inconclusive": "not certifiable", "undetermined": "not certifiable"}[v.status]
            out.append(f"  [{mark:>15}] {v.label}  (score {v.score:.6f})")
            out.append(f"                    facts: {', '.join(sorted(repr(a) for a in v.reason))}")
            out.append(f"                    {v.detail}")
        if self.deleted:
            out += [
                "",
                f"MISSING REASONS: the engine's answer does not depend on {len(self.deleted)} "
                f"reason(s) that exact inference found:",
            ]
            out += [f"  - {v.label}: {', '.join(sorted(repr(a) for a in v.reason))}"
                    for v in sorted(self.deleted, key=lambda v: (-v.score, v.label))]
        if self.jointly_necessary:
            out += [
                "",
                f"JOINTLY NECESSARY: {len(self.jointly_necessary)} reason(s) no single deletion "
                "moves the engine on, which a joint deletion does. Each would have been reported "
                "deleted by a probe that only ever switches one fact off at a time:",
            ]
            out += [
                f"  - {v.label}: with "
                f"{', '.join(sorted(repr(a) for a in v.joint_witness))} switched off together"
                for v in sorted(self.jointly_necessary, key=lambda v: (-v.score, v.label))
            ]
        if self.search is not None and not self.search.exhaustive:
            out += [
                "",
                f"THE JOINT SEARCH DID NOT FINISH: {self.search.probes} of a {self.search.budget}-"
                f"probe budget were spent over {len(self.search.space)} fact(s) without exhausting "
                "the deletion lattice, so no reason is reported deleted on the strength of it. "
                f"{len(self.undetermined)} reason(s) are reported neither way for that reason.",
            ]
        if self.non_monotone:
            out += ["", f"NON-MONOTONICITY: {NON_MONOTONE_REMARK}", ""]
            out += [f"  - {v.label}: deleting {v.probe_fact!r} raised the engine's answer by "
                    f"{-v.engine_drop:+.6f}"
                    for v in sorted(self.non_monotone, key=lambda v: (-v.score, v.label))]
        out += ["", f"ATTRIBUTION: {self.attribution}"]
        if self.deletion_semantics_refusal:
            out += ["", "NO VERDICT IS READ OFF THIS MEASUREMENT: "
                        f"{self.deletion_semantics_refusal}."]
        out += ["", "LIMITS OF THIS CERTIFICATE", f"  {LIMITS}"]
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "query": str(self.query),
            "adapter_name": self.adapter_name,
            "claimed_semantics": self.claimed_semantics,
            "exact_semantics": self.exact_semantics,
            "exact_inference": self.exact_inference,
            "monotone": self.monotone,
            "deletion_semantics_refusal": self.deletion_semantics_refusal,
            "exact_depth": self.exact_depth,
            "exact_value": self.exact_value,
            "engine_value": self.engine_value,
            "value_gap": self.value_gap,
            "tol": self.tol,
            "reasons_found": len(self.verdicts),
            "reasons_used": len(self.live),
            "reasons_deleted": len(self.deleted),
            "reasons_uncertified": len(self.uncertified),
            "reasons_unseparable": len(self.unseparable),
            "reasons_inconclusive": len(self.inconclusive),
            "reasons_undetermined": len(self.undetermined),
            "reasons_jointly_necessary": len(self.jointly_necessary),
            "reasons_non_monotone": len(self.non_monotone),
            "deletion_search": self.search.to_dict() if self.search else None,
            "missing_reasons": self.missing_reasons(),
            "verdicts": [v.to_dict() for v in self.verdicts],
            "attribution": self.attribution,
            "limits": LIMITS,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON for `to_dict`. Values outside JSON's own types are stringified exactly as
        `render` prints them, so an adapter-supplied value of any type serialises rather than
        raising."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def _attribute(verdicts, value_gap: float, tol: float) -> str:
    deleted = [v for v in verdicts if v.status == "deleted"]
    live = [v for v in verdicts if v.status == "live"]
    uncertified = [
        v for v in verdicts if v.status in ("unseparable", "inconclusive", "undetermined")
    ]
    if not verdicts:
        if abs(value_gap) > tol:
            return (
                f"Exact inference found no reason for this query at this depth, and yet the engine "
                f"returns a value {value_gap:+.6f} away from it. No reason was probed, so nothing "
                f"is certified either way, and the engine's answer rests on something this "
                f"enumeration did not find: an unsupported query, a wrong identifier, or a proof "
                f"bound below the one the engine itself uses."
            )
        return (
            "Exact inference found no reason for this query at this depth, so no reason was probed "
            "and there was nothing to compare: an unsupported query, a wrong identifier or a proof "
            "bound too low all look like this. Nothing about the engine is certified either way."
        )
    if not deleted:
        if abs(value_gap) > tol:
            return (
                f"No reason was deleted, but the engine's value differs from exact inference by "
                f"{value_gap:+.6f}. The responsible setting is the engine's aggregation over the "
                f"reasons it kept, not proof truncation: every reason still moves the answer."
            )
        if uncertified:
            return (
                f"No reason was shown deleted, but {len(uncertified)} could not be probed in "
                f"isolation, so the reason set is not certified complete."
            )
        return (
            "The engine used every reason exact inference found, and its value matched the exact "
            "value within tolerance. No inference setting is implicated on this input."
        )
    order = sorted(verdicts, key=lambda v: (-v.score, v.label))
    tail = set(order[len(live):]) if live else set(order)
    if len(live) and set(deleted) == tail and not uncertified:
        return (
            f"The deleted reasons are exactly the {len(deleted)} lowest-scoring of the "
            f"{len(verdicts)}, and the engine kept the top {len(live)}. This is the signature of "
            f"top-k proof truncation at k={len(live)}: top-k works by discarding proofs, so the "
            f"dropped reasons are lost by configuration, not by error. The missing probability "
            f"mass is {-value_gap:.6f}."
        )
    return (
        f"{len(deleted)} reason(s) deleted, but they are not the {len(deleted)} lowest-scoring "
        f"reasons, so score-ordered top-k truncation does not explain the loss. Some other setting "
        f"in the engine — proof search bound, pruning heuristic, or a defect — is dropping reasons "
        f"the exact enumeration found."
    )


def certify(program, base: dict, query, adapter, exact_depth: int,
            tol: float = 1e-9, labels: dict | None = None,
            monotone: bool | None = None,
            budget: int = DEFAULT_PROBE_BUDGET) -> Certificate:
    """Certify one nesyarena ground program: the artefact family this package ships an adapter for.

    A thin front door onto `certify_artifact`, kept because these keyword names are the shape
    `sut.artifact(decision)` documents and `engines.certificate.ARTIFACT_KEYS` names. `program`,
    `base` and `query` are exactly what the adapter and the oracle both consume (that shared input
    is the invariant nesyarena's adapter protocol exists to hold). `exact_depth` bounds proof
    enumeration; `labels` maps a reason's EDB support set to a human name, such as a reason code,
    and falls back to the facts themselves; `monotone` is the declaration
    `artifacts.InferenceArtifact` requires, and defaults to *undeclared* rather than to True — a
    direct call here is a measurement, and a verdict about a system is read off one only where the
    duty's engine has already been told. `budget` caps the engine re-runs the joint-deletion search
    may spend on this decision.
    """
    from reasonsmith.artifacts.ground_program import GroundProgramArtifact

    return certify_artifact(
        GroundProgramArtifact(program, base, query, adapter, exact_depth, labels, monotone),
        tol,
        budget=budget,
    )


def _delete(artifact: InferenceArtifact, facts) -> InferenceArtifact:
    """The same inference with every fact of `facts` switched off, one `without` at a time."""
    perturbed = artifact
    for fact in sorted(facts, key=repr):
        perturbed = perturbed.without(fact)
    return perturbed


def _resolve_jointly(
    artifact: InferenceArtifact,
    verdicts: list[ReasonVerdict],
    facts,
    singleton_moved: set,
    engine_value: float,
    tol: float,
    budget: int,
) -> tuple[list[ReasonVerdict], DeletionSearch]:
    """Re-decide every candidate-`deleted` reason against the *joint* deletions the engine notices.

    Three outcomes per candidate, and `docs/sufficient-reasons.md` §5 is the definition of each:
    a reason holding a **private** relevant fact is `live` — the movement is attributable to it and
    to nothing else; a reason **no** fact of which is relevant is `deleted`, which needs no
    attribution because there is nothing to attribute and is claimed only on an exhausted
    enumeration; anything else is `undetermined`.

    This pass only ever moves a reason *out* of `deleted`. It never promotes an `unseparable` or
    `inconclusive` reason into it, though §5's definition would let it: that would mint new
    accusations out of a search whose completeness rests on a declaration nothing here confirms.
    """
    # A fact whose deletion alone already moves the engine lies in no contrastive set of size
    # greater than one (`docs/sufficient-reasons.md` §4, Corollary 2), so it is not searched over.
    space = tuple(sorted((f for f in facts if f not in singleton_moved), key=repr))
    search = contrastive_sets(
        lambda deleted: abs(engine_value - _delete(artifact, deleted).engine_value()) > tol,
        space,
        budget=budget,
    )

    resolved = []
    for v in verdicts:
        if v.status != "deleted":
            resolved.append(v)
            continue
        private = tuple(f for f in v.probe_facts if f in search.relevant)
        shared = tuple(sorted(repr(f) for f in v.reason if f in search.relevant))
        if private:
            witness = min(
                (c for c in search.contrastive if not c.isdisjoint(private)),
                key=lambda c: (len(c), sorted(repr(f) for f in c)),
            )
            named = ", ".join(sorted(repr(f) for f in witness))
            resolved.append(replace(
                v,
                status="live",
                joint_witness=tuple(sorted(witness, key=repr)),
                detail=(
                    f"no fact of this reason moves the engine when switched off alone, but "
                    f"switching off {named} together does: the engine's answer depends on this "
                    f"reason jointly with the others in that set, so it is not deleted."
                ),
            ))
        elif shared:
            named = ", ".join(shared)
            resolved.append(replace(
                v,
                status="undetermined",
                detail=(
                    f"no fact of this reason moves the engine alone or jointly except {named}, "
                    f"which another reason also holds, so the engine's dependence cannot be "
                    f"attributed to this reason rather than to the one sharing that fact; not "
                    f"certified either way."
                ),
            ))
        elif not search.exhaustive:
            resolved.append(replace(
                v,
                status="undetermined",
                detail=(
                    f"no single deletion moves the engine on this reason, and the joint search "
                    f"spent its {search.budget}-probe budget over {len(search.space)} fact(s) "
                    f"without exhausting the deletion lattice, so no reason is deleted on the "
                    f"strength of it; not certified either way."
                ),
            ))
        else:
            resolved.append(v)
    return resolved, search


def certify_artifact(
    artifact: InferenceArtifact,
    tol: float = 1e-9,
    *,
    budget: int = DEFAULT_PROBE_BUDGET,
) -> Certificate:
    """Compare the reasons an engine actually used against the exact set, and name what is missing.

    The representation-neutral core: everything it knows about the inference it reads through
    `artifacts.InferenceArtifact`, so a second family of artefact is an adapter and not a branch
    here.
    """
    reasons = tuple(artifact.reasons())
    exact_value = artifact.exact_value()
    engine_value = artifact.engine_value()

    seen: dict[Any, int] = {}
    for r in reasons:
        for f in r:
            seen[f] = seen.get(f, 0) + 1

    verdicts = []
    #: Facts whose deletion *alone* already moves the engine. They lie in no contrastive set of size
    #: greater than one, so the joint pass below does not search over them.
    singleton_moved: set[Any] = set()
    for r in reasons:
        label = artifact.label(r)
        score = artifact.score(r)
        private = tuple(sorted((f for f in r if seen[f] == 1), key=repr))
        if not private:
            verdicts.append(ReasonVerdict(
                r, label, score, "unseparable", None, 0.0, 0.0,
                "every fact of this reason is shared with another reason, so it cannot be switched "
                "off alone; not certified either way."))
            continue
        # Every private fact, one at a time. Probing one of them and calling the reason answered
        # made coverage a function of the facts' names: two systems alike but for a field name got
        # different probes.
        signal: list[tuple[Any, float, float]] = []
        silent: list[tuple[Any, float]] = []
        for probe in private:
            probed = artifact.without(probe)
            exact_drop = exact_value - probed.exact_value()
            if exact_drop <= tol:
                silent.append((probe, exact_drop))
                continue
            signal.append((probe, exact_drop, engine_value - probed.engine_value()))
        coverage = (
            f" All {len(private)} private fact(s) of this reason were switched off, one at a time."
            if len(private) > 1
            else ""
        )
        if not signal:
            probe, exact_drop = silent[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "inconclusive", probe, exact_drop, 0.0,
                f"deleting {probe!r} does not move exact inference either ({exact_drop:+.2e}), so "
                f"the probe carries no signal; not certified either way.{coverage}",
                private, len(signal)))
            continue
        moved = [t for t in signal if abs(t[2]) > tol]
        singleton_moved.update(t[0] for t in moved)
        # A rise is the one fingerprint a non-monotone engine leaves, so it is the probe reported.
        rose = [t for t in moved if t[2] < -tol]
        if moved:
            probe, exact_drop, engine_drop = (rose or moved)[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "live", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} and the engine by "
                f"{-engine_drop:+.6f}: the engine's answer depends on this reason.{coverage}"
                + (f" {NON_MONOTONE_REMARK[0].upper()}{NON_MONOTONE_REMARK[1:]}" if rose else ""),
                private, len(signal), bool(rose)))
        else:
            probe, exact_drop, engine_drop = signal[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "deleted", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} but leaves the "
                f"engine unchanged: the engine's answer does not depend on this reason.{coverage}",
                private, len(signal)))

    # A single deletion showing no movement is not a reason the engine ignores: two reasons jointly
    # necessary and individually removable each look exactly like this. So every candidate is
    # re-decided against the joint deletions, and none stays `deleted` unless that search finished.
    search = None
    if any(v.status == "deleted" for v in verdicts):
        verdicts, search = _resolve_jointly(
            artifact, verdicts, seen, singleton_moved, engine_value, tol, budget
        )

    verdicts = tuple(verdicts)
    return Certificate(
        artifact.query, artifact.engine_name, artifact.claimed_semantics, artifact.exact_depth,
        exact_value, engine_value, tol, verdicts,
        _attribute(verdicts, engine_value - exact_value, tol),
        artifact.exact_inference, artifact.monotone, search,
        reference_semantics(artifact))
