"""Tests for `contains()`, the atom that reads what a statement says.

What this module is for:
  Every duty in the shipped packs used to be settled by whether a field was blank. That makes the
  strongest available claim about an explanation duty "the reason field is non-blank", which a
  reason string of `"n/a"` satisfies and 12 CFR 1002.9(b)(2) does not accept. `contains()` is the
  narrowest addition that lets a clause's own *negative* constraint — the wordings it names as
  insufficient — be checked against a plain decision log.

What a reader must not break:
  - The three encodings must agree. `contains()` is evaluated in three places: the rulelang
    interpreter (replay, and the solver's own cross-check), a synthetic flag fed to rtamt, and a
    regular language handed to Z3. `test_the_solvers_fold_is_the_interpreters_fold` is the
    differential check that holds the outermost two together over a generated corpus, in the same
    spirit as `test_the_solvers_blank_string_is_pythons_blank_string` does for `present()`.
    A predicate that means one thing to the monitor and another to the solver reports `proved`
    about a property nobody wrote.
  - The fold stays ASCII and stays one-to-one. `str.lower()` is not length-preserving over all of
    Unicode, and a fold the solver cannot reproduce character-for-character is the divergence
    above. A non-ASCII phrase is refused at load time rather than folded approximately.
  - A value that is present but is not text is NOT read as carrying no phrase. Answering `False`
    there would report a system satisfied on a field nothing read, which is the overclaim this
    package exists to refuse.
"""

from __future__ import annotations

import random

import pytest
import z3

from reasonsmith.engines.observed import ObservedEngine, to_stl
from reasonsmith.engines.proved import _contains_string_z3
from reasonsmith.report import evaluate_requirement
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    classify_fragment,
    contains_literal,
    eval_expression,
    fold_ascii_case,
    parse_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

REASON = "artifact_logs_reason_explanation"


def _requirement(spec: str, formalism: str, requires: tuple[str, ...]) -> Requirement:
    return Requirement(
        id="contains_probe",
        source_document="ECOA / Regulation B (12 CFR 1002.9)",
        article_clause="12 CFR 1002.9(b)(2)",
        verbatim_text="must be specific and indicate the principal reason(s)",
        stakeholder="affected individual",
        formalism=formalism,
        spec=spec,
        rationale="A probe requirement, authored by this test rather than shipped.",
        requires=requires,
        binding=True,
        scope="",
    )


def _evaluate(spec: str, values: list[object]) -> object:
    """Run a one-signal temporal property over a trace of `REASON` values."""
    records = [{REASON: value} for value in values]
    req = _requirement(spec, "temporal", (REASON,))
    return ObservedEngine.evaluate(req, BaseSUT({REASON}), records)


# --------------------------------------------------------------------------------------------
# The language
# --------------------------------------------------------------------------------------------


def test_a_contains_atom_is_a_boolean_property_outside_the_record_fragment():
    """It reads a value, so it is not a presence conjunction and cannot be a `record` duty.

    The record engine's whole diagnostic value is naming which `present()` conjunct failed, and it
    can only walk a conjunction of those. A property asking what a statement *says* belongs to a
    fragment with an engine that can evaluate it.
    """
    assert classify_fragment(f'contains({REASON}, "n/a")') == "logical"
    assert classify_fragment(f'always(not contains({REASON}, "n/a"))') == "temporal"


@pytest.mark.parametrize(
    ("spec", "fragment"),
    [
        (f'contains({REASON})', "arity"),
        (f'contains({REASON}, "a", "b")', "arity"),
        ('contains("literal", "a")', "signal name"),
        (f'contains({REASON} + "x", "a")', "signal name"),
        (f'contains({REASON}, other_signal)', "literal"),
        (f'contains({REASON}, 3)', "literal"),
        (f'contains({REASON}, "")', "empty"),
        (f'contains({REASON}, "refusé")', "non-ascii"),
    ],
)
def test_a_malformed_contains_atom_is_refused_rather_than_guessed_at(spec: str, fragment: str):
    """Every shape but `contains(signal, "literal")` raises, naming what it found.

    A computed haystack has no field for an engine to bind, and a phrase read out of the decision
    record would let the system being audited choose what it is forbidden to say.
    """
    with pytest.raises(UnsupportedConstructError):
        parse_property(spec)
    assert fragment  # the parametrisation labels why each shape is refused


def test_the_phrase_is_not_a_signal_the_property_reads():
    """`requires` gates the signal, never the words of the phrase."""
    from reasonsmith.rulelang import signal_names, unconditional_signal_names

    node = parse_property(f'contains({REASON}, "internal standards")')
    assert signal_names(node) == (REASON,)
    assert unconditional_signal_names(node) == (REASON,)


# --------------------------------------------------------------------------------------------
# The interpreter
# --------------------------------------------------------------------------------------------


def test_a_record_carrying_no_statement_carries_no_phrase():
    """Absence is false here, which is what lets an implication guarded by `present()` decide.

    12 CFR 1002.9(b)(2) governs the statement paragraph (a)(2)(i) requires. A creditor that
    lawfully took the (a)(2)(ii) disclosure branch has no statement of reasons, and a predicate
    that raised or defaulted true on the missing field would put that creditor back in breach —
    the false violation the trigger exists to remove.
    """
    node = parse_property(f'contains({REASON}, "n/a")')
    for absent in (None, "", "   ", [], {}):
        assert eval_expression(node, {REASON: absent}) is False
    assert eval_expression(node, {}) is False


def test_the_fold_is_ascii_case_and_reaches_no_further():
    loud = "You FAILED To Achieve a Qualifying Score."
    assert contains_literal(loud, "failed to achieve") is True
    assert contains_literal("failed to achieve", "FAILED TO ACHIEVE") is True
    assert contains_literal("insufficient recent repayment history", "internal standards") is False
    # Length-preserving by construction: the fold is what the solver reproduces character by
    # character, so anything outside A-Z must pass through untouched.
    for text in ("İ", "ß", "ẞ", "straße", "ÉCLAIR"):
        assert len(fold_ascii_case(text)) == len(text)
        assert fold_ascii_case(text) == "".join(
            chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in text
        )


def test_a_statement_given_in_parts_is_read_part_by_part():
    """A log recording reasons as a list is recording a statement of reasons.

    Refusing it would report *not evaluated* because of how a log is shaped rather than because of
    what it says — the same defect as declining to read a trace that is right there. The real
    system in `docs/nesyarena-conformance-report.md` records reasons exactly this way.
    """
    node = parse_property(f'contains({REASON}, "qualifying score")')
    assert eval_expression(node, {REASON: ["C03 length of credit history"]}) is False
    assert eval_expression(
        node, {REASON: ["C03 length of credit history", "Failed to achieve a QUALIFYING SCORE"]}
    ) is True


def test_the_parts_of_a_statement_are_never_joined():
    """A phrase must occur in one part, not across the seam between two.

    Joining the list would invent a sentence the system never wrote: two reasons that merely
    appeared in the same record would read as one continuous statement.
    """
    node = parse_property(f'contains({REASON}, "internal standards")')
    assert eval_expression(node, {REASON: ["nothing internal", "standards were met"]}) is False
    assert eval_expression(node, {REASON: ["our internal standards applied"]}) is True


def test_a_present_value_that_is_not_a_statement_is_refused():
    """A number or a mapping is not a statement, and is not evidence that none was insufficient."""
    node = parse_property(f'contains({REASON}, "n/a")')
    for not_a_statement in (7, {"code": "n/a"}, ["n/a", 3]):
        with pytest.raises(UnsupportedConstructError):
            eval_expression(node, {REASON: not_a_statement})


# --------------------------------------------------------------------------------------------
# The rtamt encoding
# --------------------------------------------------------------------------------------------


def test_a_forbidden_phrase_in_the_trace_is_an_observed_violation():
    result = _evaluate(
        f'always(not contains({REASON}, "failed to achieve a qualifying score"))',
        [
            "Delinquent past or present credit obligations",
            "You failed to achieve a qualifying score on our model.",
        ],
    )
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED
    assert result.details["violation_step_indices"] == [1]


def test_a_statement_naming_a_factor_is_observed_satisfied():
    result = _evaluate(
        f'always(not contains({REASON}, "failed to achieve a qualifying score"))',
        ["Length of credit history", "Excessive obligations in relation to income"],
    )
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


def test_a_non_text_value_makes_the_duty_not_evaluated_never_satisfied():
    """The counterpart of an unmeasured magnitude: a kind the trace never established."""
    result = _evaluate(
        f'always(not contains({REASON}, "n/a"))',
        ["Length of credit history", {"code": "n/a"}],
    )
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert "not text" in result.evidence_summary
    assert result.details["signals_without_text_in_trace"] == {REASON: 1}


def test_a_call_head_a_phrase_merely_quotes_is_not_rewritten():
    """Rewriting for rtamt is textual, and a forbidden phrase is pack text, not a sub-formula."""
    rendered = to_stl(f'contains({REASON}, "present(x) and contains(y, 1)")')
    assert rendered.count(">= 0.5") == 1
    assert "present(x)" not in rendered


# --------------------------------------------------------------------------------------------
# The agreement obligation
# --------------------------------------------------------------------------------------------


def _solver_says(haystack: str, needle: str) -> bool:
    """Whether the solver's whole `contains()` encoding accepts `haystack`.

    The encoding the engine emits, not the regular language inside it: the blankness rule is part
    of what `contains()` means to Z3, and a helper that reached past it would leave the one input
    class where a substring search and `is_present` pull apart uncovered.
    """
    text = z3.String("text")
    solver = z3.Solver()
    solver.set("timeout", 10000)
    solver.add(text == z3.StringVal(haystack))
    solver.add(_contains_string_z3(text, needle))
    return solver.check() == z3.sat


def test_the_solvers_fold_is_the_interpreters_fold():
    """`contains()` must mean the same thing to Z3 as it does to the interpreter.

    The solver renders each phrase character as a regular language matching exactly one character,
    itself or either ASCII case. The interpreter folds both sides with `fold_ascii_case`. The two
    agree only while that fold is one-to-one and reaches no further than A-Z, so this walks a
    generated corpus including non-ASCII text, digits, punctuation and both cases rather than
    asserting the property on the two examples a shipped pack happens to use.

    Blank haystacks stay in the corpus: a phrase made of blanks occurs in a string of blanks as a
    substring, and `contains_literal` still answers false there because the record carries nothing.
    That is the one place the two sides agree only because the solver's encoding carries the same
    blankness rule, so excluding it would leave the divergence it forbids untested.
    """
    rng = random.Random(20260802)
    alphabet = "aAbB Zz9_-.éİß"
    for _ in range(120):
        needle = "".join(rng.choice("aAbB Z9-.") for _ in range(rng.randint(1, 4)))
        haystack = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 8)))
        assert contains_literal(haystack, needle) == _solver_says(haystack, needle), (
            haystack,
            needle,
        )


def test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry():
    """The corpus reaches an all-blank string only by luck, and this is the case that matters.

    `is_present` calls a whitespace-only string absent, so `contains_literal` answers false for a
    phrase of blanks in a string of blanks. A bracketed regular language on its own answers true,
    which would let the same value be `proved` violated and `observed` satisfied.
    """
    assert contains_literal("  ", " ") is False
    assert _solver_says("  ", " ") is False


def test_a_forbidden_phrase_the_rules_can_write_is_proved_to_violate():
    """The whole point of the state fragment: a system that exposes its logic is not merely watched.

    The rules below always write a reason, so the presence conjunction every explanation duty used
    to be would report this system `proved` satisfied. One branch writes a statement the clause
    itself calls insufficient, and the solver finds it over every admitted input rather than
    waiting for it to turn up in a log.
    """
    from reasonsmith.adapters.rules import RulesAdapter

    req = _requirement(
        f'not contains({REASON}, "failed to achieve a qualifying score")',
        "logical",
        (REASON,),
    )
    sut = RulesAdapter(
        rules=[
            "approved = credit_score >= 640",
            "if approved:\n"
            f'    {REASON} = "C00 no adverse factor"\n'
            "else:\n"
            f'    {REASON} = "Applicant failed to achieve a qualifying score"\n',
        ],
        variables={"credit_score": "int", "approved": "bool", REASON: "str"},
        constraints=["credit_score >= 300", "credit_score <= 850"],
        declared_capabilities={REASON},
        test_inputs=[{"credit_score": 700}],
    )
    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.PROVED


def test_rules_that_never_write_a_forbidden_phrase_are_proved_to_satisfy():
    from reasonsmith.adapters.rules import RulesAdapter

    req = _requirement(
        f'not contains({REASON}, "failed to achieve a qualifying score")',
        "logical",
        (REASON,),
    )
    sut = RulesAdapter(
        rules=[
            "approved = credit_score >= 640",
            "if approved:\n"
            f'    {REASON} = "C00 no adverse factor"\n'
            "else:\n"
            f'    {REASON} = "C01 income insufficient for amount requested"\n',
        ],
        variables={"credit_score": "int", "approved": "bool", REASON: "str"},
        constraints=["credit_score >= 300", "credit_score <= 850"],
        declared_capabilities={REASON},
        test_inputs=[{"credit_score": 700}],
    )
    result = evaluate_requirement(req, sut)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROVED


def test_the_solver_refuses_a_signal_it_cannot_read_as_text():
    """A rule set giving the name a number is not the system this property is about.

    The refusal drops the duty to the strongest engine that *can* answer, exactly as the presence
    proof's refusals do, rather than coercing a sort and proving something about a program nobody
    wrote.
    """
    from reasonsmith.adapters.rules import RulesAdapter

    req = _requirement(f'not contains({REASON}, "n/a")', "logical", (REASON,))
    sut = RulesAdapter(
        rules=[f"{REASON} = credit_score * 2"],
        variables={"credit_score": "int", REASON: "int"},
        constraints=["credit_score >= 300"],
        declared_capabilities={REASON},
        test_inputs=[{"credit_score": 700}],
    )
    result = evaluate_requirement(req, sut)
    assert result.strength is None
    assert "recorded text" in result.evidence_summary
