"""Specification structures and pack loader for reasonsmith v0.2.

A Requirement defines a compliance property with verbatim source traceability,
its target stakeholder, formalism, specification text, and required signal names.

A Pack is a curated collection of Requirements from a specific regulatory or
governance source.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VALID_FORMALISMS = ("record", "temporal", "logical")
PACKS_DIR = Path(__file__).parent / "packs"


@dataclass(frozen=True)
class Requirement:
    """A single regulatory or governance requirement with signal dependencies.

    `requires` names the signals a system must be capable of emitting for this
    requirement to be checkable at all.
    """

    id: str
    source_document: str
    article_clause: str
    verbatim_text: str
    stakeholder: str
    formalism: Literal["record", "temporal", "logical"]
    spec: str
    requires: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.formalism not in VALID_FORMALISMS:
            raise ValueError(
                f"Invalid formalism {self.formalism!r}; must be one of {VALID_FORMALISMS}"
            )
        if not self.requires:
            raise ValueError(f"Requirement {self.id!r} must specify at least one required signal")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_document": self.source_document,
            "article_clause": self.article_clause,
            "verbatim_text": self.verbatim_text,
            "stakeholder": self.stakeholder,
            "formalism": self.formalism,
            "spec": self.spec,
            "requires": list(self.requires),
        }


@dataclass(frozen=True)
class Pack:
    """A collection of formal requirements with source metadata."""

    id: str
    title: str
    description: str
    requirements: tuple[Requirement, ...]
    source_metadata: dict = field(default_factory=dict)

    def get_requirement(self, req_id: str) -> Requirement:
        for req in self.requirements:
            if req.id == req_id:
                return req
        raise KeyError(f"Requirement {req_id!r} not found in pack {self.id!r}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requirements": [r.to_dict() for r in self.requirements],
            "source_metadata": dict(self.source_metadata),
        }


def load_pack(name_or_path: str | Path) -> Pack:
    """Load a regulation pack from a built-in pack name or TOML file path."""
    path = Path(name_or_path)
    if not path.is_file() and not str(name_or_path).endswith(".toml"):
        candidate = PACKS_DIR / f"{name_or_path}.toml"
        if candidate.is_file():
            path = candidate

    if not path.is_file():
        raise FileNotFoundError(f"Pack file not found: {name_or_path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    pack_info = data.get("pack", {})
    pack_id = pack_info.get("id", path.stem)
    title = pack_info.get("title", pack_id)
    description = pack_info.get("description", "")

    source_meta = data.get("source", {})

    reqs = []
    for rdata in data.get("requirement", []):
        req = Requirement(
            id=rdata["id"],
            source_document=rdata["source_document"],
            article_clause=rdata["article_clause"],
            verbatim_text=rdata["verbatim_text"],
            stakeholder=rdata["stakeholder"],
            formalism=rdata["formalism"],
            spec=rdata["spec"],
            requires=tuple(rdata["requires"]),
        )
        reqs.append(req)

    return Pack(
        id=pack_id,
        title=title,
        description=description,
        requirements=tuple(reqs),
        source_metadata=source_meta,
    )


def list_packs() -> list[str]:
    """List names of built-in requirement packs."""
    if not PACKS_DIR.exists():
        return []
    return sorted(p.stem for p in PACKS_DIR.glob("*.toml"))
