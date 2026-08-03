"""Tests for the unreachable-trigger guard: a duty whose antecedent never fires.

What this module is for:
  An implication holds wherever its antecedent is false. A duty written as one, put to a system
  nothing in whose evidence domain reaches the trigger, therefore comes back clean for every
  system alike — and used to come back clean at `proved`, the strongest rung this tool issues, on
  a shipped binding duty. This module holds every rung to the contract that replaced it:

      Where a requirement's property is an implication and the engine's evidence domain contains
      no element satisfying its antecedent, the result is *not evaluated*, `strength=None`, naming
      the antecedent that never fired and the size of the domain that was searched.

What a reader must not break:
  - The rule is written **once**: `rulelang.implication_antecedent` names the subtree and
    `report.not_evaluated_for_unreachable_trigger` words the refusal. A rung that grows its own
    copy of either will drift from the others, which is the state this guard replaced — the solver
    reporting `proved` on the same formula the monitor reported `observed` and the record engine
    reported violated.
  - **An earned verdict must survive.** A guard that also refuses proofs whose antecedent does
    fire is not a fix, and the two tests below that assert `satisfied @ proved` and
    `violated @ proved` are the ones that would catch that.
  - **A property with no implication in it is untouched.** The guard asks the property language a
    question; a property that is not an implication answers `None` and no rung changes behaviour.
"""

from __future__ import annotations

import ast

import pytest

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.engines.probed import ProbedEngine
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.engines.temporal import TemporalProofEngine
from reasonsmith.report import VACUOUS_TRIGGER_KEY, evaluate_requirement
from reasonsmith.rulelang import implication_antecedent, parse_property
from reasonsmith.spec import Requirement
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

TRIGGER = "income >= 30000"
DUTY = f"{TRIGGER} -> approved"
ALWAYS_DUTY = f"always({DUTY})"

VARIABLES = {
    "income": "int",
    "approved": "bool",
    "artifact_logs_reason_explanation": "str",
    "provenance_model_version": "str",
}
CAPABILITIES = {"decision", *VARIABLES}


def _req(spec: str = DUTY, formalism: str = "logical", requires=("income", "approved")):
    return Requirement(
        id="vacuity_r1",
        source_document="Internal Policy",
        article_clause="Section 1.1",
        verbatim_text="A high-income application shall be approved.",
        stakeholder="Compliance",
        formalism=formalism,
        spec=spec,
        rationale="Why this duty exists, in English.",
        requires=requires,
        binding=True,
        scope="",
        domains=(),
    )


def _rules_system(constraints: list[str], approval_rule: str = "approved = False") -> RulesAdapter:
    """A rule set whose declared input space is exactly `constraints`.

    Only the constraints move between the systems below, which is what makes the pair a control:
    the rules are the same rules and the behaviour is the same behaviour, so a verdict that moves
    when the declared space narrows is a verdict about the declaration and not about the system.
    """
    return RulesAdapter(
        rules=[
            approval_rule,
            'artifact_logs_reason_explanation = "C01 income insufficient for amount requested"',
            'provenance_model_version = "vacuity-2026.08.0"',
        ],
        variables=dict(VARIABLES),
        constraints=constraints,
        declared_capabilities=set(CAPABILITIES),
        test_inputs=[{"income": 100}, {"income": 900}],
    )


#: The system whose declared constraints put the trigger outside the input space it admits.
def _narrow() -> RulesAdapter:
    return _rules_system(["income >= 0", "income <= 1000"])


#: The same rules over an input space that does reach the trigger.
def _wide() -> RulesAdapter:
    return _rules_system(["income >= 0", "income <= 100000"])


# --------------------------------------------------------------------------------------------
# The property language: where the antecedent is, and where there is not one
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "antecedent"),
    [
        (DUTY, TRIGGER),
        ("income >= 30000 => approved", TRIGGER),
        ("Implies(income >= 30000, approved)", TRIGGER),
        (ALWAYS_DUTY, TRIGGER),
        ("present(artifact_logs_reason_explanation) -> present(provenance_model_version)",
         "present(artifact_logs_reason_explanation)"),
    ],
)
def test_the_language_names_the_antecedent_whatever_the_arrow_was_written_as(spec, antecedent):
    """One subtree, one name for it, whichever surface syntax the pack author used.

    Every engine parses the same `spec` through the same language, so the antecedent has to be the
    same node in all of them — that is the whole reason this lives in `rulelang` and not four
    times in four engines.
    """
    node = implication_antecedent(parse_property(spec))
    assert node is not None and ast.unparse(node) == antecedent


@pytest.mark.parametrize(
    "spec",
    [
        "present(artifact_logs_reason_explanation)",
        "present(artifact_logs_reason_explanation) and present(provenance_model_version)",
        "income >= 30000 or approved",
        "eventually(income >= 30000 -> approved)",
        "always(income >= 30000) and approved",
    ],
)
def test_a_property_that_is_not_one_implication_has_no_antecedent_to_be_unreachable(spec):
    """`None` for every other shape, and two of these are deliberate limits, not oversights.

    `eventually(f)` is not stripped: its vacuity is a claim about a position that never existed
    rather than about a trigger that never fired, and the two would need different sentences. A
    conjunction of implications has several antecedents and a per-conjunct vacuity. Both are
    stated in `docs/semantics.md` §4 rather than guessed at.
    """
    assert implication_antecedent(parse_property(spec)) is None


# --------------------------------------------------------------------------------------------
# The proof rung
# --------------------------------------------------------------------------------------------


def test_an_antecedent_no_admissible_input_reaches_is_not_evaluated_at_proved():
    """The defect, at the strongest rung this tool issues.

    A system that approves nobody, whose declared constraints put every income below the duty's
    threshold. `unsat` on the negation was read as a proof; it was the trigger being unreachable.
    """
    result = ProvedEngine.evaluate(_req(), _narrow(), [])

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert result.details[VACUOUS_TRIGGER_KEY] == {
        "antecedent": TRIGGER,
        "domain": "the inputs the system's declared logic and constraints admit",
    }
    assert TRIGGER in result.evidence_summary


def test_widening_the_declared_input_space_alone_turns_the_refusal_into_a_violation():
    """The control that proves the refusal was about the trigger and not about the rules.

    One constraint changes. Same rules, same refusal to approve anyone, same behaviour — and the
    duty goes from not evaluated to violated at `proved`, because now there is an admissible input
    that reaches the trigger and the system fails it there.
    """
    narrow = ProvedEngine.evaluate(_req(), _narrow(), [])
    wide = ProvedEngine.evaluate(_req(), _wide(), [])

    assert (narrow.verdict, narrow.strength) == (Verdict.INCONCLUSIVE, None)
    assert (wide.verdict, wide.strength) == (Verdict.VIOLATED, Strength.PROVED)


def test_a_satisfaction_whose_antecedent_does_fire_still_reaches_proved():
    """The guard must not cost an earned proof.

    This system approves everyone the duty asks it to, over an input space that reaches the
    trigger. That is the verdict `proved` is for, and it is unchanged.
    """
    system = _rules_system(["income >= 0", "income <= 100000"], "approved = income >= 20000")
    result = ProvedEngine.evaluate(_req(), system, [])

    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.PROVED)
    assert VACUOUS_TRIGGER_KEY not in result.details


def test_a_property_with_no_implication_is_untouched_at_proved():
    """A duty that is not an implication has no trigger to be unreachable, and nothing changes."""
    req = _req(
        spec="present(artifact_logs_reason_explanation)",
        formalism="record",
        requires=("artifact_logs_reason_explanation",),
    )
    result = ProvedEngine.evaluate(req, _narrow(), [])

    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.PROVED)
    assert VACUOUS_TRIGGER_KEY not in result.details


def test_the_temporal_reduction_inherits_the_refusal():
    """`always(f)` is decided by deciding `f`, so it inherits the guard rather than repeating it.

    The reduction hands `ProvedEngine` the state property under the `always`; a trigger that no
    admissible input reaches is unreachable at every position too, and the temporal rung must not
    be the one place a vacuous proof still gets published.
    """
    result = TemporalProofEngine.evaluate(_req(ALWAYS_DUTY, formalism="temporal"), _narrow(), [])

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert result.details[VACUOUS_TRIGGER_KEY]["antecedent"] == TRIGGER
    # The reduction's own claim about trace semantics is a claim about a verdict, and there is no
    # verdict here to make it about.
    assert "trace_semantics" not in result.details


# --------------------------------------------------------------------------------------------
# The trace rung, and the replay rung the ladder falls to
# --------------------------------------------------------------------------------------------

REASONS = "artifact_logs_reason_explanation"
VERSION = "provenance_model_version"
PRESENCE_DUTY = f"present({REASONS}) -> present({VERSION})"


def _blank(count: int = 2) -> list[dict]:
    return [{VERSION: "log-only-2026.08.0", REASONS: ""} for _ in range(count)]


def _stated(count: int = 2) -> list[dict]:
    return [
        {VERSION: "log-only-2026.08.0", REASONS: "C02 excessive obligations"}
        for _ in range(count)
    ]


def _presence_req(formalism: str = "logical", spec: str = PRESENCE_DUTY) -> Requirement:
    return _req(spec=spec, formalism=formalism, requires=(REASONS, VERSION))


def test_an_antecedent_false_at_every_position_is_not_evaluated_at_observed():
    """The monitor scoring every step non-negative is a fact about the trigger, not the system."""
    records = _blank()
    result = ObservedEngine.evaluate(_presence_req(), BaseSUT({REASONS, VERSION}), records)

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert result.details[VACUOUS_TRIGGER_KEY] == {
        "antecedent": f"present({REASONS})",
        "domain": f"the {len(records)} decision(s) of this trace",
    }


def test_a_trace_that_does_reach_the_antecedent_still_reaches_observed():
    """The earned trace verdict, unchanged: the trigger fires and the consequent holds."""
    result = ObservedEngine.evaluate(_presence_req(), BaseSUT({REASONS, VERSION}), _stated())

    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.OBSERVED)
    assert VACUOUS_TRIGGER_KEY not in result.details


def test_a_temporal_duty_over_the_same_implication_moves_with_it():
    """`always(f)` off a trace: same antecedent, same refusal, and the same sentence."""
    req = _presence_req(formalism="temporal", spec=f"always({PRESENCE_DUTY})")
    result = ObservedEngine.evaluate(req, BaseSUT({REASONS, VERSION}), _blank())

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert result.details[VACUOUS_TRIGGER_KEY]["antecedent"] == f"present({REASONS})"


def test_a_search_that_never_reached_the_antecedent_is_not_evaluated_at_probed():
    """The rung the ladder falls to when the proof rung refuses, held to the same rule.

    Without this, closing the proof rung would have moved the vacuous `satisfied` down one rung
    rather than removing it: the shipped ECOA reproduction is a `RulesAdapter`, which exposes both
    `logic()` and `decide()`.
    """

    class BlankReasons(BaseSUT):
        def decisions(self):
            return list(_blank())

        def decide(self, case):
            record = dict(case)
            record.update({REASONS: "", VERSION: "log-only-2026.08.0"})
            return record

    result = ProbedEngine.evaluate(_presence_req(), BlankReasons({REASONS, VERSION}), None)

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert result.details[VACUOUS_TRIGGER_KEY]["antecedent"] == f"present({REASONS})"
    assert result.details[VACUOUS_TRIGGER_KEY]["domain"].endswith("this search replayed")


def test_a_search_that_did_reach_the_antecedent_still_reaches_probed():
    """The control: the same engine, the same duty, a system that states a reason."""

    class StatedReasons(BaseSUT):
        def decisions(self):
            return list(_stated())

        def decide(self, case):
            record = dict(case)
            record.update(
                {REASONS: "C02 excessive obligations", VERSION: "log-only-2026.08.0"}
            )
            return record

    result = ProbedEngine.evaluate(_presence_req(), StatedReasons({REASONS, VERSION}), None)

    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.PROBED)
    assert VACUOUS_TRIGGER_KEY not in result.details


# --------------------------------------------------------------------------------------------
# What the rungs now agree about
# --------------------------------------------------------------------------------------------


def test_the_solver_and_the_monitor_no_longer_disagree_about_the_same_formula():
    """The sharper form of the defect: one system, one formula, two rungs, opposite readings.

    The solver used to report the implication `proved` while the record engine reported the signal
    absent from every record and the monitor reported the implication `observed` — three engines,
    one formula, and the strongest of them making the emptiest claim. Both rungs now refuse, and a
    reader who runs either is told the same thing about the same evidence.
    """
    system = _narrow()
    proved = ProvedEngine.evaluate(_presence_req(), system, _blank())
    observed = ObservedEngine.evaluate(_presence_req(), system, _blank())

    # `present(reason)` is assigned a non-blank string by the rules, so the solver's domain does
    # reach the trigger and the trace's does not: the two rungs are answering about different
    # domains, and each names the one it searched.
    assert (proved.verdict, proved.strength) == (Verdict.SATISFIED, Strength.PROVED)
    assert (observed.verdict, observed.strength) == (Verdict.INCONCLUSIVE, None)
    assert "this trace" in observed.details[VACUOUS_TRIGGER_KEY]["domain"]


def test_the_ladder_reports_the_refusal_rather_than_falling_to_a_weaker_vacuous_pass():
    """End to end, through `evaluate_requirement`: no rung publishes the vacuous satisfaction."""
    result = evaluate_requirement(_req(), _narrow(), _blank())

    assert (result.verdict, result.strength) == (Verdict.INCONCLUSIVE, None)
    assert VACUOUS_TRIGGER_KEY in result.details
