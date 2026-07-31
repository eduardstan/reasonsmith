"""The evidence strength lattice and verdict vocabulary for reasonsmith.

What this module is for:
  Defines the formal evidence strength lattice (`unattainable < observed < probed < proved`) and
  the verdict vocabulary (`satisfied`, `violated`, `inconclusive`, `not_applicable`) for compliance
  checking. Compliance claims carry both a verdict (whether a property holds) and a strength
  (how deeply the system exposed itself for verification).

  Strengths form a strict total order (the strength lattice):
    unattainable — The system cannot discharge the requirement as built (missing signals).
    observed     — The property holds over passive decision traces (monitors / record checks).
    probed       — The property holds under active perturbation/replay.
    proved       — The property holds for all inputs via formal reasoning / solver proof.

  Verdicts record whether a property is met:
    satisfied    — Evidence proves or demonstrates the requirement holds.
    violated     — Evidence demonstrates a counterexample or breach.
    inconclusive — Evidence is insufficient, incomplete, or unattainable.

  Lineage & Section 6.3 Scope Statements:
    The strength lattice is the operational form of Section 6.3's scope statement ("Governance,
    Monitoring, and What to Record", Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:24).
    Section 6.3 asks whether an explanation "approximates or guarantees" behavior — which is
    precisely the observed / proved distinction, with probed between them and unattainable as
    the case the paper does not name: a system that cannot produce the required record at all.

What a reader must not break:
  - Do not alter the strict total order of the strength lattice
    (`UNATTAINABLE < OBSERVED < PROBED < PROVED`).
    Why this matters: Order guarantees that weaker passive evidence can never masquerade as
    active probing or formal proof.
  - `RequirementResult` refuses to construct a result claiming more than it has (including
    `strength=None` for "no engine here evaluated this", which is deliberately not a strength on
    the lattice).
    Why this matters: Prevents un-evaluated or un-measured checks from being counted as satisfied
    or silently assigned a strength tier.
  - Nothing in this module asserts legal compliance or guarantees correctness beyond the formal
    bounds of the evidence provided.
    Why this matters: Technical checks measure evidence records against specifications, not legal
    counsel or guarantees.
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
    """Verdict on whether a requirement is satisfied.

    NOT_APPLICABLE is a statement about the duty's reach, not about the system: the
    requirement is limited to a regulatory class the system is not declared to be in, so it
    was never checked. It is deliberately distinct from INCONCLUSIVE, which says a duty that
    does reach the system was not resolved.
    """

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
      3. Else if every verdict is NOT_APPLICABLE, the combined result is NOT_APPLICABLE.
      4. Else all remaining verdicts are SATISFIED or NOT_APPLICABLE, and the combined
         result is SATISFIED.
      5. An empty collection returns INCONCLUSIVE.

    Rule 3 stops one out-of-scope sub-property turning the whole into a claim that nothing
    applies; rule 4 lets the sub-properties that *were* checked carry the verdict.

    Rule 5 is deliberately *not* vacuous truth. Logically an empty conjunction is
    true, but a conformance verdict is a claim about evidence, and having checked
    nothing is not evidence that a requirement holds. Returning SATISFIED here
    would let a run that evaluated no sub-property report as compliant, which is
    the one failure mode this tool must never have.
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
