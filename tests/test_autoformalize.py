"""Soundness tests for the model-free autoformalisation gates."""

from __future__ import annotations

from pathlib import Path

import pytest

import reasonsmith.autoformalize as harness
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


def test_harness_has_no_model_or_conformance_surface():
    source = Path(harness.__file__).read_text()
    assert "RequirementResult" not in source
    assert "check_conformance" not in source
    assert "evaluate_requirement" not in source
