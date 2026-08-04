"""The inference-artefact protocol, and the monotonicity declaration it turns on.

What this module is for:
  `reasonsmith.artifacts` is this package's own answer to *what a reason can be measured from*.
  Before it, `certificate.certify` named one representation in its signature and the deletion probe
  measured reasons out of it whatever the inference behind it did. These tests hold the two halves
  of the repair: the protocol is satisfiable by a family that has never heard of a ground program,
  and an artefact the deletion definition of a reason does not apply to is refused rather than
  measured.

What a reader must not break:
  - The defeasible system here is the reduced form of `data/rs-w1b-nonmonotonic-probe/defeasible.py`
    from the investigation that produced this work, and it must keep the property the whole finding
    turns on: the exception fact is in *no* rule body, so it is never enumerated and never switched
    off, and the probe therefore leaves no fingerprint at all. That is what makes the declaration
    load-bearing rather than a convenience — a run that could detect the condition from its own
    measurement would not need one.
  - A refusal is `not evaluated`. A test that accepted `unattainable` here would be accepting the
    instruction "change the system" for a creditor whose policy exceptions are lawful.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest
from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.ir import Atom, GroundProgram, Rule
from nesyarena.oracle import wmc
from nesyarena.suts import ExactWMC, TopK

from reasonsmith import artifacts, certificate, demo
from reasonsmith.artifacts import InferenceArtifact, default_label
from reasonsmith.artifacts.ground_program import GroundProgramArtifact
from reasonsmith.artifacts.reason_trace import ReasonTraceArtifact
from reasonsmith.certificate import certify, certify_artifact
from reasonsmith.engines.certificate import DELETED_REASON_COUNT
from reasonsmith.report import (
    EXACT_REASON_SET_KEY,
    PROBE_BUDGET_KEY,
    RequirementResult,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

ADEQUACY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"


def _duty():
    return load_pack("ecoa").get_requirement(ADEQUACY)


# ------------------------------------------------------- a defeasible credit system ----


class _RetractingAdapter:
    """An engine whose reasons are defeasible: while the exception holds it withdraws a reason.

    The defeat lives in the engine, not in the program, because a definite Horn program is monotone
    by construction — and because that is where a policy exception lives in a deployment, evaluated
    after the underwriting rules fire.
    """

    supports_grad = False
    claimed_semantics = "distribution semantics"

    def __init__(self, exception: Atom, retracts: frozenset):
        self.exception, self.retracts = exception, retracts
        self.name = "defeasible:exception-retracts-a-reason"

    def infer(self, program, base, queries):
        fired = base.get(self.exception, 0.0) > 0.5
        out = {}
        for q in queries:
            kept = [pr for pr in program.proof_supports(q, 1)
                    if not (fired and frozenset(pr) == self.retracts)]
            out[q] = wmc(kept, base) if kept else 0.0
        return out


def _defeasible_case(*, exception_in_a_rule_body: bool):
    """Two reasons and an exception that retracts the first.

    With `exception_in_a_rule_body` False the exception supports nothing — the ordinary shape, since
    an exception does not help prove the conclusion — so it is in no reason, is never switched off,
    and the probe cannot see it at all. With it True the exception is a private fact of the second
    reason, the probe reaches it, and switching it off raises the engine's answer: the one
    fingerprint a non-monotone engine leaves.
    """
    q, a, b, other = Atom("q"), Atom("a"), Atom("b"), Atom("other")
    exception = Atom("policy_exception")
    second = (exception, other) if exception_in_a_rule_body else (other, Atom("third"))
    program = GroundProgram((Rule(q, (a, b)), Rule(q, second)))
    base = {a: 0.9, b: 0.9, other: 0.5, Atom("third"): 0.5, exception: 1.0}
    return {
        "program": program,
        "base": base,
        "query": q,
        "adapter": _RetractingAdapter(exception, frozenset({a, b})),
        "exact_depth": 1,
        "labels": {frozenset({a, b}): "R01 — the reason the exception withdrew"},
    }


class _DefeasibleCreditSystem:
    """`data/rs-w1b-nonmonotonic-probe/defeasible.py`, reduced to one decision.

    Its notice states exactly the reasons its engine's answer stood on, which is what a notice
    generated from a defeasible engine correctly says — so before the declaration existed, this
    system was reported *violated* for having stated its reasons correctly.
    """

    system_domains = ("consumer-credit",)

    def __init__(self, monotone: bool | None, *, exception_in_a_rule_body: bool = False):
        self._kwargs = {**_defeasible_case(
            exception_in_a_rule_body=exception_in_a_rule_body)}
        if monotone is not None:
            self._kwargs["monotone"] = monotone

    def capabilities(self) -> set[str]:
        return {"decision_id", "artifact_logs_reason_explanation", DELETED_REASON_COUNT}

    def decisions(self) -> list[dict[str, Any]]:
        return [{
            "decision_id": "DEF-1",
            "artifact_logs_reason_explanation": "R02 — the reason that survived",
        }]

    def logic(self) -> Any:
        return None

    def artifact(self, decision: dict[str, Any]):
        return dict(self._kwargs) if decision.get("decision_id") == "DEF-1" else None


# ----------------------------------------------------------------- the refusals ----


def test_an_artefact_declaring_non_monotone_inference_is_not_evaluated_and_names_why():
    """The acceptance case: a compliant creditor whose reasons are defeasible is no longer accused.

    Nothing in this run's own measurement could have detected the condition — the exception is in no
    rule body, so it is never enumerated and never switched off. The declaration is the only thing
    that stands between this system and a `violated` verdict.
    """
    result = evaluate_requirement(_duty(), _DefeasibleCreditSystem(monotone=False))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.verdict != Verdict.VIOLATED
    assert result.verdict != Verdict.SATISFIED
    # Not evaluated, and deliberately not unattainable: the gap is in this tool, not in the system.
    assert result.strength is None
    assert artifacts.DECLARED_NON_MONOTONE in result.evidence_summary
    assert result.details["reason"] == "deletion_semantics_do_not_apply"
    assert result.details["declared_monotone"] is False


def test_the_refusal_survives_a_whole_conformance_run_and_reaches_no_weaker_duty():
    """The duty's ladder is one rung, so the refusal cannot be answered by the presence check."""
    report = check_conformance(_DefeasibleCreditSystem(monotone=False), load_pack("ecoa"))
    result = next(r for r in report.results if r.requirement_id == ADEQUACY)

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    # The sibling duty over the same clause is untouched: it asks a different question and may
    # still be answered. What must not happen is this duty being answered in its place.
    sibling = next(
        r for r in report.results
        if r.requirement_id == "ecoa_reg_b_1002_9_b_2_specific_reasons"
    )
    assert sibling.requirement_id != result.requirement_id


def test_an_artefact_that_declares_nothing_is_not_evaluated_rather_than_assumed_monotone():
    """Silence is refused, for the reason the counterfactual engine refuses undeclared directions.

    Reading silence as monotone would leave the declaration worth nothing for every system built
    before it existed — which is every system the finding is about.
    """
    result = evaluate_requirement(_duty(), _DefeasibleCreditSystem(monotone=None))

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert artifacts.UNDECLARED_MONOTONICITY in result.evidence_summary
    assert result.details["declared_monotone"] is None


def test_a_declaration_the_probe_contradicts_is_refused_rather_than_trusted():
    """The one direction of check there is: a deletion that raised the answer refutes `monotone`.

    A self-declared flag nothing checks is a second self-declaration wearing an engine's clothes.
    This is why the `non_monotone` fingerprint is kept: it no longer decorates a verdict, it
    withdraws one.
    """
    system = _DefeasibleCreditSystem(monotone=True, exception_in_a_rule_body=True)
    result = evaluate_requirement(_duty(), system)

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert artifacts.DECLARATION_REFUTED in result.evidence_summary
    assert result.details["declared_monotone"] is True
    assert result.details["reasons_whose_deletion_raised_the_engines_answer"] >= 1


def test_the_absence_of_the_fingerprint_is_not_evidence_of_monotonicity():
    """The declaration cannot be confirmed by the measurement, only refuted by it.

    Both systems here are the same defeasible engine. The probe finds the fingerprint on one and
    nothing at all on the other, purely because of where the exception sits — so a rung that trusted
    the measurement alone would clear the ordinary exception every time.
    """
    hidden = certify(**_defeasible_case(exception_in_a_rule_body=False), monotone=True)
    caught = certify(**_defeasible_case(exception_in_a_rule_body=True), monotone=True)

    assert hidden.non_monotone == []
    assert caught.non_monotone != []
    # And the reason the engine lawfully withdrew is counted `deleted` in both, exactly as a
    # dropped one is: the measurement is right about the question it asked.
    assert hidden.missing_reasons() == ["R01 — the reason the exception withdrew"]


# ------------------------------------------------- what a monotone system still gets ----


def test_a_declared_monotone_system_reaches_the_verdict_it_always_did():
    """The demonstration's own decision, whose engine truncates proofs and retracts nothing."""
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    result = next(r for r in report.results if r.requirement_id == ADEQUACY)

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROBED


@pytest.mark.parametrize("engine", [ExactWMC(), TopK(1)])
def test_a_declared_monotone_certificate_still_reports_pass_or_fail(engine):
    """A declaration that holds changes nothing about what the certificate reports."""
    case = demo.build_case("APP-1042", "typical", demo.CREDIT_QUERY, demo.CREDIT_REASONS, 0.88)
    declared = certify(case.program, case.base, case.query, ReferenceAdapter(engine),
                       exact_depth=1, labels=case.labels, monotone=True)
    bare = certify(case.program, case.base, case.query, ReferenceAdapter(engine),
                   exact_depth=1, labels=case.labels)

    assert declared.verdict == bare.verdict
    assert declared.verdict in ("PASS", "FAIL")


def test_a_certificate_over_a_non_monotone_artefact_carries_no_verdict():
    """The refusal is on the instrument too, not only in the engine that reads it."""
    cert = certify(**_defeasible_case(exception_in_a_rule_body=False), monotone=False)

    assert cert.verdict == "INCONCLUSIVE"
    assert cert.deletion_semantics_refusal == artifacts.DECLARED_NON_MONOTONE
    assert "NO VERDICT IS READ OFF THIS MEASUREMENT" in cert.render()
    assert cert.to_dict()["monotone"] is False


# ------------------------------------------------------- the protocol is a protocol ----


class _RuleTraceArtifact:
    """A second family, standing for none of them: reasons read off a table, no ground program.

    It exists to hold the protocol honest, and it declares `reasons_are_exact` nowhere on purpose:
    a family that does not say claims the *weaker* rung, which is the one line of defence against a
    family that lists something reason-shaped being handed the rung exact enumeration earned.
    """

    monotone = True
    query = "loan-1"
    engine_name = "table:reference"
    claimed_semantics = "weighted sum"
    exact_inference = "enumeration of a fixed reason table"
    exact_depth = None

    #: reason -> weight. The engine's answer is the sum of the reasons it keeps.
    TABLE = {frozenset({"a", "b"}): 0.5, frozenset({"c"}): 0.25}

    def __init__(self, off: frozenset = frozenset(), keeps: frozenset | None = None):
        self._off = off
        self._keeps = frozenset(self.TABLE) if keeps is None else keeps

    def reasons(self):
        return tuple(self.TABLE)

    def label(self, reason):
        return default_label(reason)

    def score(self, reason):
        return self.TABLE[reason]

    def _value(self, over):
        return sum(w for r, w in self.TABLE.items() if r in over and not (r & self._off))

    def exact_value(self):
        return self._value(set(self.TABLE))

    def engine_value(self):
        return self._value(self._keeps)

    def without(self, fact):
        return _RuleTraceArtifact(self._off | {fact}, self._keeps)


def test_the_protocol_is_satisfiable_without_a_ground_program():
    """A family with no program, no atoms and no oracle is certified by the same core."""
    dropped = frozenset({"c"})
    cert = certify_artifact(_RuleTraceArtifact(keeps=frozenset({frozenset({"a", "b"})})))

    assert isinstance(_RuleTraceArtifact(), InferenceArtifact)
    assert cert.verdict == "FAIL"
    assert cert.missing_reasons() == [default_label(dropped)]
    assert cert.exact_inference == "enumeration of a fixed reason table"


def test_the_ground_program_family_is_one_adapter_and_the_protocol_names_no_representation():
    """reasonsmith owns the abstraction; nesyarena is one implementation of it, on this side."""
    case = demo.build_case("APP-1042", "typical", demo.CREDIT_QUERY, demo.CREDIT_REASONS, 0.88)
    artifact = GroundProgramArtifact(
        case.program, case.base, case.query, ReferenceAdapter(ExactWMC()), 1,
        case.labels, monotone=True)

    assert isinstance(artifact, InferenceArtifact)
    assert certify_artifact(artifact).verdict == "PASS"
    # The protocol module and the certificate that reads it import no representation at all: the
    # coupling is one adapter module, which is what makes a second family an adapter and not a
    # branch in the core. Asserted on the imports rather than on the prose, which names nesyarena
    # freely and should.
    for module in (artifacts, certificate):
        imported: set[str] = set()
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        assert not any(name.startswith("nesyarena") for name in imported), module.__name__


# ------------------------------------------- the rung a recounted reason set reaches ----


class _RecountingCreditSystem:
    """A system that recounts its reasons instead of exposing an inference to enumerate.

    Its decision turns on two facts and it says so. `unfaithful` adds a third reason to what it
    recounts and to nothing else — the rationale item the answer does not depend on, which is the
    failure mode the faithfulness literature names and the one this family can measure.
    """

    system_domains = ("consumer-credit",)

    def __init__(self, *, unfaithful: bool = False, monotone: bool | None = True):
        self._unfaithful, self._monotone = unfaithful, monotone

    def capabilities(self) -> set[str]:
        return {"decision_id", "artifact_logs_reason_explanation", DELETED_REASON_COUNT}

    def decisions(self) -> list[dict[str, Any]]:
        return [{
            "decision_id": "LM-1",
            "artifact_logs_reason_explanation": "R01 — income; R02 — recent delinquency",
        }]

    @staticmethod
    def _answer(suppressed: frozenset) -> float:
        """The system re-run: only `income` and `delinquency` move it, whatever it recounted."""
        return sum(0.5 for f in ("income", "delinquency") if f not in suppressed)

    def logic(self) -> Any:
        return None

    def artifact(self, decision: dict[str, Any]):
        recounted = {
            "R01 — income": frozenset({"income"}),
            "R02 — recent delinquency": frozenset({"delinquency"}),
        }
        if self._unfaithful:
            recounted["R03 — thin file"] = frozenset({"file_thickness"})
        return ReasonTraceArtifact(
            decision["decision_id"],
            recounted,
            self._answer,
            engine_name="stub-decoder",
            claimed_semantics="free-text rationale",
            monotone=self._monotone,
        )


def test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one():
    """The rung, doing the job it was added for.

    The same duty, the same probe, the same verdict — and a rung lower, because the reason set was
    recounted by the system rather than enumerated from a model encoding. That difference was
    previously inexpressible, which is why the second artefact family was gated on it
    (`docs/semantics.md` §3).
    """
    result = evaluate_requirement(_duty(), _RecountingCreditSystem())

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.RECOUNTED
    assert result.strength < Strength.PROBED
    assert result.details[EXACT_REASON_SET_KEY] is False
    assert artifacts.RECOUNTED_REASONS in result.evidence_summary
    # And the enumerating family still reaches the rung above, on the same duty.
    enumerated = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    assert next(
        r for r in enumerated.results if r.requirement_id == ADEQUACY
    ).strength == Strength.PROBED


def test_a_recounted_reason_the_answer_does_not_depend_on_is_still_a_breach():
    """The rung is lower; it is not weaker about what it did measure.

    A rationale item no deletion moves is measured exactly as a dropped reason is, and reported
    `violated` — at `recounted`, which is the whole of the difference.
    """
    result = evaluate_requirement(_duty(), _RecountingCreditSystem(unfaithful=True))

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.RECOUNTED
    assert "R03 — thin file" in result.evidence_summary


def test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung():
    """The refusal, on the model of the ones `__post_init__` already carries.

    Expressing the difference is half the work; a result model that lets an engine claim the rung
    above anyway would leave the other half as a comment.
    """
    with pytest.raises(ValueError, match="recounted cannot be reported probed"):
        RequirementResult(
            requirement_id=ADEQUACY,
            source_clause="12 CFR 1002.9(b)(2)",
            verdict=Verdict.SATISFIED,
            strength=Strength.PROBED,
            signals_required=(DELETED_REASON_COUNT,),
            evidence_summary="every recounted reason is one the answer depends on",
            details={
                EXACT_REASON_SET_KEY: False,
                PROBE_BUDGET_KEY: {
                    "trials": 3, "strategy": "deletion probe", "seed": "none",
                    "input_space": {"decisions certified": 1},
                },
            },
        )


def test_a_family_that_does_not_say_claims_the_weaker_rung():
    """Silence about exactness concedes, where silence about monotonicity refuses.

    The two defaults go opposite ways on purpose: guessing monotone accuses a compliant system,
    while guessing recounted only understates one — the direction this package may fail in.
    """
    assert artifacts.reason_set_is_exact(_RuleTraceArtifact()) is False
    assert artifacts.reason_set_is_exact(GroundProgramArtifact) is True
    assert isinstance(
        _RecountingCreditSystem().artifact({"decision_id": "LM-1"}), InferenceArtifact
    )


def test_a_recounted_verdict_is_never_rendered_as_a_probed_one():
    """§10's presentation rule: a weaker rung must not read as the rung above, in any surface."""
    report = check_conformance(_RecountingCreditSystem(), load_pack("ecoa"))

    text = report.render_text()
    assert "[RECOUNTED] " + ADEQUACY in text
    assert "recounted measures one the system recounted" in text
    card = report.render_html().split(ADEQUACY, 1)[1].split("</article>", 1)[0]
    assert "RECOUNTED — What Was Searched" in card
    assert "PROBED — What Was Searched" not in card


def test_switching_a_fact_off_does_not_re_enumerate_the_reasons():
    """`without` perturbs the interpretation and never the question exact inference was asked."""
    case = demo.build_case("APP-1042", "typical", demo.CREDIT_QUERY, demo.CREDIT_REASONS, 0.88)
    artifact = GroundProgramArtifact(
        case.program, case.base, case.query, ReferenceAdapter(ExactWMC()), 1,
        case.labels, monotone=True)
    fact = next(iter(next(iter(artifact.reasons()))))

    assert artifact.without(fact).reasons() == artifact.reasons()
    assert artifact.without(fact).base[fact] == 0.0
    assert artifact.base[fact] != 0.0     # the parent is untouched
