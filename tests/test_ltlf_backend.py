"""Tests for the finite-trace decision procedure behind `validate-pack --analyse`.

What this module is for:
  `src/reasonsmith/ltlf.py` is a syntax mapping onto a published LTLf decision procedure and an
  emptiness question, exactly as `engines/observed.to_stl` is a syntax mapping onto rtamt. So what
  these tests pin is the mapping and its edges, never temporal semantics — the installed procedure
  owns those and this package must never grow a second implementation of them.

  The centre of the module is `test_the_ltlf_backend_agrees_with_the_monitor`, and it is the
  acceptance criterion for the whole backend rather than an extra. Two backends able to disagree
  about the same shipped duty is the defect `docs/semantics.md` §2 already guards for `contains()`
  with `test_the_solvers_fold_is_the_interpreters_fold`, and this is that test's shape: a generated
  corpus of traces, both backends asked, and a failure the moment they part.

What a reader must not break:
  - The duties are loaded from the shipped packs, never re-written here. A test authoring its own
    spec would pass while the pack said something else.
  - The differential test counts the comparisons it actually made and fails if that count collapses
    — the same guard `test_the_unreachable_trigger_case_is_actually_exercised` puts on its own
    agreement, because a differential test that silently compares nothing passes forever.
"""

from __future__ import annotations

import ast
import random

import pytest

from reasonsmith import ltlf
from reasonsmith.analysis import analyse_pack
from reasonsmith.engines.observed import MINIMUM_TRACE_LENGTH, ObservedEngine
from reasonsmith.rulelang import (
    CONTAINS_CALL,
    PRESENCE_CALL,
    UnsupportedConstructError,
    eval_expression,
    measured_magnitude_names,
    parse_property,
    signal_names,
)
from reasonsmith.spec import Requirement, list_packs, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Verdict

pytestmark = pytest.mark.skipif(
    not ltlf.available(), reason="the optional `ltlf` extra is not installed"
)

INCOMPLETENESS_DUTY = "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out"


def temporal_requirements() -> list[Requirement]:
    return [
        req
        for pack_id in list_packs()
        for req in load_pack(pack_id).requirements
        if req.formalism == "temporal"
    ]


# --------------------------------------------------------------------------------------------
# The mapping
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("always(present(a))", "G(p0)"),
        ("eventually(present(a))", "F(p0)"),
        ("next(present(a))", "X(p0)"),
        ("until(present(a), present(b))", "(p0 U p1)"),
        ("always(present(a) -> present(b))", "G((p0 -> p1))"),
        ("always(present(a) and present(b))", "G((p0 & p1))"),
        ("always(present(a) or present(b))", "G((p0 | p1))"),
        ("always(not present(a))", "G(!(p0))"),
    ],
)
def test_each_operator_of_the_fragment_has_one_ltlf_spelling(spec: str, expected: str):
    assert ltlf.to_ltlf(spec, ltlf.Abstraction()) == expected


def test_the_same_subexpression_is_the_same_atom_across_a_pack():
    """What makes an entailment between two requirements mean anything at all."""
    shared = ltlf.Abstraction()
    left = ltlf.to_ltlf("always(present(a) and present(b))", shared)
    right = ltlf.to_ltlf("always(present(b))", shared)
    assert left == "G((p0 & p1))"
    assert right == "G(p1)"
    assert ltlf.entails(left, right, shared) is True
    assert ltlf.entails(right, left, shared) is False


def test_the_phrase_atom_carries_the_axiom_the_z3_encoding_carries():
    """`analysis._PackScope` asserts `contains -> present`; so must this, at every position."""
    abstraction = ltlf.Abstraction()
    formula = ltlf.to_ltlf('always(contains(a, "no"))', abstraction)
    phrase_atom = abstraction.atoms["contains(a, 'no')"]
    assert abstraction.axioms == ["G({} -> p1)".format(phrase_atom)]
    assert ltlf.entails(formula, ltlf.to_ltlf("always(present(a))", abstraction), abstraction)


@pytest.mark.parametrize("operator", ["once", "historically", "prev", "since", "rise", "fall"])
def test_a_past_operator_is_skipped_by_name_rather_than_rendered(operator: str):
    """LTLf is the future fragment. Rendering a past operator into a future one would be
    implementing its semantics, which is the one thing this module may not do."""
    arguments = "present(a), present(b)" if operator == "since" else "present(a)"
    with pytest.raises(UnsupportedConstructError, match="past operator"):
        ltlf.to_ltlf(f"always({operator}({arguments}))", ltlf.Abstraction())


def test_the_mapping_has_no_case_the_property_language_cannot_reach():
    """A bare Boolean constant is refused by the language, so the mapping carries no spelling for
    one — a case here would answer about a `spec` nobody can write."""
    with pytest.raises(UnsupportedConstructError, match="Boolean constant"):
        ltlf.to_ltlf("always(True)", ltlf.Abstraction())


def test_the_mapping_is_closed_and_refuses_anything_it_has_no_spelling_for():
    """The default is a refusal, not a guess.

    `parse_property` already refuses every construct outside the language, so no shipped or
    authorable `spec` reaches this branch. It is asserted against the renderer directly because
    "the mapping has a case for everything the language admits" is only a guarantee while
    anything else raises rather than falling through to something plausible.
    """
    with pytest.raises(UnsupportedConstructError, match="no LTLf spelling"):
        ltlf._render(ast.parse("unknown_operator(a)", mode="eval").body, ltlf.Abstraction())


def test_the_counterfactual_atom_reaches_no_trace_logic():
    """The refusal lives in the mapping, not in the caller that happens not to pass one.

    `_temporal_analysis` only ever hands this the `temporal` fragment, so nothing in the analysis
    reaches it today — which is exactly why it is asserted here. A property of a pair of executions
    is not a property of any trace, and a guarantee kept only by the caller is a convention.
    """
    with pytest.raises(UnsupportedConstructError, match="pair of executions"):
        ltlf.to_ltlf(
            "counterfactually_invariant(decision, applicant_prohibited_basis)",
            ltlf.Abstraction(),
        )


# --------------------------------------------------------------------------------------------
# The decision procedure's edges
# --------------------------------------------------------------------------------------------


def test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable():
    """`flloat` admits the empty trace, on which every `always(f)` holds whatever `f` says.

    Without `NON_EMPTY` every `always` duty in every pack would be reported satisfiable by a trace
    no monitor ever reads, which is a clean bill of health nothing earned.
    """
    abstraction = ltlf.Abstraction()
    formula = ltlf.to_ltlf("always(present(a) and not present(a))", abstraction)
    assert ltlf.accepts(formula, []) is True
    assert ltlf.satisfiable([formula], abstraction) is False


def test_a_contradictory_pair_of_temporal_duties_is_reported_unsatisfiable_together():
    abstraction = ltlf.Abstraction()
    left = ltlf.to_ltlf("always(present(a))", abstraction)
    right = ltlf.to_ltlf("eventually(not present(a))", abstraction)
    assert ltlf.satisfiable([left], abstraction) is True
    assert ltlf.satisfiable([right], abstraction) is True
    assert ltlf.satisfiable([left, right], abstraction) is False


def test_a_question_over_the_atom_budget_is_refused_by_name():
    """The installed procedure's ceiling is refused before the automaton is built, not after.

    There is no wall clock anywhere in this package, so a question it cannot finish has to be
    turned away on a count rather than on a timeout.
    """
    abstraction = ltlf.Abstraction()
    spec = "always(" + " and ".join(f"present(s{i})" for i in range(ltlf.ATOM_BUDGET + 1)) + ")"
    formula = ltlf.to_ltlf(spec, abstraction)
    assert ltlf.atom_count(formula) == ltlf.ATOM_BUDGET + 1
    with pytest.raises(UnsupportedConstructError, match="propositional atoms"):
        ltlf.satisfiable([formula], abstraction)


# --------------------------------------------------------------------------------------------
# The differential test — the acceptance criterion
# --------------------------------------------------------------------------------------------


def _atom_values(abstraction: ltlf.Abstraction, record: dict[str, object]) -> dict[str, bool]:
    """What each abstracted atom is worth in one decision record.

    The atoms are evaluated by `rulelang.eval_expression` — the reference interpreter both the
    record engine and the replay engine already use — so the valuation the automaton reads is the
    same reading of the record rtamt's synthetic flags are built from.
    """
    return {
        letter: bool(eval_expression(parse_property(key).body, record))
        for key, letter in abstraction.atoms.items()
    }


def _corpus(req: Requirement, rng: random.Random, traces: int) -> list[list[dict[str, object]]]:
    """Random decision traces over exactly the signals one duty reads.

    A presence signal is either a recorded statement or absent; a magnitude is a number drawn
    around the constants the duty compares against, so the corpus straddles every boundary the
    property has rather than sitting on one side of all of them.
    """
    node = parse_property(req.spec)
    magnitudes = set(measured_magnitude_names(node))
    presences = {
        ast.unparse(call.args[0])
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and getattr(call.func, "id", "") in (PRESENCE_CALL, CONTAINS_CALL)
    }
    constants = sorted(
        {
            float(constant.value)
            for constant in ast.walk(node)
            if isinstance(constant, ast.Constant) and isinstance(constant.value, (int, float))
        }
        or {1.0}
    )

    def record() -> dict[str, object]:
        values: dict[str, object] = {}
        for name in sorted(magnitudes):
            around = rng.choice(constants)
            values[name] = around + rng.choice([-1.0, 0.0, 1.0])
        for name in sorted(presences):
            if rng.random() < 0.6:
                values[name] = f"{name} recorded"
        for name in signal_names(node):
            values.setdefault(name, rng.choice([0.0, 1.0]))
        return values

    return [
        [record() for _ in range(rng.randint(MINIMUM_TRACE_LENGTH, 5))] for _ in range(traces)
    ]


def test_the_ltlf_backend_agrees_with_the_monitor():
    """The two backends must not be able to disagree about a shipped duty.

    rtamt scores robustness over real-valued signals; the LTLf procedure accepts or rejects a word
    over the abstracted atoms. They answer the same question about the same trace only while the
    syntax mapping in `ltlf.to_ltlf` renders the operators the way `observed.to_stl` renders them,
    which is the thing that can silently rot — a `until` spelled as a `release`, an `always` that
    lost a position, an implication rendered the wrong way round. This walks a generated corpus of
    traces per shipped temporal duty and fails at the first trace on which they part.

    Only the definite verdicts are compared. rtamt reports NOT EVALUATED for a short trace, an
    unmeasured magnitude or an antecedent that fired nowhere; on those the monitor made no claim,
    so there is nothing for the automaton to agree or disagree with. The comparisons that did
    happen are counted, because a differential test that quietly compares nothing passes forever.
    """
    rng = random.Random(20260804)
    seen: list[Verdict] = []
    for req in temporal_requirements():
        abstraction = ltlf.Abstraction()
        formula = ltlf.to_ltlf(req.spec, abstraction)
        signals = set(signal_names(parse_property(req.spec)))
        sut = BaseSUT(signals)
        sut.system_domains = tuple(req.domains)
        for records in _corpus(req, rng, traces=12):
            monitor = ObservedEngine.evaluate(req, sut, records)
            if monitor.verdict not in (Verdict.SATISFIED, Verdict.VIOLATED):
                continue
            automaton_accepts = ltlf.accepts(
                formula, [_atom_values(abstraction, record) for record in records]
            )
            seen.append(monitor.verdict)
            assert automaton_accepts == (monitor.verdict == Verdict.SATISFIED), (
                req.id,
                req.spec,
                formula,
                records,
                monitor.verdict,
            )
    # Both sides of the agreement have to be exercised: a corpus that only ever satisfied every
    # duty would pass against a mapping that renders every formula as `true`.
    assert len(seen) >= 30, f"only {len(seen)} trace(s) reached both backends"
    assert seen.count(Verdict.SATISFIED) >= 10 and seen.count(Verdict.VIOLATED) >= 10, seen


# --------------------------------------------------------------------------------------------
# What the analysis does with it
# --------------------------------------------------------------------------------------------


def test_the_until_duty_is_no_longer_skipped_by_every_question_the_analysis_asks():
    """The measurable outcome. Before this backend the one shipped `until` duty appeared in
    `validate-pack --analyse` only as a reason string saying it had not been reduced."""
    analysis = analyse_pack(load_pack("ecoa"))
    assert analysis.temporal is not None
    assert INCOMPLETENESS_DUTY in analysis.temporal.decided
    assert INCOMPLETENESS_DUTY not in analysis.temporal.unsatisfiable


def test_every_shipped_temporal_duty_is_satisfiable_by_some_non_empty_finite_trace():
    """A duty no trace discharges reports every system violated for a reason that is the pack's."""
    for pack_id in list_packs():
        analysis = analyse_pack(load_pack(pack_id))
        assert analysis.temporal is not None
        assert analysis.temporal.unsatisfiable == (), pack_id


def test_the_analysis_says_so_when_the_extra_is_absent(monkeypatch):
    """The absence of the extra is a note, never a weaker answer wearing the same words."""
    monkeypatch.setattr("reasonsmith.analysis.available", lambda: False)
    analysis = analyse_pack(load_pack("ecoa"))
    assert analysis.temporal is None
    assert ltlf.UNAVAILABLE_NOTE in analysis.notes
    from reasonsmith.analysis import render_analysis

    rendered = render_analysis(analysis)
    assert "\n  temporal: " not in rendered
    assert "temporal entailment" not in rendered
    assert ltlf.LTLF_ABSTRACTION_LIMIT not in rendered
    assert ltlf.UNAVAILABLE_NOTE in rendered


_REQUIREMENT_BLOCK = """
[[requirement]]
id = "{id}"
source_document = "Test"
article_clause = "1"
verbatim_text = "text"
stakeholder = "auditor"
formalism = "temporal"
spec = "{spec}"
rationale = "prose"
requires = ["reason"]
binding = false
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
"""


def test_a_duty_the_procedure_cannot_express_is_skipped_by_name_in_the_analysis(tmp_path):
    """`since` is in this property language and not in LTLf, so the analysis names the duty.

    No shipped pack uses a past operator — `since` was added as `until`'s dual by an explicit
    decision (`ROADMAP.md` §2) — so this is written against a pack of its own. A silent omission
    would read as "nothing found", which is the overclaim `analysis.py` exists to refuse.
    """
    pack_file = tmp_path / "past.toml"
    pack_file.write_text(
        '[pack]\nid = "past"\n'
        + _REQUIREMENT_BLOCK.format(id="past_duty", spec="since(present(reason), present(reason))"),
        encoding="utf-8",
    )
    analysis = analyse_pack(load_pack(pack_file))
    assert analysis.temporal is not None
    assert analysis.temporal.decided == ()
    assert any("past_duty" in reason and "past operator" in reason for reason in analysis.skipped)


def test_a_temporal_duty_no_trace_discharges_is_reported_and_named(tmp_path):
    """The check has to be able to fail, and to name the duty that cannot hold.

    No shipped pack carries such a duty — `test_every_shipped_temporal_duty_is_satisfiable_...`
    is the assertion of that — so the failing side is written against a pack of its own, the way
    `test_a_contradictory_pack_is_reported_unsatisfiable_with_its_core` does for the Z3 questions.
    """
    from reasonsmith.analysis import render_analysis

    pack_file = tmp_path / "impossible.toml"
    pack_file.write_text(
        '[pack]\nid = "impossible"\n'
        + _REQUIREMENT_BLOCK.format(
            id="never_dischargeable", spec="always(present(reason) and not present(reason))"
        ),
        encoding="utf-8",
    )
    analysis = analyse_pack(load_pack(pack_file))
    assert analysis.temporal is not None
    assert analysis.temporal.decided == ("never_dischargeable",)
    assert analysis.temporal.unsatisfiable == ("never_dischargeable",)
    assert "NOT satisfiable: never_dischargeable" in render_analysis(analysis)


def test_a_pair_the_procedure_refuses_never_renders_as_a_pair_it_cleared():
    """"No temporal duty entails another" is a finding; "none was decided" is not one."""
    from reasonsmith.analysis import render_analysis

    rendered = render_analysis(analyse_pack(load_pack("ecoa")))
    assert "not decided either way" in rendered
    assert "no temporal duty entails another" not in rendered
