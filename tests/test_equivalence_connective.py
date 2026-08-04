"""`<=>` survives the rewriter as a connective, so the graded fragment can read it.

`preprocess_spec` used to rewrite `φ <=> ψ` into `(φ) == (ψ)` textually, before the Python parse.
Over the Booleans that is sound — equivalence *is* equality of truth values — and over the
residuated lattices of `manyvalued` it is not: `==` is a crisp comparison of two degrees, which
`docs/semantics.md` §9 refuses because a comparison against a degree is a threshold and no statute
states one. Because the rewriter destroyed the distinction before anything checked, the refusal
fired naming a construct the author never typed, and equivalence was unavailable in the graded
fragment for no design reason. `implies` was spared only by being spelled as a call rather than as
an arrow, which is an accident of text substitution and not a decision.

The tests here hold the fix on both sides: the two-valued reading did not move, and the graded
reading is the algebra's biresiduum.
"""

import ast
import itertools

import pytest
import z3

from reasonsmith.engines.proved import _ast_to_z3, _Scope
from reasonsmith.ltlf import Abstraction, available, entails, satisfiable, to_ltlf
from reasonsmith.manyvalued import ALGEBRAS, Grading, degree_of
from reasonsmith.rulelang import (
    EQUIVALENCE_CALL,
    UnsupportedConstructError,
    classify_fragment,
    eval_expression,
    parse_expression,
    parse_property,
    preprocess_spec,
)

GRADING = Grading(
    authority="a supervisory authority",
    scale="0 to 1",
    method="a panel reading",
    degrees={"detailed(reason)": 0.8, "adequate(notice)": 0.3},
)

EQUIVALENCE = 'degree(reason, "detailed") <=> degree(notice, "adequate")'


# --- The rewriter emits a node, not a comparison ------------------------------------------------


@pytest.mark.parametrize("token", ["<=>", "<->"])
def test_the_rewriter_never_collapses_equivalence_to_a_comparison(token):
    """The regression pin. Both spellings become one call and neither becomes `==`.

    Named in `docs/semantics.md` §9. If this fails, the graded fragment has lost equivalence again
    and every `<=>` an author writes is being refused as a threshold they did not state.
    """
    rewritten = preprocess_spec(f"approved {token} income >= 30000")
    assert rewritten.lstrip().startswith(f"{EQUIVALENCE_CALL}(")
    assert "==" not in rewritten

    node = parse_expression(f"approved {token} income >= 30000").body
    assert isinstance(node, ast.Call)
    assert node.func.id == EQUIVALENCE_CALL
    assert not any(isinstance(child, ast.Compare) and any(
        isinstance(op, ast.Eq) for op in child.ops
    ) for child in ast.walk(node))


def test_an_author_written_equality_is_still_a_comparison():
    """`==` the author typed stays a comparison, and the rewriter leaves it alone."""
    assert preprocess_spec("approved == flagged") == "approved == flagged"
    assert isinstance(parse_expression("approved == flagged").body, ast.Compare)


# --- Conservativity: the two-valued reading did not move --------------------------------------


@pytest.mark.parametrize("token", ["<=>", "<->"])
def test_the_interpreter_reads_equivalence_as_the_truth_table(token):
    """Against the truth table itself, not against whatever `==` happened to do."""
    node = parse_expression(f"p {token} q")
    for left, right in itertools.product([True, False], repeat=2):
        assert eval_expression(node, {"p": left, "q": right}) is (left == right)


@pytest.mark.parametrize("token", ["<=>", "<->"])
def test_the_solver_reads_equivalence_as_the_truth_table(token):
    """The Z3 encoding and the interpreter must agree, as they must for every other construct.

    Checked as validity of the biconditional against the table's own disjunctive spelling: an
    encoding that merely happened to agree on the four points the interpreter was asked about
    would still pass a per-point check under a free variable somewhere.
    """
    scope = _Scope({"p": "bool", "q": "bool"})
    encoded = _ast_to_z3(parse_expression(f"p {token} q").body, scope)
    table = _ast_to_z3(
        parse_expression("(p and q) or ((not p) and (not q))").body, scope
    )
    solver = z3.Solver()
    solver.add(encoded != table)
    assert solver.check() == z3.unsat


@pytest.mark.parametrize("token", ["<=>", "<->"])
def test_a_two_valued_equivalence_still_classifies_as_logical(token):
    assert classify_fragment(f"approved {token} income >= 30000") == "logical"


@pytest.mark.skipif(not available(), reason="the LTLf backend is an optional extra")
def test_the_trace_logic_has_a_spelling_for_equivalence():
    """The finite-trace backend renders it rather than skipping the duty by name.

    It has no `<->` of its own in this mapping, so the equivalence is spelled out both ways —
    which is the same expansion `engines/proved.py` encodes, and neither is a semantics this
    package implements.
    """
    abstraction = Abstraction()
    equivalence = to_ltlf("always(approved <=> present(reason))", abstraction)
    consequence = to_ltlf("always(present(reason) -> approved)", abstraction)
    assert satisfiable([equivalence], abstraction)
    assert entails(equivalence, consequence, abstraction)
    assert not entails(consequence, equivalence, abstraction)


# --- The graded reading is the biresiduum ------------------------------------------------------


def test_a_graded_equivalence_loads_and_classifies_as_graded():
    assert classify_fragment(EQUIVALENCE) == "graded"


@pytest.mark.parametrize("name", sorted(ALGEBRAS))
def test_a_graded_equivalence_is_the_algebra_s_biresiduum(name):
    """`φ ↔ ψ ≝ (φ → ψ) ⊗ (ψ → φ)`, derived from the residuum each algebra already stores."""
    algebra = ALGEBRAS[name]
    x, y = 0.8, 0.3
    expected = algebra.conjunction(algebra.residuum(x, y), algebra.residuum(y, x))
    assert degree_of(parse_property(EQUIVALENCE), {}, algebra, GRADING) == expected
    assert algebra.biresiduum(x, y) == expected


def test_lukasiewicz_equivalence_is_one_minus_the_distance():
    """The standard reading, pinned as a number rather than as its own definition restated."""
    algebra = ALGEBRAS["lukasiewicz"]
    for x, y in itertools.product([0.0, 0.25, 0.5, 0.8, 1.0], repeat=2):
        assert algebra.biresiduum(x, y) == pytest.approx(1.0 - abs(x - y))


@pytest.mark.parametrize("name", sorted(ALGEBRAS))
def test_the_biresiduum_is_one_exactly_when_the_degrees_agree(name):
    algebra = ALGEBRAS[name]
    for x, y in itertools.product([0.0, 0.3, 0.7, 1.0], repeat=2):
        assert (algebra.biresiduum(x, y) == 1.0) is (x == y)


@pytest.mark.parametrize("name", sorted(ALGEBRAS))
def test_the_graded_reading_agrees_with_the_two_valued_one_at_the_ends(name):
    """The conservativity obligation on the lattice: 0 and 1 give back the truth table."""
    algebra = ALGEBRAS[name]
    for left, right in itertools.product([0.0, 1.0], repeat=2):
        assert algebra.biresiduum(left, right) == float(left == right)


def test_a_graded_comparison_the_author_wrote_is_still_refused():
    """`==` under a graded atom is a threshold and stays refused, naming what was written."""
    with pytest.raises(UnsupportedConstructError) as raised:
        parse_property('degree(reason, "detailed") == degree(notice, "adequate")')
    message = str(raised.value)
    assert "==" in message
    assert "threshold" in message
    assert EQUIVALENCE_CALL not in message


def test_a_graded_atom_under_arithmetic_is_still_refused():
    with pytest.raises(UnsupportedConstructError):
        parse_property('degree(reason, "detailed") + 1 > 0')


# --- Chained equivalence, and the asymmetry with implication -----------------------------------


@pytest.mark.parametrize("token", ["<=>", "<->"])
def test_a_chained_equivalence_is_refused_as_ambiguous(token):
    """Still refused, and the message is still true of what the author wrote.

    An implication chain has a settled right-associative reading in every logic this package
    touches; `a <=> b <=> c` does not, so the author is asked which one they meant rather than
    handed one of them.
    """
    with pytest.raises(UnsupportedConstructError) as raised:
        preprocess_spec(f"a {token} b {token} c")
    assert "Chained equivalence" in str(raised.value)


def test_mixed_equivalence_spellings_are_refused_too():
    with pytest.raises(UnsupportedConstructError):
        preprocess_spec("a <=> b <-> c")


@pytest.mark.parametrize("token", ["->", "=>"])
def test_an_implication_chain_stays_admitted_right_associatively(token):
    """`a -> b -> c` is `a -> (b -> c)`, which the interpreter must confirm at the one point the
    two bracketings differ: `a` false, `b` true, `c` false."""
    node = parse_expression(f"a {token} b {token} c")
    assert eval_expression(node, {"a": False, "b": True, "c": False}) is True
    left_bracketed = parse_expression(f"(a {token} b) {token} c")
    assert eval_expression(left_bracketed, {"a": False, "b": True, "c": False}) is False


def test_a_parenthesised_equivalence_chain_is_admitted():
    """Parenthesising one side is the instruction the refusal gives, so it must work."""
    node = parse_expression("(a <=> b) <=> c")
    assert eval_expression(node, {"a": True, "b": True, "c": True}) is True
    assert eval_expression(node, {"a": True, "b": False, "c": True}) is False
