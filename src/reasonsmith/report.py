"""Conformance report skeleton and unattainable analysis for reasonsmith v0.2.

A ConformanceReport carries per-requirement verdict, strength, source clause, signals used,
missing signals (if unattainable), and a headline summary line.

Every emitted report carries explicit limits on its scope and guarantees.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from reasonsmith.spec import Pack, Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

LIMITS = (
    "This report is not a compliance guarantee and is not legal advice. It assesses system capability "
    "declarations and trace evidence against formal specifications. Whether these findings discharge legal "
    "duties remains a determination this tool does not make and cannot make."
)


@dataclass(frozen=True)
class RequirementResult:
    """The conformance result for a single requirement."""

    requirement_id: str
    source_clause: str
    verdict: Verdict
    strength: Strength
    signals_required: tuple[str, ...]
    signals_missing: tuple[str, ...] = ()
    evidence_summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "source_clause": self.source_clause,
            "verdict": self.verdict.value,
            "strength": self.strength.value,
            "signals_required": list(self.signals_required),
            "signals_missing": list(self.signals_missing),
            "evidence_summary": self.evidence_summary,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ConformanceReport:
    """Report summarizing conformance of a System Under Test against a Pack."""

    pack_id: str
    system_name: str
    results: tuple[RequirementResult, ...]
    limits: str = LIMITS

    @property
    def headline(self) -> str:
        """Headline count line summary (e.g. '6 requirements · 4 observed · 2 unattainable')."""
        total = len(self.results)
        proved = sum(
            1 for r in self.results if r.verdict == Verdict.SATISFIED and r.strength == Strength.PROVED
        )
        probed = sum(
            1 for r in self.results if r.verdict == Verdict.SATISFIED and r.strength == Strength.PROBED
        )
        observed = sum(
            1 for r in self.results if r.verdict == Verdict.SATISFIED and r.strength == Strength.OBSERVED
        )
        violated = sum(1 for r in self.results if r.verdict == Verdict.VIOLATED)
        unattainable = sum(1 for r in self.results if r.strength == Strength.UNATTAINABLE)
        inconclusive = sum(
            1
            for r in self.results
            if r.verdict == Verdict.INCONCLUSIVE and r.strength != Strength.UNATTAINABLE
        )

        parts = [f"{total} requirements"]
        if proved:
            parts.append(f"{proved} proved")
        if probed:
            parts.append(f"{probed} probed")
        if observed:
            parts.append(f"{observed} observed")
        if violated:
            parts.append(f"{violated} violated")
        if inconclusive:
            parts.append(f"{inconclusive} inconclusive")
        if unattainable:
            parts.append(f"{unattainable} unattainable")

        return " · ".join(parts)

    def render_text(self) -> str:
        """Readable text rendering of the report."""
        lines = [
            "CONFORMANCE REPORT",
            f"system: {self.system_name}",
            f"pack: {self.pack_id}",
            f"headline: {self.headline}",
            "",
            "REQUIREMENT FINDINGS:",
        ]
        for r in self.results:
            lines.append(
                f"  [{r.strength.value.upper()}] {r.requirement_id} ({r.source_clause}): {r.verdict.value}"
            )
            lines.append(f"    requires: {', '.join(r.signals_required)}")
            if r.signals_missing:
                lines.append(f"    MISSING SIGNALS: {', '.join(r.signals_missing)}")
            if r.evidence_summary:
                lines.append(f"    summary: {r.evidence_summary}")
        lines.extend(["", "LIMITS OF THIS REPORT", f"  {self.limits}"])
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "pack_id": self.pack_id,
            "headline": self.headline,
            "counts": {
                "total": len(self.results),
                "proved": sum(
                    1
                    for r in self.results
                    if r.verdict == Verdict.SATISFIED and r.strength == Strength.PROVED
                ),
                "probed": sum(
                    1
                    for r in self.results
                    if r.verdict == Verdict.SATISFIED and r.strength == Strength.PROBED
                ),
                "observed": sum(
                    1
                    for r in self.results
                    if r.verdict == Verdict.SATISFIED and r.strength == Strength.OBSERVED
                ),
                "violated": sum(1 for r in self.results if r.verdict == Verdict.VIOLATED),
                "unattainable": sum(
                    1 for r in self.results if r.strength == Strength.UNATTAINABLE
                ),
                "inconclusive": sum(
                    1
                    for r in self.results
                    if r.verdict == Verdict.INCONCLUSIVE and r.strength != Strength.UNATTAINABLE
                ),
            },
            "results": [r.to_dict() for r in self.results],
            "limits": self.limits,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON representation following house pattern."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def analyze_unattainable(req: Requirement, sut: SystemUnderTest) -> tuple[bool, tuple[str, ...]]:
    """Perform the unattainable analysis for a requirement against a SUT.

    COMPUTED WITHOUT EXECUTING THE SYSTEM (sut.decisions is never called).

    Returns:
        (is_unattainable, missing_signals)
    """
    declared = sut.capabilities()
    missing = tuple(sorted(set(req.requires) - declared))
    return bool(missing), missing


def evaluate_requirement(req: Requirement, sut: SystemUnderTest) -> RequirementResult:
    """Evaluate a single requirement against a SUT.

    If declared capabilities do not cover the required signals, returns UNATTAINABLE
    without executing the SUT.
    """
    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=f"{req.source_document} {req.article_clause}",
            verdict=Verdict.INCONCLUSIVE,
            strength=Strength.UNATTAINABLE,
            signals_required=tuple(req.requires),
            signals_missing=missing,
            evidence_summary=f"Unattainable: system lacks declared capability for signal(s): {', '.join(missing)}",
        )

    # System has declared capabilities: observe decision trace
    records = list(sut.decisions())
    if not records:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=f"{req.source_document} {req.article_clause}",
            verdict=Verdict.INCONCLUSIVE,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            signals_missing=(),
            evidence_summary="Observed decision trace is empty",
        )

    # Verify each required signal has a non-empty value in decision records
    missing_in_records = set()
    for rec in records:
        for signal in req.requires:
            val = rec.get(signal)
            if val is None or str(val).strip() == "":
                missing_in_records.add(signal)

    if missing_in_records:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=f"{req.source_document} {req.article_clause}",
            verdict=Verdict.VIOLATED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            signals_missing=(),
            evidence_summary=f"Violated: decision trace records missing values for required signal(s): {', '.join(sorted(missing_in_records))}",
        )

    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.SATISFIED,
        strength=Strength.OBSERVED,
        signals_required=tuple(req.requires),
        signals_missing=(),
        evidence_summary=f"Observed over decision trace: all required signals ({', '.join(req.requires)}) present",
    )


def check_conformance(
    sut: SystemUnderTest, pack: Pack, system_name: str = "SUT"
) -> ConformanceReport:
    """Check conformance of a SUT against all requirements in a Pack."""
    results = [evaluate_requirement(req, sut) for req in pack.requirements]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        results=tuple(results),
    )
