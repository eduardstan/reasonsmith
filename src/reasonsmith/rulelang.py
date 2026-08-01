"""Shared rule and specification mini-language for reasonsmith v0.2.

What this module is for:
  Rule text and requirement specs arrive as strings from pack TOML files and from adapter
  constructors. This module is the one place that parses, rewrites and executes that text, so the
  Z3 encoding in `engines/proved.py` and the reference interpreter in `adapters/rules.py` agree on
  exactly which constructs exist.

  It is also the one property language every requirement's `spec` is written in. A `spec` used to
  mean two unrelated things — a formula for `temporal` and `logical`, free English prose for
  `record` that no engine read — so a reader met prose and an STL formula in the same field.
  `classify_fragment` names which fragment of this one language a spec belongs to, the pack loader
  refuses a spec whose fragment is not the one the pack declared, and the English moved to the
  `rationale` field, which means prose. What a requirement *says* is now separate from what
  evidence discharges it: see `report.evaluate_requirement`, which searches for the strongest
  engine the fragment and the system's exposed surface allow.

What a reader must not break:
  - Nothing here may call `eval`, `exec` or `compile`. Pack files are data supplied by third
    parties; a pack that can run arbitrary Python is a pack that can do anything the user can.
    Why this matters: `{"__builtins__": ...}` is not a sandbox — `().__class__.__base__` walks out
    of it — so the whitelist has to be the interpreter itself, not the name table handed to one.
  - Every construct this module refuses must raise `UnsupportedConstructError`, never be skipped.
    Why this matters: a silently dropped statement makes the solver prove a property about logic
    the author did not write, which is reported as `proved` and is therefore an overclaim.
  - The set of constructs accepted here and the set encoded in `engines/proved.py` must stay the
    same set.
    Why this matters: counterexample verification runs the interpreter against the solver's model.
    If one side models a statement the other drops, verification agrees with itself about the
    wrong program.
  - `classify_fragment` names the *narrowest* fragment a spec belongs to, and the loader demands
    an exact match rather than a compatible one. A presence conjunction is also a well-formed
    `logical` property, so a lenient check would let one be declared `logical` and lose the record
    engine's per-signal, per-record diagnostics for nothing.
    Why this matters: the fragment is what decides which engines may discharge the duty. A
    fragment nobody checks is the silent downgrade this field was introduced to end.
"""

from __future__ import annotations

import ast
from typing import Any

_EQUIVALENCE_TOKENS = ("<=>", "<->")
_IMPLICATION_TOKENS = ("=>", "->", " implies ")

#: The atom asking whether a decision record carries a value for a signal at all.
PRESENCE_CALL = "present"

#: The temporal operators of the language, in the prefix call form a Python parser accepts.
#: rtamt's infix `until` and `since` are deliberately absent: they do not parse here, so a spec
#: using one is refused at load time rather than accepted into a fragment nothing can classify.
TEMPORAL_OPERATORS = frozenset(
    {"always", "eventually", "once", "historically", "next", "prev", "rise", "fall"}
)

#: The non-temporal function calls, with their arity.
VALUE_CALLS = {"implies": 2, "Implies": 2, "abs": 1, "min": 2, "max": 2}

#: The fragments of this language, narrowest first. `record` is a conjunction of presence atoms;
#: `logical` is any other state property of one decision record; `temporal` is anything reaching
#: across records with a temporal operator.
FRAGMENTS = ("record", "logical", "temporal")

#: The fragments that are properties of a single decision record, and can therefore be discharged
#: by an engine that reasons about one decision at a time (the solver, the replay search) as well
#: as by reading a trace.
STATE_FRAGMENTS = ("record", "logical")


def is_present(value: Any) -> bool:
    """True when a trace value carries something, not merely a key.

    A missing key, None, a blank string and an empty list/dict/set all mean the system
    emitted nothing for that signal. Only the first of those is caught by a key check,
    and only the first two by a truthiness check on `str(value)` — `str([])` is `"[]"`,
    which is why an empty reason list would otherwise pass as a reason given.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


class UnsupportedConstructError(Exception):
    """Raised when rule or specification text uses a construct this language does not model."""

    pass


def _string_mask(text: str) -> list[bool]:
    """Mark every character that lies inside a string literal, quotes included."""
    mask = [False] * len(text)
    quote = ""
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            mask[i] = True
            if char == "\\":
                if i + 1 < len(text):
                    mask[i + 1] = True
                i += 2
                continue
            if char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
            mask[i] = True
        i += 1
    if quote:
        raise UnsupportedConstructError(f"Unterminated string literal in {text!r}")
    return mask


def _find_top_level(text: str, token: str, start: int = 0) -> int:
    """Return the index of `token` outside every parenthesis group and string literal, or -1."""
    in_string = _string_mask(text)
    depth = 0
    for i in range(start, len(text)):
        if in_string[i]:
            continue
        char = text[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise UnsupportedConstructError(f"Unbalanced parentheses in {text!r}")
        elif depth == 0 and text.startswith(token, i):
            return i
    return -1


def _find_first_top_level(text: str, tokens: tuple[str, ...]) -> tuple[int, str]:
    """Return the leftmost top-level occurrence of any of `tokens` as (index, token)."""
    best_index, best_token = -1, ""
    for token in tokens:
        index = _find_top_level(text, token)
        if index >= 0 and (best_index < 0 or index < best_index):
            best_index, best_token = index, token
    return best_index, best_token


def _rewrite_groups(text: str) -> str:
    """Rewrite arrows inside each top-level parenthesis group, leaving the rest untouched."""
    in_string = _string_mask(text)
    out: list[str] = []
    i = 0
    while i < len(text):
        if in_string[i] or text[i] != "(":
            out.append(text[i])
            i += 1
            continue
        depth = 0
        j = i
        while j < len(text):
            if in_string[j]:
                j += 1
                continue
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            raise UnsupportedConstructError(f"Unbalanced parentheses in {text!r}")
        out.append("(" + _rewrite_arrows(text[i + 1 : j]) + ")")
        i = j + 1
    return "".join(out)


def _rewrite_arrows(text: str) -> str:
    """Rewrite `<=>`/`<->` and `=>`/`->` into Python-parsable form, respecting parentheses."""
    index, token = _find_first_top_level(text, _EQUIVALENCE_TOKENS)
    if index >= 0:
        after = index + len(token)
        for other in _EQUIVALENCE_TOKENS:
            if _find_top_level(text, other, after) >= 0:
                raise UnsupportedConstructError(
                    f"Chained equivalence in {text!r} is ambiguous: parenthesise one side"
                )
        return f"(({_rewrite_sub(text[:index], text)}) == ({_rewrite_sub(text[after:], text)}))"

    index, token = _find_first_top_level(text, _IMPLICATION_TOKENS)
    if index >= 0:
        after = index + len(token)
        left = _rewrite_sub(text[:index], text)
        right = _rewrite_sub(text[after:], text)
        return f"Implies(({left}), ({right}))"

    return _rewrite_groups(text)


def _rewrite_sub(part: str, whole: str) -> str:
    """Rewrite one side of an arrow, refusing an empty side."""
    if not part.strip():
        raise UnsupportedConstructError(f"Missing operand around an arrow in {whole!r}")
    return _rewrite_arrows(part)


def preprocess_spec(spec: str) -> str:
    """Normalise implication and equivalence operators into Python-parsable expression text."""
    return _rewrite_arrows(spec.strip())


def parse_expression(text: str) -> ast.Expression:
    """Parse specification or constraint text into an AST after arrow normalisation."""
    return ast.parse(preprocess_spec(text), mode="eval")


def parse_property(text: str) -> ast.Expression:
    """Parse a requirement `spec` and refuse every construct outside this language.

    `parse_expression` answers only whether Python could parse the text. This is the gate a
    requirement passes: it refuses `"Record check"` and `"not a property !@#$"` alike, naming
    what it found, so a spec that is prose can no longer sit in a field that means something
    executable.
    """
    try:
        node = parse_expression(text)
    except SyntaxError as exc:
        raise UnsupportedConstructError(
            f"{text!r} is not a property in this language: {exc.msg}. A requirement's `spec` is a "
            "formula; English belongs in `rationale`."
        ) from exc
    validate_property(node)
    return node


def _require_kind(kind: str, expected: str, node: ast.AST) -> None:
    if kind not in (expected, "unknown"):
        raise UnsupportedConstructError(
            f"{ast.unparse(node)!r} has type {kind}, expected {expected}"
        )


def expression_kind(node: ast.AST) -> str:
    """Return the language-level kind of an expression, checking its typed positions."""
    if isinstance(node, ast.Expression):
        return expression_kind(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "boolean"
        if isinstance(node.value, (int, float)):
            return "number"
        if isinstance(node.value, str):
            return "string"
        if node.value is None:
            return "none"
        raise UnsupportedConstructError(
            f"Unsupported constant type {type(node.value).__name__}: {node.value!r}"
        )

    if isinstance(node, ast.Name):
        return "unknown"

    if isinstance(node, ast.UnaryOp):
        operand_kind = expression_kind(node.operand)
        if isinstance(node.op, ast.Not):
            _require_kind(operand_kind, "boolean", node.operand)
            return "boolean"
        if isinstance(node.op, (ast.USub, ast.UAdd)):
            _require_kind(operand_kind, "number", node.operand)
            return "number"
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod)):
            raise UnsupportedConstructError(
                f"Unsupported binary operator: {type(node.op).__name__}"
            )
        left_kind = expression_kind(node.left)
        right_kind = expression_kind(node.right)
        _require_kind(left_kind, "number", node.left)
        _require_kind(right_kind, "number", node.right)
        return "number"

    if isinstance(node, ast.BoolOp):
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise UnsupportedConstructError(
                f"Unsupported boolean operator: {type(node.op).__name__}"
            )
        for value in node.values:
            _require_kind(expression_kind(value), "boolean", value)
        return "boolean"

    if isinstance(node, ast.Compare):
        for op in node.ops:
            if not isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                raise UnsupportedConstructError(f"Unsupported comparison: {type(op).__name__}")
        expression_kind(node.left)
        for comparator in node.comparators:
            expression_kind(comparator)
        return "boolean"

    if isinstance(node, ast.Call):
        if node.keywords:
            raise UnsupportedConstructError(
                f"Keyword arguments are unsupported: {ast.unparse(node)!r}"
            )
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name == PRESENCE_CALL:
            # A signal name, not an expression: `present(x)` asks whether the record carries a
            # value for the signal called x, and there is no such question about a computed value.
            if len(node.args) != 1 or not isinstance(node.args[0], ast.Name):
                raise UnsupportedConstructError(
                    f"{PRESENCE_CALL}() takes one signal name: {ast.unparse(node)!r}"
                )
            return "boolean"
        if name in TEMPORAL_OPERATORS:
            if len(node.args) != 1:
                raise UnsupportedConstructError(
                    f"{name} takes one operand, got {len(node.args)}: {ast.unparse(node)!r}"
                )
            _require_kind(expression_kind(node.args[0]), "boolean", node.args[0])
            return "boolean"
        arity = VALUE_CALLS.get(name)
        if arity is None:
            raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")
        if len(node.args) != arity:
            raise UnsupportedConstructError(
                f"{name} expects {arity} argument(s), got {len(node.args)}"
            )
        kinds = [expression_kind(argument) for argument in node.args]
        expected_kind = "boolean" if name in ("implies", "Implies") else "number"
        for argument, kind in zip(node.args, kinds, strict=True):
            _require_kind(kind, expected_kind, argument)
        return expected_kind

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def validate_property(node: ast.AST) -> None:
    """Refuse a parsed expression that is not a Boolean property in this language."""
    kind = expression_kind(node)
    if kind not in ("boolean", "unknown"):
        raise UnsupportedConstructError(
            f"Requirement spec {ast.unparse(node)!r} is not a boolean property"
        )


def presence_atoms(node: ast.AST) -> tuple[str, ...] | None:
    """The signal names of a property that is a conjunction of `present()` atoms, else None.

    `None` is the answer for every other shape, including `present(a) or present(b)` and
    `present(a) and x > 1`: the record engine walks this conjunction to name which conjunct
    failed, and it can only do that for a conjunction.
    """
    if isinstance(node, ast.Expression):
        return presence_atoms(node.body)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == PRESENCE_CALL
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
    ):
        return (node.args[0].id,)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        names: list[str] = []
        for value in node.values:
            part = presence_atoms(value)
            if part is None:
                return None
            names.extend(part)
        return tuple(names)
    return None


def signal_names(node: ast.AST) -> tuple[str, ...]:
    """Every signal name a property reads, sorted, excluding the names of its function calls."""
    called = {
        id(call.func)
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }
    return tuple(
        sorted(
            {
                name.id
                for name in ast.walk(node)
                if isinstance(name, ast.Name) and id(name) not in called
            }
        )
    )


def bare_boolean_names(node: ast.AST) -> tuple[str, ...]:
    """Signal names used directly where the property language requires a Boolean value."""
    names: set[str] = set()

    def visit(current: ast.AST, boolean_position: bool = False) -> None:
        if isinstance(current, ast.Expression):
            visit(current.body, True)
        elif isinstance(current, ast.Name):
            if boolean_position:
                names.add(current.id)
        elif isinstance(current, ast.UnaryOp):
            visit(current.operand, isinstance(current.op, ast.Not))
        elif isinstance(current, ast.BinOp):
            visit(current.left)
            visit(current.right)
        elif isinstance(current, ast.BoolOp):
            for value in current.values:
                visit(value, True)
        elif isinstance(current, ast.Compare):
            visit(current.left)
            for comparator in current.comparators:
                visit(comparator)
        elif isinstance(current, ast.Call):
            name = current.func.id if isinstance(current.func, ast.Name) else ""
            if name in TEMPORAL_OPERATORS or name in ("implies", "Implies"):
                for argument in current.args:
                    visit(argument, True)
            elif name != PRESENCE_CALL:
                for argument in current.args:
                    visit(argument)

    visit(node)
    return tuple(sorted(names))


def has_temporal_operator(node: ast.AST) -> bool:
    """True when a property reaches across records with one of `TEMPORAL_OPERATORS`."""
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id in TEMPORAL_OPERATORS
        for child in ast.walk(node)
    )


def classify_fragment(spec: str) -> str:
    """The narrowest fragment of this language `spec` belongs to.

    `temporal` when anything in it reaches across records; `record` when it is a conjunction of
    presence atoms and nothing else; `logical` for every other well-formed state property. Raises
    `UnsupportedConstructError` for text that is not in the language at all.
    """
    node = parse_property(spec)
    if has_temporal_operator(node):
        return "temporal"
    return "record" if presence_atoms(node) is not None else "logical"


def _implies(antecedent: Any, consequent: Any) -> bool:
    return (not antecedent) or bool(consequent)


def eval_expression(node: ast.AST, env: dict[str, Any]) -> Any:
    """Evaluate a whitelisted expression AST against `env` without invoking the Python compiler."""
    if isinstance(node, ast.Expression):
        return eval_expression(node.body, env)

    if isinstance(node, ast.Constant):
        if node.value is None or isinstance(node.value, (bool, int, float, str)):
            return node.value
        raise UnsupportedConstructError(
            f"Unsupported constant type {type(node.value).__name__}: {node.value!r}"
        )

    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise NameError(f"name {node.id!r} is not defined for this decision")

    if isinstance(node, ast.UnaryOp):
        operand = eval_expression(node.operand, env)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = eval_expression(node.left, env)
        right = eval_expression(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise UnsupportedConstructError(f"Unsupported binary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in node.values:
                result = eval_expression(value, env)
                if not result:
                    return result
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for value in node.values:
                result = eval_expression(value, env)
                if result:
                    return result
            return result
        raise UnsupportedConstructError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = eval_expression(node.left, env)
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            right = eval_expression(comparator, env)
            if isinstance(op, ast.Eq):
                held = left == right
            elif isinstance(op, ast.NotEq):
                held = left != right
            elif isinstance(op, ast.Lt):
                held = left < right
            elif isinstance(op, ast.LtE):
                held = left <= right
            elif isinstance(op, ast.Gt):
                held = left > right
            elif isinstance(op, ast.GtE):
                held = left >= right
            else:
                raise UnsupportedConstructError(f"Unsupported comparison: {type(op).__name__}")
            if not held:
                return False
            left = right
        return True

    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if node.keywords:
            raise UnsupportedConstructError(
                f"Keyword arguments are unsupported: {ast.unparse(node)!r}"
            )
        if name == PRESENCE_CALL:
            # Asked before the argument is evaluated, and answered without raising: a signal the
            # record does not carry is exactly what this atom is for, and resolving the name
            # first would turn "absent" into a NameError.
            if len(node.args) != 1 or not isinstance(node.args[0], ast.Name):
                raise UnsupportedConstructError(
                    f"{PRESENCE_CALL}() takes one signal name: {ast.unparse(node)!r}"
                )
            return is_present(env.get(node.args[0].id))
        args = [eval_expression(arg, env) for arg in node.args]
        if name in ("implies", "Implies"):
            _require_arity(name, args, 2)
            return _implies(args[0], args[1])
        if name == "abs":
            _require_arity(name, args, 1)
            return abs(args[0])
        if name == "min":
            _require_arity(name, args, 2)
            return min(args[0], args[1])
        if name == "max":
            _require_arity(name, args, 2)
            return max(args[0], args[1])
        raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def _require_arity(name: str, args: list[Any], expected: int) -> None:
    if len(args) != expected:
        raise UnsupportedConstructError(
            f"{name} expects {expected} argument(s), got {len(args)}"
        )


def assignment_target(stmt: ast.Assign) -> str:
    """Return the single name a rule assignment writes to, refusing every other target form."""
    if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
        raise UnsupportedConstructError(
            f"Unsupported assignment target in rule: {ast.unparse(stmt)!r}"
        )
    return stmt.targets[0].id


def execute_statements(stmts: list[ast.stmt], env: dict[str, Any]) -> None:
    """Execute a whitelisted rule block against `env`, mutating it in place."""
    for stmt in stmts:
        if isinstance(stmt, ast.Assign):
            env[assignment_target(stmt)] = eval_expression(stmt.value, env)
        elif isinstance(stmt, ast.If):
            branch = stmt.body if eval_expression(stmt.test, env) else stmt.orelse
            execute_statements(branch, env)
        elif isinstance(stmt, ast.Expr):
            raise UnsupportedConstructError(
                f"A rule statement must decide something: {ast.unparse(stmt)!r} computes a value "
                "and discards it. State an input invariant in `constraints` instead."
            )
        else:
            raise UnsupportedConstructError(
                f"Unsupported rule statement type: {type(stmt).__name__}"
            )
