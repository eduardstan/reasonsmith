"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.2.

The SUT protocol is deliberately minimal so that black-box neural models, rule engines,
and log traces qualify equally.

Capabilities are DECLARED by the system, never inferred. The unattainable analysis
relies on the system explicitly stating what signals it can emit.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Protocol, runtime_checkable

from reasonsmith.spec import load_pack


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
        # A bare string is iterable, so set("reasons") would silently declare six
        # single-character capabilities and make every real requirement look
        # unattainable for the wrong reason.
        if isinstance(declared_capabilities, str):
            raise TypeError(
                "declared_capabilities must be a collection of signal names, not a single string; "
                f"pass {{{declared_capabilities!r}}} to declare one signal"
            )
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


class FullCapabilitySUT(BaseSUT):
    """Reference SUT declaring every signal the Table 7 pack requires."""

    def __init__(self, extra_capabilities: Optional[set[str]] = None):
        declared = _table7_signals() | {"decision", "timestamp"} | (extra_capabilities or set())
        super().__init__(declared)
        self.execution_count = 0

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.execution_count += 1
        record: dict[str, Any] = {
            "decision": "approved",
            "timestamp": "2026-07-31T09:00:00Z",
        }
        for signal in sorted(self.capabilities() - set(record)):
            record[signal] = f"{signal}_value"
        return [record]


class NoReasonsSUT(BaseSUT):
    """Reference SUT declaring every Table 7 signal except the reason-giving ones.

    Calling decisions() raises, so any code path that reaches for the trace while
    answering an unattainable requirement fails loudly instead of quietly working.
    """

    def __init__(self):
        super().__init__((_table7_signals() | {"decision", "timestamp"}) - REASON_SIGNALS)
        self.was_executed = False

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.was_executed = True
        raise AssertionError(
            "NoReasonsSUT.decisions() must never be executed for unattainable checks!"
        )
