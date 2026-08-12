"""Tests for the duty whose verdict comes from a measured deviation, not a declared one.

What this module is for:
  `gdpr_recital71_error_risk_minimised` used to read `scope_statements_declared_deviation` — a
  number the system wrote about its own approximation error into its own record. It rewarded the
  measurement and not the accuracy: a system that silently under-reported its error passed, and a
  system honest enough to report a large one was the only kind the duty could flag
  (`docs/findings-nesyarena.md`, finding 1, *What has not changed*). Its left-hand side is now
  `engines.certificate.SEMANTICS_VALUE_GAP`, which reasonsmith measures from the inference artefact
  the system exposes: exact inference's answer against the system's own engine's answer, to the
  same query on the same interpretation.

  These tests hold the duty to what it now claims and — more importantly — to what it refuses.
  `docs/semantics.md` §3 (*The inference artefact*) and §4 (the four outcomes) are the contract.

What a reader must not break:
  - The requirement is loaded from the shipped pack, never re-written here. A test that authored
    its own spec would pass while the pack said something else.
  - **A system that honestly declares an approximation is never accused.** The closed vocabulary
    (`spec.CLAIMED_SEMANTICS`) has no member for a documented approximation of another member, so
    an approximating system's honest declaration is one no reference here computes, and the duty is
    reported *not evaluated* naming the claim. `test_an_honestly_declared_approximation_is_not_
    accused` is that case, and it is the one that matters: the whole ordering of this work — the
    vocabulary closing before any verdict read a gap — exists to prevent that false accusation.
  - Every artefact family outside the one that computes a reference is `unattainable`, never
    downgraded to a weaker check and never satisfied.
  - The measurement is never read from the record. A record claiming a small gap does not move a
    verdict, for the reason `_env` overwrites the deleted-reason count: a system that could settle
    this duty by writing a number about itself would be grading its own homework.
"""

from __future__ import annotations

from dataclasses import replace

from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.suts import ExactWMC, TopK

from reasonsmith.artifacts.ground_program import GroundProgramArtifact
from reasonsmith.artifacts.reason_trace import ReasonTraceArtifact
from reasonsmith.demo import DEPLOYED_CASES, SilentDropAdapter, certify_case
from reasonsmith.engines.certificate import DELETED_REASON_COUNT, SEMANTICS_VALUE_GAP
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import EvidenceBasis, Strength, Verdict

REQUIREMENT_ID = "gdpr_recital71_error_risk_minimised"

#: The demonstration's own approve threshold. It is the *system's* number here, and the margin each
#: record carries below is that system's own distance from it — the bound the clause's rationale
#: insists on, so that no number in this duty is one reasonsmith invented.
THRESHOLD = 0.5


def requirement():
    return load_pack("gdpr").get_requirement(REQUIREMENT_ID)


class _HonestlyApproximate(SilentDropAdapter):
    """The same silently-dropping engine, declaring a semantics it does not claim to compute.

    It is the shipped perturbed adapter with one attribute changed, which is the point: the
    behaviour that gets it accused below is identical, and the declaration is the whole of the
    difference.
    """

    def __init__(self):
        super().__init__()
        self.claimed_semantics = "weighted sum"


class _FixedGapAdapter:
    supports_grad = False
    claimed_semantics = "distribution semantics"

    def __init__(self, gap: float):
        self.gap = gap
        self.name = f"test:fixed-gap-{gap}"

    def infer(self, program, base, queries):
        exact = ReferenceAdapter(ExactWMC()).infer(program, base, queries)
        return {query: max(0.0, value - self.gap) for query, value in exact.items()}


class _Pipeline:
    """The demonstration's own two decisions, behind a swappable engine, logging its own margin."""

    CAPABILITIES = frozenset({
        "decision_id",
        "artifact_logs_decision_record",
        SEMANTICS_VALUE_GAP,
        "artifact_logs_decision_margin",
        "scope_statements_approximation_vs_guarantee",
    })

    def __init__(self, engine, claimed_gap: float | None = None):
        self.engine = engine
        self.claimed_gap = claimed_gap

    def capabilities(self) -> set[str]:
        return set(self.CAPABILITIES)

    def decisions(self) -> list[dict]:
        records = []
        for case in DEPLOYED_CASES:
            cert = certify_case(case, self.engine)
            record = {
                "decision_id": case.case_id,
                "artifact_logs_decision_record": f"adverse action on {case.case_id}",
                "artifact_logs_decision_margin": abs(cert.engine_value - THRESHOLD),
                "scope_statements_approximation_vs_guarantee": "approximation",
            }
            if self.claimed_gap is not None:
                record[SEMANTICS_VALUE_GAP] = self.claimed_gap
            records.append(record)
        return records

    def logic(self):
        return None

    def artifact(self, decision: dict) -> dict | None:
        for case in DEPLOYED_CASES:
            if case.case_id == decision.get("decision_id"):
                return {
                    "program": case.program,
                    "base": case.base,
                    "query": case.query,
                    "adapter": self.engine,
                    "exact_depth": 1,
                    "monotone": True,
                    "labels": case.labels,
                }
        return None


class _RecountingPipeline(_Pipeline):
    """The other shipped family: a rationale the system recounts, with no model encoding."""

    def artifact(self, decision: dict) -> ReasonTraceArtifact | None:
        return ReasonTraceArtifact(
            decision.get("decision_id"),
            {"C01 — income insufficient": frozenset({"dti_above_policy"})},
            lambda suppressed: 0.0 if suppressed else 0.8,
            engine_name="a decoder behind complete()",
            claimed_semantics="distribution semantics",
            monotone=True,
            weights={"C01 — income insufficient": 0.8},
        )


class _UnrecognisedReferenceArtifact(GroundProgramArtifact):
    """An out-of-tree family naming a reference this build's vocabulary has no member for."""

    exact_semantics = "approximate WMC"


class _UnrecognisedReferencePipeline(_Pipeline):
    def artifact(self, decision: dict) -> GroundProgramArtifact | None:
        for case in DEPLOYED_CASES:
            if case.case_id == decision.get("decision_id"):
                return _UnrecognisedReferenceArtifact(
                    case.program, case.base, case.query, self.engine, 1, case.labels, True
                )
        return None


class _ShallowPipeline(_Pipeline):
    """The same exposed artefacts, with reason enumeration deliberately finding none."""

    def artifact(self, decision: dict) -> dict | None:
        artifact = super().artifact(decision)
        if artifact is not None:
            artifact["exact_depth"] = 0
        return artifact


class _ShallowBothMeasuresPipeline(_ShallowPipeline):
    def capabilities(self):
        return super().capabilities() | {DELETED_REASON_COUNT}


def _result(sut):
    return evaluate_requirement(requirement(), sut)


def test_the_deviation_duty_is_interpretive_and_settled_against_the_artefact():
    """A recital is not an obligation, and this one is now measured rather than read.

    Three halves matter. Reported as binding it would overclaim what Recital 71 is. Limited to
    `high-risk` it would repeat the gap it exists to close. And on any basis but `artifact` it
    would have a ladder that could answer it off the system's own log, which is the substitution
    the repair removed.
    """
    req = requirement()
    assert req.binding is False
    assert req.scope == ""
    assert req.formalism == "temporal"
    assert SEMANTICS_VALUE_GAP in req.requires
    assert "scope_statements_declared_deviation" not in req.requires
    from reasonsmith.report import evidence_basis

    assert evidence_basis(req) is EvidenceBasis.ARTIFACT


def test_two_systems_differing_only_in_their_inference_get_different_verdicts():
    """Objective 5's falsifying check, against the shipped demo pair.

    The two systems are identical in every respect a report can see — the same pack, the same
    decisions, the same capability set, the same records, the same declared semantics — and differ
    only in whether the engine behind `artifact()` implements what it declares. Before the duty
    read the measurement the two reports agreed on every requirement, which is what finding 1
    measured rather than predicted.
    """
    exact = check_conformance(_Pipeline(ReferenceAdapter(ExactWMC())), load_pack("gdpr"))
    deviating = check_conformance(_Pipeline(SilentDropAdapter()), load_pack("gdpr"))

    def verdicts(report):
        return {r.requirement_id: (r.verdict, r.strength) for r in report.results}

    assert verdicts(exact) != verdicts(deviating)
    assert verdicts(exact)[REQUIREMENT_ID] == (Verdict.SATISFIED, Strength.PROBED)
    assert verdicts(deviating)[REQUIREMENT_ID] == (Verdict.VIOLATED, Strength.PROBED)


def test_the_violation_names_the_two_answers_it_compared():
    """A finding a reader cannot check is a finding they have to take on trust."""
    result = _result(_Pipeline(SilentDropAdapter()))
    assert result.verdict == Verdict.VIOLATED
    assert "distribution semantics" in result.evidence_summary
    assert "0.632000" in result.evidence_summary
    assert result.details["violation_step_indices"] == [0]


def test_value_gap_summary_names_the_decision_with_the_largest_gap():
    class _TwoGapPipeline(_Pipeline):
        def decisions(self):
            return [
                {
                    "decision_id": case.case_id,
                    "artifact_logs_decision_record": f"adverse action on {case.case_id}",
                    "artifact_logs_decision_margin": 0.0,
                    "scope_statements_approximation_vs_guarantee": "approximation",
                }
                for case in DEPLOYED_CASES
            ]

        def artifact(self, decision):
            for index, case in enumerate(DEPLOYED_CASES):
                if case.case_id == decision.get("decision_id"):
                    return {
                        "program": case.program,
                        "base": case.base,
                        "query": case.query,
                        "adapter": _FixedGapAdapter((index + 1) / 100),
                        "exact_depth": 1,
                        "monotone": True,
                        "labels": case.labels,
                    }
            return None

    result = _result(_TwoGapPipeline(ReferenceAdapter(ExactWMC())))

    assert result.verdict == Verdict.VIOLATED
    assert result.details["violation_step_indices"] == [0, 1]
    assert "On decision #1" in result.evidence_summary
    assert "a gap of 0.020000" in result.evidence_summary


def test_the_measured_gap_is_never_read_from_the_record():
    """A system cannot discharge this duty by writing a small number about itself into its log."""
    honest_log = _result(_Pipeline(SilentDropAdapter()))
    flattering_log = _result(_Pipeline(SilentDropAdapter(), claimed_gap=0.0))

    assert honest_log.verdict == Verdict.VIOLATED
    assert flattering_log.verdict == Verdict.VIOLATED


def test_an_honestly_declared_approximation_is_not_accused():
    """The case this whole ordering of work exists for.

    The engine here is the *same* deviating engine the test above reports violated. What differs is
    that it does not declare the semantics reasonsmith computes a reference for, and the closed
    vocabulary has no member for a documented approximation of one. So the honest answer is that
    this build cannot evaluate the claim — *not evaluated*, naming it — and never that the system
    departed from a semantics it never claimed. It is not `unattainable` either: nothing about the
    system needs to change, the gap is in this tool.
    """
    result = _result(_Pipeline(_HonestlyApproximate()))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "Not evaluated" in result.evidence_summary
    assert result.details["claimed_semantics"] == "weighted sum"
    assert result.details["reference_semantics"] == "distribution semantics"


def test_a_reference_outside_the_vocabulary_is_reported_and_never_raised():
    """A family naming a reference this build cannot compare is the tool's gap, not a failure.

    The value is not the audited system's claim, so refusing it where it is read — inside a
    conformance run — would turn a duty this build cannot evaluate into a decision that raised.
    The outcome owed is the mismatch refusal, naming both names.
    """
    result = _result(_UnrecognisedReferencePipeline(SilentDropAdapter()))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "Not evaluated" in result.evidence_summary
    assert result.details["reason"] == "no_reference_for_the_claimed_semantics"
    assert result.details["claimed_semantics"] == "distribution semantics"
    assert result.details["reference_semantics"] == "approximate WMC"


def test_an_artefact_family_that_computes_no_reference_is_unattainable():
    """The recounted family answers a different question, so it is refused rather than reused.

    `ReasonTraceArtifact.exact_value()` is the sum of the weights the *system* recounted. The
    difference between it and the system's answer measures how faithful a rationale is to an
    answer; it looks identical as a number and instructs a reader to do the opposite thing.
    """
    result = _result(_RecountingPipeline(SilentDropAdapter()))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert SEMANTICS_VALUE_GAP in result.signals_missing


def test_a_system_exposing_no_artefact_is_unattainable_never_satisfied():
    """Silence is not compliance, and no weaker rung stands in for the measurement."""
    req = requirement()
    sut = BaseSUT(set(req.requires))
    result = evaluate_requirement(req, sut, [{name: 0.0 for name in req.requires}])

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE


def test_a_system_that_does_not_declare_the_measured_signal_is_unattainable():
    """The gate is conjunctive, and a system never claiming it can expose an artefact says so."""
    req = requirement()

    class _Undeclared(_Pipeline):
        def capabilities(self):
            return set(self.CAPABILITIES) - {SEMANTICS_VALUE_GAP}

    result = evaluate_requirement(req, _Undeclared(ReferenceAdapter(ExactWMC())))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert SEMANTICS_VALUE_GAP in result.signals_missing


def test_a_value_gap_with_no_enumerated_reason_is_evaluated():
    """A breached value gap remains a witness even when reason enumeration found nothing."""
    result = _result(_ShallowPipeline(SilentDropAdapter()))

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROBED
    assert result.details["violation_step_indices"] == [1]
    assert "Measured against the inference artefact" in result.evidence_summary


def test_a_value_gap_with_no_enumerated_reason_can_be_satisfied():
    """A within-margin value comparison does not need a deletion-probe reason set."""
    result = _result(_ShallowPipeline(ReferenceAdapter(TopK(0))))

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    assert "inference was not shown to depart" in result.evidence_summary


def test_a_requirement_reading_both_measures_still_requires_enumeration():
    """Adding the deleted count restores its enumeration gate for the same certificate."""
    req = requirement()
    both = replace(
        req,
        spec=(
            "always(artifact_logs_semantics_value_gap <= artifact_logs_decision_margin and "
            "artifact_logs_deleted_reason_count <= 0)"
        ),
        requires=(*req.requires, DELETED_REASON_COUNT),
    )
    result = evaluate_requirement(
        both, _ShallowBothMeasuresPipeline(ReferenceAdapter(ExactWMC()))
    )

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert DELETED_REASON_COUNT in result.evidence_summary
    assert "no reason at all" in result.evidence_summary


def test_a_gap_exactly_equal_to_the_margin_is_satisfied():
    """The clause's own comparison is non-strict, so equality is a checked limit and not a breach.

    Pinned against the exact engine, whose gap is zero on a decision whose margin is zero: the
    boundary is reached by the measurement rather than by a number chosen to reach it.
    """
    result = _result(_Pipeline(ReferenceAdapter(ExactWMC())))
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
