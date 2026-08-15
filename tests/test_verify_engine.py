"""The shipped gold-triple conformance kit refuses overclaim and bad witnesses."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from test_engine_plugins import _install

from reasonsmith import witness
from reasonsmith.plugins import ENGINE_GROUP
from reasonsmith.report import RequirementResult
from reasonsmith.verdict import Strength, Verdict
from reasonsmith.verify_engine import (
    GOLD_TRIPLES,
    VerificationRow,
    _load_object,
    _one,
    load_engine,
    render,
    verify_engine,
)


def _engine_source(body: str, ceiling: str = "proved") -> str:
    return (
        "from reasonsmith.report import RequirementResult\n"
        "from reasonsmith.verdict import Strength, Verdict\n"
        "class Engine:\n"
        f"    max_strength = {ceiling!r}\n"
        "    @staticmethod\n"
        "    def evaluate(req, sut, records):\n"
        + "".join(f"        {line}\n" for line in body.strip().splitlines())
    )


def _result(verdict: str, strength: str | None = None, details: str = "{}"):
    return (
        "return RequirementResult(\n"
        "    requirement_id=req.id, source_clause='',\n"
        f"    verdict=Verdict.{verdict.upper()}, "
        f"strength={('None' if strength is None else 'Strength.' + strength.upper())},\n"
        "    signals_required=tuple(req.requires), details="
        + details
        + ", binding=req.binding, scope=req.scope)"
    )


def test_verify_engine_passes_a_known_good_engine_that_declines_everything(tmp_path, monkeypatch):
    source = _engine_source(_result("inconclusive"))
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-good", "Engine")

    rows, ceiling = verify_engine("gold-good")

    assert ceiling is Strength.PROVED
    assert len(rows) == 8
    assert all(row.passed for row in rows)


def test_verify_engine_fails_a_ceiling_violation(tmp_path, monkeypatch):
    source = _engine_source(_result("satisfied", "proved"), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-overclaim", "Engine")

    rows, _ = verify_engine("gold-overclaim")

    assert not all(row.passed for row in rows)
    assert all("engine call failed" in row.reason for row in rows)
    assert all(not row._strength_within_ceiling() for row in rows)


def test_verify_engine_fails_wrong_verdicts(tmp_path, monkeypatch):
    source = _engine_source(_result("satisfied", "observed"), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-wrong", "Engine")

    rows, _ = verify_engine("gold-wrong")

    assert not all(row.passed for row in rows)
    assert any("expected" in row.reason for row in rows)


def test_verify_engine_fails_a_refuted_witness(tmp_path, monkeypatch):
    witness = (
        '{"witness": {"kind": "trace_position", "provenance": "trusted-ceiling", '
        '"payload": {"index": 0}}}'
    )
    source = _engine_source(_result("violated", "observed", witness), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-refuted", "Engine")

    rows, _ = verify_engine("gold-refuted")

    assert not all(row.passed for row in rows)
    assert any(row.provenance == "refuted" for row in rows)


@pytest.mark.parametrize("candidate", ["engine", "Engine", "ENGINE", "engine_under_test"])
def test_load_object_accepts_each_documented_candidate(monkeypatch, candidate):
    marker = object()
    module = SimpleNamespace(**{candidate: marker})
    monkeypatch.setattr("reasonsmith.verify_engine.importlib.import_module", lambda _name: module)

    assert _load_object("local.module") is marker


def test_load_object_names_missing_candidates(monkeypatch):
    monkeypatch.setattr(
        "reasonsmith.verify_engine.importlib.import_module", lambda _name: SimpleNamespace()
    )

    with pytest.raises(ValueError, match="has no engine, Engine, ENGINE or engine_under_test"):
        _load_object("local.module")


def test_load_engine_module_attribute_and_failure_messages(tmp_path, monkeypatch):
    module_name = "local_verify_engine"
    (tmp_path / f"{module_name}.py").write_text("class Engine: pass\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    name, engine = load_engine(f"{module_name}:Engine")
    assert name == f"{module_name}:Engine"
    assert engine.__name__ == "Engine"
    with pytest.raises(ValueError, match="has no attribute 'Missing'"):
        load_engine(f"{module_name}:Missing")
    with pytest.raises(ValueError, match="no installed reasonsmith.engines entry point"):
        load_engine("missing-engine")


def test_render_has_human_and_json_surfaces():
    row = VerificationRow(GOLD_TRIPLES[0], True, "satisfied", "proved", "trusted-ceiling", "proved")

    text = render([row], "dummy", Strength.PROVED)
    payload = json.loads(render([row], "dummy", Strength.PROVED, as_json=True))

    assert "What passing proves:" in text
    assert "What passing cannot prove:" in text
    assert "The kit reports agreement on 1 named triples" in text
    assert payload["results"][0]["verdict_match"] is True
    assert payload["results"][0]["strength_within_declared_ceiling"] is True


def test_one_reports_gold_setup_failure(monkeypatch):
    import reasonsmith.cli

    def fail(_spec):
        raise ValueError("fixture setup failed")

    monkeypatch.setattr(reasonsmith.cli, "load_system_module", fail)
    row = _one(GOLD_TRIPLES[0], object(), "dummy", Strength.PROVED)

    assert not row.passed
    assert "gold triple setup failed" in row.reason


def test_one_reports_engine_call_failure():
    class Broken:
        def evaluate(self, req, sut, records):
            raise RuntimeError("boom")

    row = _one(GOLD_TRIPLES[0], Broken(), "broken", Strength.PROVED)

    assert not row.passed
    assert "engine call failed" in row.reason


def test_one_reports_missing_witness_on_required_triple():
    class NoWitness:
        def evaluate(self, req, sut, records):
            return RequirementResult(
                requirement_id=req.id,
                source_clause="",
                verdict=Verdict.VIOLATED,
                strength=Strength.PROVED,
                signals_required=tuple(req.requires),
                evidence_summary="violation",
                binding=req.binding,
                scope=req.scope,
            )

    row = _one(GOLD_TRIPLES[7], NoWitness(), "no-witness", Strength.PROVED)

    assert not row.passed
    assert "required violation witness" in row.reason


def test_verification_row_ceiling_without_strength_is_within_ceiling():
    row = VerificationRow(GOLD_TRIPLES[0], True, "not_evaluated", None, None)
    assert row._strength_within_ceiling()


def test_one_reports_wrong_result_type():
    class WrongType:
        def evaluate(self, req, sut, records):
            return "not a result"

    row = _one(GOLD_TRIPLES[0], WrongType(), "wrong-type", Strength.PROVED)
    assert "RequirementResult" in row.reason


def test_one_reports_wrong_requirement_id():
    class WrongRequirement:
        def evaluate(self, req, sut, records):
            return RequirementResult(
                requirement_id="other",
                source_clause="",
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                binding=req.binding,
                scope=req.scope,
            )

    row = _one(GOLD_TRIPLES[0], WrongRequirement(), "wrong-id", Strength.PROVED)
    assert "answered requirement" in row.reason


def test_one_accepts_the_capability_gate_result():
    class Gate:
        def evaluate(self, req, sut, records):
            return RequirementResult(
                requirement_id=req.id,
                source_clause="",
                verdict=Verdict.INCONCLUSIVE,
                strength=Strength.UNATTAINABLE,
                signals_required=tuple(req.requires),
                signals_missing=tuple(req.requires),
                binding=req.binding,
                scope=req.scope,
            )

    row = _one(GOLD_TRIPLES[5], Gate(), "gate", Strength.PROVED)
    assert row.passed


def test_verify_engine_rejects_an_unusable_ceiling(tmp_path, monkeypatch):
    source = _engine_source(_result("inconclusive"), ceiling="not-a-strength")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-unbounded", "Engine")

    with pytest.raises(ValueError, match="no usable max_strength"):
        verify_engine("gold-unbounded")


def test_render_prints_a_row_reason():
    row = VerificationRow(
        GOLD_TRIPLES[0], False, "satisfied", "observed", "trusted-ceiling", "observed", "mismatch"
    )
    assert "mismatch" in render([row], "dummy", Strength.OBSERVED)


def test_witness_vocabulary_and_trace_checker_cover_declined_shapes():
    req_record = SimpleNamespace(formalism="record", spec="present(signal_a)")
    result = SimpleNamespace(
        details={
            "violation_step_indices": [0],
            "signals_absent_from_trace": ["signal_a"],
        }
    )
    assert witness._witness(result, "record")[0] == "presence_absence"
    result.details = {"counterexample": {"x": 1}}
    assert witness._witness(result, "logical")[0] == "input_valuation"
    result.details = {"violation_step_indices": [0]}
    assert witness._witness(result, "temporal")[0] == "trace_position"
    result.details = {
        "counterexample_pair": [{"x": 0}, {"x": 1}],
        "counterexample_outcomes": [0, 1],
    }
    assert witness._witness(result, "counterfactual")[0] == "execution_pair"
    assert witness._indices({"index": 0}) == [0]
    assert witness._indices(True) is None
    assert witness._indices([0, "bad"]) == [0]
    assert witness._indices("bad") is None

    assert (
        witness._trace_check(req_record, [{}], "presence_absence", [0, ["signal_a"]])[0]
        == "confirmed"
    )
    assert (
        witness._trace_check(req_record, [{}], "presence_absence", [0, ["other"]])[0] == "refuted"
    )
    assert (
        witness._trace_check(
            req_record, [{}], "presence_absence", {"indices": [3], "signals": ["signal_a"]}
        )[0]
        == "refuted"
    )
    assert (
        witness._trace_check(
            req_record, [{"signal_a": "stated"}], "trace_position", {"indices": [0]}
        )[0]
        == "refuted"
    )
    assert witness._trace_check(req_record, [{}], "unknown", {"indices": [0]})[0] == "uncheckable"
    assert witness._trace_check(req_record, [{}], "trace_position", True)[0] == "refuted"



def test_verify_engine_rejects_forged_positive_requirement_identity():
    class Forged:
        def evaluate(self, req, sut, records):
            return RequirementResult(
                requirement_id=req.id,
                source_clause="FORGED",
                verdict=Verdict.SATISFIED,
                strength=Strength.PROVED,
                signals_required=(),
                evidence_summary="positive",
                binding=False,
                scope="forged-scope",
                domains=("consumer-credit",),
                verbatim_text="forged",
            )

    row = _one(GOLD_TRIPLES[0], Forged(), "forged", Strength.PROVED)
    assert not row.passed
    assert "forged audited requirement identity" in row.reason
