"""Tests for the either/or content duty of 12 CFR 1002.9(a)(2).

What this module is for:
  `ecoa_reg_b_1002_9_a_2_written_statement` used to demand a statement of specific reasons
  unconditionally, so a creditor that lawfully took point (ii) of the clause — a disclosure of the
  applicant's right to request the reasons — was reported `violated` on a binding duty. That is a
  false violation, the worst error this tool can produce. These tests hold the repaired property to
  the clause: either lawful branch satisfies it, and neither branch alone gates it.

What a reader must not break:
  - The requirement is loaded from the shipped pack, never re-written here. A test that authored
    its own spec would pass while the pack said something else.
  - Both branches are exercised through `evaluate_requirement`, the path a user's run takes, not
    through an engine chosen by the test. Which engine answers a duty is a fact about the system
    (`report._engine_ladder`), and pinning one here would hide a change in that ladder.
  - The neither-branch case must stay `violated`. Reporting it satisfied would make the disjunction
    vacuous, and reporting it unattainable would put a creditor that recorded neither content
    beyond the reach of the check.
"""

from __future__ import annotations

from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

CONTENT_DUTY = "ecoa_reg_b_1002_9_a_2_written_statement"
SPECIFICITY_DUTY = "ecoa_reg_b_1002_9_b_2_specific_reasons"

REASONS = "artifact_logs_reason_explanation"
DISCLOSURE = "artifact_logs_right_to_reasons_disclosure"

#: Both branch signals plus the two the clause demands whatever branch a creditor takes. A system
#: capable of either branch declares all four; which one it used shows in the records, not here.
EVERY_SIGNAL = frozenset(
    {REASONS, DISCLOSURE, "artifact_logs_decision_record", "provenance_model_version"}
)


def requirement(req_id: str = CONTENT_DUTY):
    return load_pack("ecoa").get_requirement(req_id)


def notification(**branch_content) -> dict:
    """One adverse-action record carrying the contents every branch shares, plus what is given.

    The observed engine needs at least two records to read a sampling period off the trace, so
    every test below supplies two.
    """
    record = {
        "artifact_logs_decision_record": "application 4471, adverse action",
        "provenance_model_version": "creditscore-2.3.1",
    }
    record.update(branch_content)
    return record


def test_neither_branch_signal_gates_the_content_duty():
    """The gate is a conjunction, so a branch of an either/or may not be listed in it.

    This is the defect in its static form: with both branches required, a creditor supplying only
    one is reported unattainable without being run; with one required, the creditor that took the
    other is. Only what the clause demands of every branch belongs here.
    """
    req = requirement()
    assert req.formalism == "temporal"
    assert set(req.requires) == {"artifact_logs_decision_record", "provenance_model_version"}
    assert REASONS not in req.requires
    assert DISCLOSURE not in req.requires
    assert f"present({REASONS}) or present({DISCLOSURE})" in req.spec


def test_a_creditor_giving_the_specific_reasons_is_satisfied():
    """Point (i): the statement of specific reasons itself."""
    sut = BaseSUT(set(EVERY_SIGNAL))
    records = [
        notification(**{REASONS: "insufficient recent repayment history"}),
        notification(**{REASONS: "outstanding balance above the product limit"}),
    ]
    result = evaluate_requirement(requirement(), sut, records)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_creditor_disclosing_the_right_to_request_reasons_is_satisfied():
    """Point (ii): the lawful alternative, which this duty used to report as a violation."""
    sut = BaseSUT(set(EVERY_SIGNAL))
    disclosure = (
        "You may request a statement of specific reasons within 60 days. Adverse Action Desk, "
        "PO Box 118, (555) 0100."
    )
    records = [
        notification(**{DISCLOSURE: disclosure}),
        notification(**{DISCLOSURE: disclosure}),
    ]
    result = evaluate_requirement(requirement(), sut, records)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_creditor_giving_neither_branch_is_violated():
    """An either/or is not satisfied by neither. The disjunction must still be able to fail."""
    sut = BaseSUT(set(EVERY_SIGNAL))
    records = [notification(), notification()]
    result = evaluate_requirement(requirement(), sut, records)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED


def test_one_notification_missing_both_branches_violates_the_whole_trace():
    """The duty is per notification, so a single record carrying neither content breaks it."""
    sut = BaseSUT(set(EVERY_SIGNAL))
    records = [
        notification(**{REASONS: "insufficient recent repayment history"}),
        notification(),
        notification(**{DISCLOSURE: "You may request a statement of specific reasons."}),
    ]
    result = evaluate_requirement(requirement(), sut, records)
    assert result.verdict == Verdict.VIOLATED
    assert result.details["violation_step_indices"] == [1]


def test_a_missing_shared_content_signal_is_unattainable_not_violated():
    """What the clause demands of every branch still gates: silence there is not a breach."""
    sut = BaseSUT(set(EVERY_SIGNAL) - {"provenance_model_version"})
    result = evaluate_requirement(requirement(), sut, [notification(), notification()])
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert result.signals_missing == ("provenance_model_version",)


def test_the_content_duty_and_the_specificity_duty_can_come_apart():
    """(a)(2) is about the contents of the notification, (b)(2) about the reasons' specificity.

    A creditor capable of stating reasons that instead disclosed the right to request them
    discharges the content duty and leaves the specificity duty with nothing to bite on. Before the
    either/or was formalised the two properties differed by one signal and could not separate.

    What changed, and why: this used to assert the specificity duty came back `violated` here, which
    was the residual false violation left over after the either/or repair. 12 CFR 1002.9(b)(2)
    governs, by its own words, "the statement of reasons required by paragraph (a)(2)(i)" — so a
    creditor that lawfully took the (a)(2)(ii) disclosure branch has no such statement yet and the
    clause does not reach them. The trigger is now in the property as an implication, and both
    duties come back satisfied on the same lawful notification.

    What `satisfied` does and does not mean here is stated in `docs/semantics.md` §4 and pinned by
    `test_a_duty_whose_trigger_never_fires_is_satisfied_vacuously_and_the_report_cannot_say_so`:
    the duty imposed nothing on these records, which is not the same as having been checked and
    found clean, and the four report outcomes cannot tell a reader which of the two it was.
    """
    sut = BaseSUT(set(EVERY_SIGNAL) | {"scope_statements_local_vs_global"})
    disclosure = "You may request a statement of specific reasons within 60 days."
    records = [
        notification(**{DISCLOSURE: disclosure, "scope_statements_local_vs_global": "local"}),
        notification(**{DISCLOSURE: disclosure, "scope_statements_local_vs_global": "local"}),
    ]
    content = evaluate_requirement(requirement(), sut, records)
    specificity = evaluate_requirement(requirement(SPECIFICITY_DUTY), sut, records)
    assert content.verdict == Verdict.SATISFIED
    assert specificity.verdict == Verdict.SATISFIED
    assert specificity.strength == Strength.OBSERVED


def test_a_single_decision_trace_is_not_evaluated_never_satisfied():
    """What holding the either/or costs: a log of one decision no longer answers this duty.

    A disjunction is not a conjunction of `present()` atoms, so the property is quantified over the
    trace, and a discrete-time monitor cannot read a sampling period off one sample. The duty was a
    `record` duty before the clause's `either` was formalised, and one record was enough then.
    Reporting such a log satisfied would be the overclaim: nothing was monitored.
    """
    sut = BaseSUT(set(EVERY_SIGNAL))
    records = [notification(**{REASONS: "insufficient recent repayment history"})]
    result = evaluate_requirement(requirement(), sut, records)
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "Not evaluated" in result.evidence_summary


def test_the_quotation_carries_both_branches_of_the_clause():
    """A quotation showing only point (i) is what made the either/or invisible to a reader."""
    verbatim = requirement().verbatim_text
    assert "(i) A statement of specific reasons for the action taken; or" in verbatim
    assert "(ii) A disclosure of the applicant's right to a statement of specific reasons" in (
        verbatim
    )
