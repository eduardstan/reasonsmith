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

#: Exactly the fields a [[requirement]] block carries. A pack that omits one is
#: rejected at load time rather than producing a requirement that cannot be
#: traced back to its source, and one that adds a field the loader does not read
#: is rejected too rather than looking like it carries data nothing acts on.
REQUIREMENT_FIELDS = (
    "id",
    "source_document",
    "article_clause",
    "verbatim_text",
    "stakeholder",
    "formalism",
    "spec",
    "requires",
    "binding",
    "scope",
)


@dataclass(frozen=True)
class Requirement:
    """A single regulatory or governance requirement with signal dependencies.

    `requires` names the signals a system must be capable of emitting for this
    requirement to be checkable at all.
    `binding` indicates if this duty is a legally binding obligation (true) or
    an interpretive recital/guidance item (false).
    `scope` records any regulatory class limit (e.g. 'high-risk').
    """

    id: str
    source_document: str
    article_clause: str
    verbatim_text: str
    stakeholder: str
    formalism: Literal["record", "temporal", "logical"]
    spec: str
    requires: tuple[str, ...]
    binding: bool = True
    scope: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.binding, bool):
            raise ValueError(f"Requirement {self.id!r}: field 'binding' must be a boolean")
        if not isinstance(self.scope, str):
            raise ValueError(f"Requirement {self.id!r}: field 'scope' must be a string")
        if self.formalism not in VALID_FORMALISMS:
            raise ValueError(
                f"Invalid formalism {self.formalism!r}; must be one of {VALID_FORMALISMS}"
            )
        # Traceability is the point of a pack: a requirement with a blank source
        # document, clause or quotation cannot be checked against the print, so it
        # is malformed rather than merely incomplete.
        text_fields = (
            "id", "source_document", "article_clause", "verbatim_text", "stakeholder", "spec",
        )
        for name in text_fields:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Requirement {self.id!r}: field {name!r} must be a non-empty string, "
                    f"got {value!r}"
                )
        if not self.requires:
            raise ValueError(f"Requirement {self.id!r} must specify at least one required signal")
        for signal in self.requires:
            if not isinstance(signal, str) or not signal.strip():
                raise ValueError(
                    f"Requirement {self.id!r}: every entry of 'requires' must be a non-empty "
                    f"signal name, got {signal!r}"
                )
        if len(set(self.requires)) != len(self.requires):
            raise ValueError(f"Requirement {self.id!r}: 'requires' contains duplicate signal names")

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
            "binding": self.binding,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class Pack:
    """A collection of formal requirements with source metadata."""

    id: str
    title: str
    description: str
    requirements: tuple[Requirement, ...]
    source_metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.requirements:
            raise ValueError(f"Pack {self.id!r} contains no requirements")
        ids = [r.id for r in self.requirements]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            # get_requirement returns the first match, so a duplicate id would make one of the
            # two requirements silently unreachable and never reported on.
            raise ValueError(f"Pack {self.id!r} has duplicate requirement id(s): {duplicates}")

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
        raise FileNotFoundError(
            f"Pack file not found: {name_or_path}. "
            f"Built-in packs: {', '.join(list_packs()) or 'none'}"
        )

    with path.open("rb") as f:
        data = tomllib.load(f)

    pack_info = data.get("pack", {})
    pack_id = pack_info.get("id", path.stem)
    title = pack_info.get("title", pack_id)
    description = pack_info.get("description", "")

    source_meta = data.get("source", {})

    raw_reqs = data.get("requirement", [])
    if not raw_reqs:
        raise ValueError(f"Pack {path} declares no [[requirement]] blocks")

    reqs = []
    for index, rdata in enumerate(raw_reqs):
        where = f"{path} [[requirement]] #{index + 1} ({rdata.get('id', 'no id')!r})"
        missing = [f for f in REQUIREMENT_FIELDS if f not in rdata]
        if missing:
            raise ValueError(f"{where}: missing required field(s): {', '.join(missing)}")
        # A key the loader does not read is silently dropped, so a pack with `stakeholders`
        # or a speculative `strength` would load clean and look like it carries data it does
        # not. evidence.emit rejects off-row keys for the same reason.
        unknown = sorted(set(rdata) - set(REQUIREMENT_FIELDS))
        if unknown:
            raise ValueError(
                f"{where}: unknown field(s): {', '.join(unknown)}. A requirement block carries "
                f"exactly these fields: {', '.join(REQUIREMENT_FIELDS)}"
            )
        if not isinstance(rdata["binding"], bool):
            raise ValueError(
                f"{where}: 'binding' must be a boolean, got {type(rdata['binding']).__name__}"
            )
        if not isinstance(rdata["scope"], str):
            raise ValueError(
                f"{where}: 'scope' must be a string, got {type(rdata['scope']).__name__}"
            )
        # A bare string is iterable, so tuple("reasons") would silently become five
        # single-character signal names. Reject anything that is not a TOML array.
        if not isinstance(rdata["requires"], list):
            raise ValueError(
                f"{where}: 'requires' must be an array of signal names, got "
                f"{type(rdata['requires']).__name__}"
            )
        try:
            req = Requirement(
                id=rdata["id"],
                source_document=rdata["source_document"],
                article_clause=rdata["article_clause"],
                verbatim_text=rdata["verbatim_text"],
                stakeholder=rdata["stakeholder"],
                formalism=rdata["formalism"],
                spec=rdata["spec"],
                requires=tuple(rdata["requires"]),
                binding=rdata["binding"],
                scope=rdata["scope"],
            )
        except ValueError as exc:
            raise ValueError(f"{where}: {exc}") from exc
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
