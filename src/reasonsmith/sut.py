"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.2.

The SUT protocol is deliberately minimal so that black-box neural models, rule engines,
and log traces qualify equally.

Capabilities are DECLARED by the system, never inferred. The unattainable analysis
relies on the system explicitly stating what signals it can emit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Optional, Protocol, runtime_checkable

from reasonsmith.spec import load_pack


def _validate_capability_collection(declared: Any, subject: str) -> None:
    """Refuse anything that is not a plain collection of enabled signal names.

    Shared by the two places capabilities cross into reasonsmith — BaseSUT.__init__ and the
    unattainable analysis — because a system whose declaration is misread there is judged
    against signals it never claimed, in either direction.

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
        """Return the set of signal names this system declares it can emit."""
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

    def __init__(self, extra_capabilities: Optional[set[str]] = None):
        declared = _table7_signals() | {"decision", "timestamp"} | (extra_capabilities or set())
        super().__init__(declared)
        self.execution_count = 0

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

    def __init__(self):
        super().__init__((_table7_signals() | {"decision", "timestamp"}) - REASON_SIGNALS)
        self.was_executed = False

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.was_executed = True
        return [_record_from(self.capabilities())]
