"""The reason-deletion certificate.

For a proof-based system, exact inference enumerates *every* reason for a query. That is a ground
truth post-hoc explanation methods do not have: there is a complete set to compare an engine's
answer against, rather than a plausible story about it. nesyarena supplies the pieces — the ground
program IR, bounded proof enumeration, the exact WMC oracle, and the adapter protocol — so this
module adds one thing only: the comparison, and the attribution of any gap to an inference setting.

The comparison is a deletion probe, and it works through the adapter protocol as it stands, without
asking an engine to confess which proofs it used. A reason r that has a *private* fact — one no
other exact reason uses — can be switched off in isolation by setting that fact's probability to
zero. Exact inference then loses exactly r's exclusive contribution. If the engine's answer does not
move at all, the engine's answer did not depend on r: r was deleted.

What the probe establishes and what it does not:

  - It establishes *dependence*, not correct weighting. An engine that uses every reason but weights
    them wrongly passes the probe; the separate value check against the exact oracle is what catches
    that, and both must hold for the certificate to pass.
  - A reason with no private fact cannot be switched off alone. It is reported `unseparable` and the
    certificate returns INCONCLUSIVE. It is never assumed live.
  - A probe whose exact-side drop is zero carries no signal (the private fact already had zero
    probability). It is reported `inconclusive` for the same reason, and never counted as live.
  - A query for which exact inference enumerates no reason at this depth was never probed at all,
    so it can never be PASS: the certificate returns INCONCLUSIVE, or FAIL if the engine still
    answers away from the exact value. A zero value gap on a query nobody enumerated is not
    agreement, and the attribution names what that case looks like (an unsupported query, a wrong
    identifier, a proof bound too low).
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
    "found."
)


@dataclass(frozen=True)
class ReasonVerdict:
    """One exact reason, and what the deletion probe found out about it."""

    reason: frozenset
    label: str
    score: float
    status: str  # live | deleted | unseparable | inconclusive
    probe_fact: Atom | None
    exact_drop: float
    engine_drop: float
    detail: str

    def to_dict(self) -> dict:
        return {
            "reason": [str(a) for a in sorted(self.reason, key=repr)],
            "label": self.label,
            "score": self.score,
            "status": self.status,
            "probe_fact": str(self.probe_fact) if self.probe_fact is not None else None,
            "exact_drop": self.exact_drop,
            "engine_drop": self.engine_drop,
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
        private = sorted((f for f in r if seen[f] == 1), key=repr)
        if not private:
            verdicts.append(ReasonVerdict(
                r, label, score, "unseparable", None, 0.0, 0.0,
                "every fact of this reason is shared with another reason, so it cannot be switched "
                "off alone; not certified either way."))
            continue
        probe = private[0]
        probed = dict(base)
        probed[probe] = 0.0
        exact_drop = exact_value - wmc(reasons, probed)
        if exact_drop <= tol:
            verdicts.append(ReasonVerdict(
                r, label, score, "inconclusive", probe, exact_drop, 0.0,
                f"deleting {probe!r} does not move exact inference either ({exact_drop:+.2e}), so "
                f"the probe carries no signal; not certified either way."))
            continue
        engine_drop = engine_value - float(adapter.infer(program, probed, [query])[query])
        if abs(engine_drop) > tol:
            verdicts.append(ReasonVerdict(
                r, label, score, "live", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} and the engine by "
                f"{-engine_drop:+.6f}: the engine's answer depends on this reason."))
        else:
            verdicts.append(ReasonVerdict(
                r, label, score, "deleted", probe, exact_drop, engine_drop,
                f"deleting {probe!r} moves exact inference by {-exact_drop:+.6f} but leaves the "
                f"engine unchanged: the engine's answer does not depend on this reason."))

    verdicts = tuple(verdicts)
    return Certificate(
        query, adapter.name, adapter.claimed_semantics, exact_depth, exact_value, engine_value,
        tol, verdicts, _attribute(verdicts, engine_value - exact_value, tol))
