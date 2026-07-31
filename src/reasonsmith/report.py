"""Conformance report skeleton and unattainable analysis for reasonsmith v0.2.

A ConformanceReport carries per-requirement verdict, strength, source clause, signals used,
missing signals (if unattainable), and a headline summary line.

Two properties this module exists to protect, both inherited from v0.1:

* **No result claims a strength it did not earn.** `strength` is the tier of evidence that
  actually backs the verdict, and it is `None` when no evidence was gathered at all — because
  no engine in this build covers the requirement's formalism, or because the decision trace
  was empty. A requirement that was never evaluated is reported as never evaluated; it is
  never quietly counted as satisfied, and it is never dropped from the report.
* **The unattainable analysis never runs the system.** It is a set difference over declared
  capabilities, so it is answerable before a single decision is read.

Every emitted report carries explicit limits on its scope and guarantees.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from reasonsmith.spec import Pack, Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

LIMITS = (
    "This report is not a compliance guarantee and is not legal advice. It assesses system "
    "capability declarations and trace evidence against formal specifications. Whether these "
    "findings discharge legal duties remains a determination this tool does not make and cannot "
    "make. A requirement reported without a strength was not evaluated, and no verdict on it "
    "should be read from this report."
)

#: Formalisms this build can actually evaluate. `temporal` and `logical` requirements need the
#: monitor and solver engines, which are not part of this stage; until they land, such
#: requirements are reported as not evaluated rather than judged by a weaker check that would
#: not establish the property.
SUPPORTED_FORMALISMS = ("record",)


def _is_present(value: Any) -> bool:
    """True when a trace value carries something, not merely a key.

    A missing key, None, a blank string and an empty list/dict/set all mean the system
    emitted nothing for that signal. Only the first of those is caught by a key check,
    and only the first two by a truthiness check on `str(value)` — `str([])` is `"[]"`,
    which is why an empty reason list would otherwise pass as a reason given.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


@dataclass(frozen=True)
class RequirementResult:
    """The conformance result for a single requirement.

    `strength` is `None` when the requirement was not evaluated at all; see the module
    docstring. `signals_missing` names the required signals the system does not declare,
    and is therefore populated only on an unattainable result — signals that are declared
    but absent from a particular trace are a different finding and land in `details`.
    """

    requirement_id: str
    source_clause: str
    verdict: Verdict
    strength: Strength | None
    signals_required: tuple[str, ...]
    signals_missing: tuple[str, ...] = ()
    evidence_summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unattainable = self.strength == Strength.UNATTAINABLE
        if unattainable and self.verdict != Verdict.INCONCLUSIVE:
            raise ValueError(
                f"{self.requirement_id}: an unattainable requirement cannot be reported "
                f"{self.verdict}; the system cannot discharge it as built"
            )
        if bool(self.signals_missing) != unattainable:
            raise ValueError(
                f"{self.requirement_id}: signals_missing is populated exactly when the result "
                f"is unattainable (strength={self.strength}, missing={self.signals_missing})"
            )
        if self.strength is None and self.verdict != Verdict.INCONCLUSIVE:
            raise ValueError(
                f"{self.requirement_id}: a result with no evidence strength cannot be reported "
                f"{self.verdict}"
            )
        unknown = set(self.signals_missing) - set(self.signals_required)
        if unknown:
            raise ValueError(
                f"{self.requirement_id}: signals_missing names signals the requirement does not "
                f"require: {sorted(unknown)}"
            )

    @property
    def evaluated(self) -> bool:
        """False when no evidence of any strength was gathered for this requirement."""
        return self.strength is not None

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "source_clause": self.source_clause,
            "verdict": self.verdict.value,
            "strength": self.strength.value if self.strength else None,
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
    def counts(self) -> dict[str, int]:
        """Per-category counts. Every result falls in exactly one category after `total`.

        `proved`/`probed`/`observed` count *satisfied* requirements at that strength, so a
        requirement is never counted as evidence for a property it does not have.
        """

        def satisfied_at(strength: Strength) -> int:
            return sum(
                1
                for r in self.results
                if r.verdict == Verdict.SATISFIED and r.strength == strength
            )

        return {
            "total": len(self.results),
            "proved": satisfied_at(Strength.PROVED),
            "probed": satisfied_at(Strength.PROBED),
            "observed": satisfied_at(Strength.OBSERVED),
            "violated": sum(1 for r in self.results if r.verdict == Verdict.VIOLATED),
            "inconclusive": sum(
                1
                for r in self.results
                if r.verdict == Verdict.INCONCLUSIVE
                and r.evaluated
                and r.strength != Strength.UNATTAINABLE
            ),
            "not_evaluated": sum(1 for r in self.results if not r.evaluated),
            "unattainable": sum(1 for r in self.results if r.strength == Strength.UNATTAINABLE),
        }

    @property
    def headline(self) -> str:
        """Headline count line (e.g. '6 requirements · 4 observed · 2 unattainable')."""
        counts = self.counts
        parts = [f"{counts['total']} requirements"]
        parts += [
            f"{counts[key]} {label}"
            for key, label in (
                ("proved", "proved"),
                ("probed", "probed"),
                ("observed", "observed"),
                ("violated", "violated"),
                ("inconclusive", "inconclusive"),
                ("not_evaluated", "not evaluated"),
                ("unattainable", "unattainable"),
            )
            if counts[key]
        ]
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
            tier = r.strength.value.upper() if r.strength else "NOT EVALUATED"
            lines.append(f"  [{tier}] {r.requirement_id} ({r.source_clause}): {r.verdict.value}")
            lines.append(f"    requires: {', '.join(r.signals_required)}")
            if r.signals_missing:
                lines.append(f"    MISSING SIGNALS: {', '.join(r.signals_missing)}")
            absent = r.details.get("signals_absent_from_trace")
            if absent:
                lines.append(f"    ABSENT FROM TRACE: {', '.join(absent)}")
            if r.evidence_summary:
                lines.append(f"    summary: {r.evidence_summary}")
        lines.extend(["", "LIMITS OF THIS REPORT", f"  {self.limits}"])
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "pack_id": self.pack_id,
            "headline": self.headline,
            "counts": self.counts,
            "results": [r.to_dict() for r in self.results],
            "limits": self.limits,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON representation following house pattern."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def analyze_unattainable(req: Requirement, sut: SystemUnderTest) -> tuple[bool, tuple[str, ...]]:
    """Perform the unattainable analysis for a requirement against a SUT.

    COMPUTED WITHOUT EXECUTING THE SYSTEM (sut.decisions is never called): the answer is the
    set difference between the signals the requirement needs and the signals the system
    declares it can emit. Capabilities are what the system *declares*, never what a trace
    happens to contain, so a shortfall is a statement about the system as built rather than
    about the run you happen to have.

    Returns:
        (is_unattainable, missing_signals) — missing_signals is sorted and never empty when
        is_unattainable is True.
    """
    declared = sut.capabilities()
    # A bare string is iterable, so set("reasons") reads every character as a declared signal.
    # Anything else iterable is a collection of names; matching BaseSUT.__init__ keeps a
    # third-party system free to return dict_keys or a generator expression.
    if isinstance(declared, (str, bytes)) or not isinstance(declared, Iterable):
        raise TypeError(
            f"{type(sut).__name__}.capabilities() must return a collection of signal names, "
            f"got {type(declared).__name__}"
        )
    missing = tuple(sorted(set(req.requires) - set(declared)))
    return bool(missing), missing


def _unattainable_result(req: Requirement, missing: tuple[str, ...]) -> RequirementResult:
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=Strength.UNATTAINABLE,
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=(
            "Unattainable as built: the system declares no capability to emit "
            f"{', '.join(missing)}, so no amount of testing can discharge this requirement. "
            "Determined from declared capabilities alone; the system was not executed."
        ),
    )


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
) -> RequirementResult:
    """Evaluate a single requirement against a SUT.

    If declared capabilities do not cover the required signals, returns UNATTAINABLE without
    executing the SUT. Otherwise `records` is used as the decision trace; when it is None the
    trace is fetched from the SUT, so callers holding a trace already can avoid re-running the
    system once per requirement.
    """
    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return _unattainable_result(req, missing)

    clause = f"{req.source_document} {req.article_clause}"

    if req.formalism not in SUPPORTED_FORMALISMS:
        # Declaring the signals is not evidence that a temporal or logical property holds,
        # and there is no monitor or solver in this build to establish one. Say so.
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Not evaluated: no engine in this build checks a {req.formalism!r} requirement. "
                "The system declares the signals this requirement needs, so it is attainable, "
                "but nothing here establishes that the property holds."
            ),
        )

    if records is None:
        records = list(sut.decisions())

    if not records:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=(
                "Not evaluated: the decision trace is empty, so nothing was observed. "
                "An empty trace is not evidence that the requirement holds."
            ),
        )

    absent = sorted(
        {
            signal
            for rec in records
            for signal in req.requires
            if not _is_present(rec.get(signal))
        }
    )

    if absent:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.VIOLATED,
            strength=Strength.OBSERVED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Violated over {len(records)} observed decision(s): the system declares it can "
                f"emit these signals, but records carry no value for {', '.join(absent)}."
            ),
            details={
                "signals_absent_from_trace": absent,
                "records_observed": len(records),
            },
        )

    return RequirementResult(
        requirement_id=req.id,
        source_clause=clause,
        verdict=Verdict.SATISFIED,
        strength=Strength.OBSERVED,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Observed over {len(records)} decision(s): every required signal "
            f"({', '.join(req.requires)}) carries a value in every record. Holds on the trace "
            "supplied; nothing here extends the claim to decisions not in it."
        ),
        details={"records_observed": len(records)},
    )


def check_conformance(
    sut: SystemUnderTest, pack: Pack, system_name: str = "SUT"
) -> ConformanceReport:
    """Check conformance of a SUT against all requirements in a Pack.

    Unattainability is resolved for every requirement first, and the decision trace is read at
    most once — and not at all when nothing in the pack is both attainable and checkable here.
    That keeps "the unattainable analysis does not run the system" a property of the code
    rather than of the order the requirements happen to appear in.
    """
    verdicts = [(req, *analyze_unattainable(req, sut)) for req in pack.requirements]

    needs_trace = any(
        not is_unattainable and req.formalism in SUPPORTED_FORMALISMS
        for req, is_unattainable, _ in verdicts
    )
    # When nothing needs the trace this stays empty and is never read: the only requirements
    # left are unattainable or of a formalism no engine here checks.
    records = list(sut.decisions()) if needs_trace else []

    results = [
        _unattainable_result(req, missing)
        if is_unattainable
        else evaluate_requirement(req, sut, records)
        for req, is_unattainable, missing in verdicts
    ]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        results=tuple(results),
    )
