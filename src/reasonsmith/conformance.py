"""Conformance checks, taken from Table 19.

Table 19's first playbook — auditability with minimal retraining, the SKE case where reasons must be
produced per decision — names its metrics as "fidelity to base model; coverage; stability across
time/windows; rule size/complexity caps", and names among its controls "Minority over-smoothing:
stratified fidelity/coverage; per-group checks; reason diversity tests". Those are the five checks
here, computed from reason-deletion certificates rather than estimated.

Fidelity follows nesyarena's own definition (metrics.py): one minus the mean absolute error against
the oracle, clamped to [0, 1]. Two forms are reported, because they disagree and the disagreement is
informative: absolute fidelity, and retained share, the fraction of the exact answer's value the
engine's answer still carries. A case built from low-probability reasons has small absolute error by
construction — the products are small — while having lost most of its value in relative terms.
"""

from __future__ import annotations

from itertools import combinations

LIMITS = (
    "These are measurements on the cases supplied, not a compliance guarantee and not legal "
    "advice. A per-group figure is only as representative as the cases behind it, and a group with "
    "few cases carries a correspondingly weak measurement."
)


def fidelity(cert) -> float:
    """Table 19 'fidelity to base model', per nesyarena's metrics.fidelity: 1 - |error|, clamped."""
    return max(0.0, min(1.0, 1.0 - abs(cert.value_gap)))


def retained_share(cert) -> float:
    """The fraction of the exact answer's value the engine still carries (1.0 = nothing lost).
    Undefined when exact inference gives zero, reported as 1.0 for want of anything to lose."""
    return 1.0 if cert.exact_value == 0.0 else cert.engine_value / cert.exact_value


def coverage(cert) -> float:
    """Table 19 'coverage': the share of the exact reasons the engine's answer actually depends on.
    Reasons the probe could not certify count against coverage — an uncertified reason is not a
    covered one."""
    return len(cert.live) / len(cert.verdicts) if cert.verdicts else 1.0


def reason_set_size(cert) -> int:
    """Table 19 'rule size/complexity caps': how many reasons the engine actually used."""
    return len(cert.live)


def stability(certs) -> float:
    """Table 19 'stability across time/windows': mean pairwise Jaccard similarity of the live reason
    sets across windows. 1.0 = the same reasons every window. A single window is trivially stable.

    The certificates must be *the same decision re-scored in successive windows*. Run across a
    cohort of different decisions this number means nothing, which is why it is not in
    `group_stats`.
    """
    sets = [frozenset(v.label for v in c.live) for c in certs]
    pairs = list(combinations(sets, 2))
    if not pairs:
        return 1.0
    return sum(len(a & b) / len(a | b) if (a | b) else 1.0 for a, b in pairs) / len(pairs)


def reason_diversity(certs) -> float:
    """Table 19 'reason diversity tests': the share of the distinct reasons available across these
    cases that the engine ever gives. Collapse toward a few stock reasons shows up here as a low
    number even when every individual case looks well covered."""
    available = {v.label for c in certs for v in c.verdicts}
    given = {v.label for c in certs for v in c.live}
    return len(given) / len(available) if available else 1.0


def group_stats(certs) -> dict:
    n = len(certs)
    return {
        "n": n,
        "fidelity": sum(fidelity(c) for c in certs) / n,
        "retained_share": sum(retained_share(c) for c in certs) / n,
        "coverage": sum(coverage(c) for c in certs) / n,
        "reasons_found": sum(len(c.verdicts) for c in certs) / n,
        "reasons_used": sum(reason_set_size(c) for c in certs) / n,
        "reasons_deleted": sum(len(c.deleted) for c in certs) / n,
        "reason_diversity": reason_diversity(certs),
    }


def stratified(groups: dict) -> dict:
    """Per-group checks, plus the gap between the best and worst group on each metric. This is the
    control Table 19 names against minority over-smoothing; the gaps are the thing it asks you to
    look at, since a healthy pooled figure can hide a group that has lost most of its reasons."""
    per = {name: group_stats(certs) for name, certs in groups.items() if certs}
    gaps = {}
    for metric in ("fidelity", "retained_share", "coverage", "reasons_used", "reason_diversity"):
        vals = {g: s[metric] for g, s in per.items()}
        best, worst = max(vals, key=vals.get), min(vals, key=vals.get)
        gaps[metric] = {"best": best, "worst": worst, "gap": vals[best] - vals[worst]}
    return {"per_group": per, "gaps": gaps}


def render(strat: dict, size_cap: int | None = None) -> str:
    cols = ["n", "reasons_found", "reasons_used", "reasons_deleted", "coverage", "fidelity",
            "retained_share", "reason_diversity"]
    out = ["CONFORMANCE CHECKS (Table 19: fidelity, coverage, reason-set size,",
           "                    stratified per-group checks, reason diversity;",
           "                    stability is reported separately, over windows)",
           "",
           f"  {'group':<12}" + "".join(f"{c:>17}" for c in cols)]
    for name, s in strat["per_group"].items():
        row = f"  {name:<12}" + f"{s['n']:>17}"
        row += "".join(f"{s[c]:>17.4f}" for c in cols[1:])
        out.append(row)
    out += ["", "  per-group gaps (best group minus worst):"]
    for metric, g in strat["gaps"].items():
        out.append(f"    {metric:<18} {g['gap']:+.4f}   (best {g['best']}, worst {g['worst']})")
    if size_cap is not None:
        out.append("")
        out.append(f"  reason-set size cap {size_cap}: " + "; ".join(
            f"{name} mean {s['reasons_used']:.2f} "
            f"{'within' if s['reasons_used'] <= size_cap else 'OVER'}"
            for name, s in strat["per_group"].items()))
    out += ["", "LIMITS OF THESE MEASUREMENTS", f"  {LIMITS}"]
    return "\n".join(out)
