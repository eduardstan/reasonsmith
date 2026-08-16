"""Rule-based decision system adapter for reasonsmith v0.10.2.

What this module is for:
  Adapts rule-based decision systems exposing explicit decision logic into a SystemUnderTest for
  formal verification via the proved engine.

What a reader must not break:
  - `logic()` must return an honest representation of the system's decision logic (variables,
    rules, constraints, and the `computes` directions below) without hiding or simplifying active
    constraints.
    Why this matters: Formal proofs hold relative to the logic exposed; an incomplete or inaccurate
    logic representation produces false proof verdicts.
  - `decide(inputs)` must evaluate the exact same rules as exposed by `logic()`, and must refuse
    any construct it does not model rather than skipping it.
    Why this matters: Counterexample verification checks Z3 models against `decide()`; if execution
    diverges from `logic()` — including by quietly ignoring a statement — reproduction agrees with
    the solver about a program neither of them was given. Both sides share
    `reasonsmith.rulelang` so the accepted construct set cannot drift apart.
  - `logic()["computes"]` is the *direction* declaration, and it is a subset of `variables`, so the
    two together split every name into three states the proof engine reads: a name in `computes` is
    an **output the system computes**, a name in `variables` but not in `computes` is an **input the
    decision situation supplies**, and a name in neither is one the system **has no notion of**.
    Why this matters: `_Scope.read` in the proved engine declares a free constant for any name it
    meets, so a property naming something the system has no notion of used to be answered from
    numbers nobody computed. The engine can only refuse that if something tells it which names are
    the system's own and which of those it produces, and `variables` is a type table that cannot:
    `approved` is computed and sits in it beside `income`, which is not.
  - This adapter derives `computes` from the assignment targets of its own rules unless the caller
    overrides it, so no RulesAdapter is ever undeclared.
    Why this matters: the premise of this adapter is that `rules` *is* the decision procedure and
    not a paraphrase of one, and under that premise the names the rules assign are exactly the
    names the system computes. Deriving it is therefore not a guess — it is reading the same
    declaration the caller already made. An override is for a caller whose rule set is a faithful
    but partial model of a larger system.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from typing import Any, Optional

from reasonsmith.rulelang import (
    UnsupportedConstructError,
    execute_statements,
    parse_expression,
)
from reasonsmith.sut import BaseSUT


def _extract_names(node: ast.AST) -> set[str]:
    """Extract variable names an AST node reads or writes, excluding callees and module roots."""
    callees: set[int] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            callees.add(id(child.func))
        elif isinstance(child, ast.Attribute):
            root = child.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                callees.add(id(root))

    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and id(child) not in callees
    }


def _assigned_names(node: ast.AST) -> set[str]:
    """Every name a rule block writes, on any path.

    "On any path" and not "on every path": this is the direction declaration — what the system
    *computes* — and a name written in one branch is computed by the system whichever branch runs.
    Whether every path writes it is a different question, asked by the proof engine against the
    encoded rules (`_Scope.is_definitely_assigned`), and a name declared computed that the exposed
    rules do not settle on every path is refused a proof there rather than quietly demoted here.
    """
    return {
        target.id
        for child in ast.walk(node)
        if isinstance(child, ast.Assign)
        for target in child.targets
        if isinstance(target, ast.Name)
    }


class RulesAdapter(BaseSUT):
    """System Under Test adapter for rule-based decision systems."""

    def __init__(
        self,
        rules: list[str] | str,
        variables: Optional[dict[str, str]] = None,
        constraints: Optional[list[str] | str] = None,
        declared_capabilities: Optional[set[str] | Iterable[str]] = None,
        test_inputs: Optional[Iterable[dict[str, Any]]] = None,
        computes: Optional[Iterable[str]] = None,
        frontier_ai_status: str | None = None,
    ):
        if isinstance(rules, str):
            rules = [r.strip() for r in rules.splitlines() if r.strip()]
        self._rules = list(rules)

        if isinstance(constraints, str):
            constraints = [c.strip() for c in constraints.splitlines() if c.strip()]
        self._constraints = list(constraints) if constraints is not None else []

        # Parse rules and constraints exactly as the proved engine does, to discover variable names
        discovered_vars: set[str] = set()
        assigned_vars: set[str] = set()
        for rule in self._rules:
            try:
                tree = ast.parse(rule, mode="exec")
            except SyntaxError:
                continue
            discovered_vars |= _extract_names(tree)
            assigned_vars |= _assigned_names(tree)
        for constraint in self._constraints:
            try:
                discovered_vars |= _extract_names(parse_expression(constraint))
            except (SyntaxError, UnsupportedConstructError):
                pass

        if variables is not None:
            self._variables = dict(variables)
        else:
            self._variables = {v: "real" for v in sorted(discovered_vars)}

        if isinstance(computes, (str, bytes)):
            raise ValueError(
                f"computes must be a collection of names, but {computes!r} is a string, and read "
                "as one it is a set of characters naming nothing this system computes. Pass a "
                "list, set or tuple, even for a single name"
            )
        if computes is None:
            self._computes = set(assigned_vars)
        else:
            try:
                self._computes = set(computes)
            except TypeError as exc:
                raise TypeError(
                    "computes must be a collection of names, but "
                    f"{type(computes).__name__} cannot be iterated"
                ) from exc
        undeclared = sorted(self._computes - set(self._variables))
        if undeclared:
            raise ValueError(
                "computes must name declared variables, but "
                + ", ".join(repr(name) for name in undeclared)
                + " is not in `variables`"
                + (
                    " — the rules assign it, so `variables` is missing a name this system computes"
                    if computes is None
                    else ""
                )
                + ". A name the system computes is a name the system has, so a direction declared "
                "outside the variable table would leave the proof engine unable to tell an output "
                "it cannot see from a name this system has no notion of"
            )

        if declared_capabilities is not None:
            caps = set(declared_capabilities)
        else:
            caps = set(self._variables.keys()) | discovered_vars

        super().__init__(caps, frontier_ai_status=frontier_ai_status)
        self._test_inputs = list(test_inputs) if test_inputs is not None else None

    def logic(self) -> dict[str, Any]:
        """Return decision logic structure for formal verification engines."""
        return {
            "variables": dict(self._variables),
            "rules": list(self._rules),
            "constraints": list(self._constraints),
            "computes": sorted(self._computes),
        }

    def decide(self, case: dict[str, Any]) -> dict[str, Any]:
        """Execute decision rules sequentially on input values in `case`."""
        env: dict[str, Any] = dict(case)

        for rule in self._rules:
            try:
                tree = ast.parse(rule, mode="exec")
            except SyntaxError as exc:
                raise ValueError(f"Invalid rule syntax {rule!r}: {exc}") from exc
            execute_statements(tree.body, env)

        return env

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return decision records over pre-supplied test inputs."""
        if self._test_inputs is None:
            return []
        return [self.decide(case) for case in self._test_inputs]


#: Alias for RulesAdapter
RulesSUT = RulesAdapter
