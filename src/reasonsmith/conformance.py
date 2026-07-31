"""Conformance checks, taken from Table 19.

What this module is for:
  Computes Table 19 conformance metrics directly from reason-deletion certificates rather than
  estimating them. Table 19's first playbook — auditability with minimal retraining, the SKE case
  where reasons must be produced per decision — names its metrics as "fidelity to base model;
  coverage; stability across time/windows; rule size/complexity caps", and names among its controls
  "Minority over-smoothing: stratified fidelity/coverage; per-group checks; reason diversity tests".
  Those are the five checks here.

What a reader must not break:
  - Fidelity is reported in both absolute fidelity and retained share forms.
    Why this matters: Absolute fidelity follows nesyarena's own definition (metrics.py) — one minus
    the mean absolute error against the oracle, clamped to [0, 1] — so a case built from
    low-probability reasons scores high by construction, its products being small; retained share,
    the fraction of the exact answer's value the engine's answer still carries, catches the
    relative value loss absolute fidelity misses. The two disagree, and the disagreement is
    informative.
  - An unmeasured certificate (where exact inference enumerated zero reasons) must never be
    scored as measured.
    Why this matters: Prevents un-evaluated certificates from inflating coverage or fidelity scores.
  - Per-group comparisons carry explicit disclaimers regarding cohort size limits.
    Why this matters: Per-group figures are only as representative as the cases behind them.
"""

from __future__ import annotations

from itertools import combinations

LIMITS = (
    "These are measurements on the cases supplied, not a compliance guarantee and not legal "
    "advice. A per-group figure is only as representative as the cases behind it, and a group with "
    "few cases carries a correspondingly weak measurement."
)


def measured(cert) -> bool:
    """Whether this certificate measured anything at all.

    Exact inference that enumerated no reason produced no result about the engine: nothing was
    probed and nothing was compared, so every check in this module reports None for it rather than
    a score. There is one predicate for that, and every metric is gated on it, so the difference
    between checked-and-sound and not-checked cannot come back metric by metric.
    """
    return bool(cert.verdicts)


def fidelity(cert) -> float | None:
    """Table 19 'fidelity to base model', per nesyarena's metrics.fidelity: 1 - |error|, clamped.
    None on a certificate that measured nothing: zero error against a query whose reasons were
    never enumerated is not perfect fidelity."""
    return max(0.0, min(1.0, 1.0 - abs(cert.value_gap))) if measured(cert) else None


def retained_share(cert) -> float | None:
    """The fraction of the exact answer's value the engine still carries (1.0 = nothing lost).
    Reasons enumerated but an exact value of zero is a case with nothing to lose, reported as 1.0;
    no reason enumerated at all is a case nobody measured, reported as None."""
    if not measured(cert):
        return None
    return 1.0 if cert.exact_value == 0.0 else cert.engine_value / cert.exact_value


def coverage(cert) -> float | None:
    """Table 19 'coverage': the share of the exact reasons the engine's answer actually depends on.
    Reasons the probe could not certify count against coverage — an uncertified reason is not a
    covered one."""
    return len(cert.live) / len(cert.verdicts) if measured(cert) else None


def reason_set_size(cert) -> int | None:
    """Table 19 'rule size/complexity caps': how many reasons the engine actually used."""
    return len(cert.live) if measured(cert) else None


def stability(certs) -> float | None:
    """Table 19 'stability across time/windows': mean pairwise Jaccard similarity of the live reason
    sets across windows. 1.0 = the same reasons every window. A single window is trivially stable,
    and windows that measured nothing are not windows.

    The certificates must be *the same decision re-scored in successive windows*. Run across a
    cohort of different decisions this number means nothing, which is why it is not in
    `group_stats`.
    """
    sets = [frozenset(v.label for v in c.live) for c in certs if measured(c)]
    if not sets:
        return None
    pairs = list(combinations(sets, 2))
    if not pairs:
        return 1.0
    return sum(len(a & b) / len(a | b) if (a | b) else 1.0 for a, b in pairs) / len(pairs)


def reason_diversity(certs) -> float | None:
    """Table 19 'reason diversity tests': the share of the distinct reasons available across these
    cases that the engine ever gives. Collapse toward a few stock reasons shows up here as a low
    number even when every individual case looks well covered."""
    certs = [c for c in certs if measured(c)]
    if not certs:
        return None
    available = {v.label for c in certs for v in c.verdicts}
    given = {v.label for c in certs for v in c.live}
    return len(given) / len(available)


def _mean(values) -> float | None:
    """The mean over the cases that produced a measurement, or None when none did."""
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def group_stats(certs) -> dict:
    scored = [c for c in certs if measured(c)]
    return {
        "n": len(certs),
        "measured": len(scored),
        "fidelity": _mean(fidelity(c) for c in scored),
        "retained_share": _mean(retained_share(c) for c in scored),
        "coverage": _mean(coverage(c) for c in scored),
        "reasons_found": _mean(len(c.verdicts) for c in scored),
        "reasons_used": _mean(reason_set_size(c) for c in scored),
        "reasons_deleted": _mean(len(c.deleted) for c in scored),
        "reason_diversity": reason_diversity(scored),
    }


def stratified(groups: dict) -> dict:
    """Per-group checks, plus the gap between the best and worst group on each metric. This is the
    control Table 19 names against minority over-smoothing; the gaps are the thing it asks you to
    look at, since a healthy pooled figure can hide a group that has lost most of its reasons."""
    per = {name: group_stats(certs) for name, certs in groups.items()}
    gaps = {}
    for metric in ("fidelity", "retained_share", "coverage", "reasons_used", "reason_diversity"):
        vals = {g: s[metric] for g, s in per.items() if s[metric] is not None}
        if len(vals) < 2:
            gaps[metric] = {"best": None, "worst": None, "gap": None}
            continue
        best, worst = max(vals, key=vals.get), min(vals, key=vals.get)
        gaps[metric] = {"best": best, "worst": worst, "gap": vals[best] - vals[worst]}
    return {"per_group": per, "gaps": gaps}


def _cell(value) -> str:
    if value is None:
        return f"{'not measured':>17}"
    return f"{value:>17.4f}" if isinstance(value, float) else f"{value:>17}"


def render(strat: dict, size_cap: int | None = None) -> str:
    cols = ["n", "measured", "reasons_found", "reasons_used", "reasons_deleted", "coverage",
            "fidelity", "retained_share", "reason_diversity"]
    out = ["CONFORMANCE CHECKS (Table 19: fidelity, coverage, reason-set size,",
           "                    stratified per-group checks, reason diversity;",
           "                    stability is reported separately, over windows)",
           "",
           f"  {'group':<12}" + "".join(f"{c:>17}" for c in cols)]
    for name, s in strat["per_group"].items():
        out.append(f"  {name:<12}" + "".join(_cell(s[c]) for c in cols))
    out += ["", "  per-group gaps (best group minus worst):"]
    for metric, g in strat["gaps"].items():
        if g["gap"] is None:
            out.append(f"    {metric:<18} not measured   "
                       f"(fewer than two groups produced this metric)")
        else:
            out.append(f"    {metric:<18} {g['gap']:+.4f}   (best {g['best']}, worst {g['worst']})")
    if size_cap is not None:
        out.append("")
        out.append(f"  reason-set size cap {size_cap}: " + "; ".join(
            f"{name} not measured" if s["reasons_used"] is None else
            f"{name} mean {s['reasons_used']:.2f} "
            f"{'within' if s['reasons_used'] <= size_cap else 'OVER'}"
            for name, s in strat["per_group"].items()))
    out += ["", "LIMITS OF THESE MEASUREMENTS", f"  {LIMITS}"]
    return "\n".join(out)
