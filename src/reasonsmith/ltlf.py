"""A finite-trace decision procedure for the temporal fragment using the BLACK solver.

What this module is for:
  `analysis.py` decides a pack's questions — joint satisfiability, entailment, equivalence — with
  Z3, over one decision record. A `temporal` spec is not a property of one record, so the analysis
  reduced the one shape that is — `always(f)`, through
  `engines/temporal.state_property_under_always` — and reported every other shape skipped.
  `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` is written with `until`; nothing in
  `validate-pack --analyse` could say anything about it at all.

  This module answers those questions for the whole fragment by handing the formula to a published
  LTLf decision procedure. It is **a syntax mapping and an emptiness question, and nothing else** —
  the same discipline `engines/observed.to_stl` observes for rtamt. **BLACK** `[@geatti-2019]`
  (MIT) decides LTL, LTL+Past and LTLf by a SAT-based one-pass tree-shaped tableau, over the
  finite-trace semantics of `[@degiacomo-2013]`. BLACK is invoked as a subprocess behind a strict
  boundary: the binary is identified from its own `--version` output before it is used, because
  `black` on a Python developer's PATH is usually the code formatter, and anything the solver
  prints that is not exactly `SAT` or `UNSAT` is a refusal rather than a guess.

  What was priced against it, so the choice is reconstructible rather than asserted. `flloat`
  `[@flloat]` was the previous backend and is pure Python on PyPI, which is what it was chosen
  for; it has no past operators, its DFA construction is an exponential powerset that
  `ATOM_BUDGET` had to be set around, and its licence is inconsistent at the source in the three
  ways that entry records. **LTLf2DFA** and **Lydia** compile LTLf to a minimal DFA through
  **MONA**, which is a native package (`apt install mona`) and not a wheel. **Spot** is mature and
  likewise not on PyPI. **nuXmv** is free for non-commercial use only and must not go on a
  dependency path at all. BLACK is the one candidate that decides the whole fragment under a
  licence this repository can depend on; it is paid for in publishing no wheel, so the extra is a
  binary a user installs by hand and its absence is first-class rather than worked around.

The mathematics of trace pinning:
  The production surface needs satisfiability and entailment, which BLACK natively answers:
    entails(l, r) <==> not SAT(l and not r)

  accepts(phi, sigma) — whether a concrete trace sigma satisfies formula phi — is re-encoded as
  a satisfiability question over the trace's characteristic formula pin(sigma).

  Fix the finite atom set AP. LTLf is interpreted over finite traces
  sigma = sigma_0 ... sigma_{n-1} with sigma_i <= AP. BLACK's `wX` is the weak next used for
  the language's `next`; the strong `X` remains available for pinning a concrete trace, and
  Last == !X True holds exactly at the final position.

  Complete literal at a position:
    lambda_i := AND_{a in sigma_i} a  and  AND_{a in AP \\ sigma_i} !a

  Characteristic formula:
    pin(sigma) := AND_{i=0}^{n-1} X^i lambda_i  and  X^{n-1} Last

  Proposition. L(pin(sigma)) = {sigma} over the alphabet 2^AP.
  Proof. (=>) Position i exists in sigma for every i < n and lambda_i holds there by construction,
  so sigma |= X^i lambda_i; position n-1 exists and has no successor, so sigma |= X^{n-1} Last.
  (<=) Let tau |= pin(sigma) with |tau| = m. X^{n-1} Last requires position n-1 to exist, so m >= n;
  Last there requires no successor, so m = n. Each X^i lambda_i then forces tau_i = sigma_i because
  lambda_i is complete over AP. Hence tau = sigma. Q.E.D.

  Corollary. accepts(phi, sigma) <==> SAT(phi and pin(sigma)).

Empty trace semantics:
  BLACK interprets LTLf formulas over non-empty finite traces (length >= 1), where position 0
  always exists. Unlike flloat, BLACK excludes the empty trace natively, so no additional
  `NON_EMPTY` guard formula is required.

Atom ceiling:
  `ATOM_BUDGET` is set to 100, and it is an **unmeasured** bound rather than a measured one.
  LTLf satisfiability is PSPACE-complete and BLACK's tableau is worst-case exponential, so no
  atom count is a runtime guarantee; what changed from the flloat-era 6 is the encoding, since
  pin(sigma) grows linearly in n*|AP| where flloat built a powerset DFA. It is the only bound
  `_decide` has, because there is no wall clock anywhere in this package.

What a reader must not break:
  - **Every backend adapter certifies that it consumed the whole rendered formula and produced
    exactly one property, or the requirement is reported `not evaluated`.** For LTLf, `to_ltlf`
    parses `spec` via `rulelang.parse_property`, which validates that the requirement's spec is
    a single well-formed AST expression before rendering.
  - **rtamt keeps every magnitude; this keeps every qualitative question.** The two backends are
    not interchangeable, and the split is not a preference. rtamt monitors a real-valued signal and
    scores robustness; LTLf is propositional, so every comparison of magnitudes here becomes one
    opaque Boolean atom and `x <= 30` bears no relation to `x <= 90`. That abstraction is **sound
    for the entailments it reports and incomplete for the ones it does not**, exactly as
    `analysis._PackScope` already says of the record atoms — and it is *unsound in the other
    direction for satisfiability*, which is why `satisfiable()` is only ever used to report a pack
    consistent, never to report one contradictory. `LTLF_ABSTRACTION_LIMIT` states it on every
    answer that rests on it.
  - **The extra is optional and its absence is reported, never worked around.** With BLACK absent,
    `available()` is False and the analysis says so in a note; nothing degrades to a weaker
    answer presented as the same one.
    (`test_the_analysis_says_so_when_the_extra_is_absent`)
  - **Only the future fragment.** BLACK is given LTLf formulas in the future fragment, so a spec
    using `once`, `historically`, `prev`, `since`, `rise` or `fall` is refused **by name** into the
    analysis' `skipped` list. Rendering one into a future operator would be implementing its
    semantics. (`test_a_past_operator_is_skipped_by_name_rather_than_rendered`)
  - **Every question is asked over a non-empty trace.** BLACK interprets LTLf over non-empty
    traces natively.
  - **A solver that misbehaves is refused on that question, and takes nothing else down with it.**
    A binary that passes identification and then prints both answers, prints neither, exits
    nonzero or dies on a signal raises `UnsupportedConstructError` — the same class the timeout and
    the atom budget raise, and the one every call site in `analysis.py` already turns into a named
    entry in `PackAnalysis.skipped`. These were `RuntimeError`, which nothing caught: the question
    was described here as a refusal and was in fact a traceback out of `validate-pack --analyse`,
    taking the Z3 half of the analysis — which never touched the solver — down with it.
    (`test_a_misbehaving_solver_is_skipped_and_the_rest_of_the_analysis_survives`)
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Sequence

from reasonsmith.rulelang import (
    BOUNDED_RESPONSE_CALL,
    CONTAINS_CALL,
    COUNTERFACTUAL_CALL,
    EQUIVALENCE_CALL,
    IMPLICATION_CALLS,
    PRESENCE_CALL,
    TEMPORAL_OPERATORS,
    UnsupportedConstructError,
    parse_property,
)

__all__ = [
    "ATOM_BUDGET",
    "Abstraction",
    "LTLF_ABSTRACTION_LIMIT",
    "LTLF_EXTRA",
    "UNAVAILABLE_NOTE",
    "accepts",
    "atom_count",
    "available",
    "entails",
    "satisfiable",
    "to_ltlf",
]

#: The name of the optional dependency group for temporal analysis.
LTLF_EXTRA = "ltlf"

#: What the analysis prints when the BLACK solver is not installed or available.
UNAVAILABLE_NOTE = (
    "temporal decision procedure: not installed (BLACK solver binary not found on PATH). "
    "Install BLACK from your system package manager or https://www.black-sat.org. "
    "Nothing was answered from a weaker substitute."
)

#: The limit every answer from this module carries, for the reason `MUTATION_LIMIT` is carried on
#: the score that rests on it.
LTLF_ABSTRACTION_LIMIT = (
    "Limit of these temporal answers: LTLf is propositional, so every comparison of magnitudes is "
    "one opaque atom here and `x <= 30` bears no relation to `x <= 90`. An entailment or "
    "equivalence reported holds under every interpretation of those atoms and therefore for every "
    "system; two duties it does not relate are not thereby distinguishable by any system. "
    "Satisfiability is reported only in the affirmative for the same reason: a model this finds "
    "may assign the atoms an arithmetic no system could produce, so an unsatisfiable answer would "
    "not be a claim about the pack."
)

#: The most propositional atoms **one question** may carry before it is refused by name.
#: This is an **unmeasured** bound and is stated as one: LTLf satisfiability is PSPACE-complete
#: and BLACK's tableau is worst-case exponential in the formula, so no atom count is a runtime
#: guarantee. It was raised from the flloat-era 6 because the encoding pin(sigma) hands BLACK
#: grows linearly (n*|AP| literals) where flloat built a powerset automaton, and it is the only
#: bound `_decide` has — there is no wall clock anywhere in this package. Lower it if a question
#: at this size is found not to return; do not raise it on the strength of this comment.
ATOM_BUDGET = 100

#: The rulelang operators BLACK has, and their LTLf spelling.
#: Runtime ``next`` is weak at the final position, so use BLACK's native weak-next operator.
_UNARY_RENDERING = {"always": "G", "eventually": "F", "next": "wX"}
_BINARY_RENDERING = {"until": "U"}

#: The operators of the language BLACK is not handed here. LTLf is the future fragment;
#: each of these needs the past, and rendering one into a future operator would be
#: implementing its semantics.
_PAST_OPERATORS = TEMPORAL_OPERATORS - set(_UNARY_RENDERING) - set(_BINARY_RENDERING)


@lru_cache(maxsize=None)
def _verify_black_binary(path: str) -> bool:
    try:
        res = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode != 0:
            return False
        output = res.stdout + res.stderr
        return "BLACK" in output and (
            "Bounded" in output or "sAtisfiability" in output or "black-sat" in output
        )
    except Exception:
        return False


def _get_black_path() -> str | None:
    env_path = (
        os.getenv("BLACK_SAT_PATH")
        or os.getenv("BLACK_PATH")
        or os.getenv("BLACK_EXECUTABLE")
    )
    if env_path:
        if _verify_black_binary(env_path):
            return env_path
        return None

    for candidate_name in ["black-sat", "black"]:
        candidate = shutil.which(candidate_name)
        if candidate and _verify_black_binary(candidate):
            return candidate
    return None


def available() -> bool:
    """Whether the optional BLACK decision procedure is installed and identifiable."""
    return _get_black_path() is not None


def _run_black(formula: str, timeout: int = 30) -> bool:
    path = _get_black_path()
    if not path:
        raise UnsupportedConstructError("the BLACK solver is not available")
    try:
        res = subprocess.run(
            [path, "solve", "--finite", "-f", formula],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        raise UnsupportedConstructError(f"BLACK solver timed out after {timeout} seconds") from err
    except Exception as err:
        raise UnsupportedConstructError(f"the BLACK solver could not be executed: {err}") from err

    if res.returncode != 0:
        err_msg = res.stderr.strip() or res.stdout.strip()
        raise UnsupportedConstructError(
            f"the BLACK solver failed with exit code {res.returncode}: {err_msg}"
        )

    out = res.stdout.strip()
    if out == "SAT":
        return True
    if out == "UNSAT":
        return False
    raise UnsupportedConstructError(f"unexpected output from the BLACK solver: {out!r}")


@dataclass
class Abstraction:
    """The propositional atoms a set of formulas share, and the axioms relating them.

    One instance abstracts a whole pack, so the same subexpression is the same atom in every
    formula — which is what makes an entailment between two requirements mean anything. The only
    relation asserted between atoms is the one `analysis._PackScope` already asserts in Z3: a value
    the record does not carry contains no phrase, here as `G(contains -> present)` because it holds
    at every position of the trace.
    """

    atoms: dict[str, str] = field(default_factory=dict)
    axioms: list[str] = field(default_factory=list)

    def atom(self, key: str) -> str:
        """The propositional letter standing for `key`, minted on first sight.

        The letter is synthetic rather than the signal's own name because BLACK's grammar
        reserves `true`, `false` and operator letters, and a pack is free to name a signal
        anything the loader accepts.
        """
        if key not in self.atoms:
            self.atoms[key] = f"p{len(self.atoms)}"
        return self.atoms[key]


def to_ltlf(spec: str, abstraction: Abstraction) -> str:
    """Render a requirement `spec` in BLACK's LTLf syntax, abstracting every atom.

    Raises `UnsupportedConstructError` — never a partial or approximate rendering — for a past
    operator, for the counterfactual atom, and for anything else the mapping has no spelling for.
    """
    return _render(parse_property(spec).body, abstraction)


def _render(node: ast.AST, abstraction: Abstraction) -> str:
    if isinstance(node, ast.BoolOp):
        joiner = " & " if isinstance(node.op, ast.And) else " | "
        return "(" + joiner.join(_render(value, abstraction) for value in node.values) + ")"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"!({_render(node.operand, abstraction)})"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name in _PAST_OPERATORS:
            raise UnsupportedConstructError(
                f"{name!r} is a past operator and LTLf is the future fragment, so the installed "
                "decision procedure has no spelling for it; rendering it into a future operator "
                "would be implementing its semantics"
            )
        if name in _UNARY_RENDERING:
            return f"{_UNARY_RENDERING[name]}({_render(node.args[0], abstraction)})"
        if name in _BINARY_RENDERING:
            left = _render(node.args[0], abstraction)
            right = _render(node.args[1], abstraction)
            return f"({left} {_BINARY_RENDERING[name]} {right})"
        if name in IMPLICATION_CALLS:
            left = _render(node.args[0], abstraction)
            right = _render(node.args[1], abstraction)
            return f"({left} -> {right})"
        if name == EQUIVALENCE_CALL:
            left = _render(node.args[0], abstraction)
            right = _render(node.args[1], abstraction)
            return f"(({left} -> {right}) & ({right} -> {left}))"
        if name == BOUNDED_RESPONSE_CALL:
            raise UnsupportedConstructError(
                f"{BOUNDED_RESPONSE_CALL} bounds an elapsed duration on the event clock, and "
                "LTLf keeps every position while abstracting every magnitude, so the installed "
                "decision procedure has no spelling for it; rendering it into a count of "
                "positions would be implementing a metric semantics it does not have"
            )
        if name == COUNTERFACTUAL_CALL:
            raise UnsupportedConstructError(
                f"{COUNTERFACTUAL_CALL} is a property of a pair of executions and not of any "
                "trace, so no trace logic decides it"
            )
        if name in (PRESENCE_CALL, CONTAINS_CALL):
            return _atom(node, abstraction)
    if isinstance(node, (ast.Compare, ast.Name)):
        return _atom(node, abstraction)
    raise UnsupportedConstructError(
        f"{ast.unparse(node)!r} has no LTLf spelling in this mapping"
    )


def _atom(node: ast.AST, abstraction: Abstraction) -> str:
    letter = abstraction.atom(ast.unparse(node))
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == CONTAINS_CALL:
        signal = ast.unparse(node.args[0])
        axiom = f"G({letter} -> {abstraction.atom(f'{PRESENCE_CALL}({signal})')})"
        if axiom not in abstraction.axioms:
            abstraction.axioms.append(axiom)
    return letter


def _apply_X(expr: str, count: int) -> str:
    for _ in range(count):
        expr = f"X ({expr})"
    return expr


def accepts(formula: str, valuations: Sequence[dict[str, bool]]) -> bool:
    """Whether one concrete trace of propositional valuations satisfies formula."""
    n = len(valuations)
    if n == 0:
        return False
    ap = sorted(
        set(_ATOM_PATTERN.findall(formula))
        | {k for v in valuations for k in v.keys()}
    )
    if not ap:
        lambdas = ["True"] * n
    else:
        lambdas = [
            " & ".join(a if v.get(a, False) else f"!{a}" for a in ap)
            for v in valuations
        ]

    pin_parts = [
        _apply_X(f"({lam})", i) for i, lam in enumerate(lambdas)
    ]
    pin_parts.append(_apply_X("!(X True)", n - 1))
    pin_formula = " & ".join(f"({p})" for p in pin_parts)
    combined = f"({formula}) & ({pin_formula})"
    return _run_black(combined)


_ATOM_PATTERN = re.compile(r"\bp\d+\b")


def atom_count(formula: str) -> int:
    """How many distinct propositional atoms one rendered question carries."""
    return len(set(_ATOM_PATTERN.findall(formula)))


def _conjoin(formulas: Sequence[str], abstraction: Abstraction) -> str:
    asked = "".join(formulas)
    reads = set(_ATOM_PATTERN.findall(asked))
    parts = [f"({formula})" for formula in formulas]
    parts += [
        f"({axiom})"
        for axiom in abstraction.axioms
        if reads.intersection(_ATOM_PATTERN.findall(axiom))
    ]
    return " & ".join(parts) if parts else "True"


def _decide(formula: str) -> bool:
    if atom_count(formula) > ATOM_BUDGET:
        raise UnsupportedConstructError(
            f"the question carries {atom_count(formula)} propositional atoms, over the "
            f"{ATOM_BUDGET} the installed decision procedure checks in bounded time"
        )
    return _run_black(formula)


def satisfiable(formulas: Sequence[str], abstraction: Abstraction) -> bool:
    """Whether some non-empty finite trace satisfies every formula at once.

    Read `LTLF_ABSTRACTION_LIMIT` before reporting a negative: under the propositional abstraction
    a `False` here is not a claim about the pack, which is why the analysis only ever reports the
    affirmative.
    """
    return _decide(_conjoin(formulas, abstraction))


def entails(left: str, right: str, abstraction: Abstraction) -> bool:
    """Whether every non-empty finite trace satisfying `left` satisfies `right`."""
    return not _decide(_conjoin([left, f"!({right})"], abstraction))
