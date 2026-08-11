"""Certificate engine for reasonsmith v0.2.

What this module is for:
  Evaluates the duties settled against the inference artefact behind a decision, by running
  `reasonsmith.certificate.certify` over the artefact the system exposes and grounding the two
  signals in `MEASURED_SIGNALS` with what it measured. A *reason adequacy* duty — whether the
  reasons a decision states are all the reasons its own inference had — reads
  `artifact_logs_deleted_reason_count`, from the deletion probe. A *semantics agreement* duty —
  whether the system's answer is the semantics it claims — reads
  `artifact_logs_semantics_value_gap`, from the certificate's own `value_gap`. Both are measured
  here and read from no record.

  This is the bridge between the two halves of this package. The certificate could compare an
  engine's answer against exact inference and name the reasons the engine stopped depending on,
  but no duty and no CLI verb reached it: its only caller was the demonstration. Meanwhile the
  strongest thing a reason-giving duty could claim was that the reason field was non-blank and
  carried none of two forbidden phrases — which the demonstration's own decision `APP-1042`
  satisfies while four of its five legally owed reasons are missing. The tool shipped a
  counterexample to its own verdict. This engine is what closes that: the same decision now
  reports the adequacy duty *violated*, from the measurement rather than from the log.

What a reader must not break:
  - The measured count is never read from the system's own record. `_env` overwrites whatever a
    record carries for `artifact_logs_deleted_reason_count` with the count the probe measured.
    Why this matters: a system that could settle this duty by logging a zero would be grading its
    own homework — the self-declared flag `docs/semantics.md` §3 refuses. The whole point of this
    rung is that the number comes from exact inference over the artefact, not from the log.
  - A system that exposes no `artifact()` oracle is reported UNATTAINABLE naming
    `artifact_logs_deleted_reason_count`, never satisfied and never downgraded to a presence
    check on the reason field. `report._engine_ladder` gives this duty no other rung for the same
    reason (see its `CertificateEngine` branch).
    Why this matters: substituting the presence property for the adequacy property is exactly the
    defect this engine exists to remove. A duty about whether the stated reasons are *all* the
    reasons cannot be discharged by observing that some reason was stated.
  - An artefact the deletion definition of a reason does not apply to is refused **before** it is
    measured, and the refusal is NOT EVALUATED: never violated, never satisfied, and never handed
    down to a weaker duty. Three states reach it — an artefact declaring its inference
    non-monotone, one declaring nothing, and one declaring itself monotone that the probe then
    contradicted — and `artifacts.deletion_semantics_refusal` words all three once.
    Why this matters: the probe is one-directional, so on a non-monotone inference a lawfully
    retracted reason is indistinguishable from a dropped one and this engine reports a compliant
    creditor violated. Measuring anyway and disclosing the limit was the previous answer; the
    declaration is what lets the refusal be structural. It is *not evaluated* rather than
    *unattainable* because the gap is in this tool and not in the system: a creditor whose policy
    exceptions retract reasons is behaving as designed, and "change the system" is the wrong
    instruction to hand it (`docs/semantics.md` §4, the four outcomes).
  - One refused artefact refuses the **run**, not just its own decision.
    Why this matters: a verdict assembled from the decisions that happened to be monotone is a
    verdict over a subset, and the rule below — a satisfaction needs complete evidence — already
    refuses those. Reporting `violated` off the remainder would also leave the reader unable to see
    that the trace held a decision this instrument cannot read at all.
  - The strength is PROBED or RECOUNTED, and never PROVED. The certificate's reach is the decisions
    the system supplied and the deletion probes those decisions admitted, and `RequirementResult`
    refuses to construct the result without the budget that names both. Which of the two rungs is
    decided by the *artefacts* and not by the search: one certified decision whose reason set the
    system recounted rather than enumerated caps the run at RECOUNTED, and the flag that says so
    (`report.EXACT_REASON_SET_KEY`) travels on the result, where `_validate_reason_set` refuses a
    claim above it.
    Why this matters: exact inference is exact *on one ground program and one base
    interpretation* — `certificate.LIMITS` says so in its own words. Nothing here establishes the
    property for a decision the system did not expose, and a rationale the system recounted
    establishes less again: see `artifacts.RECOUNTED_REASONS`.
  - A reason the probe could not settle (`unseparable`, `inconclusive`, `undetermined`) is not
    counted as deleted, and the count of them is reported.
    Why this matters: `certificate.certify` never assumes such a reason is live, and neither may
    this engine assume it was dropped. Counting it either way would put a verdict on evidence the
    probe explicitly declined to produce.
  - The joint-deletion search's probes are counted into `trials` and whether it *finished* is
    carried in `input_space`, beside the reasons it left `undetermined`.
    Why this matters: a reason is `deleted` only where that enumeration ran to exhaustion
    (`docs/sufficient-reasons.md` §7), so how far it got is not a curiosity about performance — it
    is the bound on what every `deleted` here claims, and `PROBE_BUDGET_FIELDS` exists so a bound
    a reader cannot see cannot be relied on.
  - A certificate whose enumeration found *no* reason measures nothing, and is evidence for
    nothing. It is dropped from the certified set, counted, and reported, and no run holding one
    reports SATISFIED: it is NOT EVALUATED naming `artifact_logs_deleted_reason_count`.
    Why this matters: `len(cert.deleted)` is zero on such a certificate for the same reason it is
    zero on a decision whose reasons the engine all used, and the two are not the same fact. The
    engine asks `conformance.measured(cert)` — this package's single predicate for whether a
    certificate measured anything at all, and the no-enumerated-reason clause of
    `Certificate.verdict`'s refusal to report PASS, "a zero value gap on an un-enumerated query is
    not agreement; exact inference never evaluated it" — rather than reading the zero. That
    property's other clause, that `uncertified` also blocks PASS, is deliberately *not* acted on
    here: an unseparable reason stays in the certified set and is reported as a caveat rather than
    turning the verdict. Lowering the artefact's own `exact_depth` to 0 would otherwise turn the
    demonstration's breached decision clean, which is weaker evidence buying a stronger verdict.
  - A duty reading the value gap is refused **before** the gap is read as evidence, on the two
    semantics names the certificate carries: `artifacts.semantics_reference_refusal` asks whether
    the family's own reference (`artifacts.reference_semantics`) computes the semantics the artefact
    claims, and the two failures land on different outcomes. A family computing no reference is
    UNATTAINABLE, and a claim the reference does not match is NOT EVALUATED, naming the claim.
    Why this matters: they are the four-outcome distinction of `docs/semantics.md` §4 on one
    measurement. `artifacts/reason_trace.py`'s exact side is the weight the *system* recounted, so
    the difference between it and the system's answer is a rationale's faithfulness and not a
    semantics claim — the fix is to expose a model encoding, which is a fact about the system. But a
    system that *documents* its approximation is behaving exactly as declared, and this build can
    compute a reference for one semantics: telling it to change would be the wrong instruction, and
    telling it that it departed from a semantics it never claimed would be a false accusation. The
    closed vocabulary (`spec.CLAIMED_SEMANTICS`) has no member for a documented approximation of
    another member, which is why that case must be refused rather than answered, and why the
    vocabulary had to close before any verdict read a gap.
  - The two monotonicity refusals above are asked **only** of a duty reading the deleted count.
    Why this matters: the declaration is the premise `deleted` rests on and no other. The value gap
    is read at the unperturbed interpretation, where nothing has been switched off and no definition
    of a reason is in play, so refusing there would report a system whose inference is lawfully
    defeasible unmeasurable on a duty its defeasibility has no bearing on.
  - A certified decision whose reasons the notice never stated does not satisfy this duty
    vacuously: a run where the property's antecedent held on no certified decision is reported NOT
    EVALUATED, never `satisfied`. The rule is not this engine's own — it is written once,
    `rulelang.implication_antecedent` naming the subtree and
    `report.not_evaluated_for_unreachable_trigger` wording the refusal — and the antecedent is
    counted in the same walk that decides the property, exactly as `engines/probed.py` counts the
    replays that reached it.
    Why this matters: this duty is written as an implication so a creditor lawfully on the
    12 CFR 1002.9(a)(2)(ii) disclosure branch is not accused of an inadequate statement it never
    made. Reading that as `satisfied` would report every such system alike clean on the adequacy of
    a statement no decision carried, which is the same empty claim at the same strength this
    engine's own reason for existing was to remove.
  - A violation needs one witness; a satisfaction needs complete evidence. A measured breach is
    reported VIOLATED however many decisions went unmeasured beside it, while SATISFIED requires
    that every certified decision was measured.
    Why this matters: the lenient rule — satisfied over whatever remained — is defeated by the
    same move the refusal above was written to stop: declare `exact_depth=0` on every decision but
    one genuinely clean one and the duty reports satisfied again. This is not the
    `decisions_without_an_artifact` case and that precedent must not be cited as one: a decision
    without an artefact was never certified, while a decision whose artefact declared depth 0 was
    certified and produced nothing — a stronger signal, not a weaker one. The asymmetry is the one
    `docs/semantics.md` §3 already states for a trace, a satisfied verdict being universal over it
    and a violated one existential.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import Any

from reasonsmith.artifacts import (
    MONOTONE_KEY,
    RECOUNTED_REASONS,
    InferenceArtifact,
    deletion_semantics_refusal,
    reason_set_is_exact,
    semantics_reference_refusal,
)
from reasonsmith.certificate import Certificate, ReasonVerdict, certify, certify_artifact
from reasonsmith.conformance import measured
from reasonsmith.report import (
    CERTIFICATE_KEY,
    CERTIFICATES_KEY,
    EXACT_REASON_SET_KEY,
    PROBE_BUDGET_KEY,
    RequirementResult,
    evidence_basis,
    not_evaluated_for_unreachable_trigger,
)
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
    implication_antecedent,
    is_unknown,
    kleene_value,
    parse_property,
    signal_names,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

__all__ = [
    "ARTIFACT_METHOD",
    "DELETED_REASON_COUNT",
    "MEASURED_SIGNALS",
    "SEED",
    "SEMANTICS_VALUE_GAP",
    "STRATEGY",
    "CertificateEngine",
]

#: The first signal this engine measures rather than reads. A duty naming it in `requires` is a
#: duty only this engine may settle (`report._engine_ladder`), and a system declaring it is
#: claiming it can expose the inference artefact below — not that it writes the number into a log.
DELETED_REASON_COUNT = "artifact_logs_deleted_reason_count"

#: The second, and the same discipline: the distance between the system's own engine's answer and
#: exact inference's answer to the same query on the same interpretation, as an absolute value.
#: Measured from the artefact, never read from a record, and only ever measured where the artefact's
#: reference computes the semantics the system claims — see `_semantics_refusal`. It is the value
#: gap `Certificate.value_gap` already carried and no verdict read.
SEMANTICS_VALUE_GAP = "artifact_logs_semantics_value_gap"

#: Both, in the order they were added. `report._engine_ladder` gives a duty naming any of them a
#: ladder of one rung and `report.evidence_basis` gives it the `artifact` basis, for the reason the
#: ladder's own docstring states: every other rung would answer a weaker question off the system's
#: own log.
MEASURED_SIGNALS = (DELETED_REASON_COUNT, SEMANTICS_VALUE_GAP)

#: The optional SUT method, exactly parallel to the optional `decide(case)`: given one decision
#: record, return the inference artefact that decision came from, or None for a decision this
#: system cannot open up. See `sut.SystemUnderTest` and `artifacts.InferenceArtifact`.
ARTIFACT_METHOD = "artifact"

#: The keyword arguments `artifact()` may return for the one artefact family this package ships an
#: adapter for — a nesyarena ground program — named in the refusal so an adapter author is told the
#: shape rather than shown a TypeError from four frames down. A system of any other family returns
#: an `artifacts.InferenceArtifact` instead, which is the whole of what a second family costs.
ARTIFACT_KEYS = (
    "program", "base", "query", "adapter", "exact_depth", "monotone", "tol", "labels", "budget",
)

#: What the search does, named on every result it produces.
STRATEGY = (
    "for each decision the system exposed an inference artefact for, its reasons are enumerated "
    "exactly by bounded proof enumeration over the ground program and scored by exact weighted "
    "model counting; every fact of a reason that no other reason uses is then switched off alone "
    "and the system's own engine re-run on the perturbed interpretation. A reason a single "
    "deletion "
    "moves the engine on is one its answer depends on. A reason no single deletion moves is then "
    "put to a second search, because two reasons jointly necessary and individually removable look "
    "exactly like two dropped ones: the subset-minimal *joint* deletions the engine notices are "
    "enumerated over the remaining facts, and a reason is counted here only where that enumeration "
    "ran to exhaustion and met no fact of it. The probe only ever switches a fact off, never on"
)

#: There is no seed: the enumeration and every probe are determined by the artefact. The budget
#: still carries the field, because a reader comparing two probed verdicts must be able to see
#: that one of them had nothing to vary rather than guess it.
SEED = "none — the proof enumeration and the deletion probes are deterministic"


def _result(
    req: Requirement,
    verdict: Verdict,
    strength: Strength | None,
    summary: str,
    *,
    missing: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> RequirementResult:
    # The basis is stamped here as well as by `evaluate_requirement`, and it is the same derivation
    # from the same requirement — `report.evidence_basis`, never a field of this engine's own. It
    # has to be: `recounted` is a rung the *artifact* row admits and the default row does not, so a
    # result carrying it could not be constructed at all before the stamp.
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=verdict,
        strength=strength,
        basis=evidence_basis(req),
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=summary,
        details=dict(details or {}),
        binding=req.binding,
        scope=req.scope,
    )


def _refused(
    req: Requirement,
    index: int,
    refusal: str,
    declared: bool | None,
    non_monotone: int = 0,
) -> RequirementResult:
    """Not evaluated, because the deletion definition of a reason does not apply to this artefact.

    The whole run and not the decision: see the module docstring. The refusal names the decision it
    was reached on so an adapter author can find the artefact, and carries the declaration and the
    refuting count in `details` so a reader can tell a system that said no from one whose own
    measurement said no for it.
    """
    return _result(
        req,
        Verdict.INCONCLUSIVE,
        None,
        (
            f"Not evaluated: on decision #{index}, {refusal}. Nothing is claimed either way about "
            "this decision or about any other in the trace, because a reason set measured under a "
            "definition that does not hold of the inference is not evidence about the notice."
        ),
        details={
            "engine": "certificate",
            "reason": "deletion_semantics_do_not_apply",
            "decision_index": index,
            "declared_monotone": declared,
            **(
                {"reasons_whose_deletion_raised_the_engines_answer": non_monotone}
                if non_monotone
                else {}
            ),
        },
    )


def _env(record: Mapping[str, Any], cert: Certificate) -> dict[str, Any]:
    """The record, with both measurements written over anything the record claimed for them."""
    return {
        **record,
        DELETED_REASON_COUNT: len(cert.deleted),
        SEMANTICS_VALUE_GAP: abs(cert.value_gap),
    }


def _unattainable(req: Requirement, index: int, refusal: str) -> RequirementResult:
    """Unattainable: this artefact's family grounds no semantics-agreement measurement.

    `unattainable` and not *not evaluated*, on the four-outcome test of `docs/semantics.md` §4: the
    gap is in the system, and the instruction that follows from it — expose the model encoding the
    inference ran over — is one an adopter can act on. Every family outside the one that computes a
    reference lands here, including a system exposing no `artifact()` at all, which the branch at
    the top of `evaluate` already reports the same way.
    """
    return _result(
        req,
        Verdict.INCONCLUSIVE,
        Strength.UNATTAINABLE,
        (
            f"Unattainable as built: on decision #{index}, {refusal}. {SEMANTICS_VALUE_GAP} is "
            "measured against exact inference over a model encoding the system exposes, and this "
            "system exposes none."
        ),
        missing=(SEMANTICS_VALUE_GAP,),
        details={
            "engine": "certificate",
            "reason": "no_semantics_reference",
            "decision_index": index,
        },
    )


def _mismatched_claim(
    req: Requirement, index: int, refusal: str, claimed: str, reference: str
) -> RequirementResult:
    """Not evaluated: the system claims a semantics this build computes no reference for.

    The other side of the same fork, and the opposite outcome: here the artefact is exactly the
    family this duty wants and the gap in this tool is that it can evaluate one semantics. Reporting
    a system that documents its own approximation `violated` against a semantics it never claimed is
    the false accusation the whole ordering of this work exists to prevent, and reporting it
    `unattainable` would tell an honest adopter to change a system that is behaving as declared.
    """
    return _result(
        req,
        Verdict.INCONCLUSIVE,
        None,
        (
            f"Not evaluated: on decision #{index}, {refusal}. Nothing is claimed either way about "
            "this system's agreement with the semantics it declared."
        ),
        details={
            "engine": "certificate",
            "reason": "no_reference_for_the_claimed_semantics",
            "decision_index": index,
            "claimed_semantics": claimed,
            "reference_semantics": reference,
        },
    )


def _reason_record(verdict: ReasonVerdict) -> dict:
    """The machine record of one reason verdict, lean by design.

    The full-fat `ReasonVerdict.to_dict` keeps the probe internals — `reason` (a frozenset of
    adapter-specific objects), `probe_fact`, `probe_facts`, `joint_witness` — that are not
    JSON-shaped and no rendering reads. What a renderer needs is the verdict itself and its
    numbers, and the distinction the record must not lose is `status` verbatim: `deleted` is a
    finding, `unseparable`/`inconclusive`/`undetermined` are the three ways a reason was not
    certified, and collapsing them would show a guess as a finding.
    """
    return {
        "label": verdict.label,
        "status": verdict.status,
        "score": verdict.score,
        "exact_drop": verdict.exact_drop,
        "engine_drop": verdict.engine_drop,
        "detail": verdict.detail,
    }


def _certificate_record(index: int, cert: Certificate) -> dict:
    """The machine record of one certificate, as `details[CERTIFICATE_KEY]` carries it.

    `index` is the decision index, so a reader can join this record against the summary under
    `CERTIFICATES_KEY` and against the trace. Everything here is read off the `Certificate`
    itself; nothing is recomputed. The certificate's own fields are carried unchanged, and
    `monotone` may be null exactly as the artefact's declaration was absent.
    """
    return {
        "decision_index": index,
        "attribution": cert.attribution,
        "exact_value": cert.exact_value,
        "engine_value": cert.engine_value,
        "claimed_semantics": cert.claimed_semantics,
        "exact_semantics": cert.exact_semantics,
        "value_gap": cert.value_gap,
        "monotone": cert.monotone,
        "reasons": [_reason_record(v) for v in cert.verdicts],
    }


def _probes(cert: Certificate) -> int:
    """Inferences this certificate replayed: one baseline, plus one per fact it switched off and
    re-ran the engine on, plus every joint deletion pattern the contrastive search re-ran it on.
    A fact whose deletion does not move exact inference costs no re-run."""
    return (
        1
        + sum(v.engine_probes for v in cert.verdicts)
        + (cert.search.probes if cert.search else 0)
    )


class CertificateEngine:
    """Engine settling a reason-adequacy duty against the reason-deletion certificate."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: list[dict[str, Any]],
    ) -> RequirementResult:
        # Imported here and not at module scope: `engines/temporal.py` imports `report`, which
        # reaches this engine, and the cycle is not worth a second spelling of the reduction.
        from reasonsmith.engines.temporal import state_property_under_always

        gated = tuple(name for name in MEASURED_SIGNALS if name in req.requires)
        artifact = getattr(sut, ARTIFACT_METHOD, None)
        if not callable(artifact):
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                Strength.UNATTAINABLE,
                (
                    f"Unattainable as built: this duty is settled against the inference artefact "
                    f"behind a decision and never read from a log. "
                    f"{type(sut).__name__} exposes no {ARTIFACT_METHOD}() supplying one, so "
                    f"{', '.join(gated) or 'the signal this engine measures'} cannot be measured "
                    "here. Nothing weaker stands in for it: what a system writes about its own "
                    "inference into its own record is a different property, and reporting it in "
                    "place of this one is the substitution this duty exists to refuse."
                ),
                missing=gated or (DELETED_REASON_COUNT,),
            )

        # `always(f)` over a finite trace holds exactly when `f` holds at every position, and every
        # position below is one decision this engine certifies — the same reduction
        # `engines/temporal.py` makes for the solver, and sound here for the same reason. It is
        # taken from the language's own function rather than re-derived, so one spelling of the
        # operator exists.
        inner = state_property_under_always(req.spec)
        try:
            node = parse_property(req.spec if inner is None else inner)
        except UnsupportedConstructError as exc:
            return _result(
                req, Verdict.INCONCLUSIVE, None, f"Not evaluated: {exc}."
            )
        measures = tuple(name for name in MEASURED_SIGNALS if name in signal_names(node))
        if not measures:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: {req.spec!r} reads none of "
                    f"{', '.join(MEASURED_SIGNALS)}, which are the only signals this engine "
                    "measures. Nothing here grounds the rest of it."
                ),
            )

        if not records:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: the decision trace is empty, so there is no decision to "
                    "certify. An empty trace is not evidence that the requirement holds."
                ),
            )

        spec_vars = set(signal_names(node))
        antecedent_node = implication_antecedent(node)
        antecedent_text = ast.unparse(antecedent_node) if antecedent_node is not None else ""
        # The decisions the duty's trigger reached, by index rather than as a count: the satisfied
        # summary owes a reader what it measured behind the *other* ones and set aside.
        triggered_at: set[int] = set()

        certified: list[tuple[int, Certificate, bool]] = []
        # The decisions whose reason set the system *recounted* rather than enumerated. One of them
        # among the certified caps the whole verdict at `recounted`: a run is only as exact as its
        # weakest artefact, exactly as a satisfaction is only as complete as its weakest decision.
        recounted_at: set[int] = set()
        uncertifiable = 0
        for index, record in enumerate(records):
            try:
                supplied = artifact(record)
            except Exception as exc:  # noqa: BLE001 — reported, never swallowed
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: {type(sut).__name__}.{ARTIFACT_METHOD}() raised "
                        f"{type(exc).__name__} on decision #{index}: {exc}. Nothing was measured "
                        "about this requirement."
                    ),
                )
            if supplied is None:
                uncertifiable += 1
                continue
            if not isinstance(supplied, (Mapping, InferenceArtifact)):
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: {type(sut).__name__}.{ARTIFACT_METHOD}() returned "
                        f"{type(supplied).__name__} for decision #{index}; it must return an "
                        f"artifacts.InferenceArtifact, or the keyword arguments of "
                        f"certificate.certify ({', '.join(ARTIFACT_KEYS)}) for a nesyarena ground "
                        "program, or None for a decision it cannot open up."
                    ),
                )
            # The mapping form names the ground-program family in its own keyword names, and that
            # family enumerates; every other family says for itself, and silence claims the weaker
            # rung (`artifacts.reason_set_is_exact`).
            if not (isinstance(supplied, Mapping) or reason_set_is_exact(supplied)):
                recounted_at.add(index)
            # Asked of the declaration before anything is measured: an artefact this definition of
            # a reason does not apply to must not be probed and then explained away. Asked only of
            # a duty that reads the *deleted count*, because the monotonicity declaration is the
            # premise that count rests on and no other: the value gap is read at the unperturbed
            # interpretation, where nothing has been switched off and no definition of a reason is
            # in play. Refusing it here too would report a system whose inference is lawfully
            # defeasible unmeasurable on a duty its defeasibility has no bearing on.
            declared = (
                supplied.get(MONOTONE_KEY)
                if isinstance(supplied, Mapping)
                else supplied.monotone
            )
            refusal = (
                deletion_semantics_refusal(declared)
                if DELETED_REASON_COUNT in measures
                else None
            )
            if refusal:
                return _refused(req, index, refusal, declared)
            try:
                cert = (
                    certify(**supplied)
                    if isinstance(supplied, Mapping)
                    else certify_artifact(supplied)
                )
            except Exception as exc:  # noqa: BLE001 — reported, never swallowed
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: certifying decision #{index} raised "
                        f"{type(exc).__name__}: {exc}. The artefact must carry the keyword "
                        f"arguments of certificate.certify ({', '.join(ARTIFACT_KEYS)})."
                    ),
                )
            # And asked again of the measurement: the declaration is a claim the system makes about
            # itself, and a deletion that moved its answer *up* is the one thing that refutes it.
            refusal = (
                deletion_semantics_refusal(
                    declared, refuted_by_measurement=bool(cert.non_monotone)
                )
                if DELETED_REASON_COUNT in measures
                else None
            )
            if refusal:
                return _refused(req, index, refusal, declared, len(cert.non_monotone))
            # And, for a duty reading the value gap, asked of the two semantics names before the
            # gap is read as evidence about either. Both certificate forms answer it the same way,
            # because `certify_artifact` carries the family's own reference onto the certificate.
            if SEMANTICS_VALUE_GAP in measures:
                refusal = semantics_reference_refusal(
                    cert.claimed_semantics, cert.exact_semantics
                )
                if refusal:
                    return (
                        _unattainable(req, index, refusal)
                        if cert.exact_semantics is None
                        else _mismatched_claim(
                            req,
                            index,
                            refusal,
                            cert.claimed_semantics,
                            cert.exact_semantics,
                        )
                    )
            try:
                env = _env(record, cert)
                val = eval_expression(node, env)
                if is_unknown(val):
                    absent = sorted([v for v in spec_vars if env.get(v) is None])
                    gaps = ", ".join(absent) if absent else "a required signal"
                    return _result(
                        req,
                        Verdict.INCONCLUSIVE,
                        None,
                        (
                            f"Not evaluated: evaluating {req.spec!r} against decision #{index} "
                            "depends on signal(s) absent from the decision record — "
                            f"no value for {gaps}. "
                            "The measurement was made; the property could not be decided from it, "
                            "so nothing is claimed either way."
                        ),
                        details={
                            "engine": "certificate",
                            "reason": "spec_evaluation_failed",
                            "decision_index": index,
                            "signals_absent_in_record": absent,
                        },
                    )
                held = bool(val)
                if (
                    antecedent_node is not None
                    and kleene_value(eval_expression(antecedent_node, env)) is True
                ):
                    triggered_at.add(index)
            except Exception as exc:  # noqa: BLE001 — reported, never swallowed
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: evaluating {req.spec!r} against decision #{index} raised "
                        f"{type(exc).__name__}: {exc}. The measurement was made; the property "
                        "could not be decided from it, so nothing is claimed either way."
                    ),
                )
            certified.append((index, cert, held))

        if not certified:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: the system exposed no inference artefact for any of the "
                    f"{len(records)} decision(s) in the trace, so {', '.join(measures)} was "
                    "measured for none of them."
                ),
            )

        # A certificate whose enumeration found no reason at all measured nothing: its zero
        # deleted-reason count is the absence of a measurement, not a measurement of zero. This is
        # the refusal `Certificate.verdict` already makes one layer down, asked for here.
        unenumerated = sum(1 for _, cert, _ in certified if not measured(cert))
        certified = [item for item in certified if measured(item[1])]
        if not certified:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: bounded proof enumeration found no reason at all behind any "
                    f"of the {unenumerated} certified decision(s), so {', '.join(measures)} is "
                    "unmeasured for every one of them and no reason was switched off. A zero "
                    "deleted-reason count on a decision whose reasons were never enumerated is "
                    "the absence of a measurement, not a measurement of zero — the artefact's own "
                    "exact_depth is the usual cause. Nothing is claimed either way."
                ),
            )

        uncertified_reasons = sum(len(cert.uncertified) for _, cert, _ in certified)
        undetermined_reasons = sum(len(cert.undetermined) for _, cert, _ in certified)
        joint_reasons = sum(len(cert.jointly_necessary) for _, cert, _ in certified)
        searches = [cert.search for _, cert, _ in certified if cert.search is not None]
        budget = {
            "trials": sum(_probes(cert) for _, cert, _ in certified),
            "strategy": STRATEGY,
            "seed": SEED,
            "input_space": {
                "decisions certified": len(certified),
                "facts switched off": sum(
                    len(v.probe_facts) for _, cert, _ in certified for v in cert.verdicts
                ),
                # The joint search's own two numbers. `docs/sufficient-reasons.md` §7: a partial
                # enumeration may still report a reason live and may never report one deleted, so
                # whether it finished is the field carrying the whole of what `deleted` claims.
                "joint deletion patterns tried": sum(s.probes for s in searches),
                "decisions whose joint search did not finish": sum(
                    1 for s in searches if not s.exhaustive
                ),
            },
        }
        # The rung this run may report at, decided by what the reason sets were rather than by what
        # the search did: the probe is the same probe either way. `RequirementResult` refuses a
        # result that claims more than the flag below allows, so this is a choice the result model
        # checks rather than a convention this engine keeps.
        exact_reason_sets = not recounted_at.intersection(index for index, _, _ in certified)
        reached = Strength.PROBED if exact_reason_sets else Strength.RECOUNTED
        recounted_note = "" if exact_reason_sets else f" Read at {reached}: {RECOUNTED_REASONS}."
        details: dict[str, Any] = {
            EXACT_REASON_SET_KEY: exact_reason_sets,
            PROBE_BUDGET_KEY: budget,
            "decisions_certified": len(certified),
            "decisions_without_an_artifact": uncertifiable,
            "decisions_without_an_enumerated_reason": unenumerated,
            "reasons_not_certifiable": uncertified_reasons,
            "reasons_undetermined_by_the_joint_search": undetermined_reasons,
            "reasons_live_only_jointly": joint_reasons,
            CERTIFICATES_KEY: [
                {
                    "decision_index": index,
                    "certificate_verdict": cert.verdict,
                    "reasons_found": len(cert.verdicts),
                    "reasons_deleted": len(cert.deleted),
                    "missing_reasons": cert.missing_reasons(),
                    "attribution": cert.attribution,
                }
                for index, cert, _ in certified
            ],
            # The full machine record the summary above condenses: one entry per certified
            # decision, carrying every reason verdict the summary counts. Present only here — a
            # result this engine did not settle carries no certificate key at all, so absence
            # means "no certificate exists", never an empty record.
            CERTIFICATE_KEY: [_certificate_record(index, cert) for index, cert, _ in certified],
        }
        # A reason no probe could isolate is not a reason shown deleted, so it never turns the
        # verdict — but a reader must be told the certified set was not complete.
        caveat = (
            f" {uncertified_reasons} reason(s) could not be switched off in isolation and are "
            "counted neither way."
            if uncertified_reasons
            else ""
        ) + (
            f" {undetermined_reasons} of those are reasons the joint-deletion search did not "
            "resolve, so they are not counted deleted: a bounded enumeration names fewer missing "
            "reasons than a complete one, never more."
            if undetermined_reasons
            else ""
        )
        skipped = (
            f" {uncertifiable} decision(s) in the trace exposed no artefact and were not certified."
            if uncertifiable
            else ""
        )
        # Named beside the caveat rather than folded into it: this one is not a reason the probe
        # declined, it is a decision the enumeration never reached. Kept apart from `skipped`
        # because the not-evaluated branch below states it in its own words and still owes the
        # reader the decisions that exposed no artefact.
        # The non-monotonicity fingerprint is not remarked on down here any more: an artefact whose
        # probe found one had already declared itself monotone, and `_refused` returned above. The
        # flag is not gone, it moved from a caveat on a verdict to the measurement that withdraws
        # one — `certificate.ReasonVerdict.non_monotone` and `Certificate.non_monotone` are where
        # it is still kept, and `deletion_semantics_refusal` is what reads it.
        unmeasured = (
            f" {unenumerated} decision(s) had no reason enumerated at all, so "
            f"{', '.join(measures)} is unmeasured for them and this verdict covers them not at "
            "all."
            if unenumerated
            else ""
        )

        breached = [(index, cert) for index, cert, held in certified if not held]
        if breached:
            details["violation_step_indices"] = [index for index, _ in breached]
            details["offending_trace_segment"] = [records[index] for index, _ in breached]
            if DELETED_REASON_COUNT in measures:
                worst = max(breached, key=lambda item: len(item[1].deleted))[1]
                missing_reasons = "; ".join(worst.missing_reasons()) or "none named"
                finding = (
                    f"the stated reasons are not all the reasons. On decision "
                    f"#{breached[0][0]} exact inference found {len(worst.verdicts)} reason(s) and "
                    f"the deletion probe showed the system's answer does not depend on "
                    f"{len(worst.deleted)} of them — {missing_reasons}."
                )
            else:
                # The other measured signal: the finding is about the *value*, so the decision the
                # summary names is the one furthest from exact inference rather than the one
                # missing the most reasons.
                worst = max(breached, key=lambda item: abs(item[1].value_gap))[1]
                finding = (
                    f"the system's inference is not the semantics it claims. On decision "
                    f"#{breached[0][0]} the engine answered {worst.engine_value:.6f} where exact "
                    f"{worst.exact_semantics} over the same model encoding and the same "
                    f"interpretation answers {worst.exact_value:.6f} — a gap of "
                    f"{abs(worst.value_gap):.6f}, larger than the margin that decision's own "
                    "record states for itself."
                )
            return _result(
                req,
                Verdict.VIOLATED,
                reached,
                (
                    f"Violated on {len(breached)} of {len(certified)} certified decision(s): "
                    f"{finding} Attribution: {worst.attribution}"
                    f"{caveat}{skipped}{unmeasured} Measured against the inference "
                    f"artefact the system exposed, not read from its decision log.{recounted_note}"
                ),
                details=details,
            )

        # A violation needs one witness, a satisfaction needs complete evidence: the breach above
        # stands whatever went unmeasured beside it, and satisfied does not.
        if unenumerated:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: bounded proof enumeration found no reason at all behind "
                    f"{unenumerated} of the {unenumerated + len(certified)} certified "
                    f"decision(s), so {', '.join(measures)} is unmeasured for them. No reason "
                    f"was shown deleted on the other {len(certified)}, but satisfaction over a "
                    "subset of the trace is not satisfaction over the trace: a violation needs "
                    "one witness, a satisfaction needs complete evidence. The artefact's own "
                    f"exact_depth is the usual cause.{caveat}{skipped} Nothing is claimed either "
                    "way."
                ),
            )

        if antecedent_node is not None and not triggered_at:
            return not_evaluated_for_unreachable_trigger(
                req,
                antecedent_text,
                f"the {len(certified)} certified decision(s) of this trace",
                details,
            )

        # A certified decision whose antecedent was false was measured and then set aside: the
        # implication holds on it vacuously, so it never turns the verdict, and a summary that
        # counted it among the decisions measured clean would be false about the measurement. Both
        # earlier clauses name evidence the probe could not get; this one names evidence it got and
        # the duty does not ask about.
        untriggered = (
            [(index, cert) for index, cert, _ in certified if index not in triggered_at]
            if antecedent_node is not None
            else []
        )
        set_aside = sum(len(cert.deleted) for _, cert in untriggered)
        if untriggered:
            details["decisions_whose_trigger_never_fired"] = [
                index for index, _ in untriggered
            ]
            details["deleted_reasons_behind_an_untriggered_decision"] = set_aside
        untouched = (
            f" On {len(untriggered)} of them the trigger {antecedent_text} was false — they stated "
            "no reasons at all — so the duty asks nothing of them and this verdict says nothing "
            "about whether their reasons were all the reasons"
            + (
                f", including the {set_aside} reason(s) the deletion probe measured deleted behind "
                "them and set aside here."
                if set_aside
                else "."
            )
            if untriggered
            else ""
        )
        return _result(
            req,
            Verdict.SATISFIED,
            reached,
            (
                f"Probed over {len(certified)} certified decision(s), "
                f"{len(triggered_at)} of which the duty's trigger reached"
                if untriggered
                else f"Probed over {len(certified)} certified decision(s)"
            )
            + (
                (
                    ": every reason exact bounded proof enumeration found is one the system's own "
                    "answer depends on, so no reason was shown deleted"
                    if DELETED_REASON_COUNT in measures
                    else (
                        ": on every one of them the system's own engine answered within the "
                        "margin that decision's record states for itself of exact "
                        f"{certified[0][1].exact_semantics} over the same model encoding, so the "
                        "inference was not shown to depart from the semantics it claims"
                    )
                )
                + (" on those." if untriggered else ".")
                + f"{untouched}{caveat}{skipped} Holds on the decisions whose artefact was "
                "exposed and within the probes the budget below names; nothing here extends the "
                f"claim to a decision the system did not open up.{recounted_note}"
            ),
            details=details,
        )
