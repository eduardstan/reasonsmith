"""Proved engine for reasonsmith v0.2.

What this module is for:
  Evaluates logical requirements (`formalism = "logical"`) over decision systems that expose
  their decision logic via `sut.logic()`, using the Z3 SMT solver.

What a reader must not break:
  - Solver outcomes of `unknown`, solver timeouts, or logic containing unsupported constructs MUST
    be reported as NOT EVALUATED (`verdict=INCONCLUSIVE`, `strength=None`), NEVER `satisfied` or
    `proved`.
    Why this matters: Never report `proved` from a solver result you did not obtain. Assuming an
    undecided or unmodelled property holds is the single overclaim this tool exists to prevent.
  - A counterexample model produced by Z3 MUST be verified to reproduce on the system under test
    before reporting `VIOLATED` at strength `PROVED`.
    Why this matters: A counterexample that does not reproduce on the actual system under test is
    worse than none and indicates a model mismatch. If verification fails, report NOT EVALUATED.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Optional

import z3

from reasonsmith.report import RequirementResult
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Strength, Verdict


class UnsupportedConstructError(Exception):
    """Raised when logic or requirement spec uses constructs unsupported by the Z3 encoding."""

    pass


def _preprocess_spec(spec: str) -> str:
    """Preprocess requirement spec text to normalize implication and equivalence operators."""
    s = spec.strip()
    s = re.sub(r"\s*<=>\s*", " == ", s)
    s = re.sub(r"\s*<->\s*", " == ", s)
    s = re.sub(r"\s*=>\s*", " implies ", s)
    s = re.sub(r"\s*->\s*", " implies ", s)
    if " implies " in s:
        parts = s.split(" implies ", 1)
        return f"Implies(({parts[0]}), ({parts[1]}))"
    return s


def _z3_promote(a: Any, b: Any) -> tuple[Any, Any]:
    """Promote Z3 Int to Real if one operand is Real and the other is Int."""
    if isinstance(a, (int, float)) and not isinstance(a, bool):
        a = z3.RealVal(a) if isinstance(b, z3.ArithRef) and b.is_real() else z3.RealVal(a)
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        b = z3.RealVal(b) if isinstance(a, z3.ArithRef) and a.is_real() else z3.RealVal(b)

    if isinstance(a, z3.ArithRef) and isinstance(b, z3.ArithRef):
        if a.is_real() and b.is_int():
            return a, z3.ToReal(b)
        if a.is_int() and b.is_real():
            return z3.ToReal(a), b
    return a, b


def _ast_to_z3(
    node: ast.AST,
    z3_vars: dict[str, Any],
    var_types: dict[str, str],
) -> Any:
    """Recursively convert a Python AST node to a Z3 expression."""
    if isinstance(node, ast.Expression):
        return _ast_to_z3(node.body, z3_vars, var_types)

    if isinstance(node, ast.Constant):
        val = node.value
        if isinstance(val, bool):
            return z3.BoolVal(val)
        if isinstance(val, int):
            return z3.IntVal(val)
        if isinstance(val, float):
            return z3.RealVal(val)
        if isinstance(val, str):
            return z3.StringVal(val)
        raise UnsupportedConstructError(f"Unsupported constant type {type(val).__name__}: {val!r}")

    if isinstance(node, ast.Name):
        name = node.id
        if name == "True":
            return z3.BoolVal(True)
        if name == "False":
            return z3.BoolVal(False)
        if name not in z3_vars:
            vtype = var_types.get(name, "real").lower()
            if vtype in ("int", "integer"):
                z3_vars[name] = z3.Int(name)
            elif vtype in ("bool", "boolean"):
                z3_vars[name] = z3.Bool(name)
            elif vtype in ("str", "string"):
                z3_vars[name] = z3.String(name)
            else:
                z3_vars[name] = z3.Real(name)
        return z3_vars[name]

    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_z3(node.operand, z3_vars, var_types)
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = _ast_to_z3(node.left, z3_vars, var_types)
        right = _ast_to_z3(node.right, z3_vars, var_types)
        left, right = _z3_promote(left, right)

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
        values = [_ast_to_z3(val, z3_vars, var_types) for val in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*values)
        if isinstance(node.op, ast.Or):
            return z3.Or(*values)
        raise UnsupportedConstructError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = _ast_to_z3(node.left, z3_vars, var_types)
        z3_ops = []
        curr = left
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            nxt = _ast_to_z3(comparator, z3_vars, var_types)
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

        if func_name in ("implies", "Implies"):
            if len(node.args) != 2:
                raise UnsupportedConstructError(
                    f"Implies expects 2 arguments, got {len(node.args)}"
                )
            arg0 = _ast_to_z3(node.args[0], z3_vars, var_types)
            arg1 = _ast_to_z3(node.args[1], z3_vars, var_types)
            return z3.Implies(arg0, arg1)

        if func_name == "abs":
            if len(node.args) != 1:
                raise UnsupportedConstructError("abs expects 1 argument")
            arg = _ast_to_z3(node.args[0], z3_vars, var_types)
            return z3.If(arg >= 0, arg, -arg)

        if func_name in ("min", "max"):
            if len(node.args) != 2:
                raise UnsupportedConstructError(f"{func_name} expects 2 arguments")
            arg0 = _ast_to_z3(node.args[0], z3_vars, var_types)
            arg1 = _ast_to_z3(node.args[1], z3_vars, var_types)
            arg0, arg1 = _z3_promote(arg0, arg1)
            if func_name == "min":
                return z3.If(arg0 <= arg1, arg0, arg1)
            return z3.If(arg0 >= arg1, arg0, arg1)

        raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


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
    safe_builtins = {"True": True, "False": False, "abs": abs, "min": min, "max": max}

    def Implies(a: bool, b: bool) -> bool:
        return (not a) or b

    prep = _preprocess_spec(spec_text)
    tree = ast.parse(prep, mode="eval")
    code = compile(tree, "<spec>", "eval")
    env = dict(record)
    env["Implies"] = Implies
    return bool(eval(code, {"__builtins__": safe_builtins}, env))


def _verify_counterexample(
    sut: SystemUnderTest, req: Requirement, ce_inputs: dict[str, Any]
) -> tuple[bool, str]:
    """Verify that feeding a solver counterexample to the SUT actually reproduces the violation."""
    try:
        if hasattr(sut, "decide") and callable(sut.decide):
            output_rec = sut.decide(ce_inputs)
        elif hasattr(sut, "target") and hasattr(sut.target, "decide"):
            output_rec = sut.target.decide(ce_inputs)
        else:
            from reasonsmith.adapters.rules import RulesAdapter

            logic_data = sut.logic()
            if isinstance(logic_data, dict) and "rules" in logic_data:
                temp_adapter = RulesAdapter(
                    rules=logic_data.get("rules", []),
                    variables=logic_data.get("variables"),
                    constraints=logic_data.get("constraints"),
                )
                output_rec = temp_adapter.decide(ce_inputs)
            else:
                return (
                    False,
                    "System under test provides no decide() method to verify counterexample",
                )

        if not isinstance(output_rec, dict):
            return False, f"SUT decide() returned {type(output_rec).__name__}, expected dict"

        spec_holds = _eval_python_spec(req.spec, output_rec)
        if not spec_holds:
            return True, "Counterexample reproduces violation on SUT"
        return False, "SUT output on counterexample input satisfied requirement (did not violate)"
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
    ) -> RequirementResult:
        clause = f"{req.source_document} {req.article_clause}"

        logic_func = getattr(sut, "logic", None)
        logic_data = logic_func() if callable(logic_func) else None

        if logic_data is None:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: no decision logic exposed for {req.formalism!r} requirement "
                    "(sut.logic() returned None). A formal proof requires explicit system logic."
                ),
                binding=req.binding,
                scope=req.scope,
            )

        if isinstance(logic_data, dict):
            rules = logic_data.get("rules", [])
            variables = logic_data.get("variables", {})
            constraints = logic_data.get("constraints", [])
        elif hasattr(logic_data, "rules"):
            rules = getattr(logic_data, "rules", [])
            variables = getattr(logic_data, "variables", {})
            constraints = getattr(logic_data, "constraints", [])
        else:
            tname = type(logic_data).__name__
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=f"Not evaluated: sut.logic() returned unexpected type {tname}.",
                binding=req.binding,
                scope=req.scope,
            )

        z3_vars: dict[str, Any] = {}
        solver = z3.Solver()
        solver.set("timeout", timeout_ms)

        try:
            for c_text in constraints:
                tree = ast.parse(_preprocess_spec(c_text), mode="eval")
                c_z3 = _ast_to_z3(tree, z3_vars, variables)
                solver.add(c_z3)

            for r_text in rules:
                rule_ast = ast.parse(r_text, mode="exec")
                for stmt in rule_ast.body:
                    if isinstance(stmt, ast.Assign):
                        t_name = (
                            stmt.targets[0].id if isinstance(stmt.targets[0], ast.Name) else ""
                        )
                        if not t_name:
                            err = f"Unsupported assignment target in rule {r_text!r}"
                            raise UnsupportedConstructError(err)
                        val_z3 = _ast_to_z3(stmt.value, z3_vars, variables)
                        _ast_to_z3(stmt.targets[0], z3_vars, variables)
                        tgt_z3 = z3_vars[t_name]
                        tgt_z3, val_z3 = _z3_promote(tgt_z3, val_z3)
                        solver.add(tgt_z3 == val_z3)
                    elif isinstance(stmt, ast.If):
                        test_z3 = _ast_to_z3(stmt.test, z3_vars, variables)
                        for b_stmt in stmt.body:
                            if isinstance(b_stmt, ast.Assign) and isinstance(
                                b_stmt.targets[0], ast.Name
                            ):
                                tn = b_stmt.targets[0].id
                                v_z3 = _ast_to_z3(b_stmt.value, z3_vars, variables)
                                _ast_to_z3(b_stmt.targets[0], z3_vars, variables)
                                tg_z3, v_z3 = _z3_promote(z3_vars[tn], v_z3)
                                solver.add(z3.Implies(test_z3, tg_z3 == v_z3))
                        for o_stmt in stmt.orelse:
                            if isinstance(o_stmt, ast.Assign) and isinstance(
                                o_stmt.targets[0], ast.Name
                            ):
                                tn = o_stmt.targets[0].id
                                v_z3 = _ast_to_z3(o_stmt.value, z3_vars, variables)
                                _ast_to_z3(o_stmt.targets[0], z3_vars, variables)
                                tg_z3, v_z3 = _z3_promote(z3_vars[tn], v_z3)
                                solver.add(z3.Implies(z3.Not(test_z3), tg_z3 == v_z3))
                    elif isinstance(stmt, ast.Expr):
                        expr_z3 = _ast_to_z3(stmt.value, z3_vars, variables)
                        solver.add(expr_z3)
                    else:
                        stype = type(stmt).__name__
                        raise UnsupportedConstructError(
                            f"Unsupported rule statement type: {stype}"
                        )

            spec_prep = _preprocess_spec(req.spec)
            spec_ast = ast.parse(spec_prep, mode="eval")
            spec_z3 = _ast_to_z3(spec_ast, z3_vars, variables)

        except UnsupportedConstructError as exc:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: system logic or requirement spec uses unsupported "
                    f"construct: {exc}."
                ),
                details={"reason": str(exc)},
                binding=req.binding,
                scope=req.scope,
            )
        except Exception as exc:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: error parsing decision logic or property {req.spec!r}: {exc}"
                ),
                details={"error": str(exc)},
                binding=req.binding,
                scope=req.scope,
            )

        solver.add(z3.Not(spec_z3))
        check_res = solver.check()

        if check_res == z3.unsat:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.SATISFIED,
                strength=Strength.PROVED,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Proved for all inputs: formal solver verified requirement {req.spec!r} "
                    "holds across all valid inputs under system constraints."
                ),
                details={"solver": "z3", "result": "unsat"},
                binding=req.binding,
                scope=req.scope,
            )

        if check_res == z3.sat:
            m = solver.model()
            ce_inputs = {}
            for name, z_var in z3_vars.items():
                val = m[z_var]
                py_val = _extract_model_value(val)
                if py_val is not None:
                    ce_inputs[name] = py_val

            reproduced, verif_msg = _verify_counterexample(sut, req, ce_inputs)
            if reproduced:
                return RequirementResult(
                    requirement_id=req.id,
                    source_clause=clause,
                    verdict=Verdict.VIOLATED,
                    strength=Strength.PROVED,
                    signals_required=tuple(req.requires),
                    evidence_summary=(
                        f"Violated: formal solver produced counterexample {ce_inputs} for "
                        f"property {req.spec!r}. Counterexample verified against SUT."
                    ),
                    details={
                        "solver": "z3",
                        "counterexample": ce_inputs,
                        "verification": verif_msg,
                    },
                    binding=req.binding,
                    scope=req.scope,
                )

            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: solver produced counterexample {ce_inputs}, but "
                    f"verification against SUT failed: {verif_msg}. Never report proved from "
                    "unverified evidence."
                ),
                details={
                    "solver": "z3",
                    "counterexample": ce_inputs,
                    "verification_error": verif_msg,
                },
                binding=req.binding,
                scope=req.scope,
            )

        reason = solver.reason_unknown() or "solver returned unknown or timed out"
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Not evaluated: formal solver could not decide requirement {req.spec!r}: "
                f"{reason}."
            ),
            details={"solver": "z3", "reason_unknown": reason},
            binding=req.binding,
            scope=req.scope,
        )
