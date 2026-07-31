"""Tests for reasonsmith v0.2 core foundations (Stage 1)."""

from __future__ import annotations

import json
import pytest

from reasonsmith.report import (
    ConformanceReport,
    RequirementResult,
    analyze_unattainable,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.spec import Pack, Requirement, list_packs, load_pack
from reasonsmith.sut import FullCapabilitySUT, NoReasonsSUT
from reasonsmith.verdict import (
    Strength,
    Verdict,
    combine_verdicts,
    max_strength,
    min_strength,
)


def test_strength_lattice_ordering():
    """Strength lattice forms a strict total order: unattainable < observed < probed < proved."""
    assert Strength.UNATTAINABLE < Strength.OBSERVED
    assert Strength.OBSERVED < Strength.PROBED
    assert Strength.PROBED < Strength.PROVED

    # Transitive checks
    assert Strength.UNATTAINABLE < Strength.PROVED
    assert Strength.OBSERVED < Strength.PROVED

    # Min/max operations
    assert min_strength([Strength.PROVED, Strength.OBSERVED, Strength.UNATTAINABLE]) == Strength.UNATTAINABLE
    assert max_strength([Strength.PROVED, Strength.OBSERVED, Strength.UNATTAINABLE]) == Strength.PROVED

    # Parsing
    assert Strength.parse("unattainable") == Strength.UNATTAINABLE
    assert Strength.parse("PROVED") == Strength.PROVED
    with pytest.raises(ValueError, match="Unknown strength"):
        Strength.parse("invalid_strength")


def test_verdict_combination():
    """Verdict combination follows worst-case propagation: VIOLATED > INCONCLUSIVE > SATISFIED."""
    assert combine_verdicts([Verdict.SATISFIED, Verdict.SATISFIED]) == Verdict.SATISFIED
    assert combine_verdicts([Verdict.SATISFIED, Verdict.INCONCLUSIVE]) == Verdict.INCONCLUSIVE
    assert combine_verdicts([Verdict.SATISFIED, Verdict.VIOLATED]) == Verdict.VIOLATED
    assert combine_verdicts([Verdict.INCONCLUSIVE, Verdict.VIOLATED]) == Verdict.VIOLATED
    assert combine_verdicts([]) == Verdict.SATISFIED

    # String representation and parsing
    assert str(Verdict.SATISFIED) == "satisfied"
    assert Verdict.parse("violated") == Verdict.VIOLATED
    with pytest.raises(ValueError, match="Unknown verdict"):
        Verdict.parse("invalid_verdict")


def test_load_table7_pack():
    """Table 7 pack loads correctly from TOML with verbatim traceability."""
    packs = list_packs()
    assert "table7" in packs

    pack = load_pack("table7")
    assert pack.id == "table7"
    assert len(pack.requirements) == 6

    # Verify requirement fields
    req_gdpr = pack.get_requirement("gdpr_art22_meaningful_information")
    assert req_gdpr.source_document == "GDPR"
    assert req_gdpr.article_clause == "Art. 22 (and Rec. 71)"
    assert req_gdpr.verbatim_text == "Automated decisions: “meaningful information about the logic involved”"
    assert req_gdpr.formalism == "record"
    assert "reasons" in req_gdpr.requires

    req_ecoa = pack.get_requirement("ecoa_reg_b_adverse_action")
    assert req_ecoa.source_document == "ECOA / Reg B"
    assert "reasons" in req_ecoa.requires


def test_unattainable_analysis_no_execution():
    """Definition of Done test: A system declaring no 'reasons' capability is reported

    unattainable for reason-giving requirements with missing signals named, WITHOUT
    the system being executed at all.
    """
    no_reasons_sut = NoReasonsSUT()
    pack = load_pack("table7")

    # Pick the two reason-giving requirements specifically
    reason_reqs = [
        pack.get_requirement("gdpr_art22_meaningful_information"),
        pack.get_requirement("ecoa_reg_b_adverse_action"),
    ]

    for req in reason_reqs:
        is_unattainable, missing = analyze_unattainable(req, no_reasons_sut)
        assert is_unattainable is True
        assert "reasons" in missing

        result = evaluate_requirement(req, no_reasons_sut)
        assert result.strength == Strength.UNATTAINABLE
        assert result.verdict == Verdict.INCONCLUSIVE
        assert "reasons" in result.signals_missing

    # Crucial assertion: decisions() was NEVER executed
    assert no_reasons_sut.was_executed is False


def test_full_conformance_report():
    """FullCapabilitySUT achieves observed strength across all Table 7 requirements."""
    full_sut = FullCapabilitySUT()
    pack = load_pack("table7")

    report = check_conformance(full_sut, pack, system_name="FullReferenceModel")
    assert report.system_name == "FullReferenceModel"
    assert report.pack_id == "table7"
    assert len(report.results) == 6

    for res in report.results:
        assert res.strength == Strength.OBSERVED
        assert res.verdict == Verdict.SATISFIED
        assert res.signals_missing == ()

    assert report.headline == "6 requirements · 6 observed"

    # Serialization tests (house pattern)
    r_dict = report.to_dict()
    assert r_dict["headline"] == "6 requirements · 6 observed"
    assert r_dict["counts"]["observed"] == 6
    assert "limits" in r_dict

    r_json = report.to_json(indent=2)
    parsed = json.loads(r_json)
    assert parsed["system_name"] == "FullReferenceModel"
    assert parsed["counts"]["total"] == 6


def test_report_headline_with_unattainable():
    """Report headline correctly reflects unattainable requirements."""
    no_reasons_sut = NoReasonsSUT()
    pack = load_pack("table7")

    # Reason-giving pack subset
    reason_pack = Pack(
        id="reason_subset",
        title="Reason Requirements",
        description="Subset of reason-requiring duties",
        requirements=(
            pack.get_requirement("gdpr_art22_meaningful_information"),
            pack.get_requirement("ecoa_reg_b_adverse_action"),
        ),
    )

    report = check_conformance(no_reasons_sut, reason_pack, system_name="BlackBoxNeuralModel")
    assert "2 requirements · 2 unattainable" in report.headline
    assert no_reasons_sut.was_executed is False
