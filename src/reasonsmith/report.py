"""Conformance report skeleton and unattainable analysis for reasonsmith v0.2.

A ConformanceReport carries per-requirement verdict, strength, source clause, signals used,
missing signals (if unattainable), and a headline summary line.

Two properties this module exists to protect, both inherited from v0.1:

* **No result claims a strength it did not earn.** `strength` is the tier of evidence that
  actually backs the verdict, and it is `None` when no evidence was gathered at all — because
  no engine in this build covers the requirement's formalism, or because the decision trace
  was empty. A requirement that was never evaluated is reported as never evaluated; it is
  never quietly counted as satisfied, and it is never dropped from the report.
* **The unattainable analysis never runs the system.** It is a set difference over the
  capability set supplied by the SUT adapter. Explicit declarations are answerable before a
  decision is read; a trace-derived adapter labels its weaker basis in the result.

Every emitted report carries explicit limits on its scope and guarantees.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from reasonsmith.spec import Pack, Requirement
from reasonsmith.sut import SystemUnderTest, _validate_capability_collection
from reasonsmith.verdict import Strength, Verdict

LIMITS = (
    "This report is not a compliance guarantee and is not legal advice. It assesses system "
    "capability information and trace evidence against formal specifications. Whether these "
    "findings discharge legal duties remains a determination this tool does not make and cannot "
    "make. A requirement reported without a strength was not evaluated, and no verdict on it "
    "should be read from this report."
)

#: Formalisms this build can actually evaluate. `logical` requirements need the
#: solver engine, which is part of stage 3; until it lands, such
#: requirements are reported as not evaluated rather than judged by a weaker check that would
#: not establish the property.
SUPPORTED_FORMALISMS = ("record", "temporal")


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
    docstring. `signals_missing` names required signals missing from the adapter's capability
    set and is therefore populated only on an unattainable result. Signals in that set but
    absent from a particular trace are a different finding and land in `details`.
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
        # Every invariant below compares against the enum members, so a raw string would
        # match none of them and walk past all of them. Normalise first: the guards are the
        # only thing standing between a caller and a result that claims more than it has.
        object.__setattr__(self, "verdict", Verdict.parse(self.verdict))
        if self.strength is not None:
            object.__setattr__(self, "strength", Strength.parse(self.strength))
        for name in ("signals_required", "signals_missing"):
            object.__setattr__(self, name, self._signal_names(name))

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

    def _signal_names(self, name: str) -> tuple[str, ...]:
        """Coerce a signal field to a tuple of names, refusing shapes that would be misread.

        A bare string is iterable, so signals_required="reasons" would become seven
        single-character signals; a mapping is iterable over its keys, for the same reason
        the capability sites reject one.
        """
        value = getattr(self, name)
        if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
            raise TypeError(
                f"{self.requirement_id}: {name} must be a sequence of signal names, got "
                f"{type(value).__name__}; pass ({value!r},) to name one signal"
            )
        names = tuple(value)
        bad = [s for s in names if not isinstance(s, str) or not s.strip()]
        if bad:
            raise TypeError(
                f"{self.requirement_id}: every entry of {name} must be a non-empty signal "
                f"name, got {bad!r}"
            )
        return names

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

    COMPUTED WITHOUT EXECUTING THE SYSTEM (`sut.decisions()` is never called here): the answer
    is the set difference between the signals the requirement needs and the capability set the
    SUT adapter supplies. Most adapters require an explicit system declaration. A trace-derived
    adapter is weaker: its result is limited to that supplied trace rather than stated as a
    property of the system as built.

    Returns:
        (is_unattainable, missing_signals) — missing_signals is sorted and never empty when
        is_unattainable is True.
    """
    declared = sut.capabilities()
    _validate_capability_collection(declared, f"{type(sut).__name__}.capabilities() must return")
    missing = tuple(sorted(set(req.requires) - set(declared)))
    return bool(missing), missing


def _read_trace(sut: SystemUnderTest) -> list[dict[str, Any]]:
    """Read a SUT's decision trace, refusing a shape that would be read record by record.

    A system returning one record instead of a list of records yields its key strings, which
    would otherwise blow up deep inside the signal check with no mention of the system that
    caused it. Shared by both places a trace is read, so neither can drift from the other.
    """
    records = list(sut.decisions())
    for rec in records:
        if not isinstance(rec, Mapping):
            raise TypeError(
                f"{type(sut).__name__}.decisions() must return an iterable of decision records, "
                f"each a mapping of signal name to value; got {type(rec).__name__}"
            )
    return records


def _unattainable_result(
    req: Requirement, missing: tuple[str, ...], sut: SystemUnderTest | None = None
) -> RequirementResult:
    """The unattainable result, worded for how the capability set was established.

    A system that declares its capabilities is speaking about itself as built. An adapter
    that infers them from a supplied trace is not: a longer trace could carry the signal, so
    the result says what it was read from rather than putting a claim in the system's mouth.
    """
    if getattr(sut, "capability_basis", "declared") == "trace":
        summary = (
            "Unattainable on the evidence supplied: no record in the supplied decision trace "
            f"carries a value for {', '.join(missing)}, and the system declared no "
            "capabilities, so nothing here can discharge this requirement. Read from that "
            "trace alone; a longer trace could show the system emitting these signals."
        )
    else:
        summary = (
            "Unattainable as built: the system declares no capability to emit "
            f"{', '.join(missing)}, so no amount of testing can discharge this requirement. "
            "Determined from declared capabilities alone; the system was not executed."
        )
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=Strength.UNATTAINABLE,
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=summary,
    )


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
) -> RequirementResult:
    """Evaluate a single requirement against a SUT.

    If the adapter's capability set does not cover the required signals, returns UNATTAINABLE
    without executing the SUT. Otherwise `records` is used as the decision trace; when it is
    None the trace is fetched from the SUT, so callers holding a trace already can avoid
    re-running the system once per requirement.
    """
    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return _unattainable_result(req, missing, sut)

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
        records = _read_trace(sut)

    if req.formalism == "record":
        from reasonsmith.engines.record import RecordEngine
        return RecordEngine.evaluate(req, sut, records)
    elif req.formalism == "temporal":
        from reasonsmith.engines.observed import ObservedEngine
        return ObservedEngine.evaluate(req, sut, records)

    return RequirementResult(
        requirement_id=req.id,
        source_clause=clause,
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Not evaluated: no engine in this build checks a {req.formalism!r} requirement."
        ),
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
    records = _read_trace(sut) if needs_trace else []

    # `records` is a list by now, so evaluate_requirement never re-reads the trace; it
    # re-derives the unattainable result itself, which is why there is no branch here.
    results = [evaluate_requirement(req, sut, records) for req, _, _ in verdicts]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        results=tuple(results),
    )
