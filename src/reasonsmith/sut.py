"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.2.

What this module is for:
  Defines the `SystemUnderTest` protocol interface (`capabilities()`, `decisions()`) and
  `CAPABILITY_TAXONOMY` categories for black-box models, rule engines, and log traces.

What a reader must not break:
  - BaseSUT requires explicit capability declarations; an adapter that instead derives them from a
    trace must say so by setting the plain instance attribute `capability_basis = "trace"`. It is
    not part of the protocol above: `report._unattainable_result` reads it with
    `getattr(sut, "capability_basis", "declared")`, so an adapter that sets nothing is worded as
    declaring its capabilities. Those two literals are the whole vocabulary — any other value, or a
    method of that name instead of an attribute, silently reads as `"declared"`.
    Why this matters: Trace-derived capabilities come from observing sample traces, whereas
    explicit declarations represent an authoritative system claim. A trace-reading adapter that
    misses the attribute has its finding worded "Unattainable as built ... the system was not
    executed" — a claim about the system, made from one sample trace.
  - A capability set is the enabled signal names and nothing else: `_validate_capability_collection`
    rejects a bare string, a mapping, a non-iterable, and any blank or non-string name, at both
    sites capabilities cross into reasonsmith.
    Why this matters: `set("reasons")` would declare seven single-character capabilities, and a
    capability map would declare the signals it marks False as available — the overclaim this tool
    exists to prevent.
  - `CAPABILITY_TAXONOMY` documents the four Section 6.3 categories that signal names are
    conventionally prefixed with (`provenance_`, `artifact_logs_`, ...). It is a reference for pack
    and adapter authors, not a validator: nothing here checks a name against it, and a pack is free
    to name a signal outside it.
    Why this matters: Reading it as enforced would hide that an out-of-taxonomy signal name passes
    unremarked and simply reports the requirement unattainable when no adapter supplies it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Optional, Protocol, runtime_checkable

from reasonsmith.spec import load_pack

#: Section 6.3 top-level taxonomy for capability signals supplied through the SUT protocol
#: (Stan, Sciavicco & Napoletano, JAIR 2026, Section 6.3, p. 36:24):
#:   - provenance: KB version, constraint set, active exceptions at inference time
#:   - artifact_logs: extracted rules/trees, constraint-satisfaction traces, proof/plan/KG traces
#:   - stability_signals: artifact drift over time, perturbation sensitivity, change
#:     after model updates
#:   - scope_statements: local vs global scope, approximation vs guarantee statements
CAPABILITY_TAXONOMY = (
    "provenance",
    "artifact_logs",
    "stability_signals",
    "scope_statements",
)


def _validate_capability_collection(declared: Any, subject: str) -> None:
    """Refuse anything that is not a plain collection of enabled signal names.

    Shared by the two places capabilities cross into reasonsmith — BaseSUT.__init__ and the
    unattainable analysis — because a malformed capability set would judge a system against
    signals its adapter never supplied, in either direction.

    A bare string is iterable, so set("reasons") would declare seven single-character
    capabilities. A mapping is iterable over its keys, so a capability map would declare the
    signals it marks False as available — the overclaim this tool exists to prevent.
    """
    if isinstance(declared, (str, bytes)):
        raise TypeError(
            f"{subject} a collection of signal names, not a single string; "
            f"pass {{{declared!r}}} to declare one signal"
        )
    if isinstance(declared, Mapping):
        raise TypeError(
            f"{subject} the enabled signal names, not a capability map; got "
            f"{type(declared).__name__}, whose False-valued entries would be read as declared. "
            "Pass the enabled names alone, e.g. {name for name, on in capabilities.items() if on}"
        )
    if not isinstance(declared, Iterable):
        raise TypeError(
            f"{subject} a collection of signal names, got {type(declared).__name__}"
        )


@runtime_checkable
class SystemUnderTest(Protocol):
    """Protocol for a system under test in reasonsmith."""

    def capabilities(self) -> set[str]:
        """Return the signal names this adapter supplies for unattainability analysis."""
        ...

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return an iterable of decision trace records."""
        ...


class BaseSUT:
    """Convenience base class or reference helper for SUT implementations."""

    def __init__(self, declared_capabilities: set[str] | Iterable[str]):
        _validate_capability_collection(declared_capabilities, "declared_capabilities must be")
        self._capabilities = set(declared_capabilities)
        for signal in self._capabilities:
            if not isinstance(signal, str) or not signal.strip():
                raise ValueError(
                    f"Declared capability must be a non-empty signal name, got {signal!r}"
                )

    def capabilities(self) -> set[str]:
        return set(self._capabilities)

    def decisions(self) -> Iterable[dict[str, Any]]:
        return []


def _table7_signals() -> set[str]:
    """Every signal the shipped Table 7 pack asks for, read from the pack itself.

    Read rather than restated: a hand-copied list would drift the moment the pack
    changes, and a reference system that declares stale signal names would make the
    unattainable analysis look wrong when it is right.
    """
    return {signal for req in load_pack("table7").requirements for signal in req.requires}


#: The Table 7 evidence fields that carry a per-decision reason. Row 3 (GDPR Art. 22)
#: and row 4 (ECOA / Reg B) name these separately, and the pack keeps the paper's own
#: keys, so a system that gives no reasons is missing both.
REASON_SIGNALS = frozenset({"per_decision_reason_string", "stored_reasons_per_decision"})


def _record_from(capabilities: set[str]) -> dict[str, Any]:
    """One decision record carrying a value for every capability the system declares.

    Derived from the declared capabilities rather than from a hand-written key list, so a
    reference system emits exactly what it says it can emit and cannot drift from the pack.
    """
    record: dict[str, Any] = {
        "decision": "approved",
        "timestamp": "2026-07-31T09:00:00Z",
    }
    for signal in sorted(capabilities - set(record)):
        record[signal] = f"{signal}_value"
    return record


class FullCapabilitySUT(BaseSUT):
    """Reference SUT declaring every signal the Table 7 pack requires."""

    def __init__(
        self, extra_capabilities: Optional[set[str]] = None, system_scope: str = "high-risk"
    ):
        declared = _table7_signals() | {"decision", "timestamp"} | (extra_capabilities or set())
        super().__init__(declared)
        self.execution_count = 0
        self.system_scope = system_scope

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.execution_count += 1
        return [_record_from(self.capabilities())]


class NoReasonsSUT(BaseSUT):
    """Reference SUT declaring every Table 7 signal except the reason-giving ones.

    The realistic black box: it keeps a decision trace, and that trace carries a value for
    every signal it declares — which is every Table 7 signal but the two that name a reason.
    So the reason-giving rows of the pack are unattainable as built while the rest stay
    checkable against the trace.

    `was_executed` records whether the trace was ever read, so a test can show that the
    unattainable analysis answered without running the system.
    """

    def __init__(self, system_scope: str = "high-risk"):
        super().__init__((_table7_signals() | {"decision", "timestamp"}) - REASON_SIGNALS)
        self.was_executed = False
        self.system_scope = system_scope

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.was_executed = True
        return [_record_from(self.capabilities())]
