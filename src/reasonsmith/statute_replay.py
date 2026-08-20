"""Replay two sourced statutory revisions through the ordinary conformance report.

This module compares two honest ``check_conformance`` evaluations.  It does not add a verdict,
change the strength lattice, or infer that a changed answer is a legal change.  A revision is a
manifest naming a validated pack file and one or more byte snapshots of the official sources; each
source records its URL, retrieval time, SHA-256 and whether it is synthetic.  Manifests are small,
reviewable JSON files and their paths are resolved relative to the manifest.

A source snapshot is historical evidence, not a live refetch.  ``from_manifest`` verifies every
recorded hash before loading the pack.  A pack quote may differ from its source: that is a drift
finding and is retained so the comparison can say that the pack was not updated, rather than
silently treating stale text as history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from reasonsmith.drift import (
    PROVISIONS,
    SOURCES_BY_KEY,
    DriftFetchError,
    SourcePayload,
    classify,
    extract_passage,
)
from reasonsmith.report import ConformanceReport, RequirementResult, check_conformance
from reasonsmith.spec import Pack, Requirement, load_pack
from reasonsmith.sut import SystemUnderTest

SCHEMA_VERSION = 1
ChangeStatus = Literal["unchanged", "changed", "added", "removed"]
Attribution = Literal[
    "none",
    "statutory-change",
    "statutory-and-pack-change",
    "pack-change",
    "system-change",
    "evidence-change",
    "not-attributable",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SourceProvenance:
    """The provenance that makes a source snapshot auditable."""

    url: str
    retrieved_at: str
    sha256: str
    synthetic: bool = False

    def __post_init__(self) -> None:
        if not self.url or not self.retrieved_at or len(self.sha256) != 64:
            raise ValueError("source provenance requires url, retrieved_at and a SHA-256 hash")
        try:
            int(self.sha256, 16)
            datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("source provenance has an invalid timestamp or SHA-256 hash") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "synthetic": self.synthetic,
        }


@dataclass(frozen=True)
class SourceSnapshot:
    """One immutable source payload and its recorded provenance."""

    key: str
    kind: str
    payload: SourcePayload
    provenance: SourceProvenance

    def __post_init__(self) -> None:
        raw = self.payload if isinstance(self.payload, bytes) else self.payload.encode("utf-8")
        actual = _sha256(raw)
        if actual != self.provenance.sha256:
            raise ValueError(
                f"source snapshot {self.key!r} hash mismatch: manifest says "
                f"{self.provenance.sha256}, bytes are {actual}"
            )
        if self.key not in SOURCES_BY_KEY:
            raise ValueError(f"unknown statutory source key {self.key!r}")

    @classmethod
    def from_file(
        cls,
        key: str,
        path: str | Path,
        *,
        url: str,
        retrieved_at: str,
        synthetic: bool = False,
        kind: str | None = None,
    ) -> SourceSnapshot:
        raw = Path(path).read_bytes()
        source_kind = kind or SOURCES_BY_KEY[key].kind
        data: SourcePayload = raw if source_kind == "pdf" else raw.decode("utf-8")
        return cls(
            key, source_kind, data, SourceProvenance(url, retrieved_at, _sha256(raw), synthetic)
        )

    def to_manifest_entry(self, path: str) -> dict[str, object]:
        return {"key": self.key, "kind": self.kind, "path": path, **self.provenance.to_dict()}


@dataclass(frozen=True)
class StatuteRevision:
    """A pack revision together with the historical source snapshots it cites."""

    revision: str
    pack: Pack
    pack_sha256: str
    sources: tuple[SourceSnapshot, ...]
    pack_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.revision:
            raise ValueError("a statutory revision needs a non-empty revision name")
        keys = [source.key for source in self.sources]
        if len(keys) != len(set(keys)):
            raise ValueError("a statutory revision cannot contain duplicate source keys")
        required = {
            PROVISIONS[req.article_clause][0]
            for req in self.pack.requirements
            if req.article_clause in PROVISIONS
        }
        missing = sorted(required - set(keys))
        if missing:
            raise ValueError(
                f"revision {self.revision!r} is missing source snapshot(s): {', '.join(missing)}"
            )
        if len(self.pack_sha256) != 64:
            raise ValueError("a statutory revision requires the pack file SHA-256")

    @classmethod
    def from_manifest(cls, manifest: str | Path) -> StatuteRevision:
        manifest_path = Path(manifest)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported statute revision schema: {data.get('schema_version')!r}")
        root = manifest_path.parent
        pack_path = root / str(data["pack"]["path"])
        pack_bytes = pack_path.read_bytes()
        declared_pack_hash = str(data["pack"].get("sha256", ""))
        if _sha256(pack_bytes) != declared_pack_hash:
            raise ValueError("pack snapshot hash does not match its manifest")
        sources = []
        for entry in data.get("sources", []):
            path = root / str(entry["path"])
            raw = path.read_bytes()
            kind = str(entry["kind"])
            payload: SourcePayload = raw if kind == "pdf" else raw.decode("utf-8")
            prov = SourceProvenance(
                str(entry["url"]),
                str(entry["retrieved_at"]),
                str(entry["sha256"]),
                bool(entry.get("synthetic", False)),
            )
            sources.append(SourceSnapshot(str(entry["key"]), kind, payload, prov))
        return cls(
            str(data["revision"]),
            load_pack(pack_path),
            declared_pack_hash,
            tuple(sources),
            pack_path,
        )

    def source(self, key: str) -> SourceSnapshot:
        for source in self.sources:
            if source.key == key:
                return source
        raise KeyError(key)

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "pack_sha256": self.pack_sha256,
            "sources": [
                {"key": source.key, "kind": source.kind, **source.provenance.to_dict()}
                for source in self.sources
            ],
        }

    def relevant_passage(self, requirement: Requirement) -> str | None:
        source_key, selector = PROVISIONS[requirement.article_clause]
        source = self.source(source_key)
        return extract_passage(source.payload, selector=selector, kind=source.kind)

    def quote_status(
        self, requirement: Requirement
    ) -> Literal["match", "differ", "could-not-verify"]:
        try:
            passage = self.relevant_passage(requirement)
        except (DriftFetchError, KeyError):
            return "could-not-verify"
        if passage is None:
            return "could-not-verify"
        return "match" if classify(requirement.verbatim_text, passage) == "match" else "differ"

    def safe_passage(self, requirement: Requirement) -> str | None:
        try:
            return self.relevant_passage(requirement)
        except (DriftFetchError, KeyError):
            return None


@dataclass(frozen=True)
class DutyComparison:
    requirement_id: str
    status: ChangeStatus
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    changed_fields: tuple[str, ...]
    attribution: Attribution
    source_changed: bool
    pack_changed: bool
    source_status_before: str | None
    source_status_after: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "status": self.status,
            "before": self.before,
            "after": self.after,
            "changed_fields": list(self.changed_fields),
            "attribution": self.attribution,
            "source_changed": self.source_changed,
            "pack_changed": self.pack_changed,
            "source_status_before": self.source_status_before,
            "source_status_after": self.source_status_after,
        }


@dataclass(frozen=True)
class StatuteComparison:
    """Two ordinary conformance reports and a per-duty comparison of their results."""

    before: StatuteRevision
    after: StatuteRevision
    before_report: ConformanceReport
    after_report: ConformanceReport
    duties: tuple[DutyComparison, ...]

    @property
    def changed(self) -> tuple[DutyComparison, ...]:
        return tuple(duty for duty in self.duties if duty.status != "unchanged")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "before_revision": self.before.revision,
            "after_revision": self.after.revision,
            "before_snapshot": self.before.to_dict(),
            "after_snapshot": self.after.to_dict(),
            "before": self.before_report.to_dict(),
            "after": self.after_report.to_dict(),
            "duties": [duty.to_dict() for duty in self.duties],
        }

    def render_text(self) -> str:
        lines = [
            f"Statute revision comparison: {self.before.revision} -> {self.after.revision}",
            "",
        ]
        for duty in self.duties:
            before = duty.before["outcome"] if duty.before else "absent"
            after = duty.after["outcome"] if duty.after else "absent"
            lines.append(
                f"  {duty.status:9} {duty.requirement_id}: {before} -> {after} ({duty.attribution})"
            )
        lines.append("")
        lines.append(
            "A changed result is not by itself evidence that the statute changed; the "
            "attribution records source, pack, and system/evidence differences."
        )
        return "\n".join(lines)


def _pack_change_fields(before: Requirement, after: Requirement) -> tuple[str, ...]:
    left, right = before.to_dict(), after.to_dict()
    return tuple(sorted(k for k in set(left) | set(right) if left.get(k) != right.get(k)))


def _pack_changed(before: Requirement, after: Requirement) -> bool:
    return bool(_pack_change_fields(before, after))


def _result_map(report: ConformanceReport) -> dict[str, RequirementResult]:
    return {result.requirement_id: result for result in report.results}


def compare_revisions(
    before: StatuteRevision,
    after: StatuteRevision,
    sut: SystemUnderTest,
    *,
    after_sut: SystemUnderTest | None = None,
    system_changed: bool = False,
    system_name: str = "SUT",
    system_scope: str | None = None,
    system_domains: Iterable[str] | None = None,
    grading: Any | None = None,
    frontier_ai_status: str | None = None,
    statistical_plan: dict[str, Any] | None = None,
) -> StatuteComparison:
    """Run ``check_conformance`` twice and compare only the reports it produced.

    ``system_changed`` is caller-supplied because reasonsmith cannot inspect whether two arbitrary
    Python systems represent the same deployment. Supplying ``after_sut`` identifies a separate
    system; otherwise a changed report with unchanged source and pack is labelled
    ``evidence-change``. Neither is attributed to the statute.
    """
    right_sut = after_sut if after_sut is not None else sut
    before_report = check_conformance(
        sut,
        before.pack,
        system_name,
        system_scope,
        system_domains,
        grading,
        frontier_ai_status=frontier_ai_status,
        statistical_plan=statistical_plan,
    )
    after_report = check_conformance(
        right_sut,
        after.pack,
        system_name,
        system_scope,
        system_domains,
        grading,
        frontier_ai_status=frontier_ai_status,
        statistical_plan=statistical_plan,
    )
    left_results, right_results = _result_map(before_report), _result_map(after_report)
    left_reqs, right_reqs = (
        {r.id: r for r in before.pack.requirements},
        {r.id: r for r in after.pack.requirements},
    )
    duties: list[DutyComparison] = []
    for req_id in sorted(set(left_reqs) | set(right_reqs)):
        left_req, right_req = left_reqs.get(req_id), right_reqs.get(req_id)
        left, right = left_results.get(req_id), right_results.get(req_id)
        if left_req is None:
            duties.append(
                DutyComparison(
                    req_id,
                    "added",
                    None,
                    right.to_dict() if right else None,
                    (),
                    "not-attributable",
                    True,
                    True,
                    None,
                    after.quote_status(right_req) if right_req else None,
                )
            )
            continue
        if right_req is None:
            duties.append(
                DutyComparison(
                    req_id,
                    "removed",
                    left.to_dict() if left else None,
                    None,
                    (),
                    "not-attributable",
                    True,
                    True,
                    before.quote_status(left_req),
                    None,
                )
            )
            continue
        left_dict, right_dict = left.to_dict(), right.to_dict()
        # The quoted source text is provenance carried on a result, not the answer to the
        # duty. A wording-only revision therefore does not masquerade as a verdict flip.
        fields = tuple(
            sorted(
                k
                for k in set(left_dict) | set(right_dict)
                if k not in {"verbatim_text", "source_clause"}
                and left_dict.get(k) != right_dict.get(k)
            )
        )
        source_before = before.safe_passage(left_req)
        source_after = after.safe_passage(right_req)
        source_changed = source_before != source_after
        pack_changed = _pack_changed(left_req, right_req)
        result_changed = bool(fields)
        if not result_changed:
            attribution: Attribution = "none"
            status: ChangeStatus = "unchanged"
        elif source_changed and pack_changed:
            pack_fields = _pack_change_fields(left_req, right_req)
            # A quote-only pack update mirrors the changed source passage. If the formal
            # property also changed, this comparison cannot honestly separate the two causes.
            if pack_fields == ("verbatim_text",):
                attribution = "statutory-change"
            else:
                attribution = "statutory-and-pack-change"
            status = "changed"
        elif pack_changed:
            attribution, status = "pack-change", "changed"
        else:
            if system_changed or after_sut is not None:
                attribution = "system-change"
            elif not source_changed:
                attribution = "evidence-change"
            else:
                attribution = "not-attributable"
            status = "changed"
        duties.append(
            DutyComparison(
                req_id,
                status,
                left_dict,
                right_dict,
                fields,
                attribution,
                source_changed,
                pack_changed,
                before.quote_status(left_req),
                after.quote_status(right_req),
            )
        )
    return StatuteComparison(before, after, before_report, after_report, tuple(duties))


def write_manifest(
    path: str | Path,
    revision: StatuteRevision,
    *,
    pack_path: str | Path,
    source_paths: dict[str, str | Path],
) -> None:
    """Write a deterministic manifest after hashing the supplied snapshot files."""
    target = Path(path)
    root = target.parent
    pack_file = Path(pack_path)
    pack_rel = str(pack_file.relative_to(root))
    entries = []
    for source in revision.sources:
        source_file = Path(source_paths[source.key])
        entries.append(source.to_manifest_entry(str(source_file.relative_to(root))))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "revision": revision.revision,
        "pack": {"path": pack_rel, "sha256": _sha256(pack_file.read_bytes())},
        "sources": entries,
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare conformance reports for two statute revisions"
    )
    parser.add_argument("before", type=Path, help="before revision manifest")
    parser.add_argument("after", type=Path, help="after revision manifest")
    parser.add_argument(
        "--system-module", required=True, help="module:attribute naming a SystemUnderTest"
    )
    parser.add_argument("--json", action="store_true", help="write the comparison as JSON")
    args = parser.parse_args(argv)
    from reasonsmith.cli import load_system_module

    sut = load_system_module(args.system_module)
    comparison = compare_revisions(
        StatuteRevision.from_manifest(args.before), StatuteRevision.from_manifest(args.after), sut
    )
    print(json.dumps(comparison.to_dict(), indent=2) if args.json else comparison.render_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
