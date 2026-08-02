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
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from reasonsmith.certificate import Certificate, certify
from reasonsmith.report import PROBE_BUDGET_KEY, RequirementResult
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
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
    "model counting; each reason holding a fact no other reason uses is then switched off alone "
    "and the system's own engine re-run on the perturbed interpretation. A reason whose deletion "
    "moves exact inference but leaves the engine unchanged is a reason the engine's answer does "
    "not depend on, and is counted here"
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
    """Inferences this certificate replayed: one baseline, plus one per reason it switched off."""
    return 1 + sum(1 for v in cert.verdicts if v.probe_fact is not None)


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
            certified.append((index, cert, bool(eval_expression(node, _env(record, cert)))))

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

        uncertified_reasons = sum(len(cert.uncertified) for _, cert, _ in certified)
        budget = {
            "trials": sum(_probes(cert) for _, cert, _ in certified),
            "strategy": STRATEGY,
            "seed": SEED,
            "input_space": {
                "decisions certified": len(certified),
                "reasons switched off": sum(
                    _probes(cert) - 1 for _, cert, _ in certified
                ),
            },
        }
        details: dict[str, Any] = {
            PROBE_BUDGET_KEY: budget,
            "decisions_certified": len(certified),
            "decisions_without_an_artifact": uncertifiable,
            "reasons_not_certifiable": uncertified_reasons,
            "certificates": [
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
                    f"{caveat}{skipped} Measured against the inference artefact the system "
                    "exposed, not read from its decision log."
                ),
                details=details,
            )

        return _result(
            req,
            Verdict.SATISFIED,
            Strength.PROBED,
            (
                f"Probed over {len(certified)} certified decision(s): every reason exact bounded "
                "proof enumeration found is one the system's own answer depends on, so no reason "
                f"was shown deleted.{caveat}{skipped} Holds on the decisions whose artefact was "
                "exposed and within the probes the budget below names; nothing here extends the "
                "claim to a decision the system did not open up."
            ),
            details=details,
        )
