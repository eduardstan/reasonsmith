"""Conservative statistical measurements over an explicitly declared sample.

This module deliberately produces measurements, never conformance verdicts.  A sampling plan is
an input supplied by the auditor; it is never inferred from a system or from the records.  The
first-wave estimator is a simultaneous Clopper--Pearson construction for fixed groups and an iid
Bernoulli outcome within each group.  Its ratio interval is a monotone outer enclosure, not a
second kind of confidence interval.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

STATISTICAL_MEASUREMENT_KEY = "statistical_measurement"
STATISTICAL_LIMIT_KEY = "proxy_blindness_limit"
PROXY_BLINDNESS_LIMIT = (
    "This is an association in selection rates for the explicitly recorded group and outcome "
    "under the declared sampling model. It does not detect a proxy, causal discrimination, "
    "intersectional interactions not named by the duty, disparate treatment, applicant "
    "discouragement, or selection-error criteria requiring ground truth; it does not establish "
    "that the sample is representative or that the authority's legal standard is discharged."
)
SAMPLING_REQUIRED_FIELDS = (
    "target_population",
    "eligibility",
    "unit_of_observation",
    "inclusion_mechanism",
    "design",
    "independence",
    "group_definition",
    "missingness",
    "time_window",
    "weights",
    "clustering",
)
AUTHORITY_REQUIRED_FIELDS = (
    "authority",
    "citation",
    "official_url",
    "api_endpoint",
    "retrieval_timestamp",
    "quoted_passage",
    "source_hash",
    "scope",
)
THRESHOLD_REQUIRED_FIELDS = ("value", "meaning", "comparison")


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Numerically stable continued fraction for the regularized beta function."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 3e-30:
        d = 3e-30
    d = 1.0 / d
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 3e-30:
            d = 3e-30
        c = 1.0 + aa / c
        if abs(c) < 3e-30:
            c = 3e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 3e-30:
            d = 3e-30
        c = 1.0 + aa / c
        if abs(c) < 3e-30:
            c = 3e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log1p(-x) - log_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _beta_quantile(probability: float, a: float, b: float) -> float:
    if not 0.0 < probability < 1.0:
        return 0.0 if probability <= 0 else 1.0
    lo, hi = 0.0, 1.0
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if _regularized_beta(a, b, mid) < probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def clopper_pearson(x: int, n: int, alpha: float) -> tuple[float, float]:
    """Return the two-sided exact binomial interval at error level ``alpha``."""
    if (
        isinstance(x, bool)
        or isinstance(n, bool)
        or not isinstance(x, int)
        or not isinstance(n, int)
    ):
        raise TypeError("x and n must be integers")
    if n <= 0 or x < 0 or x > n:
        raise ValueError(f"require 0 <= x <= n and n > 0, got x={x}, n={n}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha!r}")
    lower = 0.0 if x == 0 else _beta_quantile(alpha / 2.0, x, n - x + 1)
    upper = 1.0 if x == n else _beta_quantile(1.0 - alpha / 2.0, x + 1, n - x)
    return lower, upper


def ratio_enclosure(intervals: Mapping[str, Sequence[float]]) -> tuple[float, float]:
    """Enclose min(rate)/max(rate) from simultaneous per-group intervals."""
    if not intervals:
        raise ValueError("at least one group interval is required")
    lows, highs = [], []
    for group, interval in intervals.items():
        if len(interval) != 2:
            raise ValueError(f"interval for {group!r} must have two endpoints")
        low, high = float(interval[0]), float(interval[1])
        if not 0.0 <= low <= high <= 1.0:
            raise ValueError(f"invalid interval for {group!r}: {interval!r}")
        lows.append(low)
        highs.append(high)
    denominator = max(highs)
    if denominator == 0.0:
        raise ValueError("the population denominator is not identified: every upper bound is zero")
    lower = min(lows) / denominator
    max_lower = max(lows)
    upper = 1.0 if max_lower == 0.0 else min(1.0, min(highs) / max_lower)
    return lower, upper


def validate_sampling_plan(plan: Mapping[str, Any] | None) -> tuple[bool, str]:
    if plan is None:
        return False, "records supplied; no probability sampling model was declared"
    if not isinstance(plan, Mapping):
        raise TypeError("sampling_assumption must be a mapping")
    status = plan.get("status")
    if status == "absent":
        return False, str(plan.get("description") or "no probability sampling model was declared")
    missing = [name for name in SAMPLING_REQUIRED_FIELDS if plan.get(name) in (None, "")]
    if missing:
        raise ValueError("sampling plan is incomplete; missing " + ", ".join(missing))
    if plan.get("design") not in (
        "iid_binomial",
        "fixed_group_counts_iid",
        "simple_random_sampling",
    ):
        raise ValueError("first-wave sampling plan must declare an iid binomial-compatible design")
    if plan.get("weights") not in (False, None, "none", "not_used"):
        raise ValueError("weights are not supported by the first-wave estimator")
    if plan.get("clustering") not in (False, None, "none", "not_used"):
        raise ValueError("clustering is not supported by the first-wave estimator")
    return True, ""


def _authority_complete(authority: Mapping[str, Any] | None) -> bool:
    if authority is None:
        return False
    if not isinstance(authority, Mapping):
        raise TypeError("authority_provenance must be a mapping")
    required = ("authority", "citation", "retrieval_timestamp", "scope")
    missing = [name for name in required if not str(authority.get(name, "")).strip()]
    if not any(
        str(authority.get(name, "")).strip()
        for name in ("official_url", "api_endpoint", "official_api_endpoint")
    ):
        missing.append("official_url or api_endpoint")
    if not any(
        str(authority.get(name, "")).strip()
        for name in ("quoted_passage", "source_hash", "quote_hash")
    ):
        missing.append("quoted_passage or source_hash")
    if missing:
        raise ValueError("authority provenance is incomplete; missing " + ", ".join(missing))
    return True


def validate_measurement_payload(
    payload: Mapping[str, Any], *, future_verdict: bool = False
) -> None:
    """Validate the closed shape carried in ``details[STATISTICAL_MEASUREMENT_KEY]``."""
    if not isinstance(payload, Mapping):
        raise TypeError("statistical measurement must be a mapping")
    required = (
        "groups",
        "sampling_assumption",
        "counts",
        "metric",
        "confidence",
        "threshold",
        "authority_provenance",
        "decision_rule",
        "status",
        "refusal",
        STATISTICAL_LIMIT_KEY,
    )
    missing = [f for f in required if f not in payload]
    if missing:
        raise ValueError("statistical measurement is missing " + ", ".join(missing))
    groups = payload["groups"]
    if isinstance(groups, (str, bytes)) or not isinstance(groups, Sequence) or not groups:
        raise ValueError("statistical measurement groups must be a non-empty sequence")
    if len(set(groups)) != len(groups):
        raise ValueError("statistical measurement groups must be unique")
    counts = payload["counts"]
    if payload.get("status") == "refused" and counts == {} and payload.get("n") == 0:
        counts = None
    if counts is not None and (not isinstance(counts, Mapping) or set(counts) != set(groups)):
        raise ValueError("per-group counts must name exactly the fixed groups")
    counts_map: Mapping[Any, Any] = counts if counts is not None else {}
    total = 0
    for group in groups if counts is not None else ():
        row = counts_map[group]
        if not isinstance(row, Mapping):
            raise ValueError(f"counts for {group!r} must carry integer n and successes")
        n, successes = row.get("n"), row.get("successes")
        if (
            isinstance(n, bool)
            or isinstance(successes, bool)
            or not isinstance(n, int)
            or not isinstance(successes, int)
            or n <= 0
            or not 0 <= successes <= n
        ):
            raise ValueError(f"invalid counts for {group!r}")
        total += n
    if counts is not None and payload.get("n") != total:
        raise ValueError("n must reconcile exactly to the per-group counts")
    metric = payload["metric"]
    if not isinstance(metric, Mapping):
        raise ValueError("metric must be a mapping")
    rates = metric.get("rates")
    if isinstance(rates, Mapping):
        for group in groups:
            rate = rates.get(group)
            if (
                rate is None
                or isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(float(rate))
                or not 0 <= float(rate) <= 1
            ):
                raise ValueError(f"invalid point estimate for {group!r}")
    if payload["decision_rule"] is not None:
        raise ValueError("first-wave statistical measurements require decision_rule=null")
    if payload[STATISTICAL_LIMIT_KEY] != PROXY_BLINDNESS_LIMIT:
        raise ValueError("every statistical measurement must carry the proxy-blindness limit")
    plan_ok, _ = validate_sampling_plan(payload["sampling_assumption"])
    if plan_ok:
        confidence = payload["confidence"]
        if not isinstance(confidence, Mapping) or not 0.0 < float(confidence.get("level", 0)) < 1.0:
            raise ValueError("a declared sampling plan requires a confidence level in (0, 1)")
        if confidence.get("interval_method") != "clopper_pearson_simultaneous_bonferroni":
            raise ValueError(
                "the first-wave interval method is Clopper-Pearson with Bonferroni allocation"
            )
    if future_verdict and (payload["threshold"] is None or payload["authority_provenance"] is None):
        raise ValueError("a future statistical verdict requires authority and threshold provenance")
    if payload["threshold"] is not None:
        if not isinstance(payload["threshold"], Mapping) or any(
            payload["threshold"].get(k) is None for k in THRESHOLD_REQUIRED_FIELDS
        ):
            raise ValueError("threshold must carry value, meaning and comparison")
    if payload["authority_provenance"] is not None:
        _authority_complete(payload["authority_provenance"])


def measure_selection_rates(
    records: Iterable[Mapping[str, Any]],
    *,
    groups: Sequence[str],
    group_field: str,
    outcome_field: str,
    sampling_assumption: Mapping[str, Any] | None = None,
    confidence_level: float = 0.95,
    authority_provenance: Mapping[str, Any] | None = None,
    threshold: Mapping[str, Any] | None = None,
    unit_field: str | None = None,
) -> dict[str, Any]:
    """Compute the first-wave descriptive/CP measurement from raw records."""
    groups = tuple(groups)
    if not groups or len(set(groups)) != len(groups):
        raise ValueError("groups must be a non-empty sequence of unique names")
    rows = list(records)
    counts = {group: {"n": 0, "successes": 0} for group in groups}
    seen: set[Any] = set()
    for row in rows:
        if group_field not in row or outcome_field not in row:
            raise ValueError("every record must carry raw group and outcome values")
        group = row[group_field]
        if group not in counts:
            raise ValueError(f"record uses undeclared group {group!r}")
        if unit_field is not None:
            if unit_field not in row:
                raise ValueError("every record must carry the declared unit identifier")
            unit = row[unit_field]
            if unit in seen:
                raise ValueError(f"duplicate unit {unit!r}")
            seen.add(unit)
        outcome = row[outcome_field]
        if isinstance(outcome, bool):
            value = int(outcome)
        elif isinstance(outcome, int) and outcome in (0, 1):
            value = outcome
        else:
            raise ValueError("outcome must be binary 0/1")
        counts[group]["n"] += 1
        counts[group]["successes"] += value
    empty = [g for g, value in counts.items() if value["n"] == 0]
    if empty:
        raise ValueError("every declared group must have at least one record: " + ", ".join(empty))
    plan_ok, plan_reason = validate_sampling_plan(sampling_assumption)
    rates = {g: value["successes"] / value["n"] for g, value in counts.items()}
    maximum = max(rates.values())
    point_ratio = None if maximum == 0 else min(rates.values()) / maximum
    intervals: dict[str, list[float]] | None = None
    ratio_interval: list[float] | None = None
    if plan_ok:
        if not 0.0 < confidence_level < 1.0:
            raise ValueError("confidence_level must lie in (0, 1)")
        alpha_group = (1.0 - confidence_level) / len(groups)
        intervals = {
            g: list(clopper_pearson(value["successes"], value["n"], alpha_group))
            for g, value in counts.items()
        }
        try:
            ratio_interval = list(ratio_enclosure(intervals))
        except ValueError:
            ratio_interval = None
    complete_authority = (
        False if authority_provenance is None else _authority_complete(authority_provenance)
    )
    status = (
        "measurement"
        if plan_ok and complete_authority
        else ("measurement_no_authority" if plan_ok else "descriptive_only")
    )
    refusal = None if plan_ok and complete_authority else (None if plan_ok else plan_reason)
    if plan_ok and not complete_authority:
        refusal = (
            "no named authority provenance; the interval is not a legal or conformance decision"
        )
    payload = {
        "groups": list(groups),
        "sampling_assumption": dict(sampling_assumption)
        if sampling_assumption is not None
        else {"status": "absent", "description": plan_reason},
        "n": sum(v["n"] for v in counts.values()),
        "counts": counts,
        "metric": {
            "formula": "min_g(p_hat_g) / max_h(p_hat_h)",
            "group_field": group_field,
            "outcome_field": outcome_field,
            "rates": rates,
            "point_estimate": point_ratio,
            "denominator_status": "identified" if maximum else "not_identified",
        },
        "confidence": {
            "level": confidence_level if plan_ok else None,
            "interval_method": "clopper_pearson_simultaneous_bonferroni" if plan_ok else None,
            "tail_allocation": "alpha/(2G) per tail" if plan_ok else None,
            "intervals": intervals,
            "ratio_interval": ratio_interval,
        },
        "threshold": dict(threshold) if threshold is not None else None,
        "authority_provenance": dict(authority_provenance)
        if authority_provenance is not None
        else None,
        "decision_rule": None,
        "status": status,
        "refusal": refusal,
        STATISTICAL_LIMIT_KEY: PROXY_BLINDNESS_LIMIT,
    }
    validate_measurement_payload(payload)
    return payload
