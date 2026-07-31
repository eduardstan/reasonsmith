"""Rule-based decision system adapter for reasonsmith v0.2.

What this module is for:
  Adapts rule-based decision systems exposing explicit decision logic into a SystemUnderTest for
  formal verification via the proved engine.

What a reader must not break:
  - `logic()` must return an honest representation of the system's decision logic (variables,
    rules, and constraints) without hiding or simplifying active constraints.
    Why this matters: Formal proofs hold relative to the logic exposed; an incomplete or inaccurate
    logic representation produces false proof verdicts.
  - `decide(inputs)` must evaluate the exact same rules as exposed by `logic()`, and must refuse
    any construct it does not model rather than skipping it.
    Why this matters: Counterexample verification checks Z3 models against `decide()`; if execution
    diverges from `logic()` — including by quietly ignoring a statement — reproduction agrees with
    the solver about a program neither of them was given. Both sides share
    `reasonsmith.rulelang` so the accepted construct set cannot drift apart.
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


class RulesAdapter(BaseSUT):
    """System Under Test adapter for rule-based decision systems."""

    def __init__(
        self,
        rules: list[str] | str,
        variables: Optional[dict[str, str]] = None,
        constraints: Optional[list[str] | str] = None,
        declared_capabilities: Optional[set[str] | Iterable[str]] = None,
        test_inputs: Optional[Iterable[dict[str, Any]]] = None,
    ):
        if isinstance(rules, str):
            rules = [r.strip() for r in rules.splitlines() if r.strip()]
        self._rules = list(rules)

        if isinstance(constraints, str):
            constraints = [c.strip() for c in constraints.splitlines() if c.strip()]
        self._constraints = list(constraints) if constraints is not None else []

        # Parse rules and constraints exactly as the proved engine does, to discover variable names
        discovered_vars: set[str] = set()
        for rule in self._rules:
            try:
                discovered_vars |= _extract_names(ast.parse(rule, mode="exec"))
            except SyntaxError:
                pass
        for constraint in self._constraints:
            try:
                discovered_vars |= _extract_names(parse_expression(constraint))
            except (SyntaxError, UnsupportedConstructError):
                pass

        if variables is not None:
            self._variables = dict(variables)
        else:
            self._variables = {v: "real" for v in sorted(discovered_vars)}

        if declared_capabilities is not None:
            caps = set(declared_capabilities)
        else:
            caps = set(self._variables.keys()) | discovered_vars

        super().__init__(caps)
        self._test_inputs = list(test_inputs) if test_inputs is not None else None

    def logic(self) -> dict[str, Any]:
        """Return decision logic structure for formal verification engines."""
        return {
            "variables": dict(self._variables),
            "rules": list(self._rules),
            "constraints": list(self._constraints),
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
