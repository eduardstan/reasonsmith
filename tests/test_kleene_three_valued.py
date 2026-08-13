"""The third value is Kleene's, and it is read off a truth value rather than off an identity.

`docs/theory/03-semantics.md` Definition 3.11 writes out the tables and states which
three-valuedness
this is. These
are the tests that claim names, in the discipline `test_language_definition.py` enforces: a table
written in a document and checked nowhere is a table nothing holds the interpreter to.

The regression the truth-value tests close: every Kleene operator once compared its operands with
`is True` / `is False`, so an atom returning `0`, `1` or `""` — values an audited system's records
supply and this language's atoms return — matched neither branch and fell through to the operator's
unit. That produced a genuine `True` off a falsy conjunct and a genuine `False` off a truthy
disjunct at the `probed` and `certificate` rungs, which guard no atom, and it is exactly the
silent-wrong-answer class the third value exists to prevent.
"""

from __future__ import annotations

import pytest

from reasonsmith.rulelang import (
    UNKNOWN,
    eval_expression,
    eval_temporal_trace,
    is_unknown,
    kleene_and,
    kleene_and_binary,
    kleene_iff,
    kleene_implies,
    kleene_not,
    kleene_or,
    kleene_or_binary,
    kleene_value,
    parse_property,
)

#: The chain `F < U < T`, as `docs/theory/03-semantics.md` Definition 3.11 writes it.
VALUES = (False, UNKNOWN, True)


def _name(val: object) -> str:
    return "U" if is_unknown(val) else ("T" if val is True else "F")


def _same(a: object, b: object) -> bool:
    return is_unknown(a) if is_unknown(b) else (not is_unknown(a) and a is b)


# ------------------------------------------------------------------------------------------------
# 1. The tables are Kleene's and no other's
# ------------------------------------------------------------------------------------------------

#: `¬φ` — the table's first column.
NEGATION = {"F": "T", "U": "U", "T": "F"}

#: `φ ∧ ψ`, rows `φ`, columns `ψ`.
CONJUNCTION = {
    ("F", "F"): "F", ("F", "U"): "F", ("F", "T"): "F",
    ("U", "F"): "F", ("U", "U"): "U", ("U", "T"): "U",
    ("T", "F"): "F", ("T", "U"): "U", ("T", "T"): "T",
}

#: `φ ∨ ψ`, rows `φ`, columns `ψ`.
DISJUNCTION = {
    ("F", "F"): "F", ("F", "U"): "U", ("F", "T"): "T",
    ("U", "F"): "U", ("U", "U"): "U", ("U", "T"): "T",
    ("T", "F"): "T", ("T", "U"): "T", ("T", "T"): "T",
}


def test_the_kleene_tables_are_the_ones_the_language_doc_writes_out():
    for val in VALUES:
        assert _name(kleene_not(val)) == NEGATION[_name(val)]

    for a in VALUES:
        for b in VALUES:
            key = (_name(a), _name(b))
            assert _name(kleene_and_binary(a, b)) == CONJUNCTION[key], key
            assert _name(kleene_or_binary(a, b)) == DISJUNCTION[key], key
            assert _name(kleene_and([a, b])) == CONJUNCTION[key], key
            assert _name(kleene_or([a, b])) == DISJUNCTION[key], key


def test_implication_and_equivalence_are_derived_and_not_tabulated():
    """`φ → ψ` is `¬φ ∨ ψ` and `φ ↔ ψ` is `(φ → ψ) ∧ (ψ → φ)`, which is why `U ↔ U = U`."""
    for a in VALUES:
        for b in VALUES:
            assert _same(kleene_implies(a, b), kleene_or_binary(kleene_not(a), b))
            assert _same(
                kleene_iff(a, b),
                kleene_and_binary(kleene_implies(a, b), kleene_implies(b, a)),
            )

    assert is_unknown(kleene_iff(UNKNOWN, UNKNOWN))
    assert is_unknown(kleene_implies(UNKNOWN, UNKNOWN))


def test_the_unknown_value_refuses_to_coerce_to_a_boolean():
    """A third value that silently read as `False` at an `if` is a two-valued answer in disguise."""
    with pytest.raises(TypeError):
        bool(UNKNOWN)

    assert is_unknown(UNKNOWN)
    assert not is_unknown(False)
    assert not is_unknown(None)

    class _UnknownType:  # noqa: N801 - deliberately the sentinel class's own name
        pass

    assert not is_unknown(_UnknownType()), "the third value is one object, not a class name"


# ------------------------------------------------------------------------------------------------
# 2. The operators read a truth value, never an identity
# ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("falsy", [0, 0.0, "", [], {}, None])
def test_a_falsy_operand_is_false_and_not_a_third_thing(falsy):
    assert kleene_and([falsy]) is False
    assert kleene_and_binary(falsy, True) is False
    assert kleene_or([falsy]) is False
    assert kleene_not(falsy) is True
    assert kleene_value(falsy) is False


@pytest.mark.parametrize("truthy", [1, 1.0, "yes", [0], 2])
def test_a_truthy_operand_is_true_and_not_a_third_thing(truthy):
    assert kleene_or([truthy]) is True
    assert kleene_or_binary(truthy, False) is True
    assert kleene_and([truthy]) is True
    assert kleene_not(truthy) is False
    assert kleene_value(truthy) is True


def test_the_interpreter_does_not_answer_a_conjunction_off_a_falsy_atom():
    """The regression: `0 and present(x)` answered `True`; `1 or present(z)` answered `False`."""
    conjunction = parse_property("approved and present(x)")
    assert eval_expression(conjunction, {"approved": 0, "x": "y"}) is False

    disjunction = parse_property("approved or present(z)")
    assert eval_expression(disjunction, {"approved": 1}) is True


def test_a_trace_of_records_evaluates_into_the_kleene_chain_and_not_into_raw_values():
    """`eval_temporal_trace` returns truth values, so `b is False` at a call site is sound."""
    trace = eval_temporal_trace(parse_property("always(flag)"), [{"flag": 0}, {"flag": 1}])
    assert all(b is True or b is False or is_unknown(b) for b in trace)
    assert trace[0] is False

    per_step = eval_temporal_trace(parse_property("flag"), [{"flag": 0}, {"flag": "yes"}, {}])
    assert per_step[0] is False
    assert per_step[1] is True
    assert is_unknown(per_step[2])


# ------------------------------------------------------------------------------------------------
# 3. Sound for the question, and not complete for it
# ------------------------------------------------------------------------------------------------


def test_kleene_is_sound_and_not_complete_for_determinacy():
    """A two-valued answer holds under every completion; `φ ∨ ¬φ` is `U` although every does."""
    for a in VALUES:
        for b in VALUES:
            for op in (kleene_and_binary, kleene_or_binary, kleene_implies, kleene_iff):
                got = op(a, b)
                if is_unknown(got):
                    continue
                completions = {
                    op(a if not is_unknown(a) else ca, b if not is_unknown(b) else cb)
                    for ca in (True, False)
                    for cb in (True, False)
                }
                assert completions == {got}, (op.__name__, _name(a), _name(b))

    assert is_unknown(kleene_or_binary(UNKNOWN, kleene_not(UNKNOWN)))


# --------------------------------------------------------------------------------------------
# The two atoms of the language must not disagree about the sentinel
# --------------------------------------------------------------------------------------------


def test_the_sentinel_reaches_a_decision_record_through_a_shipped_adapter():
    """The path, before the verdict: nothing here hand-builds the sentinel.

    `RulesAdapter` runs the rules and writes whatever the interpreter returned straight into the
    record, and the interpreter returns UNKNOWN for a rule whose inputs were not all supplied. So
    a log an auditor is handed can carry the sentinel without anyone having injected it, which is
    why a fixture that hand-built one would prove nothing about whether the real path is closed.
    """
    from reasonsmith.adapters.rules import RulesAdapter

    adapter = RulesAdapter(
        rules=["notice = appeal_flag and True"],
        variables={"appeal_flag": "bool", "notice": "bool"},
        constraints=[],
        declared_capabilities={"notice", "appeal_flag"},
        test_inputs=[{}],
    )
    records = adapter.decisions()

    assert is_unknown(records[0]["notice"])


def test_present_and_a_bare_name_agree_about_the_sentinel():
    """`present(x)` answered true for a value whose whole meaning is *no value was determined*.

    Two atoms of one language, one object, opposite answers: a bare `notice` read as UNKNOWN while
    `present(notice)` read as satisfied. End to end that landed `satisfied` at strength `observed`
    on a trace of records carrying nothing, under the summary "every required signal carries a
    value in every record".
    """
    from reasonsmith.rulelang import is_present

    assert is_present(UNKNOWN) is False
    assert is_unknown(kleene_value(UNKNOWN))
    assert eval_expression(parse_property("present(notice)"), {"notice": UNKNOWN}) is False


def test_a_record_duty_over_a_log_of_sentinels_is_not_satisfied():
    """The verdict the disagreement produced, at the rung it produced it at."""
    from reasonsmith.adapters.rules import RulesAdapter
    from reasonsmith.engines.record import RecordEngine
    from reasonsmith.spec import Requirement
    from reasonsmith.verdict import Verdict

    adapter = RulesAdapter(
        rules=["notice = appeal_flag and True"],
        variables={"appeal_flag": "bool", "notice": "bool"},
        constraints=[],
        declared_capabilities={"notice"},
        test_inputs=[{}, {}],
    )
    log = [dict(record) for record in adapter.decisions()]

    class LogOnly:
        system_domains = ("consumer-credit",)

        def capabilities(self):
            return {"notice"}

        def decisions(self):
            return [dict(record) for record in log]

        def logic(self):
            return None

    req = Requirement(
        id="sentinel_presence",
        source_document="Internal Policy",
        article_clause="Section 1.1",
        verbatim_text="A notice shall be recorded for every decision.",
        stakeholder="Compliance",
        formalism="record",
        spec="present(notice)",
        rationale="Why this duty exists, in English.",
        requires=("notice",),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    system = LogOnly()
    result = RecordEngine.evaluate(req, system, system.decisions())

    assert result.verdict != Verdict.SATISFIED
    assert "carries a value in every record" not in result.evidence_summary
