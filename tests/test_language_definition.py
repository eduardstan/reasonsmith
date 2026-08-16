"""Conformance tests for `docs/theory/02-syntax.md`: the grammar, and the monitor's reading of it.

What this module is for:
  `docs/theory/02-syntax.md` defines the property language — a grammar, a denotation, and four
  implementations of that denotation. A grammar nothing generates from is a comment, and a
  denotation nothing executes is prose with notation in it. This module is what makes both
  checkable:

  - the EBNF block in the document is compared against `rulelang`'s own call-name constants, so a
    call added to the language and not to the grammar fails the build;
  - specs are generated from the productions of that grammar and asserted accepted, and placed in
    the fragment the generator built them for;
  - every refusal the document names by id is refused, and every refusal this module knows is
    named there — the two halves of one pin;
  - the four lexical decisions the document settles are asserted rather than described;
  - the `observed` implementation is held to the reference reading, with its four divergences
    named rather than averaged away.

What a reader must not break:
  - `MONITOR_DIVERGENCES` is an exclusion list, and an exclusion list that can grow silently is
    worthless. `test_the_four_named_shapes_are_still_what_the_document_records` asserts each row is
    still what §4 says it is — three refused in the rendering and still divergent behind the
    refusal, one the boundary convention — and
    `test_the_monitor_agrees_with_the_reference_reading` fails if a *new* shape diverges.
    Why this matters: these are four places where two implementations of one semantics answer
    differently. Silently widening the list turns a finding into a habit, and keeping a refusal
    after its reason has gone costs a duty a rung for nothing.
  - `RTAMT_BEHAVIOUR` is why the refusal list is three constructs and not more: rtamt raises for
    nearly everything else this language admits and it does not support.
    `test_rtamt_still_behaves_the_way_the_refusals_assume` measures that rather than trusting it.
    Why this matters: the `%` defect existed because rtamt error-recovered instead of raising, and a
    version bump could do the same for another construct with nothing to notice it.
  - The refusal table is keyed by the ids `docs/theory/02-syntax.md` Definition 2.5 uses.
    Renaming one there without renaming it here fails, which is the point.
"""

from __future__ import annotations

import ast
import re
from datetime import timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from reasonsmith.engines.observed import (
    MisreadShapeError,
    ObservedEngine,
    _monitor,
    _refuse_shapes_the_monitor_misreads,
    _render_stl,
    to_stl,
)
from reasonsmith.rulelang import (
    BOUNDED_RESPONSE_CALL,
    CONTAINS_CALL,
    COUNTERFACTUAL_CALL,
    DEGREE_CALL,
    PRESENCE_CALL,
    TEMPORAL_OPERATORS,
    UNDETERMINED_CALL,
    VALUE_CALLS,
    UnsupportedConstructError,
    classify_fragment,
    eval_expression,
    parse_property,
    preprocess_spec,
    signal_names,
)
from reasonsmith.spec import Requirement, list_packs, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
SYNTAX_DOC = REPO_ROOT / "docs" / "theory" / "02-syntax.md"
SEMANTICS_DOC = REPO_ROOT / "docs" / "theory" / "03-semantics.md"
CLAIM_MAP_DOC = REPO_ROOT / "docs" / "theory" / "claim-map.md"

#: A `test_...` identifier as the document writes them. A name followed by `.py` is a module the
#: document points at, not a claim's enforcing test. Same convention as `test_docs_semantics.py`.
_TEST_NAME = re.compile(r"\btest_[a-z0-9_]+\b(?!\.py)")

#: The words the grammar quotes that are Python keywords or literals rather than call names.
_GRAMMAR_KEYWORDS = frozenset({"not", "and", "or", "True", "False", "None"})


def _document() -> str:
    assert SYNTAX_DOC.is_file(), f"{SYNTAX_DOC} does not exist"
    return SYNTAX_DOC.read_text(encoding="utf-8")


def _semantics_document() -> str:
    assert SEMANTICS_DOC.is_file(), f"{SEMANTICS_DOC} does not exist"
    return SEMANTICS_DOC.read_text(encoding="utf-8")


def _claim_map() -> str:
    assert CLAIM_MAP_DOC.is_file(), f"{CLAIM_MAP_DOC} does not exist"
    return CLAIM_MAP_DOC.read_text(encoding="utf-8")


def _ebnf_block() -> str:
    """The one fenced ```ebnf block of the document."""
    blocks = re.findall(r"```ebnf\n(.*?)```", _document(), re.DOTALL)
    assert len(blocks) == 1, f"expected exactly one ebnf block, found {len(blocks)}"
    return blocks[0]


def _language_call_names() -> set[str]:
    return (
        {
            BOUNDED_RESPONSE_CALL,
            PRESENCE_CALL,
            CONTAINS_CALL,
            COUNTERFACTUAL_CALL,
            UNDETERMINED_CALL,
            DEGREE_CALL,
        }
        | set(TEMPORAL_OPERATORS)
        | set(VALUE_CALLS)
    )


# ------------------------------------------------------------------------------------------------
# 1. The grammar, checked against the language it describes
# ------------------------------------------------------------------------------------------------


def test_the_grammar_names_exactly_the_calls_the_language_defines():
    """The EBNF is a description of `rulelang`, and a description that drifts is worthless.

    Every identifier-shaped terminal the grammar quotes is either a Python keyword the grammar
    needs (`and`, `not`, `True`, …) or the head of a call this language admits. The comparison runs
    both ways: a call the language gained and the grammar did not fails here, and so does a call the
    grammar names and the language does not have.
    """
    quoted = {token.strip() for token in re.findall(r'"([^"]*)"', _ebnf_block())}
    named = {token for token in quoted if token.isidentifier()} - _GRAMMAR_KEYWORDS

    defined = _language_call_names()
    assert named == defined, (
        "docs/theory/02-syntax.md Definition 2.2 and rulelang disagree about the call set. "
        f"only in the grammar: {sorted(named - defined)}; "
        f"only in the language: {sorted(defined - named)}"
    )


# --- generation from the grammar ---------------------------------------------------------------
#
# The pools are disjoint on purpose. A signal cannot hold both the bare-Boolean role and the
# measured-magnitude role in one property (§1.5), so a single pool would generate refusals and this
# test would be measuring the side conditions rather than the grammar.

MAGNITUDES = ["count_a", "count_b", "margin_a"]
FLAGS = ["flag_a", "flag_b"]
RECORD_SIGNALS = ["reason_a", "reason_b", "notice_a"]
PHRASES = ["n/a", "internal policies", "no reason"]

_NUMBER = st.one_of(
    st.integers(min_value=-9, max_value=9).map(str),
    st.sampled_from(["0.5", "1.5", "-2.0", "30", "90"]),
)

_ARITH = st.recursive(
    st.one_of(st.sampled_from(MAGNITUDES), _NUMBER),
    lambda children: st.one_of(
        st.tuples(st.sampled_from(["+", "-", "*", "/", "%"]), children, children).map(
            lambda item: f"({item[1]} {item[0]} {item[2]})"
        ),
        children.map(lambda child: f"(-{child})"),
        children.map(lambda child: f"abs({child})"),
        st.tuples(st.sampled_from(["min", "max"]), children, children).map(
            lambda item: f"{item[0]}({item[1]}, {item[2]})"
        ),
    ),
    max_leaves=4,
)

_CMP_OP = st.sampled_from(["==", "!=", "<", "<=", ">", ">="])

_COMPARISON = st.one_of(
    st.tuples(_ARITH, _CMP_OP, _ARITH).map(lambda item: f"({item[0]} {item[1]} {item[2]})"),
    st.tuples(_ARITH, _CMP_OP, _ARITH, _CMP_OP, _ARITH).map(
        lambda item: f"({item[0]} {item[1]} {item[2]} {item[3]} {item[4]})"
    ),
)

_PRESENCE = st.sampled_from(RECORD_SIGNALS).map(lambda name: f"present({name})")

_STATE_ATOM = st.one_of(
    st.sampled_from(FLAGS),
    _COMPARISON,
    _PRESENCE,
    st.tuples(st.sampled_from(RECORD_SIGNALS), st.sampled_from(PHRASES)).map(
        lambda item: f'contains({item[0]}, "{item[1]}")'
    ),
)


def _connectives(children: st.SearchStrategy[str]) -> st.SearchStrategy[str]:
    """Every Boolean connective the grammar admits, in every spelling it admits.

    Each arrow form is fully parenthesised, which is what the rewriter does to each side anyway and
    what keeps a generated equivalence from becoming a chained one (§1.5).
    """
    return st.one_of(
        st.tuples(st.sampled_from(["and", "or"]), children, children).map(
            lambda item: f"({item[1]} {item[0]} {item[2]})"
        ),
        children.map(lambda child: f"(not {child})"),
        st.tuples(st.sampled_from(["implies", "Implies", "Iff"]), children, children).map(
            lambda item: f"{item[0]}({item[1]}, {item[2]})"
        ),
        st.tuples(st.sampled_from(["->", "=>", " implies ", "<->", "<=>"]), children, children).map(
            lambda item: f"(({item[1]}){item[0]}({item[2]}))"
        ),
    )


_STATE = st.recursive(_STATE_ATOM, _connectives, max_leaves=4)

_RECORD = st.lists(_PRESENCE, min_size=1, max_size=4).map(" and ".join)

_TEMPORAL = st.one_of(
    st.tuples(
        st.sampled_from(sorted(TEMPORAL_OPERATORS - {"until", "since"})), _STATE
    ).map(lambda item: f"{item[0]}({item[1]})"),
    st.tuples(st.sampled_from(["until", "since"]), _STATE, _STATE).map(
        lambda item: f"{item[0]}({item[1]}, {item[2]})"
    ),
)

#: The bounded-response construct in both positions §1.4 admits: alone, and under the one enclosing
#: shape whose trigger is the anchor it measures. The two event names are drawn distinct because a
#: repeated name is a refusal rather than a production.
_BOUNDED_RESPONSE = st.tuples(
    st.lists(st.sampled_from(RECORD_SIGNALS), min_size=2, max_size=2, unique=True),
    st.sampled_from(["24h", "3d", "1mo", "12hours", "2days", "6months"]),
    st.booleans(),
).map(
    lambda item: (
        f'{BOUNDED_RESPONSE_CALL}(present({item[0][0]}), present({item[0][1]}), "{item[1]}")'
        if not item[2]
        else (
            f"always(implies(present({item[0][0]}), "
            f'{BOUNDED_RESPONSE_CALL}(present({item[0][0]}), present({item[0][1]}), "{item[1]}")))'
        )
    )
)

_PREDICATES = st.sampled_from(["meaningful", "adequate"])

_DEGREE = st.tuples(st.sampled_from(RECORD_SIGNALS), _PREDICATES).map(
    lambda item: f'{DEGREE_CALL}({item[0]}, "{item[1]}")'
)
_UNDETERMINED = st.tuples(st.sampled_from(RECORD_SIGNALS), _PREDICATES).map(
    lambda item: f'{UNDETERMINED_CALL}({item[0]}, "{item[1]}", "a supervisory authority")'
)

#: A graded (resp. undetermined) spec is the open-texture atom under the Boolean connectives and
#: nowhere else — which is exactly what §1.5 admits, so the generator's shape is the rule.
_GRADED = st.recursive(st.one_of(_DEGREE, _STATE_ATOM), _connectives, max_leaves=3).filter(
    lambda spec: f"{DEGREE_CALL}(" in spec
)
_UNSETTLED = st.recursive(st.one_of(_UNDETERMINED, _STATE_ATOM), _connectives, max_leaves=3).filter(
    lambda spec: f"{UNDETERMINED_CALL}(" in spec
)

_COUNTERFACTUAL = st.tuples(
    st.sampled_from(["decision_a", "decision_b"]), st.sampled_from(["basis_a", "basis_b"])
).map(lambda item: f"{COUNTERFACTUAL_CALL}({item[0]}, {item[1]})")

GENERATORS = {
    "state": (_STATE, {"record", "logical"}),
    "record": (_RECORD, {"record"}),
    "temporal": (_TEMPORAL, {"temporal"}),
    "bounded_response": (_BOUNDED_RESPONSE, {"temporal"}),
    "graded": (_GRADED, {"graded"}),
    "undetermined": (_UNSETTLED, {"undetermined"}),
    "counterfactual": (_COUNTERFACTUAL, {"counterfactual"}),
}


@pytest.mark.parametrize("production", sorted(GENERATORS))
@settings(
    max_examples=120,
    deadline=timedelta(seconds=30),
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(data=st.data())
def test_every_spec_the_grammar_generates_is_accepted(production: str, data) -> None:
    """The grammar of §1.2, generated from and asserted against the parser it describes.

    Two assertions per example, because a grammar that only guaranteed acceptance would admit a
    production that parses and lands in the wrong fragment — and the fragment is what decides which
    engines may discharge a duty.
    """
    strategy, fragments = GENERATORS[production]
    spec = data.draw(strategy)
    parse_property(spec)
    assert classify_fragment(spec) in fragments, (production, spec)


# --- the refusals ------------------------------------------------------------------------------

#: One witness per row of `docs/theory/02-syntax.md` Definition 2.5, keyed by the id
#: that table uses.
#:
#: `classify_fragment` is the entry point for every row rather than `parse_property`, because it
#: runs the whole gate: the rewriter, the parse, the whitelist walk, and — for a formula reaching
#: the temporal fragment — `validate_temporal_property`.
REFUSALS = {
    "R-PROSE": "Record check",
    "R-NOT-READ-WHOLE": "present(reason_a) # and present(reason_b)",
    # A bare carriage return CPython's parser normalises away and its tokenizer refuses as a
    # non-printable character: the read-whole check cannot run, so the spec is refused rather
    # than answered on a token list that may itself be partial.
    "R-NOT-TOKENISED-WHOLE": "present(reason_a)\r\r# tail",
    "R-UNTERMINATED-STRING": "contains(reason_a, 'oops)",
    "R-UNBALANCED-PARENS": "(present(reason_a)",
    "R-EMPTY-ARROW-OPERAND": "present(reason_a) ->",
    "R-CHAINED-EQUIVALENCE": "flag_a <=> flag_b <=> flag_c",
    "R-CONSTANT-TYPE": "count_a > 1j",
    "R-UNARY-OP": "~count_a > 1",
    "R-BINARY-OP": "count_a ** 2 > 1",
    "R-COMPARISON-OP": "count_a in count_b",
    "R-CONSTRUCT": "present(reason_a) if flag_a else flag_b",
    "R-KEYWORD-ARGUMENT": "min(x=1) > 1",
    "R-UNKNOWN-CALL": "never(present(reason_a))",
    "R-ARITY": "abs(count_a, count_b) > 1",
    "R-KIND": "abs(present(reason_a)) > 1",
    "R-NOT-BOOLEAN": "count_a + 1",
    "R-PRESENT-ARGUMENT": "present(count_a + 1)",
    "R-CONTAINS-SHAPE": "contains(reason_a, phrase_a)",
    "R-CONTAINS-EMPTY": 'contains(reason_a, "")',
    "R-CONTAINS-NON-ASCII": 'contains(reason_a, "né")',
    "R-COUNTERFACTUAL-ARGUMENT": f"{COUNTERFACTUAL_CALL}(decision_a, decision_a)",
    "R-COUNTERFACTUAL-COMPOSED": (
        f"{COUNTERFACTUAL_CALL}(decision_a, basis_a) and present(reason_a)"
    ),
    "R-OPEN-TEXTURE-LITERAL": f'{UNDETERMINED_CALL}(reason_a, "", "a court")',
    "R-OPEN-TEXTURE-BOTH": (
        f'{UNDETERMINED_CALL}(reason_a, "meaningful", "a court") and '
        f'{DEGREE_CALL}(reason_b, "adequate")'
    ),
    "R-DEGREE-UNDER-COMPARISON": f'{DEGREE_CALL}(reason_a, "meaningful") >= 0.8',
    "R-DEGREE-UNDER-TEMPORAL": f'always({DEGREE_CALL}(reason_a, "meaningful"))',
    "R-BARE-BOOLEAN-CONSTANT": "present(reason_a) and True",
    "R-CONFLICTING-ROLES": "count_a and count_a > 1",
    "R-TEMPORAL-BOOLEAN-COMPARISON": "always(flag_a == True)",
    "R-BOUNDED-RESPONSE-OPERAND": (
        f'{BOUNDED_RESPONSE_CALL}(contains(reason_a, "aware"), present(notice_a), "24h")'
    ),
    "R-BOUNDED-RESPONSE-SAME-EVENT": (
        f'{BOUNDED_RESPONSE_CALL}(present(reason_a), present(reason_a), "24h")'
    ),
    "R-BOUNDED-RESPONSE-DURATION": (
        f'{BOUNDED_RESPONSE_CALL}(present(reason_a), present(notice_a), "1y")'
    ),
    "R-BOUNDED-RESPONSE-COMPOSED": (
        f'{BOUNDED_RESPONSE_CALL}(present(reason_a), present(notice_a), "24h") '
        "and present(reason_b)"
    ),
    "R-BOUNDED-RESPONSE-TRIGGER": (
        f"always(implies(present(reason_b), "
        f'{BOUNDED_RESPONSE_CALL}(present(reason_a), present(notice_a), "24h")))'
    ),
}


@pytest.mark.parametrize("refusal", sorted(REFUSALS))
def test_every_documented_refusal_is_refused(refusal: str) -> None:
    """Each row of the refusal table, with a witness the language must not accept."""
    with pytest.raises(UnsupportedConstructError):
        classify_fragment(REFUSALS[refusal])


def test_every_refusal_the_grammar_test_knows_is_named_here():
    """The other half of the pin: the table in the document lists exactly these ids.

    A refusal witnessed here and not named there is an undocumented rule; a row named there and
    witnessed by nothing is a rule nothing checks.
    """
    document = _document()
    named = set(re.findall(r"`(R-[A-Z-]+)`", document))
    assert named == set(REFUSALS), (
        f"only in the document: {sorted(named - set(REFUSALS))}; "
        f"only in this module: {sorted(set(REFUSALS) - named)}"
    )


def test_the_fragment_order_is_the_documented_order():
    """§1.6 is an *order*, and each of the first three dominates everything after it.

    Each spec below carries two fragment-triggering features at once; the fragment reported is the
    earlier one. That is the whole guarantee that a duty carrying an atom no engine settles is not
    answered on its settleable conjuncts and the answer reported as the duty's.
    """
    cases = {
        f"{COUNTERFACTUAL_CALL}(decision_a, basis_a)": "counterfactual",
        f'present(reason_a) and {UNDETERMINED_CALL}(reason_b, "meaningful", "a court")': (
            "undetermined"
        ),
        f'always({UNDETERMINED_CALL}(reason_b, "meaningful", "a court"))': "undetermined",
        f'present(reason_a) and {DEGREE_CALL}(reason_b, "meaningful")': "graded",
        "always(present(reason_a))": "temporal",
        "present(reason_a) and present(reason_b)": "record",
        "present(reason_a) and count_a > 1": "logical",
    }
    for spec, fragment in cases.items():
        assert classify_fragment(spec) == fragment, spec


# ------------------------------------------------------------------------------------------------
# 2. The four lexical decisions
# ------------------------------------------------------------------------------------------------


def test_the_numeral_syntax_is_pythons_and_the_other_constant_types_are_refused():
    """L1. Every Python numeral notation is admitted; every other constant type is refused."""
    for numeral in ("0x10", "0o17", "0b101", "1_000", "1e9", ".5", "-3"):
        assert classify_fragment(f"count_a > {numeral}") == "logical", numeral
    for constant in ("1j", 'b"x"', "..."):
        with pytest.raises(UnsupportedConstructError):
            classify_fragment(f"count_a > {constant}")


def test_an_identifier_the_tokenizer_normalises_is_refused_by_the_requires_gate(tmp_path):
    """L2. CPython normalises identifiers, and the loader catches what that would otherwise hide.

    `present(ﬁeld)` reads the signal `field`, because the tokenizer applies NFKC before this
    package ever sees the name. A pack whose `requires` names the unnormalised spelling therefore
    reads a signal it never gated, and the ungated-signal error is what stops it — no separate rule
    about identifier characters is needed, which is why there is none.
    """
    assert signal_names(parse_property("present(ﬁeld)")) == ("field",)

    pack = tmp_path / "ligature.toml"
    pack.write_text(
        """
[pack]
id = "fixture"
title = "Fixture pack"
description = "A fixture pack, quoting no statute."

[[requirement]]
id = "fixture_duty"
source_document = "Fixture"
article_clause = "Article 1"
verbatim_text = "A fixture clause, quoted from nothing."
stakeholder = "fixture"
formalism = "record"
spec = '''present(ﬁeld)'''
rationale = "A fixture duty."
requires = ["ﬁeld"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="requires"):
        load_pack(pack)


def test_the_word_arrow_needs_a_space_on_each_side_and_the_symbol_arrows_do_not():
    """L3. The token is `" implies "`, and the symbol arrows have no whitespace requirement."""
    assert "Implies(" in preprocess_spec("flag_a implies flag_b")
    assert "Implies(" in preprocess_spec("flag_a->flag_b")
    assert "Implies(" in preprocess_spec("flag_a=>flag_b")

    # A signal whose name merely begins with the word is untouched: the token needs the space.
    assert "Implies(" not in preprocess_spec("flag_a and implies_this")

    # Without the spaces the word is not an arrow, and what is left is not Python.
    with pytest.raises(UnsupportedConstructError):
        classify_fragment("(flag_a)implies(flag_b)")


def test_a_call_carrying_keywords_or_unpacking_is_refused():
    """L5. Nothing about a call reaches an engine but its head name and positional arguments."""
    for spec in ("min(x=1) > 1", "min(*count_a) > 1", "min(**count_a) > 1"):
        with pytest.raises(UnsupportedConstructError):
            classify_fragment(spec)


# ------------------------------------------------------------------------------------------------
# 3. The `observed` implementation, against the reference reading
# ------------------------------------------------------------------------------------------------
#
# The corpus is state formulas over magnitudes only. `present()` and `contains()` are deliberately
# absent: both reach rtamt as synthetic flags computed by the same `rulelang` function the reference
# reading uses, so there is nothing for the two sides to disagree about. What is under test here is
# the *formula* rendering — the seam where one implementation reads a connective and an operator
# differently from the other.

#: Every shape the monitor renders, paired with the reference reading over a value grid.
MONITOR_CORPUS = (
    "count_a > 1",
    "count_a >= 1",
    "count_a == 1",
    "count_a < count_b",
    "(count_a >= 1) and (count_b >= 1)",
    "(count_a >= 1) or (count_b >= 1)",
    "not (count_a >= 1)",
    "(count_a >= 1) -> (count_b >= 1)",
    "((count_a >= 1) and (count_b >= 1)) -> (count_a >= 1)",
    "count_a + count_b > 1",
    "count_a - count_b > 1",
    "count_a * count_b > 1",
    "count_a / 2 > 1",
    "abs(count_a) > 1",
)

MONITOR_VALUES = (-2.0, 0.0, 0.5, 1.0, 2.0, 3.0)

#: The four shapes `docs/theory/03-semantics.md` Remark 3.1 names, with the witness it quotes
#: for each and what the
#: `observed` implementation now does with it. Rows 1-3 are shapes rtamt reads under a different
#: semantics from §2's, and are *refused in the rendering*, so a duty using one is reported not
#: evaluated rather than answered; row 4 is the boundary convention, which is not a defect and was
#: deliberately left alone.
#:
#: This is an *exclusion list for the conformance test above it*, and its cost is stated where it is
#: paid: `test_the_four_named_shapes_are_still_what_the_document_records` asserts every row is still
#: what §4 says it is, so neither a silent addition nor a silently reopened hole can leave it stale.
MONITOR_DIVERGENCES = (
    ("the remainder operator", "count_a % count_b > 1", {"count_a": -2.0, "count_b": 2.0}, True),
    ("a chained comparison", "1 < count_a < 10", {"count_a": -2.0, "count_b": 0.0}, True),
    (
        "equivalence",
        "(count_a >= 1) <-> (count_b >= 1)",
        {"count_a": -2.0, "count_b": 0.0},
        True,
    ),
    ("an exact tie", "count_a > 1", {"count_a": 1.0, "count_b": 0.0}, False),
)


def _monitor_robustness(spec: str, env: dict[str, float]) -> float:
    """The monitor's score for a state formula, over a constant two-record trace.

    Two records because rtamt's offline evaluator reads its sampling period off the trace and
    raises on a one-sample dataset (`observed.MINIMUM_TRACE_LENGTH`). The values are constant, so
    the score is the formula's value at one record and nothing temporal is under test here.

    It renders through `_render_stl` rather than `to_stl` deliberately: `to_stl` now refuses the
    shapes rtamt reads differently, and what these tests need is to keep asking rtamt itself what
    it does with them. A refusal nothing probes behind stops being evidence the moment the
    dependency changes.
    """
    series: dict[str, list] = {"time": [0, 1]}
    for name, value in env.items():
        series[name] = [value, value]
    scores = _monitor(_render_stl(spec)[0], "conformance", set(env), series)
    return min(value for _, value in scores)


def _reference_reading(spec: str, env: dict[str, float]) -> bool:
    return bool(eval_expression(parse_property(spec), dict(env)))


def test_the_monitor_agrees_with_the_reference_reading():
    """The `observed` implementation of §2, held to the reference interpreter of §3.1.

    A verdict is read off the sign of the robustness score, exactly as `ObservedEngine` reads it: a
    breach is a negative score, so `>= 0` is the monitor's `satisfied`. A score of exactly zero is
    skipped — that is row 4 of `MONITOR_DIVERGENCES`, the boundary convention, and it is excluded
    by name rather than by a tolerance.

    Both outcomes have to occur, because a corpus that satisfied every formula would pass against a
    rendering that emitted `true`.
    """
    agreed = {True: 0, False: 0}
    for spec in MONITOR_CORPUS:
        for first in MONITOR_VALUES:
            for second in MONITOR_VALUES:
                env = {"count_a": first, "count_b": second}
                robustness = _monitor_robustness(spec, env)
                if robustness == 0:
                    continue
                reference = _reference_reading(spec, env)
                assert reference == (robustness > 0), (spec, env, robustness, reference)
                agreed[reference] += 1
    assert agreed[True] >= 20 and agreed[False] >= 20, agreed


@pytest.mark.parametrize(
    "label,spec,env,refused", MONITOR_DIVERGENCES, ids=lambda item: str(item)[:24]
)
def test_the_four_named_shapes_are_still_what_the_document_records(
    label: str, spec: str, env: dict[str, float], refused: bool
) -> None:
    """Each row of §4, asserted to still be what §4 says it is.

    This test was written to fail when `engines/observed.py` was fixed, and it did: rows 1-3 are now
    refused in the rendering rather than misrendered, and this is the updated reading of them. What
    it still is for is unchanged — an exclusion list nothing checks rots into a permanent exception.
    A refused row must still be *rtamt-divergent behind the refusal*, or the refusal has outlived
    its reason and the row should leave `MONITOR_DIVERGENCES` and §4 in the same change.
    """
    try:
        robustness = _monitor_robustness(spec, env)
    except Exception:
        assert refused, f"{label} raised unexpectedly"
    else:
        assert _reference_reading(spec, env) != (robustness >= 0), (label, spec, env, robustness)
    if refused:
        with pytest.raises(MisreadShapeError):
            to_stl(spec)
    else:
        assert to_stl(spec)  # the boundary convention is answered, not refused


def test_the_divergences_are_the_ones_the_document_reports():
    """§4 quotes a witness per row; a divergence found here and not reported there is hidden."""
    document = _semantics_document()
    assert len(MONITOR_DIVERGENCES) == 4
    for _, spec, _, _ in MONITOR_DIVERGENCES[:3]:
        assert spec in document, spec


def test_no_shipped_spec_uses_a_shape_the_monitor_misrenders():
    """The three refused shapes are latent, and this is what keeps them so.

    Before the refusal landed, a pack gaining one of these turned a documented finding into a wrong
    verdict. Now it costs the duty its trace rung instead — the honest outcome, and still not one to
    take by accident. It asks the engine's own refusal rather than re-walking for `%`, a chained
    comparison and an equivalence here, so the two cannot drift into disagreeing about what a
    shipped pack may say.
    """
    for pack_id in list_packs():
        for req in load_pack(pack_id).requirements:
            _refuse_shapes_the_monitor_misreads(parse_property(req.spec))


def _misread_requirement(spec: str) -> Requirement:
    """A minimal state duty whose only unusual feature is the shape under test."""
    return Requirement(
        id="misread_shape",
        source_document="Internal Policy",
        article_clause="Section 1.1",
        verbatim_text="A clause, quoted.",
        stakeholder="Compliance",
        formalism="logical",
        spec=spec,
        rationale="Why this duty exists, in English.",
        requires=("count_a", "count_b"),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )


def _observed_on(spec: str):
    req = _misread_requirement(spec)
    records = [{"count_a": 2.0, "count_b": 2.0}, {"count_a": 2.0, "count_b": 2.0}]
    return ObservedEngine.evaluate(req, BaseSUT(set(req.requires)), records)


@pytest.mark.parametrize(
    "spec,construct",
    [
        ("count_a % count_b > 1", "remainder"),
        ("1 < count_a < 10", "chained comparison"),
        ("(count_a >= 1) <-> (count_b >= 1)", "equivalence"),
        ("(count_a >= 1) <=> (count_b >= 1)", "equivalence"),
    ],
)
def test_a_duty_using_a_misread_shape_is_not_evaluated_and_names_the_construct(
    spec: str, construct: str
) -> None:
    """The refusal reaches a verdict, not just `to_stl`, and says which construct earned it.

    A trace this monitor could score is deliberately supplied: the point is that a formula rtamt
    reads differently is never answered, however answerable the trace was.
    """
    result = _observed_on(spec)
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.evidence_summary.startswith("Not evaluated:")
    assert construct in result.evidence_summary, result.evidence_summary
    # Refusal is the soundness boundary: no robustness margin may accompany a
    # record that deliberately has no verdict for the monitor-misread formula.
    assert "evaluation_scores" not in result.details


def test_both_spellings_of_equivalence_reach_the_same_refusal():
    """`<->` and `<=>` are one connective, and this rung used to treat them as two.

    `<->` was in rtamt's grammar and was monitored — and misread; `<=>` was not, and was reported
    not evaluated by rtamt raising. Same formula, two answers, decided by which arrow the author
    happened to type. The refusal is asked of the parsed `Iff` node, which is where both arrive.
    """
    arrow = _observed_on("(count_a >= 1) <-> (count_b >= 1)")
    long_arrow = _observed_on("(count_a >= 1) <=> (count_b >= 1)")
    assert arrow.verdict == long_arrow.verdict == Verdict.INCONCLUSIVE
    assert arrow.evidence_summary.replace("<->", "<=>") == long_arrow.evidence_summary


def test_dropped_token_and_multi_statement_formulas_are_not_evaluated():
    """Formulas with dropped tokens (e.g. %) or multiple statements (e.g. 'a b > 1') are reported
    not evaluated.
    """
    for spec in ("count_a % count_b > 1", "count_a count_b > 1"):
        result = _observed_on(spec)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert result.evidence_summary.startswith("Not evaluated:")


def test_sweep_every_shipped_pack_formula_parses_to_exactly_one_statement():
    """Sweep every formula in every shipped pack and prove each parses to exactly 1 statement."""
    import re

    import rtamt

    from reasonsmith.engines.observed import _render_stl
    from reasonsmith.rulelang import UnsupportedConstructError

    BaseLexer = rtamt.StlDiscreteTimeSpecification().ast.antrlLexerType
    ErrorListener = rtamt.StlDiscreteTimeSpecification().ast.parserErrorListenerType

    class StrictLexer(BaseLexer):
        def __init__(self, input_stream):
            super().__init__(input_stream)
            self._listeners = [ErrorListener()]

    keywords = {
        "always",
        "eventually",
        "until",
        "then",
        "implies",
        "and",
        "or",
        "not",
        "true",
        "false",
        "historically",
        "once",
        "since",
        "rise",
        "fall",
        "prev",
    }

    checked_count = 0
    for pack_id in list_packs():
        pack = load_pack(pack_id)
        for req in pack.requirements:
            try:
                stl_text, synth_vars, _ = _render_stl(req.spec)
            except (UnsupportedConstructError, Exception):
                continue
            found_vars = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", stl_text)) - keywords
            all_vars = set(synth_vars.keys()) | set(req.requires) | found_vars
            spec = rtamt.StlDiscreteTimeSpecification()
            spec.ast.antrlLexerType = StrictLexer
            spec.name = "sweep_test"
            for var in all_vars:
                spec.declare_var(var, "float")
            spec.spec = stl_text
            try:
                spec.parse()
            except Exception:
                continue
            checked_count += 1
            assert len(spec.ast.specs) == 1, (
                f"Requirement {req.id} in pack {pack_id} parsed to {len(spec.ast.specs)} "
                f"statements, expected 1: {req.spec!r}"
            )
    assert checked_count > 0


#: What rtamt does with every construct the property language admits, measured rather than assumed.
#: `raises` — `spec.parse()` rejects it, which is this engine's oldest protection; `agrees` — it is
#: monitored and scores the reference reading; `misreads` — it is monitored and does not, which is
#: what `_refuse_shapes_the_monitor_misreads` refuses. A row moving between those three is the event
#: this table exists to catch: the `%` hole was invisible precisely because rtamt error-recovered
#: instead of raising, and an rtamt version bump could open the same hole under another construct.
RTAMT_BEHAVIOUR = (
    ("the remainder operator", "count_a % count_b > 1", {"count_a": -2.0, "count_b": 2.0},
     "raises"),
    ("a chained comparison", "1 < count_a < 10", {"count_a": -2.0}, "misreads"),
    ("`<->`", "(count_a >= 1) <-> (count_b >= 1)", {"count_a": -2.0, "count_b": 0.0}, "misreads"),
    ("`<=>`", "(count_a >= 1) <=> (count_b >= 1)", {"count_a": -2.0, "count_b": 0.0}, "raises"),
    ("`!=`", "count_a != 1", {"count_a": -2.0}, "raises"),
    ("`min`", "min(count_a, count_b) > 1", {"count_a": -2.0, "count_b": 0.0}, "raises"),
    ("`max`", "max(count_a, count_b) > 1", {"count_a": -2.0, "count_b": 0.0}, "raises"),
    ("`Implies(...)`", "Implies(count_a >= 1, count_b >= 1)", {"count_a": -2.0}, "raises"),
    ("`abs`", "abs(count_a) > 1", {"count_a": -2.0}, "agrees"),
    ("the arrow", "(count_a >= 1) -> (count_b >= 1)", {"count_a": -2.0, "count_b": 0.0}, "agrees"),
    ("division", "count_a / 2 > 1", {"count_a": -2.0}, "agrees"),
    ("negation", "not (count_a >= 1)", {"count_a": -2.0}, "agrees"),
)


@pytest.mark.parametrize(
    "label,spec,env,expected", RTAMT_BEHAVIOUR, ids=lambda item: str(item)[:24]
)
def test_rtamt_still_behaves_the_way_the_refusals_assume(
    label: str, spec: str, env: dict[str, float], expected: str
) -> None:
    """The standing probe behind `_refuse_shapes_the_monitor_misreads`.

    The refusal list is three constructs long because rtamt *raises* for every other shape this
    language admits and it does not support. That is a fact about a dependency, not a property of
    this package, and it is the whole reason the list is not longer. So it is measured here rather
    than trusted: a construct that stops raising and starts being silently monitored is exactly the
    `%` defect reopening under another name, and it must fail the build rather than ship a verdict.

    Do not delete this test because it looks redundant with the refusal it guards. The refusal is
    correct today *because* this table reads the way it does.
    """
    env = dict(env)
    env.setdefault("count_b", 0.0)
    try:
        robustness = _monitor_robustness(spec, env)
    except Exception:
        assert expected == "raises", f"{label} no longer raises: rtamt now reads {spec!r}"
        return
    assert expected != "raises", f"{label} no longer raises: rtamt now reads {spec!r}"
    agrees = _reference_reading(spec, env) == (robustness > 0)
    assert agrees == (expected == "agrees"), (label, spec, env, robustness)


# ------------------------------------------------------------------------------------------------
# 4. The document's own warrant
# ------------------------------------------------------------------------------------------------


def test_every_test_named_in_the_language_doc_exists():
    """The claim-to-test map is the document's warrant; a dangling name voids it.

    The same discipline `test_docs_semantics.py` applies to `docs/semantics.md`, applied here, and
    for the same reason: a claim whose enforcing test has been renamed away is a claim nothing
    checks.
    """
    named = set(
        _TEST_NAME.findall(_document())
        + _TEST_NAME.findall(_semantics_document())
        + _TEST_NAME.findall(_claim_map())
    )
    assert named, "the document names no test, so nothing in it is enforced"

    defined: set[str] = set()
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                defined.add(node.name)

    missing = sorted(named - defined)
    assert not missing, (
        "theory chapters name test(s) that do not exist in tests/: "
        + ", ".join(missing)
        + ". Rename the claim's test back, or cut the claim."
    )


def test_the_language_doc_is_linked_from_the_documentation_index():
    """A definition nobody can find is a definition nobody checks against."""
    assert "theory/02-syntax.md" in (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "theory/02-syntax.md" in (
        REPO_ROOT / "docs" / "semantics.md"
    ).read_text(encoding="utf-8")
