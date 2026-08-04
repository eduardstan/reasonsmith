"""Proved engine for reasonsmith v0.2.

What this module is for:
  Evaluates state properties — `formalism = "logical"` and `formalism = "record"` alike — over
  decision systems that expose their decision logic via `sut.logic()`, using the Z3 SMT solver.
  A record-keeping duty written as `present(reason)` is a property of one decision like any
  other, so a system that exposes rules always assigning `reason` can have it *proved* rather
  than merely observed on the decisions it chose to log; see `_present_to_z3` for the three
  cases where that would be an overclaim and is refused instead.

What a reader must not break:
  - Solver outcomes of `unknown`, solver timeouts, or logic containing unsupported constructs MUST
    be reported as NOT EVALUATED (`verdict=INCONCLUSIVE`, `strength=None`), NEVER `satisfied` or
    `proved`.
    Why this matters: Never report `proved` from a solver result you did not obtain. Assuming an
    undecided or unmodelled property holds is the single overclaim this tool exists to prevent.
  - The encoded premises MUST be checked satisfiable before `unsat` on the negated property is
    read as a proof.
    Why this matters: `unsat` from premises no input can satisfy proves every property and its
    negation alike. A vacuous model is a modelling failure, so it is reported NOT EVALUATED.
  - Where the property is an implication, the antecedent MUST be checked satisfiable under the
    same premises before `unsat` on the negation is read as a proof.
    Why this matters: it is the premise check one quantifier deeper. `unsat` from an antecedent no
    admissible input reaches proves the implication and every other implication with that
    antecedent, so the verdict is a fact about the formula wearing the strongest rung this tool
    issues. `rulelang.implication_antecedent` names the subtree and
    `report.not_evaluated_for_unreachable_trigger` words the refusal, both once for every engine.
  - Rule assignments MUST be encoded in static single assignment form.
    Why this matters: `logic()` describes a program executed statement by statement, so `score =
    score + 10` reassigns. Encoding it as one equality per name turns reassignment into a
    contradiction, which is the vacuous proof above wearing a different hat.
  - The encoding MUST be checked against the reference interpreter on the premise model before any
    verdict is read off the solver, and a disagreement MUST be reported as NOT EVALUATED.
    Why this matters: this module and `rulelang` are two implementations of one language, and the
    solver is free to exploit any gap between them — a declared sort narrowing the inputs, an
    operator that rounds differently — to make a property come out `unsat` for a reason the system
    does not implement. One agreed witness is not a proof of equivalence, but it is what catches
    the divergence before it is reported as `proved`.
  - A `proved` verdict resting on Real arithmetic MUST carry `REAL_ARITHMETIC_LIMIT`.
    Why this matters: the solver reasons over exact rationals while the system runs float64, so
    `t = a + b; d = t - b` proves `d == a` and yet returns 0.10000000000000003 for a=0.1, b=0.2.
    Encoding IEEE floats would be a different engine; naming the abstraction on the result that
    makes the claim is what stops `proved` from being read as more than it is.
  - A property reading a name the declared rules never assign MUST be refused where reading it is
    a claim about what the system computed — `present`, `contains` and a comparison of magnitudes
    alike (`_present_to_z3`, `_contains_to_z3`, `_check_magnitudes_are_computed`, and
    `_check_declared_directions` on top of it wherever the logic declares directions).
    Why this matters: such a name is a free constant of this encoding. `deviation <= margin` over
    two of them is arithmetic over numbers nobody computed, and the counterexample verification
    cannot catch it because the reference interpreter is handed the same free inputs.
  - Where `sut.logic()` declares `computes`, a name in neither `computes` nor `variables` MUST be
    refused outright, and that declaration MUST NOT admit anything the sort heuristic refuses:
    both guards run, and a declaration narrows what reaches the solver rather than widening it.
    Why this matters: a name the system has no notion of is one `_Scope.read` invents a constant
    for, and every verdict downstream is then about the invention. The heuristic below cannot see
    that at all; it can only ask what sort a name would get, which is the wrong question — but
    `variables` is a type table, so it cannot answer the heuristic's question either: a caller
    listing a name the system merely logs is not calling it an input, and reading it as one
    restores the `violated`-at-`proved` verdict over uncomputed numbers in one direction and, once
    a constraint mentions those numbers, a `satisfied`-at-`proved` verdict on a duty the system
    asserted about itself in the other.
  - A counterexample model produced by Z3 MUST be verified to reproduce on the system under test
    before reporting `VIOLATED` at strength `PROVED`, and the evidence summary must say what that
    verification actually ran against.
    Why this matters: A counterexample that does not reproduce on the actual system under test is
    worse than none and indicates a model mismatch. If verification fails, report NOT EVALUATED.
"""

from __future__ import annotations

import ast
import math
from typing import Any, Optional

import z3

from reasonsmith.report import RequirementResult, not_evaluated_for_unreachable_trigger
from reasonsmith.rulelang import (
    CONTAINS_CALL,
    PRESENCE_CALL,
    UnsupportedConstructError,
    assignment_target,
    contains_arguments,
    eval_expression,
    execute_statements,
    fold_ascii_case,
    implication_antecedent,
    parse_expression,
    parse_property,
    signal_names,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict

__all__ = [
    "REAL_ARITHMETIC_LIMIT",
    "LogicDeclarationError",
    "ProvedEngine",
    "decision_runner",
    "encode_logic_domain",
    "UnsupportedConstructError",
    "read_declared_logic",
]

#: The limit every proof touching a `real` carries, stated on the result that makes the claim.
REAL_ARITHMETIC_LIMIT = (
    "Limit of this proof: `real` is the exact rationals to the solver and IEEE-754 float64 to the "
    "system, so this holds over the rationals and not over the arithmetic the system runs. A "
    "property that depends on rounding can be proved here and still fail in execution."
)
_UNSET_LOGIC = object()


class LogicDeclarationError(UnsupportedConstructError):
    """A `sut.logic()` payload no solver-backed engine can read, with what to report about it.

    Carries the summary and the details rather than only a message, because every refusal below
    was already worded for a reader of a report and the two engines that read a declaration must
    word them identically. A subclass of `UnsupportedConstructError` so a caller that only knows
    the base class still refuses rather than crashing.
    """

    def __init__(self, summary: str, details: dict[str, Any]):
        super().__init__(summary)
        self.summary = summary
        self.details = details


def read_declared_logic(logic_data: Any) -> tuple[list[str], dict[str, str], list[str], Any]:
    """The rules, the type table, the constraints and the declared `computes` of a `logic()`.

    One reading of a declaration, shared by the state-property proof and by the self-composition
    the counterfactual duty needs. `computes` is returned as a `set` of names, or `None` where the
    system declared no directions at all — which is not the same as declaring it computes nothing,
    and the two engines answer it differently.
    """
    if isinstance(logic_data, dict):
        rules = logic_data.get("rules", [])
        variables = logic_data.get("variables", {})
        constraints = logic_data.get("constraints", [])
        declared_computes = logic_data.get("computes")
    elif hasattr(logic_data, "rules"):
        rules = getattr(logic_data, "rules", [])
        variables = getattr(logic_data, "variables", {})
        constraints = getattr(logic_data, "constraints", [])
        declared_computes = getattr(logic_data, "computes", None)
    else:
        tname = type(logic_data).__name__
        raise LogicDeclarationError(
            f"Not evaluated: sut.logic() returned unexpected type {tname}.", {}
        )

    if isinstance(declared_computes, (str, bytes)):
        raise LogicDeclarationError(
            "Not evaluated: sut.logic() declares `computes` as a string rather than a "
            "collection of names, and read as one it is a set of characters naming nothing "
            "the system computes. Silently accepted it would read every declared variable as "
            "an input, which is the reading the declaration exists to replace.",
            {"computes": repr(declared_computes)},
        )

    if declared_computes is not None:
        try:
            declared_computes = set(declared_computes)
        except TypeError:
            raise LogicDeclarationError(
                "Not evaluated: sut.logic() declares `computes` as "
                f"{type(declared_computes).__name__}, which is not a collection of names at "
                "all, so nothing here can read which variables the system computes. A "
                "direction declaration that cannot be read is refused rather than ignored.",
                {"computes": repr(declared_computes)},
            ) from None
        not_names = sorted(repr(n) for n in declared_computes if not isinstance(n, str))
        if not_names:
            raise LogicDeclarationError(
                "Not evaluated: sut.logic() declares `computes` entries that are not variable "
                "names: " + ", ".join(not_names) + ". An entry naming no variable matches no "
                "name in the property, so accepting it would silently read a computed output "
                "as an input the situation supplies.",
                {"computes": ", ".join(not_names)},
            )

    return rules, variables, constraints, declared_computes


def _declare(name: str, var_types: dict[str, str], suffix: str = "") -> Any:
    """Create a Z3 constant for `name` at the sort its declared type asks for."""
    vtype = str(var_types.get(name, "real")).lower()
    label = f"{name}{suffix}"
    if vtype in ("int", "integer"):
        return z3.Int(label)
    if vtype in ("bool", "boolean"):
        return z3.Bool(label)
    if vtype in ("str", "string"):
        return z3.String(label)
    return z3.Real(label)


class _Scope:
    """Static single assignment name table: current version per name, plus the free inputs.

    `namespace` labels every constant this scope declares, and exists so the *same* rule block can
    be encoded twice into one solver without the two copies collapsing into each other. An SSA
    label is `name#version`, which is unique within one execution and identical across two, so two
    copies sharing a solver would silently assert that the second execution's `approved#1` is the
    first execution's — turning a property of a *pair* of runs into a property of one. The default
    is the empty namespace, so a single-copy encoding is labelled exactly as it always was.
    """

    def __init__(self, var_types: Optional[dict[str, str]], namespace: str = ""):
        self.var_types: dict[str, str] = dict(var_types or {})
        self.namespace = namespace
        self.current: dict[str, Any] = {}
        self.inputs: dict[str, Any] = {}
        self.uses_real_arithmetic = False
        self._versions: dict[str, int] = {}
        self._definitely_assigned: set[str] = set()

    def note_sort(self, expr: Any) -> Any:
        """Record that the encoding reached the Real sort, and return `expr` unchanged."""
        if isinstance(expr, z3.ArithRef) and expr.is_real():
            self.uses_real_arithmetic = True
        return expr

    def read(self, name: str) -> Any:
        """Return the constant holding the current value of `name`, declaring it as a free input."""
        if name not in self.current:
            const = self.note_sort(_declare(name, self.var_types, self.namespace))
            self.current[name] = const
            self.inputs[name] = const
        return self.current[name]

    def assign(self, name: str) -> Any:
        """Bind `name` to a fresh constant and return it."""
        version = self._versions.get(name, 0) + 1
        self._versions[name] = version
        const = self.note_sort(_declare(name, self.var_types, f"{self.namespace}#{version}"))
        self.current[name] = const
        self._definitely_assigned.add(name)
        return const

    def is_definitely_assigned(self, name: str) -> bool:
        """True when every encoded path writes `name` before the property is evaluated."""
        return name in self._definitely_assigned

    def present(self, name: str) -> Any:
        """This scope's `present(name)`. See `_present_to_z3` for what it encodes and refuses.

        A method rather than a free function so that a scope encoding a property against something
        other than a rule block — `reasonsmith.analysis`, which reasons about a pack's formulas
        with no system to assign anything — can say what the atom means there without a second
        copy of `_ast_to_z3`. Everything above the atoms stays one implementation, which is the
        agreement obligation `contains()` is already held to.
        """
        if not self.is_definitely_assigned(name):
            raise UnsupportedConstructError(
                f"{PRESENCE_CALL}({name}) cannot be proved: the declared rules do not assign "
                f"{name!r} on every path, so the exposed logic does not establish that every "
                "decision carries it"
            )
        const = self.read(name)
        if const.sort() == z3.StringSort():
            return z3.Not(z3.InRe(const, _blank_string_re()))
        return z3.BoolVal(True)

    def contains(self, signal: str, phrase: str) -> Any:
        """This scope's `contains(signal, phrase)`. See `_contains_to_z3`."""
        if not self.is_definitely_assigned(signal):
            raise UnsupportedConstructError(
                f"{CONTAINS_CALL}({signal}, ...) cannot be proved: the declared rules do not "
                f"assign {signal!r} on every path, so the exposed logic does not establish what "
                "every decision says"
            )
        const = self.read(signal)
        if const.sort() != z3.StringSort():
            raise UnsupportedConstructError(
                f"{CONTAINS_CALL}({signal}, ...) reads recorded text, but the declared rules give "
                f"{signal!r} sort {const.sort()}"
            )
        return _contains_string_z3(const, phrase)

    def snapshot(self) -> tuple[dict[str, Any], set[str]]:
        return dict(self.current), set(self._definitely_assigned)

    def restore(self, snapshot: tuple[dict[str, Any], set[str]]) -> None:
        self.current = dict(snapshot[0])
        self._definitely_assigned = set(snapshot[1])


def _to_real(expr: Any) -> Any:
    """Widen a Z3 Int expression to Real, leaving every other sort alone."""
    if isinstance(expr, z3.ArithRef) and expr.is_int():
        return z3.ToReal(expr)
    return expr


def _python_mod(left: Any, right: Any) -> Any:
    """Encode Python's floor-based `%`, which Z3's `mod` matches only for a positive divisor."""
    both_int = (
        isinstance(left, z3.ArithRef)
        and left.is_int()
        and isinstance(right, z3.ArithRef)
        and right.is_int()
    )
    if both_int and z3.is_int_value(right) and right.as_long() > 0:
        return left % right

    floor_quotient = z3.ToInt(_to_real(left) / _to_real(right))
    if both_int:
        return left - right * floor_quotient
    return _to_real(left) - _to_real(right) * z3.ToReal(floor_quotient)


def _z3_promote(a: Any, b: Any) -> tuple[Any, Any]:
    """Promote Z3 Int to Real if one operand is Real and the other is Int."""
    if isinstance(a, z3.ArithRef) and isinstance(b, z3.ArithRef):
        if a.is_real() and b.is_int():
            return a, z3.ToReal(b)
        if a.is_int() and b.is_real():
            return z3.ToReal(a), b
    return a, b


#: Exactly the characters Python's `str.strip()` removes, which is exactly the set for which
#: `str.isspace()` is true. `rulelang.is_present` calls a string absent when stripping it leaves
#: nothing, so this list is what makes the solver's notion of a blank string the same notion —
#: `test_the_solvers_blank_string_is_pythons_blank_string` enumerates the codepoint space and
#: fails if the two ever diverge. Widening or narrowing it by hand breaks that agreement.
BLANK_CHARACTERS = tuple(chr(code) for code in range(0x110000) if chr(code).isspace())


def _blank_string_re() -> Any:
    """The Z3 regular language of strings `is_present` calls absent: blanks, `""` included."""
    return z3.Star(z3.Union(*[z3.Re(z3.StringVal(char)) for char in BLANK_CHARACTERS]))


def _present_to_z3(node: ast.Call, scope: _Scope) -> Any:
    """Encode `present(signal)` against the declared rules, or refuse it.

    `present(x)` asks whether a decision carries a value for `x`, in the `rulelang.is_present`
    sense the record engine and the replay search both use. The exposed logic can answer that for
    a name its own rules assign — every execution of those rules writes that name — and the
    encoding is per sort:

    - **bool, int, real** — every value of the sort is a value a record carries. `is_present` says
      so too: `0` and `False` are present, and only `None` and blanks are not.
    - **string** — present means non-blank, and `""` is not the only blank string. The encoding is
      "not in the language of blanks" over `BLANK_CHARACTERS`, which is exactly the set
      `str.strip()` removes, so the solver and `is_present` agree on every string rather than
      approximately.

    A **free input** is refused. The rules read it and never write it, so proving anything about
    the solver's free constant would say the record carries `x` because this encoding declared a
    constant called `x` — a fact about the encoding, not about the system. The refusal is an
    `UnsupportedConstructError`, so the requirement falls to the strongest engine that *can*
    discharge it (`report._engine_ladder`) rather than losing its verdict altogether.
    """
    if len(node.args) != 1 or not isinstance(node.args[0], ast.Name):
        raise UnsupportedConstructError(
            f"{PRESENCE_CALL}() takes one signal name: {ast.unparse(node)!r}"
        )
    return scope.present(node.args[0].id)


def _any_string_re() -> Any:
    """The Z3 regular language of every string, used to bracket a substring search.

    `Full` rather than the equivalent `Star(AllChar(...))`: the two accept the same language, and
    the solver reaches an answer about twice as fast on the one it recognises as a primitive. The
    difference decides whether this engine finishes inside its own timeout, and a proof that
    depends on how the same language was spelled is a proof that flakes.
    """
    return z3.Full(z3.ReSort(z3.StringSort()))


def _case_folded_re(phrase: str) -> Any:
    """The Z3 regular language of `phrase` under `fold_ascii_case`, character by character.

    `z3.Contains` would be shorter and would be case-*sensitive*, which is not the predicate
    `rulelang.contains_literal` implements: a notice reading "Failed to achieve a qualifying score"
    is the same statement as the lower-case one, and a duty that misses it because of a capital
    letter is theatre. Each character therefore becomes a regular language matching exactly one
    character — itself, or either case where it is an ASCII letter. Exactly one character per
    character is what makes this the same fold: the interpreter's is length-preserving by
    construction (`fold_ascii_case`), and `contains_arguments` refuses a non-ASCII phrase rather
    than let the two sides disagree about a fold only one of them can perform.
    """
    parts = []
    for char in phrase:
        lowered = fold_ascii_case(char)
        if "a" <= lowered <= "z":
            parts.append(
                z3.Union(
                    z3.Re(z3.StringVal(lowered)),
                    z3.Re(z3.StringVal(chr(ord(lowered) - 32))),
                )
            )
        else:
            # `fold_ascii_case` changes nothing but the twenty-six capitals, so every other
            # character stands for itself and for no other.
            parts.append(z3.Re(z3.StringVal(char)))
    return z3.Concat(*parts) if len(parts) > 1 else parts[0]


def _contains_string_z3(const: Any, phrase: str) -> Any:
    """The solver's `contains(const, phrase)`, blankness rule included.

    Two conditions, and the first is the one a bracketed regular language alone would lose:
    `rulelang.contains_literal` calls a value the record does not carry — a blank string among
    them — a value that carries no phrase, so a phrase made of blanks must not be found in a
    string of blanks. `_present_to_z3` already builds that language; this reuses it so the solver
    and the interpreter cannot disagree about the one input class where a substring search and
    `is_present` pull apart.
    """
    any_string = _any_string_re()
    return z3.And(
        z3.Not(z3.InRe(const, _blank_string_re())),
        z3.InRe(const, z3.Concat(any_string, _case_folded_re(phrase), any_string)),
    )


def _contains_to_z3(node: ast.Call, scope: _Scope) -> Any:
    """Encode `contains(signal, "phrase")` against the declared rules, or refuse it.

    Two refusals, and both drop the duty to the strongest engine that *can* answer it rather than
    losing its verdict, exactly as `_present_to_z3`'s refusal does:

    - **The signal is a free input of the rules.** Read, never written. What a statement says is a
      fact about what the system writes into it; the solver's free constant says nothing about that.
    - **The signal is not declared a string.** The predicate reads recorded text, and a rule set
      that gives this name a number or a Boolean is not one this property is about. Coercing a sort
      would prove a property about a program nobody wrote.
    """
    signal, phrase = contains_arguments(node)
    return scope.contains(signal, phrase)


def _check_magnitudes_are_computed(node: ast.AST, scope: _Scope) -> None:
    """Refuse a property whose magnitudes are all free constants of this encoding.

    The third call site of the refusal `_present_to_z3` and `_contains_to_z3` already make, resting
    on the identical argument: a name the rules read and never write is a free constant of this
    encoding, so `deviation <= margin` over two such names is arithmetic over numbers nobody
    computed. The solver duly finds `deviation = 1, margin = 0`, and the counterexample
    verification duly reproduces it, because the reference interpreter is handed the same free
    inputs — so a system whose rules decide on a score alone is told it breaches a GDPR duty at the
    highest strength this tool issues. Refused, the duty falls to the engine that reads the trace,
    where an unmeasured magnitude is reported as an unmeasured magnitude.

    The refusal is narrow, and both conditions are needed. It fires only when

    - the property reads **no** name the rules assign, so it constrains nothing the system
      computes and its verdict is a fact about the declared sorts and constraints alone; and
    - at least one name it does read is a **magnitude** — an arithmetic sort. A property over
      free *Booleans* is left alone, because quantifying over those is a reading duties genuinely
      take: `gdpr_art22_1_no_prohibited_decision_for_any_input` asks whether any admissible input
      yields a prohibited decision, and the Article 22 flags are exactly the free inputs that
      question ranges over. Firing on every unassigned name would silence that duty.

    Keeping the antecedent case is what the first condition buys: `income >= 30000 and age >= 18
    implies approved == True` reads three free magnitudes and one computed `approved`, and it is a
    claim about what the system decides. Proving it is the engine's whole purpose.

    **It is a heuristic, and cuts along the wrong joint.** The distinction that matters is an
    *input to the decision situation* versus an *output the system computes*, and it answers that
    with a name's sort and reachability, which are proxies for neither. `logic()` may now declare
    `computes`, and where it does `_check_declared_directions` asks the question directly — but
    this guard runs **as well**, never instead. A declaration may narrow what reaches the solver
    and may not widen it, because the two guards refuse on different grounds and neither subsumes
    the other: `variables` is a type table, so a name listed there and absent from `computes` is
    not thereby an input the situation supplies — it may be one the system merely logs, and a
    declaration read as though it were hands back exactly the `violated`-at-`proved` verdict this
    guard stops, over numbers nobody computed. A constraint mentioning those numbers is worse
    still: it makes the same encoding report `satisfied` at `proved` on a duty the system has
    asserted about itself. `docs/semantics.md` §3.5 states the pair, for the reader.
    """
    names = signal_names(node)
    if any(scope.is_definitely_assigned(name) for name in names):
        return
    free_magnitudes = [
        name for name in names if isinstance(_declare(name, scope.var_types), z3.ArithRef)
    ]
    if not free_magnitudes:
        return
    raise UnsupportedConstructError(
        "the property compares "
        + ", ".join(repr(name) for name in free_magnitudes)
        + " as magnitudes and reads nothing the declared rules assign, so no value in it is one "
        "the system computes. Proving a property of the solver's free constants would report "
        "arithmetic over numbers nobody computed as a fact about the system"
    )


def _check_declared_directions(node: ast.AST, scope: _Scope, computes: set[str]) -> None:
    """Refuse a property the declared directions say this encoding cannot be about.

    Runs whenever `sut.logic()` declares `computes`, and asks the question
    `_check_magnitudes_are_computed` could only approximate — *beside* that guard rather than in
    place of it, so a declaration narrows what reaches the solver and never widens it. The
    declaration splits every name into three, the two lists together supplying the outer boundary
    and `computes` the inner one:

    - **in `computes`** — an output the system produces. `RulesAdapter` keeps `computes` a subset
      of `variables`, but nothing in the protocol requires an adapter to repeat a computed name in
      the type table, so a name declared computed and nothing else is an output here and not an
      unknown: it is a name the system said it produces, whatever sort `_declare` gives it.
    - **in `variables`, not in `computes`** — a name the type table gives a sort and the
      declaration does not call an output. That is *at most* an input the decision situation
      supplies, and the solver's free constant is the right encoding of one, so quantifying over
      it is what a proof *is*: `income >= 30000 implies approved` and
      `gdpr_art22_1_no_prohibited_decision_for_any_input` both live here. It is not *only* that,
      because `variables` is a type table and a caller may list a name the system merely logs —
      which is why `_check_magnitudes_are_computed` still runs after this.
    - **in neither** — a name the system has no notion of.

    Two refusals follow, and neither is a judgement about the property:

    - **A name the system has no notion of.** `_Scope.read` declares a constant for any name it
      meets, so without this the encoding invents the very value the verdict is then about. This is
      the defect `_check_magnitudes_are_computed` was written against, caught at its own joint:
      a system deciding on a score alone has no `artifact_logs_decision_margin`, and it does not
      matter what sort one would be given.
    - **A declared output the exposed rules do not settle on every path.** The system says it
      computes this name and the logic it handed over does not show how, so the constant standing
      in for it is free after all. `present()` and `contains()` refuse the same thing for their own
      atoms and with their own wording, which is why this runs after the property is encoded rather
      than before: their message is the more specific one and should win.

    Both are `UnsupportedConstructError`, so the duty falls to the strongest engine that *can*
    discharge it (`report._engine_ladder`) rather than losing its verdict.

    What this does not do is second-guess the declaration. An adapter that calls an output an input
    is claiming its situation supplies a value it in fact produces, and this engine will duly prove
    things about that claim — the same trust `system_domains` is given, and stated in
    `docs/semantics.md` §3.5.
    """
    names = signal_names(node)
    unknown = sorted(
        name for name in names if name not in scope.var_types and name not in computes
    )
    if unknown:
        raise UnsupportedConstructError(
            "the property reads "
            + ", ".join(repr(name) for name in unknown)
            + ", which the declared logic gives the system no notion of — neither an input it "
            "accepts nor a value it computes. Proving anything about it would be a fact about a "
            "constant this encoding invented"
        )
    unsettled = sorted(
        name for name in names if name in computes and not scope.is_definitely_assigned(name)
    )
    if unsettled:
        raise UnsupportedConstructError(
            "the system declares it computes "
            + ", ".join(repr(name) for name in unsettled)
            + ", but the declared rules do not assign it on every path, so the exposed logic does "
            "not establish the value the property is about"
        )


def _ast_to_z3(node: ast.AST, scope: _Scope) -> Any:
    """Recursively convert a Python AST node to a Z3 expression."""
    if isinstance(node, ast.Expression):
        return _ast_to_z3(node.body, scope)

    if isinstance(node, ast.Constant):
        val = node.value
        if isinstance(val, bool):
            return z3.BoolVal(val)
        if isinstance(val, int):
            return z3.IntVal(val)
        if isinstance(val, float):
            return scope.note_sort(z3.RealVal(val))
        if isinstance(val, str):
            return z3.StringVal(val)
        raise UnsupportedConstructError(f"Unsupported constant type {type(val).__name__}: {val!r}")

    if isinstance(node, ast.Name):
        return scope.read(node.id)

    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_z3(node.operand, scope)
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = _ast_to_z3(node.left, scope)
        right = _ast_to_z3(node.right, scope)
        left, right = _z3_promote(left, right)

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return scope.note_sort(_to_real(left) / _to_real(right))
        if isinstance(node.op, ast.Mod):
            return scope.note_sort(_python_mod(left, right))
        raise UnsupportedConstructError(f"Unsupported binary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BoolOp):
        values = [_ast_to_z3(val, scope) for val in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*values)
        if isinstance(node.op, ast.Or):
            return z3.Or(*values)
        raise UnsupportedConstructError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = _ast_to_z3(node.left, scope)
        z3_ops = []
        curr = left
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            nxt = _ast_to_z3(comparator, scope)
            c_left, c_nxt = _z3_promote(curr, nxt)
            if isinstance(op, ast.Eq):
                z3_ops.append(c_left == c_nxt)
            elif isinstance(op, ast.NotEq):
                z3_ops.append(c_left != c_nxt)
            elif isinstance(op, ast.Lt):
                z3_ops.append(c_left < c_nxt)
            elif isinstance(op, ast.LtE):
                z3_ops.append(c_left <= c_nxt)
            elif isinstance(op, ast.Gt):
                z3_ops.append(c_left > c_nxt)
            elif isinstance(op, ast.GtE):
                z3_ops.append(c_left >= c_nxt)
            else:
                raise UnsupportedConstructError(f"Unsupported comparison: {type(op).__name__}")
            curr = nxt
        return z3.And(*z3_ops) if len(z3_ops) > 1 else z3_ops[0]

    if isinstance(node, ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        if node.keywords:
            raise UnsupportedConstructError(
                f"Keyword arguments are unsupported: {ast.unparse(node)!r}"
            )

        if func_name == PRESENCE_CALL:
            return _present_to_z3(node, scope)

        if func_name == CONTAINS_CALL:
            return _contains_to_z3(node, scope)

        if func_name in ("implies", "Implies"):
            if len(node.args) != 2:
                raise UnsupportedConstructError(
                    f"Implies expects 2 arguments, got {len(node.args)}"
                )
            arg0 = _ast_to_z3(node.args[0], scope)
            arg1 = _ast_to_z3(node.args[1], scope)
            return z3.Implies(arg0, arg1)

        if func_name == "abs":
            if len(node.args) != 1:
                raise UnsupportedConstructError("abs expects 1 argument")
            arg = _ast_to_z3(node.args[0], scope)
            return z3.If(arg >= 0, arg, -arg)

        if func_name in ("min", "max"):
            if len(node.args) != 2:
                raise UnsupportedConstructError(f"{func_name} expects 2 arguments")
            arg0 = _ast_to_z3(node.args[0], scope)
            arg1 = _ast_to_z3(node.args[1], scope)
            arg0, arg1 = _z3_promote(arg0, arg1)
            if func_name == "min":
                return z3.If(arg0 <= arg1, arg0, arg1)
            return z3.If(arg0 >= arg1, arg0, arg1)

        raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def encode_logic_domain(
    logic_data: Any, timeout_ms: int = 5000
) -> tuple[_Scope, z3.Solver, list[str], Any]:
    """Encode a `logic()` payload's constraints and rules into a fresh solver.

    The inputs a system's declared logic and constraints admit, as this engine understands them,
    and nothing else — no property is asserted. `ProvedEngine.evaluate` builds its domain here, and
    so does `reasonsmith.analysis` when it asks a vacuity question against the same domain the
    engine would have quantified over. Extracted rather than copied for the reason the atom methods
    on `_Scope` are methods: two encodings of one system that disagree is the defect this module
    already guards against between itself and the interpreter.
    """
    rules, variables, constraints, declared_computes = read_declared_logic(logic_data)
    scope = _Scope(variables)
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    for c_text in constraints:
        c_z3 = _ast_to_z3(parse_expression(c_text), scope)
        solver.add(_as_bool(c_z3, f"System constraint {c_text!r}"))
    for r_text in rules:
        _encode_block(ast.parse(r_text, mode="exec").body, scope, solver)
    return scope, solver, rules, declared_computes


def _as_bool(expr: Any, what: str) -> Any:
    """Return `expr` if it is a Z3 Boolean, else refuse it as an unsupported construct."""
    if not z3.is_bool(expr):
        raise UnsupportedConstructError(f"{what} is not a boolean property")
    return expr


def _bind(scope: _Scope, name: str, val_z3: Any, solver: z3.Solver, what: str) -> None:
    """Bind a fresh version of `name` to `val_z3`, refusing what the declared sort cannot hold."""
    tgt_z3 = scope.assign(name)
    if isinstance(tgt_z3, z3.ArithRef) and isinstance(val_z3, z3.ArithRef):
        if tgt_z3.is_int() and val_z3.is_real():
            raise UnsupportedConstructError(
                f"{what} gives {name!r} a real value, but {name!r} is declared int. The solver "
                "could only satisfy that by restricting the inputs, which the rules do not do"
            )
        tgt_z3, val_z3 = _z3_promote(tgt_z3, val_z3)
    elif tgt_z3.sort() != val_z3.sort():
        raise UnsupportedConstructError(
            f"{what} gives {name!r} a value of sort {val_z3.sort()}, "
            f"but {name!r} is declared {tgt_z3.sort()}"
        )
    solver.add(tgt_z3 == val_z3)


def _encode_block(stmts: list[ast.stmt], scope: _Scope, solver: z3.Solver) -> None:
    """Encode a rule block into `solver` in static single assignment form."""
    for stmt in stmts:
        if isinstance(stmt, ast.Assign):
            name = assignment_target(stmt)
            val_z3 = _ast_to_z3(stmt.value, scope)
            _bind(scope, name, val_z3, solver, f"Rule {ast.unparse(stmt)!r}")

        elif isinstance(stmt, ast.If):
            test_z3 = _as_bool(
                _ast_to_z3(stmt.test, scope), f"Rule condition {ast.unparse(stmt.test)!r}"
            )
            before = scope.snapshot()

            _encode_block(stmt.body, scope, solver)
            then_state = scope.snapshot()

            scope.restore(before)
            _encode_block(stmt.orelse, scope, solver)
            else_state = scope.snapshot()

            scope.restore(before)
            then_current, then_assigned = then_state
            else_current, else_assigned = else_state
            for name in sorted(set(then_current) | set(else_current)):
                then_val = then_current[name] if name in then_current else scope.read(name)
                else_val = else_current[name] if name in else_current else scope.read(name)
                if z3.eq(then_val, else_val):
                    scope.current[name] = then_val
                    continue
                then_val, else_val = _z3_promote(then_val, else_val)
                _bind(
                    scope,
                    name,
                    z3.If(test_z3, then_val, else_val),
                    solver,
                    f"Branch on {ast.unparse(stmt.test)!r}",
                )
            scope._definitely_assigned = then_assigned & else_assigned

        elif isinstance(stmt, ast.Expr):
            raise UnsupportedConstructError(
                f"A rule statement must decide something: {ast.unparse(stmt)!r} computes a value "
                "and discards it. State an input invariant in `constraints` instead."
            )

        else:
            raise UnsupportedConstructError(
                f"Unsupported rule statement type: {type(stmt).__name__}"
            )


def _extract_model_value(val: Any) -> Any:
    """Extract a native Python value from a Z3 model valuation."""
    if val is None:
        return None
    if z3.is_bool(val):
        return z3.is_true(val)
    if z3.is_int_value(val):
        return val.as_long()
    if z3.is_rational_value(val):
        num = val.numerator_as_long()
        den = val.denominator_as_long()
        res = num / den
        return int(res) if res.is_integer() else res
    if z3.is_algebraic_value(val):
        num_approx = val.approx(6)
        res = num_approx.numerator_as_long() / num_approx.denominator_as_long()
        return int(res) if res.is_integer() else res
    if z3.is_string_value(val):
        return val.as_string()
    try:
        if hasattr(val, "as_long"):
            return val.as_long()
        if hasattr(val, "as_decimal"):
            d = val.as_decimal(6).replace("?", "")
            f = float(d)
            return int(f) if f.is_integer() else f
    except Exception:
        pass
    return str(val)


def _eval_python_spec(spec_text: str, record: dict[str, Any]) -> bool:
    """Evaluate requirement specification expression over a decision record."""
    return bool(eval_expression(parse_property(spec_text), dict(record)))


def _model_inputs(scope: _Scope, model: z3.ModelRef) -> dict[str, Any]:
    """Read the free inputs of a Z3 model back as native Python values."""
    inputs = {}
    for name, const in scope.inputs.items():
        value = _extract_model_value(model[const])
        if value is not None:
            inputs[name] = value
    return inputs


def _values_agree(encoded: Any, computed: Any) -> bool:
    """Compare a Z3 model valuation with an interpreter result, allowing float representation."""
    if isinstance(encoded, bool) or isinstance(computed, bool):
        return encoded is computed
    if isinstance(encoded, (int, float)) and isinstance(computed, (int, float)):
        return math.isclose(encoded, computed, rel_tol=1e-9, abs_tol=1e-9)
    return encoded == computed


def _check_encoding_against_interpreter(
    rules: list[str], scope: _Scope, model: z3.ModelRef
) -> Optional[tuple[str, str]]:
    """Check the Z3 encoding against the reference interpreter on one witness the solver chose.

    Returns `None` when they agree, else the kind of divergence and a message naming the witness.
    """
    env = _model_inputs(scope, model)
    witness = dict(env)
    try:
        for r_text in rules:
            execute_statements(ast.parse(r_text, mode="exec").body, env)
    except Exception as exc:
        return "rules_undefined_on_witness", (
            f"the declared rules are undefined on the inputs {witness}, which the solver is free "
            f"to choose: {exc}. State the invariant the rules rely on in `constraints`"
        )

    for name, const in sorted(scope.current.items()):
        if name not in env:
            continue
        encoded = _extract_model_value(model[const])
        if encoded is None:
            continue
        if not _values_agree(encoded, env[name]):
            return "encoding_mismatch", (
                f"on inputs {witness} the solver's model has {name}={encoded!r} "
                f"while the declared rules compute {name}={env[name]!r}"
            )
    return None


def decision_runner(sut: SystemUnderTest, logic_data: Any) -> tuple[Any, str] | None:
    """How to run one input through this system, and what to call that in a report.

    The system's own `decide()` where it has one; otherwise the declared rules executed by the
    reference interpreter, which is the only other thing here that *is* the system's procedure.
    `None` when neither exists, so a caller can say so in its own words.

    The rules alone, because `decide()` executes nothing else: the type table and the constraint
    list reach only `logic()`, which nothing here calls, while handing them over lets a declaration
    mismatch that has nothing to do with replaying an input refuse the interpreter construction and
    report a reproducible finding not evaluated.
    """
    if hasattr(sut, "decide") and callable(sut.decide):
        return sut.decide, "the system's own decide()"
    if not isinstance(logic_data, dict) or "rules" not in logic_data:
        return None
    from reasonsmith.adapters.rules import RulesAdapter

    return RulesAdapter(rules=logic_data.get("rules", [])).decide, (
        "the declared logic from sut.logic(), executed by the reference rule "
        "interpreter, because the system exposes no decide() to run"
    )


def _verify_counterexample(
    sut: SystemUnderTest,
    req: Requirement,
    ce_inputs: dict[str, Any],
    logic_data: Any,
) -> tuple[bool, str]:
    """Verify that feeding a solver counterexample to the SUT actually reproduces the violation."""
    try:
        runner = decision_runner(sut, logic_data)
        if runner is None:
            return (
                False,
                "System under test provides no decide() method to verify counterexample",
            )
        decide, ran_against = runner
        output_rec = decide(ce_inputs)

        if not isinstance(output_rec, dict):
            return False, f"SUT decide() returned {type(output_rec).__name__}, expected dict"

        spec_holds = _eval_python_spec(req.spec, output_rec)
        if not spec_holds:
            return True, f"Counterexample reproduces the violation against {ran_against}"
        return False, (
            f"Output of {ran_against} on the counterexample input satisfied the requirement "
            "(did not violate)"
        )
    except Exception as exc:
        return False, f"SUT execution on counterexample raised exception: {exc}"


class ProvedEngine:
    """Formal solver engine powered by Z3."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: Optional[list[dict[str, Any]]] = None,
        timeout_ms: int = 5000,
        *,
        logic_data: Any = _UNSET_LOGIC,
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

        if logic_data is _UNSET_LOGIC:
            logic_func = getattr(sut, "logic", None)
            logic_data = logic_func() if callable(logic_func) else None

        if logic_data is None:
            return not_evaluated(
                f"Not evaluated: no decision logic exposed for {req.formalism!r} requirement "
                "(sut.logic() returned None). A formal proof requires explicit system logic.",
                {},
            )

        try:
            read_declared_logic(logic_data)
        except LogicDeclarationError as exc:
            return not_evaluated(exc.summary, exc.details)

        try:
            scope, solver, rules, declared_computes = encode_logic_domain(logic_data, timeout_ms)

            # Every rule is encoded by now, so `scope` knows which names the rules assign — which
            # is what both guards need and why they are asked here rather than while the property
            # is walked, and after it is encoded so that `present()`'s and `contains()`'s more
            # specific refusals win. Both guards run: a `computes` list answers the direction
            # question outright, and the sort heuristic is an *additional* filter, never an
            # alternative one, so a declaration can narrow what reaches the solver and never
            # widen it.
            property_node = parse_property(req.spec)
            spec_z3 = _as_bool(
                _ast_to_z3(property_node, scope),
                f"Requirement spec {req.spec!r}",
            )
            if declared_computes is not None:
                _check_declared_directions(property_node, scope, declared_computes)
            _check_magnitudes_are_computed(property_node, scope)

            premise_check = solver.check()
            premise_reason = (
                solver.reason_unknown() if premise_check == z3.unknown else ""
            ) or "solver returned unknown or timed out"
            premise_model = solver.model() if premise_check == z3.sat else None

        except UnsupportedConstructError as exc:
            return not_evaluated(
                f"Not evaluated: system logic or requirement spec uses unsupported "
                f"construct: {exc}.",
                {"reason": str(exc)},
            )
        except Exception as exc:
            return not_evaluated(
                f"Not evaluated: error parsing decision logic or property {req.spec!r}: {exc}",
                {"error": str(exc)},
            )

        if premise_check == z3.unsat:
            return not_evaluated(
                "Not evaluated: the encoded system logic and constraints admit no input at all, "
                "so the negated property is unsatisfiable for a reason that has nothing to do "
                f"with requirement {req.spec!r}. A vacuous model proves everything and is "
                "therefore reported as no evidence.",
                {"solver": "z3", "result": "unsatisfiable_premises"},
            )

        if premise_check != z3.sat or premise_model is None:
            return not_evaluated(
                f"Not evaluated: formal solver could not decide requirement {req.spec!r}: "
                f"{premise_reason}.",
                {"solver": "z3", "reason_unknown": premise_reason},
            )

        divergence = _check_encoding_against_interpreter(rules, scope, premise_model)
        if divergence is not None:
            kind, message = divergence
            if kind == "rules_undefined_on_witness":
                summary = (
                    f"Not evaluated: {message}. Until then the solver reasons over inputs the "
                    "system has no defined behaviour for, and nothing proved that way is "
                    "evidence about the system."
                )
            else:
                summary = (
                    "Not evaluated: the solver encoding does not agree with the declared logic — "
                    f"{message}. A property proved about an encoding the system does not "
                    "implement is not evidence about the system."
                )
            return not_evaluated(summary, {"solver": "z3", kind: message})

        # The property is checked on a *fresh* solver carrying the same assertions, rather than by
        # adding the negation to the one that just answered the premises. The assertions are
        # identical, so nothing about the claim changes; what changes is that the solver is not
        # already carrying the internal state it built to produce a premise model. For a property
        # over string regular languages that state costs whole seconds — enough to turn this
        # engine's own timeout into the answer — and a proof that depends on whether some earlier
        # query happened to be asked first is a proof that flakes.
        property_solver = z3.Solver()
        property_solver.set("timeout", timeout_ms)
        try:
            property_solver.add(*solver.assertions())
            property_solver.add(z3.Not(spec_z3))
            check_res = property_solver.check()
            unknown_reason = (
                property_solver.reason_unknown() if check_res == z3.unknown else ""
            ) or "solver returned unknown or timed out"
        except Exception as exc:
            return not_evaluated(
                f"Not evaluated: error checking property {req.spec!r}: {exc}",
                {"error": str(exc)},
            )

        if check_res == z3.unsat:
            # `unsat` on the negation is a proof only if there was something to prove. Where the
            # property is an implication whose antecedent no admissible input satisfies, the
            # negation is unsatisfiable because the trigger is unreachable and not because the
            # system settles the consequent — the same shape as the unsatisfiable-premises refusal
            # above, one quantifier deeper, and the same three lines `engines/counterfactual.py`
            # already runs to ask whether an admissible differing pair exists at all. Asked here,
            # on the satisfied path alone: a violated verdict names an input whose antecedent did
            # fire, so vacuity cannot arise on it, and an earned proof pays for one extra check.
            antecedent = implication_antecedent(property_node)
            if antecedent is not None:
                trigger_solver = z3.Solver()
                trigger_solver.set("timeout", timeout_ms)
                try:
                    trigger_solver.add(*solver.assertions())
                    trigger_solver.add(
                        _as_bool(
                            _ast_to_z3(antecedent, scope),
                            f"Antecedent {ast.unparse(antecedent)!r}",
                        )
                    )
                    trigger_res = trigger_solver.check()
                    trigger_unknown = (
                        trigger_solver.reason_unknown() if trigger_res == z3.unknown else ""
                    ) or "solver returned unknown or timed out"
                except Exception as exc:
                    return not_evaluated(
                        "Not evaluated: error checking whether any admissible input reaches the "
                        f"antecedent of {req.spec!r}: {exc}",
                        {"error": str(exc)},
                    )
                if trigger_res == z3.unsat:
                    return not_evaluated_for_unreachable_trigger(
                        req,
                        ast.unparse(antecedent),
                        "the inputs the system's declared logic and constraints admit",
                        {"solver": "z3", "result": "unreachable_antecedent"},
                    )
                if trigger_res != z3.sat:
                    return not_evaluated(
                        "Not evaluated: the solver could not decide whether any admissible input "
                        f"reaches the antecedent of {req.spec!r}: {trigger_unknown}. Until it "
                        "does, `unsat` on the negation is not distinguishable from a trigger that "
                        "never fires, and neither reading may be reported.",
                        {"solver": "z3", "reason_unknown": trigger_unknown},
                    )

            proof_details: dict[str, Any] = {"solver": "z3", "result": "unsat"}
            proof_limits = ""
            if scope.uses_real_arithmetic:
                proof_limits = REAL_ARITHMETIC_LIMIT
                proof_details["limits"] = proof_limits
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.SATISFIED,
                strength=Strength.PROVED,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Proved for all inputs: formal solver verified requirement {req.spec!r} "
                    "holds across all valid inputs under system constraints."
                    + (f" {proof_limits}" if proof_limits else "")
                ),
                details=proof_details,
                binding=req.binding,
                scope=req.scope,
            )

        if check_res == z3.sat:
            ce_inputs = _model_inputs(scope, property_solver.model())
            reproduced, verif_msg = _verify_counterexample(sut, req, ce_inputs, logic_data)
            if reproduced:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.VIOLATED,
                    strength=Strength.PROVED,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Violated: formal solver produced counterexample {ce_inputs} for "
                        f"property {req.spec!r}. {verif_msg}."
                    ),
                    details={
                        "solver": "z3",
                        "counterexample": ce_inputs,
                        "verification": verif_msg,
                    },
                    binding=req.binding,
                    scope=req.scope,
                )

            return not_evaluated(
                f"Not evaluated: solver produced counterexample {ce_inputs}, but "
                f"verification against SUT failed: {verif_msg}. Never report proved from "
                "unverified evidence.",
                {
                    "solver": "z3",
                    "unverified_counterexample": ce_inputs,
                    "verification_error": verif_msg,
                },
            )

        return not_evaluated(
            f"Not evaluated: formal solver could not decide requirement {req.spec!r}: "
            f"{unknown_reason}.",
            {"solver": "z3", "reason_unknown": unknown_reason},
        )
