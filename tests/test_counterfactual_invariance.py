"""Counterfactual invariance under one named protected variable.

The self-composition spike is at the top: it is the measurement that decided the `proved` rung was
affordable at all, and it stays as a test so a change that makes two copies of a rule block
collide, or makes the solver stop returning on one, fails here rather than in a report.
"""

from __future__ import annotations

import ast

import pytest

z3 = pytest.importorskip("z3")

from reasonsmith.engines.proved import (  # noqa: E402
    _as_bool,
    _ast_to_z3,
    _encode_block,
    _Scope,
)
from reasonsmith.examples import symbolic_rules  # noqa: E402
from reasonsmith.rulelang import parse_expression  # noqa: E402

#: A protected variable the shipped example does not have, added here and nowhere else. The
#: shipped systems deliberately do not carry one: a decision record holding a fact about a natural
#: person is a collection cost this repository does not create, and the counterfactual duty needs
#: only that the *decision procedure* accept the variable. See docs/refinement.md.
PROTECTED = "applicant_prohibited_basis"


def _self_compose(rules, variables, constraints, protected):
    """Encode `rules` twice into one solver, every input held equal but `protected`."""
    solver = z3.Solver()
    solver.set("timeout", 5000)
    scopes = []
    for namespace in ("@0", "@1"):
        scope = _Scope(variables, namespace)
        for text in constraints:
            solver.add(_as_bool(_ast_to_z3(parse_expression(text), scope), text))
        for text in rules:
            _encode_block(ast.parse(text, mode="exec").body, scope, solver)
        scope.read(protected)
        scopes.append(scope)
    left, right = scopes
    for name in sorted(set(left.inputs) & set(right.inputs) - {protected}):
        solver.add(left.inputs[name] == right.inputs[name])
    return solver, left, right


def _example_logic(extra_rule: str | None = None):
    variables = {**symbolic_rules.VARIABLES, PROTECTED: "int"}
    constraints = [*symbolic_rules.CONSTRAINTS, f"{PROTECTED} >= 0", f"{PROTECTED} <= 1"]
    rules = list(symbolic_rules.RULES)
    if extra_rule is not None:
        rules[3] = extra_rule
    return rules, variables, constraints


def test_two_copies_of_one_rule_block_do_not_collide():
    """The namespace is what makes a two-copy encoding a property of a *pair* of runs.

    Without it an SSA label is `name#version`, which is identical across two executions of the
    same rules, so the solver would read the second copy's constants as the first copy's and
    decide a property of one run while the duty asks about two.
    """
    rules, variables, constraints = _example_logic()
    _, left, right = _self_compose(rules, variables, constraints, PROTECTED)

    left_labels = {str(const) for const in left.current.values()}
    right_labels = {str(const) for const in right.current.values()}
    assert left_labels, "the encoding declared no constants at all"
    assert left_labels.isdisjoint(right_labels)
    assert all("@0" in label for label in left_labels)
    assert all("@1" in label for label in right_labels)


@pytest.mark.parametrize("outcome", ["artifact_logs_decision_record", "adverse_action"])
def test_a_rule_set_ignoring_the_protected_variable_is_unsat_on_the_negation(outcome):
    rules, variables, constraints = _example_logic()
    solver, left, right = _self_compose(rules, variables, constraints, PROTECTED)
    assert solver.check() == z3.sat, "the two copies admit no input at all"
    solver.add(left.current[outcome] != right.current[outcome])
    assert solver.check() == z3.unsat


@pytest.mark.parametrize("outcome", ["artifact_logs_decision_record", "adverse_action"])
def test_a_rule_set_reading_the_protected_variable_yields_a_witness_pair(outcome):
    rules, variables, constraints = _example_logic(
        f"low_score = credit_score < 640 + 40 * {PROTECTED}"
    )
    solver, left, right = _self_compose(rules, variables, constraints, PROTECTED)
    solver.add(left.current[outcome] != right.current[outcome])
    assert solver.check() == z3.sat
    model = solver.model()
    assert str(model[left.inputs[PROTECTED]]) != str(model[right.inputs[PROTECTED]])


# --------------------------------------------------------------------------------------------
# The duty itself.
# --------------------------------------------------------------------------------------------

from reasonsmith.adapters.rules import RulesAdapter  # noqa: E402
from reasonsmith.engines.counterfactual import (  # noqa: E402
    TREATMENT_LIMIT,
    CounterfactualProofEngine,
    PairedReplayEngine,
)
from reasonsmith.report import evaluate_requirement  # noqa: E402
from reasonsmith.rulelang import UnsupportedConstructError, classify_fragment  # noqa: E402
from reasonsmith.spec import Requirement, load_pack  # noqa: E402
from reasonsmith.verdict import Strength, Verdict  # noqa: E402

OUTCOME = "artifact_logs_decision_record"
SPEC = f"counterfactually_invariant({OUTCOME}, {PROTECTED})"

#: A rule set deciding on a score, which also *accepts* the protected variable. Nothing reads it.
AWARE_RULES = [
    "approved = credit_score >= 640",
    (
        "if approved:\n"
        f'    {OUTCOME} = "credit granted on this application"\n'
        "else:\n"
        f'    {OUTCOME} = "adverse action taken on this application"\n'
    ),
]

AWARE_VARIABLES = {
    "credit_score": "int",
    PROTECTED: "int",
    "approved": "bool",
    OUTCOME: "str",
}

AWARE_CONSTRAINTS = [
    "credit_score >= 300",
    "credit_score <= 850",
    f"{PROTECTED} >= 0",
    f"{PROTECTED} <= 1",
]

AWARE_INPUTS = [
    {"credit_score": 715, PROTECTED: 0},
    {"credit_score": 602, PROTECTED: 1},
]


def _requirement(spec: str = SPEC, requires: tuple[str, ...] = (OUTCOME, PROTECTED)):
    return Requirement(
        id="test_counterfactual",
        source_document="ECOA / Regulation B",
        article_clause="12 CFR 1002.4(a)",
        verbatim_text="A creditor shall not discriminate against an applicant on a "
        "prohibited basis regarding any aspect of a credit transaction.",
        stakeholder="applicant",
        formalism="counterfactual",
        spec=spec,
        rationale="Test requirement.",
        requires=requires,
        binding=True,
        scope="",
        domains=("consumer-credit",),
    )


def _aware_system(rules=None, variables=None, constraints=None):
    return RulesAdapter(
        rules=list(AWARE_RULES if rules is None else rules),
        variables=dict(AWARE_VARIABLES if variables is None else variables),
        constraints=list(AWARE_CONSTRAINTS if constraints is None else constraints),
        declared_capabilities={"decision", OUTCOME},
        test_inputs=[dict(case) for case in AWARE_INPUTS],
    )


def _unaware_system():
    """The same decision procedure, by a system that has no notion of the protected variable."""
    variables = {name: sort for name, sort in AWARE_VARIABLES.items() if name != PROTECTED}
    constraints = [c for c in AWARE_CONSTRAINTS if PROTECTED not in c]
    sut = RulesAdapter(
        rules=list(AWARE_RULES),
        variables=variables,
        constraints=constraints,
        declared_capabilities={"decision", OUTCOME},
        test_inputs=[{"credit_score": case["credit_score"]} for case in AWARE_INPUTS],
    )
    return sut


# --- the language -----------------------------------------------------------------------------


def test_the_atom_classifies_into_its_own_fragment_and_not_into_logical():
    assert classify_fragment(SPEC) == "counterfactual"


def test_the_atom_is_the_whole_spec_or_no_part_of_one():
    for spec in (
        f"{SPEC} and present({OUTCOME})",
        f"not {SPEC}",
        f"always({SPEC})",
        f"Implies(present({PROTECTED}), {SPEC})",
    ):
        with pytest.raises(UnsupportedConstructError):
            classify_fragment(spec)


def test_both_arguments_are_signal_names_and_must_differ():
    for spec in (
        f"counterfactually_invariant({OUTCOME}, {PROTECTED} + 1)",
        f"counterfactually_invariant({OUTCOME})",
        f"counterfactually_invariant({OUTCOME}, {OUTCOME})",
        f'counterfactually_invariant({OUTCOME}, "sex")',
    ):
        with pytest.raises(UnsupportedConstructError):
            classify_fragment(spec)


def test_no_engine_can_evaluate_the_atom_against_a_decision_record():
    """The refusal that makes 'no trace rung' a fact about the code, not a ladder convention."""
    from reasonsmith.rulelang import eval_expression, parse_property

    record = {OUTCOME: "credit granted on this application", PROTECTED: 0}
    with pytest.raises(UnsupportedConstructError, match="cannot be evaluated against a"):
        eval_expression(parse_property(SPEC), record)


def test_the_ladder_for_this_fragment_carries_no_trace_rung():
    from reasonsmith.report import _engine_ladder, _EvaluationResources

    sut = _aware_system()
    rungs = _engine_ladder(_requirement(), sut, None, _EvaluationResources(sut))
    assert [strength for strength, _ in rungs] == [Strength.PROVED, Strength.PROBED]
    assert Strength.OBSERVED not in [strength for strength, _ in rungs]


def test_a_log_only_system_is_never_answered_from_its_trace():
    """No `decide()` and no `logic()`: the honest answer is that nothing established anything."""

    class LogOnly:
        capability_basis = "trace"

        def capabilities(self):
            return {"decision", OUTCOME}

        def decisions(self):
            return [{OUTCOME: "credit granted on this application", PROTECTED: 0}] * 20

    result = evaluate_requirement(
        _requirement(), LogOnly(), system_domains=("consumer-credit",)
    )
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "no trace" in result.evidence_summary or "decision log" in result.evidence_summary


# --- the two cases that must not be confused ---------------------------------------------------


def test_a_system_accepting_the_protected_variable_and_ignoring_it_is_satisfied():
    result = evaluate_requirement(
        _requirement(), _aware_system(), system_domains=("consumer-credit",)
    )
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROVED
    assert TREATMENT_LIMIT in result.evidence_summary


def test_a_system_with_no_notion_of_the_protected_variable_is_unattainable():
    """Unawareness is not a discharge, and this is the whole reason `computes` is consulted."""
    result = evaluate_requirement(
        _requirement(), _unaware_system(), system_domains=("consumer-credit",)
    )
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert result.signals_missing == (PROTECTED,)
    assert "no notion" in result.evidence_summary


def test_the_two_cases_reach_different_verdicts_on_the_same_rules():
    """The rules are byte-identical; only the declaration differs, and the verdicts must differ."""
    aware = evaluate_requirement(
        _requirement(), _aware_system(), system_domains=("consumer-credit",)
    )
    unaware = evaluate_requirement(
        _requirement(), _unaware_system(), system_domains=("consumer-credit",)
    )
    assert aware.strength == Strength.PROVED
    assert unaware.strength == Strength.UNATTAINABLE
    assert aware.verdict != unaware.verdict


def test_a_system_that_never_logs_the_protected_variable_is_still_answered():
    """`requires` gates on what a system can emit; this variable is one it *accepts*.

    A creditor whose procedure takes a prohibited basis and whose audit log deliberately carries it
    for nobody must reach the engines and be answered. Gating on the capability would report that
    system unattainable and tell it to start logging a prohibited basis per decision.
    """
    sut = _aware_system()
    assert PROTECTED not in sut.capabilities()
    result = evaluate_requirement(_requirement(), sut, system_domains=("consumer-credit",))
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROVED
    assert result.signals_missing == ()


# --- the two roads to a proof of nothing --------------------------------------------------------


def test_constraints_pinning_the_protected_variable_are_not_a_proof():
    """`unsat` because no pair exists is not evidence that no pair disagrees."""
    pinned = [
        *(c for c in AWARE_CONSTRAINTS if PROTECTED not in c),
        f"{PROTECTED} >= 0",
        f"{PROTECTED} <= 0",
    ]
    result = CounterfactualProofEngine.evaluate(
        _requirement(), _aware_system(constraints=pinned)
    )
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "no second value" in result.evidence_summary
    assert TREATMENT_LIMIT in result.evidence_summary

    # And the two rungs agree: the replay refuses the same system for the same reason.
    replayed = PairedReplayEngine.evaluate(_requirement(), _aware_system(constraints=pinned))
    assert replayed.strength is None
    assert replayed.details["reason"] == "no_second_admissible_value"


def test_rules_assigning_the_protected_variable_are_not_a_proof():
    """The route the direction declaration cannot close: assigned by the rules, absent from
    `computes`. The encoding overwrites the input the intervention turns, so the negation is
    unsatisfiable because the question never reached the decision."""
    sut = _aware_system(rules=[f"{PROTECTED} = 0", *AWARE_RULES])
    logic = sut.logic()
    logic["computes"] = [name for name in logic["computes"] if name != PROTECTED]
    result = CounterfactualProofEngine.evaluate(_requirement(), sut, logic_data=logic)
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details["reason"] == "protected_variable_assigned_by_the_rules"
    assert TREATMENT_LIMIT in result.evidence_summary


def test_a_system_declaring_no_directions_is_not_evaluated():
    sut = _aware_system()
    logic = sut.logic()
    logic.pop("computes", None)
    result = CounterfactualProofEngine.evaluate(_requirement(), sut, logic_data=logic)
    assert result.strength is None
    assert "which of them it produces" in result.evidence_summary


# --- a system that does discriminate ------------------------------------------------------------

DISCRIMINATING_RULES = [
    f"approved = credit_score >= 640 + 40 * {PROTECTED}",
    (
        "if approved:\n"
        f'    {OUTCOME} = "credit granted on this application"\n'
        "else:\n"
        f'    {OUTCOME} = "adverse action taken on this application"\n'
    ),
]


def test_a_rule_set_reading_the_protected_variable_is_violated_at_proved():
    result = evaluate_requirement(
        _requirement(),
        _aware_system(rules=DISCRIMINATING_RULES),
        system_domains=("consumer-credit",),
    )
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED
    pair = result.details["counterexample_pair"]
    assert len(pair) == 2
    assert pair[0][PROTECTED] != pair[1][PROTECTED]
    assert pair[0]["credit_score"] == pair[1]["credit_score"]
    outcomes = result.details["counterexample_outcomes"]
    assert outcomes[0] != outcomes[1]


def test_the_witness_pair_is_replayed_on_both_halves():
    """A `violated` verdict must say both halves ran, not one."""
    result = evaluate_requirement(
        _requirement(),
        _aware_system(rules=DISCRIMINATING_RULES),
        system_domains=("consumer-credit",),
    )
    assert "Both halves" in result.details["verification"]


# --- the probed rung ----------------------------------------------------------------------------


def _opaque(rules=None, test_inputs=None):
    """A system whose `decide()` is real and whose `logic()` hands over no rules to prove on.

    The shape the paired-replay rung exists for: an input space the system declares, a decision
    procedure it will run, and nothing a solver can encode.
    """
    sut = _aware_system(rules=rules, constraints=AWARE_CONSTRAINTS)
    if test_inputs is not None:
        sut._test_inputs = [dict(case) for case in test_inputs]
    declared = sut.logic()
    declared["rules"] = []
    sut.logic = lambda: declared
    return sut


def test_paired_replay_reaches_probed_when_the_proof_rung_cannot():
    result = PairedReplayEngine.evaluate(_requirement(), _opaque())
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    budget = result.details["probe_budget"]
    assert budget["trials"] >= 1
    assert budget["input_space"]["protected values used"] == [0, 1]
    assert budget["pairs_errored"] == 0


def test_paired_replay_finds_a_disagreement_and_verifies_it():
    # A score of 660 clears the threshold under basis 0 and misses it under basis 1, so this is a
    # recorded decision whose twin differs. Neither of the standing base cases is: a bounded search
    # finds what the trace it was handed lets it reach, which is the whole difference from `proved`.
    result = PairedReplayEngine.evaluate(
        _requirement(),
        _opaque(rules=DISCRIMINATING_RULES, test_inputs=[{"credit_score": 660, PROTECTED: 0}]),
    )
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROBED
    assert "reproduced" in result.evidence_summary


def test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach():
    """The bounded-search claim, pinned: the same discriminating rules, satisfied at `probed`.

    The `proved` rung finds this system's breach because it quantifies over the declared input
    space; this rung sees only the decisions the system logged, and neither of them straddles the
    threshold the protected variable moves. That gap is what the strength lattice is for, and a
    `probed` satisfied result must keep saying it is a bounded search.
    """
    result = PairedReplayEngine.evaluate(
        _requirement(), _opaque(rules=DISCRIMINATING_RULES)
    )
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
    assert "not a proof" in result.evidence_summary

    proved = evaluate_requirement(
        _requirement(),
        _aware_system(rules=DISCRIMINATING_RULES),
        system_domains=("consumer-credit",),
    )
    assert proved.verdict == Verdict.VIOLATED


def test_paired_replay_takes_no_protected_value_from_the_trace():
    """A value the trace shows for the protected variable is never one this search replays."""
    sut = _opaque(test_inputs=[{"credit_score": 715, PROTECTED: 99}])
    result = PairedReplayEngine.evaluate(_requirement(), sut)
    used = result.details["probe_budget"]["input_space"]["protected values used"]
    assert used == [0, 1]
    assert 99 not in used


# --- the shipped pack ---------------------------------------------------------------------------


def test_the_shipped_duty_is_the_only_counterfactual_requirement():
    counterfactual = [
        (pack_name, req.id)
        for pack_name in ("ecoa", "eu_ai_act", "gdpr", "gpai", "table7")
        for req in load_pack(pack_name).requirements
        if req.formalism == "counterfactual"
    ]
    assert counterfactual == [("ecoa", "ecoa_reg_b_1002_4_a_no_disparate_treatment")]


def test_the_shipped_duty_is_satisfied_by_a_system_that_provably_ignores_the_basis():
    req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment")
    result = evaluate_requirement(req, _aware_system(), system_domains=("consumer-credit",))
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROVED
