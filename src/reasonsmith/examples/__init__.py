"""The runnable example systems and the sample decision log, shipped inside the package.

What this module is for:
  Every command the README and `docs/three-systems.md` print must run for the reader who typed
  `pip install reasonsmith` and nothing else. Before these files lived here they lived under
  `docs/`, which no wheel carries, so three documented commands failed for exactly the audience
  the documentation was written for. They are ordinary package modules now:
  `python -m reasonsmith.examples.symbolic_rules` runs one, and
  `--system-module reasonsmith.examples.symbolic_rules:system_under_test` reaches the same system
  from the CLI, both without a checkout.

What a reader must not break:
  - `SAMPLE_LOG` and `EXAMPLES_DIR` are how a shell command names a file that lives inside an
    installed package: `python -m reasonsmith.examples` prints `EXAMPLES_DIR`, which is what lets
    the README's `--system` example be a literal command rather than an instruction to go and
    find the file. Renaming either one breaks a documented command.
    Why this matters: `tests/test_packaged_examples.py` builds the distribution and asserts these
    files are in it, because the defect this package exists to fix was invisible from a checkout.
  - `sample_decisions.jsonl` is package data, so `pyproject.toml`'s `package-data` entry must keep
    naming it. A `.py` file is packaged by virtue of being a module; a `.jsonl` file is not.
"""

from __future__ import annotations

from pathlib import Path

#: The directory these example systems and the sample log were installed into.
EXAMPLES_DIR = Path(__file__).resolve().parent

#: The committed three-record decision trace from a credit-scoring pipeline, so the CLI commands
#: in the README run with no data of the reader's own.
SAMPLE_LOG = EXAMPLES_DIR / "sample_decisions.jsonl"

__all__ = ["EXAMPLES_DIR", "SAMPLE_LOG"]
