"""Holds the built distribution to what the documented commands need from it.

What this module is for:
  The README's flagship demonstration is three commands, and for one release they all failed for
  the audience the README is written for: the wheel shipped `table7.toml` and the packs and
  nothing else, so `python -m reasonsmith.examples.neural_scorer`, the `--system-module` run and
  the sample-log run each died on a file `pip install reasonsmith` had never put on disk. Reading
  the documentation from a checkout could not see it — every one of those files was right there.
  This test builds the distribution and reads what is actually inside it, which is the only view
  that can.

What a reader must not break:
  - The wheel is built from this tree, not inspected from the source directory. A test that
    listed `src/reasonsmith/examples/` would have passed on the day the defect shipped.
  - The build runs against a copy of the tree with `*.egg-info` left out. `include-package-data`
    defaults to true, and setuptools will happily read a stale `SOURCES.txt` an editable install
    left behind and ship a data file the `package-data` entry no longer names — so a build in a
    developer's working directory reports a wheel nobody else would get. Removing that exclusion
    makes this test pass while the published wheel is missing the file.
  - `sample_decisions.jsonl` is the member that needs `pyproject.toml`'s `package-data` entry: a
    `.py` file ships by being a module, a data file does not ship at all unless named. Dropping
    the `examples/*.jsonl` pattern is the exact regression this fails on.
  - The module list is taken from the commands the documentation prints. A file that stops being
    documented can leave this list; a documented file may not.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Every path inside the installed package that a command in `README.md`,
#: `docs/three-systems.md` or `docs/language-model.md` depends on existing after
#: `pip install reasonsmith`, with no checkout and no data of the reader's own.
DOCUMENTED_PACKAGE_FILES = (
    "reasonsmith/examples/__init__.py",
    "reasonsmith/examples/__main__.py",
    "reasonsmith/examples/neural_scorer.py",
    "reasonsmith/examples/onnx_credit_scorer.py",
    "reasonsmith/examples/probabilistic_scorer.py",
    "reasonsmith/examples/symbolic_rules.py",
    "reasonsmith/examples/recounted_reason_trace.py",
    "reasonsmith/examples/language_model_notices.py",
    "reasonsmith/examples/truncating_credit_system.py",
    "reasonsmith/examples/sample_decisions.jsonl",
    "reasonsmith/table7.toml",
    "reasonsmith/packs/ecoa.toml",
    "reasonsmith/packs/eu_ai_act.toml",
    "reasonsmith/packs/gdpr.toml",
    "reasonsmith/packs/table7.toml",
)


#: Left out of the copy the wheel is built from: build leftovers that would make the build report
#: something other than what a fresh clone produces, `.git`, and the virtualenvs and caches a
#: working directory accumulates.
_NOT_COPIED = shutil.ignore_patterns(
    "*.egg-info", "__pycache__", "build", "dist", ".git", ".venv", ".*_cache"
)


def _build(source: Path, destination: Path, isolated: bool) -> subprocess.CompletedProcess:
    """One `pip wheel` run over `source`, with or without PEP 517 build isolation."""
    command = [sys.executable, "-m", "pip", "wheel", str(source), "--no-deps", "--no-cache-dir"]
    if not isolated:
        command.append("--no-build-isolation")
    command += ["--wheel-dir", str(destination)]
    return subprocess.run(command, capture_output=True, text=True)


def _built_wheel_members(destination: Path) -> set[str]:
    """Build a wheel from a clean copy of this tree and return the paths it carries.

    The first attempt is unisolated, which needs no network when the environment already has the
    `setuptools` backend `pyproject.toml` names. A modern CI runner may not have it — a venv on
    3.12+ ships without setuptools — so a failure falls back to an isolated build, which fetches
    the backend. Only both failing is a failure: neither a missing backend nor a missing network
    is this test's finding, but silently skipping would leave the wheel unchecked.
    """
    source = destination / "tree"
    shutil.copytree(REPO_ROOT, source, ignore=_NOT_COPIED, symlinks=True)
    build = _build(source, destination, isolated=False)
    if build.returncode != 0:
        unisolated = build
        build = _build(source, destination, isolated=True)
        if build.returncode != 0:
            pytest.fail(
                "building the wheel failed, unisolated and isolated:\n"
                f"{unisolated.stdout}\n{unisolated.stderr}\n{build.stdout}\n{build.stderr}"
            )
    wheels = sorted(destination.glob("reasonsmith-*.whl"))
    assert len(wheels) == 1, f"expected exactly one reasonsmith wheel, got {wheels}"
    with zipfile.ZipFile(wheels[0]) as wheel:
        return set(wheel.namelist())


def test_the_wheel_carries_every_file_a_documented_command_needs(tmp_path):
    members = _built_wheel_members(tmp_path)
    missing = [name for name in DOCUMENTED_PACKAGE_FILES if name not in members]
    assert not missing, (
        "the built wheel is missing files documented commands depend on: "
        f"{', '.join(missing)}. A data file needs a pattern in pyproject.toml's "
        "[tool.setuptools.package-data]; a module needs to live in a discovered package."
    )
