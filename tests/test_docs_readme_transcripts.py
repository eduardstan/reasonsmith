"""Holds the README's transcript block to its builder.

What this module is for:
  `README.md` carries a conformance-check transcript that is CLI stdout pasted unedited, produced
  by `docs/build_readme_transcripts.py`. Every other generated document in this repository is
  pinned byte-for-byte to its builder; the README block was the one that was not, and it went
  stale once already — the ad-hoc helper that produced it silently matched nothing and the stale
  text survived a green suite. This test makes the README the same shape of guarantee the others
  are: the committed block must be exactly what the builder writes.

What a reader must not break:
  - The builder is loaded from its path and run, never re-implemented, exactly as
    `tests/test_nesyarena_conformance.py` loads `docs/build_nesyarena_report.py` and
    `tests/test_docs_audiences.py` loads `docs/build_audiences.py`. `docs/` is not an import
    package.
  - Compare verbatim. `regenerate` returns the README with every command's transcript replaced
    by that command's own stdout and raises if a substitution matches anything other than one
    block, so a stale block, a renamed command or a reordered block all fail here rather than
    passing quietly.
  - The builder is run from the repository root, because its `main()` chdirs there and the CLI
    inserts the working directory into `sys.path` to resolve `--system-module` names.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

BUILD_COMMAND = "python docs/build_readme_transcripts.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_readme_transcripts", REPO_ROOT / "docs" / "build_readme_transcripts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


def test_readme_transcripts_match_the_builder():
    """The committed block is what the command it names writes, byte-for-byte."""
    readme = README.read_text(encoding="utf-8")
    cwd = os.getcwd()
    try:
        os.chdir(REPO_ROOT)
        regenerated = builder.regenerate(readme)
    finally:
        os.chdir(cwd)
    assert readme == regenerated, (
        f"{README.name} diverges from {BUILD_COMMAND}; regenerate it with that command and commit "
        "the change"
    )
