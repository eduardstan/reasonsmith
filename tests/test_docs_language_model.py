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
