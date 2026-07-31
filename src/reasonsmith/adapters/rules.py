"""Rule-based decision system adapter for reasonsmith v0.2.

What this module is for:
  Adapts rule-based decision systems exposing explicit decision logic into a SystemUnderTest for
  formal verification via the proved engine.

What a reader must not break:
  - `logic()` must return an honest representation of the system's decision logic (variables,
    rules, and constraints) without hiding or simplifying active constraints.
    Why this matters: Formal proofs hold relative to the logic exposed; an incomplete or inaccurate
    logic representation produces false proof verdicts.
  - `decide(inputs)` must evaluate the exact same rules as exposed by `logic()`.
    Why this matters: Counterexample verification checks Z3 models against `decide()`; if execution
    diverges from `logic()`, counterexample reproduction will fail.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from typing import Any, Optional

from reasonsmith.sut import BaseSUT


def _extract_names(node: ast.AST) -> set[str]:
    """Extract variable names from an AST node."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Param):
            # Exclude built-in names or keywords if any
            if child.id not in ("True", "False", "None"):
                names.add(child.id)
    return names


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

        # Parse rules to discover all variable names
        discovered_vars: set[str] = set()
        for stmt in self._rules + self._constraints:
            try:
                tree = ast.parse(stmt, mode="exec")
                discovered_vars |= _extract_names(tree)
            except SyntaxError:
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
        # Standard safe builtins for rule evaluation
        safe_builtins = {"True": True, "False": False, "abs": abs, "min": min, "max": max}

        for rule in self._rules:
            try:
                tree = ast.parse(rule, mode="exec")
            except SyntaxError as exc:
                raise ValueError(f"Invalid rule syntax {rule!r}: {exc}") from exc

            for stmt in tree.body:
                if isinstance(stmt, ast.Assign):
                    val = eval(
                        compile(ast.Expression(stmt.value), "<rule>", "eval"),
                        {"__builtins__": safe_builtins},
                        env,
                    )
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            env[target.id] = val
                elif isinstance(stmt, ast.If):
                    test_val = eval(
                        compile(ast.Expression(stmt.test), "<rule>", "eval"),
                        {"__builtins__": safe_builtins},
                        env,
                    )
                    body_stmts = stmt.body if test_val else stmt.orelse
                    for b_stmt in body_stmts:
                        if isinstance(b_stmt, ast.Assign):
                            val = eval(
                                compile(ast.Expression(b_stmt.value), "<rule>", "eval"),
                                {"__builtins__": safe_builtins},
                                env,
                            )
                            for target in b_stmt.targets:
                                if isinstance(target, ast.Name):
                                    env[target.id] = val
                elif isinstance(stmt, ast.Expr):
                    eval(
                        compile(ast.Expression(stmt.value), "<rule>", "eval"),
                        {"__builtins__": safe_builtins},
                        env,
                    )

        return env

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return decision records over pre-supplied test inputs."""
        if self._test_inputs is None:
            return []
        return [self.decide(case) for case in self._test_inputs]


#: Alias for RulesAdapter
RulesSUT = RulesAdapter
