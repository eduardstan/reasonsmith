"""Certificate engine for reasonsmith v0.2.

What this module is for:
  Evaluates a *reason adequacy* duty — whether the reasons a decision states are all the reasons
  its own inference had — by running `reasonsmith.certificate.certify` against the inference
  artefact the system exposes, and grounding one measured signal,
  `artifact_logs_deleted_reason_count`, with what the deletion probe found.

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
  - The strength is PROBED and never PROVED. The certificate's reach is the decisions the system
    supplied and the deletion probes those decisions admitted, and `RequirementResult` refuses to
    construct the result without the budget that names both.
    Why this matters: exact inference is exact *on one ground program and one base
    interpretation* — `certificate.LIMITS` says so in its own words. Nothing here establishes the
    property for a decision the system did not expose.
  - A reason the probe could not switch off in isolation (`unseparable`, `inconclusive`) is not
    counted as deleted, and the count of them is reported.
    Why this matters: `certificate.certify` never assumes such a reason is live, and neither may
    this engine assume it was dropped. Counting it either way would put a verdict on evidence the
    probe explicitly declined to produce.
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

from reasonsmith.certificate import NON_MONOTONE_REMARK, Certificate, certify
from reasonsmith.conformance import measured
from reasonsmith.report import (
    CERTIFICATES_KEY,
    PROBE_BUDGET_KEY,
    RequirementResult,
    not_evaluated_for_unreachable_trigger,
)
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
    implication_antecedent,
    parse_property,
    signal_names,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

__all__ = ["ARTIFACT_METHOD", "DELETED_REASON_COUNT", "SEED", "STRATEGY", "CertificateEngine"]

#: The one signal this engine measures rather than reads. A duty naming it in `requires` is a
#: duty only this engine may settle (`report._engine_ladder`), and a system declaring it is
#: claiming it can expose the inference artefact below — not that it writes the number into a log.
DELETED_REASON_COUNT = "artifact_logs_deleted_reason_count"

#: The optional SUT method, exactly parallel to the optional `decide(case)`: given one decision
#: record, return the keyword arguments of `certificate.certify` for the inference that decision
#: came from, or None for a decision this system cannot open up. See `sut.SystemUnderTest`.
ARTIFACT_METHOD = "artifact"

#: The keyword arguments `artifact()` may return, named in the refusal so an adapter author is
#: told the shape rather than shown a TypeError from four frames down.
ARTIFACT_KEYS = ("program", "base", "query", "adapter", "exact_depth", "tol", "labels")

#: What the search does, named on every result it produces.
STRATEGY = (
    "for each decision the system exposed an inference artefact for, its reasons are enumerated "
    "exactly by bounded proof enumeration over the ground program and scored by exact weighted "
    "model counting; every fact of a reason that no other reason uses is then switched off alone "
    "and the system's own engine re-run on the perturbed interpretation. A reason no such deletion "
    "moves the engine on, where it moved exact inference, is a reason the engine's answer does "
    "not depend on, and is counted here. The probe only ever switches a fact off, never on"
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
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=verdict,
        strength=strength,
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=summary,
        details=dict(details or {}),
        binding=req.binding,
        scope=req.scope,
    )


def _env(record: Mapping[str, Any], cert: Certificate) -> dict[str, Any]:
    """The record, with the measured count written over anything the record claimed for it."""
    return {**record, DELETED_REASON_COUNT: len(cert.deleted)}


def _probes(cert: Certificate) -> int:
    """Inferences this certificate replayed: one baseline, plus one per fact it switched off and
    re-ran the engine on. A fact whose deletion does not move exact inference costs no re-run."""
    return 1 + sum(v.engine_probes for v in cert.verdicts)


class CertificateEngine:
    """Engine settling a reason-adequacy duty against the reason-deletion certificate."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: list[dict[str, Any]],
    ) -> RequirementResult:
        artifact = getattr(sut, ARTIFACT_METHOD, None)
        if not callable(artifact):
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                Strength.UNATTAINABLE,
                (
                    f"Unattainable as built: this duty asks whether the reasons a decision states "
                    f"are all the reasons its inference had, which is measured against the "
                    f"inference artefact and never read from a log. "
                    f"{type(sut).__name__} exposes no {ARTIFACT_METHOD}() supplying one, so "
                    f"{DELETED_REASON_COUNT} cannot be measured here. Nothing weaker stands in "
                    "for it: that the decision states some reason is a different property, and "
                    "reporting it in place of this one is the substitution this duty exists to "
                    "refuse."
                ),
                missing=(DELETED_REASON_COUNT,),
            )

        try:
            node = parse_property(req.spec)
        except UnsupportedConstructError as exc:
            return _result(
                req, Verdict.INCONCLUSIVE, None, f"Not evaluated: {exc}."
            )
        if DELETED_REASON_COUNT not in signal_names(node):
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: {req.spec!r} does not read {DELETED_REASON_COUNT}, which is "
                    "the only signal this engine measures. Nothing here grounds the rest of it."
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

        antecedent_node = implication_antecedent(node)
        antecedent_text = ast.unparse(antecedent_node) if antecedent_node is not None else ""
        # The decisions the duty's trigger reached, by index rather than as a count: the satisfied
        # summary owes a reader what it measured behind the *other* ones and set aside.
        triggered_at: set[int] = set()

        certified: list[tuple[int, Certificate, bool]] = []
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
            if not isinstance(supplied, Mapping):
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: {type(sut).__name__}.{ARTIFACT_METHOD}() returned "
                        f"{type(supplied).__name__} for decision #{index}; it must return the "
                        f"keyword arguments of certificate.certify ({', '.join(ARTIFACT_KEYS)}) "
                        "or None for a decision it cannot open up."
                    ),
                )
            try:
                cert = certify(**supplied)
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
            try:
                env = _env(record, cert)
                held = bool(eval_expression(node, env))
                if antecedent_node is not None and eval_expression(antecedent_node, env):
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
                    f"{len(records)} decision(s) in the trace, so {DELETED_REASON_COUNT} was "
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
                    f"of the {unenumerated} certified decision(s), so {DELETED_REASON_COUNT} is "
                    "unmeasured for every one of them and no reason was switched off. A zero "
                    "deleted-reason count on a decision whose reasons were never enumerated is "
                    "the absence of a measurement, not a measurement of zero — the artefact's own "
                    "exact_depth is the usual cause. Nothing is claimed either way."
                ),
            )

        uncertified_reasons = sum(len(cert.uncertified) for _, cert, _ in certified)
        budget = {
            "trials": sum(_probes(cert) for _, cert, _ in certified),
            "strategy": STRATEGY,
            "seed": SEED,
            "input_space": {
                "decisions certified": len(certified),
                "facts switched off": sum(
                    len(v.probe_facts) for _, cert, _ in certified for v in cert.verdicts
                ),
            },
        }
        details: dict[str, Any] = {
            PROBE_BUDGET_KEY: budget,
            "decisions_certified": len(certified),
            "decisions_without_an_artifact": uncertifiable,
            "decisions_without_an_enumerated_reason": unenumerated,
            "reasons_not_certifiable": uncertified_reasons,
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
        }
        # A reason no probe could isolate is not a reason shown deleted, so it never turns the
        # verdict — but a reader must be told the certified set was not complete.
        caveat = (
            f" {uncertified_reasons} reason(s) could not be switched off in isolation and are "
            "counted neither way."
            if uncertified_reasons
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
        # Not a caveat about coverage but about the instrument: on a system whose reasons can be
        # retracted, `deleted` reads a retraction as a drop. Said on the verdict rather than hidden
        # in an inconclusive bucket, which would lose the only signal that detects the condition.
        non_monotone = sum(len(cert.non_monotone) for _, cert, _ in certified)
        if non_monotone:
            details["reasons_whose_deletion_raised_the_engines_answer"] = non_monotone
        drift = (
            f" On {non_monotone} reason(s) {NON_MONOTONE_REMARK}"
            if non_monotone
            else ""
        )
        unmeasured = (
            f" {unenumerated} decision(s) had no reason enumerated at all, so "
            f"{DELETED_REASON_COUNT} is unmeasured for them and this verdict covers them not at "
            "all."
            if unenumerated
            else ""
        )

        breached = [(index, cert) for index, cert, held in certified if not held]
        if breached:
            details["violation_step_indices"] = [index for index, _ in breached]
            details["offending_trace_segment"] = [records[index] for index, _ in breached]
            worst = max(breached, key=lambda item: len(item[1].deleted))[1]
            missing_reasons = "; ".join(worst.missing_reasons()) or "none named"
            return _result(
                req,
                Verdict.VIOLATED,
                Strength.PROBED,
                (
                    f"Violated on {len(breached)} of {len(certified)} certified decision(s): the "
                    f"stated reasons are not all the reasons. On decision #{breached[0][0]} exact "
                    f"inference found {len(worst.verdicts)} reason(s) and the deletion probe "
                    f"showed the system's answer does not depend on {len(worst.deleted)} of them "
                    f"— {missing_reasons}. Attribution: {worst.attribution}"
                    f"{caveat}{skipped}{unmeasured}{drift} Measured against the inference "
                    "artefact the system exposed, not read from its decision log."
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
                    f"decision(s), so {DELETED_REASON_COUNT} is unmeasured for them. No reason "
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
            Strength.PROBED,
            (
                f"Probed over {len(certified)} certified decision(s), "
                f"{len(triggered_at)} of which the duty's trigger reached"
                if untriggered
                else f"Probed over {len(certified)} certified decision(s)"
            )
            + (
                ": every reason exact bounded proof enumeration found is one the system's own "
                "answer depends on, so no reason was shown deleted"
                + (" on those." if untriggered else ".")
                + f"{untouched}{caveat}{skipped}{drift} Holds on the decisions whose artefact was "
                "exposed and within the probes the budget below names; nothing here extends the "
                "claim to a decision the system did not open up."
            ),
            details=details,
        )
