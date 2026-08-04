"""Subset-minimal sufficient reasons, over the deletions an inference artefact admits.

What this module is for:
  `docs/sufficient-reasons.md` is the definition and this is the measurement of it. The reason-
  deletion certificate used to switch each reason off *alone*, which answers a question about single
  facts and reports an answer about reasons. Two reasons that are jointly necessary and individually
  removable defeat that: removing either alone leaves the engine's answer where it was, so both were
  reported `deleted` and the tool accused a system of omitting two reasons its inference
  demonstrably used. This module is what the certificate asks instead.

  The objects are Ignatiev, Narodytska and Marques-Silva's abductive explanation (AXp) and its
  contrastive dual (CXp), specialised to the one perturbation space `artifacts.InferenceArtifact`
  reaches — the *deletion lattice*, since the protocol has a `without(fact)` and deliberately no
  `with_(fact)`. A **CXp** is a subset-minimal set of facts whose joint removal moves the engine's
  answer; an **AXp** is a subset-minimal set of facts whose retention holds it, and the two are
  minimal hitting sets of each other (Reiter 1987; Ignatiev, Narodytska, Asher and Marques-Silva
  2020). A fact is **relevant** iff it lies in some CXp, which is the same as lying in some AXp.
  `docs/sufficient-reasons.md` §4 carries the lemmas and §9 the sources.

  The enumeration is the seed/shrink/grow MARCO loop of Liffiton, Previti, Malik and Marques-Silva,
  with Z3 as the oracle over the subset lattice — one Boolean per searchable fact, blocking clauses
  recording what has been covered — and the *engine* as the membership oracle, one probe per
  `moved()` call.

What a reader must not break:
  - **The two claims have different quantifiers, and the budget only ever weakens one of them.**
    That a fact is relevant is existential over CXps: one witness establishes it and a search that
    stopped early keeps every witness it found. That a fact is irrelevant is universal: it is
    established only by `exhaustive`, the map solver having gone unsatisfiable with every subset
    covered. So a caller may read `relevant` off a partial search and may read irrelevance off no
    search but an exhausted one.
    Why this matters: `deleted` is what drives a violated verdict. A shorter search must report
    *fewer* missing reasons and never more — there must be no setting of `budget` at which this
    instrument accuses a system it would otherwise have cleared.
  - **Every lemma the search rests on needs the artefact's monotonicity declaration and none of
    them is available without it.** Upward closure of `moved` is what makes a subset-minimal moving
    set a CXp at all, what makes the whole-space short circuit sound, and what lets the caller prune
    the facts a singleton probe already settled. The declaration `artifacts.InferenceArtifact`
    requires for a soundness reason is exactly the precondition this theory needs; it is one premise
    and not two.
    Why this matters: on an engine that is not monotone, `¬moved(space)` no longer implies
    `¬moved(D)` for every `D`, and the one-probe short circuit would report a complete enumeration
    having looked at one point.
  - **The budget is spent in probes and counted here, not estimated by the caller.** `probes` is the
    number of distinct deletion patterns the engine was actually re-run on; repeats are served from
    the cache and cost nothing.
    Why this matters: the count travels into `RequirementResult.details[PROBE_BUDGET_KEY]` under the
    discipline `PROBE_BUDGET_FIELDS` already forces, and a bound a reader cannot see is a bound that
    may as well not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["DEFAULT_PROBE_BUDGET", "DeletionSearch", "contrastive_sets"]

#: Engine re-runs one decision's joint search may spend before it gives up and reports a partial
#: enumeration. A whole-space probe settles a truncating engine in one (`docs/sufficient-reasons.md`
#: §4, Corollary 3), and the loop below costs on the order of `|space|` per contrastive set found,
#: so this is generous for the artefacts this package ships and finite for the ones it does not.
DEFAULT_PROBE_BUDGET = 256


class _BudgetSpent(Exception):
    """Raised inside the loop the moment a probe would exceed the budget, so a half-shrunk set is
    abandoned rather than recorded: a set that is moving but not yet minimal is not a CXp."""


@dataclass(frozen=True)
class DeletionSearch:
    """What the contrastive search saw, and how much of the lattice it got through."""

    #: The facts searched over. The caller prunes it; see `certificate.certify_artifact`.
    space: tuple[Any, ...]
    #: Every CXp found: a subset-minimal set of facts whose joint deletion moves the engine.
    contrastive: tuple[frozenset, ...]
    #: The union of them — the facts shown **relevant**. Sound whether or not the search finished.
    relevant: frozenset
    #: Whether the enumeration terminated. **Only** an exhaustive search licenses irrelevance.
    exhaustive: bool
    #: Distinct deletion patterns the engine was re-run on.
    probes: int
    #: The cap those probes were counted against.
    budget: int

    def to_dict(self) -> dict:
        return {
            "facts_searched": [str(f) for f in self.space],
            "contrastive_sets": [
                sorted(str(f) for f in c) for c in self.contrastive
            ],
            "relevant_facts": sorted(str(f) for f in self.relevant),
            "exhaustive": self.exhaustive,
            "probes": self.probes,
            "budget": self.budget,
        }


def contrastive_sets(
    moved: Callable[[frozenset], bool],
    space,
    *,
    budget: int = DEFAULT_PROBE_BUDGET,
) -> DeletionSearch:
    """Enumerate the CXps of one decision over `space`, within `budget` engine probes.

    `moved(D)` answers whether deleting exactly the facts `D` moves the engine's answer past the
    certificate's tolerance. It is assumed upward-closed — deleting more never un-moves an answer —
    which is what the artefact's monotonicity declaration asserts and what every step below needs.
    """
    space = tuple(space)
    cache: dict[frozenset, bool] = {}
    spent = 0

    def probe(facts) -> bool:
        nonlocal spent
        key = frozenset(facts)
        if key not in cache:
            if spent >= budget:
                raise _BudgetSpent
            spent += 1
            cache[key] = bool(moved(key))
        return cache[key]

    found: list[frozenset] = []
    exhaustive = True
    if space:
        try:
            # `docs/sufficient-reasons.md` §4, Corollary 3: if deleting everything does not move the
            # engine, upward closure says nothing does, so the enumeration is complete and empty.
            # This is the ordinary shape of a truncating engine and it costs one probe.
            if probe(space):
                found, exhaustive = _marco(probe, space)
        except _BudgetSpent:
            exhaustive = False

    return DeletionSearch(
        space=space,
        contrastive=tuple(found),
        relevant=frozenset().union(*found) if found else frozenset(),
        exhaustive=exhaustive,
        probes=spent,
        budget=budget,
    )


def _marco(probe, space) -> tuple[list[frozenset], bool]:
    """Seed / shrink / grow, with Z3 holding the unexplored region of the subset lattice.

    One Boolean per fact. A moved seed shrinks to a CXp and blocks its supersets; an unmoved seed
    grows to a maximal unmoved set — whose complement is an AXp — and blocks its subsets. The map
    going unsatisfiable means every subset is covered, so every CXp has been found.
    """
    import z3

    variable = {fact: z3.Bool(f"delete_{index}") for index, fact in enumerate(space)}
    unexplored = z3.Solver()
    found: list[frozenset] = []
    try:
        while unexplored.check() == z3.sat:
            model = unexplored.model()
            seed = frozenset(
                fact
                for fact in space
                if z3.is_true(model.eval(variable[fact], model_completion=True))
            )
            if probe(seed):
                core = _shrink(probe, seed)
                found.append(core)
                unexplored.add(z3.Or([z3.Not(variable[fact]) for fact in core]))
            else:
                maximal = _grow(probe, seed, space)
                unexplored.add(
                    z3.Or([variable[fact] for fact in space if fact not in maximal])
                )
    except _BudgetSpent:
        return found, False
    return found, True


def _shrink(probe, seed: frozenset) -> frozenset:
    """A moved set, reduced to a subset-minimal one: a CXp. Deterministic in `repr` order."""
    core = seed
    for fact in sorted(seed, key=repr):
        smaller = core - {fact}
        if smaller and probe(smaller):
            core = smaller
    return core


def _grow(probe, seed: frozenset, space) -> frozenset:
    """An unmoved set, extended to a maximal unmoved one: the complement of an AXp."""
    maximal = seed
    for fact in sorted((f for f in space if f not in seed), key=repr):
        larger = maximal | {fact}
        if not probe(larger):
            maximal = larger
    return maximal
