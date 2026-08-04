"""Tests for `reasonsmith.analysis` — the pack read as a set of formulas.

What this module is for:
  `analysis.py` answers four questions about a pack that no other code path can: joint
  satisfiability, entailment between requirements, vacuous discharge, and how many mutants of a
  system's declared rules each duty notices. The first three rest on the Z3 encoding in
  `engines/proved.py`, which is the point: there is one encoding, and these tests check that the
  analysis reaches the same answers the engine would.

What a reader must not break:
  - `test_vacuity_coincides_with_the_unreachable_trigger_rule` is the acceptance test of the whole
    vacuity definition, not an extra. `report.not_evaluated_for_unreachable_trigger` catches an
    implication whose antecedent nothing satisfies; that is exactly the case where the
    implication's *consequent* is a replaceable subformula, so the two must agree wherever the
    engine reaches a verdict at all.
    Why this matters: a vacuity rule that diverges from the one already shipped is either a false
    alarm generator or a silent widening of an existing refusal, and both make the analysis
    ignorable. A disagreement is a finding to report, not a definition to loosen.
  - No test here asserts a mutation *score*. The numbers move whenever the example system's rules
    or the mutation operators change, and pinning one would make an honest improvement look like a
    regression.
    Why this matters: the score is a measurement about a pack and a system, and this suite is not
    where a measurement lives — `RESULTS.md` is, with the commit it was taken at.
"""

from __future__ import annotations

import ast

import pytest

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.analysis import (
    MUTATION_LIMIT,
    analyse_pack,
    mutate_rules,
    render_analysis,
    vacuous_subformulas,
)
from reasonsmith.cli import main as cli_main
from reasonsmith.engines.proved import ProvedEngine, encode_logic_domain
from reasonsmith.examples.symbolic_rules import system_under_test as symbolic_system
from reasonsmith.report import VACUOUS_TRIGGER_KEY
from reasonsmith.rulelang import implication_antecedent, parse_property
from reasonsmith.spec import load_pack

#: A creditor that records no reason at all, so `present(artifact_logs_reason_explanation)` — the
#: antecedent of two shipped ECOA duties — is false for every input its logic admits. This is the
#: case `report.not_evaluated_for_unreachable_trigger` exists for.
_SILENT_RULES = [
    'artifact_logs_reason_explanation = ""',
    'artifact_logs_decision_record = "adverse action taken on this application"',
    'provenance_model_version = "silent-2026.01"',
    'scope_statements_local_vs_global = "global"',
]

_SILENT_VARIABLES = {
    "artifact_logs_reason_explanation": "str",
    "artifact_logs_decision_record": "str",
    "provenance_model_version": "str",
    "scope_statements_local_vs_global": "str",
}


def _silent_system() -> RulesAdapter:
    return RulesAdapter(rules=_SILENT_RULES, variables=_SILENT_VARIABLES)


def _consequent(spec: str) -> str:
    """The consequent of a spec that is one implication, as the analysis would print it."""
    node = parse_property(spec)
    assert implication_antecedent(node) is not None, f"{spec!r} is not an implication"
    body = node.body
    while not (isinstance(body, ast.Call) and body.func.id in ("implies", "Implies")):
        body = body.args[0]
    return ast.unparse(body.args[1])


def _vacuous_over_declared_logic(spec: str, sut) -> tuple[str, ...]:
    scope, solver, _, _ = encode_logic_domain(sut.logic())
    return vacuous_subformulas(parse_property(spec), scope, list(solver.assertions()))


def test_the_eu_ai_act_logging_duties_are_reported_equivalent():
    """The acceptance case: found by the tool, with no human reading either TOML block."""
    analysis = analyse_pack(load_pack("eu_ai_act"))
    equivalences = {
        frozenset((relation.left, relation.right))
        for relation in analysis.relations
        if relation.equivalent
    }
    assert (
        frozenset(
            ("eu_ai_act_art12_1_automatic_logging", "eu_ai_act_art12_2_traceability_monitoring")
        )
        in equivalences
    )


def test_every_shipped_pack_is_jointly_satisfiable():
    """A pack whose duties contradict each other reports every system violated for its own
    reason, which is the pack's defect and not the system's."""
    for name in ("ecoa", "eu_ai_act", "gdpr", "gpai", "table7"):
        analysis = analyse_pack(load_pack(name))
        assert analysis.satisfiable is True, f"{name}: {analysis.unsatisfiable_core}"


def test_a_contradictory_pack_is_reported_unsatisfiable_with_its_core(tmp_path):
    """The check has to be able to fail, and to name which duties cannot hold together."""
    pack_file = tmp_path / "contradictory.toml"
    block = """
[[requirement]]
id = "{id}"
source_document = "Test"
article_clause = "{clause}"
verbatim_text = "text"
stakeholder = "auditor"
formalism = "{formalism}"
spec = "{spec}"
rationale = "prose"
requires = ["reason"]
binding = false
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
"""
    pack_file.write_text(
        '[pack]\nid = "contradictory"\n'
        + block.format(id="must_state", clause="1", spec="present(reason)", formalism="record")
        + block.format(
            id="must_not_state", clause="2", spec="not present(reason)", formalism="logical"
        ),
        encoding="utf-8",
    )
    analysis = analyse_pack(load_pack(pack_file))
    assert analysis.satisfiable is False
    assert set(analysis.unsatisfiable_core) == {"must_state", "must_not_state"}


def test_the_counterfactual_fragment_is_skipped_by_name_and_never_answered():
    """A question the encoding cannot reach is named, because silence reads as nothing found."""
    analysis = analyse_pack(load_pack("ecoa"))
    assert any(
        "ecoa_reg_b_1002_4_a_no_disparate_treatment" in reason for reason in analysis.skipped
    )
    assert all(
        finding.requirement_id != "ecoa_reg_b_1002_4_a_no_disparate_treatment"
        for finding in analysis.vacuities
    )


def test_vacuity_coincides_with_the_unreachable_trigger_rule():
    """The acceptance test of the definition: the shipped special case and the general rule agree.

    `report.not_evaluated_for_unreachable_trigger` fires when an implication's antecedent is
    unsatisfiable over the engine's domain. Over that same domain the implication then holds
    whatever its consequent says, so the consequent is a replaceable subformula — and if the
    consequent is replaceable, taking the replacement to be a contradiction gives that the
    antecedent is false everywhere. The two are the same fact, and this asserts it on every shipped
    implication against a system whose trigger fires and one whose trigger never does.
    """
    compared = 0
    for system in (symbolic_system(), _silent_system()):
        for pack_name in ("ecoa", "gdpr"):
            for req in load_pack(pack_name).requirements:
                if req.formalism != "logical" or implication_antecedent(
                    parse_property(req.spec)
                ) is None:
                    continue
                result = ProvedEngine.evaluate(req, system)
                engine_says_vacuous = VACUOUS_TRIGGER_KEY in result.details
                if not engine_says_vacuous and result.strength is None:
                    # The engine reached no verdict for some other reason — an unassigned signal,
                    # an unsupported construct — so there is nothing to agree or disagree with.
                    continue
                analysis_says_vacuous = _consequent(req.spec) in _vacuous_over_declared_logic(
                    req.spec, system
                )
                assert engine_says_vacuous == analysis_says_vacuous, (
                    f"{req.id}: the unreachable-trigger rule says {engine_says_vacuous} and the "
                    f"vacuity rule says {analysis_says_vacuous} over the same domain"
                )
                compared += 1
    assert compared, "no implication was compared, so this test asserted nothing"


def test_the_unreachable_trigger_case_is_actually_exercised():
    """The coincidence above is worth nothing if neither side ever says yes."""
    system = _silent_system()
    req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_b_2_specific_reasons")
    assert VACUOUS_TRIGGER_KEY in ProvedEngine.evaluate(req, system).details
    assert _consequent(req.spec) in _vacuous_over_declared_logic(req.spec, system)


def test_the_general_rule_catches_a_vacuous_pass_the_trigger_rule_does_not():
    """The findings worth having: a satisfied duty part of whose property does no work.

    `ecoa_reg_b_1002_9_a_1_timing_of_notice` is `proved` satisfied against the shipped symbolic
    system, so the trigger rule says nothing about it. Its 90-day counteroffer branch is
    nevertheless replaceable by any formula: the system's own batch window bounds the latency below
    thirty days, so the first disjunct settles the duty on every admissible input.
    """
    system = symbolic_system()
    req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
    assert VACUOUS_TRIGGER_KEY not in ProvedEngine.evaluate(req, system).details
    findings = _vacuous_over_declared_logic(
        "present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30)"
        " or ((artifact_logs_counteroffer_not_accepted >= 0.5) and "
        "(artifact_logs_notification_latency_days <= 90)))",
        system,
    )
    assert any("artifact_logs_counteroffer_not_accepted >= 0.5" in finding for finding in findings)


def test_no_shipped_pack_is_vacuous_on_its_own_formulas():
    """Without a system the domain is every assignment, where only a tautology is vacuous.

    A duty reported vacuous here would be one no evidence whatever could make matter, which is a
    defect in the property rather than a fact about a system. That none is reported is also what
    keeps the pack-only rendering free of the false alarms a looser definition would print.
    """
    for name in ("ecoa", "eu_ai_act", "gdpr", "gpai", "table7"):
        assert analyse_pack(load_pack(name)).vacuities == ()


def test_a_mutant_is_one_change_and_the_rules_still_parse():
    mutants = mutate_rules(["approved = score >= 640 and history > 12"])
    labels = {label for label, _ in mutants}
    assert any("640" in label for label in labels)
    assert any(">=" in label for label in labels)
    for _, rules in mutants:
        assert len(rules) == 1
        ast.parse(rules[0], mode="exec")
    assert all(rules != ["approved = score >= 640 and history > 12"] for _, rules in mutants)


def test_a_mutation_score_travels_with_its_limit_and_a_system_without_rules_gets_none():
    """A score reaches only a system exposing rules, and never travels without what it is not."""
    analysis = analyse_pack(load_pack("ecoa"), symbolic_system())
    assert analysis.mutation, "the shipped symbolic system exposes rules, so it must be scored"
    assert all(score.mutants > 0 for score in analysis.mutation)
    assert MUTATION_LIMIT in render_analysis(analysis)

    log_only = analyse_pack(load_pack("ecoa"))
    assert log_only.mutation == ()
    assert any("nothing to mutate" in note for note in log_only.notes)


def test_a_duty_no_mutant_moves_is_named_as_having_no_discriminating_power():
    analysis = analyse_pack(load_pack("ecoa"), symbolic_system())
    blind = [score.requirement_id for score in analysis.mutation if score.detected == 0]
    rendered = render_analysis(analysis)
    if blind:
        assert "no discriminating power against these mutants" in rendered
        for req_id in blind:
            assert req_id in rendered


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["validate-pack", "eu_ai_act", "--analyse"], 0),
        (["validate-pack", "eu_ai_act"], 0),
    ],
)
def test_analyse_prints_findings_and_leaves_the_exit_code_alone(capsys, argv, expected):
    assert cli_main(argv) == expected
    out = capsys.readouterr().out
    assert ("analysis: eu_ai_act" in out) == ("--analyse" in argv)


def test_system_module_without_analyse_is_a_usage_error(capsys):
    rc = cli_main(
        ["validate-pack", "ecoa", "--system-module", "reasonsmith.examples.symbolic_rules:"
         "system_under_test"]
    )
    assert rc == 1
    assert "--analyse" in capsys.readouterr().err
