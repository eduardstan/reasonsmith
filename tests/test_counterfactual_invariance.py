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
