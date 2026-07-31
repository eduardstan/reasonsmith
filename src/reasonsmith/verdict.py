"""The evidence strength lattice and verdict vocabulary for reasonsmith.

Compliance claims carry both a verdict (whether a property holds) and a strength
(how deeply the system exposed itself for verification).

Strengths form a strict total order (the strength lattice):
  unattainable < observed < probed < proved

  unattainable — The system cannot discharge the requirement as built (missing signals).
  observed     — The property holds over passive decision traces (monitors / record checks).
  probed       — The property holds under active perturbation/replay.
  proved       — The property holds for all inputs via formal reasoning / solver proof.

Lineage & Section 6.3 Scope Statements:
  The strength lattice is the operational form of Section 6.3's scope statement ("Governance,
  Monitoring, and What to Record", Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:24).
  Section 6.3 asks whether an explanation "approximates or guarantees" behavior — which is
  precisely the observed / proved distinction, with probed between them and unattainable as
  the case the paper does not name: a system that cannot produce the required record at all.

Verdicts record whether a property is met:
  satisfied    — Evidence proves or demonstrates the requirement holds.
  violated     — Evidence demonstrates a counterexample or breach.
  inconclusive — Evidence is insufficient, incomplete, or unattainable.

Nothing in this module asserts legal compliance or guarantees correctness beyond the
formal bounds of the evidence provided.
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering
from typing import Iterable


@total_ordering
class Strength(Enum):
    """Evidence strength in the reasonsmith lattice."""

    UNATTAINABLE = "unattainable"
    OBSERVED = "observed"
    PROBED = "probed"
    PROVED = "proved"

    @property
    def rank(self) -> int:
        ranks = {
            "unattainable": 0,
            "observed": 1,
            "probed": 2,
            "proved": 3,
        }
        return ranks[self.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Strength):
            return NotImplemented
        return self.rank < other.rank

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: str | Strength) -> Strength:
        if isinstance(value, cls):
            return value
        val_lower = str(value).strip().lower()
        for member in cls:
            if member.value == val_lower:
                return member
        raise ValueError(f"Unknown strength {value!r}; valid: {[m.value for m in cls]}")


class Verdict(Enum):
    """Verdict on whether a requirement is satisfied."""

    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: str | Verdict) -> Verdict:
        if isinstance(value, cls):
            return value
        val_lower = str(value).strip().lower().replace(" ", "_")
        for member in cls:
            if member.value == val_lower:
                return member
        raise ValueError(f"Unknown verdict {value!r}; valid: {[m.value for m in cls]}")


def combine_verdicts(verdicts: Iterable[Verdict | str]) -> Verdict:
    """Combine multiple verdicts using worst-case propagation.

    Rules:
      1. If any verdict is VIOLATED, the combined result is VIOLATED.
      2. Else if any verdict is INCONCLUSIVE, the combined result is INCONCLUSIVE.
      3. Else if all verdicts are NOT_APPLICABLE, the combined result is NOT_APPLICABLE.
      4. Else if all non-NOT_APPLICABLE verdicts are SATISFIED, the combined result is SATISFIED.
      5. An empty collection returns INCONCLUSIVE.
    """
    v_list = [Verdict.parse(v) for v in verdicts]
    if not v_list:
        return Verdict.INCONCLUSIVE
    if any(v == Verdict.VIOLATED for v in v_list):
        return Verdict.VIOLATED
    if any(v == Verdict.INCONCLUSIVE for v in v_list):
        return Verdict.INCONCLUSIVE
    if all(v == Verdict.NOT_APPLICABLE for v in v_list):
        return Verdict.NOT_APPLICABLE
    return Verdict.SATISFIED


def min_strength(strengths: Iterable[Strength | str]) -> Strength:
    """Return the weakest strength in a collection (weakest-link principle).

    An empty collection raises ValueError.
    """
    s_list = [Strength.parse(s) for s in strengths]
    if not s_list:
        raise ValueError("Cannot compute min_strength of an empty collection")
    return min(s_list)


def max_strength(strengths: Iterable[Strength | str]) -> Strength:
    """Return the strongest strength in a collection.

    An empty collection raises ValueError.
    """
    s_list = [Strength.parse(s) for s in strengths]
    if not s_list:
        raise ValueError("Cannot compute max_strength of an empty collection")
    return max(s_list)
