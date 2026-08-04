"""Tests for the evidence basis: the second coordinate of an evidence claim, beside strength.

What this module is for:
  `unattainable < observed < probed < proved` is a chain, and three shipped duties are not about
  the thing that chain ranks. A counterfactual duty is a property of a *pair* of executions, so no
  trace observes one. A certificate duty is measured against the *inference artefact* behind a
  decision, so no exposure of the system proves one. A graded duty rests on a predicate a named
  *authority* applies, so no rung ranks one at all. Each of those was prose in a module docstring
  and nothing in the result model, the counts or any rendering carried it.

  `verdict.EvidenceBasis` is the classification that carries it, `report.evidence_basis` derives it
  from the duty, and these tests hold the three claims it makes. `docs/semantics.md` §10 is the
  contract and names every test here.

What a reader must not break:
  - **A basis is a kind and never a rank.** The members carry no order, comparing two of them
    raises, and no rendering may draw one as a rung. That is the whole reason this is a second
    dimension rather than a fifth member of the lattice, and
    `test_the_evidence_bases_are_not_ordered` and `test_no_rendering_draws_a_basis_as_a_rung` are
    what hold it.
  - **The basis is derived from the duty, never declared.** Not a pack field, not a system's
    self-description, not a function of which engine answered. A declared basis would let a pack
    author or an adapter widen what a duty can claim, which is the move `_validate_basis` exists to
    refuse.
  - **`BASIS_RUNGS` and `_engine_ladder` must keep agreeing.** The table says which rungs a basis
    admits; the ladder decides which engines actually run. A row widened ahead of an engine turns a
    structural refusal into a comment, and `test_the_basis_admits_exactly_the_rungs_the_ladder_can_
    reach` is the drift check.
  - **No shipped verdict moved.** This describes evidence differently; it measures nothing new.
    `test_the_basis_changed_no_verdict_and_no_strength` is the pin, and it is the constraint the
    whole change was made under.
"""

from __future__ import annotations

import inspect

import pytest

from reasonsmith import render
from reasonsmith import report as report_module
from reasonsmith.manyvalued import Grading, atom_key
from reasonsmith.render import AUDIENCES, basis_sentence
from reasonsmith.report import (
    RequirementResult,
    check_conformance,
    evaluate_requirement,
    evidence_basis,
)
from reasonsmith.spec import Requirement, list_packs, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import BASIS_RUNGS, EvidenceBasis, Strength, Verdict

#: The three shipped duties that are not on the behavioural basis, and the basis each is on. There
#: is no graded one — `test_no_shipped_pack_uses_either_open_texture_construct` keeps it that way —
#: so the `assessment` row is exercised by a fixture below and by no pack.
NON_BEHAVIOURAL = {
    "ecoa_reg_b_1002_9_b_2_principal_reasons_complete": EvidenceBasis.ARTIFACT,
    "ecoa_reg_b_1002_4_a_no_disparate_treatment": EvidenceBasis.RELATIONAL,
}

REASON = "artifact_logs_reason_explanation"


def _all_requirements():
    for name in list_packs():
        for req in load_pack(name).requirements:
            yield req


def _graded_duty() -> Requirement:
    """A graded fixture duty, built directly. No shipped pack has one and none may gain one here."""
    return Requirement(
        id="fixture_graded",
        source_document="Fixture",
        article_clause="Article 1",
        verbatim_text="A fixture clause, quoted from nothing.",
        stakeholder="fixture",
        formalism="graded",
        spec=f'degree({REASON}, "meaningful")',
        rationale="A fixture duty, standing in for a clause nobody has read yet.",
        requires=(REASON,),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
        algebra="lukasiewicz",
    )


def _grading() -> Grading:
    return Grading(
        authority="a three-assessor panel convened for this fixture",
        scale="0 = states no information at all, 1 = states everything the clause asks for",
        method="independent scoring, median taken",
        degrees={atom_key(REASON, "meaningful"): 0.63},
    )


# --------------------------------------------------------------------------------------------
# A kind is not a rank.
# --------------------------------------------------------------------------------------------


def test_the_evidence_bases_are_not_ordered():
    """Comparing two bases raises, so nothing can sort them into a ladder.

    This is the acceptance test of the whole design. The pressure that produced it would have been
    answered by four more members of the strength lattice, and that answer is wrong: `artifact` is
    not more or less than `observed`, it is *about something else*. A comparison that quietly
    answered would let a report rank a certificate duty against a record duty and print the result.
    """
    for left in EvidenceBasis:
        for right in EvidenceBasis:
            for op in ("__lt__", "__le__", "__gt__", "__ge__"):
                with pytest.raises(TypeError, match="not ordered"):
                    getattr(left, op)(right)
    with pytest.raises(TypeError):
        sorted(EvidenceBasis)
    assert not hasattr(EvidenceBasis.ARTIFACT, "rank"), (
        "a basis must not acquire a rank; `Strength.rank` is the only rank in this package"
    )


def test_a_basis_is_never_compared_against_a_strength():
    """The two coordinates are not on one scale, and neither knows how to be on the other's."""
    with pytest.raises(TypeError):
        EvidenceBasis.ARTIFACT.__lt__(Strength.PROVED)
    assert Strength.PROVED.__lt__(EvidenceBasis.ARTIFACT) is NotImplemented


def test_no_rendering_draws_a_basis_as_a_rung():
    """`basis_sentence` is the only place any rendering words a basis.

    The counterpart of `test_no_rendering_prints_a_bare_degree_without_the_source_that_fixed_it`,
    and for the same reason: a bare word beside a rung word is read as a rung. So the basis word
    never appears inside a lattice step, and the sentence that carries it always names which rungs
    the duty cannot reach.
    """
    source = inspect.getsource(render)
    assert source.count("_BASIS_SENTENCES") == 2, (
        "the basis wording table is read somewhere other than `basis_sentence`; one function "
        "writes it, for the reason `degree_sentence` is the only place a degree is formatted"
    )
    for basis in EvidenceBasis:
        assert f'"{basis.value}"' not in source and f"'{basis.value}'" not in source, (
            f"{basis.value!r} is spelled as a bare literal in render.py; a rendering reads the "
            "basis off the result and words it through `basis_sentence`, never by name"
        )

    sut = _log_only_system()
    html_out = check_conformance(sut, load_pack("ecoa")).render_html()
    for basis in EvidenceBasis:
        assert f'lattice-step ">{basis.value}' not in html_out
        assert f"</span> {basis.value}</span>" not in html_out, (
            f"{basis.value!r} is drawn as a step of the strength lattice"
        )
    assert 'class="lattice-basis"' in html_out


def test_the_behavioural_basis_says_nothing_and_the_other_three_name_their_ceiling():
    """The default basis renders exactly as it always did; the other three explain themselves."""
    assert basis_sentence(EvidenceBasis.BEHAVIOURAL) is None
    for basis in (EvidenceBasis.RELATIONAL, EvidenceBasis.ARTIFACT, EvidenceBasis.ASSESSMENT):
        sentence = basis_sentence(basis)
        assert sentence and sentence.startswith(f"{basis.value} — ")
        assert [s for s in Strength if s not in basis.rungs], (
            "a basis with a sentence must have a rung it cannot reach; a basis reaching every "
            "rung has no ceiling to explain and should render like the behavioural one"
        )
        # The sentence's job is the ceiling: a reader who has just read a tier tag must learn
        # which rungs are out of this duty's reach and that the reason is the duty's, not the
        # system's. So it names every rung above `unattainable` that the basis *does* admit, or
        # says outright that there is none.
        reachable = [s for s in basis.rungs if s is not Strength.UNATTAINABLE]
        if reachable:
            for rung in reachable:
                assert rung.value in sentence, (
                    f"the {basis.value} sentence must name {rung.value}, a rung this duty can "
                    "reach, or a reader cannot tell the ceiling from the floor"
                )
        else:
            assert "No rung of the strength lattice" in sentence


# --------------------------------------------------------------------------------------------
# The basis is derived from the duty, and the result model refuses to disagree with it.
# --------------------------------------------------------------------------------------------


def test_the_basis_is_derived_from_the_duty_and_never_declared():
    """No pack field, no system attribute, and no dependence on which engine answered."""
    assert "basis" not in {f for req in _all_requirements() for f in vars(req)}
    duty = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment")
    assert evidence_basis(duty) is EvidenceBasis.RELATIONAL

    class Liar(BaseSUT):
        basis = "behavioural"
        evidence_basis = "behavioural"

    result = evaluate_requirement(duty, Liar(set(duty.requires)))
    assert result.basis is EvidenceBasis.RELATIONAL


def test_a_result_cannot_carry_a_rung_its_basis_does_not_admit():
    """Three refusals, one per basis, each previously only a sentence in a module docstring."""
    for basis, rung in (
        (EvidenceBasis.RELATIONAL, Strength.OBSERVED),
        (EvidenceBasis.ARTIFACT, Strength.PROVED),
        (EvidenceBasis.ASSESSMENT, Strength.OBSERVED),
    ):
        with pytest.raises(ValueError, match="cannot be reported"):
            RequirementResult(
                requirement_id="fixture",
                source_clause="Fixture Article 1",
                verdict=Verdict.SATISFIED,
                strength=rung,
                signals_required=("a",),
                basis=basis,
            )


def test_every_basis_admits_unattainable_so_the_capability_gate_is_never_bypassed():
    """The gate runs before any basis is consulted, so no basis may refuse its answer.

    `unattainable` is not an engine's conclusion: it is a set difference over declared signal
    names, identical for every duty. A basis whose row omitted it would turn a system that can show
    nothing into a not-evaluated result, which is the substitution `docs/semantics.md` §4 keeps
    four outcomes apart to prevent.
    """
    for basis, rungs in BASIS_RUNGS.items():
        assert Strength.UNATTAINABLE in rungs, basis
        assert rungs[0] is Strength.UNATTAINABLE, "rungs are listed weakest first"
        assert list(rungs) == sorted(rungs, key=lambda s: s.rank)


def test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach():
    """`BASIS_RUNGS` and `report._engine_ladder` may not drift apart.

    The table is a claim about what could be reached; the ladder is what runs. The check is in both
    directions: no ladder offers a rung its duty's basis refuses (which would be refused at the
    stamp, at run time, on a user's report), and no basis advertises a rung above the strongest any
    ladder for a duty on that basis offers (which would draw a step on the HTML track that nothing
    can ever light).

    The second direction is a *ceiling* check and not an equality, and the reason is
    `Strength.RECOUNTED`: a ladder entry is chosen without executing the system, so the certificate
    branch cannot know whether the artefact behind a decision enumerates its reasons or recounts
    them, and it declares the strongest rung it might reach. That a lower rung on the row is
    reachable is shown by running the engine instead —
    `test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one` in
    `tests/test_artifact_protocol.py` — which is better evidence than reading it off the ladder.
    """
    offered: dict[EvidenceBasis, set[Strength]] = {b: set() for b in EvidenceBasis}
    for req in _all_requirements():
        basis = evidence_basis(req)
        sut = _fully_exposing_system(req)
        resources = report_module._EvaluationResources(sut)
        ladder = report_module._engine_ladder(req, sut, [], resources)
        rungs = {strength for strength, _run in ladder}
        assert rungs <= set(basis.rungs), (
            f"{req.id}: the ladder offers {sorted(s.value for s in rungs)} but the "
            f"{basis} basis admits {sorted(s.value for s in basis.rungs)}"
        )
        offered[basis] |= rungs

    for basis, rungs in offered.items():
        if basis is EvidenceBasis.ASSESSMENT:
            continue  # no shipped duty, and by design no ladder at all — see below.
        advertised = set(basis.rungs) - {Strength.UNATTAINABLE}
        assert rungs <= advertised and max(advertised) == max(rungs), (
            f"the {basis} basis advertises {sorted(s.value for s in advertised)} but the shipped "
            f"ladders offer {sorted(s.value for s in rungs)}"
        )


def test_an_assessment_duty_reaches_no_engine_at_all():
    """The `assessment` basis admits `unattainable` and nothing else, and the code agrees.

    Both open-texture fragments return before `_engine_ladder` is built, which is what keeps a
    system that can show nothing `unattainable` rather than a low degree
    (`docs/semantics.md` §9). The basis is that fact written into the result model.
    """
    duty = _graded_duty()
    assert evidence_basis(duty) is EvidenceBasis.ASSESSMENT
    assert EvidenceBasis.ASSESSMENT.rungs == (Strength.UNATTAINABLE,)

    nothing = BaseSUT(set())
    assert evaluate_requirement(duty, nothing).strength is Strength.UNATTAINABLE

    able = BaseSUT({REASON})
    graded = evaluate_requirement(
        duty, able, records=[{REASON: "a stated reason"}], grading=_grading()
    )
    assert graded.strength is None
    assert graded.basis is EvidenceBasis.ASSESSMENT


# --------------------------------------------------------------------------------------------
# The three pressures, each discharged and each pinned.
# --------------------------------------------------------------------------------------------


def test_a_graded_duty_is_counted_apart_from_a_duty_no_engine_settled():
    """Pressure 1. Two very different facts used to render as one number in the headline.

    A measured truth degree and a solver timeout both reach `strength=None`, and before the basis
    both landed in `not evaluated` — a category whose instruction is *fix the evidence or the
    specification*, which is the wrong instruction for a duty no rung of this lattice was ever
    going to rank.
    """
    able = BaseSUT({REASON})
    graded = evaluate_requirement(
        _graded_duty(), able, records=[{REASON: "a stated reason"}], grading=_grading()
    )
    unsettled = RequirementResult(
        requirement_id="fixture_unsettled",
        source_clause="Fixture Article 2",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=(REASON,),
        evidence_summary="Not evaluated: the trace was empty.",
    )
    both = report_module.ConformanceReport(
        pack_id="fixture", system_name="SUT", results=(graded, unsettled)
    )
    counts = both.counts
    assert counts["on_an_assessment"] == 1
    assert counts["not_evaluated"] == 1
    assert "1 on an assessment" in both.headline
    assert "1 not evaluated" in both.headline
    assert counts["binding_total"] == counts["total"] == 2


def test_a_counterfactual_duty_is_never_observed_however_long_the_trace():
    """Pressure 2. The missing bottom rung is the property's, not the system's.

    The refusal already existed in `rulelang.eval_expression` and in `_engine_ladder`; what did not
    exist was any way for a reader of a report to see it. The rendering now names it, and the
    result model now refuses a result that contradicts it.
    """
    duty = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment")
    assert Strength.OBSERVED not in evidence_basis(duty).rungs

    text = check_conformance(_log_only_system(), load_pack("ecoa")).render_text()
    assert "evidence basis: relational" in text
    assert "a decision record holds one" in text


def test_the_certificate_dutys_ceiling_is_named_as_the_dutys_and_not_the_systems():
    """Pressure 3. A ladder of one rung read as a system that had not exposed enough.

    `[PROBED]` with `proved` drawn greyed-out beside it is an instruction to expose more of the
    system, and for this duty that instruction is false: the measurement is against the inference
    artefact, and no exposure raises it. The track shows the rungs this duty has — three since
    `recounted` landed, and still neither `observed` nor `proved`.
    """
    duty = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_b_2_principal_reasons_complete")
    assert evidence_basis(duty).rungs == (
        Strength.UNATTAINABLE,
        Strength.RECOUNTED,
        Strength.PROBED,
    )

    html_out = check_conformance(_log_only_system(), load_pack("ecoa")).render_html()
    card = html_out.split(duty.id, 1)[1].split("</article>", 1)[0]
    assert "lattice-step" in card
    assert ">🏆 proved<" not in card, "a rung nothing can reach is still drawn on the track"
    assert "Evidence basis: artifact" in card


# --------------------------------------------------------------------------------------------
# The constraint the change was made under, and the census.
# --------------------------------------------------------------------------------------------


def test_the_basis_changed_no_verdict_and_no_strength():
    """Every shipped duty against a shipped system reports what it reported before.

    The basis describes evidence; it measures nothing. This is the constraint the whole change was
    made under, asserted against the values recorded on `main` rather than against the code that
    produced them.
    """
    expected = {
        "ecoa_reg_b_1002_9_a_1_timing_of_notice": (Verdict.SATISFIED, Strength.OBSERVED),
        "ecoa_reg_b_1002_9_a_2_written_statement": (Verdict.SATISFIED, Strength.OBSERVED),
        "ecoa_reg_b_1002_9_b_2_specific_reasons": (Verdict.SATISFIED, Strength.OBSERVED),
        "ecoa_reg_b_1002_9_b_2_principal_reasons_complete": (
            Verdict.INCONCLUSIVE,
            Strength.UNATTAINABLE,
        ),
        "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out": (
            Verdict.INCONCLUSIVE,
            Strength.UNATTAINABLE,
        ),
        "ecoa_reg_b_1002_4_a_no_disparate_treatment": (Verdict.INCONCLUSIVE, None),
    }
    got = {
        r.requirement_id: (r.verdict, r.strength)
        for r in check_conformance(_log_only_system(), load_pack("ecoa")).results
    }
    assert got == expected


def test_exactly_two_shipped_duties_are_not_on_the_behavioural_basis():
    """The census, pinned. A third one arriving is a decision, not a side effect of a pack edit.

    The shape of `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy`: a count that
    fails when the packs move, so the count in `docs/semantics.md` §10 cannot go stale silently.
    """
    census = {
        req.id: evidence_basis(req)
        for req in _all_requirements()
        if evidence_basis(req) is not EvidenceBasis.BEHAVIOURAL
    }
    assert census == NON_BEHAVIOURAL


def test_the_json_envelope_carries_the_basis_on_every_result():
    payload = check_conformance(_log_only_system(), load_pack("ecoa")).to_dict()
    for result in payload["results"]:
        assert result["basis"] in {b.value for b in EvidenceBasis}
    by_id = {r["requirement_id"]: r["basis"] for r in payload["results"]}
    assert by_id["ecoa_reg_b_1002_4_a_no_disparate_treatment"] == "relational"
    assert by_id["ecoa_reg_b_1002_9_b_2_principal_reasons_complete"] == "artifact"


def test_the_lay_audience_is_never_shown_an_evidence_basis():
    """The audience rule. A reader not shown the rungs is not shown a sentence about them.

    `docs/semantics.md` §9's rule 4 is the precedent: the affected-individual projection already
    suppresses an engine's account and reports an unsettled duty in words. A basis word there would
    be read as a grade of the answer, whatever sentence surrounded it.
    """
    run = check_conformance(_log_only_system(), load_pack("ecoa"))
    lay = run.render_text(audience="affected-individual")
    lay_html = run.render_html(audience="affected-individual")
    for surface in (lay, lay_html):
        assert "evidence basis" not in surface.lower()
        for basis in EvidenceBasis:
            assert basis.value not in surface

    for name, projection in AUDIENCES.items():
        rendered = run.render_text(audience=name)
        assert ("evidence basis:" in rendered) is projection.strength, name


#: The trace `_log_only_system` replays: two adverse actions, each with a stated reason, each
#: notified inside the 30 days 12 CFR 1002.9(a)(1) allows. Written out rather than loaded so the
#: verdicts `test_the_basis_changed_no_verdict_and_no_strength` pins are the fixture's own.
_TRACE = [
    {
        "decision_id": "APP-1",
        "artifact_logs_decision_record": "adverse action",
        "artifact_logs_reason_explanation": "Income insufficient for the amount requested",
        "artifact_logs_notification_latency_days": 4,
        "artifact_logs_counteroffer_not_accepted": False,
        "provenance_model_version": "v1",
        "scope_statements_local_vs_global": "local",
    },
    {
        "decision_id": "APP-2",
        "artifact_logs_decision_record": "adverse action",
        "artifact_logs_reason_explanation": "Delinquent credit obligations on file",
        "artifact_logs_notification_latency_days": 6,
        "artifact_logs_counteroffer_not_accepted": False,
        "provenance_model_version": "v1",
        "scope_statements_local_vs_global": "local",
    },
]


class _LogOnlySystem(BaseSUT):
    """A decision log and nothing else: no `decide()`, no rules, no inference artefact.

    The system all three pressures are visible on at once. It reaches `observed` where a trace
    answers the duty, and on the other two it hits a ceiling that is the *duty's* — which before
    this change no rendering said.
    """

    system_domains = ("consumer-credit",)

    def decisions(self):
        return list(_TRACE)


def _log_only_system() -> BaseSUT:
    return _LogOnlySystem(
        {
            "artifact_logs_decision_record",
            "artifact_logs_reason_explanation",
            "artifact_logs_notification_latency_days",
            "artifact_logs_counteroffer_not_accepted",
            "provenance_model_version",
            "scope_statements_local_vs_global",
            "applicant_prohibited_basis",
        }
    )


def _fully_exposing_system(req: Requirement) -> BaseSUT:
    """A system exposing every optional interface, so every rung a duty admits is offered.

    The ladder is built from the callable surface alone and never executes the system, so the body
    below is never called: what matters is that `decide` exists beside the `logic` every `BaseSUT`
    already has.
    """

    class Exposing(BaseSUT):
        def decide(self, inputs):  # pragma: no cover - the ladder only checks it is callable
            return {}

    return Exposing(set(req.requires))
