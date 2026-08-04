"""Tests for open-textured predicates: the two constructs, and the five refusals that bound them.

What this module is for:
  Twenty-one of the shipped requirements are presence checks, and the fourth column of
  `docs/refinement.md` says the same thing repeatedly: *meaningful*, *sufficiently detailed*,
  *adequate*, *appropriate* were not modelled. Two constructs answer different halves of that.
  `undetermined(signal, "predicate", "authority")` is the conservative half — a predicate no engine
  settles, resolved by a named authority outside this tool. `degree(signal, "predicate")` is the
  graded half, read over an algebra the pack declares against a grading whose source is declared
  beside it.

  Every test here is a **refusal**, and that is the design. A graded semantics makes every duty
  *answerable*, which would destroy the one property this tool has: it refuses rather than guessing.

What a reader must not break:
  - `test_a_system_that_can_show_nothing_is_unattainable_and_never_graded` is the acceptance test of
    the whole design, and it is the first one written. A system with no capability is `unattainable`
    exactly as it was before any of this existed, and never a low degree.
    Why this matters: `unattainable` and `not evaluated` must stay reachable. A low truth degree
    that quietly replaced either would turn a refusal into a finding about a system nobody measured.
  - A degree never appears anywhere without the source that fixed it, in **every** rendering — text,
    HTML, JSON and each of the five audience projections.
    Why this matters: a reader handed `0.7` reads *seventy percent compliant*.
    `docs/authoring-packs.md` forbids exactly this move for a group-parity duty, and the objection
    is stronger here because a degree looks like a measurement of the duty rather than of a rate.
  - A two-valued duty cannot acquire a degree, and the gate is `classify_fragment`.
    Why this matters: the machinery existing is not a reason for a duty with a sharp boundary to
    stop having one.
  - No test here asserts a *verdict* derived from a degree, because none is derived. If a future
    change makes a degree decide `satisfied`, these tests keep passing and `docs/semantics.md` §9
    stops being true — read it before adding one.
"""

from __future__ import annotations

import ast
import json

import pytest

from reasonsmith.manyvalued import (
    ALGEBRAS,
    Grading,
    UngradedAtomError,
    algebra_named,
    atom_key,
    degree_of,
    degree_over_trace,
)
from reasonsmith.render import AUDIENCES
from reasonsmith.report import (
    OPEN_TEXTURE_KEY,
    TRUTH_DEGREE_KEY,
    ConformanceReport,
    RequirementResult,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    classify_fragment,
    eval_expression,
    parse_property,
)
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

REASON = "artifact_logs_reason_explanation"

#: The fixture degree. A distinctive decimal on purpose: the rendering test searches every surface
#: for the bare numeral, and a round value like 0.5 collides with an opacity in the page stylesheet,
#: which would make the search pass on a coincidence instead of on the report.
DEGREE = 0.63
AUTHORITY = "the competent supervisory authority under GDPR Article 51"

#: A grading standing in for a real assessment. Every field is filled because a `Grading` refuses to
#: exist without them — which is the point of constraint B and not a convenience of this fixture.
GRADING = Grading(
    authority="a three-assessor panel convened for this fixture",
    scale="0 = states no information at all, 1 = states everything the clause asks for",
    method="independent scoring, median taken",
    degrees={atom_key(REASON, "meaningful"): DEGREE},
)


def _requirement(spec: str, formalism: str, algebra: str = "", requires=(REASON,)):
    """A requirement carrying a fixture property, built directly rather than loaded from a pack.

    No shipped pack has a graded or an undetermined duty and none may gain one here: which
    statutory predicate becomes the first graded duty is a legal reading, not a test fixture.
    """
    return Requirement(
        id=f"fixture_{formalism}",
        source_document="Fixture",
        article_clause="Article 1",
        verbatim_text="A fixture clause, quoted from nothing.",
        stakeholder="fixture",
        formalism=formalism,
        spec=spec,
        rationale="A fixture duty, standing in for a clause nobody has read yet.",
        requires=tuple(requires),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
        algebra=algebra,
    )


def _graded_duty():
    return _requirement(f'degree({REASON}, "meaningful")', "graded", "lukasiewicz")


def _undetermined_duty():
    return _requirement(
        f'undetermined({REASON}, "meaningful", {AUTHORITY!r})', "undetermined"
    )


def _records(count: int = 2):
    return [{REASON: f"a stated reason {i}"} for i in range(count)]


def _pack_toml(spec: str, formalism: str, grading_table: str = "") -> str:
    return f"""
[pack]
id = "fixture"
title = "Fixture pack"
description = "A fixture pack, quoting no statute."
{grading_table}
[[requirement]]
id = "fixture_duty"
source_document = "Fixture"
article_clause = "Article 1"
verbatim_text = "A fixture clause, quoted from nothing."
stakeholder = "fixture"
formalism = "{formalism}"
spec = '''{spec}'''
rationale = "A fixture duty."
requires = ["{REASON}"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
"""


# --------------------------------------------------------------------------------------------
# Acceptance 1 — the failure mode this whole design is against.
# --------------------------------------------------------------------------------------------


def test_a_system_that_can_show_nothing_is_unattainable_and_never_graded():
    """A system with no capability gets `unattainable`, on a graded duty and an undetermined one.

    Written first and kept passing. A graded semantics makes every duty answerable, which is
    precisely what must not happen here: the capability gate runs before either fragment is
    dispatched, so the answer for a system that can show nothing is the answer it always was.
    A low degree in its place would report a breach measured from nothing.
    """
    nothing = BaseSUT(set())
    for req in (_graded_duty(), _undetermined_duty()):
        result = evaluate_requirement(req, nothing, records=[], grading=GRADING)
        assert result.strength == Strength.UNATTAINABLE
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.signals_missing == (REASON,)
        assert TRUTH_DEGREE_KEY not in result.details
        assert OPEN_TEXTURE_KEY not in result.details


def test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero():
    """A predicate nobody assessed is not a predicate assessed as wholly false.

    The substitution this refuses is the same one presence-as-a-proxy makes: answering the question
    that can be answered and reporting it as the one that was asked. `0.0` here would report a
    system violated on evidence nobody produced.
    """
    ungraded = Grading(
        authority="a panel that assessed a different predicate",
        scale="0 to 1",
        method="scored by hand",
        degrees={atom_key(REASON, "timely"): 1.0},
    )
    result = evaluate_requirement(
        _graded_duty(), BaseSUT({REASON}), records=_records(), grading=ungraded
    )
    assert result.strength is None
    assert TRUTH_DEGREE_KEY not in result.details
    assert "scores no degree" in result.evidence_summary

    with pytest.raises(UngradedAtomError):
        ungraded.degree(REASON, "meaningful")


def test_a_graded_duty_with_no_grading_or_no_trace_is_not_evaluated():
    """Two absences, two sentences, and no degree in either.

    An empty trace matters most: the degree over a trace is the infimum of its per-decision degrees,
    and the infimum of nothing is the top of the lattice. Answering `1.0` there is the vacuous
    `satisfied` this package refuses, rewritten as a number.
    """
    system = BaseSUT({REASON})

    ungraded_run = evaluate_requirement(_graded_duty(), system, records=_records(), grading=None)
    assert ungraded_run.strength is None
    assert "no grading was supplied" in ungraded_run.evidence_summary

    empty_trace = evaluate_requirement(_graded_duty(), system, records=[], grading=GRADING)
    assert empty_trace.strength is None
    assert TRUTH_DEGREE_KEY not in empty_trace.details
    assert "infimum of nothing" in empty_trace.evidence_summary

    with pytest.raises(ValueError, match="infimum of nothing"):
        degree_over_trace(
            parse_property(f'degree({REASON}, "meaningful")'),
            [],
            algebra_named("godel"),
            GRADING,
        )


# --------------------------------------------------------------------------------------------
# Acceptance 2 — the algebra is a declared parameter of a pack, refused at load when missing.
# --------------------------------------------------------------------------------------------


def test_a_pack_shipping_a_graded_duty_without_an_algebra_is_refused_at_load(tmp_path):
    """The refusal names the declaration that is missing, and where it goes.

    Which residuated lattice the connectives are read over changes what a conjunction of two `0.5`s
    means — Łukasiewicz says `0`, Gödel says `0.5`, product says `0.25` — so a default would be a
    semantics this tool picked on a pack author's behalf and no rendering would say which.
    """
    path = tmp_path / "nograding.toml"
    path.write_text(_pack_toml(f'degree({REASON}, "meaningful")', "graded"), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_pack(path)
    message = str(exc.value)
    assert "[grading]" in message
    assert "algebra" in message
    for name in ALGEBRAS:
        assert name in message


def test_a_pack_declaring_an_algebra_this_package_cannot_read_is_refused(tmp_path):
    """A misspelling is refused where it is written, not silently resolved to a neighbour."""
    path = tmp_path / "typo.toml"
    path.write_text(
        _pack_toml(
            f'degree({REASON}, "meaningful")',
            "graded",
            grading_table='\n[grading]\nalgebra = "lukasiewitz"\n',
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="lukasiewitz"):
        load_pack(path)


def test_a_pack_declaring_an_algebra_loads_its_graded_duty(tmp_path):
    """The positive case, so the refusals above are not passing because nothing ever loads."""
    path = tmp_path / "graded.toml"
    path.write_text(
        _pack_toml(
            f'degree({REASON}, "meaningful")',
            "graded",
            grading_table='\n[grading]\nalgebra = "godel"\n',
        ),
        encoding="utf-8",
    )
    pack = load_pack(path)
    assert pack.algebra == "godel"
    assert pack.requirements[0].algebra == "godel"


# --------------------------------------------------------------------------------------------
# Acceptance 3 — no rendering prints a bare degree.
# --------------------------------------------------------------------------------------------


def _graded_report() -> ConformanceReport:
    system = BaseSUT({REASON})
    system.decisions = lambda: _records()  # type: ignore[method-assign]
    result = evaluate_requirement(
        _graded_duty(), system, records=_records(), grading=GRADING
    )
    assert result.details[TRUTH_DEGREE_KEY]["degree"] == DEGREE
    return ConformanceReport(
        pack_id="fixture", system_name="fixture-system", results=(result,)
    )


def test_no_rendering_prints_a_bare_degree_without_the_source_that_fixed_it():
    """Every surface, not only the plain-text one: text, HTML, JSON and all five audiences.

    The rule is that the numeral and what fixed it are one inseparable sentence, and the enforcement
    is two-sided: `render.degree_sentence` is the only place a degree is formatted, and
    `RequirementResult._validate_truth_degree` refuses a result that could not fill it. This test is
    what fails if a second formatting route appears.
    """
    report = _graded_report()
    numeral = str(DEGREE)
    surfaces = {
        "text": report.render_text(),
        "html": report.render_html(commit_hash=""),
        "json": json.dumps(report.to_dict()),
    }
    for audience in AUDIENCES:
        surfaces[f"text:{audience}"] = report.render_text(audience=audience)
        surfaces[f"html:{audience}"] = report.render_html(commit_hash="", audience=audience)

    showed_it_somewhere = False
    for name, surface in surfaces.items():
        if numeral not in surface:
            continue
        showed_it_somewhere = True
        assert GRADING.authority in surface, f"{name} prints a degree without its authority"
        assert GRADING.scale in surface, f"{name} prints a degree without its scale"
        assert GRADING.method in surface, f"{name} prints a degree without its method"
        assert "lukasiewicz" in surface, f"{name} prints a degree without the algebra"
        assert "%" not in surface.split(numeral)[1][:200], (
            f"{name} renders a degree near a percent sign; a degree is not a percentage"
        )
    assert showed_it_somewhere, (
        "no surface rendered the degree at all, so this test asserts nothing — it must fail when a "
        "rendering drops the source, not when it drops the number"
    )


def test_the_lay_audience_is_shown_the_duty_as_unsettled_and_never_the_number():
    """The affected individual is told the duty was not settled, in words, with no lattice in it.

    Not a suppression bolted on for this construct: the projection that hides an engine's account
    already hides this one, and `_lay_sections` already reports a `strength=None` result as a duty
    nothing here could settle. A degree shown to a lay reader would be read as a score whatever
    sentence surrounded it.
    """
    rendered = _graded_report().render_text(audience="affected-individual")
    assert str(DEGREE) not in rendered
    assert "lukasiewicz" not in rendered
    assert "left open rather than answered" in rendered


# --------------------------------------------------------------------------------------------
# Acceptance 4 — a two-valued duty cannot acquire a degree.
# --------------------------------------------------------------------------------------------


def test_a_two_valued_duty_cannot_acquire_a_degree():
    """`classify_fragment` is the gate, exactly as it is for the counterfactual atom.

    Three ways in are closed. A spec with no `degree()` atom is never classified `graded`; a
    requirement declaring `graded` over such a spec is refused; and a requirement carrying an
    algebra beside a two-valued formalism is refused, so a pack shipping one graded duty leaves its
    presence checks as two-valued as they were.
    """
    assert classify_fragment(f"present({REASON})") == "record"
    assert classify_fragment(f'contains({REASON}, "n/a")') == "logical"
    assert classify_fragment(f'degree({REASON}, "meaningful")') == "graded"

    with pytest.raises(ValueError, match="two-valued"):
        _requirement(f"present({REASON})", "record", algebra="godel")


def test_a_pack_declaring_an_algebra_leaves_its_two_valued_duties_two_valued(tmp_path):
    """The declaration reaches the graded requirement and no other, checked on a mixed pack."""
    path = tmp_path / "mixed.toml"
    path.write_text(
        _pack_toml(
            f'degree({REASON}, "meaningful")',
            "graded",
            grading_table='\n[grading]\nalgebra = "product"\n',
        )
        + f"""
[[requirement]]
id = "fixture_presence"
source_document = "Fixture"
article_clause = "Article 2"
verbatim_text = "A second fixture clause."
stakeholder = "fixture"
formalism = "record"
spec = '''present({REASON})'''
rationale = "A two-valued duty in a pack that declares an algebra."
requires = ["{REASON}"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
""",
        encoding="utf-8",
    )
    pack = load_pack(path)
    graded, presence = pack.requirements
    assert graded.algebra == "product"
    assert presence.algebra == ""

    system = BaseSUT({REASON})
    report = check_conformance(system, pack, grading=GRADING)
    by_id = {r.requirement_id: r for r in report.results}
    assert TRUTH_DEGREE_KEY not in by_id["fixture_presence"].details
    assert by_id["fixture_presence"].strength is None  # empty trace, exactly as before


# --------------------------------------------------------------------------------------------
# Acceptance 5 — an undetermined atom names the authority that would settle it.
# --------------------------------------------------------------------------------------------


def test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority():
    """Never silently true, never silently false, and never a gap blamed on the system.

    The verdict is `inconclusive` at `strength=None` — this package's *not evaluated* — reusing the
    path `not_evaluated_for_unreachable_trigger` already established rather than inventing one
    beside it. What the construct adds is that the result names the predicate and the authority.
    """
    result = evaluate_requirement(
        _undetermined_duty(), BaseSUT({REASON}), records=_records(), grading=None
    )
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details[OPEN_TEXTURE_KEY] == [
        {"signal": REASON, "predicate": "meaningful", "authority": AUTHORITY}
    ]
    assert AUTHORITY in result.evidence_summary
    assert AUTHORITY in result.render_text() if hasattr(result, "render_text") else True

    report = ConformanceReport(pack_id="fixture", system_name="s", results=(result,))
    for surface in (report.render_text(), report.render_html(commit_hash="")):
        assert AUTHORITY in surface
        assert "meaningful" in surface


def test_an_undetermined_atom_is_refused_by_the_two_valued_interpreter():
    """The load-bearing refusal: every trace-reading engine evaluates through `eval_expression`.

    Refusing here is what makes "no engine settles an open-textured predicate" a fact about the code
    rather than a convention `report._engine_ladder` is trusted to keep — the same argument the
    counterfactual atom's refusal rests on.
    """
    record = {REASON: "we declined because your obligations are excessive"}
    for spec in (
        f'undetermined({REASON}, "meaningful", {AUTHORITY!r})',
        f'degree({REASON}, "meaningful")',
    ):
        with pytest.raises(UnsupportedConstructError):
            eval_expression(parse_property(spec), record)


def test_an_undetermined_duty_dominates_the_settleable_parts_of_its_formula():
    """One unsettled atom leaves the whole formula unsettled, and it is classified that way.

    Answering the presence conjunct and reporting the answer as the duty's is the substitution
    presence-as-a-proxy already is, and it is exactly what this construct exists to end.
    """
    spec = f'present({REASON}) and undetermined({REASON}, "meaningful", {AUTHORITY!r})'
    assert classify_fragment(spec) == "undetermined"
    result = evaluate_requirement(
        _requirement(spec, "undetermined"), BaseSUT({REASON}), records=_records(), grading=None
    )
    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE


# --------------------------------------------------------------------------------------------
# The algebra, and the shapes the language refuses.
# --------------------------------------------------------------------------------------------


def test_the_three_algebras_disagree_about_a_conjunction_of_two_halves():
    """The reason the algebra is declared rather than defaulted, in one line of arithmetic."""
    half = 0.5
    assert ALGEBRAS["lukasiewicz"].conjunction(half, half) == 0.0
    assert ALGEBRAS["godel"].conjunction(half, half) == 0.5
    assert ALGEBRAS["product"].conjunction(half, half) == 0.25


@pytest.mark.parametrize("name", sorted(ALGEBRAS))
def test_each_algebra_is_a_residuated_lattice_on_the_grid(name):
    """Residuation, on a grid: `x AND y <= z` exactly when `x <= y -> z`.

    The law that makes an algebra a reading of implication rather than three unrelated functions,
    checked rather than asserted, so a member added to the table cannot arrive without it. The grid
    is coarse and this is a check, not a proof — but a member that fails it is wrong everywhere.
    """
    algebra = ALGEBRAS[name]
    grid = [i / 8 for i in range(9)]
    for x in grid:
        for y in grid:
            for z in grid:
                left = algebra.conjunction(x, y) <= z + 1e-9
                right = x <= algebra.residuum(y, z) + 1e-9
                assert left == right, f"{name} fails residuation at {x}, {y}, {z}"


def test_the_degree_of_a_trace_is_the_infimum_of_its_records():
    """The graded reading of "holds at every decision", and the reason it is not an average.

    An average would let a long run of compliant decisions pay for a bad one, which is not what a
    universal duty says. The infimum is the lattice meet and is what the record and observed engines
    already take over a trace, read on a scale instead of on two values.
    """
    node = parse_property(f'present({REASON}) and degree({REASON}, "meaningful")')
    algebra = algebra_named("godel")
    records = [{REASON: "stated"}, {REASON: ""}]
    assert degree_of(node, records[0], algebra, GRADING) == DEGREE
    assert degree_of(node, records[1], algebra, GRADING) == 0.0
    assert degree_over_trace(node, records, algebra, GRADING) == 0.0


def test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else():
    """A subtree with no graded atom is answered by the interpreter every other engine uses.

    Not an optimisation. It is what keeps `present()`'s treatment of a blank string and
    `contains()`' ASCII fold identical inside a graded formula and outside one — the same agreement
    obligation `test_the_solvers_fold_is_the_interpreters_fold` holds for the phrase atom.
    """
    node = parse_property(f'contains({REASON}, "EXCESSIVE") and degree({REASON}, "meaningful")')
    algebra = algebra_named("lukasiewicz")
    folded = {REASON: "obligations are excessive"}
    unfolded = {REASON: "no reason given"}
    assert degree_of(node, folded, algebra, GRADING) == pytest.approx(DEGREE)
    assert degree_of(node, unfolded, algebra, GRADING) == 0.0


def test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused():
    """A comparison of degrees is a threshold, and a threshold is the author's number as the law's.

    This is where a graded pack would launder a compliance cut-off into something that looks like a
    formula. `degree(x, "p") >= 0.8` states that eight tenths discharges the duty, which no statute
    says and this tool will not say for one.
    """
    for spec in (
        f'degree({REASON}, "meaningful") >= 0.8',
        f'degree({REASON}, "meaningful") + 1 > 1',
    ):
        with pytest.raises(UnsupportedConstructError):
            parse_property(spec)


def test_a_graded_atom_under_a_temporal_operator_is_refused_at_load():
    """A many-valued reading of a temporal operator is a temporal semantics, and there is none here.

    This package implements no temporal semantics at any rung — rtamt monitors and `flloat`
    decides — and inventing one on a lattice would be a larger claim than either. The graded
    fragment is a property of one decision record, quantified over the trace by the infimum.
    """
    with pytest.raises(UnsupportedConstructError, match="temporal"):
        parse_property(f'always(degree({REASON}, "meaningful"))')


def test_a_spec_using_both_open_texture_atoms_is_refused():
    """One says nothing here settles the predicate; the other asks for it to be graded.

    A spec carrying both would be classified `graded` and never graded in fact, which is a pack
    author told a semantics ran that did not.
    """
    with pytest.raises(UnsupportedConstructError, match="one or the other"):
        parse_property(
            f'undetermined({REASON}, "meaningful", {AUTHORITY!r}) and '
            f'degree({REASON}, "detailed")'
        )


def test_an_atom_leaving_its_authority_or_predicate_blank_is_refused():
    """A construct whose whole value is naming who settles the predicate must name one."""
    for spec in (
        f'undetermined({REASON}, "meaningful", "")',
        f'undetermined({REASON}, "", {AUTHORITY!r})',
        f'degree({REASON}, "  ")',
    ):
        with pytest.raises(UnsupportedConstructError):
            parse_property(spec)


# --------------------------------------------------------------------------------------------
# The result model's own refusals.
# --------------------------------------------------------------------------------------------


def _result(details: dict, strength=None) -> RequirementResult:
    return RequirementResult(
        requirement_id="fixture",
        source_clause="Fixture Article 1",
        verdict=Verdict.INCONCLUSIVE,
        strength=strength,
        signals_required=(REASON,),
        details=details,
    )


def test_a_result_cannot_carry_a_degree_without_the_source_that_fixed_it():
    """Constraint B, made structural: the refusal is in the type, not in a rendering convention."""
    reading = {
        "degree": DEGREE,
        "algebra": "godel",
        "atoms": {atom_key(REASON, "meaningful"): DEGREE},
        "source": GRADING.source(),
    }
    _result({TRUTH_DEGREE_KEY: dict(reading)})  # the complete one is constructible

    for broken in (
        {**reading, "source": {"authority": "a panel"}},
        {**reading, "source": {"authority": "", "scale": "0-1", "method": "median"}},
        {k: v for k, v in reading.items() if k != "algebra"},
    ):
        with pytest.raises(ValueError):
            _result({TRUTH_DEGREE_KEY: broken})


def test_a_result_carrying_a_degree_cannot_carry_a_strength():
    """Constraint A, made structural: a degree is a distinct evidence basis, never a rescaled rung.

    No member of the strength lattice means "graded", and this design deliberately added none. A
    result offering both would invite exactly the reading the whole construct is against — the
    number as a fraction of the rung.
    """
    reading = {
        "degree": DEGREE,
        "algebra": "godel",
        "atoms": {atom_key(REASON, "meaningful"): DEGREE},
        "source": GRADING.source(),
    }
    with pytest.raises(ValueError, match="rescaled verdict"):
        _result({TRUTH_DEGREE_KEY: reading}, strength=Strength.OBSERVED)


def test_a_result_cannot_carry_an_open_textured_finding_without_an_authority():
    """Acceptance 5, made structural: a `not evaluated` naming no authority is the old result."""
    _result({OPEN_TEXTURE_KEY: [{"signal": REASON, "predicate": "m", "authority": AUTHORITY}]})
    for broken in ([], [{"signal": REASON, "predicate": "m"}], "not a list"):
        with pytest.raises(ValueError):
            _result({OPEN_TEXTURE_KEY: broken})


def test_the_graded_reading_refuses_a_shape_the_loader_would_never_admit():
    """`degree_of` guards itself, and does not rely on having been called after `parse_property`.

    The loader refuses a graded atom under arithmetic or a comparison, so a pack cannot reach this
    raise. A caller doing many-valued work directly against this module can, and it is the module a
    future graded engine is built on — a guard that only holds for one entry point is not a guard.
    """
    unvalidated = ast.parse(f'degree({REASON}, "meaningful") + 1', mode="eval")
    with pytest.raises(UnsupportedConstructError, match="threshold|undefined scale"):
        degree_of(unvalidated, {REASON: "x"}, algebra_named("godel"), GRADING)


def test_an_algebra_is_never_resolved_from_something_that_is_not_a_name():
    """No default, no fallback, and no coercion of whatever a caller happened to pass."""
    for bad in (None, "", "   ", 7):
        with pytest.raises(ValueError, match="algebra"):
            algebra_named(bad)


def test_a_grading_refuses_a_degree_that_is_not_a_number_or_a_key_that_is_not_one():
    """A grading is a table of assessments; a boolean or a blank key is neither."""
    with pytest.raises(TypeError, match=r"\[0, 1\]"):
        Grading(authority="a", scale="b", method="c", degrees={atom_key("x", "p"): True})
    with pytest.raises(ValueError, match="predicate\\(signal\\)"):
        Grading(authority="a", scale="b", method="c", degrees={"": 0.5})


def test_a_whole_pack_run_reads_the_trace_for_a_graded_duty_itself(tmp_path):
    """`check_conformance` supplies the trace, so a graded duty is measured on a real run."""
    path = tmp_path / "graded.toml"
    path.write_text(
        _pack_toml(
            f'degree({REASON}, "meaningful")',
            "graded",
            grading_table='\n[grading]\nalgebra = "godel"\n',
        ),
        encoding="utf-8",
    )
    system = BaseSUT({REASON})
    system.decisions = lambda: _records()  # type: ignore[method-assign]
    report = check_conformance(system, load_pack(path), grading=GRADING)
    reading = report.results[0].details[TRUTH_DEGREE_KEY]
    assert reading["degree"] == DEGREE
    assert reading["algebra"] == "godel"
    assert reading["source"] == GRADING.source()
    assert report.results[0].strength is None


def test_a_grading_must_state_who_fixed_the_scale():
    """A degree with no source is a figure, and a `Grading` refuses to be one."""
    for missing in ("authority", "scale", "method"):
        fields = {"authority": "a panel", "scale": "0-1", "method": "median"}
        fields[missing] = "  "
        with pytest.raises(ValueError, match=missing):
            Grading(**fields, degrees={})
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        Grading(authority="a", scale="b", method="c", degrees={atom_key("x", "p"): 1.5})


# --------------------------------------------------------------------------------------------
# Nothing shipped changed.
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("pack_name", ["ecoa", "eu_ai_act", "gdpr", "gpai", "table7"])
def test_no_shipped_pack_uses_either_open_texture_construct(pack_name):
    """The machinery ships with no duty on it, and that is the hard limit of this change.

    Which statutory predicate becomes the first graded one is a legal reading and the captain's to
    make. A shipped pack that quietly gained one would also have moved a verdict, which this change
    is not permitted to do.
    """
    pack = load_pack(pack_name)
    assert pack.algebra == ""
    for req in pack.requirements:
        assert req.formalism not in ("graded", "undetermined")
        assert req.algebra == ""
