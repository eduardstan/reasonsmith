"""System Under Test (SUT) protocol and reference implementations for reasonsmith v0.10.2.

What this module is for:
  Defines the required `SystemUnderTest` protocol interface (`capabilities()`, `decisions()`,
  `logic()`), the two optional hooks — `decide(case)` for active probing and `artifact(decision)`
  for the reason-deletion certificate — and `CAPABILITY_TAXONOMY` categories for black-box models,
  rule engines, and log traces.

What a reader must not break:
  - `artifact(decision)` is the second optional hook, and it returns an
    `artifacts.InferenceArtifact` — or, for the one family this package ships an adapter for, the
    *inputs* to `certificate.certify`: `program`, `base`, `query`, `adapter`, `exact_depth`,
    `monotone`, and optionally `tol`, `labels`, `budget` and `decision_threshold` — never a verdict.
    `decision_threshold` is optional; when present it must be a finite real number and is measured
    into the semantics-agreement margin, while absence preserves the decision record's declared
    margin. A decision this system cannot
    open up returns None.
    Why this matters: an adapter that returned its own certificate, or a `reasons_are_complete`
    flag, would be a system grading its own homework, and `docs/semantics.md` §3 refuses exactly
    that. reasonsmith runs the enumeration and the deletion probes itself, over the artefact, so
    the number in the verdict is measured rather than declared. It stays outside the protocol for
    the reason `decide` does: a system that cannot expose its inference artefact is a lawful
    system, reported unattainable on a reason-adequacy duty rather than broken.
  - The artefact declares whether its inference is **monotone in its facts**, and that declaration
    is required: an artefact declaring nothing, declaring `False`, or declaring `True` where the
    probe measured a deletion that raised the system's answer is reported *not evaluated* rather
    than measured (`artifacts.deletion_semantics_refusal`, `docs/semantics.md` §3, *The inference
    artefact*).
    Why this matters: the deletion probe defines a reason as one the answer would not have been
    reached without, and measures it by switching facts off. On an inference a fact can *retract* a
    reason from, a lawfully withdrawn reason is indistinguishable from a dropped one, and this is
    the one place a self-declaration is the difference between a false accusation and a refusal.
    It is not read as a promise: it can be refuted by the measurement and never confirmed by it,
    and the standing answer for every other self-declaration here (`docs/semantics.md` §3, *The
    assumption all seven share*) governs it otherwise.
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
    it: the proved engine's older sort heuristic runs whether or not directions are declared, so
    logic that omits `computes` is answered by that heuristic alone rather than refused, and a
    declaration narrows what reaches the solver and never widens it — but an adapter exposing logic
    and declaring no directions is leaving that engine
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
  - A decision record may carry its own clock under the reserved `TIME_DOMAIN_KEY`, and
    `read_time_domain` is the one place a trace is asked what clock it states. A trace carrying no
    such key is `ORDINAL_DOMAIN` — the record index, which is what every reader here has always
    counted on — so a timeless log never acquires a clock by having been read.
    Why this matters: a deadline duty today reads one latency number the system computes about
    itself, and which event it was counted from is that system's own claim (`docs/refinement.md`,
    the `ecoa_reg_b_1002_9_a_1_timing_of_notice` row). The recorded events are what lets an engine
    check such a bound against the log instead, and one engine now does: the bounded-response
    evaluator in `engines/observed` reads the parsed instants of `TimeDomain.instants` directly.
    `TimeDomain.ticks` still refuses every domain but the ordinal one, because the rtamt axis is
    positional and nothing else may be relabelled as time, so a duty needing a real clock and
    written without that operator is still reported not evaluated rather than answered off record
    indices.
  - `CAPABILITY_TAXONOMY` documents the four Section 6.3 categories that signal names are
    conventionally prefixed with (`provenance_`, `artifact_logs_`, ...). It is a reference for pack
    and adapter authors, not a validator: nothing here checks a name against it, and a pack is free
    to name a signal outside it.
    Why this matters: Reading it as enforced would hide that an out-of-taxonomy signal name passes
    unremarked and simply reports the requirement unattainable when no adapter supplies it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional, Protocol, runtime_checkable

from reasonsmith.event_time import EventTimeError, parse_timestamp
from reasonsmith.neural import DeclaredInputSpace
from reasonsmith.spec import Pack, load_pack, normalize_frontier_ai_status

#: Section 6.3 top-level taxonomy for capability signals supplied through the SUT protocol
#: (Stan, Sciavicco & Napoletano, JAIR 2026, Section 6.3, p. 36:24 — `[@stan-2026]`):
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


#: The reserved decision-record key carrying that decision's own clock: a mapping of event-kind
#: name to the timestamp that event happened at, e.g.
#: ``{"completed_application_received": "2026-06-01T09:00:00Z",
#:    "applicant_notified": "2026-06-15T09:00:00Z"}``.
#:
#: It is dunder-spelled because it is not a signal: nothing in the property language reads it, it
#: is never a name in a `spec`, and no capability declares it. What it records is *which* event a
#: duration was counted from, which today is the one thing a latency number a system computes
#: about itself cannot say (`docs/refinement.md`, the `ecoa_reg_b_1002_9_a_1_timing_of_notice`
#: row). Event kinds are the record's own vocabulary; `ECOA_1002_9_A_1_EVENTS` is the worked case
#: and not a closed list.
TIME_DOMAIN_KEY = "__time_domain__"

#: The time domain the positional monitor counts on: the record index, one tick per decision, in
#: the order the trace supplied them (`docs/semantics.md` §2, *Time is the record index*).
ORDINAL_TIME = "ordinal"

#: The time domain of a trace whose records carry `TIME_DOMAIN_KEY`. The bounded-response metric
#: operator is the sole reader of these timestamps; other temporal duties remain positional.
EVENT_TIME = "event"

#: The domains a trace may declare and a duty may be asked for on.
TIME_DOMAINS = (ORDINAL_TIME, EVENT_TIME)

#: The events 12 CFR 1002.9(a)(1) counts its notification deadline from — the worked case, and the
#: reason a recorded clock is worth having. Paragraphs (i), (ii) and (iii) each start a 30-day
#: clock at a different event and (iv) starts a 90-day one; `applicant_notified` is where all four
#: stop. A record naming which of these it holds a timestamp for states what the clause needs and
#: a single latency number cannot. Reference names for a pack and adapter author, not a validator:
#: nothing here checks an event kind against them.
ECOA_1002_9_A_1_EVENTS = (
    "completed_application_received",
    "adverse_action_on_incomplete_application",
    "adverse_action_on_existing_account",
    "counteroffer_notified",
    "applicant_notified",
)


@dataclass(frozen=True)
class TimeDomain:
    """The clock a decision trace states, and the axis a monitor is fed.

    `kind` is one of `TIME_DOMAINS`. `events` is empty for `ORDINAL_TIME`, and otherwise holds one
    entry per record — that record's event-kind-to-timestamp mapping, or None for a record that
    carries none.

    `ticks` is deliberately the only way a positional monitor axis is produced, and it refuses every
    domain but the ordinal one. The bounded-response event-time evaluator does not use a synthetic
    axis: it reads and subtracts the parsed timestamp maps directly.
    """

    kind: str
    events: tuple[Mapping[str, str] | None, ...] = ()
    # Parsed UTC instants are populated for event traces. The raw ``events`` mapping remains
    # untouched for backwards-compatible report/debug output.
    instants: tuple[Mapping[str, datetime] | None, ...] = ()

    @property
    def is_ordinal(self) -> bool:
        return self.kind == ORDINAL_TIME

    def ticks(self, length: int) -> list[int]:
        """The `length` time points a monitor over this domain is fed."""
        if not self.is_ordinal:
            raise ValueError(
                f"No time axis exists for the {self.kind!r} time domain: reasonsmith counts "
                "decisions, not seconds"
            )
        return list(range(length))


#: The domain of every trace that states no clock, and the domain every positional duty is asked
#: on. Shared because it carries no per-record state.
ORDINAL_DOMAIN = TimeDomain(ORDINAL_TIME)

#: Explicit selection for the bounded-response operator. Metric evaluation does not turn this into
#: an rtamt axis: the event-time engine reads the timestamp maps directly.
EVENT_DOMAIN = TimeDomain(EVENT_TIME)


def read_time_domain(records: Iterable[Mapping[str, Any]]) -> TimeDomain:
    """The time domain a decision trace states, read off the records themselves.

    `ORDINAL_DOMAIN` unless at least one record carries `TIME_DOMAIN_KEY`, so a log that says
    nothing about time acquires no clock by having been read — the backwards-compatible answer,
    stated once here rather than assumed at every reader.
    """
    events: list[Mapping[str, str] | None] = []
    instants: list[Mapping[str, datetime] | None] = []
    clocked = False
    for record in records:
        stamps = record.get(TIME_DOMAIN_KEY)
        if stamps is None:
            events.append(None)
            instants.append(None)
            continue
        if not isinstance(stamps, Mapping):
            raise TypeError(
                f"{TIME_DOMAIN_KEY} must map an event-kind name to a timestamp, got "
                f"{type(stamps).__name__}"
            )
        parsed: dict[str, datetime] = {}
        for kind, stamp in stamps.items():
            if not isinstance(kind, str) or not kind.strip():
                raise ValueError(f"Event kind must be a non-empty name, got {kind!r}")
            if not isinstance(stamp, str) or not stamp.strip():
                raise ValueError(f"Event {kind!r} must carry a timestamp, got {stamp!r}")
            try:
                parsed[kind] = parse_timestamp(stamp)
            except EventTimeError as exc:
                raise ValueError(f"Event {kind!r} has an invalid timestamp: {exc}") from exc
        clocked = True
        events.append(dict(stamps))
        instants.append(parsed)
    return TimeDomain(EVENT_TIME, tuple(events), tuple(instants)) if clocked else ORDINAL_DOMAIN


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

    An adapter may additionally expose ``decide(case)``, ``artifact(decision=None)`` or
    ``input_space()``. These hooks remain optional: ``decide`` is used for active probing only
    when no exposed ``logic()`` is available, and ``artifact`` only by a reason-adequacy duty,
    which reports a system exposing none unattainable rather than judging it on something weaker.
    What a decision-bound ``artifact(decision)`` returns is
    `artifacts.InferenceArtifact`, whose own contract is the one this module's docstring states.
    The additive ``artifact(None)`` convention may instead return a model-global
    `neural.OnnxArtifact`; certificate code never asks for that form. ``input_space()`` may return
    a `neural.DeclaredInputSpace` and is not consumed by the current engines.
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


@runtime_checkable
class NeuralExposures(Protocol):
    """Optional, additive neural exposure hooks.

    This separate protocol keeps ``SystemUnderTest`` runtime-compatible with every existing
    adapter: neither hook is required merely to be a SUT.
    """

    def artifact(self, decision: Mapping[str, Any] | None = None) -> Any:
        """Return a decision artifact, or a model-global OnnxArtifact for ``None``."""
        ...

    def input_space(self) -> DeclaredInputSpace | None:
        """Return a validated declared replay space when the adapter exposes one."""
        ...


class BaseSUT:
    """Convenience base class or reference helper for SUT implementations.

    ``frontier_ai_status`` is an optional, self-asserted applicability declaration for the Seoul
    pack. It is not a record capability and reasonsmith never infers or independently verifies it.
    """

    def __init__(
        self,
        declared_capabilities: set[str] | Iterable[str],
        *,
        frontier_ai_status: str | None = None,
    ):
        _validate_capability_collection(declared_capabilities, "declared_capabilities must be")
        self._capabilities = set(declared_capabilities)
        self.frontier_ai_status = normalize_frontier_ai_status(frontier_ai_status)
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
