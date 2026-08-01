"""Probed engine for reasonsmith v0.2.

What this module is for:
  Evaluates logical requirements (`formalism = "logical"`) against a system that exposes no
  decision logic to reason over but does expose `decide()` — the opaque system the `proved`
  engine cannot reach and the `observed` engine can only watch. It searches for a
  counterexample by perturbing the inputs of the decisions the system already made and
  replaying them through `decide()`.

What a reader must not break:
  - Probed never rounds up to proved. "No counterexample within the budget" is a statement about
    a bounded search, not about the property, and it is reported at `Strength.PROBED` carrying
    the budget that produced it.
    Why this matters: the whole difference between this engine and the proved engine is that this
    one searched a finite set of inputs. A verdict that does not carry what was searched cannot be
    read for what it is worth, so `RequirementResult` refuses to construct a probed result whose
    `details` do not carry `probe_budget` (see `report.PROBE_BUDGET_FIELDS`) — the budget is a
    construction-time invariant, not a rendering convention.
  - The search MUST be reproducible: the same records, trials and seed replay the same inputs in
    the same order (`plan_inputs`), and the seed is part of the recorded budget.
    Why this matters: a report that names a budget nobody can re-derive attests to nothing.
  - A candidate counterexample MUST be replayed and seen to fail a second time before it is
    reported, and a candidate that does not reproduce is reported NOT EVALUATED, never violated.
    Why this matters: a system that answers differently on the same input has not been shown to
    violate anything; the finding would be a bug in this search reported as a breach of the duty.
  - A system exposing no `decide()`, a property this engine cannot parse, or a trace with no
    decision to perturb are all reported NOT EVALUATED (`verdict=INCONCLUSIVE`, `strength=None`),
    naming which of the three happened, and never `satisfied`.
    Why this matters: absent evidence is not evidence of compliance.
"""

from __future__ import annotations

import ast
import random
from collections.abc import Mapping
from typing import Any, Optional

from reasonsmith.report import PROBE_BUDGET_KEY, RequirementResult
from reasonsmith.rulelang import UnsupportedConstructError, eval_expression, parse_expression
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

__all__ = ["DEFAULT_SEED", "DEFAULT_TRIALS", "STRATEGY", "ProbedEngine", "plan_inputs"]

#: Inputs replayed by default. Chosen to finish in well under a second on the shipped demo:
#: a default an adopter waits minutes for is a default nobody runs.
DEFAULT_TRIALS = 200

#: The default seed. Fixed rather than drawn from the clock, so a run is reproducible unless the
#: caller deliberately asks for a different search.
DEFAULT_SEED = 0

#: What the search does, named on every result it produces.
STRATEGY = (
    "seeded random perturbation of the decisions in the trace: each replayed input is one "
    "recorded decision with one or two fields replaced by a value drawn from that field's "
    "candidate pool (the values the trace shows for it, the numeric literals of the property, "
    "and their immediate neighbours)"
)


def _spec_numbers(spec: str) -> set[float]:
    """The numeric literals the property compares against — the thresholds worth landing on."""
    try:
        tree = parse_expression(spec)
    except (SyntaxError, UnsupportedConstructError):
        return set()
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }


def _pools(req: Requirement, records: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Candidate values per field: the bounded input space this engine searches.

    A field whose values are of a kind this engine has no way to vary (an object, a nested
    structure) is left out entirely rather than perturbed into something the system never sees;
    the budget reports the fields that were in the space, so what was held fixed is readable.
    """
    literals = _spec_numbers(req.spec)
    pools: dict[str, list[Any]] = {}
    for field in sorted({key for rec in records for key in rec}):
        values = [rec[field] for rec in records if field in rec]
        candidates: set[Any] = set()
        if any(isinstance(v, bool) for v in values):
            candidates = {True, False}
        elif values and all(isinstance(v, (int, float)) for v in values):
            for value in values:
                candidates |= {value, value + 1, value - 1, -value, 0, value * 2}
            for literal in literals:
                candidates |= {literal, literal + 1, literal - 1}
        elif values and all(isinstance(v, str) for v in values):
            # The empty string is the edge worth having: a reason field the system leaves blank.
            candidates = set(values) | {""}
        else:
            continue
        pools[field] = sorted(candidates, key=repr)
    return pools


def _key(case: Mapping[str, Any]) -> tuple:
    """A hashable identity for a replayed input, so the same input is never paid for twice."""
    return tuple(sorted((str(k), repr(v)) for k, v in case.items()))


def plan_inputs(
    req: Requirement,
    records: list[dict[str, Any]],
    trials: int = DEFAULT_TRIALS,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """The exact inputs this engine replays, in order.

    Deterministic in `(req.spec, records, trials, seed)` and nothing else, which is what makes a
    reported budget re-derivable. The recorded decisions come first, unperturbed: a property the
    system already breaks on its own trace should not have to be searched for.
    """
    if trials <= 0 or not records:
        return []

    pools = _pools(req, records)
    fields = sorted(pools)
    rng = random.Random(seed)
    seen: set[tuple] = set()
    plan: list[dict[str, Any]] = []

    def offer(case: dict[str, Any]) -> None:
        key = _key(case)
        if key not in seen:
            seen.add(key)
            plan.append(case)

    for rec in records:
        offer(dict(rec))
        if len(plan) >= trials:
            return plan[:trials]

    if not fields:
        return plan[:trials]

    # Bounded so a small input space cannot spin here once every distinct input has been drawn.
    attempts_left = trials * 10
    while len(plan) < trials and attempts_left > 0:
        attempts_left -= 1
        case = dict(records[rng.randrange(len(records))])
        for field in rng.sample(fields, min(len(fields), rng.choice((1, 2)))):
            case[field] = rng.choice(pools[field])
        offer(case)

    return plan[:trials]


def _as_record(case: dict[str, Any], output: Any) -> dict[str, Any]:
    """The decision record a replay produced.

    A system that answers with a full record speaks for itself. One that answers with a bare
    label is read the way `CallableAdapter.decisions()` reads it — the input it was given plus
    the answer under `decision` — so this engine and the trace describe the same thing.
    """
    if isinstance(output, Mapping):
        return dict(output)
    record = dict(case)
    record["decision"] = output
    return record


class ProbedEngine:
    """Active falsification engine: perturb, replay, and look for a counterexample."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: Optional[list[dict[str, Any]]] = None,
        trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> RequirementResult:
        clause = f"{req.source_document} {req.article_clause}"

        def not_evaluated(summary: str, details: dict[str, Any]) -> RequirementResult:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=summary,
                details=details,
                binding=req.binding,
                scope=req.scope,
            )

        decide = getattr(sut, "decide", None)
        if not callable(decide):
            return not_evaluated(
                "Not evaluated: the system exposes no decide(), so there is nothing to replay a "
                "perturbed input against. Active falsification needs a system that can be run.",
                {"engine": "probed", "reason": "no_decide"},
            )

        try:
            spec_ast = parse_expression(req.spec)
        except (SyntaxError, UnsupportedConstructError) as exc:
            return not_evaluated(
                f"Not evaluated: property {req.spec!r} is not expressible for this engine: {exc}",
                {"engine": "probed", "reason": "property_not_expressible", "error": str(exc)},
            )

        trace = list(records) if records is not None else list(sut.decisions())
        for rec in trace:
            if not isinstance(rec, Mapping):
                return not_evaluated(
                    "Not evaluated: the decision trace holds a "
                    f"{type(rec).__name__} where a decision record was expected, so there is no "
                    "decision to generate inputs around.",
                    {"engine": "probed", "reason": "malformed_trace"},
                )
        trace = [dict(rec) for rec in trace]

        plan = plan_inputs(req, trace, trials=trials, seed=seed)
        if not plan:
            return not_evaluated(
                "Not evaluated: the search could not run — the decision trace holds no decision "
                "to generate inputs around, so nothing was perturbed and nothing was replayed.",
                {"engine": "probed", "reason": "no_seed_decisions", "records_observed": len(trace)},
            )

        pools = _pools(req, trace)
        input_space = {field: len(values) for field, values in pools.items()}

        def budget(replayed: int, errored: int) -> dict[str, Any]:
            return {
                "trials": replayed,
                "trials_requested": trials,
                "strategy": STRATEGY,
                "seed": seed,
                "seed_decisions": len(trace),
                "input_space": input_space,
                "inputs_errored": errored,
            }

        def holds(record: dict[str, Any]) -> bool:
            return bool(eval_expression(spec_ast, dict(record)))

        errored = 0
        first_error = ""
        for index, case in enumerate(plan):
            try:
                record = _as_record(case, decide(case))
                satisfied = holds(record)
            except Exception as exc:  # the system, or the property, has nothing to say here
                errored += 1
                first_error = first_error or f"{type(exc).__name__}: {exc}"
                continue

            if satisfied:
                continue

            # Verify before reporting: a candidate that does not fail a second time is a defect in
            # this search, not a finding about the system.
            try:
                replay = _as_record(case, decide(case))
                reproduced = not holds(replay)
                replay_note = ""
            except Exception as exc:
                reproduced = False
                replay_note = f" Replay raised {type(exc).__name__}: {exc}."

            if not reproduced:
                return not_evaluated(
                    f"Not evaluated: input {case} failed property {req.spec!r} once but did not "
                    f"reproduce when replayed against the system's own decide().{replay_note} A "
                    "counterexample that does not reproduce is a defect in this search, not a "
                    "violation, and is never reported as one.",
                    {
                        "engine": "probed",
                        "reason": "counterexample_did_not_reproduce",
                        "unverified_counterexample": case,
                        PROBE_BUDGET_KEY: budget(index + 1, errored),
                    },
                )

            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.VIOLATED,
                strength=Strength.PROBED,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Violated under active perturbation: replaying input {case} through the "
                    f"system's own decide() produced a decision that fails {req.spec!r}, and the "
                    "counterexample reproduced when replayed a second time."
                ),
                details={
                    "engine": "probed",
                    "counterexample": case,
                    "counterexample_decision": record,
                    "verification": (
                        "Counterexample replayed against the system's own decide() and failed the "
                        "property again."
                    ),
                    PROBE_BUDGET_KEY: budget(index + 1, errored),
                },
                binding=req.binding,
                scope=req.scope,
            )

        if errored == len(plan):
            return not_evaluated(
                f"Not evaluated: the search could not run — every one of the {len(plan)} replayed "
                f"inputs raised rather than producing a decision this property could be read "
                f"over. First failure: {first_error}",
                {
                    "engine": "probed",
                    "reason": "every_replay_failed",
                    "error": first_error,
                    PROBE_BUDGET_KEY: budget(len(plan), errored),
                },
            )

        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.SATISFIED,
            strength=Strength.PROBED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Probed: no counterexample to {req.spec!r} in {len(plan)} input(s) replayed "
                f"through the system's own decide() (seed {seed}, generated by perturbing "
                f"{len(trace)} recorded decision(s) over {len(input_space)} field(s)). This is a "
                "bounded search, not a proof: the property is unchecked outside the inputs this "
                "budget names."
            ),
            details={
                "engine": "probed",
                PROBE_BUDGET_KEY: budget(len(plan), errored),
            },
            binding=req.binding,
            scope=req.scope,
        )
