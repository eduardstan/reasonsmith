"""Counterfactual invariance engines for reasonsmith.

What this module is for:
  Discharges the one relational duty in this repository: `counterfactually_invariant(outcome,
  protected)` — hold every input fixed, move one named variable, and the decision must not move.
  It is the first property here that is not a property of one decision record but of a *pair* of
  executions, which is why it has a fragment of its own (`rulelang.COUNTERFACTUAL_CALL`) and a
  ladder of its own (`report._engine_ladder`).

  Two rungs and no third:

  - `CounterfactualProofEngine` at `proved`. The declared rules are encoded **twice** into one Z3
    solver under two namespaces, every free input constrained equal across the copies except the
    protected one, and `outcome@0 != outcome@1` put to the solver. `unsat` is a proof over every
    pair of valuations the system's own `constraints` admit.
  - `PairedReplayEngine` at `probed`. Each recorded decision is replayed through the system's own
    `decide()` once per admissible value of the protected variable, and the outcomes compared.

  There is **no trace rung**, and it is not an omission. A trace holds what the system decided; a
  counterfactual asks what it would have decided. `rulelang.eval_expression` refuses the atom
  outright, so no engine that reads a decision log can answer one even if a ladder handed it the
  duty.

What a reader must not break:
  - **Unawareness is not a discharge.** A system whose declared logic gives the protected variable
    no notion at all — in neither `variables` nor `computes` — is reported UNATTAINABLE naming that
    variable, never `satisfied`. Both engines refuse it and refuse it on the same declaration.
    Why this matters: without the direction declaration these two cases produce the *identical*
    encoding. A system that accepts race and provably ignores it, and a system that has never heard
    of race, both leave the protected name a free constant the outcome does not depend on, so
    `outcome@0 != outcome@1` comes back `unsat` for both. Reporting the second `satisfied` would
    certify an unaware system as provably fair, which is the single most common way a fairness
    claim is wrong: proxies survive unawareness. `computes` is what tells the two apart, so a
    system declaring no directions at all is reported not evaluated rather than guessed at.
  - **The protected variable's values never come from the trace.** At `proved` they are every value
    the declared `constraints` admit; at `probed` they are enumerated from those same constraints.
    Why this matters: a decision record carrying a protected attribute is a collection cost this
    tool would be creating — under the GDPR, an Article 9 processing purpose invented to check a
    fairness duty. The question is about the decision procedure, and a system can answer it while
    its audit log carries a protected attribute for nobody.
  - **The witness is a pair, and both halves are cross-checked and replayed.** The premise model is
    checked against the reference interpreter on *each* copy, and a counterexample is replayed as
    both of its inputs with the outcomes compared.
    Why this matters: every other engine here cross-checks the encoding it proved something about
    and replays the counterexample it found. Checking one half of a 2-safety witness would leave
    this engine's runtime-agreement guarantee weaker than every other engine's while it claims the
    same rung.
  - **A disagreement between the two rungs names its cause and never moves a verdict.** The rungs
    do not range over the same object — the proof quantifies over the *declared rules* on the
    *declared input space*, the replay runs the *implementation* on the *logged* cases — so a
    disagreement eliminates a disjunction rather than impeaching a rung. `cross_rung_signal` is
    the whole of it, and the relation it rests on is stated in
    `theory/04-decision-problems.md` §4.4.
    Why this matters: "the two rungs disagree" tells an adopter nothing it can act on. Which
    disjunct failed tells it either to widen its log or to fix a declaration its own procedure
    does not implement, and those are opposite instructions.
  - **Every result carries `TREATMENT_LIMIT`.** A satisfied verdict here is about one named
    variable and says nothing about a proxy for it.
    Why this matters: a rule set that never reads the protected variable and decides by postcode is
    `satisfied` here, correctly and uselessly. A reader shown a green fairness row without that
    sentence is worse informed than a reader shown no fairness row at all.
  - Everything `engines/proved.py`'s docstring forbids is forbidden here, because the `proved` rung
    is that encoding twice: `unknown`, a timeout, unsatisfiable premises, an encoding that
    disagrees with the interpreter, or a counterexample that does not reproduce all yield NOT
    EVALUATED rather than a rung.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import Any, Optional

import z3

from reasonsmith.report import PROBE_BUDGET_KEY, RequirementResult
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    counterfactual_atom,
    eval_expression,
    is_unknown,
    kleene_value,
    parse_expression,
    parse_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

__all__ = [
    "DEFAULT_MAX_PAIRS",
    "DEFAULT_MAX_VALUES",
    "PAIR_SEMANTICS",
    "RUNG_DISAGREEMENT_FIELDS",
    "RUNG_DISAGREEMENT_KEY",
    "STRATEGY",
    "TREATMENT_LIMIT",
    "CounterfactualProofEngine",
    "PairedReplayEngine",
    "cross_rung_signal",
]

#: What this duty cannot see, carried on every result it produces rather than left to a renderer.
#: It is the column-four sentence of `docs/refinement.md` in the words a reader of one verdict
#: needs, and it is on the *satisfied* results that it matters most.
TREATMENT_LIMIT = (
    "Limit of this duty: it is invariance under one named variable holding all others fixed, so it "
    "is a property of treatment and says nothing about effects. A proxy is invisible to it — a "
    "rule set that never reads the protected variable and decides by postcode is satisfied here — "
    "and a disparate impact is not a thing it can find. It also reaches exactly one variable: a "
    "system answerable on several prohibited bases is answered here about the one this duty names."
)

#: What a `proved` verdict from the self-composition claims, and what it does not. Carried on the
#: result for the reason `engines.temporal.TRACE_SEMANTICS` is: the claim is about a *set of pairs*,
#: and a reader who cannot see which set cannot read the verdict.
PAIR_SEMANTICS = (
    "Pair semantics of this verdict: the declared rules were encoded twice over two input vectors "
    "constrained equal on every variable the system accepts except the protected one, and the "
    "solver was asked whether the two outcomes can differ. A satisfied verdict is universal over "
    "every pair of valuations the system's own `constraints` admit, so narrowing those constraints "
    "narrows the claim. A violated verdict is existential: it names one admissible pair whose "
    "outcomes differ, verified to reproduce on the system, and is a finding about the system as "
    "built rather than about any decision it has taken."
)

#: What the paired replay does, named on every result it produces.
STRATEGY = (
    "each decision the system logged is replayed through its own decide() once per admissible "
    "value of the protected variable, with every other field of the recorded input left exactly "
    "as it was, and the outcomes compared. The admissible values are enumerated from the system's "
    "declared `constraints` and its declared sort for that variable, never from the trace: the "
    "values recorded for a protected attribute are the one place this search must not look. Each "
    "value is compared against the first, which finds any disagreement among them without "
    "replaying every pair"
)

#: How many admissible values of the protected variable the replay enumerates, and how many pairs
#: it will run. Both are deliberately small: the rung is a bounded search whose whole claim is the
#: budget it reports, and a default an adopter waits minutes for is a default nobody runs.
DEFAULT_MAX_VALUES = 4
DEFAULT_MAX_PAIRS = 200

#: Where a result records what a disagreement between this duty's two rungs *eliminated*. It is a
#: signal beside the verdict and never a verdict: `cross_rung_signal` returns the reported rung's
#: own result with this key added, and changes nothing else on it.
RUNG_DISAGREEMENT_KEY = "rung_disagreement"

#: The fields that key carries, named here for the reason `report.PROBE_BUDGET_FIELDS` is: a
#: rendering asks the result rather than parsing a sentence that is free to be reworded. `cause`
#: is one of `RUNG_DISAGREEMENT_CAUSES` and is the whole point of the signal — which disjunct of
#: the claim in the counterfactual decision-problem chapter failed, rather
#: than the bare fact that two rungs differ.
RUNG_DISAGREEMENT_FIELDS = (
    "reported_rung",
    "reported_verdict",
    "lower_rung",
    "lower_verdict",
    "cause",
    "account",
)

#: The four causes, and there is no fifth: one for each direction of disagreement, and the second
#: direction splits on the membership question `_pair_membership` decides.
RUNG_DISAGREEMENT_CAUSES = (
    "trace_does_not_exercise_the_declared_space",
    "replay_input_outside_the_declared_space",
    "declaration_unfaithful_to_the_implementation",
    "membership_undetermined",
)

_UNSET_LOGIC = object()


def _result(
    req: Requirement,
    verdict: Verdict,
    strength: Strength | None,
    summary: str,
    *,
    missing: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> RequirementResult:
    """A result of this duty, with the treatment limit on it whatever else it says."""
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=verdict,
        strength=strength,
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=f"{summary} {TREATMENT_LIMIT}",
        details={**dict(details or {}), "treatment_limit": TREATMENT_LIMIT},
        binding=req.binding,
        scope=req.scope,
    )


def _atom(req: Requirement) -> tuple[str, str] | None:
    """The (outcome, protected) pair of a spec that is one counterfactual atom, else None."""
    try:
        return counterfactual_atom(parse_property(req.spec))
    except UnsupportedConstructError:
        return None


def _wrong_shape(req: Requirement) -> RequirementResult:
    return _result(
        req,
        Verdict.INCONCLUSIVE,
        None,
        (
            f"Not evaluated: {req.spec!r} is not a counterfactual invariance atom, and that is the "
            "only property these engines discharge. Nothing here reasons about a pair of "
            "executions in any other shape."
        ),
        details={"engine": "counterfactual", "reason": "not_a_counterfactual_atom"},
    )


def _direction_refusal(
    req: Requirement,
    outcome: str,
    protected: str,
    variables: Mapping[str, str],
    computes: Any,
) -> RequirementResult | None:
    """Refuse what the declared directions say this system cannot be asked, or None to proceed.

    Five questions, and the order matters because the first two are about the *system* and the
    rest about what it handed over.

    - **No directions declared at all.** Reported not evaluated. This is the case the whole duty
      turns on: without `computes`, a system that accepts the protected variable and one that has
      no notion of it produce the same encoding and the same `unsat`, so answering either would be
      answering both.
    - **The protected variable is in neither list.** The system has no notion of it. UNATTAINABLE
      naming it — unawareness is not a discharge.
    - **The protected variable is one the system computes.** There is no intervention to make: a
      value the system derives from its other inputs is not a knob a counterfactual turns, and
      holding the other inputs fixed while moving it asks about a system nobody built.
    - **The outcome is not a value the system computes.** An outcome the declaration calls an input
      is held equal across the two copies by the equality the encoding asserts, so the negation is
      unsatisfiable for a reason that has nothing to do with the protected variable. That is the
      vacuous proof this package refuses everywhere else, reached by a different road.
    - **The protected variable is not integer-typed.** Reported not evaluated, naming the variable
      and the sort it was declared as. A prohibited basis is a category, and a category declared
      over a dense sort cannot be answered honestly at either rung: the replay search enumerates
      fractions between the categories and reports a clean verdict having never reached one, and a
      witness the proof rung finds may be a pair the system can never be given. Refusing an
      authoring mistake is the four-outcome discipline; sampling it and answering is not.
    """
    if computes is None:
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            None,
            (
                "Not evaluated: the system's declared logic says which variables exist but not "
                "which of them it produces, and this duty cannot be answered without that. A "
                f"system that accepts {protected!r} and provably never lets it change the decision "
                "and a system that has never heard of it encode identically here — in both, the "
                "name is a free constant the outcome does not depend on. Declaring `computes` on "
                "sut.logic() is what tells the two apart; guessing would report the second one "
                "provably fair."
            ),
            details={"engine": "counterfactual", "reason": "no_declared_directions"},
        )
    if protected not in variables and protected not in computes:
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            Strength.UNATTAINABLE,
            (
                f"Unattainable as built: the declared logic gives this system no notion of "
                f"{protected!r} — neither an input it accepts nor a value it computes — so there "
                "is no variable here to hold everything else fixed and move. Not knowing a "
                "protected variable is not evidence of not using one: a decision procedure that "
                "never reads it can still track it exactly through a proxy, and this duty would "
                "report that system satisfied if it were answered from the absence."
            ),
            missing=(protected,),
            details={"engine": "counterfactual", "reason": "protected_variable_unknown"},
        )
    if protected in computes:
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            None,
            (
                f"Not evaluated: the system declares that it computes {protected!r}, so it is not "
                "an input this duty can intervene on. Moving a value the system derives while "
                "holding its other inputs fixed describes a system nobody built, and whatever the "
                "solver said about it would be about that description."
            ),
            details={"engine": "counterfactual", "reason": "protected_variable_computed"},
        )
    if outcome not in computes:
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            None,
            (
                f"Not evaluated: the system does not declare that it computes {outcome!r}, so the "
                "declared logic does not establish it as the decision this duty is about. An "
                "outcome the declaration treats as an input is held equal across the two copies by "
                "the encoding itself, and the resulting proof would be of the equality rather than "
                "of anything the system decides."
            ),
            details={"engine": "counterfactual", "reason": "outcome_not_computed"},
        )
    # Read the same way `engines.proved._sort_for` reads it, default included, so the sort refused
    # here is the sort the encoding would have used.
    declared_sort = str(variables.get(protected, "real")).lower()
    if declared_sort not in ("int", "integer"):
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            None,
            (
                f"Not evaluated: the system declares {protected!r} as {declared_sort!r}, and this "
                "duty answers only an integer-typed protected variable. A prohibited basis is a "
                "category rather than a magnitude, and over a sort that is not the integers the "
                "values between the categories are admissible too: the replay search would move "
                "the variable across fractions the system can never be given and report a clean "
                "verdict having reached no second category, and a pair the solver names may be "
                "one that does not exist. Declaring the sort the values actually are is what "
                "makes the question answerable."
            ),
            details={
                "engine": "counterfactual",
                "reason": "protected_variable_not_integer_typed",
                "declared_sort": declared_sort,
            },
        )
    return None


def _encode_copy(
    namespace: str,
    rules: Iterable[str],
    variables: Mapping[str, str],
    constraints: Iterable[str],
    protected: str,
    solver: z3.Solver,
) -> Any:
    """Encode one copy of the declared logic into `solver` under its own namespace."""
    from reasonsmith.engines.proved import _as_bool, _ast_to_z3, _encode_block, _Scope

    scope = _Scope(dict(variables), namespace)
    for text in constraints:
        scope_z3 = _ast_to_z3(parse_expression(text), scope)
        solver.add(_as_bool(scope_z3, f"System constraint {text!r}"))
    for text in rules:
        _encode_block(ast.parse(text, mode="exec").body, scope, solver)
    # Declared after the rules so that a protected variable no rule and no constraint mentions
    # still exists as a free input of this copy. Without it the two copies would have nothing to
    # differ in and the negation would be unsatisfiable because the question was never asked.
    scope.read(protected)
    return scope


class CounterfactualProofEngine:
    """Proves counterfactual invariance by encoding the declared rules twice."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: Optional[list[dict[str, Any]]] = None,
        timeout_ms: int = 5000,
        *,
        logic_data: Any = _UNSET_LOGIC,
    ) -> RequirementResult:
        from reasonsmith.engines.proved import (
            REAL_ARITHMETIC_LIMIT,
            LogicDeclarationError,
            _check_encoding_against_interpreter,
            _model_inputs,
            decision_runner,
            read_declared_logic,
        )

        atom = _atom(req)
        if atom is None:
            return _wrong_shape(req)
        outcome, protected = atom

        if logic_data is _UNSET_LOGIC:
            logic_func = getattr(sut, "logic", None)
            logic_data = logic_func() if callable(logic_func) else None

        if logic_data is None:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: no decision logic exposed (sut.logic() returned None). Proving "
                    "that a variable cannot move a decision means encoding the decision procedure "
                    "twice, and there is no procedure here to encode."
                ),
                details={"engine": "counterfactual", "reason": "no_logic"},
            )

        try:
            rules, variables, constraints, computes = read_declared_logic(logic_data)
        except LogicDeclarationError as exc:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                exc.summary,
                details={"engine": "counterfactual", **exc.details},
            )

        refusal = _direction_refusal(req, outcome, protected, variables, computes)
        if refusal is not None:
            return refusal

        solver = z3.Solver()
        solver.set("timeout", timeout_ms)
        try:
            left = _encode_copy("@0", rules, variables, constraints, protected, solver)
            right = _encode_copy("@1", rules, variables, constraints, protected, solver)
        except UnsupportedConstructError as exc:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: system logic uses a construct this encoding does not model: "
                    f"{exc}."
                ),
                details={"engine": "counterfactual", "reason": str(exc)},
            )
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                f"Not evaluated: error encoding the declared decision logic: {exc}",
                details={"engine": "counterfactual", "error": str(exc)},
            )

        for scope in (left, right):
            # An `unsat` that means "no pair exists" is not evidence of "no disagreement", and the
            # declaration cannot rule this route out: `_direction_refusal` refuses a protected name
            # the system *declares* it computes, while a name the rules assign and `computes` omits
            # arrives here with the encoding overwriting the free input the intervention turns.
            if scope.is_definitely_assigned(protected) or protected not in scope.inputs:
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: the declared rules assign {protected!r} themselves, so "
                        "the encoding overwrites the input this duty intervenes on and the copies "
                        "decide from a value neither pair member was free to differ in. The "
                        "negation would be unsatisfiable because no pair differing in "
                        f"{protected!r} reaches the decision — not because the decision cannot "
                        "move — and a proof of that is a proof of nothing."
                    ),
                    details={
                        "engine": "counterfactual",
                        "reason": "protected_variable_assigned_by_the_rules",
                    },
                )
            if not scope.is_definitely_assigned(outcome):
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: the system declares it computes {outcome!r}, but the "
                        "declared rules do not assign it on every path, so the exposed logic does "
                        "not settle the decision this duty compares. A pair of free constants "
                        "agreeing proves something about this encoding and nothing about the "
                        "system."
                    ),
                    details={"engine": "counterfactual", "reason": "outcome_not_settled"},
                )

        # Everything the two copies take from outside, held equal but the one variable. Anything
        # the rules derive is a function of these in each copy, so the SSA encoding carries the
        # equality forward without a second assertion.
        held_equal = sorted((set(left.inputs) & set(right.inputs)) - {protected})
        for name in held_equal:
            solver.add(left.inputs[name] == right.inputs[name])

        premise_check = solver.check()
        if premise_check == z3.unsat:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: the two encoded copies of the system logic and its constraints "
                    "admit no pair of inputs at all, so the negated property is unsatisfiable for "
                    "a reason that has nothing to do with "
                    f"{protected!r}. A vacuous model proves everything and is therefore reported "
                    "as no evidence."
                ),
                details={"engine": "counterfactual", "result": "unsatisfiable_premises"},
            )
        if premise_check != z3.sat:
            reason = solver.reason_unknown() or "solver returned unknown or timed out"
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: the formal solver could not decide whether the two encoded "
                    f"copies admit an input at all: {reason}."
                ),
                details={"engine": "counterfactual", "reason_unknown": reason},
            )

        # The pair this duty is about must exist before its absence can be read as invariance. A
        # declaration pinning the protected variable — directly, or by tying it to a variable the
        # equalities above hold fixed — makes the negation unsatisfiable for a reason that is not
        # the property, and the replay rung refuses the same system for the same reason.
        pair_solver = z3.Solver()
        pair_solver.set("timeout", timeout_ms)
        pair_solver.add(*solver.assertions())
        pair_solver.add(left.inputs[protected] != right.inputs[protected])
        pair_check = pair_solver.check()
        if pair_check == z3.unsat:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    f"Not evaluated: the system's own declaration admits no pair of inputs that "
                    f"differ in {protected!r} at all — the constraints pin it, alone or through a "
                    "variable this encoding holds equal across the two copies. There is no second "
                    "value to hold everything else fixed and move to, so the negated property is "
                    "unsatisfiable because the question could not be asked and not because the "
                    f"decision cannot move. A duty about a variable the declared input space pins "
                    "is not a duty this proof can discharge."
                ),
                details={
                    "engine": "counterfactual",
                    "result": "no_admissible_pair_differing_in_the_protected_variable",
                },
            )
        if pair_check != z3.sat:
            reason = pair_solver.reason_unknown() or "solver returned unknown or timed out"
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                (
                    "Not evaluated: the formal solver could not decide whether the declaration "
                    f"admits any pair of inputs differing in {protected!r}: {reason}."
                ),
                details={"engine": "counterfactual", "reason_unknown": reason},
            )

        # Both halves, because the witness of a 2-safety property is a pair. Checking one would
        # leave this engine's agreement guarantee weaker than every other engine's.
        premise_model = solver.model()
        for label, scope in (("first", left), ("second", right)):
            divergence = _check_encoding_against_interpreter(rules, scope, premise_model)
            if divergence is not None:
                kind, message = divergence
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: on the {label} copy of the encoding, {message}. A "
                        "property proved about an encoding the system does not implement is not "
                        "evidence about the system."
                    ),
                    details={"engine": "counterfactual", "copy": label, kind: message},
                )

        # A fresh solver carrying the same assertions, for the reason `ProvedEngine` gives: a proof
        # that depends on which query happened to be asked first is a proof that flakes.
        property_solver = z3.Solver()
        property_solver.set("timeout", timeout_ms)
        property_solver.add(*solver.assertions())
        property_solver.add(left.current[outcome] != right.current[outcome])
        check = property_solver.check()

        space = {
            "variables held equal": held_equal,
            "protected variable varied": protected,
            "outcome compared": outcome,
            "constraints quantified over": list(constraints),
        }

        if check == z3.unsat:
            details: dict[str, Any] = {
                "engine": "counterfactual",
                "solver": "z3",
                "result": "unsat",
                "pair_semantics": PAIR_SEMANTICS,
                "input_space": space,
            }
            real_limit = ""
            if left.uses_real_arithmetic or right.uses_real_arithmetic:
                real_limit = f" {REAL_ARITHMETIC_LIMIT}"
                details["limits"] = REAL_ARITHMETIC_LIMIT
            return _result(
                req,
                Verdict.SATISFIED,
                Strength.PROVED,
                (
                    f"Proved for every admitted pair: no input the system's own constraints admit "
                    f"can be changed in {protected!r} alone and move {outcome!r}. The declared "
                    "rules were encoded twice over two input vectors held equal on "
                    f"{len(held_equal)} variable(s) and free to differ in {protected!r}, and the "
                    f"solver found the two outcomes cannot differ. {PAIR_SEMANTICS}{real_limit}"
                ),
                details=details,
            )

        if check == z3.sat:
            model = property_solver.model()
            left_inputs = _model_inputs(left, model)
            right_inputs = _model_inputs(right, model)
            runner = decision_runner(sut, logic_data)
            if runner is None:
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: the solver produced a pair {left_inputs} / {right_inputs} "
                        "whose outcomes differ, but the system exposes no decide() and its "
                        "logic() carries no rules to replay it against, so neither half of the "
                        "witness could be verified. Never report proved from unverified evidence."
                    ),
                    details={
                        "engine": "counterfactual",
                        "unverified_counterexample": [left_inputs, right_inputs],
                    },
                )
            decide, ran_against = runner
            try:
                left_record = decide(dict(left_inputs))
                right_record = decide(dict(right_inputs))
            except Exception as exc:  # noqa: BLE001 — reported, never swallowed
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: replaying the witness pair against {ran_against} raised "
                        f"{type(exc).__name__}: {exc}, so the counterexample was not verified."
                    ),
                    details={
                        "engine": "counterfactual",
                        "unverified_counterexample": [left_inputs, right_inputs],
                        "verification_error": f"{type(exc).__name__}: {exc}",
                    },
                )
            unusable = [
                half
                for half, record in (("first", left_record), ("second", right_record))
                if not isinstance(record, Mapping) or outcome not in record
            ]
            if unusable:
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: replaying the {', '.join(unusable)} half of the witness "
                        f"pair against {ran_against} produced no value for {outcome!r}, so the two "
                        "outcomes could not be compared and the counterexample was not verified."
                    ),
                    details={
                        "engine": "counterfactual",
                        "unverified_counterexample": [left_inputs, right_inputs],
                    },
                )
            if left_record[outcome] == right_record[outcome]:
                return _result(
                    req,
                    Verdict.INCONCLUSIVE,
                    None,
                    (
                        f"Not evaluated: the solver produced a pair {left_inputs} / {right_inputs} "
                        f"whose outcomes it says differ, but replaying both halves against "
                        f"{ran_against} produced the same {outcome!r} for each. A counterexample "
                        "that does not reproduce is a defect in this encoding, not a finding about "
                        "the system, and is never reported as one."
                    ),
                    details={
                        "engine": "counterfactual",
                        "unverified_counterexample": [left_inputs, right_inputs],
                    },
                )
            return _result(
                req,
                Verdict.VIOLATED,
                Strength.PROVED,
                (
                    f"Violated: the system's own constraints admit a pair of inputs differing only "
                    f"in {protected!r} whose decisions differ. With {protected}="
                    f"{left_inputs.get(protected)!r} the system decided "
                    f"{outcome}={left_record[outcome]!r}; with {protected}="
                    f"{right_inputs.get(protected)!r} and every other input unchanged it decided "
                    f"{outcome}={right_record[outcome]!r}. Both halves were replayed against "
                    f"{ran_against} and the disagreement reproduced. {PAIR_SEMANTICS}"
                ),
                details={
                    "engine": "counterfactual",
                    "solver": "z3",
                    "counterexample_pair": [left_inputs, right_inputs],
                    "counterexample_outcomes": [left_record[outcome], right_record[outcome]],
                    "verification": (
                        f"Both halves of the pair replayed against {ran_against} and the outcomes "
                        "differed again."
                    ),
                    "pair_semantics": PAIR_SEMANTICS,
                    "input_space": space,
                },
            )

        reason = property_solver.reason_unknown() or "solver returned unknown or timed out"
        return _result(
            req,
            Verdict.INCONCLUSIVE,
            None,
            (
                f"Not evaluated: the formal solver could not decide whether {protected!r} can move "
                f"{outcome!r}: {reason}."
            ),
            details={"engine": "counterfactual", "reason_unknown": reason},
        )


def _admissible_values(
    variables: Mapping[str, str],
    constraints: Iterable[str],
    protected: str,
    limit: int,
    *,
    timeout_ms: int = 5000,
) -> list[Any]:
    """Distinct values of `protected` the declared constraints and sort admit, sorted.

    Enumerated from the declaration and never from the trace — see the module docstring. Sorted
    before use so the baseline the replay compares against is the same one on every run, whatever
    order the solver happened to produce the models in.

    Bounded by a solver timeout for the reason every other solver here carries one: the caller
    reports a raise, and cannot report a hang. A check that comes back neither `sat` nor `unsat`
    raises rather than truncating, because a partial enumeration read as the whole admissible set
    would report a variable the system pins.
    """
    from reasonsmith.engines.proved import (
        _as_bool,
        _ast_to_z3,
        _extract_model_value,
        _Scope,
    )

    scope = _Scope(dict(variables))
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    for text in constraints:
        solver.add(_as_bool(_ast_to_z3(parse_expression(text), scope), f"constraint {text!r}"))
    const = scope.read(protected)
    values: list[Any] = []
    while len(values) < limit:
        outcome = solver.check()
        if outcome == z3.unsat:
            break
        if outcome != z3.sat:
            reason = solver.reason_unknown() or "solver returned unknown or timed out"
            raise UnsupportedConstructError(
                f"the declared constraints could not be searched for values of {protected!r}: "
                f"{reason}"
            )
        # `model_completion=True` because a variable no constraint mentions is absent from the
        # model, and absent from the model is the *widest* input space rather than the narrowest:
        # the declaration admits every value of the sort. Reading `model[const]` alone would return
        # None there and this search would report a variable the system pins.
        found = solver.model().eval(const, model_completion=True)
        values.append(_extract_model_value(found))
        solver.add(const != found)
    return sorted(values, key=repr)


class PairedReplayEngine:
    """Replays each recorded decision once per admissible value of the protected variable."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: Optional[list[dict[str, Any]]] = None,
        *,
        trace_provider: Callable[[], Iterable[dict[str, Any]]] | None = None,
        max_values: int = DEFAULT_MAX_VALUES,
        max_pairs: int = DEFAULT_MAX_PAIRS,
    ) -> RequirementResult:
        from reasonsmith.engines.probed import _clone_case
        from reasonsmith.engines.proved import LogicDeclarationError, read_declared_logic

        atom = _atom(req)
        if atom is None:
            return _wrong_shape(req)
        outcome, protected = atom

        def not_evaluated(summary: str, reason: str, **extra: Any) -> RequirementResult:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                summary,
                details={"engine": "paired-replay", "reason": reason, **extra},
            )

        decide = getattr(sut, "decide", None)
        if not callable(decide):
            return not_evaluated(
                "Not evaluated: the system exposes no decide(), so there is no twin decision to "
                "run. A counterfactual is what the system would have decided, and a decision log "
                "records only what it did — no trace, however long, establishes one.",
                "no_decide",
            )

        logic_func = getattr(sut, "logic", None)
        try:
            logic_data = logic_func() if callable(logic_func) else None
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            return not_evaluated(
                f"Not evaluated: reading the system's decision logic failed — "
                f"{type(sut).__name__}.logic() raised {type(exc).__name__}: {exc}, and the values "
                f"of {protected!r} this search may use come from the declared constraints and from "
                "nowhere else.",
                "logic_raised",
            )
        if logic_data is None:
            return not_evaluated(
                "Not evaluated: the system declares no input space, so there is no admissible "
                f"value of {protected!r} to replay a decision against. This search never takes a "
                "protected value from the trace — a decision record is what happened to one "
                "applicant, and reading a counterfactual value out of it would make this duty a "
                "reason to log a protected attribute.",
                "no_declared_input_space",
            )

        try:
            _, variables, constraints, computes = read_declared_logic(logic_data)
        except LogicDeclarationError as exc:
            return _result(
                req,
                Verdict.INCONCLUSIVE,
                None,
                exc.summary,
                details={"engine": "paired-replay", **exc.details},
            )

        refusal = _direction_refusal(req, outcome, protected, variables, computes)
        if refusal is not None:
            return refusal

        try:
            # One more than the bound, so the summary can say whether the search saw the whole
            # admitted set or stopped inside it. Reporting the searched values as the admitted set
            # was a false claim about the measurement.
            values = _admissible_values(variables, constraints, protected, max_values + 1)
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            return not_evaluated(
                f"Not evaluated: the admissible values of {protected!r} could not be enumerated "
                f"from the declared constraints — {type(exc).__name__}: {exc}.",
                "values_not_enumerable",
            )
        bounded = len(values) > max_values
        values = values[:max_values]
        if len(values) < 2:
            return not_evaluated(
                f"Not evaluated: the declared constraints admit "
                f"{'only ' + repr(values[0]) if values else 'no value'} for {protected!r}, so "
                "there is no second value to hold everything else fixed and move to. A duty about "
                "a variable the system's own input space pins is not a duty this search can run.",
                "no_second_admissible_value",
                admissible_values=values,
            )

        try:
            trace = list(records) if records is not None else list(
                (trace_provider or sut.decisions)()
            )
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            return not_evaluated(
                "Not evaluated: the decision trace could not be acquired, so there was no recorded "
                f"decision to build a twin of. {type(exc).__name__}: {exc}",
                "trace_acquisition_failed",
            )
        bases = [dict(record) for record in trace if isinstance(record, Mapping)]
        if not bases:
            return not_evaluated(
                "Not evaluated: the decision trace holds no decision to build a twin of. The trace "
                "supplies the inputs this search varies around and nothing else — the value of "
                f"{protected!r} always comes from the declared constraints.",
                "no_base_decisions",
            )

        baseline, alternatives = values[0], values[1:]
        errored = 0
        first_error = ""
        replayed = 0
        attempted = 0

        def budget() -> dict[str, Any]:
            return {
                "trials": replayed,
                "strategy": STRATEGY,
                "seed": (
                    "none — the base cases are the recorded decisions in the order the system "
                    "returned them, and the protected values are those the declared constraints "
                    "admit, sorted"
                ),
                "input_space": {
                    "base decisions": len(bases),
                    "protected variable": protected,
                    "protected values used": values,
                    "pairs planned": min(len(bases) * len(alternatives), max_pairs),
                },
                "pairs_errored": errored,
            }

        def replay_input(case: Mapping[str, Any], value: Any) -> dict[str, Any]:
            # Cloned per half for the reason the sibling search clones per probe: a decide() that
            # mutates a nested value it was handed would otherwise change the second half's input,
            # and the two outcomes would differ for a reason that is not the protected variable.
            replay = _clone_case(dict(case))
            replay[protected] = value
            return replay

        def run_pair(case: Mapping[str, Any], other: Any) -> tuple[Any, Any]:
            left = decide(replay_input(case, baseline))
            right = decide(replay_input(case, other))
            for record in (left, right):
                if not isinstance(record, Mapping) or outcome not in record:
                    raise UnsupportedConstructError(
                        f"a replayed decision carried no value for {outcome!r}"
                    )
            return left[outcome], right[outcome]

        for case in bases:
            if attempted >= max_pairs:
                break
            for other in alternatives:
                # The cap counts pairs *attempted*, not pairs that came back: a decide() that
                # raises on every pair would otherwise run the whole product while the budget
                # reported a bound it was not keeping.
                if attempted >= max_pairs:
                    break
                attempted += 1
                try:
                    left_outcome, right_outcome = run_pair(case, other)
                except Exception as exc:  # noqa: BLE001 — counted, never read as a pass
                    errored += 1
                    first_error = first_error or f"{type(exc).__name__}: {exc}"
                    continue
                replayed += 1
                if left_outcome == right_outcome:
                    continue

                # Verified before reporting, both halves, exactly as the solver rung verifies its
                # own pair: a disagreement that does not happen twice is a defect in this search.
                try:
                    again_left, again_right = run_pair(case, other)
                except Exception as exc:  # noqa: BLE001 — reported, never swallowed
                    return not_evaluated(
                        f"Not evaluated: replaying the pair {case} under {protected}="
                        f"{baseline!r} / {other!r} disagreed once, but the verification run raised "
                        f"{type(exc).__name__}: {exc}, so nothing is claimed.",
                        "verification_raised",
                        **{PROBE_BUDGET_KEY: budget()},
                    )
                if again_left == again_right:
                    return not_evaluated(
                        f"Not evaluated: replaying the recorded decision {case} under "
                        f"{protected}={baseline!r} and {protected}={other!r} produced different "
                        f"values for {outcome!r} once and the same value when run again. A "
                        "counterexample that does not reproduce is a defect in this search, not a "
                        "finding about the system, and is never reported as one.",
                        "counterexample_did_not_reproduce",
                        unverified_counterexample=dict(case),
                        **{PROBE_BUDGET_KEY: budget()},
                    )
                return _result(
                    req,
                    Verdict.VIOLATED,
                    Strength.PROBED,
                    (
                        f"Violated under paired replay: the recorded decision {case}, replayed "
                        f"through the system's own decide() with {protected}={baseline!r} and "
                        f"again with {protected}={other!r} and nothing else changed, produced "
                        f"{outcome}={left_outcome!r} and {outcome}={right_outcome!r}. The "
                        "disagreement reproduced when both halves were run a second time."
                    ),
                    details={
                        "engine": "paired-replay",
                        "counterexample": dict(case),
                        "counterexample_pair": [
                            {protected: baseline, outcome: left_outcome},
                            {protected: other, outcome: right_outcome},
                        ],
                        "verification": (
                            "Both halves of the pair replayed through the system's own decide() "
                            "and the outcomes differed again."
                        ),
                        PROBE_BUDGET_KEY: budget(),
                    },
                )

        if replayed == 0:
            return not_evaluated(
                f"Not evaluated: every one of the {errored} planned pair(s) raised rather than "
                f"producing two decisions this duty could compare. First failure: {first_error}.",
                "every_replay_failed",
                **{PROBE_BUDGET_KEY: budget()},
            )

        if errored:
            return not_evaluated(
                f"Not evaluated: {errored} of the {attempted} planned pair(s) raised rather than "
                f"producing two decisions this duty could compare. The other {replayed} pair(s) "
                "showed no change, but satisfaction requires every planned pair to complete. "
                f"First failure: {first_error}.",
                "some_replays_failed",
                **{PROBE_BUDGET_KEY: budget()},
            )

        # What was searched, and out of what: the values below are what this search moved the
        # variable across, which is the whole admitted set only when the enumeration ran out
        # before the bound did.
        searched = (
            f"{len(values)} of the values the declared constraints admit — the search bound "
            "stopped the enumeration there and the declaration admits more"
            if bounded
            else f"every one of the {len(values)} values the declared constraints admit"
        )
        return _result(
            req,
            Verdict.SATISFIED,
            Strength.PROBED,
            (
                f"Probed over {replayed} pair(s): no recorded decision changed its {outcome!r} "
                f"when {protected!r} was moved across {searched} "
                f"({', '.join(repr(value) for value in values)}) and nothing else was "
                "changed. This is a bounded search over the decisions the system logged "
                "and the values the budget below names, not a proof: the property is unchecked for "
                "every input outside it."
            ),
            details={"engine": "paired-replay", PROBE_BUDGET_KEY: budget()},
        )


def _pair_membership(
    case: Mapping[str, Any],
    protected: str,
    values: Iterable[Any],
    constraints: Iterable[str],
) -> tuple[str, str | None]:
    """Whether the replayed pair lies in the input space the proof rung quantified over.

    Three answers and not two, because a decision record is not obliged to carry every variable
    the declaration names: `('inside', None)`, `('outside', constraint)` naming the first declared
    constraint the pair fails, or `('undetermined', constraint)` naming the first the record
    leaves unsettled. Read through `rulelang.kleene_value`, so a flag logged as `1` is a truth
    value here exactly as it is at every other rung.

    Both halves are tested, and the protected value is one of the two the replay used rather than
    the one the record carries: the pair the replay ran is the pair whose membership decides
    whether the proof said anything about it.
    """
    undetermined: str | None = None
    values = list(values)
    for text in constraints:
        try:
            node = parse_expression(text)
            held = [
                kleene_value(eval_expression(node, {**case, protected: value}))
                for value in values
            ]
        except Exception:  # noqa: BLE001 — any failure to read a constraint is the third answer
            # A constraint this interpreter cannot read, or cannot evaluate against the values the
            # record carries, is one whose truth on the replayed pair is unknown — the third answer
            # rather than a reason to claim either of the other two. The catch is deliberately
            # every exception class: `eval_expression` raises `UnsupportedConstructError` for a
            # construct outside the language and whatever the operands raise for a comparison the
            # record's own values do not support, and neither eliminates a disjunct.
            undetermined = undetermined or text
            continue
        if any(val is False for val in held):
            return "outside", text
        if any(is_unknown(val) for val in held):
            undetermined = undetermined or text
    if undetermined is not None:
        return "undetermined", undetermined
    return "inside", None


def _residual(
    replay: RequirementResult,
    outcome: str,
    protected: str,
    logic_data: Any,
) -> tuple[str, str]:
    """The cause and the account for a replay that violated where the proof was satisfied.

    The proof is universal over the declared input space and the replay is existential over the
    logged one, so this direction is only possible if the replayed pair left that space, or if the
    system's `decide()` does not implement the `logic()` it declared. The first is cheap and
    decidable, so it is discharged here before anything is said about the second — reporting the
    unfaithful declaration without eliminating the escaped pair would accuse a compliant system of
    the more serious of the two.
    """
    # Read again rather than threaded through: the proof rung read the same declaration to reach
    # the verdict this is annotating, so it is there and it parses.
    from reasonsmith.engines.proved import read_declared_logic

    opening = (
        f"The lower rung disagrees with this proof: replaying a decision this system logged, with "
        f"{protected!r} moved and nothing else changed, produced two different values for "
        f"{outcome!r}. Only two things can make that happen — a replayed pair outside the input "
        "space this proof quantified over, or a decide() that does not implement the declared "
        "rules"
    )
    case = replay.details.get("counterexample")
    pair = replay.details.get("counterexample_pair") or []
    values = [half[protected] for half in pair if isinstance(half, Mapping) and protected in half]
    _, _, constraints, _ = read_declared_logic(logic_data)
    if not isinstance(case, Mapping) or not values:
        return "membership_undetermined", (
            f"{opening} — and which of them it is could not be decided here: the lower rung "
            "reported no replayed pair this check could test against the declared constraints, so "
            "neither possibility is eliminated."
        )

    state, constraint = _pair_membership(case, protected, values, constraints)
    if state == "outside":
        return "replay_input_outside_the_declared_space", (
            f"{opening} — and it is the first: the replayed pair fails the system's own constraint "
            f"{constraint!r}, so it is not a pair this proof ever claimed anything about. Nothing "
            "here says the declaration is unfaithful, and what the disagreement names is the log: "
            "it holds a decision the declared input space does not admit."
        )
    if state == "undetermined":
        return "membership_undetermined", (
            f"{opening} — and which of them it is could not be decided here: the recorded decision "
            f"leaves the system's own constraint {constraint!r} unsettled, so whether the replayed "
            "pair is inside the space this proof quantified over is unknown and neither "
            "possibility is eliminated."
        )
    return "declaration_unfaithful_to_the_implementation", (
        f"{opening} — and the first is eliminated: the replayed pair satisfies every constraint "
        "the system declares, so it is inside the space this proof quantified over. One "
        "possibility remains, that the system's decide() does not implement the logic() it "
        "declares. Read this proof as a proof about the declared rules and not about the "
        "procedure that took the decisions in the log."
    )


def cross_rung_signal(
    req: Requirement,
    proof: RequirementResult,
    replay: RequirementResult,
    logic_data: Any,
) -> RequirementResult:
    """`proof`, with what the lower rung's disagreement eliminated recorded on it.

    The two rungs do not range over the same object. The proof asks whether the *declared rules*
    treat alike every pair the *declared constraints* admit; the replay asks whether the
    *implementation* treated alike the pairs built from the decisions the system *logged*. So a
    disagreement is not a contradiction to be resolved by trusting a rung: it eliminates a
    disjunction, and which disjunct failed is what an adopter can act on. The
    counterfactual decision-problem chapter states the claim and its contrapositive.

    Nothing here moves a verdict, a strength or a witness: the reported rung's own result comes
    back with one key added. A rung that established nothing, and two rungs that agree, are
    returned unchanged — this signal exists for the disagreement and says nothing in its absence.
    """
    decided = (Verdict.SATISFIED, Verdict.VIOLATED)
    atom = _atom(req)
    if (
        atom is None
        or replay.strength is None
        or replay.verdict not in decided
        or proof.verdict not in decided
        or proof.verdict == replay.verdict
    ):
        return proof
    outcome, protected = atom

    if proof.verdict == Verdict.VIOLATED:
        # The expected direction, and not a defect in either rung: the proof reaches the whole
        # declared input space and the replay reaches only what the log exercises.
        cause = "trace_does_not_exercise_the_declared_space"
        account = (
            "The lower rung was run and did not reproduce this finding: replaying the decisions "
            f"this system logged, with {protected!r} moved across the values its own constraints "
            f"admit, moved no {outcome!r}. That is the expected relation between these two rungs "
            "rather than a defect in either — this proof quantifies over every input the declared "
            "constraints admit, and the replay reaches only the cases the log exercises — so the "
            "finding above stands, and what the disagreement names is the log: it does not "
            "exercise what the rules permit."
        )
    else:
        cause, account = _residual(replay, outcome, protected, logic_data)

    disagreement = {
        "reported_rung": proof.strength.value if proof.strength else None,
        "reported_verdict": proof.verdict.value,
        "lower_rung": replay.strength.value,
        "lower_verdict": replay.verdict.value,
        "cause": cause,
        "account": account,
    }
    return replace(
        proof,
        evidence_summary=f"{proof.evidence_summary} {account}",
        details={**proof.details, RUNG_DISAGREEMENT_KEY: disagreement},
    )
