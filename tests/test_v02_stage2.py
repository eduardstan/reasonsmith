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
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.rulelang import parse_property, signal_names
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

    def test_partial_presence_is_a_capability_and_a_trace_gap(self, tmp_path: Path):
        """A field emitted once is a capability; the record it is missing from is a violation.

        Reporting it as a missing capability would say the system cannot emit a signal it
        demonstrably did emit, and would put a trace gap beyond the reach of any engine.
        """
        log_file = tmp_path / "partial.jsonl"
        with log_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"a": 1, "b": 2}) + "\n")
            f.write(json.dumps({"a": 1}) + "\n")

        sut = JSONLAdapter(log_file)
        assert sut.capabilities() == {"a", "b"}
        assert sut.partially_present_fields == {"b": (1, 2)}

    def test_partially_present_signal_is_reported_violated_not_unattainable(
        self, jsonl_violating_fixture_file: Path
    ):
        from reasonsmith.report import evaluate_requirement

        sut = JSONLAdapter(jsonl_violating_fixture_file)
        req = Requirement(
            id="req_partial",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="record",
            spec="present(artifact_logs_reason_explanation)",
            rationale="Why this duty exists, in English.",
            requires=("artifact_logs_reason_explanation",),
            binding=True,
            scope="",
            domains=(),
        )
        result = evaluate_requirement(req, sut)
        assert result.verdict == Verdict.VIOLATED
        assert result.strength == Strength.OBSERVED
        assert result.signals_missing == ()

    def test_unattainable_from_a_trace_does_not_speak_for_the_system(
        self, jsonl_violating_fixture_file: Path
    ):
        from reasonsmith.report import evaluate_requirement

        sut = JSONLAdapter(jsonl_violating_fixture_file)
        req = Requirement(
            id="req_never_emitted",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="record",
            spec="present(scope_statements_explanation_scope)",
            rationale="Why this duty exists, in English.",
            requires=("scope_statements_explanation_scope",),
            binding=True,
            scope="",
            domains=(),
        )
        result = evaluate_requirement(req, sut)
        assert result.strength == Strength.UNATTAINABLE
        assert "supplied decision trace" in result.evidence_summary
        assert "the system declares no capability" not in result.evidence_summary

    def test_declared_capabilities_word_the_finding_as_about_the_system(
        self, jsonl_violating_fixture_file: Path
    ):
        """The other half of the wording the sut.py docstring describes: declared, not trace."""
        from reasonsmith.report import evaluate_requirement

        sut = JSONLAdapter(
            jsonl_violating_fixture_file,
            declared_capabilities={"provenance_model_version"},
        )
        assert sut.capability_basis == "declared"
        req = Requirement(
            id="req_never_emitted",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="record",
            spec="present(scope_statements_explanation_scope)",
            rationale="Why this duty exists, in English.",
            requires=("scope_statements_explanation_scope",),
            binding=True,
            scope="",
            domains=(),
        )
        result = evaluate_requirement(req, sut)
        assert result.strength == Strength.UNATTAINABLE
        assert "Unattainable as built" in result.evidence_summary
        assert "supplied decision trace" not in result.evidence_summary

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

    def test_inline_jsonl_string_longer_than_the_filename_limit(self):
        """A realistic inline trace exceeds the OS filename limit; it is text, not a path."""
        text = "\n".join(
            json.dumps({"decision_id": f"app-{i}", "artifact_logs_reason_explanation": "x" * 60})
            for i in range(4)
        )
        assert len(text) > 255
        sut = JSONLAdapter(text)
        assert len(list(sut.decisions())) == 4
        assert "artifact_logs_reason_explanation" in sut.capabilities()

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


def test_record_and_temporal_formalisms_route_through_report():
    sut = BaseSUT({"signal_a", "signal_b"})
    records = [
        {"signal_a": True, "signal_b": True},
        {"signal_a": False, "signal_b": False},
    ]

    def requirement(formalism: str, spec: str) -> Requirement:
        return Requirement(
            id=f"route_{formalism}",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism=formalism,
            spec=spec,
            rationale="Why this duty exists, in English.",
            requires=("signal_a", "signal_b"),
            binding=True,
            scope="",
            domains=(),
        )

    record = evaluate_requirement(
        requirement("record", "present(signal_a) and present(signal_b)"), sut, records
    )
    temporal = evaluate_requirement(
        requirement("temporal", "always((signal_a >= 0.5) -> (signal_b >= 0.5))"),
        sut,
        records,
    )

    assert record.verdict == Verdict.SATISFIED
    assert record.details == {"records_observed": 2}
    assert temporal.verdict == Verdict.SATISFIED
    assert "evaluation_scores" in temporal.details


@pytest.mark.parametrize(
    "value",
    [pytest.param(0, id="zero"), pytest.param(False, id="false")],
)
def test_temporal_presence_agrees_with_record_presence_for_falsy_values(value):
    sut = BaseSUT({"signal_a"})
    records = [{"signal_a": value}, {"signal_a": value}]
    fields = {
        "source_document": "Doc",
        "article_clause": "Art 1",
        "verbatim_text": "Quote",
        "stakeholder": "deployer",
        "rationale": "A value was recorded.",
        "requires": ("signal_a",),
        "binding": True,
        "scope": "",
        "domains": (),
    }
    record = Requirement(
        id="record_presence", formalism="record", spec="present(signal_a)", **fields
    )
    temporal = Requirement(
        id="temporal_presence",
        formalism="temporal",
        spec="always(present(signal_a))",
        **fields,
    )

    assert RecordEngine.evaluate(record, sut, records).verdict == Verdict.SATISFIED
    assert ObservedEngine.evaluate(temporal, sut, records).verdict == Verdict.SATISFIED


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
            spec="present(provenance_model_version) and present(artifact_logs_event_log)",
            rationale="Why this duty exists, in English.",
            requires=("provenance_model_version", "artifact_logs_event_log"),
            binding=True,
            scope="",
            domains=(),
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
            spec="present(provenance_model_version) and present(artifact_logs_reason_explanation)",
            rationale="Why this duty exists, in English.",
            requires=("provenance_model_version", "artifact_logs_reason_explanation"),
            binding=True,
            scope="",
            domains=(),
        )
        records = list(sut.decisions())
        result = RecordEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.strength == Strength.OBSERVED
        assert "artifact_logs_reason_explanation" in result.details["signals_absent_from_trace"]

    def test_the_record_engine_evaluates_its_spec(self, jsonl_fixture_file: Path):
        """A `record` duty is discharged by the property in its `spec`, not by its `requires`.

        `spec` used to be free prose for a record duty and no engine read it, so two requirements
        differing only in that field produced the identical verdict and a reader who took a record
        verdict as a claim about the `spec` text was reading something nothing checked. It is now
        a formula in one language with the other fragments, and this test is what says so: the
        signals the engine looks for are the `present()` atoms the property names, and a `spec`
        this engine cannot walk as a conjunction of them is not evaluated rather than answered
        from `requires`.
        """
        sut = JSONLAdapter(jsonl_fixture_file)
        records = list(sut.decisions())

        def result_for(spec: str):
            return RecordEngine.evaluate(
                Requirement(
                    id="req_rec_spec",
                    source_document="Doc",
                    article_clause="Art 1",
                    verbatim_text="Quote",
                    stakeholder="deployer",
                    formalism="record",
                    spec=spec,
                    rationale="Why this duty exists, in English.",
                    requires=("provenance_model_version", "artifact_logs_event_log"),
                    binding=True,
                    scope="",
                    domains=(),
                ),
                sut,
                records,
            )

        both = result_for("present(provenance_model_version) and present(artifact_logs_event_log)")
        assert both.verdict == Verdict.SATISFIED
        assert both.strength == Strength.OBSERVED

        # The property, not the `requires` list, decides which signals are looked for: this one
        # names a signal the trace does not carry, and `requires` cannot make it satisfied.
        narrower = result_for("present(stability_signals_perturbation_sensitivity)")
        assert narrower.verdict == Verdict.VIOLATED
        assert narrower.details["signals_absent_from_trace"] == [
            "stability_signals_perturbation_sensitivity"
        ]

        # Prose, a state property that is not a presence conjunction, and text no parser accepts
        # are each not evaluated — never answered from `requires` as if the spec were absent.
        for spec in (
            "Record check",
            "provenance_model_version == 'never this version'",
            "not a property !@#$",
        ):
            unreadable = result_for(spec)
            assert unreadable.verdict == Verdict.INCONCLUSIVE, spec
            assert unreadable.strength is None, spec
            assert "Not evaluated" in unreadable.evidence_summary, spec


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
            rationale="Why this duty exists, in English.",
            requires=("signal_a", "signal_b"),
            binding=True,
            scope="",
            domains=(),
        )
        records = [
            {"signal_a": True, "signal_b": True},
            {"signal_a": False, "signal_b": False},
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.SATISFIED
        assert result.strength == Strength.OBSERVED

    def test_a_false_bare_boolean_atom_is_violated(self):
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_bare_false",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(signal_a)",
            rationale="The signal remains true.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )
        records = [{"signal_a": True}, {"signal_a": False}]

        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.strength == Strength.OBSERVED
        assert result.details["violation_step_indices"] == [1]

    def test_a_bare_boolean_atom_is_monitored_for_true_and_false_traces(self):
        sut = BaseSUT({"approved"})
        req = Requirement(
            id="temp_bare_boolean",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(approved)",
            rationale="Approval remains true.",
            requires=("approved",),
            binding=True,
            scope="",
            domains=(),
        )

        satisfied = ObservedEngine.evaluate(
            req, sut, [{"approved": True}, {"approved": True}]
        )
        violated = ObservedEngine.evaluate(
            req, sut, [{"approved": True}, {"approved": False}]
        )

        assert satisfied.verdict == Verdict.SATISFIED
        assert satisfied.strength == Strength.OBSERVED
        assert violated.verdict == Verdict.VIOLATED
        assert violated.strength == Strength.OBSERVED

    def test_a_direct_temporal_boolean_comparison_is_not_evaluated(self):
        sut = BaseSUT({"approved"})
        req = Requirement(
            id="temp_boolean_comparison",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(approved == True)",
            rationale="Approval remains true.",
            requires=("approved",),
            binding=True,
            scope="",
            domains=(),
        )

        result = ObservedEngine.evaluate(
            req, sut, [{"approved": True}, {"approved": True}]
        )

        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert "always(approved)" in result.details["error"]

    def test_a_bare_boolean_atom_without_an_established_kind_is_not_evaluated(
        self,
    ):
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_bare_unknown",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(signal_a)",
            rationale="The signal remains true.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )

        result = ObservedEngine.evaluate(
            req, sut, [{"signal_a": "yes"}, {"signal_a": "no"}]
        )
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert result.details["signals_without_boolean_trace_kind"] == {"signal_a": 2}

    def test_conflicting_boolean_and_magnitude_roles_are_not_evaluated(self):
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_conflicting_roles",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(signal_a and signal_a > 0)",
            rationale="The signal cannot have incompatible roles.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )

        result = ObservedEngine.evaluate(
            req, sut, [{"signal_a": 1}, {"signal_a": 2}]
        )
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert "bare Boolean role" in result.details["error"]
        assert "measured magnitude role" in result.details["error"]

    def test_presence_and_bare_boolean_atoms_keep_distinct_false_semantics(self):
        sut = BaseSUT({"signal_a"})
        records = [{"signal_a": False}, {"signal_a": False}]
        fields = {
            "source_document": "Doc",
            "article_clause": "Art 1",
            "verbatim_text": "Quote",
            "stakeholder": "deployer",
            "formalism": "temporal",
            "rationale": "The trace carries the required Boolean evidence.",
            "requires": ("signal_a",),
            "binding": True,
            "scope": "",
            "domains": (),
        }
        presence = Requirement(
            id="temp_present_false", spec="always(present(signal_a))", **fields
        )
        truth = Requirement(id="temp_bare_false", spec="always(signal_a)", **fields)

        assert ObservedEngine.evaluate(presence, sut, records).verdict == Verdict.SATISFIED
        assert ObservedEngine.evaluate(truth, sut, records).verdict == Verdict.VIOLATED

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
            rationale="Why this duty exists, in English.",
            requires=("signal_a", "signal_b"),
            binding=True,
            scope="",
            domains=(),
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

    @pytest.mark.parametrize("records", [[], [{"signal_a": True}]])
    def test_trace_too_short_names_the_trace_not_the_formula(self, records: list):
        """rtamt cannot read a sampling period off one sample; that is a limit of the trace.

        Letting the failure surface from rtamt's internals would report a well-formed pack
        requirement as unexpressible and leak a third-party traceback string as the reason.
        """
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_short",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(signal_a >= 0.5)",
            rationale="Why this duty exists, in English.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert result.details["records_observed"] == len(records)
        assert "decision trace" in result.evidence_summary
        assert "rtamt" not in result.evidence_summary

    def test_non_finite_flag_counts_as_absent(self):
        """NaN is the absence of a value, and every robustness comparison against it is False."""
        sut = BaseSUT({"signal_a"})
        req = Requirement(
            id="temp_nan_flag",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec="always(signal_a >= 0.5)",
            rationale="Why this duty exists, in English.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )
        records = [{"signal_a": True}, {"signal_a": float("nan")}]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert all(
            score == score for _, score in result.details["evaluation_scores"]
        ), "a NaN robustness score would also make the report's JSON unparseable"

    @pytest.mark.parametrize(
        "spec",
        [
            pytest.param("always(signal_a <= 0.5)", id="bound-at-the-presence-threshold"),
            pytest.param("always(signal_a <= signal_b)", id="variable-against-variable"),
        ],
    )
    def test_quantitative_bound_needs_a_measurement(self, spec: str):
        """Only `var >= 0.5` asks whether a signal is present; every other bound is a quantity.

        Reading one of these as a flag would score an unmeasured record 0.0 and report the
        bound satisfied by a number nobody measured.
        """
        sut = BaseSUT({"signal_a", "signal_b"})
        req = Requirement(
            id="temp_bound",
            source_document="Doc",
            article_clause="Art 1",
            verbatim_text="Quote",
            stakeholder="deployer",
            formalism="temporal",
            spec=spec,
            rationale="Why this duty exists, in English.",
            requires=("signal_a", "signal_b"),
            binding=True,
            scope="",
            domains=(),
        )
        result = ObservedEngine.evaluate(req, sut, [{"signal_b": 0.2}, {"signal_b": 0.3}])
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert "signal_a" in result.details["signals_unmeasured_in_trace"]

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
            rationale="Why this duty exists, in English.",
            requires=("signal_a",),
            binding=True,
            scope="",
            domains=(),
        )
        records = [{"signal_a": True}, {"signal_a": True}]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert "cannot express or parse" in result.evidence_summary
        assert "Not evaluated" in result.evidence_summary


class TestRequirementsMeasureTheirDuty:
    """A requirement must fail on a trace that breaches the duty it quotes.

    A spec that only checks that the signal names appear would report SATISFIED at
    `observed` strength for a deadline nothing measured.
    """

    def test_ecoa_thirty_day_notice_violated_by_a_late_notification(self):
        req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
        sut = BaseSUT(set(req.requires))
        records = [
            {"artifact_logs_decision_record": {"id": "dec-1"},
             "artifact_logs_notification_latency_days": 12},
            {"artifact_logs_decision_record": {"id": "dec-2"},
             "artifact_logs_notification_latency_days": 45},
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.details["violation_step_indices"] == [1]
        assert result.details["offending_trace_segment"] == [records[1]]

        on_time = [dict(r, artifact_logs_notification_latency_days=12) for r in records]
        assert ObservedEngine.evaluate(req, sut, on_time).verdict == Verdict.SATISFIED

    def test_ecoa_unaccepted_counteroffer_gets_the_ninety_day_deadline(self):
        """1002.9(a)(1)(iv) allows 90 days after a counteroffer the applicant never took up.

        Judging that record against the 30-day deadline of (i) would report a breach of a
        clause the trace does not breach.
        """
        req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
        sut = BaseSUT(set(req.requires))
        records = [
            {"artifact_logs_decision_record": {"id": "dec-1"},
             "artifact_logs_counteroffer_not_accepted": False,
             "artifact_logs_notification_latency_days": 12},
            {"artifact_logs_decision_record": {"id": "dec-2"},
             "artifact_logs_counteroffer_not_accepted": True,
             "artifact_logs_notification_latency_days": 45},
        ]
        assert ObservedEngine.evaluate(req, sut, records).verdict == Verdict.SATISFIED

        late = [records[0], dict(records[1], artifact_logs_notification_latency_days=95)]
        result = ObservedEngine.evaluate(req, sut, late)
        assert result.verdict == Verdict.VIOLATED
        assert result.details["violation_step_indices"] == [1]

    def test_ecoa_accepted_counteroffer_keeps_the_thirty_day_deadline(self):
        req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
        sut = BaseSUT(set(req.requires))
        records = [
            {
                "artifact_logs_decision_record": {"id": "dec-1"},
                "artifact_logs_counteroffer_not_accepted": False,
                "artifact_logs_notification_latency_days": 90,
            },
            {
                "artifact_logs_decision_record": {"id": "dec-2"},
                "artifact_logs_counteroffer_not_accepted": False,
                "artifact_logs_notification_latency_days": 90,
            },
        ]

        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED
        assert result.details["violation_step_indices"] == [0, 1]

    @pytest.mark.parametrize(
        "unmeasured_latency",
        [
            pytest.param({}, id="absent"),
            pytest.param({"artifact_logs_notification_latency_days": ""}, id="blank"),
            pytest.param({"artifact_logs_notification_latency_days": "45"}, id="json-string"),
            pytest.param({"artifact_logs_notification_latency_days": True}, id="bool"),
            pytest.param(
                {"artifact_logs_notification_latency_days": float("nan")}, id="nan"
            ),
            pytest.param(
                {"artifact_logs_notification_latency_days": float("inf")}, id="infinity"
            ),
        ],
    )
    def test_ecoa_thirty_day_notice_not_evaluated_without_a_measured_latency(
        self, unmeasured_latency: dict
    ):
        """Nothing that is not a number is a number of days.

        Absence is not a notice in 0 days and the string "45" is not a notice in 1 day; both
        would otherwise pass the deadline they breach.
        """
        req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
        sut = BaseSUT(set(req.requires))
        records = [
            {"artifact_logs_decision_record": {"id": "dec-1"},
             "artifact_logs_notification_latency_days": 12},
            {"artifact_logs_decision_record": {"id": "dec-2"}, **unmeasured_latency},
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None
        assert result.details["signals_unmeasured_in_trace"] == {
            "artifact_logs_notification_latency_days": 1
        }

    def test_ecoa_thirty_day_notice_not_evaluated_when_the_signal_is_only_declared(self):
        """Declaring the capability is not measuring it: an all-zero column is not evidence."""
        req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_a_1_timing_of_notice")
        sut = BaseSUT(set(req.requires))
        records = [
            {"artifact_logs_decision_record": {"id": "dec-1"}},
            {"artifact_logs_decision_record": {"id": "dec-2"}},
        ]
        result = ObservedEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.strength is None

    def test_eu_ai_act_traceability_violated_by_an_unlogged_decision(self):
        req = load_pack("eu_ai_act").get_requirement("eu_ai_act_art12_2_traceability_monitoring")
        assert req.formalism == "record"
        sut = BaseSUT(set(req.requires))
        records = [
            {"artifact_logs_event_log": True, "provenance_model_version": "v1.2.0"},
            {"provenance_model_version": "v1.2.0"},
        ]
        result = RecordEngine.evaluate(req, sut, records)
        assert result.verdict == Verdict.VIOLATED


#: The shipped signals that are deliberately outside the paper's four Section 6.3 categories,
#: and the complete list of them. See `test_exactly_one_shipped_signal_is_outside_the_paper_s_
#: taxonomy` for the argument, and `docs/refinement.md` for what the duty using it can and cannot
#: see.
OUTSIDE_THE_TAXONOMY = {"applicant_prohibited_basis"}


class TestRegulationPacks:
    """Tests for EU AI Act, GDPR, and ECOA regulation packs."""

    @pytest.mark.parametrize("pack_name", ["eu_ai_act", "gpai", "gdpr", "ecoa"])
    def test_pack_loads_and_validates(self, pack_name: str):
        assert pack_name in list_packs()
        pack = load_pack(pack_name)
        assert pack.id == pack_name
        assert len(pack.requirements) >= 3
        for req in pack.requirements:
            assert req.verbatim_text.strip()
            assert req.source_document.strip()
            assert req.article_clause.strip()
            # Verify Section 6.3 taxonomy prefixes or categories. Every name the property reads
            # is checked, not only the gated ones: a signal read inside a disjunction is exempt
            # from `requires` by design, so this is the only check standing between a typo there
            # and a branch no system can ever satisfy.
            checked = set(req.requires) | set(signal_names(parse_property(req.spec)))
            for signal in sorted(checked):
                assert any(
                    signal.startswith(cat) for cat in CAPABILITY_TAXONOMY
                ) or signal in OUTSIDE_THE_TAXONOMY, (
                    f"Signal {signal!r} in pack {pack_name} must belong to "
                    f"Section 6.3 taxonomy {CAPABILITY_TAXONOMY}"
                )

    def test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy(self):
        """The exemption above is a category, not a spelling licence, and it stays at one.

        Every one of the paper's four Section 6.3 categories names a fact about an *inference*, its
        artefacts, or the governance around it. None names a fact about a person, so the protected
        variable of the counterfactual duty is the first signal in any shipped pack that is not
        about the system at all — it is an input the decision procedure accepts, and the duty asks
        whether the procedure uses it. Widening `CAPABILITY_TAXONOMY` is not the fix: it is a
        verbatim transcription of the paper (`sut.py`), and the paper does not have this category.
        Naming the one exception here is, so that a second one has to be argued for rather than
        typed.
        """
        shipped = {
            signal
            # The four statutory packs, exactly as the check above is parametrised. `table7` is
            # out of frame here as it is there: its signal names are the paper's own evidence-field
            # keys, transcribed rather than authored, and `test_pack_matches_table7_transcription`
            # is what holds those to the print.
            for pack_name in ("eu_ai_act", "gpai", "gdpr", "ecoa")
            for req in load_pack(pack_name).requirements
            for signal in set(req.requires) | set(signal_names(parse_property(req.spec)))
        }
        outside = {
            signal
            for signal in shipped
            if not any(signal.startswith(cat) for cat in CAPABILITY_TAXONOMY)
        }
        assert outside == OUTSIDE_THE_TAXONOMY

    @pytest.mark.parametrize("pack_name", ["eu_ai_act", "gpai", "gdpr", "ecoa"])
    def test_pack_quotes_found_verbatim_in_legal_sources_report(self, pack_name: str):
        """Every requirement quote in the regulation packs must be found character-for-character
        in docs/legal-sources.md.
        """
        report_path = Path(__file__).resolve().parents[1] / "docs" / "legal-sources.md"
        assert report_path.is_file(), f"Legal sources report missing at {report_path}"
        report_text = report_path.read_text(encoding="utf-8").replace("\r\n", "\n")

        pack = load_pack(pack_name)
        for req in pack.requirements:
            verbatim = req.verbatim_text.replace("\r\n", "\n")
            assert verbatim in report_text, (
                f"Requirement {req.id!r} in pack {pack_name!r} has verbatim_text not found "
                f"verbatim in docs/legal-sources.md:\n{req.verbatim_text!r}"
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
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "eu_ai_act",
                "--system-scope",
                "high-risk",
            ]
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "CONFORMANCE REPORT" in captured.out
        assert "eu_ai_act" in captured.out

    def test_cli_exits_zero_when_every_requirement_is_not_applicable(
        self, jsonl_fixture_file: Path, capsys
    ):
        """Not declaring a regulatory class is not a breach, so it must not fail the build.

        Every eu_ai_act duty is limited to high-risk systems. With no `--system-scope` the
        tool will not infer the class, so it reports each one not applicable and says so —
        but nothing was found against the system, so the run exits 0.
        """
        rc = cli_main(["check", "--system", str(jsonl_fixture_file), "--pack", "eu_ai_act"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "NOT APPLICABLE" in captured.out
        assert "declared scope: undeclared" in captured.out

    def test_cli_rejects_a_scope_outside_the_vocabulary(
        self, jsonl_fixture_file: Path, capsys
    ):
        """A typo must not pass for an out-of-class run that exits clean.

        Every eu_ai_act duty is limited to high-risk, so `hihg-risk` would otherwise report
        four not-applicable results and exit 0 — indistinguishable from a correct run against
        a system that genuinely is not high-risk.
        """
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "eu_ai_act",
                "--system-scope",
                "hihg-risk",
            ]
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "CONFORMANCE REPORT" not in captured.out
        assert "'hihg-risk'" in captured.err
        assert "'high-risk'" in captured.err

    def test_cli_accepts_a_known_class_the_pack_does_not_target(
        self, jsonl_fixture_file: Path, capsys
    ):
        """limited-risk is a real class, so the run answers rather than refusing."""
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "eu_ai_act",
                "--system-scope",
                "limited-risk",
            ]
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "declared scope: limited-risk" in captured.out
        assert "NOT APPLICABLE" in captured.out

    def test_cli_exits_zero_when_findings_are_unattainable(
        self, jsonl_fixture_file: Path, capsys
    ):
        """gdpr needs a signal this log never carries: a finding to read, not a breach."""
        rc = cli_main(["check", "--system", str(jsonl_fixture_file), "--pack", "gdpr"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "gdpr" in captured.out
        assert "UNATTAINABLE" in captured.out

    def test_cli_exits_nonzero_on_a_violation(self, tmp_path: Path, capsys):
        """Only a violation fails the run, and it is the violation that is reported."""
        log_file = tmp_path / "violating_gdpr.jsonl"
        records = [
            {
                "artifact_logs_decision_record": {"id": "dec-1"},
                "provenance_active_exceptions": ["none"],
            },
            {
                "artifact_logs_decision_record": {"id": "dec-2"},
                "provenance_active_exceptions": [],  # blank -> absent from this record
            },
        ]
        with log_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        rc = cli_main(["check", "--system", str(log_file), "--pack", "gdpr"])
        assert rc == 2
        captured = capsys.readouterr()
        assert "violated" in captured.out
        assert "provenance_active_exceptions" in captured.out
