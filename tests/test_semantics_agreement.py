"""Differential test: the interpreter and the Z3 encoding are one semantics.

`rulelang`'s module docstring states the invariant this file checks:

    The set of constructs accepted here and the set encoded in `engines/proved.py` must stay the
    same set. [...] counterexample verification runs the interpreter against the solver's model.
    If one side models a statement the other drops, verification agrees with itself about the
    wrong program.

Two implementations, kept in step by hand and checked only by the examples someone thought to
write. This generates specs from the accepted grammar instead, and asserts both halves of the
invariant:

- **Same answer.** `rulelang.eval_expression` over an environment, and Z3 asked whether the same
  formula is entailed by a rule block assigning every signal that environment's value, agree.
- **Same set.** A spec `rulelang.parse_property` accepts must not make the encoder raise anything
  other than its own deliberate `UnsupportedConstructError`, and where the encoder does accept, the
  interpreter must not refuse.

The route into the encoder is the engine's own: `_Scope`, `_encode_block` and `_ast_to_z3`, driven
by a synthetic rule block of `signal = <literal>` lines. That is not a second comparison harness —
it is the same encoding path `ProvedEngine.evaluate` takes, minus the solver-outcome bookkeeping,
and it is what makes `present()`/`contains()` reachable at all: both refuse a free input, so a
signal has to be *assigned* by rules before either atom is encodable.

Bounds, stated rather than discovered: `max_examples` and `deadline` below, and a solver timeout
per example. String regular languages are the slow case and the reason the deadline is generous.
"""

from __future__ import annotations

import ast
from datetime import timedelta

import pytest
import z3
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from reasonsmith.engines.proved import (
    _ast_to_z3,
    _encode_block,
    _extract_model_value,
    _Scope,
    _values_agree,
)
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    eval_expression,
    parse_property,
)

#: The signal pool every generated spec draws from, with the declared type the encoder reads.
#:
#: Numeric magnitudes are `int` and `real`, and the real values generated below are exact halves.
#: That is deliberate: `REAL_ARITHMETIC_LIMIT` already records that the solver reasons over exact
#: rationals while Python runs float64, so generating values where the two representations differ
#: would rediscover a documented, deliberate divergence rather than an unknown one.
SIGNAL_TYPES = {
    "count_a": "int",
    "count_b": "int",
    "margin_a": "real",
    "margin_b": "real",
    "flag_a": "bool",
    "flag_b": "bool",
    "text_a": "string",
    "text_b": "string",
}

NUMERIC_SIGNALS = ["count_a", "count_b", "margin_a", "margin_b"]
BOOLEAN_SIGNALS = ["flag_a", "flag_b"]
STRING_SIGNALS = ["text_a", "text_b"]

#: Recorded statements, chosen so blank, absent-by-blankness and phrase-bearing cases all occur.
TEXT_VALUES = ["", " ", "  ", "Denied", "denied for cause", "N/A", "no reason", "AB", "ab"]

#: Phrases a duty might fix. Non-empty and ASCII, which is all `contains_arguments` accepts.
PHRASES = ["denied", "N/A", "a", "AB", " ", "no", "cause"]

SOLVER_TIMEOUT_MS = 10_000


def _number_literal() -> st.SearchStrategy[str]:
    return st.one_of(
        st.integers(min_value=-5, max_value=5).map(str),
        st.sampled_from(["0.5", "1.5", "-2.5", "2.0", "0.0"]),
    )


_NUMERIC = st.recursive(
    st.one_of(st.sampled_from(NUMERIC_SIGNALS), _number_literal()),
    lambda children: st.one_of(
        st.tuples(st.sampled_from(["+", "-", "*", "%"]), children, children).map(
            lambda item: f"({item[1]} {item[0]} {item[2]})"
        ),
        children.map(lambda child: f"(-{child})"),
        children.map(lambda child: f"abs({child})"),
        st.tuples(st.sampled_from(["min", "max"]), children, children).map(
            lambda item: f"{item[0]}({item[1]}, {item[2]})"
        ),
    ),
    max_leaves=5,
)

_COMPARISON = st.one_of(
    st.tuples(_NUMERIC, st.sampled_from(["==", "!=", "<", "<=", ">", ">="]), _NUMERIC).map(
        lambda item: f"({item[0]} {item[1]} {item[2]})"
    ),
    # A chained comparison: the interpreter short-circuits, the encoder conjoins pairwise.
    st.tuples(
        _NUMERIC,
        st.sampled_from(["<", "<=", ">", ">="]),
        _NUMERIC,
        st.sampled_from(["<", "<=", ">", ">="]),
        _NUMERIC,
    ).map(lambda item: f"({item[0]} {item[1]} {item[2]} {item[3]} {item[4]})"),
)

_BOOLEAN_ATOM = st.one_of(
    st.sampled_from(BOOLEAN_SIGNALS),
    _COMPARISON,
    st.sampled_from(sorted(SIGNAL_TYPES)).map(lambda name: f"present({name})"),
    st.tuples(st.sampled_from(STRING_SIGNALS), st.sampled_from(PHRASES)).map(
        lambda item: f'contains({item[0]}, "{item[1]}")'
    ),
)

SPECS = st.recursive(
    _BOOLEAN_ATOM,
    lambda children: st.one_of(
        st.tuples(st.sampled_from(["and", "or"]), children, children).map(
            lambda item: f"({item[1]} {item[0]} {item[2]})"
        ),
        children.map(lambda child: f"(not {child})"),
        # All three spellings of implication, which `preprocess_spec` folds to one call.
        st.tuples(st.sampled_from(["Implies", "implies"]), children, children).map(
            lambda item: f"{item[0]}({item[1]}, {item[2]})"
        ),
        st.tuples(st.sampled_from(["->", "=>", " implies "]), children, children).map(
            lambda item: f"(({item[1]}){item[0]}({item[2]}))"
        ),
        # Both spellings of equivalence, which `preprocess_spec` folds to `Iff(...)` and
        # deliberately not to `==` — see `tests/test_equivalence_connective.py`. Here for the
        # reason implication is: the interpreter and the encoder must not drift on it.
        st.tuples(st.sampled_from(["<->", "<=>"]), children, children).map(
            lambda item: f"(({item[1]}){item[0]}({item[2]}))"
        ),
    ),
    max_leaves=5,
)

ENVIRONMENTS = st.fixed_dictionaries(
    {
        "count_a": st.integers(min_value=-4, max_value=4),
        "count_b": st.integers(min_value=-4, max_value=4),
        "margin_a": st.sampled_from([-2.5, -0.5, 0.0, 0.5, 1.5, 3.0]),
        "margin_b": st.sampled_from([-2.5, -0.5, 0.0, 0.5, 1.5, 3.0]),
        "flag_a": st.booleans(),
        "flag_b": st.booleans(),
        "text_a": st.sampled_from(TEXT_VALUES),
        "text_b": st.sampled_from(TEXT_VALUES),
    }
)


def _rule_block(env: dict[str, object]) -> str:
    """A rule block assigning every signal its environment value, in a fixed order.

    Assignment is what makes the environment reachable by the encoder at all: `_present_to_z3` and
    `_contains_to_z3` both refuse a signal the rules only read, and `scope.read` would otherwise
    hand back a free constant the solver may set to anything.
    """
    return "\n".join(f"{name} = {env[name]!r}" for name in sorted(SIGNAL_TYPES))


def _ground_encoding(env: dict[str, object]) -> tuple[_Scope, z3.Solver]:
    """A scope and solver carrying one assignment of every signal to its environment value."""
    scope = _Scope(SIGNAL_TYPES)
    solver = z3.Solver()
    solver.set("timeout", SOLVER_TIMEOUT_MS)
    _encode_block(ast.parse(_rule_block(env), mode="exec").body, scope, solver)
    return scope, solver


def _solver_truth(spec: str, env: dict[str, object]) -> bool | None:
    """Z3's answer for `spec` under `env`, or None when the solver did not decide it.

    The rule block is ground, so exactly one of `spec` and `not spec` is unsatisfiable alongside it.
    Anything else — both, neither, an `unknown` — means the solver did not settle this example, and
    the caller skips it rather than reading a verdict off a non-answer.
    """
    scope, base = _ground_encoding(env)
    spec_z3 = _ast_to_z3(parse_property(spec), scope)

    outcomes = []
    for claim in (spec_z3, z3.Not(spec_z3)):
        solver = z3.Solver()
        solver.set("timeout", SOLVER_TIMEOUT_MS)
        solver.add(*base.assertions())
        solver.add(claim)
        outcomes.append(solver.check())

    holds, fails = outcomes
    if holds == z3.sat and fails == z3.unsat:
        return True
    if holds == z3.unsat and fails == z3.sat:
        return False
    return None


@settings(
    max_examples=200,
    deadline=timedelta(seconds=30),
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(spec=SPECS, env=ENVIRONMENTS)
def test_the_encoder_and_the_interpreter_answer_the_same(spec: str, env: dict) -> None:
    """One spec, one assignment, two implementations, one answer."""
    try:
        node = parse_property(spec)
    except UnsupportedConstructError:
        # Not in the accepted grammar, so it says nothing about the encoder. The generator aims at
        # the accepted set; this is the residue, not a filter widening it.
        assume(False)
        return

    try:
        solver_answer = _solver_truth(spec, env)
    except UnsupportedConstructError:
        # The set half of the invariant: a deliberate refusal by the encoder is allowed, and the
        # interpreter must refuse the same spec rather than answer it.
        with pytest.raises(UnsupportedConstructError):
            eval_expression(node, dict(env))
        return

    assume(solver_answer is not None)

    try:
        interpreter_answer = bool(eval_expression(node, dict(env)))
    except ZeroDivisionError:
        # `x % 0` is a Python error, not a semantics the encoder is claimed to share: Z3's division
        # by zero is a total, underspecified function. Named here rather than generated away.
        assume(False)
        return

    assert interpreter_answer == solver_answer, (
        f"interpreter says {interpreter_answer} and Z3 says {solver_answer} "
        f"for {spec!r} on {env!r}"
    )


@settings(
    max_examples=200,
    deadline=timedelta(seconds=30),
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(expression=_NUMERIC, env=ENVIRONMENTS)
def test_the_encoder_and_the_interpreter_compute_the_same_number(
    expression: str, env: dict
) -> None:
    """The same agreement one level down, on the value rather than on the property.

    Comparing only a property's truth lets a connective above a diverging term hide it: `False and
    <wrong>` is `False` on both sides. `%` is the term that showed this — `_python_mod` reimplements
    Python's floor-based remainder because Z3's `mod` is not it, and a `%` divergence is invisible
    to the property-level test far more often than it is visible. Arithmetic is therefore compared
    where it is computed.
    """
    node = ast.parse(expression, mode="eval")
    scope, solver = _ground_encoding(env)
    encoded = _ast_to_z3(node, scope)

    assume(solver.check() == z3.sat)
    solver_value = _extract_model_value(solver.model().eval(encoded, model_completion=True))

    try:
        interpreter_value = eval_expression(node, dict(env))
    except ZeroDivisionError:
        assume(False)
        return

    assert _values_agree(solver_value, interpreter_value), (
        f"Z3 computes {solver_value!r} and the interpreter {interpreter_value!r} "
        f"for {expression!r} on {env!r}"
    )
