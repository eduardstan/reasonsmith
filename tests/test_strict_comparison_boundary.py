"""Tests for the Boolean temporal evaluator over finite traces.

What this module is for:
  Verifies that the temporal engine derives its verdict from the Boolean semantics over a
  finite trace rather than from quantitative robustness sign alone. Binds strict comparison
  boundaries, asserts the soundness differential property against rtamt, and tests all ten
  temporal operators.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.rulelang import (
    TEMPORAL_OPERATORS,
    eval_temporal_trace,
    parse_property,
)
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict


def test_strict_comparison_boundary_table():
    """Regression test for strict comparison boundary at robustness zero.

    Checks the four-line table:
      always(b > 0)    b=0.0   -> VIOLATED
      always(b >= 0)   b=0.0   -> SATISFIED
      always(b < 0)    b=0.0   -> VIOLATED
      always(b <= 0)   b=0.0   -> SATISFIED
    """
    cases = [
        ("always(b > 0)", Verdict.VIOLATED),
        ("always(b >= 0)", Verdict.SATISFIED),
        ("always(b < 0)", Verdict.VIOLATED),
        ("always(b <= 0)", Verdict.SATISFIED),
    ]

    sut = BaseSUT({"b"})
    records = [{"b": 0.0}, {"b": 0.0}]

    for spec, expected_verdict in cases:
        req = Requirement(
            id=f"test-{spec}",
            source_document="test",
            article_clause="test",
            verbatim_text="test",
            stakeholder="test",
            formalism="temporal",
            spec=spec,
            requires=("b",),
            rationale="strict comparison boundary test",
            binding=True,
            scope="",
            domains=(),
            deontic_type="obligation",
            defeasibility="strict",
        )
        res = ObservedEngine.evaluate(req, sut, records)
        assert res.verdict == expected_verdict, f"Failed for {spec}: got {res.verdict}"
        assert res.strength == Strength.OBSERVED


def test_differential_property_shipped_packs_and_systems():
    """Differential property Part 1: Over all shipped temporal requirements and systems,

    wherever robustness is non-zero (rho != 0), the Boolean fold must agree with sign(rho).
    """
    from reasonsmith.examples.language_model_notices import system_under_test as lm_sut
    from reasonsmith.examples.neural_scorer import system_under_test as neural_sut
    from reasonsmith.examples.probabilistic_scorer import system_under_test as prob_sut
    from reasonsmith.examples.symbolic_rules import system_under_test as sym_sut
    from reasonsmith.examples.truncating_credit_system import (
        system_under_test as trunc_sut,
    )

    systems = [neural_sut(), prob_sut(), sym_sut(), lm_sut(), trunc_sut()]
    packs_dir = Path(__file__).resolve().parents[1] / "src" / "reasonsmith" / "packs"

    for pack_path in sorted(packs_dir.glob("*.toml")):
        pack = load_pack(pack_path.stem)
        for req in pack.requirements:
            if req.formalism != "temporal":
                continue
            for sut in systems:
                records = list(sut.decisions())
                if len(records) < 2:
                    continue

                res = ObservedEngine.evaluate(req, sut, records)
                if res.strength is None:
                    continue

                node = parse_property(req.spec)
                bool_evals = eval_temporal_trace(node, records)
                rob_scores = res.details.get("evaluation_scores", [])

                for t, (_time, rob) in enumerate(rob_scores):
                    b = bool_evals[t]
                    if rob > 0:
                        assert b is True, (
                            f"Disagreement on {req.id} with {sut} at step {t}: rob={rob}, fold={b}"
                        )
                    elif rob < 0:
                        assert b is False, (
                            f"Disagreement on {req.id} with {sut} at step {t}: rob={rob}, fold={b}"
                        )


@settings(deadline=timedelta(seconds=30))
@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=2,
        max_size=10,
    )
)
def test_differential_property_random_traces(trace_tuples: list[tuple[float, float]]):
    """Differential property Part 2: Over hypothesis-generated random traces,

    eval_temporal_trace must agree with sign(rho) whenever rho != 0.
    """
    specs = [
        "always(x > 0.5)",
        "eventually(x < 0.2)",
        "always(x > 0.5 -> y > 0.5)",
        "until(x > 0.5, y > 0.8)",
        "since(x > 0.5, y > 0.8)",
        "historically(x > 0.3)",
        "once(y > 0.7)",
        "next(x > 0.5)",
        "prev(y > 0.5)",
        "rise(x > 0.5)",
        "fall(y > 0.5)",
    ]

    records = [{"x": x, "y": y} for x, y in trace_tuples]
    sut = BaseSUT({"x", "y"})

    for spec_str in specs:
        req = Requirement(
            id="test-spec",
            source_document="test",
            article_clause="test",
            verbatim_text="test",
            stakeholder="test",
            formalism="temporal",
            spec=spec_str,
            requires=("x", "y"),
            rationale="random trace test",
            binding=True,
            scope="",
            domains=(),
            deontic_type="obligation",
            defeasibility="strict",
        )
        res = ObservedEngine.evaluate(req, sut, records)
        if res.strength is None:
            continue

        ast_node = parse_property(spec_str)
        bool_evals = eval_temporal_trace(ast_node, records)
        rob_scores = res.details.get("evaluation_scores", [])

        for t, (_time, rob) in enumerate(rob_scores):
            b = bool_evals[t]
            if rob > 0:
                assert b is True, f"Disagreement on {spec_str} at step {t}: rob={rob}, fold={b}"
            elif rob < 0:
                assert b is False, f"Disagreement on {spec_str} at step {t}: rob={rob}, fold={b}"


def test_all_ten_temporal_operators_covered_and_distinguished():
    """Verify that all 10 temporal operators in TEMPORAL_OPERATORS are supported,

    and each has a test case distinguishing it from its neighbours.
    """
    assert len(TEMPORAL_OPERATORS) == 10
    expected_ops = {
        "always",
        "eventually",
        "next",
        "until",
        "historically",
        "once",
        "prev",
        "since",
        "rise",
        "fall",
    }
    assert TEMPORAL_OPERATORS == expected_ops

    # Trace 1: b is True at step 1 only: [False, True, False]
    r1 = [{"b": False}, {"b": True}, {"b": False}]

    # 1. always vs eventually
    node_always = parse_property("always(b)")
    node_eventually = parse_property("eventually(b)")
    assert eval_temporal_trace(node_always, r1) == [False, False, False]
    assert eval_temporal_trace(node_eventually, r1) == [True, True, False]

    # 2. next vs prev
    node_next = parse_property("next(b)")
    node_prev = parse_property("prev(b)")
    assert eval_temporal_trace(node_next, r1) == [True, False, True]
    assert eval_temporal_trace(node_prev, r1) == [True, False, True]
    # Distinguish next and prev on asymmetrical trace: [True, False, False]
    r_asym = [{"b": True}, {"b": False}, {"b": False}]
    assert eval_temporal_trace(node_next, r_asym) == [False, False, True]
    assert eval_temporal_trace(node_prev, r_asym) == [True, True, False]

    # 3. historically vs once
    node_hist = parse_property("historically(b)")
    node_once = parse_property("once(b)")
    assert eval_temporal_trace(node_hist, r1) == [False, False, False]
    assert eval_temporal_trace(node_once, r1) == [False, True, True]

    # 4. rise vs fall
    node_rise = parse_property("rise(b)")
    node_fall = parse_property("fall(b)")
    assert eval_temporal_trace(node_rise, r1) == [False, True, False]
    assert eval_temporal_trace(node_fall, r1) == [True, False, True]

    # `rise` at position 0 takes the strong reading — f(-1) is false — while `prev` is the weak
    # previous. On a trace beginning `b = False` both readings give False at position 0, so the
    # boundary needs a trace beginning `b = True` to be pinned at all. This is the witness
    # `docs/theory/03-semantics.md` §2.8 states: `rise(b)` and `b and not prev(b)`
    # part company at position 0.
    r_rise_at_zero = [{"b": True}, {"b": False}]
    node_rise_spelled_out = parse_property("b and not prev(b)")
    assert eval_temporal_trace(node_rise, r_rise_at_zero) == [True, False]
    assert eval_temporal_trace(node_prev, r_rise_at_zero) == [True, True]
    assert eval_temporal_trace(node_rise_spelled_out, r_rise_at_zero) == [False, False]
    assert eval_temporal_trace(node_fall, [{"b": False}, {"b": True}]) == [True, False]

    # 5. until vs since
    node_until = parse_property("until(a, b)")
    node_since = parse_property("since(a, b)")
    r_until_since = [
        {"a": True, "b": False},
        {"a": False, "b": False},
        {"a": False, "b": True},
    ]
    assert eval_temporal_trace(node_until, r_until_since) == [False, False, True]
    r_since = [
        {"a": False, "b": True},
        {"a": True, "b": False},
        {"a": True, "b": False},
    ]
    assert eval_temporal_trace(node_since, r_since) == [True, True, True]
    assert eval_temporal_trace(node_until, r_since) == [True, False, False]


def test_missing_numeric_signal_returns_inconclusive():
    """A temporal requirement over records missing a required numeric signal must return

    INCONCLUSIVE.
    """
    req = Requirement(
        id="test-missing-latency",
        source_document="test",
        article_clause="test",
        verbatim_text="test",
        stakeholder="test",
        formalism="temporal",
        spec="always(latency <= 30)",
        requires=("latency",),
        rationale="missing numeric signal test",
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    sut = BaseSUT({"latency"})
    records = [{"id": 1}, {"id": 2}]
    res = ObservedEngine.evaluate(req, sut, records)
    assert res.strength is None
    assert res.verdict == Verdict.INCONCLUSIVE
    assert "Not evaluated" in res.evidence_summary


def test_unreachable_trigger_antecedent_zero_boundary():
    """Reproduction 1: antecedent b > 0 with b = 0.0 must return INCONCLUSIVE / None."""
    req = Requirement(
        id="test-zero-antecedent",
        source_document="test",
        article_clause="test",
        verbatim_text="test",
        stakeholder="test",
        formalism="temporal",
        spec="always(b > 0 -> c > 0)",
        requires=("b", "c"),
        rationale="antecedent zero boundary test",
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    sut = BaseSUT({"b", "c"})
    records = [{"b": 0.0, "c": 1.0}, {"b": 0.0, "c": 1.0}]
    res = ObservedEngine.evaluate(req, sut, records)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "vacuous_trigger" in res.details


def test_unreachable_trigger_antecedent_negative_boundary():
    """Reproduction 2: antecedent b > 0 with b = -1.0 must return INCONCLUSIVE / None."""
    req = Requirement(
        id="test-negative-antecedent",
        source_document="test",
        article_clause="test",
        verbatim_text="test",
        stakeholder="test",
        formalism="temporal",
        spec="always(b > 0 -> c > 0)",
        requires=("b", "c"),
        rationale="antecedent negative boundary test",
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    sut = BaseSUT({"b", "c"})
    records = [{"b": -1.0, "c": 1.0}, {"b": -1.0, "c": 1.0}]
    res = ObservedEngine.evaluate(req, sut, records)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "vacuous_trigger" in res.details


def test_unknown_antecedent_returns_inconclusive():
    """Antecedent never true and unknown somewhere must return INCONCLUSIVE / None."""
    req = Requirement(
        id="test-unknown-antecedent",
        source_document="test",
        article_clause="test",
        verbatim_text="test",
        stakeholder="test",
        formalism="temporal",
        spec="always(b > 0 -> c > 0)",
        requires=("b", "c"),
        rationale="unknown antecedent test",
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    sut = BaseSUT({"b", "c"})
    records = [{"c": 1.0}, {"c": 1.0}]
    res = ObservedEngine.evaluate(req, sut, records)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "Not evaluated" in res.evidence_summary


def test_negative_zero_antecedent_robustness_cannot_slip_through():
    """Assert directly that the vacuity guard fires for an antecedent whose robustness is -0.0."""
    req = Requirement(
        id="test-negative-zero-antecedent",
        source_document="test",
        article_clause="test",
        verbatim_text="test",
        stakeholder="test",
        formalism="temporal",
        spec="always(b > 0 -> c > 0)",
        requires=("b", "c"),
        rationale="negative zero antecedent test",
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    sut = BaseSUT({"b", "c"})
    records = [{"b": -0.0, "c": 1.0}, {"b": -0.0, "c": 1.0}]
    res = ObservedEngine.evaluate(req, sut, records)
    assert res.verdict == Verdict.INCONCLUSIVE
    assert res.strength is None
    assert "vacuous_trigger" in res.details

