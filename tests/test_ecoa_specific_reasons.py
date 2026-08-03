"""Tests for the specificity duty of 12 CFR 1002.9(b)(2), against a plain decision log.

What this module is for:
  `ecoa_reg_b_1002_9_b_2_specific_reasons` used to be a conjunction of `present()` atoms, so the
  strongest claim it could make was that the reason field was non-blank. A reason string of `"n/a"`
  satisfied it, and the clause it quotes obliges reasons that are *specific* and indicate the
  *principal* reasons. The clause supplies its own negative constraint — it names two statements
  that are insufficient — and that is what the property now checks.

  Every test here runs against a `JSONLAdapter` over a temporary log file: no exposed logic, no
  replay hook, no oracle. That is the point. A duty that can only be falsified by a system that
  hands over its decision procedure is not a duty a bank's log can fail.

What a reader must not break:
  - The requirement is loaded from the shipped pack, never authored here. A test that wrote its own
    spec would pass while the pack said something else.
  - The forbidden wordings are the clause's own. If a test starts asserting on a phrase that is not
    in `verbatim_text`, the property has stopped being derived from the regulation.
  - `test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung` pins a feature, and one
    that used to be the limit this module recorded: a trace where the antecedent held nowhere was
    reported `satisfied` at `observed` while the solver reported the same formula `proved`. Both
    rungs now refuse it. Do not restore the old assertion — see `docs/semantics.md` §4, and
    `rulelang.implication_antecedent` for where the rule is written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

DUTY = "ecoa_reg_b_1002_9_b_2_specific_reasons"

REASONS = "artifact_logs_reason_explanation"
DISCLOSURE = "artifact_logs_right_to_reasons_disclosure"
VERSION = "provenance_model_version"
SCOPE = "scope_statements_local_vs_global"

#: A creditor able to take either branch of (a)(2) declares both branch signals. Which one it used
#: shows in the records, not here.
DECLARED = (REASONS, DISCLOSURE, VERSION, SCOPE)


def requirement():
    return load_pack("ecoa").get_requirement(DUTY)


def _notification(**overrides) -> dict:
    record = {VERSION: "underwriting-2026.05.0", SCOPE: "local"}
    record.update(overrides)
    return record


def _log(tmp_path: Path, records: list[dict]) -> JSONLAdapter:
    """A plain decision log on disk, read by the adapter a reader would use for a black box.

    It declares `consumer-credit`, which is what puts it inside these duties at all: 12 CFR 1002.9
    is limited to that decision domain, and a system declaring none is reported not applicable
    rather than judged (`tests/test_domain_gate.py`). Every case here is about *what a creditor's
    notification said*, so each has to be a creditor first.
    """
    path = tmp_path / "decisions.jsonl"
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    adapter = JSONLAdapter(path, declared_capabilities=DECLARED)
    adapter.system_domains = ("consumer-credit",)
    return adapter


def _check(tmp_path: Path, records: list[dict]):
    return evaluate_requirement(requirement(), _log(tmp_path, records))


# --------------------------------------------------------------------------------------------
# The three the clause itself decides
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "Applicant failed to achieve a qualifying score on our credit scoring system.",
        "You failed to achieve a qualifying score.",
        # The fold is ASCII case, so the sentence-cased wording a real notice would carry is caught.
        "Failed to achieve a qualifying score",
    ],
)
def test_a_statement_the_clause_calls_insufficient_is_violated_on_a_bare_log(
    tmp_path, statement
):
    """The claim WP6 exists to make: a plain log can now *fail* a reason-quality duty.

    No oracle establishes this. The clause names the statement, the log carries it, and the verdict
    is `observed` — a claim about the decisions supplied and nothing beyond them.
    """
    result = _check(
        tmp_path,
        [
            _notification(**{REASONS: "Length of credit history"}),
            _notification(**{REASONS: statement}),
        ],
    )

    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED
    assert result.details["violation_step_indices"] == [1]


def test_a_statement_resting_on_internal_standards_or_policies_is_violated(tmp_path):
    """The clause's other named insufficiency, and both of its nouns."""
    for statement in (
        "Declined under the creditor's internal standards.",
        "This decision was based on our internal policies.",
    ):
        result = _check(
            tmp_path,
            [_notification(**{REASONS: statement}), _notification(**{REASONS: statement})],
        )
        assert result.verdict == Verdict.VIOLATED, statement
        assert result.strength == Strength.OBSERVED, statement


def test_a_statement_naming_a_principal_factor_is_satisfied(tmp_path):
    """A specific factor passes, so the duty is not a blanket accusation.

    A property that failed every log would be as useless as one that passed every log; both stop a
    reader learning anything from a verdict.
    """
    result = _check(
        tmp_path,
        [
            _notification(**{REASONS: "C04 delinquent past or present credit obligations"}),
            _notification(**{REASONS: "C02 excessive obligations in relation to income"}),
        ],
    )

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_creditor_who_took_the_disclosure_branch_is_not_violated(tmp_path):
    """The residual false violation, removed — and what removing it does *not* buy.

    12 CFR 1002.9(b)(2) governs "the statement of reasons required by paragraph (a)(2)(i)". A
    creditor that lawfully disclosed the right to request reasons under (a)(2)(ii) has no such
    statement yet, so the clause does not reach that notification. Reporting them `violated` on a
    binding duty was the worst error this tool can make, and the README's Impact section said so in
    public. That is the assertion this test exists for and it is unchanged.

    What changed is the second half. This creditor used to be reported `satisfied` at `observed`,
    which was the duty's antecedent being false rather than its consequent being met — nothing about
    the wording of any statement was examined, because there was no statement. The trigger guard
    reports that *not evaluated* and names the antecedent that never fired. It is a weaker report of
    the same creditor and a truer one, and `docs/semantics.md` §4 states the cost: a lawful
    disclosure-branch creditor no longer gets a clean line on this duty, and the honest answer
    (`not applicable`, per record) is one the result model still cannot express.
    """
    disclosure = "Write to Credit Review, 1 Example Street, within 60 days of this notice."
    result = _check(
        tmp_path,
        [
            _notification(**{DISCLOSURE: disclosure}),
            _notification(**{DISCLOSURE: disclosure}),
        ],
    )

    assert result.verdict != Verdict.VIOLATED
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert f"present({REASONS})" in result.evidence_summary


def test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung():
    """The limit this module used to record, closed. See `docs/semantics.md` §4.

    Two traces, two situations, and they must not share a verdict. In the first the duty imposed a
    requirement and the records met it: `satisfied` at `observed`, which is what the monitor
    established. In the second the antecedent held at no position, so the duty imposed nothing and
    nothing about the wording of any statement was examined — and this used to be reported
    `satisfied` at `observed` too, with no field of the result telling the two apart. It is now
    *not evaluated*, and the summary names the antecedent that never fired and the trace it was
    looked for in, which are the two things a reader needs to see that the duty was not answered.

    `not_applicable` is still the honest answer for the second and is still out of reach:
    applicability in reasonsmith is a per-*requirement*, per-*system* question decided from the
    declared class and domain before any engine runs, and there is no per-record equivalent. What
    changed is that the un-answerable case is no longer reported as an answer.
    """
    from reasonsmith.sut import BaseSUT

    sut = BaseSUT(set(DECLARED))
    sut.system_domains = ("consumer-credit",)
    checked = [
        _notification(**{REASONS: "C03 length of credit history"}),
        _notification(**{REASONS: "C03 length of credit history"}),
    ]
    never_triggered = [
        _notification(**{DISCLOSURE: "Request reasons within 60 days."}),
        _notification(**{DISCLOSURE: "Request reasons within 60 days."}),
    ]

    a = evaluate_requirement(requirement(), sut, checked)
    b = evaluate_requirement(requirement(), sut, never_triggered)

    assert (a.verdict, a.strength) == (Verdict.SATISFIED, Strength.OBSERVED)
    assert (b.verdict, b.strength) == (Verdict.INCONCLUSIVE, None)
    assert b.details["vacuous_trigger"] == {
        "antecedent": f"present({REASONS})",
        "domain": f"the {len(never_triggered)} decision(s) of this trace",
    }


# --------------------------------------------------------------------------------------------
# What the property does not capture, pinned where it can rot
# --------------------------------------------------------------------------------------------


def test_the_property_does_not_decide_whether_any_other_statement_is_specific(tmp_path):
    """`contains()` is a substring test, and the duty claims exactly that much.

    "n/a" is not a specific principal reason and the clause would not accept it, but the clause
    names two insufficient statements and this is neither of them. Inventing a definition of
    "specific" to catch it is precisely what the brief for this work forbade, so the limit is
    asserted here and stated in `docs/refinement.md`'s fourth column rather than papered over.
    """
    result = _check(
        tmp_path,
        [_notification(**{REASONS: "n/a"}), _notification(**{REASONS: "n/a"})],
    )

    assert result.verdict == Verdict.SATISFIED


def test_the_forbidden_wordings_are_the_clauses_own(tmp_path):
    """No phrase in the property may be one this pack invented — including the one that is derived.

    Two of the three are contiguous quotations. The third is not, and saying so is the point of this
    test: the clause writes *"the creditor's internal standards or policies"*, one adjective over
    two coordinated nouns, so a property matching text has to distribute it into the two readings
    the clause states in one breath. That is reading the coordination, not inventing a wording — but
    it is a step away from the print, so it is asserted here word by word and named in the
    requirement's own `rationale` rather than left for a reader to notice.
    """
    req = requirement()

    for quoted in ("internal standards", "failed to achieve a qualifying score"):
        assert quoted in req.spec
        assert quoted in req.verbatim_text

    coordination = "the creditor's internal standards or policies"
    assert coordination in req.verbatim_text
    assert "internal policies" in req.spec
    assert all(word in coordination.split() for word in "internal policies".split())
    assert "internal standards or policies" in req.rationale


def test_a_single_decision_log_is_not_evaluated_never_satisfied(tmp_path):
    """What leaving the record fragment costs this duty, stated rather than hidden.

    The trigger is an implication, so the property is no longer a conjunction of `present()` atoms
    and the record engine — which walks exactly that shape to name a missing signal — cannot answer
    it. The monitor that can needs two samples to establish a sampling period, so a log holding one
    decision is reported not evaluated and leaves the binding headline counts. This duty answered a
    one-record log before the trigger was formalised.
    """
    result = _check(tmp_path, [_notification(**{REASONS: "C03 length of credit history"})])

    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "Not evaluated" in result.evidence_summary
