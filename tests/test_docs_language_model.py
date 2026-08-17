"""Holds `docs/language-model.md` and its adapter to what they actually do.

What this module is for:
  `docs/three-systems.md` is about rungs. `docs/language-model.md` is about the axis underneath —
  which duties a system can be answered on at all — and its whole claim is that a language model
  reaches `probed` on one half of 12 CFR 1002.9(b)(2) and `unattainable` on the other. That is
  worth something only while the printed output is the real output and the ceiling is real, so this
  module checks both.

What a reader must not break:
  - The transcript is compared verbatim, ```sh block to ```text block, the same way
    `test_docs_three_systems.py` holds its three. Normalising whitespace or matching substrings
    would let a stale transcript pass, which is the one failure this exists to catch.
  - `test_the_language_model_cannot_be_raised_above_probed` asserts the ceiling on the *mechanism*.
    `logic()` is `None`, so the solver has nothing to read and `proved` is unreachable however the
    adapter is written; and the adequacy duty is reported unattainable naming the signal it lacks,
    never quietly answered by the presence check that shares its clause. Both are facts about what
    the system exposes. A change that lifts either by editing the adapter rather than the system
    makes the document overclaim, which is the exact failure this package exists to prevent.
"""

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.engines.counterfactual import PairedReplayEngine
from reasonsmith.neural import DeclaredInputSpace, render_template
from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = REPO_ROOT / "docs" / "language-model.md"

PAIR_RE = re.compile(r"```sh\n(.*?)\n```\n\n```text\n(.*?)```\n", re.DOTALL)

#: The two halves of 12 CFR 1002.9(b)(2), and the whole point of the document.
PRESENCE_DUTY = "ecoa_reg_b_1002_9_b_2_specific_reasons"
ADEQUACY_DUTY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"


def _adapter():
    """Import the example system the way a reader who installed the package would reach it."""
    return importlib.import_module("reasonsmith.examples.language_model_notices")


def test_committed_transcript_is_the_real_stdout():
    pairs = PAIR_RE.findall(DOCUMENT.read_text(encoding="utf-8"))
    assert len(pairs) == 1, "expected one command/transcript pair in docs/language-model.md"
    command, transcript = pairs[0]

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run(
        command.replace("python ", f"{sys.executable} ", 1),
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert run.returncode == 0, f"{command} exited {run.returncode}: {run.stderr}"
    assert (
        run.stdout.replace("\r\n", "\n") == transcript.replace("\r\n", "\n")
    ), "transcript for docs/language-model.md is stale"


def test_the_stub_model_is_deterministic():
    """A generated document that changes between runs is worse than no document."""
    module = _adapter()
    once = list(module.system_under_test().decisions())
    twice = list(module.system_under_test().decisions())
    assert once == twice


def test_the_language_model_cannot_be_raised_above_probed():
    """`probed` is this system's ceiling, and it is a fact about the surface it exposes."""
    module = _adapter()
    sut = module.system_under_test()
    pack = load_pack("ecoa")

    # `proved` is structurally unreachable: there is nothing for the solver to read.
    assert sut.logic() is None, "a prompt is not a rule set; logic() must stay unexposed"

    result = evaluate_requirement(pack.get_requirement(PRESENCE_DUTY), sut)
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED


def test_the_adequacy_duty_is_unattainable_and_names_the_signal_it_lacks():
    """The finding: reasonsmith refuses the duty rather than answering the easier one instead."""
    module = _adapter()
    sut = module.system_under_test()

    assert "artifact_logs_deleted_reason_count" not in sut.capabilities()

    result = evaluate_requirement(load_pack("ecoa").get_requirement(ADEQUACY_DUTY), sut)
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength == Strength.UNATTAINABLE
    assert list(result.signals_missing) == ["artifact_logs_deleted_reason_count"]


def test_the_probed_verdict_carries_the_budget_that_produced_it():
    module = _adapter()
    duty = load_pack("ecoa").get_requirement(PRESENCE_DUTY)
    result = evaluate_requirement(duty, module.system_under_test())

    budget = result.details["probe_budget"]
    assert budget["trials"] > 0
    assert budget["seed"] == 0
    assert set(budget["input_space"]) >= set(duty.requires)


def test_an_unchanged_callable_without_input_space_remains_not_evaluated():
    """The additive hook does not reinterpret an old callable as counterfactual evidence."""
    module = _adapter()
    old = CallableAdapter(
        lambda case: {**case, "artifact_logs_decision_record": "notice"},
        declared_capabilities={"artifact_logs_decision_record"},
        decisions=[{"artifact_logs_decision_record": "notice"}],
    )
    result = PairedReplayEngine.evaluate(
        load_pack("ecoa").get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment"),
        old,
    )
    assert result.strength is None
    assert result.details["reason"] == "no_declared_input_space"
    assert module.system_under_test().logic() is None


def test_a_protected_slot_absent_from_the_declared_template_is_refused():
    """A declaration cannot name a protected slot the runtime template does not render."""
    from reasonsmith.neural import DeclaredInputSpace

    with pytest.raises(ValueError, match="does not expose slot"):
        DeclaredInputSpace(
            [{"signal": "applicant_prohibited_basis", "type": "string-enum", "values": ["a"]}],
            template="notice without the protected placeholder",
        )


def test_counterfactual_budget_carries_candidate_values_and_replay_accounting():
    module = _adapter()
    result = evaluate_requirement(
        load_pack("ecoa").get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment"),
        module.system_under_test(),
    )
    assert result.strength == Strength.PROBED
    budget = result.details["probe_budget"]
    assert budget["input_space"]["protected values enumerated"] == list(module.PROTECTED_VALUES)
    assert budget["pairs_attempted"] == 4
    assert budget["facts_switched"] == 4
    assert budget["calls_made"] == 8
    assert budget["terminated"] is True
    assert budget["termination"] == "complete"


def test_shared_renderer_is_deterministic_and_checks_domains_and_constraints():
    space = DeclaredInputSpace(
        [
            {
                "signal": "basis",
                "type": "string-enum",
                "values": ("a", "b"),
                "value_to_token": {"a": "A token", "b": "B token"},
            },
            {"signal": "score", "type": "integer", "lower": 0, "upper": 10},
        ],
        constraints=[{"signal": "score", "op": ">=", "value": 2}],
        template={"text": "basis={basis}; score={score}", "escaping": "url"},
    )
    values = {"basis": "a", "score": 2}
    assert render_template(space, values) == "basis=A%20token; score=2"
    assert render_template(space, values) == render_template(space, values)
    with pytest.raises(ValueError, match="finite domain"):
        render_template(space, {"basis": "c", "score": 2})
    with pytest.raises(ValueError, match="constraint"):
        render_template(space, {"basis": "a", "score": 1})
    with pytest.raises(ValueError, match="cover exactly"):
        render_template(space, {"basis": "a"})


def test_callable_rejects_a_target_template_that_disagrees_with_the_declaration():
    class Target:
        template = "actual={basis}"

        def decide(self, case):
            return {"artifact_logs_decision_record": "notice"}

    space = DeclaredInputSpace(
        [{
            "signal": "basis",
            "type": "string-enum",
            "values": ("a",),
            "value_to_token": {"a": "A"},
        }],
        template="declared={basis}",
    )
    with pytest.raises(ValueError, match="actual template"):
        CallableAdapter(Target(), {"artifact_logs_decision_record"}, input_space=space)


def test_renderer_supports_json_and_mapping_declarations_and_rejects_numeric_values():
    from reasonsmith.neural import render_declared_template

    declaration = {
        "slots": [
            {"signal": "integer", "type": "integer", "lower": 0, "upper": 3},
            {"signal": "real", "type": "real", "lower": 0, "upper": 1},
        ],
        "template": {"text": "i={integer}; r={real}", "escaping": "json"},
    }
    assert render_declared_template(
        declaration, {"integer": 1, "real": 0.5}
    ) == 'i="1"; r="0.5"'
    space = DeclaredInputSpace.from_value(declaration)
    with pytest.raises(ValueError, match="integer value"):
        render_template(space, {"integer": True, "real": 0.5})
    with pytest.raises(ValueError, match="numeric value"):
        render_template(space, {"integer": 1, "real": "bad"})
    with pytest.raises(ValueError, match="outside"):
        render_template(space, {"integer": 4, "real": 0.5})
    with pytest.raises(ValueError, match="outside"):
        render_template(space, {"integer": 1, "real": 2.0})


def test_renderer_checks_cross_input_constraints_and_identifier_templates():
    from reasonsmith.neural import render_declared_template

    space = DeclaredInputSpace(
        [
            {"signal": "left", "type": "integer", "lower": 0, "upper": 2},
            {"signal": "right", "type": "integer", "lower": 0, "upper": 2},
        ],
        constraints=[{"left": "left", "op": "<=", "right": "right"}],
        template="{left}/{right}",
    )
    assert render_template(space, {"left": 1, "right": 2}) == "1/2"
    with pytest.raises(ValueError, match="constraint"):
        render_template(space, {"left": 2, "right": 1})
    identifier = DeclaredInputSpace(
        [{"signal": "x", "type": "string-enum", "values": ("a",), "value_to_token": {"a": "a"}}],
        template={"identifier": "template-sha256", "placeholders": {"x": "x"}},
    )
    with pytest.raises(ValueError, match="renderable"):
        render_declared_template(identifier, {"x": "a"})


def test_callable_accepts_prompt_template_alias_and_template_free_targets():
    class AliasTarget:
        prompt_template = "declared={basis}"

        def __call__(self, case):
            return {"artifact_logs_decision_record": "notice"}

    space = DeclaredInputSpace(
        [{
            "signal": "basis",
            "type": "string-enum",
            "values": ("a",),
            "value_to_token": {"a": "A"},
        }],
        template="declared={basis}",
    )
    assert (
        CallableAdapter(
            AliasTarget(), {"artifact_logs_decision_record"}, input_space=space
        ).input_space()
        == space
    )

    class NoTemplateTarget:
        def __call__(self, case):
            return {"artifact_logs_decision_record": "notice"}

    assert (
        CallableAdapter(
            NoTemplateTarget(), {"artifact_logs_decision_record"}, input_space=space
        ).input_space()
        == space
    )


def test_neural_helpers_cover_declared_constraint_and_dtype_boundaries():
    import reasonsmith.neural as neural

    space = DeclaredInputSpace(
        [{"signal": "x", "type": "integer", "lower": 0, "upper": 2}],
        constraints=[{"signal": "x", "op": ">=", "value": 0}],
    )
    assert neural._constraint_holds(space, {})
    assert neural._constraint_holds(space, {"x": 1})
    assert neural._dtype_name(neural.TensorProto.FLOAT) == "float32"
    assert neural._dtype_name(neural.TensorProto.DOUBLE) == "float64"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(neural, "TensorProto", None)
    assert neural._dtype_name(123) == "123"
    monkeypatch.undo()


def test_onnx_constant_tensor_attributes_are_checked(monkeypatch):
    pytest.importorskip("onnx")
    from onnx import TensorProto, helper

    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1])
    constant = helper.make_tensor("constant", TensorProto.FLOAT, [1], [0.0])
    graph = helper.make_graph(
        [helper.make_node("Constant", [], ["y"], value=constant)], "constant", [x], [y]
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    from reasonsmith.neural import OnnxArtifact

    artifact = OnnxArtifact(
        model=model.SerializeToString(),
        inputs=[{"name": "x", "signal_map": {"x": 0}}],
        outputs=[
            {
                "name": "y",
                "signal_map": {"score": 0},
                "decoder": {
                    "score": {"threshold": 0, "low": "no", "high": "yes", "tie": "no"}
                },
            }
        ],
        input_space=DeclaredInputSpace(
            [{"signal": "x", "type": "real", "lower": 0, "upper": 1}]
        ),
    )
    assert artifact.model_sha256
    import reasonsmith.neural as neural
    monkeypatch.setattr(neural, "onnx", None)
    with pytest.raises(ValueError, match="validation requires"):
        OnnxArtifact(
            model=model.SerializeToString(),
            inputs=[{"name": "x", "signal_map": {"x": 0}}],
            outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": {
                "score": {"threshold": 0, "low": "no", "high": "yes", "tie": "no"}
            }}],
            input_space=DeclaredInputSpace(
                [{"signal": "x", "type": "real", "lower": 0, "upper": 1}]
            ),
        )


def test_onnx_schema_rejects_custom_domain_and_missing_metadata(monkeypatch):
    pytest.importorskip("onnx")
    from onnx import TensorProto, helper

    import reasonsmith.neural as neural
    from reasonsmith.neural import OnnxArtifact
    monkeypatch.setattr(neural.checker, "check_model", lambda *args, **kwargs: None)

    def make(node, *, opsets=True, ir=True, custom=False):
        x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1])
        y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1])
        model = helper.make_model(
            helper.make_graph([node], "bad", [x], [y]),
            opset_imports=[helper.make_opsetid("", 13)] if opsets else [],
        )
        if custom:
            model.opset_import.append(helper.make_opsetid("custom", 1))
        if not ir:
            model.ir_version = 0
        return model.SerializeToString()

    def artifact(data):
        return OnnxArtifact(
            model=data,
            inputs=[{"name": "x", "signal_map": {"x": 0}}],
            outputs=[{"name": "y", "signal_map": {"score": 0}, "decoder": {
                "score": {"threshold": 0, "low": "no", "high": "yes", "tie": "no"}
            }}],
            input_space=DeclaredInputSpace(
                [{"signal": "x", "type": "real", "lower": 0, "upper": 1}]
            ),
        )

    with pytest.raises(ValueError, match="custom ONNX"):
        artifact(make(helper.make_node("Identity", ["x"], ["y"], domain="custom"), custom=True))
    with pytest.raises(ValueError, match="opset"):
        artifact(make(helper.make_node("Identity", ["x"], ["y"]), opsets=False))
    with pytest.raises(ValueError, match="IR version"):
        artifact(make(helper.make_node("Identity", ["x"], ["y"]), ir=False))
