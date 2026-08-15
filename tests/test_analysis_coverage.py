"""Behavioral coverage for pack-analysis refusal and relation reporting paths."""

from reasonsmith import analysis
from reasonsmith.spec import Pack, Requirement


def req(identifier: str, spec: str, formalism: str = "logical", algebra: str = "") -> Requirement:
    return Requirement(
        id=identifier, source_document="test", article_clause="clause", verbatim_text="text",
        stakeholder="auditor", formalism=formalism, spec=spec, rationale="rationale",
        requires=("signal",), binding=True, scope="", domains=(), deontic_type="obligation",
        defeasibility="strict", algebra=algebra,
    )


def pack(*requirements: Requirement) -> Pack:
    return Pack("test", "Test", "description", tuple(requirements))


def test_state_property_refuses_non_boolean_fragments_and_reduces_always():
    assert "graded fragment" in analysis._state_property(
        req("graded", "degree(x, \"adequate\")", "graded", "godel")
    )[1]
    assert "predicate the law states" in analysis._state_property(
        req("open", "undetermined(x, \"adequate\", \"law\")", "undetermined")
    )[1]
    assert analysis._state_property(
        req("temporal", "always(present(x))", "temporal")
    )[0] is not None
    assert "not `always(state property)`" in analysis._state_property(
        req("temporal", "eventually(present(x))", "temporal")
    )[1]


def test_satisfiability_reports_unsat_core_and_one_way_entailment():
    result = analysis._satisfiability_and_relations(
        pack(req("strong", "present(a)"), req("weak", "present(a) or present(b)")), 1000
    )

    satisfiable, core, relations, skipped, notes = result
    assert satisfiable is True
    assert core == ()
    assert any(r.left == "strong" and r.right == "weak" and not r.equivalent for r in relations)
    assert skipped == []
    assert notes == []


def test_satisfiability_skips_unencodable_and_all_skipped_is_not_decided():
    result = analysis._satisfiability_and_relations(
        pack(req("open", "undetermined(x, \"adequate\", \"law\")", "undetermined")), 1000
    )

    assert result[:3] == (None, (), ())
    assert "open:" in result[3][0]


def test_mutate_rules_changes_comparisons_boolean_constants_and_strings():
    mutants = analysis.mutate_rules(["return x >= 2 and label == 'ok'"])
    labels = [label for label, _ in mutants]

    assert any(">=" in label and "<" in label for label in labels)
    assert any("and" in label and "or" in label for label in labels)
    assert any("'ok'" in label for label in labels)
    assert all("True" not in label for label, _ in analysis.mutate_rules(["return True"]))


def test_render_analysis_names_undecided_and_unsatisfiable_core():
    text = analysis.render_analysis(
        analysis.PackAnalysis(
            pack_id="test", satisfiable=None, temporal=None, unsatisfiable_core=(),
            relations=(), vacuities=(), mutation=(), mutation_domain="",
            skipped=("open: skipped",), notes=("solver note",),
        )
    )

    assert "satisfiability: not decided" in text
    assert "entailment: no requirement entails another" in text
    assert "skipped: open: skipped" in text


def test_valid_returns_both_solver_truth_values():
    assert analysis._valid([], analysis.z3.BoolVal(True), 1000) is True
    assert analysis._valid([], analysis.z3.BoolVal(False), 1000) is False


def test_render_analysis_reports_every_available_analysis_dimension():
    analysis_result = analysis.PackAnalysis(
        pack_id="test",
        satisfiable=False,
        unsatisfiable_core=("first", "second"),
        relations=(
            analysis.Relation("first", "second", False), analysis.Relation("same", "copy", True)
        ),
        vacuities=(analysis.VacuityFinding("first", "present(flag)", "inputs"),),
        mutation=(analysis.MutationScore("first", 1, 2),),
        mutation_domain="2 mutants",
        skipped=("a skipped requirement",),
        notes=("a recorded note",),
        temporal=analysis.TemporalAnalysis(
            decided=("temporal-a",),
            unsatisfiable=("temporal-a",),
            relations=(analysis.Relation("temporal-a", "temporal-b", False),),
            pairs_decided=1,
            pairs_refused=1,
        ),
    )

    text = analysis.render_analysis(analysis_result)

    assert "NOT jointly satisfiable" in text
    assert "core: first, second" in text
    assert "subsumes: first => second" in text
    assert "equivalent: same <=> copy" in text
    assert "temporal: 1 temporal dut(ies) decided" in text
    assert "NOT satisfiable: temporal-a" in text
    assert "1 of 2 pair(s) not decided" in text
    assert "vacuous: first" in text
    assert "mutation domain: 2 mutants" in text
    assert "1/2" in text
    assert "a skipped requirement" in text
    assert "a recorded note" in text


def test_analysis_render_non_unsatisfiable_temporal_and_unknown_solver(monkeypatch):
    temporal = analysis.TemporalAnalysis(decided=("a", "b"), pairs_decided=1, pairs_refused=0)
    text = analysis.render_analysis(
        analysis.PackAnalysis(
            pack_id="test", satisfiable=True, temporal=temporal
        )
    )
    assert "each satisfiable by some non-empty finite trace" in text
    assert "no temporal duty entails another" in text

    class UnknownSolver:
        def set(self, *args):
            pass

        def add(self, *args):
            pass

        def check(self):
            return analysis.z3.unknown

    monkeypatch.setattr(analysis.z3, "Solver", UnknownSolver)
    assert analysis._valid([], analysis.z3.BoolVal(True), 1) is None


def test_analysis_skips_requirement_when_encoding_refuses_it(monkeypatch):
    original = analysis._encoded

    def refuse(node, scope, what):
        raise analysis.UnsupportedConstructError("unsupported test construct")

    monkeypatch.setattr(analysis, "_encoded", refuse)
    result = analysis._satisfiability_and_relations(pack(req("bad", "present(a)")), 1000)

    assert result[0] is None and "unsupported test construct" in result[3][0]
    monkeypatch.setattr(analysis, "_encoded", original)


def test_joint_satisfiability_unknown_is_reported_without_guessing(monkeypatch):
    class UnknownSolver:
        def set(self, *args):
            pass

        def add(self, *args):
            pass

        def assert_and_track(self, *args):
            pass

        def check(self):
            return analysis.z3.unknown

        def unsat_core(self):
            return []

    monkeypatch.setattr(analysis.z3, "Solver", UnknownSolver)
    result = analysis._satisfiability_and_relations(
        pack(req("requirement", "present(signal)")), 1
    )

    assert result[0] is None
    assert "returned unknown" in result[4][0]


def test_relations_report_reverse_entailment_direction():
    result = analysis._satisfiability_and_relations(
        pack(
            req("weak", "present(a) or present(b)"),
            req("strong", "present(a)"),
        ),
        1000,
    )

    assert any(r.left == "strong" and r.right == "weak" and not r.equivalent for r in result[2])


def test_temporal_analysis_names_constructs_it_cannot_render(monkeypatch):
    monkeypatch.setattr(analysis, "available", lambda: True)
    temporal, skipped, notes = analysis._temporal_analysis(
        pack(req("past", "once(present(signal))", "temporal"))
    )

    assert temporal is not None and skipped
    assert "not decided as a finite-trace formula" in skipped[0]
    assert notes == []
