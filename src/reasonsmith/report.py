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
    "make. A requirement reported without a strength was not evaluated or is not applicable, "
    "and no verdict on it should be read from this report. "
    "Recital and guidance items inform how statutory duties are interpreted but cannot create "
    "an obligation on its own; interpretive requirements are evaluated for completeness and "
    "excluded from binding headline counts."
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

    `strength` is `None` when the requirement was not evaluated at all or is not applicable;
    see the module docstring. `signals_missing` names required signals missing from the adapter's capability
    set and is therefore populated only on an unattainable result. Signals in that set but
    absent from a particular trace are a different finding and land in `details`.
    `binding` records whether the duty is legally binding (true) or an interpretive recital/guidance (false).
    `scope` records any regulatory class limit (e.g. 'high-risk').
    """

    requirement_id: str
    source_clause: str
    verdict: Verdict
    strength: Strength | None
    signals_required: tuple[str, ...]
    signals_missing: tuple[str, ...] = ()
    evidence_summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    binding: bool = True
    scope: str = ""

    def __post_init__(self) -> None:
        # Every invariant below compares against the enum members, so a raw string would
        # match none of them and walk past all of them. Normalise first: the guards are the
        # only thing standing between a caller and a result that claims more than it has.
        object.__setattr__(self, "verdict", Verdict.parse(self.verdict))
        if self.strength is not None:
            object.__setattr__(self, "strength", Strength.parse(self.strength))
        object.__setattr__(self, "binding", bool(self.binding))
        object.__setattr__(self, "scope", str(self.scope))
        for name in ("signals_required", "signals_missing"):
            object.__setattr__(self, name, self._signal_names(name))

        if self.verdict == Verdict.NOT_APPLICABLE:
            if self.strength is not None:
                raise ValueError(
                    f"{self.requirement_id}: a not_applicable requirement cannot carry evidence strength {self.strength}"
                )
            if bool(self.signals_missing):
                raise ValueError(
                    f"{self.requirement_id}: a not_applicable requirement cannot have missing signals"
                )

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
        if self.strength is None and self.verdict not in (Verdict.INCONCLUSIVE, Verdict.NOT_APPLICABLE):
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
        """Coerce a signal field to a tuple of names, refusing shapes that would be misread."""
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
            "binding": self.binding,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class ConformanceReport:
    """Report summarizing conformance of a System Under Test against a Pack."""

    pack_id: str
    system_name: str
    results: tuple[RequirementResult, ...]
    system_scope: str | None = None
    limits: str = LIMITS

    @property
    def counts(self) -> dict[str, int]:
        """Per-category counts for binding requirements and summary counts for interpretive items.

        Interpretive requirements are evaluated and reported, but excluded from binding counts.
        """
        binding_res = [r for r in self.results if r.binding]
        interp_res = [r for r in self.results if not r.binding]

        def satisfied_at(res_list: list[RequirementResult], strength: Strength) -> int:
            return sum(
                1 for r in res_list if r.verdict == Verdict.SATISFIED and r.strength == strength
            )

        res = {
            "total": len(binding_res),
            "proved": satisfied_at(binding_res, Strength.PROVED),
            "probed": satisfied_at(binding_res, Strength.PROBED),
            "observed": satisfied_at(binding_res, Strength.OBSERVED),
            "violated": sum(1 for r in binding_res if r.verdict == Verdict.VIOLATED),
            "inconclusive": sum(
                1
                for r in binding_res
                if r.verdict == Verdict.INCONCLUSIVE
                and r.evaluated
                and r.strength != Strength.UNATTAINABLE
            ),
            "not_evaluated": sum(
                1 for r in binding_res if not r.evaluated and r.verdict != Verdict.NOT_APPLICABLE
            ),
            "unattainable": sum(1 for r in binding_res if r.strength == Strength.UNATTAINABLE),
            "not_applicable": sum(1 for r in binding_res if r.verdict == Verdict.NOT_APPLICABLE),
            "interpretive_total": len(interp_res),
            "interpretive_satisfied": sum(1 for r in interp_res if r.verdict == Verdict.SATISFIED),
            "interpretive_violated": sum(1 for r in interp_res if r.verdict == Verdict.VIOLATED),
            "interpretive_inconclusive": sum(
                1
                for r in interp_res
                if r.verdict == Verdict.INCONCLUSIVE
                and r.evaluated
                and r.strength != Strength.UNATTAINABLE
            ),
            "interpretive_not_evaluated": sum(
                1 for r in interp_res if not r.evaluated and r.verdict != Verdict.NOT_APPLICABLE
            ),
            "interpretive_unattainable": sum(
                1 for r in interp_res if r.strength == Strength.UNATTAINABLE
            ),
            "interpretive_not_applicable": sum(
                1 for r in interp_res if r.verdict == Verdict.NOT_APPLICABLE
            ),
        }
        return res

    @property
    def headline(self) -> str:
        """Headline count line distinguishing binding duties from interpretive recitals/guidance."""
        counts = self.counts
        has_binding = counts["total"] > 0
        has_interp = counts["interpretive_total"] > 0

        parts = []
        if has_binding or not has_interp:
            lbl = "binding requirements" if has_interp else "requirements"
            parts.append(f"{counts['total']} {lbl}")
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
                    ("not_applicable", "not applicable"),
                )
                if counts[key]
            ]
        
        if has_interp:
            interp_sub = [
                f"{counts[key]} {label}"
                for key, label in (
                    ("interpretive_satisfied", "satisfied"),
                    ("interpretive_violated", "violated"),
                    ("interpretive_inconclusive", "inconclusive"),
                    ("interpretive_not_evaluated", "not evaluated"),
                    ("interpretive_unattainable", "unattainable"),
                    ("interpretive_not_applicable", "not applicable"),
                )
                if counts[key]
            ]
            interp_str = f": {', '.join(interp_sub)}" if interp_sub else ""
            parts.append(f"+ {counts['interpretive_total']} interpretive{interp_str}")

        return " · ".join(parts)

    def render_text(self) -> str:
        """Readable text rendering of the report."""
        lines = [
            "CONFORMANCE REPORT",
            f"system: {self.system_name}",
            f"declared scope: {self.system_scope or 'undeclared'}",
            f"pack: {self.pack_id}",
            f"headline: {self.headline}",
            "",
            "REQUIREMENT FINDINGS:",
        ]
        for r in self.results:
            if r.verdict == Verdict.NOT_APPLICABLE:
                tier = "NOT APPLICABLE"
            else:
                tier = r.strength.value.upper() if r.strength else "NOT EVALUATED"
            interp_tag = " [INTERPRETIVE]" if not r.binding else ""
            lines.append(
                f"  [{tier}]{interp_tag} {r.requirement_id} ({r.source_clause}): {r.verdict.value}"
            )
            lines.append(f"    requires: {', '.join(r.signals_required)}")
            if r.scope:
                lines.append(f"    scope limit: {r.scope}")
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
            "system_scope": self.system_scope,
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
    """Perform the unattainable analysis for a requirement against a SUT."""
    declared = sut.capabilities()
    _validate_capability_collection(declared, f"{type(sut).__name__}.capabilities() must return")
    missing = tuple(sorted(set(req.requires) - set(declared)))
    return bool(missing), missing


def _read_trace(sut: SystemUnderTest) -> list[dict[str, Any]]:
    """Read a SUT's decision trace, refusing a shape that would be read record by record."""
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
    """The unattainable result, worded for how the capability set was established."""
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
        binding=req.binding,
        scope=req.scope,
    )


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
    system_scope: str | None = None,
) -> RequirementResult:
    """Evaluate a single requirement against a SUT."""
    if system_scope is None:
        system_scope = getattr(sut, "system_scope", getattr(sut, "declared_scope", None))

    if req.scope:
        req_scope_norm = req.scope.strip().lower().replace("-", "_")
        sys_scope_norm = (
            system_scope.strip().lower().replace("-", "_")
            if system_scope and isinstance(system_scope, str)
            else ""
        )
        if not sys_scope_norm or sys_scope_norm != req_scope_norm:
            clause = f"{req.source_document} {req.article_clause}"
            desc = f"declared as {system_scope!r}" if system_scope else "undeclared"
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.NOT_APPLICABLE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not applicable: requirement scope is {req.scope!r}, but system regulatory "
                    f"class is {desc}. reasonsmith never infers a system's regulatory class."
                ),
                binding=req.binding,
                scope=req.scope,
            )

    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return _unattainable_result(req, missing, sut)

    clause = f"{req.source_document} {req.article_clause}"

    if req.formalism not in SUPPORTED_FORMALISMS:
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
            binding=req.binding,
            scope=req.scope,
        )

    if records is None:
        records = _read_trace(sut)

    if req.formalism == "record":
        from reasonsmith.engines.record import RecordEngine
        return RecordEngine.evaluate(req, sut, records)
    elif req.formalism == "temporal":
        from reasonsmith.engines.observed import ObservedEngine
        return ObservedEngine.evaluate(req, sut, records)

    raise NotImplementedError(
        f"{req.formalism!r} is listed in SUPPORTED_FORMALISMS but no engine here evaluates it. "
        "Widen SUPPORTED_FORMALISMS when the engine lands, not before."
    )


def check_conformance(
    sut: SystemUnderTest,
    pack: Pack,
    system_name: str = "SUT",
    system_scope: str | None = None,
) -> ConformanceReport:
    """Check conformance of a SUT against all requirements in a Pack."""
    if system_scope is None:
        system_scope = getattr(sut, "system_scope", getattr(sut, "declared_scope", None))

    eval_plan = []
    for req in pack.requirements:
        req_norm = req.scope.strip().lower().replace("-", "_") if req.scope else ""
        sys_norm = (
            system_scope.strip().lower().replace("-", "_")
            if system_scope and isinstance(system_scope, str)
            else ""
        )
        applicable = not req_norm or (bool(sys_norm) and sys_norm == req_norm)
        if not applicable:
            eval_plan.append((req, False, ()))
        else:
            eval_plan.append((req, *analyze_unattainable(req, sut)))

    needs_trace = any(
        (not req.scope or (bool(system_scope) and system_scope.strip().lower().replace("-", "_") == req.scope.strip().lower().replace("-", "_")))
        and not is_unattainable
        and req.formalism in SUPPORTED_FORMALISMS
        for req, is_unattainable, _ in eval_plan
    )

    records = _read_trace(sut) if needs_trace else []

    results = [
        evaluate_requirement(req, sut, records, system_scope=system_scope)
        for req in pack.requirements
    ]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        system_scope=system_scope,
        results=tuple(results),
    )
