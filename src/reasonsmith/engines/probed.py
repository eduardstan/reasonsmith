"""Probed engine for reasonsmith v0.2.

What this module is for:
  Evaluates state properties — `formalism = "logical"` and `formalism = "record"` alike — against
  a system that exposes no decision logic to reason over but does expose `decide()`: the opaque
  system the `proved` engine cannot reach and the `observed` engine can only watch. It searches
  for a counterexample by perturbing the inputs of the decisions the system already made and
  replaying them through `decide()`.

  A record-keeping duty is a state property like any other once it is written as a formula, so a
  system that can be re-run reaches this rung for one: `present(reason)` is checked against the
  decisions the search generates, not only against the decisions the system happened to log.

What a reader must not break:
  - Probed never rounds up to proved. "No counterexample within the budget" is a statement about
    a bounded search, not about the property, and it is reported at `Strength.PROBED` carrying
    the budget that produced it.
    Why this matters: the whole difference between this engine and the proved engine is that this
    one searched a finite set of inputs. A verdict that does not carry what was searched cannot be
    read for what it is worth, so `RequirementResult` refuses to construct a probed result whose
    `details` do not carry `probe_budget` (see `report.PROBE_BUDGET_FIELDS`) — the budget is a
    construction-time invariant, not a rendering convention.
  - Where the property is an implication, a search in which no replayed decision reached the
    antecedent is reported NOT EVALUATED, never `satisfied`.
    Why this matters: "no counterexample" is worth what the search was; a search where the trigger
    fired nowhere found no counterexample the way an empty search does. The rule is the solver's
    own (`engines/proved.py`), asked of this domain, and it is written once —
    `rulelang.implication_antecedent` names the subtree,
    `report.not_evaluated_for_unreachable_trigger` words the refusal.
  - A violation needs one witness; a satisfaction needs complete evidence. A search in which any
    planned input raised rather than producing a decision is reported NOT EVALUATED, never
    `satisfied`, naming how many went unmeasured. The rule is `engines/certificate.py`'s, asked of
    this domain, and this engine was the last rung not keeping it.
    Why this matters: the inputs a system raises on are not a random sample of the search space —
    they are the ones its own author put outside the band it answers for, which is where a
    property is most at risk. A lender correct to 40000 and raising above it would otherwise be
    reported `satisfied` on `income >= 30000 -> approved` over a domain a quarter of which it
    refused to be measured on. This is asked on the satisfied path alone: a counterexample that
    reproduced is a witness, and it stands however many inputs raised beside it.
  - No summary, budget or rendering may state a replay count larger than the number of inputs the
    property was read over. `inputs_errored` is carried in the budget and surfaced wherever the
    budget is rendered (`render._budget_line`), so the two numbers a reader sees reconcile.
    Why this matters: `evidence_summary` travels into `--json` and into every downstream consumer,
    so a count that includes inputs which raised is a false statement at the data level, not a
    rendering nicety.
  - The search MUST be reproducible: the same records, trials and seed replay the same inputs in
    the same order (`plan_inputs`), and the seed is part of the recorded budget.
    Why this matters: a report that names a budget nobody can re-derive attests to nothing.
  - A candidate counterexample MUST be replayed and seen to fail a second time before it is
    reported, and a candidate that does not reproduce is reported NOT EVALUATED, never violated.
    Why this matters: a system that answers differently on the same input has not been shown to
    violate anything; the finding would be a bug in this search reported as a breach of the duty.
  - Replay inputs are isolated against accidental mutation by the system under test. This does
    not defend against a system that deliberately subverts copying: a system that lies to its
    auditor cannot be audited by that auditor, and reasonsmith does not claim otherwise.
  - A system exposing no `decide()`, a property this engine cannot parse, or a trace with no
    decision to perturb are all reported NOT EVALUATED (`verdict=INCONCLUSIVE`, `strength=None`),
    naming which of the three happened, and never `satisfied`.
    Why this matters: absent evidence is not evidence of compliance.
  - So is a replayed decision that records something which is not a statement where a
    `contains()` atom reads one (`rulelang.NotAStatementError`). That refusal is a property that
    could not be evaluated, not an input the system failed to decide, so it is never absorbed
    into `inputs_errored` and skipped.
    Why this matters: `engines/observed.py` reports the same shape NOT EVALUATED off a trace. A
    rung that answers `satisfied` where a weaker one answers *not evaluated* would make the
    stronger claim the easier one to earn, which inverts the strength lattice.
"""

from __future__ import annotations

import ast
import copy
import random
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Optional

from reasonsmith.report import (
    PROBE_BUDGET_KEY,
    RequirementResult,
    not_evaluated_for_unreachable_trigger,
)
from reasonsmith.rulelang import (
    NotAStatementError,
    UnsupportedConstructError,
    eval_expression,
    expression_kind,
    implication_antecedent,
    parse_expression,
    parse_property,
)
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


def _operation_text(operator: ast.operator | ast.cmpop) -> str:
    return {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.Mod: "%",
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
    }[type(operator)]


def _trace_operand_kind(
    node: ast.AST, field_kinds: Mapping[str, str]
) -> tuple[str, tuple[tuple[str, str], ...]]:
    if isinstance(node, ast.Name):
        kind = field_kinds.get(node.id, "unknown")
        origins = ((node.id, kind),) if kind != "unknown" else ()
        return kind, origins
    if isinstance(node, ast.Constant):
        return expression_kind(node), ()
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        kind, origins = _trace_operand_kind(node.operand, field_kinds)
        if kind not in ("number", "unknown") and origins:
            field, established = origins[0]
            operation = "unary -" if isinstance(node.op, ast.USub) else "unary +"
            raise UnsupportedConstructError(
                f"Field {field!r} has trace-established kind {established}, which contradicts "
                f"arithmetic operation {operation!r} in {ast.unparse(node)!r}"
            )
        return ("unknown" if kind == "unknown" else "number"), origins
    if isinstance(node, ast.BinOp):
        left_kind, left_origins = _trace_operand_kind(node.left, field_kinds)
        right_kind, right_origins = _trace_operand_kind(node.right, field_kinds)
        origins = left_origins + right_origins
        for kind, kind_origins in (
            (left_kind, left_origins),
            (right_kind, right_origins),
        ):
            if kind not in ("number", "unknown") and kind_origins:
                field, established = kind_origins[0]
                operation = _operation_text(node.op)
                raise UnsupportedConstructError(
                    f"Field {field!r} has trace-established kind {established}, which "
                    f"contradicts arithmetic operation {operation!r} in {ast.unparse(node)!r}"
                )
        kind = "unknown" if "unknown" in (left_kind, right_kind) else "number"
        return kind, origins
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name in ("abs", "min", "max"):
            kinds_and_origins = [
                _trace_operand_kind(argument, field_kinds) for argument in node.args
            ]
            origins = tuple(
                origin
                for _, argument_origins in kinds_and_origins
                for origin in argument_origins
            )
            for kind, argument_origins in kinds_and_origins:
                if kind not in ("number", "unknown") and argument_origins:
                    field, established = argument_origins[0]
                    raise UnsupportedConstructError(
                        f"Field {field!r} has trace-established kind {established}, which "
                        f"contradicts arithmetic operation {name!r} in {ast.unparse(node)!r}"
                    )
            kind = (
                "unknown"
                if any(kind == "unknown" for kind, _ in kinds_and_origins)
                else "number"
            )
            return kind, origins
    return expression_kind(node), ()


def _validate_trace_kinds(node: ast.Expression, field_kinds: Mapping[str, str]) -> None:
    boolean_positions: list[tuple[ast.AST, str]] = []
    if isinstance(node.body, ast.Name):
        boolean_positions.append((node.body, "property result"))
    for current in ast.walk(node):
        if isinstance(current, ast.UnaryOp) and isinstance(current.op, ast.Not):
            boolean_positions.append((current.operand, "not"))
        elif isinstance(current, ast.BoolOp):
            operation = "and" if isinstance(current.op, ast.And) else "or"
            boolean_positions.extend((value, operation) for value in current.values)
        elif isinstance(current, ast.Call):
            name = current.func.id if isinstance(current.func, ast.Name) else ""
            if name in ("implies", "Implies"):
                boolean_positions.extend((argument, name) for argument in current.args)

    for position, operation in boolean_positions:
        if not isinstance(position, ast.Name):
            continue
        kind = field_kinds.get(position.id, "unknown")
        if kind not in ("boolean", "unknown"):
            raise UnsupportedConstructError(
                f"Field {position.id!r} has trace-established kind {kind}, which contradicts "
                f"Boolean operation {operation!r}"
            )

    for comparison in (item for item in ast.walk(node) if isinstance(item, ast.Compare)):
        left = comparison.left
        left_kind, left_origins = _trace_operand_kind(left, field_kinds)
        for operator, right in zip(comparison.ops, comparison.comparators, strict=True):
            right_kind, right_origins = _trace_operand_kind(right, field_kinds)
            known = left_kind != "unknown" and right_kind != "unknown"
            ordered = isinstance(operator, (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            compatible = left_kind == right_kind and (
                not ordered or left_kind in ("number", "string")
            )
            if known and not compatible:
                operator_text = _operation_text(operator)
                established_fields = left_origins + right_origins
                if established_fields:
                    evidence = ", ".join(
                        f"{field!r} ({kind})" for field, kind in established_fields
                    )
                    raise UnsupportedConstructError(
                        f"Trace-established field kind(s) {evidence} contradict comparison "
                        f"operation {operator_text!r} in {ast.unparse(comparison)!r}"
                    )
                raise UnsupportedConstructError(
                    f"Comparison {ast.unparse(left)!r} {operator_text} "
                    f"{ast.unparse(right)!r} has incompatible established kinds "
                    f"{left_kind} and {right_kind}"
                )
            left = right
            left_kind = right_kind
            left_origins = right_origins


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
            spec_ast = parse_property(req.spec)
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

        # The same question the solver asks of its input space, asked of this one: did any
        # replayed decision reach the property's antecedent at all? Counted alongside the
        # property rather than in a second walk, because the interpreter is already evaluating
        # both — `Implies(a, b)` evaluates its antecedent to answer the implication.
        antecedent_ast = implication_antecedent(spec_ast)
        antecedent_text = ast.unparse(antecedent_ast) if antecedent_ast is not None else ""
        triggered = 0

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
                if antecedent_ast is not None and eval_expression(antecedent_ast, dict(record)):
                    triggered += 1
            except NotAStatementError as exc:
                return not_evaluated(
                    f"Not evaluated: {req.spec!r} asks what a statement says, but replaying input "
                    f"{case_snapshot} produced a decision recording something that is not text. A "
                    "non-text value is not evidence about the wording of a statement, so the "
                    f"property was not read over this search. {exc}.{kind_limit}",
                    {
                        "engine": "probed",
                        "reason": "signal_without_text_in_replay",
                        "error": f"{type(exc).__name__}: {exc}",
                        PROBE_BUDGET_KEY: budget(index, errored),
                    },
                )
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

        # A violation needs one witness, a satisfaction needs complete evidence. The breach above
        # stands whatever raised beside it; satisfaction over the part of the domain that answered
        # is not satisfaction over the domain this search set out to measure. Asked before the
        # trigger guard on purpose: where inputs raised, "the antecedent fired nowhere" is a claim
        # about the measured part alone, and the inputs that raised are exactly the ones that
        # might have reached it.
        measured = len(plan) - errored
        if errored:
            return not_evaluated(
                f"Not evaluated: {errored} of the {len(plan)} input(s) this search planned raised "
                f"rather than producing a decision this property could be read over, so the "
                f"property is unmeasured on them. No counterexample to {req.spec!r} was found in "
                f"the other {measured}, but satisfaction over the part of the search space that "
                "answered is not satisfaction over the search space: a violation needs one "
                f"witness, a satisfaction needs complete evidence. First failure: {first_error}. "
                f"Nothing is claimed either way.{kind_limit}",
                {
                    "engine": "probed",
                    "reason": "inputs_unmeasured",
                    "error": first_error,
                    PROBE_BUDGET_KEY: budget(len(plan), errored),
                },
            )

        if antecedent_ast is not None and not triggered:
            return not_evaluated_for_unreachable_trigger(
                req,
                antecedent_text,
                f"the {measured} decision(s) this search replayed",
                {"engine": "probed", PROBE_BUDGET_KEY: budget(len(plan), errored)},
            )

        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.SATISFIED,
            strength=Strength.PROBED,
            signals_required=tuple(req.requires),
            evidence_summary=(
                # `measured`, never `len(plan)`: the count names the inputs this property was
                # actually read over. The guard above makes the two equal here, and saying so in
                # the arithmetic keeps the sentence true of its own accord rather than by grace
                # of a check several lines up.
                f"Probed: no counterexample to {req.spec!r} in {measured} input(s) replayed "
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
