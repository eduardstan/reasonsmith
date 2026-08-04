"""The reason-deletion certificate as an engine on the ladder.

What this module is for:
  `certificate.py` could measure which reasons an engine's answer stopped depending on, and no
  duty and no CLI verb reached it. The two halves of the package met in exactly one place —
  `demo.render_key_finding_html`, on decision `APP-1042` — and there they disagreed: the evidence
  record reports COMPLETE while the certificate reports FAIL, so `reasonsmith check` reported the
  reason-giving duty *satisfied* on a decision this same package proves has four reasons deleted.
  These tests hold the bridge that closes it.

What a reader must not break:
  - The acceptance test asserts on the verdict, never on a rendering. A bridge that only changed
    what the report printed would not have changed what the tool claims.
  - A system that cannot supply the oracle must be reported UNATTAINABLE on the adequacy duty and
    must never fall back to the presence property. Two tests hold that from two directions: the
    ladder itself has exactly one rung, and a system that logs its own completeness count is still
    judged on the measurement.
    Why this matters: substituting "some reason was stated" for "the stated reasons are all the
    reasons" is the defect this engine exists to remove, and it is the kind of defect that comes
    back as a convenience.
"""

from __future__ import annotations

from typing import Any

import pytest
from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.suts import ExactWMC, TopK

from reasonsmith import demo
from reasonsmith.cli import main as cli_main
from reasonsmith.engines.certificate import (
    ARTIFACT_METHOD,
    DELETED_REASON_COUNT,
    CertificateEngine,
)
from reasonsmith.report import (
    PROBE_BUDGET_FIELDS,
    PROBE_BUDGET_KEY,
    _engine_ladder,
    _EvaluationResources,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

#: The duty this engine settles, and its sibling, which reads the same clause and answers the
#: weaker question. They are checked together on purpose.
ADEQUACY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"
SPECIFICITY = "ecoa_reg_b_1002_9_b_2_specific_reasons"

#: The demonstration's own case: five reasons, of which a top-1 engine keeps one.
APP_1042 = demo.build_case("APP-1042", "typical", demo.CREDIT_QUERY, demo.CREDIT_REASONS, 0.88)


def _duty(req_id: str = ADEQUACY):
    return load_pack("ecoa").get_requirement(req_id)


class _CreditSystem:
    """One decision, exposing whatever the test asks it to expose.

    `artifact` is attached only when `oracle` is given, so a system with no oracle is a system
    without the attribute at all — which is how a real adapter that cannot open up its inference
    presents itself.
    """

    system_domains = ("consumer-credit",)

    def __init__(self, oracle=None, record: dict[str, Any] | None = None, trace=None):
        self._record = record if record is not None else {
            "decision_id": "APP-1042",
            "artifact_logs_reason_explanation": "C01 — Income insufficient for amount requested",
        }
        self._trace = [self._record] if trace is None else trace
        if oracle is not None:
            self._oracle = oracle
            self.artifact = self._artifact

    def capabilities(self) -> set[str]:
        return {"decision_id", "artifact_logs_reason_explanation", DELETED_REASON_COUNT}

    def decisions(self) -> list[dict[str, Any]]:
        return list(self._trace)

    def logic(self) -> Any:
        return None

    def _artifact(self, decision: dict[str, Any]):
        return self._oracle(decision)


def _artifact_of(adapter):
    """The artefact behind `APP-1042`, at the depth the record itself asks for.

    A record carrying `shallow` gets `exact_depth=0`, which enumerates no reason at all — the one
    number the reproduction of the false-satisfied defect moves.
    """
    def supply(decision: dict[str, Any]):
        if decision.get("decision_id") != APP_1042.case_id:
            return None
        return {
            "program": APP_1042.program,
            "base": APP_1042.base,
            "query": APP_1042.query,
            "adapter": adapter,
            "exact_depth": 0 if decision.get("shallow") else 1,
            "labels": APP_1042.labels,
        }

    return supply


# --------------------------------------------------------------- the acceptance test ----


def test_the_demonstrations_own_decision_is_reported_violated():
    """`APP-1042` — record COMPLETE, certificate FAIL — must now come back violated.

    Asserted on the verdict rather than on any rendering: the defect was what the tool *claimed*,
    not how it printed it.
    """
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    result = next(r for r in report.results if r.requirement_id == ADEQUACY)

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROBED
    deleted = result.details["certificates"][-1]
    assert deleted["decision_index"] == 1  # APP-1042 is the second decision in the log
    assert deleted["reasons_found"] == 5
    assert deleted["reasons_deleted"] == 4
    assert "top-k proof truncation at k=1" in deleted["attribution"]


def test_form_completeness_and_reason_fidelity_are_now_separate_verdicts():
    """The two halves that used to disagree silently now disagree in the report, out loud.

    On the same decision and the same trace, the specificity duty is satisfied — a statement of
    reasons is there and names none of the wordings the clause calls insufficient — while the
    adequacy duty is violated. That is the finding the demonstration narrated and the report
    could not previously make.
    """
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    verdicts = {r.requirement_id: r.verdict for r in report.results}

    assert verdicts[SPECIFICITY] == Verdict.SATISFIED
    assert verdicts[ADEQUACY] == Verdict.VIOLATED


def test_the_cli_reports_the_demonstration_decision_violated(capsys):
    """The front door, not just the library: a violation exits 2 and names the duty."""
    exit_code = cli_main([
        "check",
        "--system-module",
        "reasonsmith.demo:deployed_credit_system",
        "--pack",
        "ecoa",
    ])
    out = capsys.readouterr().out

    assert exit_code == 2
    assert f"[PROBED] {ADEQUACY}" in out
    assert "violated" in out


# ------------------------------------------------- no oracle is never a presence check ----


def test_a_system_exposing_no_oracle_is_unattainable_and_names_the_signal():
    """A system that cannot open up its inference is unattainable, never satisfied.

    The system here declares the capability and logs a perfectly good statement of reasons, so
    every weaker rung would report *satisfied*. Only the measurement can settle this duty, and
    the result says which signal could not be measured and why nothing weaker stands in for it.
    """
    result = evaluate_requirement(_duty(), _CreditSystem())

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert result.signals_missing == (DELETED_REASON_COUNT,)
    assert ARTIFACT_METHOD in result.evidence_summary
    assert "substitution" in result.evidence_summary


def test_the_adequacy_duty_is_never_downgraded_to_the_presence_check():
    """The ladder for this duty has exactly one rung, whatever else the system exposes.

    A system exposing `logic()` and `decide()` would otherwise reach the proved and probed rungs,
    and a trace would reach the observed one — each of them answering *some reason was stated*
    where the duty asks whether the stated reasons are all the reasons. This test fails the moment
    a later change lets any of them stand in.
    """
    class _FullySurfaced(_CreditSystem):
        def logic(self):
            return {"rules": "", "inputs": {}, "constraints": []}

        def decide(self, case):
            return dict(case)

    req = _duty()
    sut = _FullySurfaced()
    ladder = _engine_ladder(req, sut, None, _EvaluationResources(sut))

    assert len(ladder) == 1, "the adequacy duty gained a rung that answers a weaker property"
    strength, run = ladder[0]
    assert strength == Strength.PROBED
    assert run().strength == Strength.UNATTAINABLE

    # And end to end: with the strongest surfaces exposed, the verdict is still unattainable.
    assert evaluate_requirement(req, sut).strength == Strength.UNATTAINABLE


def test_a_logged_completeness_count_never_settles_the_duty():
    """A system that writes its own zero into the record is still judged on the measurement.

    This is the self-declared flag `docs/semantics.md` §3 refuses, in the one place it could still
    have got in: the engine builds the property's environment from the record, so a record
    claiming `artifact_logs_deleted_reason_count = 0` would settle the duty if the measured value
    did not overwrite it.
    """
    liar = {
        "decision_id": "APP-1042",
        "artifact_logs_reason_explanation": "C01 — Income insufficient for amount requested",
        DELETED_REASON_COUNT: 0,
    }
    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))), record=liar)
    result = evaluate_requirement(_duty(), sut)

    assert result.verdict == Verdict.VIOLATED
    assert result.details["certificates"][0]["reasons_deleted"] == 4


# ------------------------------------------------------------- what the rung does claim ----


def test_the_certificate_verdict_carries_its_probe_budget():
    """A probed result cannot exist without the bound that produced it, this rung included."""
    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))))
    result = evaluate_requirement(_duty(), sut)

    budget = result.details[PROBE_BUDGET_KEY]
    assert all(field in budget for field in PROBE_BUDGET_FIELDS)
    # One baseline inference plus one replay per *fact* the probe switched off — every private
    # fact of every reason, not one per reason.
    assert budget["trials"] == 9
    assert budget["input_space"] == {"decisions certified": 1, "facts switched off": 8}
    assert "deterministic" in budget["seed"]

    # The invariant is enforced at construction, not at rendering: strip the budget and the
    # result refuses to exist.
    with pytest.raises(ValueError, match="search budget"):
        type(result)(
            requirement_id=result.requirement_id,
            source_clause=result.source_clause,
            verdict=result.verdict,
            strength=Strength.PROBED,
            signals_required=result.signals_required,
        )


def test_an_engine_that_deletes_nothing_is_probed_and_never_proved():
    """Exact inference behind the same decision deletes no reason — and still only reaches probed.

    The certificate is exact on *one* ground program and one base interpretation. Nothing here
    establishes the property for a decision the system did not expose, which is the whole distance
    between this rung and `proved`.
    """
    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(ExactWMC())))
    result = evaluate_requirement(_duty(), sut)

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    assert "nothing here extends the claim" in result.evidence_summary


def test_a_decision_whose_reasons_were_never_enumerated_cannot_buy_satisfied():
    """Weaker evidence must never produce a stronger verdict.

    The same system, the same trace, the same reasons, the same notices — only the artefact's own
    `exact_depth` moves, from 1 to 0. At 0 the enumeration finds no reason, so nothing is switched
    off and `len(cert.deleted)` is zero for the absence of a measurement rather than for a decision
    whose reasons the engine all used. `certificate.Certificate.verdict` already refuses to call
    such a query a PASS; this asserts the engine one layer up makes that refusal — through
    `conformance.measured` — instead of reporting the clean unqualified probe that turned the
    demonstration's breached decision into a satisfied one.

    Both halves of the asymmetry are pinned here: a violation needs one witness, so a measured
    breach still comes back `violated` at `probed` beside an unmeasured decision, while a
    satisfaction needs complete evidence, so a trace holding one unmeasured decision buys no
    strength at all however clean the rest of it is.
    """
    shallow = {
        "decision_id": "APP-1042",
        "artifact_logs_reason_explanation": "C01 — Income insufficient for amount requested",
        "shallow": True,
    }
    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))), record=shallow)
    result = evaluate_requirement(_duty(), sut)

    assert result.verdict != Verdict.SATISFIED
    assert result.strength is None
    assert "no reason at all" in result.evidence_summary
    assert DELETED_REASON_COUNT in result.evidence_summary

    # A violation needs one witness: a decision that *was* enumerated and breached still carries
    # its verdict, and the unenumerated one beside it is counted and named, never allowed to
    # dilute or to silence it.
    deep = {k: v for k, v in shallow.items() if k != "shallow"}
    mixed = _CreditSystem(
        oracle=_artifact_of(ReferenceAdapter(TopK(1))), record=deep, trace=[deep, shallow]
    )
    partial = evaluate_requirement(_duty(), mixed)

    assert partial.verdict == Verdict.VIOLATED
    assert partial.strength == Strength.PROBED
    assert partial.details["decisions_certified"] == 1
    assert partial.details["decisions_without_an_enumerated_reason"] == 1
    assert "no reason enumerated at all" in partial.evidence_summary

    # A satisfaction needs complete evidence: the same trace with an engine that deletes nothing
    # would be satisfied on the enumerated decision alone, and is not evaluated because of the
    # decision beside it. Satisfaction over a subset of the trace is not satisfaction over it.
    clean = _CreditSystem(
        oracle=_artifact_of(ReferenceAdapter(ExactWMC())), record=deep, trace=[deep, shallow]
    )
    subset = evaluate_requirement(_duty(), clean)

    assert subset.verdict != Verdict.SATISFIED
    assert subset.strength is None
    assert DELETED_REASON_COUNT in subset.evidence_summary
    assert "subset of the trace" in subset.evidence_summary


def test_a_trace_with_no_artifact_is_not_evaluated_never_satisfied():
    """An empty trace, and a trace whose decisions the system cannot open up, both say so."""
    empty = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))), trace=[])
    assert evaluate_requirement(_duty(), empty).strength is None

    other = _CreditSystem(
        oracle=_artifact_of(ReferenceAdapter(TopK(1))),
        record={"decision_id": "APP-9999", "artifact_logs_reason_explanation": "C01"},
    )
    result = evaluate_requirement(_duty(), other)
    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "no inference artefact" in result.evidence_summary


def test_an_artifact_that_raises_or_is_the_wrong_shape_is_not_evaluated():
    """A broken oracle establishes nothing, and is reported rather than raised through the run."""
    def boom(_decision):
        raise RuntimeError("the artefact store is down")

    result = evaluate_requirement(_duty(), _CreditSystem(oracle=boom))
    assert result.strength is None
    assert "the artefact store is down" in result.evidence_summary

    result = evaluate_requirement(_duty(), _CreditSystem(oracle=lambda _d: ["not", "a", "mapping"]))
    assert result.strength is None
    assert "certificate.certify" in result.evidence_summary

    result = evaluate_requirement(_duty(), _CreditSystem(oracle=lambda _d: {"program": None}))
    assert result.strength is None
    assert "raised" in result.evidence_summary


def test_a_property_that_cannot_be_decided_on_a_record_is_not_evaluated():
    """The measurement can succeed and the property still fail to decide. Neither raises through.

    Two ways in, both reachable from a pack: a construct this engine's interpreter does not
    implement, and a second signal the certified record does not carry. The count was measured
    either way, so the failure is reported as not evaluated rather than escaping the run as a
    traceback the CLI does not catch.
    """
    from dataclasses import replace

    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))))

    temporal = replace(
        _duty(),
        spec=(
            "always(present(artifact_logs_reason_explanation) -> "
            "(artifact_logs_deleted_reason_count <= 0))"
        ),
        formalism="temporal",
    )
    result = CertificateEngine.evaluate(temporal, sut, sut.decisions())
    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "Not evaluated" in result.evidence_summary

    unread = replace(
        _duty(),
        spec=(
            "(artifact_logs_notification_latency_days <= 30) and "
            "(artifact_logs_deleted_reason_count <= 0)"
        ),
    )
    result = CertificateEngine.evaluate(unread, sut, sut.decisions())
    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert "artifact_logs_notification_latency_days" in result.evidence_summary


def test_the_engine_refuses_a_property_it_cannot_ground():
    """It measures one signal. A duty whose property never reads it is not evaluated, not passed.

    Reached only by a caller building a requirement by hand — the pack loader and the ladder agree
    on which duties come here — so guessing at what such a property meant would answer a duty
    nobody wrote.
    """
    from dataclasses import replace

    req = replace(_duty(), spec="present(artifact_logs_reason_explanation)", formalism="record")
    sut = _CreditSystem(oracle=_artifact_of(ReferenceAdapter(TopK(1))))
    result = CertificateEngine.evaluate(req, sut, sut.decisions())

    assert result.strength is None
    assert DELETED_REASON_COUNT in result.evidence_summary
