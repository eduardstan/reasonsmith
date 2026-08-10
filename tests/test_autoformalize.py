"""Soundness tests for the model-free autoformalisation gates."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import reasonsmith.autoformalize as harness
import reasonsmith.proposer as proposer
from reasonsmith.spec import list_packs, load_pack


def _requirements():
    return {
        req.id: req
        for pack_name in list_packs()
        for req in load_pack(pack_name).requirements
    }


def test_shipped_challenge_sets_are_two_way_complete_and_lawyer_readable():
    sets = harness.load_challenge_sets()
    requirements = _requirements()
    assert set(sets) <= set(requirements)
    assert sets
    for requirement_id, challenge in sets.items():
        assert challenge.requirement_id == requirement_id
        assert challenge.rationale.strip()
        assert {case.kind for case in challenge.cases} >= {"satisfied", "violated", "near-miss"}
        assert all(case.description.strip() for case in challenge.cases)


def test_the_shipped_properties_clear_both_machine_gates():
    requirements = _requirements()
    for requirement_id in harness.challenge_requirements():
        req = requirements[requirement_id]
        assert harness.round_trip_check(req, req.spec).passed
        assert harness.check_challenges(req, req.spec).passed
        assert harness.candidate_ready(req, req.spec)
        assert not harness.candidate_acceptable(req, req.spec)


def test_round_trip_reports_stronger_weaker_and_incomparable_without_rewriting():
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]
    stronger_candidate = (
        "present(artifact_logs_event_log) and present(provenance_model_version) and present(extra)"
    )
    stronger = harness.round_trip_check(req, stronger_candidate)
    weaker = harness.round_trip_check(req, "present(artifact_logs_event_log)")
    logical_req = _requirements()["ecoa_reg_b_1002_9_b_2_specific_reasons"]
    incomparable = harness.round_trip_check(
        logical_req,
        "present(artifact_logs_reason_explanation) or present(provenance_model_version)",
    )
    assert stronger.status == "stronger" and stronger.witness
    assert weaker.status == "weaker" and weaker.witness
    assert incomparable.status == "incomparable" and incomparable.witness
    assert not stronger.passed and not weaker.passed and not incomparable.passed
    assert stronger.candidate == stronger_candidate
    assert "stricter" in stronger.repair_message
    assert "weaker" in weaker.repair_message
    assert "both directions" in incomparable.repair_message
    assert "equivalent" in harness.round_trip_check(req, req.spec).repair_message
    assert "cannot be compared" in harness.round_trip_check(req, "present(bad").repair_message


RECORD_CHALLENGE_REQUIREMENTS = frozenset({
    "eu_ai_act_art12_2_traceability_monitoring",
    "eu_ai_act_art13_1_transparency_deployers",
    "eu_ai_act_art13_2_instructions_for_use",
    "eu_ai_act_art13_transparency",
    "eu_ai_act_art12_record_keeping",
    "gdpr_art22_meaningful_information",
    "ecoa_reg_b_adverse_action",
    "fda_gmlp_samd",
    "nist_ai_rmf_risk_evidence",
    "gdpr_art22_1_automated_decision_prohibition",
    "gdpr_art22_3_safeguards_human_intervention",
    "gdpr_recital71_meaningful_explanation",
    "eu_ai_act_art53_1_a_technical_documentation",
    "eu_ai_act_art53_1_b_downstream_documentation",
    "eu_ai_act_art53_1_c_copyright_policy",
    "eu_ai_act_art53_1_d_training_content_summary",
    "eu_ai_act_art55_1_a_model_evaluation",
    "eu_ai_act_art55_1_b_systemic_risk_assessment",
    "eu_ai_act_art55_1_c_serious_incident_reporting",
    "eu_ai_act_art55_1_d_cybersecurity_protection",
})


@pytest.mark.parametrize("requirement_id", sorted(RECORD_CHALLENGE_REQUIREMENTS))
def test_each_added_record_set_catches_a_dropped_required_field(requirement_id):
    """A plausible AND-to-OR/omitted-field candidate must fail its gold cases."""
    req = _requirements()[requirement_id]
    fields = re.findall(r"present\(([^)]+)\)", req.spec)
    assert len(fields) >= 2
    for omitted in fields:
        candidate = " and ".join(
            f"present({field})" for field in fields if field != omitted
        )
        check = harness.check_challenges(req, candidate)
        assert not check.passed
        assert any(
            case.case_id == "missing-" + omitted.replace("_", "-")
            for case in check.failures
        )


def test_principal_reasons_set_catches_omitting_the_deletion_bound():
    req = _requirements()["ecoa_reg_b_1002_9_b_2_principal_reasons_complete"]
    candidate = "present(artifact_logs_reason_explanation)"
    check = harness.check_challenges(req, candidate)
    assert not check.passed
    assert {case.case_id for case in check.failures} >= {
        "complete-reasons", "deleted-principal-reason"
    }


def test_challenge_scope_rejects_missing_or_wrong_typed_signal():
    with pytest.raises(ValueError, match="does not provide"):
        harness._ChallengeScope({}, {}).read("missing")
    with pytest.raises(ValueError, match="must be true or false"):
        harness._ChallengeScope({"flag": "bool"}, {"flag": 1}).read("flag")


def test_challenge_scope_reads_declared_scalar_types():
    scope = harness._ChallengeScope(
        {"count": "int", "text": "str", "amount": "real"},
        {"count": 2, "text": "notice", "amount": 1.5},
    )
    assert str(scope.read("count")) == "2"
    assert str(scope.read("text")) == '"notice"'
    assert str(scope.read("amount")) == "3/2"
    with pytest.raises(ValueError, match="must be an integer"):
        harness._ChallengeScope({"count": "int"}, {"count": 1.5}).read("count")
    with pytest.raises(ValueError, match="must be text"):
        harness._ChallengeScope({"text": "str"}, {"text": 1}).read("text")
    with pytest.raises(ValueError, match="must be numeric"):
        harness._ChallengeScope({"amount": "real"}, {"amount": "bad"}).read("amount")




def test_wrong_specific_reasons_candidate_is_caught_by_near_misses():
    req = _requirements()["ecoa_reg_b_1002_9_b_2_specific_reasons"]
    candidate = "present(artifact_logs_reason_explanation)"
    check = harness.check_challenges(req, candidate)
    assert not check.passed
    assert any(case.case_id == "missing-provenance" for case in check.failures)
    assert not harness.candidate_ready(req, candidate)


def test_fragment_mismatch_is_refused_not_downgraded():
    req = _requirements()["eu_ai_act_art12_1_automatic_logging"]
    candidate = "present(artifact_logs_event_log) or present(provenance_model_version)"
    result = harness.round_trip_check(req, candidate)
    assert result.status == "refused"
    assert "fragment" in result.reason


def test_human_signoff_is_explicitly_separate_from_machine_gates():
    for requirement_id in harness.challenge_requirements():
        record = harness.signoff(requirement_id)
        assert record.status == "pending"
        assert not record.signed


def test_challenge_loader_rejects_unknown_case_fields(tmp_path: Path):
    path = tmp_path / "bad.toml"
    path.write_text('''requirement = "eu_ai_act_art12_1_automatic_logging"
rationale = "why"
[[case]]
id = "x"
kind = "satisfied"
expected = "satisfied"
description = "d"
signals = {}
extra = true
''')
    with pytest.raises(ValueError, match="fields mismatch"):
        harness._load_file(path)


def test_challenge_loader_rejects_duplicate_case_ids(tmp_path: Path):
    path = tmp_path / "bad.toml"
    path.write_text('''requirement = "eu_ai_act_art12_1_automatic_logging"
rationale = "why"
[[case]]
id = "x"
kind = "satisfied"
expected = "satisfied"
description = "d"
signals = {}
[[case]]
id = "x"
kind = "violated"
expected = "violated"
description = "d"
signals = {}
''')
    with pytest.raises(ValueError, match="case ids"):
        harness._load_file(path)


def test_harness_and_proposer_have_no_conformance_surface():
    from types import ModuleType

    for module in (harness, proposer):
        bound_names = vars(module)
        bound_modules = {
            value.__name__ for value in bound_names.values() if isinstance(value, ModuleType)
        }
        assert "RequirementResult" not in bound_names
        assert "check_conformance" not in bound_names
        assert "evaluate_requirement" not in bound_names
        assert "reasonsmith.conformance" not in bound_modules
        assert not any(name.startswith("reasonsmith.engines") for name in bound_modules)

TEMPORAL_CHALLENGE_REQUIREMENTS = frozenset(
    {
        "gdpr_recital71_error_risk_minimised",
        "ecoa_reg_b_1002_9_a_1_timing_of_notice",
        "ecoa_reg_b_1002_9_a_2_written_statement",
        "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out",
    }
)


def test_new_challenge_shapes_are_explicit_and_baselines_pass():
    requirements = _requirements()
    sets = harness.load_challenge_sets()
    for requirement_id in TEMPORAL_CHALLENGE_REQUIREMENTS:
        assert sets[requirement_id].formalism == "temporal"
        assert all(case.shape == "trace" and case.trace for case in sets[requirement_id].cases)
        assert harness.check_challenges(
            requirements[requirement_id], requirements[requirement_id].spec
        ).passed
    counterfactual = sets["ecoa_reg_b_1002_4_a_no_disparate_treatment"]
    assert counterfactual.formalism == "counterfactual"
    assert all(case.shape == "pair" and case.pairs for case in counterfactual.cases)
    req = requirements[counterfactual.requirement_id]
    assert harness.check_challenges(req, req.spec).passed


@pytest.mark.parametrize(
    ("requirement_id", "candidate", "case_id"),
    [
        (
            "gdpr_recital71_error_risk_minimised",
            "always(scope_statements_declared_deviation < artifact_logs_decision_margin)",
            "equal-is-not-breach",
        ),
        (
            "ecoa_reg_b_1002_9_a_1_timing_of_notice",
            (
                "always(present(artifact_logs_decision_record) -> "
                "((artifact_logs_notification_latency_days < 30) or "
                "((artifact_logs_counteroffer_not_accepted >= 0.5) and "
                "(artifact_logs_notification_latency_days < 90))))"
            ),
            "thirty-day-boundary",
        ),
        (
            "ecoa_reg_b_1002_9_a_2_written_statement",
            (
                "always(present(artifact_logs_decision_record) and "
                "present(provenance_model_version) and "
                "present(artifact_logs_reason_explanation))"
            ),
            "right-to-reasons-branch",
        ),
        (
            "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out",
            (
                "always(present(artifact_logs_incompleteness_notice_sent) -> "
                "(present(artifact_logs_action_taken_notification) or "
                "present(artifact_logs_response_period_lapsed)))"
            ),
            "notice-then-action",
        ),
    ],
)
def test_temporal_gold_cases_discriminate_plausible_wrong_candidates(
    requirement_id, candidate, case_id
):
    req = _requirements()[requirement_id]
    check = harness.check_challenges(req, candidate)
    assert not check.passed
    assert any(case.case_id == case_id for case in check.failures)


def test_counterfactual_pairs_require_the_named_intervention_and_outcome():
    req = _requirements()["ecoa_reg_b_1002_4_a_no_disparate_treatment"]
    wrong_protected = harness.check_challenges(
        req,
        (
            "counterfactually_invariant("
            "artifact_logs_decision_record, artifact_logs_notification_latency_days)"
        ),
    )
    wrong_outcome = harness.check_challenges(
        req,
        (
            "counterfactually_invariant("
            "artifact_logs_notification_latency_days, applicant_prohibited_basis)"
        ),
    )
    assert not wrong_protected.passed and not wrong_outcome.passed
    assert any(case.case_id == "same-decision-across-basis" for case in wrong_protected.failures)
    assert any(case.case_id == "decision-changes-across-basis" for case in wrong_outcome.failures)


def test_loader_rejects_empty_trace_and_malformed_pairs(tmp_path: Path):
    trace = tmp_path / "trace.toml"
    trace.write_text("""formalism = \"temporal\"
requirement = \"gdpr_recital71_error_risk_minimised\"
rationale = \"why\"
[[case]]
id = \"empty\"
kind = \"satisfied\"
expected = \"satisfied\"
description = \"d\"
trace = []
""")
    with pytest.raises(ValueError, match="non-empty"):
        harness._load_file(trace)
    pair = tmp_path / "pair.toml"
    pair.write_text("""formalism = \"counterfactual\"
requirement = \"ecoa_reg_b_1002_4_a_no_disparate_treatment\"
rationale = \"why\"
[[case]]
id = \"bad\"
kind = \"satisfied\"
expected = \"satisfied\"
description = \"d\"
pairs = [{}]
""")
    with pytest.raises(ValueError, match="left and right"):
        harness._load_file(pair)


def test_challenge_case_pair_compatibility_view():
    case = harness.ChallengeCase(
        "pair", "satisfied", "satisfied", "description", {},
        pairs=(({"x": 0}, {"x": 1}),),
    )
    assert case.pair == ({"x": 0}, {"x": 1})
