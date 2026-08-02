"""Holds `docs/three-systems.md` and its three adapters to what they actually do.

What this module is for:
  `docs/three-systems.md` is the answer to "how does any model get fed into this tool and have a
  legal property verified on it?": three genuinely different systems under `docs/adapters/`,
  checked against one binding duty, reaching three different rungs. The claim is only worth
  anything while the printed output is the real output and the rungs are still three, so this
  module checks both.

What a reader must not break:
  - Transcripts are compared verbatim, positionally paired ```sh block to ```text block, the same
    way `test_docs_example_output.py` holds the worked example. Normalising whitespace or matching
    substrings would let a stale transcript pass, which is the one failure this exists to catch.
  - `test_the_neural_system_cannot_be_raised_above_observed` is the honest half of the artefact.
    The neural system exposes a decision log and nothing else, so `probed` needs something to
    re-run that is not there and `proved` needs something to read that is not there. Raising that
    ceiling means changing the *system*; a change that raises it by handing the adapter a replay
    hook makes the document overclaim, which is the exact failure this package exists to prevent.
"""

import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from reasonsmith.engines.probed import ProbedEngine
from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.rulelang import STATE_FRAGMENTS
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

REPO_ROOT = Path(__file__).resolve().parents[1]
THREE_SYSTEMS = REPO_ROOT / "docs" / "three-systems.md"
ADAPTERS = REPO_ROOT / "docs" / "adapters"

PAIR_RE = re.compile(r"```sh\n(.*?)\n```\n\n```text\n(.*?)```\n", re.DOTALL)


def _load(module_name: str):
    """Import one adapter file the way a reader who copied it would run it."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, ADAPTERS / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _duty(module):
    """The one shipped requirement the adapter names, unmodified."""
    return load_pack("ecoa").get_requirement(module.REQUIREMENT_ID)


def test_committed_transcripts_are_the_real_stdout():
    text = THREE_SYSTEMS.read_text(encoding="utf-8")
    pairs = PAIR_RE.findall(text)
    assert len(pairs) == 3, "expected three command/transcript pairs in docs/three-systems.md"

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    for command, transcript in pairs:
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
        ), f"transcript for `{command}` is stale"


def test_one_duty_reaches_three_different_rungs():
    """The thesis of the document, asserted rather than described.

    The same shipped requirement, three systems, three strengths — and all three satisfied, so the
    difference between them is how far the claim reaches, never whether it holds.
    """
    reached = {}
    for module_name in ("neural_scorer", "probabilistic_scorer", "symbolic_rules"):
        module = _load(module_name)
        result = evaluate_requirement(_duty(module), module.system_under_test())
        assert result.verdict == Verdict.SATISFIED, module_name
        reached[module_name] = result.strength

    assert reached == {
        "neural_scorer": Strength.OBSERVED,
        "probabilistic_scorer": Strength.PROBED,
        "symbolic_rules": Strength.PROVED,
    }


def test_the_neural_system_cannot_be_raised_above_observed():
    """`observed` is this system's ceiling, and it is a fact about the surface it exposes."""
    module = _load("neural_scorer")
    sut = module.system_under_test()
    req = _duty(module)

    assert not hasattr(sut, "decide"), "the black box must expose no replay hook"
    assert sut.logic() is None, "the black box must expose no logic to reason over"

    # Not merely "the ladder chose observed": the two stronger engines have nothing to work with.
    probed = ProbedEngine.evaluate(req, sut, list(sut.decisions()))
    assert probed.strength is None
    assert probed.details["reason"] == "no_decide"

    assert evaluate_requirement(req, sut).strength == Strength.OBSERVED


def test_the_probed_verdict_carries_the_budget_that_produced_it():
    module = _load("probabilistic_scorer")
    result = evaluate_requirement(_duty(module), module.system_under_test())

    budget = result.details["probe_budget"]
    assert budget["trials"] > 0
    assert budget["seed"] == 0
    assert set(budget["input_space"]) >= set(_duty(module).requires)


def test_each_adapter_reports_only_the_duty_it_names():
    """The report's pack line says which duty was run, so no reader reads it as the whole pack."""
    for module_name in ("neural_scorer", "probabilistic_scorer", "symbolic_rules"):
        module = _load(module_name)
        pack = load_pack("ecoa")
        one_duty = replace(
            pack,
            id=f"{pack.id}:{module.REQUIREMENT_ID}",
            requirements=(pack.get_requirement(module.REQUIREMENT_ID),),
        )
        report = check_conformance(module.system_under_test(), one_duty, system_name=module_name)
        assert report.counts["total"] == 1
        assert report.pack_id.endswith(module.REQUIREMENT_ID)


def test_the_chosen_duty_is_binding_and_reaches_an_undeclared_system():
    """Why this duty and not `gdpr_recital71_meaningful_explanation`, asserted where it can rot.

    "Undeclared" is now about the regulatory class only. The duty is limited to the
    `consumer-credit` decision domain, so each of the three systems declares that domain — which
    is what puts it inside a duty about adverse-action reasons. A system that declared nothing
    would be reported not applicable here rather than judged, and the artefact would demonstrate
    nothing; that is the gate working, not a way around it.

    The fragment changed from `record` to `logical` when the duty gained the (a)(2)(i) trigger and
    the clause's own negative constraint: an implication is not a conjunction of `present()` atoms.
    Both are `STATE_FRAGMENTS` — properties of a single decision record — which is what keeps all
    three rungs reachable, and is why the assertion below is on that rather than on either name.
    A `temporal` property here would cap every system at `observed` and the document would have no
    thesis left.
    """
    req = load_pack("ecoa").get_requirement("ecoa_reg_b_1002_9_b_2_specific_reasons")
    assert req.binding is True
    assert req.scope == ""
    assert req.domains == ("consumer-credit",)
    assert req.formalism == "logical"
    assert req.formalism in STATE_FRAGMENTS
    for name in ("neural_scorer", "probabilistic_scorer", "symbolic_rules"):
        module = _load(name)
        assert module.system_under_test().system_domains == ("consumer-credit",)
