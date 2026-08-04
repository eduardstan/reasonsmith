"""The reason-deletion certificate.

What this module is for:
  Compares an engine's output against exact inference ground truth (enumerated via `nesyarena` WMC).
  Using deletion probes, it tests whether disabling isolated facts changes engine output,
  attributing dropped reasons to proof truncation or inference settings.

  Deletion probe mechanism:
    A reason r with a private fact (one no other exact reason uses) is switched off by setting its
    fact probability to zero. Exact inference loses r's exclusive contribution. If the engine's
    answer does not move at all, the engine did not depend on r: r was deleted. Every private fact
    of r is switched off, one at a time, and one that moves the engine settles r live.

What a reader must not break:
  - The probe only ever sets a probability *to zero*. It never raises one and it never adds a fact,
    so `deleted` means "the engine's answer did not depend on this reason under this
    interpretation" and nothing stronger.
    Why this matters: on an engine whose reasons can be *retracted* by an added fact, a lawfully
    retracted reason is indistinguishable from a dropped one under this definition — see `LIMITS`
    and `docs/semantics.md` §3 (*certificate*). The one fingerprint such an engine leaves is a
    deletion that moves its answer *up*, which is why the sign of `engine_drop` is kept rather than
    taken in absolute value, and reported as `ReasonVerdict.non_monotone` /
    `Certificate.non_monotone`.
  - Both independent checks must pass for a certificate to pass: the deletion probe
    (every reason live) and the value check against the exact oracle. Neither check
    subsumes the other.
    Why this matters: An engine that uses every reason but weights them wrongly passes the probe;
    the value check is what catches that. Conversely, an engine that drops a reason and
    compensates its value back onto the exact one passes the value check; the deletion probe is
    what catches that, and it names the reason that stopped mattering.
  - A reason with no private fact cannot be switched off alone (`unseparable`) and returns
    `INCONCLUSIVE`.
    Why this matters: Reasons sharing all facts cannot be probed in isolation, so dependency
    cannot be proven and is never assumed live.
  - A probe whose exact-side drop is zero carries no signal and is reported `inconclusive`.
    Why this matters: Zero drop means the private fact already had zero probability, producing no
    measurable signal.
  - A query with no enumerated reasons is never a `PASS` (returns `INCONCLUSIVE` or `FAIL`).
    Why this matters: A zero value gap on an un-enumerated query is not agreement; exact inference
    never evaluated it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from nesyarena.ir import Atom, GroundProgram
from nesyarena.oracle import wmc
from nesyarena.suts import proof_score

LIMITS = (
    "This certificate compares one engine's answer against exact inference on one ground program "
    "and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS "
    "means no reason was shown to be deleted and the engine's value matched the exact value on "
    "this input; it does not certify the engine on any other input, and it does not establish that "
    "the reasons themselves are correct, only that the engine used all of the ones exact inference "
    "found. The probe is one-directional: it only switches facts off, never on, so `deleted` means "
    "the engine's answer did not depend on this reason *under this interpretation*. On a system "
    "whose reasons can be retracted by an added fact — a policy exception evaluated after the "
    "rules fire — a lawfully retracted reason is reported deleted here exactly as a dropped one "
    "is, and can drive a violated verdict against a system that stated its reasons correctly. "
    "Where a "
    "deletion moves the engine's answer up, that is reported as a possible non-monotonicity, and "
    "it is the only fingerprint of the condition this instrument can leave."
)


#: Said once, on the verdict and on the certificate, wherever a deletion moved the engine's answer
#: up. Deliberately a remark and not a bucket: the reason it is attached to was probed cleanly, and
#: burying it in an inconclusive bucket would lose the one signal that detects the condition.
NON_MONOTONE_REMARK = (
    "the engine's answer rose when a fact was removed; this engine may not be monotone in its "
    "inputs. Deletion probing assumes it is, so a reason this engine withdrew under the base "
    "interpretation — a policy exception firing, say — is reported deleted here exactly as a "
    "dropped one is."
)


@dataclass(frozen=True)
class ReasonVerdict:
    """One exact reason, and what the deletion probe found out about it."""

    reason: frozenset
    label: str
    score: float
    status: str  # live | deleted | unseparable | inconclusive
    probe_fact: Atom | None  # the fact whose probe settled this status
    exact_drop: float
    engine_drop: float
    detail: str
    #: Every private fact of this reason, each switched off alone. Empty for `unseparable`.
    probe_facts: tuple[Atom, ...] = ()
    #: Engine re-runs this reason cost: one per probe that moved exact inference at all.
    engine_probes: int = 0
    #: A probe of this reason moved the engine's answer *up*. Not a fault of the reason — evidence
    #: that the engine is not monotone in its inputs, and that `deleted` may be reading a
    #: retraction. See `LIMITS`.
    non_monotone: bool = False

    def to_dict(self) -> dict:
        return {
            "reason": [str(a) for a in sorted(self.reason, key=repr)],
            "label": self.label,
            "score": self.score,
            "status": self.status,
            "probe_fact": str(self.probe_fact) if self.probe_fact is not None else None,
            "probe_facts": [str(a) for a in self.probe_facts],
            "engine_probes": self.engine_probes,
            "exact_drop": self.exact_drop,
            "engine_drop": self.engine_drop,
            "non_monotone": self.non_monotone,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Certificate:
    query: Atom
    adapter_name: str
    claimed_semantics: str
    exact_depth: int
    exact_value: float
    engine_value: float
    tol: float
    verdicts: tuple[ReasonVerdict, ...]
    attribution: str

    def _by(self, status: str) -> list[ReasonVerdict]:
        return [v for v in self.verdicts if v.status == status]

    @property
    def deleted(self) -> list[ReasonVerdict]:
        return self._by("deleted")

    @property
    def live(self) -> list[ReasonVerdict]:
        return self._by("live")

    @property
    def uncertified(self) -> list[ReasonVerdict]:
        return self._by("unseparable") + self._by("inconclusive")

    @property
    def non_monotone(self) -> list[ReasonVerdict]:
        """Reasons a probe of which moved the engine's answer up. See `LIMITS`."""
        return [v for v in self.verdicts if v.non_monotone]

    @property
    def value_gap(self) -> float:
        return self.engine_value - self.exact_value

    @property
    def verdict(self) -> str:
        if self.deleted or abs(self.value_gap) > self.tol:
            return "FAIL"
        if not self.verdicts or self.uncertified:
            return "INCONCLUSIVE"
        return "PASS"

    def missing_reasons(self) -> list[str]:
        return [v.label for v in self.deleted]

    def render(self) -> str:
        out = [
            f"REASON-DELETION CERTIFICATE [{self.verdict}]",
            f"query: {self.query!r}",
            f"engine: {self.adapter_name}   claims: {self.claimed_semantics}",
            f"exact inference: bounded proof enumeration to depth {self.exact_depth} "
            f"(nesyarena ground-program IR) + exact weighted model counting",
            f"exact value {self.exact_value:.6f}   engine value {self.engine_value:.6f}   "
            f"gap {self.value_gap:+.6f}   tolerance {self.tol:g}",
            f"reasons: {len(self.verdicts)} found by exact inference, {len(self.live)} used by the "
            f"engine, {len(self.deleted)} deleted, {len(self.uncertified)} not certifiable",
            "",
        ]
        for v in sorted(self.verdicts, key=lambda v: (-v.score, v.label)):
            mark = {"live": "used", "deleted": "DELETED", "unseparable": "not certifiable",
                    "inconclusive": "not certifiable"}[v.status]
            out.append(f"  [{mark:>15}] {v.label}  (score {v.score:.6f})")
            out.append(f"                    facts: {', '.join(sorted(repr(a) for a in v.reason))}")
            out.append(f"                    {v.detail}")
        if self.deleted:
            out += [
                "",
                f"MISSING REASONS: the engine's answer does not depend on {len(self.deleted)} "
                f"reason(s) that exact inference found:",
            ]
            out += [f"  - {v.label}: {', '.join(sorted(repr(a) for a in v.reason))}"
                    for v in sorted(self.deleted, key=lambda v: (-v.score, v.label))]
        if self.non_monotone:
            out += ["", f"NON-MONOTONICITY: {NON_MONOTONE_REMARK}", ""]
            out += [f"  - {v.label}: deleting {v.probe_fact!r} raised the engine's answer by "
                    f"{-v.engine_drop:+.6f}"
                    for v in sorted(self.non_monotone, key=lambda v: (-v.score, v.label))]
        out += ["", f"ATTRIBUTION: {self.attribution}"]
        out += ["", "LIMITS OF THIS CERTIFICATE", f"  {LIMITS}"]
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "query": str(self.query),
            "adapter_name": self.adapter_name,
            "claimed_semantics": self.claimed_semantics,
            "exact_depth": self.exact_depth,
            "exact_value": self.exact_value,
            "engine_value": self.engine_value,
            "value_gap": self.value_gap,
            "tol": self.tol,
            "reasons_found": len(self.verdicts),
            "reasons_used": len(self.live),
            "reasons_deleted": len(self.deleted),
            "reasons_uncertified": len(self.uncertified),
            "reasons_non_monotone": len(self.non_monotone),
            "missing_reasons": self.missing_reasons(),
            "verdicts": [v.to_dict() for v in self.verdicts],
            "attribution": self.attribution,
            "limits": LIMITS,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON for `to_dict`. Values outside JSON's own types are stringified exactly as
        `render` prints them, so an adapter-supplied value of any type serialises rather than
        raising."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def _attribute(verdicts, value_gap: float, tol: float) -> str:
    deleted = [v for v in verdicts if v.status == "deleted"]
    live = [v for v in verdicts if v.status == "live"]
    uncertified = [v for v in verdicts if v.status in ("unseparable", "inconclusive")]
    if not verdicts:
        if abs(value_gap) > tol:
            return (
                f"Exact inference found no reason for this query at this depth, and yet the engine "
                f"returns a value {value_gap:+.6f} away from it. No reason was probed, so nothing "
                f"is certified either way, and the engine's answer rests on something this "
                f"enumeration did not find: an unsupported query, a wrong identifier, or a proof "
                f"bound below the one the engine itself uses."
            )
        return (
            "Exact inference found no reason for this query at this depth, so no reason was probed "
            "and there was nothing to compare: an unsupported query, a wrong identifier or a proof "
            "bound too low all look like this. Nothing about the engine is certified either way."
        )
    if not deleted:
        if abs(value_gap) > tol:
            return (
                f"No reason was deleted, but the engine's value differs from exact inference by "
                f"{value_gap:+.6f}. The responsible setting is the engine's aggregation over the "
                f"reasons it kept, not proof truncation: every reason still moves the answer."
            )
        if uncertified:
            return (
                f"No reason was shown deleted, but {len(uncertified)} could not be probed in "
                f"isolation, so the reason set is not certified complete."
            )
        return (
            "The engine used every reason exact inference found, and its value matched the exact "
            "value within tolerance. No inference setting is implicated on this input."
        )
    order = sorted(verdicts, key=lambda v: (-v.score, v.label))
    tail = set(order[len(live):]) if live else set(order)
    if len(live) and set(deleted) == tail and not uncertified:
        return (
            f"The deleted reasons are exactly the {len(deleted)} lowest-scoring of the "
            f"{len(verdicts)}, and the engine kept the top {len(live)}. This is the signature of "
            f"top-k proof truncation at k={len(live)}: top-k works by discarding proofs, so the "
            f"dropped reasons are lost by configuration, not by error. The missing probability "
            f"mass is {-value_gap:.6f}."
        )
    return (
        f"{len(deleted)} reason(s) deleted, but they are not the {len(deleted)} lowest-scoring "
        f"reasons, so score-ordered top-k truncation does not explain the loss. Some other setting "
        f"in the engine — proof search bound, pruning heuristic, or a defect — is dropping reasons "
        f"the exact enumeration found."
    )


def certify(program: GroundProgram, base: dict, query: Atom, adapter, exact_depth: int,
            tol: float = 1e-9, labels: dict | None = None) -> Certificate:
    """Compare the reasons an engine actually used against the exact set, and name what is missing.

    `program`, `base` and `query` are exactly what the adapter and the oracle both consume (that
    shared input is the invariant nesyarena's adapter protocol exists to hold). `exact_depth` bounds
    proof enumeration; `labels` maps a reason's EDB support set to a human name, such as a reason
    code, and falls back to the facts themselves.
    """
    labels = labels or {}
    reasons = program.proof_supports(query, exact_depth)
    exact_value = wmc(reasons, base)
    engine_value = float(adapter.infer(program, base, [query])[query])

    seen: dict[Atom, int] = {}
    for r in reasons:
        for f in r:
            seen[f] = seen.get(f, 0) + 1

    verdicts = []
    for r in reasons:
        label = labels.get(r, "{" + ", ".join(sorted(repr(a) for a in r)) + "}")
        score = proof_score(r, base)
        private = tuple(sorted((f for f in r if seen[f] == 1), key=repr))
        if not private:
            verdicts.append(ReasonVerdict(
                r, label, score, "unseparable", None, 0.0, 0.0,
                "every fact of this reason is shared with another reason, so it cannot be switched "
                "off alone; not certified either way."))
            continue
        # Every private fact, one at a time. Probing one of them and calling the reason answered
        # made coverage a function of the facts' names: two systems alike but for a field name got
        # different probes.
        signal: list[tuple[Atom, float, float]] = []
        silent: list[tuple[Atom, float]] = []
        for probe in private:
            probed = dict(base)
            probed[probe] = 0.0
            exact_drop = exact_value - wmc(reasons, probed)
            if exact_drop <= tol:
                silent.append((probe, exact_drop))
                continue
            signal.append(
                (probe, exact_drop,
                 engine_value - float(adapter.infer(program, probed, [query])[query])))
        coverage = (
            f" All {len(private)} private fact(s) of this reason were switched off, one at a time."
            if len(private) > 1
            else ""
        )
        if not signal:
            probe, exact_drop = silent[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "inconclusive", probe, exact_drop, 0.0,
                f"deleting {probe!r} does not move exact inference either ({exact_drop:+.2e}), so "
                f"the probe carries no signal; not certified either way.{coverage}",
                private, len(signal)))
            continue
        moved = [t for t in signal if abs(t[2]) > tol]
        # A rise is the one fingerprint a non-monotone engine leaves, so it is the probe reported.
        rose = [t for t in moved if t[2] < -tol]
        if moved:
            probe, exact_drop, engine_drop = (rose or moved)[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "live", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} and the engine by "
                f"{-engine_drop:+.6f}: the engine's answer depends on this reason.{coverage}"
                + (f" {NON_MONOTONE_REMARK[0].upper()}{NON_MONOTONE_REMARK[1:]}" if rose else ""),
                private, len(signal), bool(rose)))
        else:
            probe, exact_drop, engine_drop = signal[0]
            verdicts.append(ReasonVerdict(
                r, label, score, "deleted", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} but leaves the "
                f"engine unchanged: the engine's answer does not depend on this reason.{coverage}",
                private, len(signal)))

    verdicts = tuple(verdicts)
    return Certificate(
        query, adapter.name, adapter.claimed_semantics, exact_depth, exact_value, engine_value,
        tol, verdicts, _attribute(verdicts, engine_value - exact_value, tol))
