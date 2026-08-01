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
import copy
import random
from collections.abc import Callable, Iterable, Mapping
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
    "the recorded decisions are replayed first unmodified; remaining inputs use seeded random "
    "perturbation of one recorded decision, replacing one or two fields with values drawn from "
    "that field's candidate pool (the values the trace shows for it, the numeric literals of "
    "the property, and their immediate neighbours)"
)


def _require_kind(kind: str, expected: str, node: ast.AST) -> None:
    if kind not in (expected, "unknown"):
        raise UnsupportedConstructError(
            f"{ast.unparse(node)!r} has type {kind}, expected {expected}"
        )


def _expression_kind(node: ast.AST) -> str:
    if isinstance(node, ast.Expression):
        return _expression_kind(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "boolean"
        if isinstance(node.value, (int, float)):
            return "number"
        if isinstance(node.value, str):
            return "string"
        raise UnsupportedConstructError(
            f"Unsupported constant type {type(node.value).__name__}: {node.value!r}"
        )

    if isinstance(node, ast.Name):
        return "unknown"

    if isinstance(node, ast.UnaryOp):
        operand_kind = _expression_kind(node.operand)
        if isinstance(node.op, ast.Not):
            _require_kind(operand_kind, "boolean", node.operand)
            return "boolean"
        if isinstance(node.op, (ast.USub, ast.UAdd)):
            _require_kind(operand_kind, "number", node.operand)
            return "number"
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left_kind = _expression_kind(node.left)
        right_kind = _expression_kind(node.right)
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            raise UnsupportedConstructError(
                f"Unsupported binary operator: {type(node.op).__name__}"
            )
        _require_kind(left_kind, "number", node.left)
        _require_kind(right_kind, "number", node.right)
        return "number"

    if isinstance(node, ast.BoolOp):
        kinds = [_expression_kind(value) for value in node.values]
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise UnsupportedConstructError(
                f"Unsupported boolean operator: {type(node.op).__name__}"
            )
        for value, kind in zip(node.values, kinds, strict=True):
            _require_kind(kind, "boolean", value)
        return "boolean"

    if isinstance(node, ast.Compare):
        _expression_kind(node.left)
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            _expression_kind(comparator)
            if not isinstance(operator, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                raise UnsupportedConstructError(
                    f"Unsupported comparison: {type(operator).__name__}"
                )
        return "boolean"

    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if node.keywords:
            raise UnsupportedConstructError(
                f"Keyword arguments are unsupported: {ast.unparse(node)!r}"
            )
        kinds = [_expression_kind(argument) for argument in node.args]
        if name in ("implies", "Implies"):
            if len(kinds) != 2:
                raise UnsupportedConstructError(f"{name} expects 2 argument(s), got {len(kinds)}")
            for argument, kind in zip(node.args, kinds, strict=True):
                _require_kind(kind, "boolean", argument)
            return "boolean"
        if name in ("abs", "min", "max"):
            expected = 1 if name == "abs" else 2
            if len(kinds) != expected:
                raise UnsupportedConstructError(
                    f"{name} expects {expected} argument(s), got {len(kinds)}"
                )
            for argument, kind in zip(node.args, kinds, strict=True):
                _require_kind(kind, "number", argument)
            return "number"
        raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def _validate_property(node: ast.Expression, spec: str) -> None:
    if _expression_kind(node) not in ("boolean", "unknown"):
        raise UnsupportedConstructError(f"Requirement spec {spec!r} is not a boolean property")


def _value_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "unknown"


def _property_names(node: ast.AST) -> tuple[str, ...]:
    function_nodes = {
        id(call.func)
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }
    return tuple(
        sorted(
            {
                name.id
                for name in ast.walk(node)
                if isinstance(name, ast.Name) and id(name) not in function_nodes
            }
        )
    )


def _trace_field_kinds(
    node: ast.AST, records: list[dict[str, Any]]
) -> tuple[dict[str, str], tuple[str, ...]]:
    established: dict[str, str] = {}
    unestablished = []
    for name in _property_names(node):
        observed = {_value_kind(record[name]) for record in records if name in record}
        if len(observed) == 1 and "unknown" not in observed:
            established[name] = observed.pop()
        else:
            unestablished.append(name)
    return established, tuple(unestablished)


def _operand_kind(node: ast.AST, field_kinds: Mapping[str, str]) -> str:
    if isinstance(node, ast.Name):
        return field_kinds.get(node.id, "unknown")
    return _expression_kind(node)


def _validate_trace_kinds(node: ast.Expression, field_kinds: Mapping[str, str]) -> None:
    boolean_positions: list[ast.AST] = []
    if isinstance(node.body, ast.Name):
        boolean_positions.append(node.body)
    for current in ast.walk(node):
        if isinstance(current, ast.UnaryOp) and isinstance(current.op, ast.Not):
            boolean_positions.append(current.operand)
        elif isinstance(current, ast.BoolOp):
            boolean_positions.extend(current.values)
        elif isinstance(current, ast.Call):
            name = current.func.id if isinstance(current.func, ast.Name) else ""
            if name in ("implies", "Implies"):
                boolean_positions.extend(current.args)

    for position in boolean_positions:
        if not isinstance(position, ast.Name):
            continue
        kind = field_kinds.get(position.id, "unknown")
        if kind not in ("boolean", "unknown"):
            raise UnsupportedConstructError(
                f"Field {position.id!r} is used in Boolean position, but the trace establishes "
                f"its kind as {kind}"
            )

    for comparison in (item for item in ast.walk(node) if isinstance(item, ast.Compare)):
        left = comparison.left
        left_kind = _operand_kind(left, field_kinds)
        for operator, right in zip(comparison.ops, comparison.comparators, strict=True):
            right_kind = _operand_kind(right, field_kinds)
            known = left_kind != "unknown" and right_kind != "unknown"
            ordered = isinstance(operator, (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            compatible = left_kind == right_kind and (
                not ordered or left_kind in ("number", "string")
            )
            if known and not compatible:
                operator_text = {
                    ast.Eq: "==",
                    ast.NotEq: "!=",
                    ast.Lt: "<",
                    ast.LtE: "<=",
                    ast.Gt: ">",
                    ast.GtE: ">=",
                }[type(operator)]
                raise UnsupportedConstructError(
                    f"Comparison {ast.unparse(left)!r} {operator_text} "
                    f"{ast.unparse(right)!r} has incompatible established kinds "
                    f"{left_kind} and {right_kind}"
                )
            left = right
            left_kind = right_kind


def _shared_mutable_path(
    original: Any,
    cloned: Any,
    path: str = "input",
    seen: Optional[set[tuple[int, int]]] = None,
) -> str | None:
    if isinstance(original, (type(None), bool, int, float, complex, str, bytes)):
        return None
    if seen is None:
        seen = set()
    pair = (id(original), id(cloned))
    if pair in seen:
        return None
    seen.add(pair)
    if isinstance(original, Mapping) and isinstance(cloned, Mapping):
        if original is cloned:
            return path
        for key, value in original.items():
            if key in cloned:
                cloned_key = next((candidate for candidate in cloned if candidate == key), key)
                shared_key = _shared_mutable_path(
                    key, cloned_key, f"{path}.key[{key!r}]", seen
                )
                if shared_key:
                    return shared_key
                shared = _shared_mutable_path(value, cloned[key], f"{path}[{key!r}]", seen)
                if shared:
                    return shared
        return None
    if isinstance(original, (list, tuple)) and isinstance(cloned, (list, tuple)):
        if isinstance(original, list) and original is cloned:
            return path
        for index, (value, copied) in enumerate(zip(original, cloned, strict=True)):
            shared = _shared_mutable_path(value, copied, f"{path}[{index}]", seen)
            if shared:
                return shared
        return None
    if isinstance(original, (set, frozenset)) and isinstance(cloned, (set, frozenset)):
        if isinstance(original, set) and original is cloned:
            return path
        for value in original:
            for copied in cloned:
                if value is copied:
                    shared = _shared_mutable_path(value, copied, f"{path}{{{value!r}}}", seen)
                    if shared:
                        return shared
        return None
    if hasattr(original, "__dict__") and hasattr(cloned, "__dict__"):
        return _shared_mutable_path(vars(original), vars(cloned), f"{path}.__dict__", seen)
    slots = getattr(type(original), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    for slot in slots:
        if hasattr(original, slot) and hasattr(cloned, slot):
            shared = _shared_mutable_path(
                getattr(original, slot),
                getattr(cloned, slot),
                f"{path}.{slot}",
                seen,
            )
            if shared:
                return shared
    return path if original is cloned else None


def _clone_case(case: dict[str, Any]) -> dict[str, Any]:
    cloned = copy.deepcopy(case)
    shared = _shared_mutable_path(case, cloned)
    if shared:
        raise TypeError(f"deep copy retained a shared mutable value at {shared}")
    return cloned


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
        *,
        trace_provider: Callable[[], Iterable[dict[str, Any]]] | None = None,
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
            _validate_property(spec_ast, req.spec)
        except (SyntaxError, UnsupportedConstructError) as exc:
            return not_evaluated(
                f"Not evaluated: property {req.spec!r} is not expressible for this engine: {exc}",
                {"engine": "probed", "reason": "property_not_expressible", "error": str(exc)},
            )

        if trials <= 0:
            return not_evaluated(
                f"Not evaluated: the probe trial budget must be positive; got {trials}, so the "
                "search was not run.",
                {
                    "engine": "probed",
                    "reason": "invalid_trial_budget",
                    "trials_requested": trials,
                },
            )

        try:
            if records is not None:
                trace = list(records)
            else:
                provider = trace_provider or sut.decisions
                trace = list(provider())
        except Exception as exc:
            return not_evaluated(
                "Not evaluated: the decision trace could not be acquired, so there was no "
                f"search space to probe. {type(exc).__name__}: {exc}",
                {
                    "engine": "probed",
                    "reason": "trace_acquisition_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
        for rec in trace:
            if not isinstance(rec, Mapping):
                return not_evaluated(
                    "Not evaluated: the decision trace holds a "
                    f"{type(rec).__name__} where a decision record was expected, so there is no "
                    "decision to generate inputs around.",
                    {"engine": "probed", "reason": "malformed_trace"},
                )
        trace = [dict(rec) for rec in trace]

        field_kinds, unestablished_kinds = _trace_field_kinds(spec_ast, trace)
        try:
            _validate_trace_kinds(spec_ast, field_kinds)
        except UnsupportedConstructError as exc:
            return not_evaluated(
                f"Not evaluated: property {req.spec!r} is not expressible for this engine: {exc}",
                {
                    "engine": "probed",
                    "reason": "property_not_expressible",
                    "error": str(exc),
                },
            )

        kind_limit = ""
        if unestablished_kinds:
            kind_limit = (
                " Trace did not establish kinds for property field(s) "
                f"{', '.join(unestablished_kinds)}; validation remained permissive for those "
                "fields."
            )

        try:
            plan = plan_inputs(req, trace, trials=trials, seed=seed)
            pools = _pools(req, trace)
            input_space = {field: len(values) for field, values in pools.items()}
        except Exception as exc:
            return not_evaluated(
                "Not evaluated: the probe input plan could not be built, so no input was "
                f"replayed. {type(exc).__name__}: {exc}",
                {
                    "engine": "probed",
                    "reason": "input_planning_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
        if not plan:
            return not_evaluated(
                "Not evaluated: the search could not run — "
                + (
                    "the decision trace holds no decision to generate inputs around"
                    if not trace
                    else "the input planner produced no replayable input"
                )
                + ", so nothing was perturbed and nothing was replayed.",
                {
                    "engine": "probed",
                    "reason": "no_seed_decisions" if not trace else "no_inputs_planned",
                    "records_observed": len(trace),
                },
            )

        def budget(replayed: int, errored: int) -> dict[str, Any]:
            return {
                "trials": replayed,
                "trials_requested": trials,
                "strategy": STRATEGY,
                "seed": seed,
                "seed_decisions": len(trace),
                "input_space": input_space,
                "inputs_errored": errored,
                "property_kinds_unestablished": list(unestablished_kinds),
            }

        def holds(record: dict[str, Any]) -> bool:
            result = eval_expression(spec_ast, dict(record))
            if not isinstance(result, bool):
                raise UnsupportedConstructError(
                    f"Requirement spec {req.spec!r} is not a boolean property"
                )
            return result

        errored = 0
        first_error = ""
        for index, case in enumerate(plan):
            try:
                case_snapshot = _clone_case(case)
                first_input = _clone_case(case_snapshot)
            except Exception as exc:
                return not_evaluated(
                    "Not evaluated: a probe input could not be cloned safely, so it was not "
                    f"replayed. {type(exc).__name__}: {exc}.{kind_limit}",
                    {
                        "engine": "probed",
                        "reason": "input_clone_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        PROBE_BUDGET_KEY: budget(index, errored),
                    },
                )
            try:
                record = _as_record(case_snapshot, decide(first_input))
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
                verification_input = _clone_case(case_snapshot)
            except Exception as exc:
                return not_evaluated(
                    "Not evaluated: the counterexample input could not be cloned safely for "
                    f"verification. {type(exc).__name__}: {exc}.{kind_limit}",
                    {
                        "engine": "probed",
                        "reason": "input_clone_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "unverified_counterexample": case_snapshot,
                        PROBE_BUDGET_KEY: budget(index + 1, errored),
                    },
                )
            try:
                replay = _as_record(case_snapshot, decide(verification_input))
                reproduced = not holds(replay)
                replay_note = ""
            except Exception as exc:
                reproduced = False
                replay_note = f" Replay raised {type(exc).__name__}: {exc}."

            if not reproduced:
                return not_evaluated(
                    f"Not evaluated: input {case_snapshot} failed property {req.spec!r} once "
                    "but did not "
                    f"reproduce when replayed against the system's own decide().{replay_note} A "
                    "counterexample that does not reproduce is a defect in this search, not a "
                    f"violation, and is never reported as one.{kind_limit}",
                    {
                        "engine": "probed",
                        "reason": "counterexample_did_not_reproduce",
                        "unverified_counterexample": case_snapshot,
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
                    f"Violated under active perturbation: replaying input {case_snapshot} "
                    "through the system's own decide() produced a decision that fails "
                    f"{req.spec!r}, and the "
                    f"counterexample reproduced when replayed a second time.{kind_limit}"
                ),
                details={
                    "engine": "probed",
                    "counterexample": case_snapshot,
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
                f"over. First failure: {first_error}.{kind_limit}",
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
                f"budget names.{kind_limit}"
            ),
            details={
                "engine": "probed",
                PROBE_BUDGET_KEY: budget(len(plan), errored),
            },
            binding=req.binding,
            scope=req.scope,
        )
