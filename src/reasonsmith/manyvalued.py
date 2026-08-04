"""Many-valued readings of the property language, for predicates the law states without a boundary.

What this module is for:
  Twenty-one of the shipped requirements are presence checks, and the fourth column of
  `docs/refinement.md` says the same thing over and over: *meaningful*, *sufficiently detailed*,
  *adequate*, *appropriate* were not modelled. Presence is not a bad proxy for those predicates —
  it is a refusal to model them at all. Two constructs answer different halves of that, and they
  compose rather than compete; this module is the second of them.

  The first is `undetermined(signal, "predicate", "authority")`, which needs no machinery beyond a
  refusal and lives in `rulelang` and `report.not_evaluated_for_open_texture`: an open-textured
  predicate that **no engine settles**, resolved only by the named authority outside this tool.

  The second is here. Vagueness is not missing information. *Sufficiently detailed* has no sharp
  boundary **even when every fact is known**, which is the case two-valued logic mishandles and
  many-valued logic exists for. `degree(signal, "predicate")` is an atom whose value is a truth
  degree in [0, 1], the connectives around it are read over a **declared** algebra, and the degree
  itself comes from a **declared source** — never from the system being audited.

What a reader must not break:
  - **A truth degree is never a verdict, and this module never returns one.** `degree_of` returns a
    number and `report` carries it as a measurement on a result whose verdict is `inconclusive` at
    `strength=None`. Turning a degree into `satisfied` needs a threshold, and a threshold in a
    shipped pack is a number invented for it and presented as the regulation's — the objection
    `docs/authoring-packs.md` already makes about an invented bound, arriving as a cut-off on a
    lattice rather than as a constant in a `spec`. Which statutory predicate becomes the first
    graded duty, and what discharges it, is a legal reading and not this module's to make.
    Why this matters: a graded semantics makes every duty *answerable*, and that would destroy the
    one property this tool has — it refuses rather than guessing. `unattainable` and `not evaluated`
    stay reachable, and a low degree never replaces either.
  - **The algebra is declared, never assumed.** Which residuated lattice the connectives are read
    over changes what a conjunction of two `0.5`s means: Łukasiewicz says `0`, Gödel says `0.5`,
    product says `0.25`. There is no default here and `ALGEBRAS` is not consulted without a name;
    `spec.load_pack` refuses a pack shipping a graded duty without `[grading] algebra`.
    Why this matters: a global default nobody reads is a semantics this tool picked on a pack
    author's behalf, and a reader of the verdict could not tell which one answered.
  - **The degree has a declared source, and it travels with the verdict.** `Grading` carries the
    authority that fixed the scale, what the scale is, and how the degrees were obtained, and
    `RequirementResult.__post_init__` refuses a degree that does not carry all three — the shape
    `PROBE_BUDGET_FIELDS` already forces on a bounded search.
    Why this matters: a degree a system asserts about itself is the `reason_is_specific`
    self-declaration wearing a lattice's clothes. `Grading` is an argument to `check_conformance`
    and is deliberately not read off the system under test or off its trace.
  - **An empty trace yields no degree.** The degree of a duty over a trace is the infimum of its
    degree at each decision, and the infimum of nothing is the top of the lattice. Returning `1.0`
    there would be `combine_verdicts`' vacuous `satisfied` re-derived on a scale.
    Why this matters: having observed zero decisions is not evidence graded any higher than it is
    evidence Boolean.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from reasonsmith.rulelang import (
    DEGREE_CALL,
    EQUIVALENCE_CALL,
    IMPLICATION_CALLS,
    UnsupportedConstructError,
    degree_arguments,
    eval_expression,
    has_degree_atom,
)

#: The fields a `Grading` must name, and the reason it must name them. Read by
#: `report.RequirementResult.__post_init__`, which refuses a result carrying a degree without them,
#: exactly as it refuses a probed result carrying no `PROBE_BUDGET_FIELDS`. A number on a page with
#: no account of who fixed the scale it lies on is not evidence — it is a figure.
DEGREE_SOURCE_FIELDS = ("authority", "scale", "method")


@dataclass(frozen=True)
class Algebra:
    """One reading of the connectives over [0, 1]: a t-norm and the operations it determines.

    The three shipped members are the three fundamental continuous t-norms — Łukasiewicz, Gödel and
    product — from which every continuous t-norm is built as an ordinal sum (Hájek, *Metamathematics
    of Fuzzy Logic*, 1998). Each is stored with its residuum rather than deriving one, because the
    residuum is what an implication means and a reader checking this file against a textbook should
    find it written down.

    `disjunction` is the dual t-conorm and `negation` is the one the residuum induces
    (`residuum(x, 0)`), so a member is internally consistent by construction rather than by three
    independent choices. Adding a member means adding a row here; nothing else in this package needs
    to know about it, which is the generality this table exists for.
    """

    name: str
    description: str
    conjunction: Callable[[float, float], float]
    disjunction: Callable[[float, float], float]
    negation: Callable[[float], float]
    residuum: Callable[[float, float], float]

    def biresiduum(self, x: float, y: float) -> float:
        """The degree to which two degrees are equivalent: `(x → y) ⊗ (y → x)`.

        Derived and not stored, for the reason `negation` is derived from the residuum: a member of
        this table stays internally consistent by construction rather than by a fourth independent
        choice. Under Łukasiewicz it works out to `1 − |x − y|`, which is the standard reading,
        pinned as such in `tests/test_equivalence_connective.py`.

        This is what `<=>` means in the graded fragment, and it is emphatically not `x == y`. A
        crisp comparison of two degrees is a threshold, which `docs/semantics.md` §9 refuses; an
        author who writes `==` still receives that refusal, and an author who writes `<=>` now
        receives this.
        """
        return self.conjunction(self.residuum(x, y), self.residuum(y, x))


def _lukasiewicz_residuum(x: float, y: float) -> float:
    return min(1.0, 1.0 - x + y)


def _godel_residuum(x: float, y: float) -> float:
    return 1.0 if x <= y else y


def _product_residuum(x: float, y: float) -> float:
    return 1.0 if x <= y else y / x


#: The algebras a pack may declare, by the name it declares. Not a default and not a fallback:
#: `algebra_named` refuses a name outside this table rather than picking one.
ALGEBRAS: dict[str, Algebra] = {
    "lukasiewicz": Algebra(
        name="lukasiewicz",
        description=(
            "Łukasiewicz: conjunction max(0, x + y - 1), implication min(1, 1 - x + y), involutive "
            "negation 1 - x. Two half-true conjuncts are wholly false, so evidence accumulates "
            "against a duty rather than plateauing"
        ),
        conjunction=lambda x, y: max(0.0, x + y - 1.0),
        disjunction=lambda x, y: min(1.0, x + y),
        negation=lambda x: 1.0 - x,
        residuum=_lukasiewicz_residuum,
    ),
    "godel": Algebra(
        name="godel",
        description=(
            "Gödel: conjunction min(x, y), implication 1 when x <= y and y otherwise. The degree "
            "of a conjunction is its weakest conjunct and nothing else, so a formula's degree is "
            "always one of its atoms' degrees"
        ),
        conjunction=min,
        disjunction=max,
        negation=lambda x: 1.0 if x == 0.0 else 0.0,
        residuum=_godel_residuum,
    ),
    "product": Algebra(
        name="product",
        description=(
            "Product: conjunction x * y, implication 1 when x <= y and y / x otherwise. Conjuncts "
            "compound, so a long conjunction of nearly-true atoms is markedly less true than any "
            "of them"
        ),
        conjunction=lambda x, y: x * y,
        disjunction=lambda x, y: x + y - x * y,
        negation=lambda x: 1.0 if x == 0.0 else 0.0,
        residuum=_product_residuum,
    ),
}


def algebra_named(name: str) -> Algebra:
    """The algebra a pack declared, refusing a name this package has no reading for.

    Refused where it is written rather than defaulted, for the reason `normalize_scope` refuses a
    class outside its vocabulary: a misspelling that silently became Gödel would answer every graded
    duty in the pack under a semantics nobody chose, and no rendering would say so.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "a graded duty is read over a declared algebra, and none was named. Declare "
            "`[grading] algebra` in the pack; accepted: "
            f"{', '.join(sorted(ALGEBRAS))}"
        )
    key = name.strip().lower()
    if key not in ALGEBRAS:
        raise ValueError(
            f"{name!r} is not an algebra this package reads a graded duty over. Accepted: "
            f"{', '.join(sorted(ALGEBRAS))}. Which residuated lattice the connectives are read "
            "over changes what a conjunction of two 0.5s means, so it is a declared parameter of "
            "the pack and never a default — see docs/semantics.md §9."
        )
    return ALGEBRAS[key]


def atom_key(signal: str, predicate: str) -> str:
    """The one spelling of a graded atom, used as a `Grading` key and in every rendering."""
    return f"{predicate}({signal})"


class UngradedAtomError(UnsupportedConstructError):
    """Raised when a graded formula reads an atom the supplied grading does not score.

    A subclass, so every caller that already reports an inexpressible construct as *not evaluated*
    reports this the same way. It is deliberately not answered with `0.0`: a predicate nobody
    assessed is not a predicate assessed as wholly false, and that substitution is the whole failure
    mode this module is designed against.
    """


@dataclass(frozen=True)
class Grading:
    """Truth degrees for open-textured predicates, and the account of who fixed the scale.

    This is **third-party evidence**, supplied to `check_conformance` beside the pack, in the way a
    decision trace is first-party evidence read off the system. It is deliberately not an attribute
    of a `SystemUnderTest` and is never read off a decision record: a degree a system asserts about
    itself is a self-declaration, and this package refuses one whether it arrives as a
    `reason_is_specific` flag, as a group rate, or as a number on a lattice.

    `degrees` is keyed by `atom_key(signal, predicate)` — one degree per open-textured predicate per
    signal, for the whole run. There is deliberately no per-record grading: a per-decision degree is
    a per-decision assessment, and inventing one by repeating a single figure down the log is the
    quiet symptom `docs/authoring-packs.md` describes for a group rate.
    """

    authority: str
    scale: str
    method: str
    degrees: Mapping[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "degrees", dict(self.degrees or {}))
        for name in DEGREE_SOURCE_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"a grading must state its {name!r}: who fixed the scale, what the scale is, "
                    "and how the degrees were obtained. A degree with no source is a figure, not "
                    "evidence — see docs/semantics.md §9"
                )
        for key, value in self.degrees.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"a grading is keyed by predicate(signal); got {key!r}")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"the degree of {key} must be a number in [0, 1], got "
                    f"{type(value).__name__}: {value!r}"
                )
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"the degree of {key} must lie in [0, 1], got {value!r}")

    def source(self) -> dict[str, str]:
        """The three fields that travel with every verdict this grading contributed to."""
        return {name: getattr(self, name) for name in DEGREE_SOURCE_FIELDS}

    def degree(self, signal: str, predicate: str) -> float:
        """The degree assessed for one open-textured predicate of one signal.

        Raises `UngradedAtomError` when the grading scores no such atom, rather than returning a
        degree of its own. See the class docstring.
        """
        key = atom_key(signal, predicate)
        if key not in self.degrees:
            raise UngradedAtomError(
                f"the grading supplied by {self.authority!r} scores no degree for {key}. A "
                "predicate nobody assessed is not a predicate assessed as false, so this duty is "
                "reported not evaluated rather than graded"
            )
        return float(self.degrees[key])


def degree_of(
    node: ast.AST,
    env: dict[str, Any],
    algebra: Algebra,
    grading: Grading,
) -> float:
    """The truth degree of a graded property at one decision record.

    Every subtree containing no `degree()` atom is answered by the two-valued interpreter that
    already exists and mapped to `1.0`/`0.0`. That is not an optimisation: it is what keeps the
    crisp parts of a graded formula meaning exactly what they mean everywhere else in this package,
    including `present()`'s treatment of a blank string and `contains()`' ASCII fold. Only the
    connectives *above* a graded atom are read over the algebra, because they are the only ones
    whose reading the algebra changes.

    A graded atom under arithmetic or a comparison is refused rather than coerced: `degree(x, "p") +
    1` asks for a number on a scale this package has not defined, and a comparison of two degrees is
    a threshold — the one construct §9 refuses to let a pack state. `<=>` is not that comparison: it
    parses to `Iff(...)` and is read over `Algebra.biresiduum`, which is why the refusal now reaches
    only the author who actually wrote `==`.
    """
    if isinstance(node, ast.Expression):
        return degree_of(node.body, env, algebra, grading)

    if not has_degree_atom(node):
        return 1.0 if eval_expression(node, env) else 0.0

    if isinstance(node, ast.BoolOp):
        parts = [degree_of(value, env, algebra, grading) for value in node.values]
        combine = algebra.conjunction if isinstance(node.op, ast.And) else algebra.disjunction
        result = parts[0]
        for part in parts[1:]:
            result = combine(result, part)
        return result

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return algebra.negation(degree_of(node.operand, env, algebra, grading))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name == DEGREE_CALL:
            signal, predicate = degree_arguments(node)
            return grading.degree(signal, predicate)
        if name in IMPLICATION_CALLS and len(node.args) == 2:
            return algebra.residuum(
                degree_of(node.args[0], env, algebra, grading),
                degree_of(node.args[1], env, algebra, grading),
            )
        if name == EQUIVALENCE_CALL and len(node.args) == 2:
            return algebra.biresiduum(
                degree_of(node.args[0], env, algebra, grading),
                degree_of(node.args[1], env, algebra, grading),
            )

    raise UnsupportedConstructError(
        f"{ast.unparse(node)!r} puts a graded atom somewhere this reading has no meaning for it. "
        f"{DEGREE_CALL}() stands under the boolean connectives, under an implication and under an "
        "equivalence, and nowhere else: under arithmetic it asks for a number on an undefined "
        "scale, and under a comparison it states a threshold, which is the pack author's number "
        "presented as the regulation's. Note that `<=>` is an equivalence and reaches the "
        "algebra's biresiduum, while `==` is a comparison and does not"
    )


def degree_over_trace(
    node: ast.AST,
    records: list[dict[str, Any]],
    algebra: Algebra,
    grading: Grading,
) -> float:
    """The degree of a graded property over a whole trace: the infimum of its per-record degrees.

    The infimum is the lattice meet, which is `min` in every algebra here, and it is the graded
    reading of "holds at every decision" — the same universal quantification the record and observed
    engines take over a trace. An empty trace is refused by the caller and never reaches here: the
    infimum of nothing is the top of the lattice, and answering `1.0` for a run that observed
    nothing is the vacuous `satisfied` this package refuses, rewritten as a number.
    """
    if not records:
        raise ValueError(
            "the degree of a duty over an empty trace is the infimum of nothing, which is the top "
            "of the lattice. Nothing observed is not evidence graded 1.0"
        )
    return min(degree_of(node, record, algebra, grading) for record in records)
