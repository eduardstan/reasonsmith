"""Tests for Stage 2 of reasonsmith v0.2 overhaul.

Covers:
- JSONL decision-log reader adapter (JSONLAdapter / JsonlSUT)
- Callable wrapper adapter (CallableAdapter / CallableSUT)
- Record engine (RecordEngine)
- Observed engine (ObservedEngine with rtamt)
- Three regulation packs (eu_ai_act, gdpr, ecoa)
- Section 6.3 taxonomy integration & verbatim legal quotes
- End-to-end definition of done CLI & conformance check path
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reasonsmith.adapters import CallableAdapter, JSONLAdapter
from reasonsmith.cli import main as cli_main
from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.engines.record import RecordEngine
from reasonsmith.report import check_conformance
from reasonsmith.spec import Requirement, list_packs, load_pack
from reasonsmith.sut import CAPABILITY_TAXONOMY, BaseSUT
from reasonsmith.verdict import Strength, Verdict


@pytest.fixture
def jsonl_fixture_file(tmp_path: Path) -> Path:
    """Fixture JSONL file with compliant decision records."""
    log_file = tmp_path / "decisions.jsonl"
    records = [
        {
            "artifact_logs_event_log": True,
            "artifact_logs_decision_record": {"id": "dec-1", "result": "approved"},
            "artifact_logs_reason_explanation": "Credit score 750 exceeds threshold",
            "provenance_model_version": "v1.2.0",
            "provenance_active_exceptions": [],
            "stability_signals_artifact_drift": 0.02,
            "scope_statements_explanation_scope": "local",
            "scope_statements_local_vs_global": "local",
            "scope_statements_approximation_vs_guarantee": "approximation",
            "provenance_constraint_set": ["rule_1", "rule_2"],
        },
        {
            "artifact_logs_event_log": True,
            "artifact_logs_decision_record": {"id": "dec-2", "result": "denied"},
            "artifact_logs_reason_explanation": "Debt-to-income ratio 0.45 exceeds 0.36 limit",
            "provenance_model_version": "v1.2.0",
            "provenance_active_exceptions": [],
            "stability_signals_artifact_drift": 0.01,
            "scope_statements_explanation_scope": "local",
            "scope_statements_local_vs_global": "local",
            "scope_statements_approximation_vs_guarantee": "approximation",
            "provenance_constraint_set": ["rule_1", "rule_2"],
        },
    ]
    with log_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return log_file


@pytest.fixture
def jsonl_violating_fixture_file(tmp_path: Path) -> Path:
    """Fixture JSONL file where some records have missing/blank required fields."""
    log_file = tmp_path / "violating_decisions.jsonl"
    records = [
        {
            "artifact_logs_event_log": True,
            "provenance_model_version": "v1.2.0",
            "artifact_logs_reason_explanation": "Valid reason",
        },
        {
            "artifact_logs_event_log": True,
            "provenance_model_version": "v1.2.0",
            "artifact_logs_reason_explanation": "",  # Blank -> absent
        },
    ]
    with log_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return log_file


class TestJSONLAdapter:
    """Tests for JSONL decision-log reader."""

    def test_derives_capabilities_honestly_from_full_presence(self, jsonl_fixture_file: Path):
        sut = JSONLAdapter(jsonl_fixture_file)
        caps = sut.capabilities()
        assert "artifact_logs_event_log" in caps
        assert "provenance_model_version" in caps
        assert "artifact_logs_reason_explanation" in caps
        assert sut.partially_present_fields == {}

    def test_partial_presence_excluded_from_capabilities(self, tmp_path: Path):
        log_file = tmp_path / "partial.jsonl"
        with log_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"a": 1, "b": 2}) + "\n")
            f.write(json.dumps({"a": 1}) + "\n")

        sut = JSONLAdapter(log_file)
        assert sut.capabilities() == {"a"}
        assert sut.partially_present_fields == {"b": (1, 2)}

    def test_explicit_declared_capabilities_override(self, jsonl_fixture_file: Path):
        sut = JSONLAdapter(
            jsonl_fixture_file,
            declared_capabilities={"provenance_model_version"},
        )
        assert sut.capabilities() == {"provenance_model_version"}

    def test_decisions_iterates_records(self, jsonl_fixture_file: Path):
        sut = JSONLAdapter(jsonl_fixture_file)
        records = list(sut.decisions())
        assert len(records) == 2
        assert records[0]["provenance_model_version"] == "v1.2.0"

    def test_invalid_json_raises_value_error(self, tmp_path: Path):
        log_file = tmp_path / "bad.jsonl"
        log_file.write_text("not json\n")
        with pytest.raises(ValueError, match="not valid JSON"):
            JSONLAdapter(log_file)


class TestCallableAdapter:
    """Tests for callable / model wrapper adapter."""

    def test_wraps_predict_method(self):
        class DummyModel:
            def predict(self, case):
                return {"decision": "approved", "score": case["income"] * 2}

        model = DummyModel()
        sut = CallableAdapter(
            target=model,
            declared_capabilities={"decision", "score"},
            test_inputs=[{"income": 50}, {"income": 100}],
        )
        assert sut.capabilities() == {"decision", "score"}
        records = list(sut.decisions())
        assert len(records) == 2
        assert records[0] == {"decision": "approved", "score": 100}

    def test_wraps_decide_method(self):
        class DummyDecider:
            def decide(self, case):
                return {"decision": "denied", "reason": "high risk"}

        sut = CallableAdapter(
            target=DummyDecider(),
            declared_capabilities={"decision", "reason"},
            test_inputs=[{"id": 1}],
        )
        records = list(sut.decisions())
        assert records[0]["reason"] == "high risk"

    def test_refuses_unsupported_target(self):
        sut = CallableAdapter(
            target=12345,
            declared_capabilities={"decision"},
        )
        with pytest.raises(TypeError, match="not callable"):
            sut.decide({"case": 1})


class TestRecordEngine:
    """Tests for RecordEngine completeness verification."""

    def test_record_engine_satisfied(self, jsonl_fixture_file: Path):
        sut = JSONLAdapter(jsonl_fixture_file)
        req = Requirement(
            id="req_rec",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="record",
            spec="Record check",
            requires=("provenance_model_version", "artifact_logs_event_log"),
        )
        records = list(sut.decisions())
        result = RecordEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.SATISFIED
        assert result.strength == Strength.OBSERVED

    def test_record_engine_violated_on_blank_field(self, jsonl_violating_fixture_file: Path):
        sut = JSONLAdapter(
            jsonl_violating_fixture_file,
            declared_capabilities={"provenance_model_version", "artifact_logs_reason_explanation"},
        )
        req = Requirement(
            id="req_rec_viol",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="record",
            spec="Record check",
            requires=("provenance_model_version", "artifact_logs_reason_explanation"),
        )
        records = list(sut.decisions())
        result = RecordEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.strength == Strength.OBSERVED
        assert "artifact_logs_reason_explanation" in result.details["signals_absent_from_trace"]


class TestObservedEngine:
    """Tests for ObservedEngine temporal monitors."""

    def test_temporal_satisfied(self):
        sut = BaseSUT({"signal_a", "signal_b"})
        req = Requirement(
            id="temp_sat",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always((signal_a >= 0.5) -> (signal_b >= 0.5))",
            requires=("signal_a", "signal_b"),
        )
        records = [
            {"signal_a": True, "signal_b": True},
            {"signal_a": False, "signal_b": False},
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.SATISFIED
        assert result.strength == Strength.OBSERVED

    def test_temporal_violated_returns_offending_segment(self):
        sut = BaseSUT({"signal_a", "signal_b"})
        req = Requirement(
            id="temp_viol",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="(signal_a >= 0.5) -> (signal_b >= 0.5)",
            requires=("signal_a", "signal_b"),
        )
        records = [
            {"signal_a": True, "signal_b": True, "id": 0},
            {"signal_a": True, "signal_b": False, "id": 1},  # Violated at t=1
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.strength == Strength.OBSERVED
        assert "offending_trace_segment" in result.details
        offending = result.details["offending_trace_segment"]
        assert offending[0]["id"] == 1

    def test_unexpressible_formula_reports_not_evaluated(self):
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_unexp",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="invalid syntax !@#$%",
            requires=("signal_a",),
        )
        records = [{"signal_a": True}]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert "Not evaluated" in result.evidence_summary


class TestRegulationPacks:
    """Tests for EU AI Act, GDPR, and ECOA regulation packs."""

    @pytest.mark.parametrize("pack_name", ["eu_ai_act", "gdpr", "ecoa"])
    def test_pack_loads_and_validates(self, pack_name: str):
        assert pack_name in list_packs()
        pack = load_pack(pack_name)
        assert pack.id == pack_name
        assert len(pack.requirements) >= 3
        for req in pack.requirements:
            assert req.verbatim_text.strip()
            assert req.source_document.strip()
            assert req.article_clause.strip()
            # Verify Section 6.3 taxonomy prefixes or categories
            for signal in req.requires:
                assert any(
                    signal.startswith(cat) for cat in CAPABILITY_TAXONOMY
                ), (
                    f"Signal {signal!r} in pack {pack_name} must belong to "
                    f"Section 6.3 taxonomy {CAPABILITY_TAXONOMY}"
                )

    @pytest.mark.parametrize("pack_name", ["eu_ai_act", "gdpr", "ecoa"])
    def test_pack_quotes_found_verbatim_in_legal_sources_report(self, pack_name: str):
        """Every requirement quote in the regulation packs must be found character-for-character
        in data/rs-legal-sources/report.md.
        """
        report_path = Path("data/rs-legal-sources/report.md")
        assert report_path.is_file(), f"Legal sources report missing at {report_path}"
        report_text = report_path.read_text(encoding="utf-8")

        pack = load_pack(pack_name)
        for req in pack.requirements:
            assert req.verbatim_text in report_text, (
                f"Requirement {req.id!r} in pack {pack_name!r} has verbatim_text not found "
                f"verbatim in data/rs-legal-sources/report.md:\n{req.verbatim_text!r}"
            )


class TestDefinitionOfDoneEndToEnd:
    """End-to-end definition of done verification."""

    def test_end_to_end_conformance_check(self, jsonl_fixture_file: Path):
        sut = JSONLAdapter(jsonl_fixture_file)
        pack = load_pack("eu_ai_act")

        report = check_conformance(sut, pack, system_name="MyProductionSystem")

        # Every requirement has a clause citation on its rendered line
        text = report.render_text()
        for req in pack.requirements:
            assert f"({req.source_document} {req.article_clause})" in text

        # Report headline contains counts
        assert "requirements" in report.headline
        assert report.counts["total"] == len(pack.requirements)

    def test_cli_command_end_to_end(self, jsonl_fixture_file: Path, capsys):
        rc = cli_main(["check", "--system", str(jsonl_fixture_file), "--pack", "gdpr"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "CONFORMANCE REPORT" in captured.out
        assert "gdpr" in captured.out
