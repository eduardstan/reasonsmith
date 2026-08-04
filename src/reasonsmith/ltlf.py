"""A finite-trace decision procedure for the temporal fragment, behind an optional extra.

What this module is for:
  `analysis.py` decides a pack's questions — joint satisfiability, entailment, equivalence — with
  Z3, over one decision record. A `temporal` spec is not a property of one record, so the analysis
  reduced the one shape that is — `always(f)`, through
  `engines/temporal.state_property_under_always` — and reported every other shape skipped.
  `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` is written with `until`; nothing in
  `validate-pack --analyse` could say anything about it at all.

  This module answers those questions for the whole fragment by handing the formula to a published
  LTLf decision procedure. It is **a syntax mapping and an emptiness question, and nothing else** —
  the same discipline `engines/observed.to_stl` observes for rtamt. `flloat` (Favorito & Fuggitti,
  Apache-2.0) compiles an LTLf formula to a DFA over its propositional atoms; a formula is
  satisfiable exactly when that automaton's language is non-empty, entailment is
  `left & !right` unsatisfiable, and equivalence is entailment both ways. No temporal semantics,
  automaton construction, tableau or monitor is implemented here, and none may be.

  What was priced against `flloat`, so the choice is reconstructible rather than asserted. **BLACK**
  (Geatti, Gigante, Montanari; MIT) decides LTL, LTL+Past and LTLf and would have covered the past
  operators this does not, but publishes no PyPI distribution under any name searched, so
  integrating it means shipping a subprocess boundary onto a binary a user installs by hand.
  **LTLf2DFA** and **Lydia** compile LTLf to a minimal DFA through **MONA**, which is a native
  package (`apt install mona`) and not a wheel: `pip install reasonsmith[ltlf]` would succeed and
  the tool would still not run, which is worse than no extra. **Spot** is mature and has Python
  bindings, and is likewise not on PyPI. **nuXmv** is free for non-commercial use only and must not
  go on a dependency path at all. `flloat` is the one candidate that is pure Python on PyPI, and it
  is chosen for exactly that: the extra installs with no native toolchain. It is paid for in the
  ceiling `ATOM_BUDGET` records — measured, not assumed — and in having no past operators.

  It is deliberately **not** under `engines/`. An engine returns a `RequirementResult` about a
  system and occupies a rung of the strength lattice. This decides formulas, is never given a
  system, and adds no rung: `release discipline` counts the modules under `engines/` and the count
  in `ROADMAP.md` and `README.md` is still right.

What a reader must not break:
  - **rtamt keeps every magnitude; this keeps every qualitative question.** The two backends are
    not interchangeable, and the split is not a preference. rtamt monitors a real-valued signal and
    scores robustness; LTLf is propositional, so every comparison of magnitudes here becomes one
    opaque Boolean atom and `x <= 30` bears no relation to `x <= 90`. That abstraction is **sound
    for the entailments it reports and incomplete for the ones it does not**, exactly as
    `analysis._PackScope` already says of the record atoms — and it is *unsound in the other
    direction for satisfiability*, which is why `satisfiable()` is only ever used to report a pack
    consistent, never to report one contradictory. `LTLF_ABSTRACTION_LIMIT` states it on every
    answer that rests on it.
  - **The extra is optional and its absence is reported, never worked around.** `pip install
    reasonsmith` stays a two-command demo: `flloat` arrives with `pip install reasonsmith[ltlf]`.
    With it absent, `available()` is False and the analysis says so in a note; nothing degrades to
    a weaker answer presented as the same one.
    (`test_the_analysis_says_so_when_the_extra_is_absent`)
  - **Only the future fragment.** `flloat` parses LTLf, which has no past operators, so a spec
    using `once`, `historically`, `prev`, `since`, `rise` or `fall` is refused **by name** into the
    analysis' `skipped` list. Rendering one into a future operator would be implementing its
    semantics. (`test_a_past_operator_is_skipped_by_name_rather_than_rendered`)
  - **Every question is asked over a non-empty trace.** LTLf as `flloat` implements it admits the
    empty trace, on which `always(f)` holds whatever `f` says — so every `always` duty would be
    reported satisfiable by a trace no monitor ever reads. `NON_EMPTY` is the LTLf formula for
    "there is a position", conjoined into every question, so the models this reports are the traces
    the monitors run on. It is a formula and not a construction.
    (`test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable`)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Sequence

from reasonsmith.rulelang import (
    CONTAINS_CALL,
    COUNTERFACTUAL_CALL,
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
    "NON_EMPTY",
    "UNAVAILABLE_NOTE",
    "atom_count",
    "available",
    "entails",
    "satisfiable",
    "to_ltlf",
]

#: The name of the optional dependency group that installs the decision procedure.
LTLF_EXTRA = "ltlf"

#: What the analysis prints when the extra is not installed. It names the install command rather
#: than the package, because the package is an implementation detail of the extra.
UNAVAILABLE_NOTE = (
    "temporal decision procedure: not installed, so no temporal duty was decided as a formula. "
    "`pip install reasonsmith[ltlf]` adds it. Nothing was answered from a weaker substitute."
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

#: The LTLf formula for "this trace has a position". See the module docstring: `flloat` admits the
#: empty trace, on which every `always(f)` holds, and the traces this package's monitors read are
#: non-empty. `F(true)` is a formula of the logic and not a construction over its automata.
NON_EMPTY = "F(true)"

#: The most propositional atoms **one question** may carry before it is refused by name. This is
#: the installed procedure's ceiling and not a policy: `flloat` enumerates the full powerset of the
#: atoms as the automaton's alphabet and calls `sympy.satisfiable` once per symbol per state, so a
#: pack-shaped question measured on this tree costs about 2 s at four atoms, 9 s at five and more
#: than 90 s at six. There is no wall clock anywhere in this package — the same limit
#: `docs/authoring-engines.md` states for a plug-in — so the count is checked before the automaton
#: is built rather than after the run has hung. Every shipped temporal duty is three or four atoms;
#: every *pair* of them is seven, which is why the pack's entailment questions are reported refused
#: rather than answered. (`test_a_question_over_the_atom_budget_is_refused_by_name`)
ATOM_BUDGET = 5

#: The rulelang operators `flloat` has, and their LTLf spelling.
_UNARY_RENDERING = {"always": "G", "eventually": "F", "next": "X"}
_BINARY_RENDERING = {"until": "U"}

#: The operators of the language `flloat` does not have. LTLf is the future fragment; each of these
#: needs the past, and rendering one into a future operator would be implementing its semantics.
_PAST_OPERATORS = TEMPORAL_OPERATORS - set(_UNARY_RENDERING) - set(_BINARY_RENDERING)


def available() -> bool:
    """Whether the optional decision procedure is installed."""
    try:
        import flloat.parser.ltlf  # noqa: F401
    except Exception:  # pragma: no cover - exercised only where the extra is absent
        return False
    return True


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

        The letter is synthetic rather than the signal's own name because `flloat`'s grammar
        reserves `true`, `false` and the operator letters, and a pack is free to name a signal
        anything the loader accepts.
        """
        if key not in self.atoms:
            self.atoms[key] = f"p{len(self.atoms)}"
        return self.atoms[key]


def to_ltlf(spec: str, abstraction: Abstraction) -> str:
    """Render a requirement `spec` in `flloat`'s LTLf syntax, abstracting every atom.

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
    # There is no case for a bare Boolean constant: `rulelang.validate_property` refuses one before
    # a spec reaches here, so a case would be a spelling for something no `spec` can say.
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
        if name in ("implies", "Implies"):
            left = _render(node.args[0], abstraction)
            right = _render(node.args[1], abstraction)
            return f"({left} -> {right})"
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


def _language_non_empty(formula: str) -> bool:
    """Whether some non-empty finite trace satisfies `formula`.

    The whole of the decision procedure this module uses: `flloat` compiles the formula to a DFA
    whose states are exactly the ones its construction reaches from the initial state, so the
    language is non-empty exactly when one of them accepts.
    """
    from flloat.parser.ltlf import LTLfParser

    automaton = LTLfParser()(f"({formula}) & {NON_EMPTY}").to_automaton()
    return bool(automaton.accepting_states)


def accepts(formula: str, valuations: Sequence[dict[str, bool]]) -> bool:
    """Whether the formula's automaton accepts one trace of propositional valuations.

    The one entry point the differential test needs, and the reason it is here rather than in the
    test: every call into the installed procedure goes through this module, so there is one place
    where what LTLf means to this package is decided.
    """
    from flloat.parser.ltlf import LTLfParser

    return bool(LTLfParser()(formula).to_automaton().accepts([dict(v) for v in valuations]))


_ATOM_PATTERN = re.compile(r"\bp\d+\b")


def atom_count(formula: str) -> int:
    """How many distinct propositional atoms one rendered question carries."""
    return len(set(_ATOM_PATTERN.findall(formula)))


def _conjoin(formulas: Sequence[str], abstraction: Abstraction) -> str:
    """The question put to the procedure: the formulas, plus every axiom that speaks about them.

    Only the axioms whose atoms the question already reads. `Abstraction` is shared across a whole
    pack, so an axiom belonging to some other requirement's `contains()` would otherwise add its two
    atoms to every question — inflating the count `ATOM_BUDGET` is checked against and refusing a
    question for a reason that is not the question's.
    """
    asked = "".join(formulas)
    reads = set(_ATOM_PATTERN.findall(asked))
    parts = [f"({formula})" for formula in formulas]
    parts += [
        f"({axiom})"
        for axiom in abstraction.axioms
        if reads.intersection(_ATOM_PATTERN.findall(axiom))
    ]
    return " & ".join(parts) if parts else "true"


def _decide(formula: str) -> bool:
    if atom_count(formula) > ATOM_BUDGET:
        raise UnsupportedConstructError(
            f"the question carries {atom_count(formula)} propositional atoms, over the "
            f"{ATOM_BUDGET} the installed decision procedure builds an automaton for in "
            "bounded time"
        )
    return _language_non_empty(formula)


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
