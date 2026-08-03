"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.2.

What this module is for:
  Defines the required `SystemUnderTest` protocol interface (`capabilities()`, `decisions()`,
  `logic()`), the two optional hooks — `decide(case)` for active probing and `artifact(decision)`
  for the reason-deletion certificate — and `CAPABILITY_TAXONOMY` categories for black-box models,
  rule engines, and log traces.

What a reader must not break:
  - `artifact(decision)` is the second optional hook, and it returns the *inputs* to
    `certificate.certify` — `program`, `base`, `query`, `adapter`, `exact_depth`, and optionally
    `tol` and `labels` — never a verdict. A decision this system cannot open up returns None.
    Why this matters: an adapter that returned its own certificate, or a `reasons_are_complete`
    flag, would be a system grading its own homework, and `docs/semantics.md` §3 refuses exactly
    that. reasonsmith runs the enumeration and the deletion probes itself, over the artefact, so
    the number in the verdict is measured rather than declared. It stays outside the protocol for
    the reason `decide` does: a system that cannot expose its inference artefact is a lawful
    system, reported unattainable on a reason-adequacy duty rather than broken.
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
  - `logic()` may declare `computes` beside `variables`, `rules` and `constraints`: the names the
    system *produces*, as against the ones its decision situation supplies. Nothing here requires
    it, and logic that omits it is answered by the proved engine's older sort heuristic rather than
    refused — but an adapter exposing logic and declaring no directions is leaving that engine
    guessing, so `RulesAdapter` derives the declaration rather than let one go missing. It must be
    a collection of names and never a bare string, which reads as its own characters; the proved
    engine reports such logic not evaluated rather than take the reading. Declaring a computed name
    in `variables` too is the sound habit — that is where its sort comes from, and `RulesAdapter`
    refuses to construct without it — but the engine takes either list as saying the system has the
    name, so a computed name absent from the type table is an output at the default sort and never
    one the system has no notion of.
    Why this matters: the proved engine declares a free constant for every name it meets, so
    without directions a property naming something the system has no notion of is answered from
    numbers nobody computed. `variables` cannot carry it — it is a type table, and `approved` sits
    in it beside `income` — and `declared_capabilities` is what a system can *emit* into a decision
    record, which is the opposite direction. `docs/semantics.md` §3.5, *When the magnitudes are not
    the system's own*, states the three states the declaration makes readable.
  - `system_domains` is the second plain instance attribute the report reads off an adapter, the
    way `system_scope` already was: a collection of `spec.DECISION_DOMAINS` names saying what kind
    of decision this system makes. It is outside the protocol for the same reason `system_scope`
    is — an adapter that declares nothing is a system whose domain is undeclared, which is a
    lawful state and not a broken adapter.
    Why this matters: a system that declares no domain is never reported `satisfied` on a
    domain-limited duty. An adapter that sets the attribute to a domain its system does not
    decide in is claiming reach it does not have, and the report will answer duties that do not
    govern it — the false positive the gate exists to stop, reintroduced from the adapter side.
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
from functools import lru_cache
from typing import Any, Optional, Protocol, runtime_checkable

from reasonsmith.spec import Pack, load_pack

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
    """Required protocol for a system under test in reasonsmith.

    An adapter may additionally expose ``decide(case)`` or ``artifact(decision)``. Both stay
    outside this protocol because both are optional: ``decide`` is used for active probing only
    when no exposed ``logic()`` is available, and ``artifact`` only by a reason-adequacy duty,
    which reports a system exposing none unattainable rather than judging it on something weaker.
    """

    def capabilities(self) -> set[str]:
        """Return the signal names this adapter supplies for unattainability analysis."""
        ...

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return an iterable of decision trace records."""
        ...

    def logic(self) -> Any:
        """Return exposed decision logic for formal verification, if available."""
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

    def logic(self) -> Any:
        return None


@lru_cache(maxsize=1)
def _table7_pack() -> Pack:
    """The shipped Table 7 pack, parsed once for every derivation below.

    Cached because both derivations are read in the same constructor, and a reference system
    is built many times over a run: `load_pack` re-reads and re-parses the TOML on every call.
    The pack is frozen, so a shared instance cannot be edited by one caller under another.
    """
    return load_pack("table7")


def _table7_signals() -> set[str]:
    """Every signal the shipped Table 7 pack asks for, read from the pack itself.

    Read rather than restated: a hand-copied list would drift the moment the pack
    changes, and a reference system that declares stale signal names would make the
    unattainable analysis look wrong when it is right.
    """
    return {signal for req in _table7_pack().requirements for signal in req.requires}


def _table7_domains() -> tuple[str, ...]:
    """Every decision domain the shipped Table 7 pack targets, read from the pack itself.

    The same reasoning as `_table7_signals`: these reference systems exist to be the case where
    nothing is missing, so what they declare is read off the pack rather than typed out beside
    it. A hand-written list would make the domain gate look wrong the first time a row of the
    pack changed domain.
    """
    return tuple(sorted({d for req in _table7_pack().requirements for d in req.domains}))


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
        self,
        extra_capabilities: Optional[set[str]] = None,
        system_scope: str = "high-risk",
        system_domains: Optional[Iterable[str]] = None,
    ):
        declared = _table7_signals() | {"decision", "timestamp"} | (extra_capabilities or set())
        super().__init__(declared)
        self.execution_count = 0
        self.system_scope = system_scope
        self.system_domains = (
            _table7_domains() if system_domains is None else tuple(system_domains)
        )

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

    def __init__(
        self, system_scope: str = "high-risk", system_domains: Optional[Iterable[str]] = None
    ):
        super().__init__((_table7_signals() | {"decision", "timestamp"}) - REASON_SIGNALS)
        self.was_executed = False
        self.system_scope = system_scope
        self.system_domains = (
            _table7_domains() if system_domains is None else tuple(system_domains)
        )

    def decisions(self) -> Iterable[dict[str, Any]]:
        self.was_executed = True
        return [_record_from(self.capabilities())]
