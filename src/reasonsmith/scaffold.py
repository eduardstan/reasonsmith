"""Generate installable out-of-tree pack and engine plug-in skeletons."""

from __future__ import annotations

import re
from pathlib import Path

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class ScaffoldError(ValueError):
    """Raised when a requested scaffold cannot be created safely."""


def _module_name(name: str) -> str:
    module = name.replace("-", "_").lower()
    if not _NAME_RE.fullmatch(name) or not module.isidentifier():
        raise ScaffoldError(
            f"{name!r} is not a valid scaffold name; use letters, numbers, '-' or '_' "
            "and start with a letter"
        )
    return module


def _pyproject(name: str, module: str, group: str, target: str) -> str:
    package_data = (
        f"\n[tool.setuptools.package-data]\n{module} = [\"pack.toml\"]\n"
        if group == "reasonsmith.packs"
        else ""
    )
    return f'''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
description = "{target} plug-in for reasonsmith"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["reasonsmith>=0.9"]

[project.entry-points."{group}"]
{name} = "{module}:{target}"

[tool.setuptools.packages.find]
where = ["src"]
{package_data}'''


def _pack_files(name: str, module: str) -> dict[str, str]:
    pack_id = name.replace("-", "_")
    pack_toml = f'''# TODO: replace every placeholder with a source-backed requirement
# before shipping.
[pack]
id = "{pack_id}"
title = "TODO: pack title"
description = "TODO: describe the source, scope, and formalisation limits."

[source]
document = "TODO: official source or internal policy"
publication = "TODO: publication or provenance record"
url = "https://example.invalid/replace-me"

[[requirement]]
id = "{pack_id}_todo"
source_document = "TODO: source document"
article_clause = "TODO: exact article or section"
verbatim_text = "TODO: replace with the exact source text."
stakeholder = "TODO: affected stakeholder"
formalism = "record"
spec = "present(todo_signal)"
rationale = "TODO: explain what this property establishes and what it leaves out."
requires = ["todo_signal"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
'''
    return {
        "pyproject.toml": _pyproject(name, module, "reasonsmith.packs", "pack_path"),
        "README.md": f'''# {name}

An out-of-tree reasonsmith requirement-pack plug-in.

1. Replace the TODO source and requirement fields in `src/{module}/pack.toml` with
   traceable, legally reviewed content.
2. Run `reasonsmith validate-pack src/{module}/pack.toml`.
3. Install this package (`pip install -e .`) and check it by entry-point name:
   `reasonsmith validate-pack {name}`.

Read the [pack authoring guide](https://github.com/eduardstan/reasonsmith/blob/main/docs/authoring-packs.md)
for the complete contract. The generated row is deliberately a placeholder, not legal advice.
''',
        f"src/{module}/__init__.py": '''"""Entry point for the generated reasonsmith pack
plug-in."""

from pathlib import Path


def pack_path() -> Path:
    """Return the packaged TOML file for the ``reasonsmith.packs`` entry point."""
    return Path(__file__).with_name("pack.toml")
''',
        f"src/{module}/pack.toml": pack_toml,
    }


def _engine_files(name: str, module: str) -> dict[str, str]:
    return {
        "pyproject.toml": _pyproject(name, module, "reasonsmith.engines", "engine"),
        "README.md": f'''# {name}

An out-of-tree reasonsmith engine plug-in scaffold. The generated engine declines every
requirement until you implement one deliberately.

- Read the [engine authoring guide](https://github.com/eduardstan/reasonsmith/blob/main/docs/authoring-engines.md).
- Run `reasonsmith verify-engine {name}` to validate the installed engine entry point
  against the engine contract.
- Install this package (`pip install -e .`) to make the entry point discoverable.

The stub's explicit `max_strength` is `observed`; raising it is a claim that your engine must
make and support with the guide's result contract.
''',
        f"src/{module}/__init__.py": '''"""Entry point for the generated reasonsmith engine
plug-in."""

from .engine import engine

__all__ = ["engine"]
''',
        f"src/{module}/engine.py": '''"""A declining engine scaffold; implement only after
reading the authoring guide."""

from reasonsmith.report import RequirementResult, evidence_basis
from reasonsmith.verdict import Strength, Verdict


class StubEngine:
    """Decline every requirement until a real engine is implemented.

    See https://github.com/eduardstan/reasonsmith/blob/main/docs/authoring-engines.md.
    """

    max_strength = Strength.OBSERVED.value

    def evaluate(self, req, sut, records) -> RequirementResult:
        """Return an honest non-answer for every offered requirement."""
        del sut, records
        return RequirementResult(
            requirement_id=req.id,
            source_clause=f"{req.source_document} {req.article_clause}",
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary="Not evaluated: this scaffold engine declines the requirement.",
            binding=req.binding,
            scope=req.scope,
            domains=tuple(req.domains),
            basis=evidence_basis(req),
            verbatim_text=req.verbatim_text,
        )


engine = StubEngine()
''',
    }


def create_scaffold(kind: str, name: str, parent: str | Path = ".") -> Path:
    """Create a new package directory for a ``pack`` or ``engine`` plug-in."""
    if kind not in {"pack", "engine"}:
        raise ScaffoldError(f"unknown scaffold kind {kind!r}; choose 'pack' or 'engine'")
    module = _module_name(name)
    target = Path(parent) / name
    if target.exists():
        raise ScaffoldError(f"refusing to overwrite existing directory {target}")
    files = _pack_files(name, module) if kind == "pack" else _engine_files(name, module)
    try:
        for relative, content in files.items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    except OSError:
        # Best-effort cleanup keeps a failed scaffold from looking installable.
        import shutil

        shutil.rmtree(target, ignore_errors=True)
        raise
    return target
