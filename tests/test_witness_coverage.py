"""Behavioral coverage for the core plug-in witness re-checkers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
import z3

import reasonsmith.engines.observed as observed_engine
from reasonsmith import witness
from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.report import RequirementResult
from reasonsmith.spec import Requirement
from reasonsmith.verdict import EvidenceBasis, Strength, Verdict


@pytest.fixture(autouse=True)
def _z3_sort_predicates(monkeypatch):
    # The witness module intentionally asks z3's public sort predicates.  Older z3-solver
    # releases expose the equivalent predicates without the ``_sort`` suffix.
    for name, predicate in (
        ("is_bool_sort", lambda sort: sort.kind() == z3.Z3_BOOL_SORT),
        ("is_int_sort", lambda sort: sort.kind() == z3.Z3_INT_SORT),
        ("is_real_sort", lambda sort: sort.kind() == z3.Z3_REAL_SORT),
        ("is_string_sort", lambda sort: sort.kind() == z3.Z3_SEQ_SORT),
    ):
        if not hasattr(z3, name):
            monkeypatch.setattr(z3, name, predicate, raising=False)


def _req(formalism: str, spec: str):
    return Requirement(
        id="witness-test",
        source_document="Test source",
        article_clause="section 1",
        verbatim_text="A system shall satisfy the property.",
        stakeholder="applicant",
        formalism=formalism,
        spec=spec,
        rationale="A test property.",
        requires=("signal",),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )


def _result(
    *,
    details=None,
    verdict=Verdict.VIOLATED,
    strength=Strength.OBSERVED,
    basis=EvidenceBasis.BEHAVIOURAL,
):
    return RequirementResult(
        requirement_id="witness-test",
        source_clause="section 1",
        verdict=verdict,
        strength=strength,
        signals_required=(),
        evidence_summary="engine result",
        details={} if details is None else details,
        basis=basis,
    )


def test_public_replay_lifts_and_trace_witnesses() -> None:
    sut = RulesAdapter(
        rules=["approved = x >= 1"],
        variables={"x": "int", "approved": "bool"},
        constraints=["x >= 0"],
    )
    req = _req("logical", "x >= 0 implies approved == True")
    runner = witness.decision_runner(sut, sut.logic())
    assert runner is not None and runner[1] == "the system's own decide()"
    assert witness.verify_counterexample(sut, req, {"x": 0}, sut.logic())[0]

    temporal = _req("temporal", "always(present(reason))")
    assert witness._state_spec(temporal) == "present(reason)"
    status, reason = witness._trace_check(
        temporal, [{"reason": ""}], "presence_absence", [0, ["reason"]]
    )
    assert status == "confirmed" and "confirmed" in reason


def test_indices_and_presence_witness_shapes_are_checked() -> None:
    req = _req("record", "present(reason) and present(detail)")
    records = [{"reason": "", "detail": "specific"}]
    assert witness._indices({"index": 0}) == [0]
    assert witness._indices({"position": [0, 1]}) == [0, 1]
    assert witness._indices(True) is None
    assert witness._indices([0, "bad"]) == [0]
    assert witness._indices([0, "signals"]) == [0]

    assert (
        witness._trace_check(req, records, "presence_absence", {"index": 0, "signals": ["reason"]})[
            0
        ]
        == "confirmed"
    )
    assert witness._trace_check(req, records, "presence_absence", [0, ["reason"]])[0] == "confirmed"
    assert (
        witness._trace_check(req, records, "presence_absence", {"index": 0, "signals": "reason"})[0]
        == "refuted"
    )
    assert (
        witness._trace_check(req, records, "presence_absence", {"index": 0, "signals": ["other"]})[
            0
        ]
        == "refuted"
    )
    assert (
        witness._trace_check(req, records, "presence_absence", {"index": 3, "signals": ["reason"]})[
            0
        ]
        == "refuted"
    )
    assert (
        witness._trace_check(req, records, "presence_absence", {"index": 0, "signals": []})[0]
        == "refuted"
    )


def test_trace_position_checker_distinguishes_confirmed_refuted_and_uncheckable() -> None:
    req = _req("logical", "approved == True")
    assert (
        witness._trace_check(req, [{"approved": False}], "trace_position", {"index": 0})[0]
        == "confirmed"
    )
    assert (
        witness._trace_check(req, [{"approved": True}], "trace_position", {"index": 0})[0]
        == "refuted"
    )
    assert (
        witness._trace_check(req, [{"approved": False}], "trace_position", {"index": 2})[0]
        == "refuted"
    )
    assert (
        witness._trace_check(req, [{"approved": False}], "other", {"index": 0})[0] == "uncheckable"
    )
    assert witness._trace_check(req, [{}], "trace_position", {"index": 0})[0] == "refuted"
    assert witness._trace_check(req, [], "trace_position", {})[0] == "refuted"


class _NoReplay:
    def logic(self):
        return None


class _RaisingLogic:
    def logic(self):
        raise RuntimeError("logic broken")


class _Replay:
    def __init__(self, value):
        self.value = value

    def logic(self):
        return None

    def decide(self, _payload):
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


@pytest.mark.parametrize(
    ("sut", "payload", "expected"),
    [
        (_NoReplay(), 3, "refuted"),
        (_RaisingLogic(), {"x": 1}, "uncheckable"),
        (_Replay(RuntimeError("replay broken")), {"x": 1}, "refuted"),
        (_Replay("not a record"), {"x": 1}, "refuted"),
    ],
)
def test_valuation_checker_reports_replay_boundary_failures(sut, payload, expected) -> None:
    req = _req("logical", "approved == True")
    assert witness._valuation_check(req, sut, payload)[0] == expected


def test_valuation_checker_confirms_refutes_and_reports_interpreter_refusal() -> None:
    req = _req("logical", "approved == True")
    assert witness._valuation_check(req, _Replay({"approved": False}), {"x": 1})[0] == "confirmed"
    assert witness._valuation_check(req, _Replay({"approved": True}), {"x": 1})[0] == "refuted"
    malformed = _req("logical", "approved ==")
    assert witness._valuation_check(malformed, _Replay({"approved": False}), {})[0] == "uncheckable"


def test_admissible_handles_declared_sorts_and_unsat_domain() -> None:
    for sort, value in (("bool", True), ("int", 2), ("real", 2.5), ("str", "ok")):
        sut = RulesAdapter(rules=["out = x"], variables={"x": sort, "out": sort})
        assert witness._admissible(sut.logic(), {"x": value})[0]
    sut = RulesAdapter(
        rules=["out = x"], variables={"x": "int", "out": "int"}, constraints=["x >= 2"]
    )
    admitted, reason = witness._admissible(sut.logic(), {"x": 1})
    assert not admitted and "unsat" in reason
    assert witness._admissible(sut.logic(), {"missing": 1})[0] is False
    assert witness._admissible(object(), {})[0] is False


def _counterfactual_sut():
    return RulesAdapter(
        rules=['if protected == 1:\n    outcome = "yes"\nelse:\n    outcome = "no"'],
        variables={"protected": "int", "outcome": "str"},
        constraints=["protected >= 0", "protected <= 1"],
    )


def test_pair_checker_validates_shape_domain_replay_and_outcome() -> None:
    req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    sut = _counterfactual_sut()
    assert witness._pair_check(req, sut, [{"protected": 0}, {"protected": 1}])[0] == "confirmed"
    assert (
        witness._pair_check(req, sut, {"left": {"protected": 0}, "right": {"protected": 1}})[0]
        == "confirmed"
    )
    assert (
        witness._pair_check(req, sut, {"left": {"protected": 0}, "right": {"protected": 0}})[0]
        == "refuted"
    )
    assert (
        witness._pair_check(
            req, sut, {"left": {"protected": 0, "x": 1}, "right": {"protected": 1, "x": 2}}
        )[0]
        == "refuted"
    )
    assert (
        witness._pair_check(req, sut, {"left": {"protected": 0}, "right": {"protected": 2}})[0]
        == "refuted"
    )
    assert witness._pair_payload("bad") is None


def test_pair_checker_reports_missing_domain_replay_and_record_outcome() -> None:
    req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    pair = [{"protected": 0}, {"protected": 1}]

    class LogicNone:
        def logic(self):
            return None

    class LogicRaises:
        def logic(self):
            raise RuntimeError("no logic")

    class LogicNoDecide:
        def logic(self):
            return {
                "variables": {"protected": "int", "outcome": "str"},
                "rules": [],
                "constraints": ["protected >= 0"],
            }

    assert witness._pair_check(req, LogicNone(), pair)[0] == "uncheckable"
    assert witness._pair_check(req, LogicRaises(), pair)[0] == "uncheckable"
    assert witness._pair_check(req, LogicNoDecide(), pair)[0] == "uncheckable"

    class SameOutcome:
        def logic(self):
            return _counterfactual_sut().logic()

        def decide(self, values):
            return {"outcome": "same", **values}

    assert witness._pair_check(req, SameOutcome(), pair)[0] == "refuted"

    class NoOutcome:
        def logic(self):
            return _counterfactual_sut().logic()

        def decide(self, values):
            return dict(values)

    assert witness._pair_check(req, NoOutcome(), pair)[0] == "uncheckable"


@pytest.mark.parametrize("kind", ["reserved", "unknown"])
def test_check_dispatches_unknown_witness_kinds(kind) -> None:
    status, reason, checker = witness._check(_req("logical", "True"), _NoReplay(), [], kind, {})
    assert status == "uncheckable" and kind in reason and checker.endswith("_uncheckable")


def test_plugin_result_provenance_and_artifact_boundary() -> None:
    req = _req("logical", "approved == True")
    no_witness = _result(details={})
    assert witness.check_plugin_result(req, _NoReplay(), [], no_witness) is no_witness
    nonviolation = _result(
        verdict=Verdict.SATISFIED,
        details={
            "witness": {
                "kind": "trace_position",
                "provenance": "trusted-ceiling",
                "payload": {"index": 0},
                "checker": "plugin",
            }
        },
    )
    sanitized = witness.check_plugin_result(req, _NoReplay(), [], nonviolation)
    assert sanitized.details["witness"] == {
        "kind": "trace_position",
        "provenance": "trusted-ceiling",
        "payload": {"index": 0},
    }
    artifact = _result(
        basis=EvidenceBasis.ARTIFACT,
        strength=Strength.RECOUNTED,
        details={
            "probe_budget": {"trials": 1, "strategy": "test", "seed": 0, "input_space": "test"},
            "witness": {
                "kind": "trace_position",
                "provenance": "trusted-ceiling",
                "payload": {"index": 0},
            },
        },
    )
    assert (
        witness.check_plugin_result(req, _NoReplay(), [], artifact).details["witness"]["provenance"]
        == "trusted-ceiling"
    )


def test_plugin_result_marks_confirmed_and_uncheckable_witnesses() -> None:
    req = _req("logical", "approved == True")
    confirmed = _result(
        details={
            "witness": {
                "kind": "trace_position",
                "provenance": "trusted-ceiling",
                "payload": {"index": 0},
            }
        }
    )
    out = witness.check_plugin_result(req, _NoReplay(), [{"approved": False}], confirmed)
    assert out.details["witness"]["provenance"] == "witness-checked"
    unknown = _result(
        details={
            "witness": {
                "kind": "position_certificate",
                "provenance": "trusted-ceiling",
                "payload": {},
            }
        }
    )
    out = witness.check_plugin_result(req, _NoReplay(), [], unknown)
    assert out.details["witness"]["provenance"] == "trusted-ceiling"
    assert "checker" not in out.details["witness"]


def test_witness_discovery_and_payload_normalization_cover_legacy_shapes() -> None:
    record = _result(
        details={"violation_step_indices": [1], "signals_absent_from_trace": ["reason"]}
    )
    assert witness._trace_payload(record, "presence_absence")["signals"] == ["reason"]
    assert witness._trace_payload(record, "trace_position") == {"indices": [1]}
    assert witness._witness(record, "record")[0] == "presence_absence"
    logical = _result(details={"counterexample": {"x": 1}})
    assert witness._witness(logical, "logical")[0] == "input_valuation"
    temporal = _result(details={"violation_step_indices": [2]})
    assert witness._witness(temporal, "temporal")[0] == "trace_position"
    pair = _result(
        details={"counterexample_pair": [{"p": 0}, {"p": 1}], "counterexample_outcomes": ["a", "b"]}
    )
    kind, payload, explicit = witness._witness(pair, "counterfactual")
    assert kind == "execution_pair" and payload["outcomes"] == ["a", "b"] and not explicit
    assert witness._witness(_result(details={}), "logical") is None


def test_trace_and_valuation_refusals_and_plugin_demotion() -> None:
    req = _req("record", "present(reason)")
    assert (
        witness._trace_check(req, [{"reason": "ok"}], "presence_absence", {"index": 0})[0]
        == "refuted"
    )
    assert witness._valuation_check(req, _NoReplay(), {"x": 1})[0] == "uncheckable"
    logical = _req("logical", "approved == True")
    bad = _result(
        details={
            "witness": {
                "kind": "trace_position",
                "provenance": "trusted-ceiling",
                "payload": {"index": 0},
            }
        }
    )
    out = witness.check_plugin_result(logical, _NoReplay(), [{"approved": True}], bad)
    assert out.verdict is Verdict.INCONCLUSIVE and out.strength is None
    assert out.details["witness"]["provenance"] == "refuted"
    assert "failure" in out.details["witness"] and "unverified_payload" in out.details["witness"]


def test_pair_payload_and_checker_rejections() -> None:
    req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    sut = _counterfactual_sut()
    assert witness._pair_check(req, sut, {})[0] == "refuted"
    assert (
        witness._pair_check(
            req, sut, [{"protected": 0, "x": 0}, {"protected": 1, "x": 1, "outcome": "x"}]
        )[0]
        == "refuted"
    )
    assert witness._pair_check(req, sut, [{"protected": 0}, {"protected": 0}])[0] == "refuted"
    assert witness._pair_payload({"pair": "bad"}) is None

    class Raising:
        def logic(self):
            return sut.logic()

        def decide(self, _values):
            raise ValueError("cannot replay")

    assert witness._pair_check(req, Raising(), [{"protected": 0}, {"protected": 1}])[0] == "refuted"

    class BadRecords:
        def logic(self):
            return sut.logic()

        def decide(self, values):
            return []

    assert (
        witness._pair_check(req, BadRecords(), [{"protected": 0}, {"protected": 1}])[0] == "refuted"
    )


def test_remaining_dispatch_and_sanitization_edges() -> None:
    req = _req("record", "present(reason)")
    assert (
        witness._trace_check(req, [{"reason": ""}], "presence_absence", {"index": 0})[0]
        == "refuted"
    )
    assert witness._trace_check(req, [{"reason": ""}], "presence_absence", [0])[0] == "refuted"
    assert (
        witness._trace_check(
            _req("logical", 'contains(approved, "x")'),
            [{"approved": False}],
            "trace_position",
            {"index": 0},
        )[0]
        == "uncheckable"
    )
    pair_req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    assert witness._pair_payload({"pair": [{"p": 1}, {"p": 2}]}) == ({"p": 1}, {"p": 2})
    assert witness._pair_payload({"pair": "bad", "left": {"p": 1}, "right": {"p": 2}}) == (
        {"p": 1},
        {"p": 2},
    )
    status, _, checker = witness._check(
        _req("logical", "approved == True"), _NoReplay(), [], "input_valuation", 3
    )
    assert status == "refuted" and checker.endswith("_valuation_check")
    status, _, checker = witness._check(pair_req, _counterfactual_sut(), [], "execution_pair", {})
    assert status == "refuted" and checker.endswith("_pair_check")

    @dataclass
    class Raw:
        details: dict

    raw = Raw(
        details={
            "witness": {
                "kind": "trace_position",
                "unverified_payload": {"index": 0},
                "checker": "plugin",
            }
        }
    )
    sanitized = witness._trusted_result(raw)
    assert sanitized.details["witness"]["payload"] == {"index": 0}


def test_pair_checker_refuses_unchanged_protected_input_and_missing_replay(monkeypatch):
    req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    sut = _counterfactual_sut()
    assert "changes []" in witness._pair_check(
        req, sut, [{"protected": 0}, {"protected": 0}]
    )[1]

    monkeypatch.setattr(witness, "_admissible", lambda logic, values: (True, "admitted"))
    monkeypatch.setattr(witness, "decision_runner", lambda sut, logic: None)
    status, reason = witness._pair_check(
        req, sut, [{"protected": 0}, {"protected": 1}]
    )
    assert status == "uncheckable" and "no replay surface" in reason


def test_temporal_prefix_witness_is_confirmed_refuted_or_uncheckable() -> None:
    req = _req("temporal", "until(present(start), present(end))")
    confirmed_records = [{"start": "sent"}]
    payload = {"trace": confirmed_records, "positions": [0], "position": 0}
    assert witness._trace_prefix_check(req, confirmed_records, payload)[0] == "confirmed"

    refuted_records = [{"start": "sent", "end": "done"}]
    assert witness._trace_prefix_check(req, refuted_records, payload)[0] == "refuted"

    unknown_req = _req("temporal", "until(present(start), end >= 1)")
    unknown_records = [{"start": "sent"}]
    # A missing magnitude makes the reference interpreter unable to decide rather than evidence
    # that the witness is wrong.
    status, _ = witness._trace_prefix_check(
        unknown_req, unknown_records, {"trace": unknown_records}
    )
    assert status == "uncheckable"


def test_temporal_prefix_dispatches_through_plugin_witness_checker() -> None:
    req = _req("temporal", "until(present(start), present(end))")
    records = [{"start": "sent"}]
    result = _result(
        details={
            "witness": {
                "kind": "trace_prefix",
                "provenance": "trusted-ceiling",
                "payload": {"trace": records, "positions": [0]},
            }
        }
    )
    checked = witness.check_plugin_result(req, object(), records, result)
    assert checked.details["witness"]["provenance"] == "witness-checked"



def test_observed_until_violation_emits_recheckable_prefix() -> None:
    req = _req("temporal", "until(present(start), present(end))")
    records = [{"start": "sent"}, {"start": "still sent"}]
    result = ObservedEngine.evaluate(req, object(), records)

    assert result.verdict is Verdict.VIOLATED
    witness_record = result.details["witness"]
    assert witness_record["kind"] == "trace_prefix"
    prefix = witness_record["payload"]["trace"]
    assert witness._trace_prefix_check(req, records, witness_record["payload"])[0] == "confirmed"
    assert prefix == records[: len(prefix)]

def test_temporal_prefix_payload_shapes_and_malformed_witnesses() -> None:
    req = _req("temporal", "until(present(start), present(end))")
    records = [{"start": "sent"}]

    # The checker accepts both a bare list and a position-only witness, deriving the prefix from
    # the supplied trace.
    assert witness._trace_prefix_check(req, records, records)[0] == "confirmed"
    assert witness._trace_prefix_check(req, records, {"position": 0})[0] == "confirmed"

    malformed = [
        "not a trace",
        {"trace": "not a sequence"},
        {"trace": []},
        {"trace": ["not a record"]},
        {"trace": [{"start": "different"}]},
        {"trace": records, "positions": []},
        {"trace": records, "positions": [2]},
        {},
    ]
    for payload in malformed:
        assert witness._trace_prefix_check(req, records, payload)[0] == "refuted"


def test_temporal_prefix_checker_refuses_non_temporal_and_bad_interpreters(monkeypatch) -> None:
    records = [{"start": "sent"}]
    temporal = _req("temporal", "until(present(start), present(end))")
    payload = {"trace": records}

    assert witness._trace_prefix_check(_req("logical", "present(start)"), records, payload)[0] == (
        "refuted"
    )
    assert witness._trace_prefix_check(_req("temporal", "until("), records, payload)[0] == (
        "uncheckable"
    )
    # A syntactically valid temporal call with missing operands reaches the reference evaluator
    # and is uncheckable when that evaluator cannot interpret it.
    bad_eval = _req("temporal", "until(present(start))")
    assert witness._trace_prefix_check(bad_eval, records, payload)[0] == "uncheckable"

    monkeypatch.setattr(witness, "eval_temporal_trace", lambda _node, _records: [])
    assert witness._trace_prefix_check(temporal, records, payload)[0] == "refuted"


def test_temporal_prefix_checker_distinguishes_unknown_and_true_positions() -> None:
    unknown_req = _req(
        "temporal",
        "always(until(present(start), present(end) and latency >= 1))",
    )
    unknown_records = [{}, {"start": "sent", "end": "done"}]
    assert witness._trace_prefix_check(
        unknown_req, unknown_records, {"trace": unknown_records, "positions": [1]}
    )[0] == "uncheckable"

    true_req = _req("temporal", "always(until(present(start), present(end)))")
    true_records = [{}, {"start": "sent", "end": "done"}]
    assert witness._trace_prefix_check(
        true_req, true_records, {"trace": true_records, "positions": [1]}
    )[0] == "refuted"

def test_temporal_prefix_checker_handles_reference_failure_and_late_violation(monkeypatch) -> None:
    req = _req("temporal", "until(present(start), present(end))")
    records = [{"start": "sent", "end": "done"}, {"start": "sent"}]
    # The first one-record prefix is satisfied; the full prefix is the temporal counterexample.
    assert witness._trace_prefix_check(req, records, {"trace": records})[0] == "refuted"

    def raises(_node, _records):
        raise RuntimeError("reference unavailable")

    monkeypatch.setattr(witness, "eval_temporal_trace", raises)
    assert witness._trace_prefix_check(req, records, {"trace": records})[0] == "uncheckable"


def test_observed_prefix_fallback_and_pair_shape_are_covered(monkeypatch) -> None:
    req = _req("temporal", "always(until(present(start), present(end)))")
    records = [{"start": "sent"}, {"start": "sent"}]
    calls = 0

    def folded(_node, _records):
        nonlocal calls
        calls += 1
        return [False] if calls == 1 else []

    monkeypatch.setattr(observed_engine, "eval_temporal_trace", folded)
    result = ObservedEngine.evaluate(req, object(), records)
    assert result.verdict is Verdict.VIOLATED
    assert result.details["violation_step_indices"] == [0]

    pair_req = _req("counterfactual", "counterfactually_invariant(outcome, protected)")
    assert witness._pair_check(
        pair_req, object(), [{"protected": 0}, {"protected": 0}]
    )[0] == "refuted"

def test_temporal_prefix_work_does_not_hide_unsupported_domain_sorts(monkeypatch) -> None:
    class Sort:
        def kind(self):
            return -1

    class Const:
        def sort(self):
            return Sort()

    class Solver:
        def add(self, _constraint):
            pass

        def check(self):
            return "sat"

    class Scope:
        inputs = {"x": Const()}

    monkeypatch.setattr(
        "reasonsmith.engines.proved.encode_logic_domain",
        lambda _logic: (Scope(), Solver(), [], {}),
    )
    admitted, reason = witness._admissible(object(), {"x": 1})
    assert admitted is False and "unsupported declared sort" in reason
