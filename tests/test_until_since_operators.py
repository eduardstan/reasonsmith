"""Tests for the two binary temporal operators of the property language.

What this module is for:
  `until` and `since` are prefix calls in this language and infix operators in rtamt, which has
  parsed both all along. Everything this package adds is the mapping between the two spellings, so
  what these tests pin is the mapping: that the loader accepts a spec using one, that
  `classify_fragment` puts it in the `temporal` fragment, and above all that the text `to_stl`
  produces is text rtamt actually parses and monitors. Nothing here tests temporal semantics —
  the monitor owns that, and this package must never grow a second implementation of it.

What a reader must not break:
  - The shipped duty is loaded from the pack, never re-written here. A test authoring its own spec
    would pass while the pack said something else.
  - `since` is exercised even though no shipped duty uses it. It was added as the dual of `until`
    by an explicit decision rather than on the evidence of a clause (`ROADMAP.md` §2), so nothing
    but a test stands between it and rotting unrendered.
"""

from __future__ import annotations

import pytest

from reasonsmith.engines.observed import _monitor, to_stl
from reasonsmith.report import evaluate_requirement
from reasonsmith.rulelang import (
    BINARY_TEMPORAL_OPERATORS,
    TEMPORAL_OPERATORS,
    UnsupportedConstructError,
    classify_fragment,
    parse_property,
)
from reasonsmith.spec import load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

INCOMPLETENESS_DUTY = "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out"

NOTICE = "artifact_logs_incompleteness_notice_sent"
ACTION = "artifact_logs_action_taken_notification"
LAPSED = "artifact_logs_response_period_lapsed"


def creditor() -> BaseSUT:
    sut = BaseSUT({NOTICE, ACTION, LAPSED})
    sut.system_domains = ("consumer-credit",)
    return sut


def requirement():
    return load_pack("ecoa").get_requirement(INCOMPLETENESS_DUTY)


def test_the_binary_operators_are_temporal_operators_of_the_language():
    assert BINARY_TEMPORAL_OPERATORS == {"until", "since"}
    assert BINARY_TEMPORAL_OPERATORS <= TEMPORAL_OPERATORS


@pytest.mark.parametrize("operator", sorted(BINARY_TEMPORAL_OPERATORS))
def test_a_binary_temporal_spec_classifies_as_temporal(operator: str):
    assert classify_fragment(f"{operator}(present(a), present(b))") == "temporal"


@pytest.mark.parametrize("operator", sorted(BINARY_TEMPORAL_OPERATORS))
def test_the_arity_check_reaches_the_binary_operators(operator: str):
    """The one-operand check the unary operators get, at the arity these two take."""
    for spec in (f"{operator}(present(a))", f"{operator}(present(a), present(b), present(c))"):
        with pytest.raises(UnsupportedConstructError, match="operand"):
            parse_property(spec)


@pytest.mark.parametrize("operator", sorted(BINARY_TEMPORAL_OPERATORS))
def test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it(operator: str):
    """The mapping is the risky part of this feature, so it is pinned end to end.

    Rendering to a string that merely looks like rtamt's syntax proves nothing; the monitor is
    what decides, so the rendered text is handed to it over a trace.
    """
    stl = to_stl(f"{operator}(x >= 1, y >= 1)")
    assert stl == f"((x >= 1) {operator} ( y >= 1))"
    scores = _monitor(
        stl,
        f"spec_{operator}",
        {"x", "y"},
        {"time": [0.0, 1.0, 2.0], "x": [2.0, 2.0, 2.0], "y": [0.0, 0.0, 2.0]},
    )
    assert [robustness > 0 for _t, robustness in scores] == (
        [True, True, True] if operator == "until" else [False, False, True]
    )


def test_a_quoted_call_head_is_not_rewritten():
    """`contains(reason, "until(x)")` forbids a phrase; it does not state a temporal property."""
    rendered = to_stl('contains(reason, "until(x)")')
    assert "until" not in rendered.replace("__reasonsmith", "")


def test_the_shipped_incompleteness_duty_uses_until():
    req = requirement()
    assert req.formalism == "temporal"
    assert "until(" in req.spec
    assert req.requires == (NOTICE,)
    assert req.defeasibility == "defeasible-modelled"


def test_a_notice_ended_by_action_or_by_the_period_lapsing_is_satisfied():
    """The two endings 12 CFR 1002.9(c)(2) itself names, one per trace."""
    for ending in (ACTION, LAPSED):
        records = [
            {NOTICE: "application 8812, further information requested"},
            {NOTICE: "application 8812, further information requested", ending: "yes"},
        ]
        result = evaluate_requirement(requirement(), creditor(), records)
        assert result.verdict == Verdict.SATISFIED, ending
        assert result.strength == Strength.OBSERVED, ending


def test_a_notice_that_never_ends_is_violated():
    """A creditor that sent the notice and then neither acted nor let the period run out."""
    records = [
        {NOTICE: "application 8812, further information requested"},
        {NOTICE: "application 8812, further information requested"},
    ]
    result = evaluate_requirement(requirement(), creditor(), records)
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED
