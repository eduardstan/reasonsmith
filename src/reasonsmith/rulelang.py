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
import io
import math
import tokenize
from typing import Any, Iterable, Mapping

from reasonsmith.event_time import EventTimeError, parse_duration

_EQUIVALENCE_TOKENS = ("<=>", "<->")
_IMPLICATION_TOKENS = ("=>", "->", " implies ")

#: The atom asking whether a decision record carries a value for a signal at all.
PRESENCE_CALL = "present"

#: The atom asking whether a signal's recorded text carries a given phrase.
#:
#: `contains(signal, "phrase")` is the second — and, at the time of writing, only other — atom whose
#: first argument is a signal *name* rather than an expression, for the same reason `present()` is:
#: every engine has to bind it to one field of one decision record, and there is no such field
#: behind a computed value. Its second argument is a string literal and never a name, so the phrase
#: a duty forbids is fixed by the pack rather than supplied by the system being audited.
#:
#: It exists because fifteen of the eighteen shipped duties were conjunctions of `present()`, which
#: made the strongest claim available about an explanation duty "the field is non-blank" — a reason
#: string of `"n/a"` satisfies that and violates 12 CFR 1002.9(b)(2). The clause supplies its own
#: negative constraint, naming the statements that are insufficient, and this atom is the narrowest
#: thing that expresses one. It deliberately does not model "specific": it answers whether a phrase
#: occurs, and nothing about what the text means.
CONTAINS_CALL = "contains"

#: The atom asking whether one named variable can move a named outcome, holding everything else
#: fixed — `counterfactually_invariant(outcome_signal, protected_signal)`.
#:
#: It is the third atom whose arguments are signal *names* rather than expressions, for the reason
#: the other two give: every engine has to bind them to named variables, and there is no variable
#: behind a computed value. It is the first atom in this language that is **not a property of one
#: decision record**. `present()` and `contains()` ask something about a decision; this asks whether
#: two decisions the system would make — differing in one input and in nothing else — agree. That
#: is a property of a *pair* of executions, which is why it has a fragment of its own
#: (`classify_fragment`) rather than being admitted into `logical`: a trace holds what happened and
#: a counterfactual is about what would have happened, so no engine reading a trace may be handed
#: this. `report._engine_ladder` gives the fragment no trace rung, and `eval_expression` refuses the
#: atom outright so that nothing can evaluate one against a decision record by accident.
#:
#: The admissible values of the protected variable come from the system's declared `constraints`,
#: never from the trace. See `engines/counterfactual.py` and `docs/semantics.md` §3.
COUNTERFACTUAL_CALL = "counterfactually_invariant"

#: Narrow population aggregate atom; it is never evaluated per record.
STATISTICAL_CALL = "selection_rate_ratio"

#: The atom for a predicate the law states in words with no sharp boundary, which **no engine here
#: settles** — `undetermined(signal, "predicate", "authority")`.
#:
#: It is the fourth atom whose first argument is a signal *name* rather than an expression, and it
#: exists because the fourth column of `docs/refinement.md` says the same thing over and over:
#: *meaningful*, *sufficiently detailed*, *adequate*, *appropriate* were not modelled, and a
#: presence check stood in for each. Roughly three quarters of that already happened incidentally,
#: through whichever not-evaluated path a duty happened to fall down. This makes it a construct: the
#: pack states, in the property itself, which predicate is open-textured and **which authority would
#: settle it** — a supervisory authority, a court, a published guideline — and the result names
#: both. It is never silently true and never silently false.
#:
#: The signal argument is load-bearing and is not decoration. It is what puts the name into
#: `requires`, so a system that cannot emit the thing the predicate is about is reported
#: `unattainable` by the capability gate before this atom is ever reached. An undetermined duty is
#: therefore not a way for every system to get the same answer.
UNDETERMINED_CALL = "undetermined"

#: The atom whose value is a **truth degree** rather than a truth value —
#: `degree(signal, "predicate")`.
#:
#: The other half of the same problem, and a different half. `undetermined()` is the conservative
#: reading: the predicate is not settled here, so nothing is claimed. But vagueness is not missing
#: information — *sufficiently detailed* has no sharp boundary even when every fact is known, which
#: is what many-valued logic exists for. This atom's degree comes from a declared source outside the
#: system (`manyvalued.Grading`), and the connectives above it are read over an algebra the pack
#: declares (`manyvalued.ALGEBRAS`). Neither is optional and neither has a default.
#:
#: Nothing here turns a degree into a verdict. See `manyvalued` and `docs/semantics.md` §9.
DEGREE_CALL = "degree"

#: The sole metric-temporal construct. Its operands are named event predicates and its bound is
#: a fixed duration string (for example ``"24h"`` or ``"1mo"``), never a logged latency.
BOUNDED_RESPONSE_CALL = "within_after"

#: Every atom whose first argument is a signal *name* the engine binds to a field or a variable,
#: rather than an expression to be computed. Named once because two walkers ask the same question of
#: it — `_bare_boolean_parts`, deciding which names are read as flags, and `_value_signal_names`,
#: deciding which are read as magnitudes — and an atom added to one tuple and forgotten in the other
#: would give its signal a role the property never gave it.
_SIGNAL_ARGUMENT_CALLS = (
    PRESENCE_CALL,
    CONTAINS_CALL,
    COUNTERFACTUAL_CALL,
    STATISTICAL_CALL,
    UNDETERMINED_CALL,
    DEGREE_CALL,
)

#: The characters `contains()` folds, and the only ones. See `fold_ascii_case`.
_ASCII_UPPER = frozenset(chr(code) for code in range(ord("A"), ord("Z") + 1))

#: The numeric comparison that gives a signal the flag role rather than the magnitude role.
FLAG_THRESHOLD = 0.5

#: The one temporal operator whose vacuity question is the state property's own. `always(f)` holds
#: at every position, so a trigger inside `f` that fires nowhere leaves the whole quantification
#: vacuous in exactly the way `f` is vacuous at each position. Named here rather than in
#: `engines/temporal.py` because `implication_antecedent` is a fact about the language and the
#: engine's `ALWAYS` is this constant.
ALWAYS_OPERATOR = "always"

#: The one-operand temporal operators of the language, in the prefix call form a Python parser
#: accepts.
UNARY_TEMPORAL_OPERATORS = frozenset(
    {"always", "eventually", "once", "historically", "next", "prev", "rise", "fall"}
)

#: The two-operand temporal operators, written in the same prefix call form `implies(a, b)` uses.
#: rtamt parses both as infix operators already; the language exposes them as prefix calls because
#: it parses through Python's `ast`, and `engines/observed.to_stl` renders them back to the infix
#: form the monitor reads. Nothing here implements their semantics — the monitor this package
#: already depends on does.
BINARY_TEMPORAL_OPERATORS = frozenset({"until", "since"})

#: The positional temporal operators. ``within_after`` is kept outside this legacy vocabulary
#: because it is metric event-time semantics rather than an ordinal operator;
#: ``has_temporal_operator`` still recognises it as temporal for classification and proof refusal.
TEMPORAL_OPERATORS = UNARY_TEMPORAL_OPERATORS | BINARY_TEMPORAL_OPERATORS

#: The call the arrow rewriter emits for `<=>` and `<->`, on the footing `Implies(...)` already has.
#:
#: It is a **distinct node** and deliberately not `==`. Over the Booleans equivalence *is* equality
#: of truth values, and `eval_expression` reads it that way, so nothing two-valued moved. Over the
#: residuated lattices of `manyvalued` it is not: `==` is a crisp comparison of two degrees, which
#: is a threshold, and `docs/semantics.md` §9 refuses one. Collapsing the connective textually
#: before the parse destroyed the distinction, so the refusal named a construct nobody wrote and
#: equivalence was unavailable in the graded fragment for no design reason — the same accident that
#: spared `implies`, which survived only by being spelled as a call rather than as an arrow.
#: `manyvalued.degree_of` reads this over the algebra's biresiduum.
EQUIVALENCE_CALL = "Iff"

#: The two spellings of implication, which the rewriter folds `=>`, `->` and ` implies ` into.
IMPLICATION_CALLS = frozenset({"implies", "Implies"})

#: Every call whose operands stand in Boolean position and whose value is a truth value. Named once
#: because three walkers ask the same question of it, and a connective added to one and forgotten in
#: another would give its operands a role the property never gave them.
BOOLEAN_CONNECTIVE_CALLS = IMPLICATION_CALLS | {EQUIVALENCE_CALL}

#: The non-temporal function calls, with their arity.
VALUE_CALLS = {"implies": 2, "Implies": 2, EQUIVALENCE_CALL: 2, "abs": 1, "min": 2, "max": 2}

#: The fragments of this language, narrowest first. `record` is a conjunction of presence atoms;
#: `logical` is any other state property of one decision record; `temporal` is anything reaching
#: across records with a temporal operator; `counterfactual` is the one relational fragment — a
#: property of a *pair* of executions rather than of any trace, and the only one nothing that reads
#: a decision log may discharge.
#:
#: `undetermined` and `graded` are the two open-texture fragments, and they are fragments rather
#: than a flag for the reason `counterfactual` is: the fragment is what decides which engines may
#: discharge a duty, and neither of these may be discharged by any of them. A spec with no
#: `degree()` atom can never be classified `graded`, which is the whole of the guarantee that a duty
#: with a sharp boundary does not acquire a truth degree because the machinery now exists.
FRAGMENTS = (
    "record",
    "logical",
    "temporal",
    "counterfactual",
    "statistical",
    "undetermined",
    "graded",
)

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

    UNKNOWN is the language's own name for *no value was determined*, so it is absent here
    too: otherwise `present(x)` would answer true where a bare `x` answers unknown, and the
    two atoms would disagree about the same object.
    """
    if value is None or is_unknown(value):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


class UnsupportedConstructError(Exception):
    """Raised when rule or specification text uses a construct this language does not model."""

    pass


class NotAStatementError(UnsupportedConstructError):
    """Raised when `contains()` meets a value that is present but is not a statement.

    A subclass, so every engine that already refuses an inexpressible construct keeps refusing
    this one unchanged. Separate, because the two meanings are not the same thing: an ordinary
    refusal says the property cannot be read here at all, while this one says one decision carried
    a kind that is no evidence about what a statement says. `engines/observed.py` reports the
    second NOT EVALUATED, and `engines/probed.py` must reach the same answer rather than fold it
    into the errored-input count and go on to report `satisfied` — a stronger rung that is easier
    to satisfy than a weaker one inverts the lattice. The type is what carries the distinction; a
    message string is not an interface, and nothing may tell the two apart by reading one.
    """

    pass


def fold_ascii_case(text: str) -> str:
    """Lowercase the twenty-six ASCII capitals and change nothing else.

    `contains()` is case-insensitive, and this is exactly how far. `str.lower()` would be the
    obvious choice and is the wrong one: it is not length-preserving over the whole of Unicode —
    `"İ".lower()` is two characters — and `str.casefold()` is worse. The Z3 encoding in
    `engines/proved.py` renders each literal character as a regular language matching *one*
    character, so any fold that is not one-to-one would make the solver and this interpreter
    disagree about the same string, and a silent divergence between two engines is worse than a
    narrower predicate. This fold is one-to-one by construction, which is why
    `contains_literal` refuses a non-ASCII literal rather than folding one it cannot promise
    agreement on.
    """
    return "".join(chr(ord(char) + 32) if char in _ASCII_UPPER else char for char in text)


def contains_literal(haystack: Any, needle: str) -> bool:
    """Whether a recorded value carries `needle`, folding ASCII case on both sides.

    Three cases, and the boundary between them is the point:

    - **A value the record does not carry**, in the `is_present` sense, contains nothing. A duty
      triggered by what a reason *says* has to be false where no reason was said, so that the
      implication guarding it can be the thing that decides.
    - **A string** is searched directly.
    - **A list or tuple of strings** is a statement given in parts, and contains the phrase when
      one of its parts does. A decision log recording reasons as `["C02 excessive obligations",
      "C04 delinquent obligations"]` is recording a statement of reasons, and refusing to read it
      would report *not evaluated* because of how the log is shaped rather than because of what it
      says. The parts are searched separately and never joined: joining them would let a phrase
      match across a boundary between two reasons that never appeared together.

    Anything else present raises `NotAStatementError`, which every engine reading this atom answers
    NOT EVALUATED. Answering `False` for a value nothing read would report a system
    satisfied on evidence that was never examined, which is the overclaim this package exists to
    refuse — and a number or a mapping is not a statement in any case.
    """
    if not is_present(haystack):
        return False
    folded_needle = fold_ascii_case(needle)
    if isinstance(haystack, str):
        return folded_needle in fold_ascii_case(haystack)
    if isinstance(haystack, (list, tuple)) and all(isinstance(part, str) for part in haystack):
        return any(folded_needle in fold_ascii_case(part) for part in haystack)
    raise NotAStatementError(
        f"{CONTAINS_CALL}() reads a recorded statement — text, or a list of text given in parts — "
        f"but this decision carries {type(haystack).__name__} {haystack!r}. A value that is not a "
        "statement is not evidence about what one says, so it is refused rather than read as "
        "carrying nothing"
    )


def contains_arguments(node: ast.Call) -> tuple[str, str]:
    """The signal name and the literal phrase of a `contains()` atom, refusing every other shape.

    One place decides what a well-formed `contains()` is, so the rtamt renderer, the Z3 encoder and
    the interpreter cannot drift on it.
    """
    if len(node.args) != 2:
        raise UnsupportedConstructError(
            f"{CONTAINS_CALL}() takes a signal name and a literal phrase: {ast.unparse(node)!r}"
        )
    signal, phrase = node.args
    if not isinstance(signal, ast.Name):
        raise UnsupportedConstructError(
            f"{CONTAINS_CALL}() reads one signal of the decision record, so its first argument is "
            f"a signal name and not an expression: {ast.unparse(node)!r}"
        )
    if not isinstance(phrase, ast.Constant) or not isinstance(phrase.value, str):
        raise UnsupportedConstructError(
            f"{CONTAINS_CALL}() looks for a phrase the pack fixes, so its second argument is a "
            f"string literal and never a name: {ast.unparse(node)!r}"
        )
    if not phrase.value:
        raise UnsupportedConstructError(
            f"{CONTAINS_CALL}({signal.id}, '') is true of every text and false of every absent "
            "one, which is `present()` written the long way. Write the phrase the duty forbids"
        )
    if not phrase.value.isascii():
        raise UnsupportedConstructError(
            f"{CONTAINS_CALL}() folds ASCII case only, so a non-ASCII phrase is refused rather "
            f"than compared under a fold the solver cannot reproduce: {phrase.value!r}. This is a "
            "limit of the predicate, recorded in docs/semantics.md, not of the clause"
        )
    return signal.id, phrase.value


def counterfactual_arguments(node: ast.Call) -> tuple[str, str]:
    """The outcome name and the protected name of a `counterfactually_invariant()` atom.

    One place decides what a well-formed atom is, so the solver's self-composition and the paired
    replay cannot drift on it — the same reason `contains_arguments` exists.

    Both arguments are signal names and never expressions. A computed value has no variable behind
    it for the protected copy of the encoding to *vary*, and no field of a replayed input to
    replace, so an expression in either position would name nothing either engine could act on.

    The two names must differ. `counterfactually_invariant(x, x)` asks whether `x` moves when `x`
    moves, which is answered by the shape of the question rather than by anything about a system.
    """
    if len(node.args) != 2:
        raise UnsupportedConstructError(
            f"{COUNTERFACTUAL_CALL}() takes an outcome signal name and a protected signal name: "
            f"{ast.unparse(node)!r}"
        )
    outcome, protected = node.args
    for argument, role in ((outcome, "outcome"), (protected, "protected")):
        if not isinstance(argument, ast.Name):
            raise UnsupportedConstructError(
                f"{COUNTERFACTUAL_CALL}()'s {role} argument is a signal name and not an "
                f"expression: {ast.unparse(node)!r}. Every engine has to bind it to a named "
                "variable of the decision procedure, and a computed value has no such variable"
            )
    if outcome.id == protected.id:
        raise UnsupportedConstructError(
            f"{COUNTERFACTUAL_CALL}({outcome.id}, {outcome.id}) asks whether {outcome.id!r} moves "
            "when it is itself moved, which the shape of the question answers and no system does. "
            "Name the decision as the outcome and the protected variable as the second argument"
        )
    return outcome.id, protected.id


def _signal_and_literals(node: ast.Call, call: str, roles: tuple[str, ...]) -> tuple[str, ...]:
    """A signal name followed by non-empty string literals, refusing every other shape.

    Shared by `undetermined_arguments` and `degree_arguments` because the two atoms have the same
    argument discipline `contains()` set: the first argument names one field of one decision record,
    so it is a name and not an expression, and every argument after it is a literal the *pack* fixes
    rather than a value the audited system supplies. A predicate word or an authority read out of
    the system's own log would be the `reason_is_specific` self-declaration with an extra step.
    """
    expected = 1 + len(roles)
    if len(node.args) != expected:
        raise UnsupportedConstructError(
            f"{call}() takes a signal name and {', '.join(roles)}: {ast.unparse(node)!r}"
        )
    signal, *literals = node.args
    if not isinstance(signal, ast.Name):
        raise UnsupportedConstructError(
            f"{call}() is about one signal of the decision record, so its first argument is a "
            f"signal name and not an expression: {ast.unparse(node)!r}"
        )
    values: list[str] = []
    for role, literal in zip(roles, literals, strict=True):
        if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
            raise UnsupportedConstructError(
                f"{call}()'s {role} is fixed by the pack, so it is a string literal and never a "
                f"name: {ast.unparse(node)!r}"
            )
        if not literal.value.strip():
            raise UnsupportedConstructError(
                f"{call}()'s {role} must be stated: {ast.unparse(node)!r} leaves it blank, which "
                "reports the reader a name for nothing"
            )
        values.append(literal.value)
    return (signal.id, *values)


def undetermined_arguments(node: ast.Call) -> tuple[str, str, str]:
    """The signal, the open-textured predicate and the authority of an `undetermined()` atom.

    All three are required, and the authority most of all: the point of the construct is that this
    tool does not settle the predicate and says who would. An atom that named no authority would be
    an ordinary not-evaluated result with extra syntax.
    """
    signal, predicate, authority = _signal_and_literals(
        node, UNDETERMINED_CALL, ("the open-textured predicate", "the authority that settles it")
    )
    return signal, predicate, authority


def degree_arguments(node: ast.Call) -> tuple[str, str]:
    """The signal and the open-textured predicate of a `degree()` atom.

    Deliberately no third argument naming where the degree came from: that is one account for the
    whole run and it belongs to the `Grading` supplied beside the pack, not to the pack. A pack that
    could name its own degree source would be naming an assessment nobody performed.
    """
    signal, predicate = _signal_and_literals(node, DEGREE_CALL, ("the open-textured predicate",))
    return signal, predicate


def _atom_calls(node: ast.AST, call: str) -> tuple[ast.Call, ...]:
    return tuple(
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == call
    )


def undetermined_atoms(node: ast.AST) -> tuple[tuple[str, str, str], ...]:
    """Every `undetermined()` atom of a property, as (signal, predicate, authority) triples."""
    return tuple(undetermined_arguments(call) for call in _atom_calls(node, UNDETERMINED_CALL))


def has_undetermined_atom(node: ast.AST) -> bool:
    """True when `undetermined()` occurs anywhere in a property."""
    return bool(_atom_calls(node, UNDETERMINED_CALL))


def has_degree_atom(node: ast.AST) -> bool:
    """True when `degree()` occurs anywhere in a property."""
    return bool(_atom_calls(node, DEGREE_CALL))


def degree_atoms(node: ast.AST) -> tuple[tuple[str, str], ...]:
    """Every `degree()` atom of a property, as (signal, predicate) pairs."""
    return tuple(degree_arguments(call) for call in _atom_calls(node, DEGREE_CALL))


def counterfactual_atom(node: ast.AST) -> tuple[str, str] | None:
    """The (outcome, protected) pair when the *whole* property is one counterfactual atom.

    `None` for every other shape, and that is deliberately the only shape the language admits: see
    `validate_property`, which refuses the atom in any other position. One atom, one meaning, and
    no general hyperproperty logic — a conjunction, an implication or a negation over a 2-safety
    atom is a different and much larger claim, and nothing here could discharge one.
    """
    if isinstance(node, ast.Expression):
        return counterfactual_atom(node.body)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == COUNTERFACTUAL_CALL
    ):
        return counterfactual_arguments(node)
    return None


def statistical_atom(node: ast.AST) -> tuple[str, str] | None:
    """Return the raw outcome/group signal pair for the whole statistical atom."""
    if isinstance(node, ast.Expression):
        return statistical_atom(node.body)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == STATISTICAL_CALL
    ):
        if len(node.args) != 2 or not all(isinstance(arg, ast.Name) for arg in node.args):
            raise UnsupportedConstructError(
                f"{STATISTICAL_CALL}() takes exactly two signal names: {ast.unparse(node)!r}"
            )
        return (node.args[0].id, node.args[1].id)
    return None


def has_statistical_atom(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == STATISTICAL_CALL
        for child in ast.walk(node)
    )


def has_counterfactual_atom(node: ast.AST) -> bool:
    """True when `counterfactually_invariant()` occurs anywhere in a property."""
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == COUNTERFACTUAL_CALL
        for child in ast.walk(node)
    )


def string_literal_mask(text: str) -> list[bool]:
    """Mark every character that lies inside a string literal, quotes included.

    Public because `engines/observed.py` rewrites atoms textually and must not rewrite one that a
    `contains()` phrase merely quotes. One implementation of "is this character inside a literal"
    is the only way the two rewriters agree about it.
    """
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
    in_string = string_literal_mask(text)
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
    in_string = string_literal_mask(text)
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
    """Rewrite `<=>`/`<->` and `=>`/`->` into Python-parsable form, respecting parentheses.

    Equivalence becomes `Iff(...)` and never `==`; see `EQUIVALENCE_CALL` for why a distinct node
    rather than a comparison. Chained equivalence stays refused as ambiguous while implication
    chains stay admitted right-associatively: `a -> b -> c` has a settled reading in every logic
    this package touches and `a <=> b <=> c` does not, so the author is asked which one they wrote.
    """
    index, token = _find_first_top_level(text, _EQUIVALENCE_TOKENS)
    if index >= 0:
        after = index + len(token)
        for other in _EQUIVALENCE_TOKENS:
            if _find_top_level(text, other, after) >= 0:
                raise UnsupportedConstructError(
                    f"Chained equivalence in {text!r} is ambiguous: parenthesise one side"
                )
        return (
            f"{EQUIVALENCE_CALL}(({_rewrite_sub(text[:index], text)}), "
            f"({_rewrite_sub(text[after:], text)}))"
        )

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


def _normalize_tokens_for_read_whole(text: str) -> list[str]:
    """Extract code tokens from expression text, skipping the pure syntax `unparse` normalises.

    Parens and a trailing comma carry no meaning and are normalised away by `ast.unparse`, so
    counting them would refuse an idiomatic multi-line call as truncated.
    """
    tokens = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in (
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NEWLINE,
                tokenize.NL,
            ):
                continue
            val = tok.string
            if val in ("(", ")", ","):
                continue
            tokens.append(val)
    except Exception as exc:
        raise UnsupportedConstructError(
            f"{text!r} could not be tokenised whole: {exc}. A partial token list would make a "
            "truncated specification look read whole, which is the failure this check exists to "
            "close."
        ) from exc
    return tokens


def verify_parsed_whole(text: str, node: ast.AST | None = None) -> None:
    """Verify that Python's parser read the whole source text without dropping text.

    `parse_expression` uses Python's `ast.parse`, which silently drops comments (`# ...`) and
    trailing unparsed tokens. This check verifies that unparsing the parsed AST accounts for all
    tokens in the source text. If text was dropped (resulting in fewer unparsed tokens than the
    input), `UnsupportedConstructError` is raised so every engine reports `not evaluated`
    rather than answering a truncated formula.
    """
    pre = preprocess_spec(text)
    if node is None:
        try:
            node = ast.parse(pre, mode="eval")
        except SyntaxError as exc:
            raise UnsupportedConstructError(
                f"{text!r} is not a property in this language: {exc.msg}."
            ) from exc
    unparsed = ast.unparse(node)

    tokens_pre = _normalize_tokens_for_read_whole(pre)
    tokens_unp = _normalize_tokens_for_read_whole(unparsed)

    if len(tokens_pre) > len(tokens_unp):
        raise UnsupportedConstructError(
            f"Specification {text!r} was not read whole: unparsing the parsed AST produced "
            f"{unparsed!r}, dropping text from the input."
        )


def parse_expression(text: str) -> ast.Expression:
    """Parse specification or constraint text into an AST after arrow normalisation."""
    tree = ast.parse(preprocess_spec(text), mode="eval")
    verify_parsed_whole(text, tree)
    return tree


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


def bounded_response_arguments(node: ast.AST) -> tuple[str, str, str]:
    """Return the two named event signals and duration of a ``within_after`` call.

    The construct is intentionally not a general interval expression: both event predicates must
    be exactly ``present(name)`` and the finite window must be a string accepted by the shared
    event-time parser.
    """
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == BOUNDED_RESPONSE_CALL
    ):
        raise UnsupportedConstructError(
            f"Expected {BOUNDED_RESPONSE_CALL}() call, got {ast.unparse(node)!r}"
        )
    if node.keywords or len(node.args) != 3:
        raise UnsupportedConstructError(
            f"{BOUNDED_RESPONSE_CALL} takes anchor, endpoint and duration: {ast.unparse(node)!r}"
        )

    names: list[str] = []
    for role, argument in zip(("anchor", "endpoint"), node.args[:2], strict=True):
        if not (
            isinstance(argument, ast.Call)
            and isinstance(argument.func, ast.Name)
            and argument.func.id == PRESENCE_CALL
            and len(argument.args) == 1
            and isinstance(argument.args[0], ast.Name)
            and not argument.keywords
        ):
            raise UnsupportedConstructError(
                f"{BOUNDED_RESPONSE_CALL}() {role} must be present(event_name), got "
                f"{ast.unparse(argument)!r}"
            )
        names.append(argument.args[0].id)
    if names[0] == names[1]:
        raise UnsupportedConstructError(
            f"{BOUNDED_RESPONSE_CALL}() needs distinct anchor and endpoint events, got "
            f"{names[0]!r} twice"
        )
    duration = node.args[2]
    if not isinstance(duration, ast.Constant) or not isinstance(duration.value, str):
        raise UnsupportedConstructError(
            f"{BOUNDED_RESPONSE_CALL}() duration must be a quoted fixed duration such as '24h' "
            f"or '1mo', got {ast.unparse(duration)!r}"
        )
    try:
        parse_duration(duration.value)
    except EventTimeError as exc:
        raise UnsupportedConstructError(
            f"{BOUNDED_RESPONSE_CALL}() has an invalid duration: {exc}"
        ) from exc
    return names[0], names[1], duration.value


def bounded_response_calls(node: ast.AST) -> tuple[ast.Call, ...]:
    """Return every metric-temporal call in an AST, in source order."""
    return tuple(
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == BOUNDED_RESPONSE_CALL
    )


def has_bounded_response(node: ast.AST) -> bool:
    """Whether a parsed property explicitly requests event-time bounded-response semantics."""
    return bool(bounded_response_calls(node))


def _validate_bounded_response_shape(node: ast.AST) -> None:
    """Keep the metric extension to one named bounded-response shape."""
    calls = bounded_response_calls(node)
    if not calls:
        return
    if len(calls) != 1:
        raise UnsupportedConstructError(
            f"A property may contain exactly one {BOUNDED_RESPONSE_CALL}() obligation; "
            f"got {len(calls)}"
        )
    bounded_response_arguments(calls[0])
    body = node.body if isinstance(node, ast.Expression) else node
    allowed = (
        isinstance(body, ast.Call)
        and isinstance(body.func, ast.Name)
        and body.func.id == BOUNDED_RESPONSE_CALL
    )
    if not allowed:
        allowed = (
            isinstance(body, ast.Call)
            and isinstance(body.func, ast.Name)
            and body.func.id == ALWAYS_OPERATOR
            and len(body.args) == 1
            and isinstance(body.args[0], ast.Call)
            and isinstance(body.args[0].func, ast.Name)
            and body.args[0].func.id in IMPLICATION_CALLS
            and len(body.args[0].args) == 2
            and isinstance(body.args[0].args[1], ast.Call)
            and body.args[0].args[1] is calls[0]
        )
    if not allowed:
        raise UnsupportedConstructError(
            f"{BOUNDED_RESPONSE_CALL}() is only supported alone or as "
            f"always(implies(present(anchor), {BOUNDED_RESPONSE_CALL}(...)))"
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
        if name == CONTAINS_CALL:
            contains_arguments(node)
            return "boolean"
        if name == COUNTERFACTUAL_CALL:
            counterfactual_arguments(node)
            return "boolean"
        if name == STATISTICAL_CALL:
            statistical_atom(node)
            return "boolean"
        if name == UNDETERMINED_CALL:
            undetermined_arguments(node)
            return "boolean"
        if name == BOUNDED_RESPONSE_CALL:
            bounded_response_arguments(node)
            return "boolean"
        if name == DEGREE_CALL:
            # Boolean in the *type* system of this language, and a degree only under the graded
            # reading. Saying "number" here would let it stand as an operand of arithmetic and of a
            # comparison, which is exactly what `manyvalued.degree_of` refuses: a comparison of two
            # degrees is a threshold, and a threshold in a shipped pack is the pack author's number
            # presented as the regulation's.
            degree_arguments(node)
            return "boolean"
        if name in TEMPORAL_OPERATORS:
            operands = 2 if name in BINARY_TEMPORAL_OPERATORS else 1
            if len(node.args) != operands:
                raise UnsupportedConstructError(
                    f"{name} takes {operands} operand(s), got {len(node.args)}: "
                    f"{ast.unparse(node)!r}"
                )
            for argument in node.args:
                _require_kind(expression_kind(argument), "boolean", argument)
            return "boolean"
        arity = VALUE_CALLS.get(name)
        if arity is None:
            raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")
        if len(node.args) != arity:
            raise UnsupportedConstructError(
                f"{name} expects {arity} argument(s), got {len(node.args)}"
            )
        kinds = [expression_kind(argument) for argument in node.args]
        expected_kind = "boolean" if name in BOOLEAN_CONNECTIVE_CALLS else "number"
        for argument, kind in zip(node.args, kinds, strict=True):
            _require_kind(kind, expected_kind, argument)
        return expected_kind

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def validate_property(node: ast.AST) -> None:
    """Refuse a parsed expression that is not a Boolean property in this language."""
    if has_statistical_atom(node) and statistical_atom(node) is None:
        raise UnsupportedConstructError(
            f"{STATISTICAL_CALL}() is a population measurement and must be the whole of a spec: "
            f"{ast.unparse(node)!r} mixes the aggregate with another construct"
        )
    # The one relational atom stands alone or not at all. A conjunction, a negation or an
    # implication over a 2-safety atom is a strictly larger claim — a property of a pair of runs
    # combined with a property of one, or with a second pair — and no engine here discharges one.
    # Admitting the shape and reporting it not evaluated would put the atom into `logical`'s reach
    # via classification, where the trace rung would answer the part it could read and call the
    # result the duty's.
    if has_counterfactual_atom(node) and counterfactual_atom(node) is None:
        raise UnsupportedConstructError(
            f"{COUNTERFACTUAL_CALL}() is a property of a *pair* of executions and is the whole of "
            f"a spec or no part of one: {ast.unparse(node)!r} combines it with something else. "
            "Nothing here discharges a combination, and admitting one would let the part that is "
            "a property of one decision be answered off a trace and reported as the duty"
        )
    # The two open-texture atoms answer different questions and a formula asking both answers
    # neither. `undetermined()` says nothing here settles the predicate, so the duty is not
    # evaluated whatever else the formula says; `degree()` says the predicate is graded and asks for
    # the whole formula to be read over the declared algebra. A spec carrying both would be graded
    # by classification and never graded in fact, which is a pack author told a semantics ran that
    # did not.
    if has_undetermined_atom(node) and has_degree_atom(node):
        raise UnsupportedConstructError(
            f"{ast.unparse(node)!r} uses both {UNDETERMINED_CALL}() and {DEGREE_CALL}(). The first "
            "says no engine here settles the predicate and the second asks for it to be graded "
            "over the pack's algebra; a duty is one or the other. Split the clause, or decide "
            "which reading the predicate gets — see docs/semantics.md §9"
        )
    # A graded atom under a temporal operator would need a many-valued reading of the operator, and
    # this package implements no temporal semantics of its own at any rung (see the module docstring
    # of `ltlf.py` and `engines/observed.to_stl`). Refused at load rather than reported not
    # evaluated at run time, so the pack author learns it where the spec is written.
    for call in (
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id in TEMPORAL_OPERATORS
    ):
        if has_degree_atom(call):
            raise UnsupportedConstructError(
                f"{ast.unparse(call)!r} puts a {DEGREE_CALL}() atom under a temporal operator. A "
                "many-valued reading of a temporal operator is a temporal semantics, and this "
                "package implements none — the graded fragment is a property of one decision "
                "record, quantified over the trace by the infimum of its per-record degrees "
                "(docs/semantics.md §9)"
            )
    # A graded atom under a comparison **states a threshold**, and this is the one place a graded
    # pack could launder a compliance cut-off into something that looks like a formula:
    # `degree(x, "p") >= 0.8` says eight tenths discharges the duty, which no statute says. Under
    # arithmetic it asks for a number on a scale this package has not defined. Both are refused
    # where the spec is written rather than reported not evaluated at run time — the pack author is
    # the person who can fix it.
    for parent in (
        child
        for child in ast.walk(node)
        if isinstance(child, (ast.Compare, ast.BinOp, ast.UnaryOp))
        and not isinstance(getattr(child, "op", None), ast.Not)
    ):
        if has_degree_atom(parent):
            raise UnsupportedConstructError(
                f"{ast.unparse(parent)!r} puts a {DEGREE_CALL}() atom under a comparison or "
                "arithmetic. A comparison of degrees is a threshold, and a threshold written into "
                "a pack is the author's number presented as the regulation's; arithmetic on a "
                "degree asks for a number on a scale this package has not defined. A graded atom "
                "stands under the boolean connectives and under an implication, and nowhere else "
                "(docs/semantics.md §9)"
            )
    _validate_bounded_response_shape(node)
    kind = expression_kind(node)
    if kind not in ("boolean", "unknown"):
        raise UnsupportedConstructError(
            f"Requirement spec {ast.unparse(node)!r} is not a boolean property"
        )
    constants = bare_boolean_constants(node)
    if constants:
        values = ", ".join(repr(value) for value in constants)
        raise UnsupportedConstructError(
            f"Boolean constant(s) {values} cannot stand as bare Boolean atoms. Compare a signal "
            "to a Boolean constant when that is the property being stated"
        )
    conflicting = sorted(set(bare_boolean_names(node)) & set(measured_magnitude_names(node)))
    if conflicting:
        raise UnsupportedConstructError(
            "Signal(s) used in both a bare Boolean role and a measured magnitude role: "
            f"{', '.join(conflicting)}. A signal cannot have both roles in one property"
        )


def validate_temporal_property(node: ast.AST) -> None:
    """Refuse valid state expressions that the temporal fragment cannot render soundly."""
    for comparison in (item for item in ast.walk(node) if isinstance(item, ast.Compare)):
        left = comparison.left
        for operator, right in zip(comparison.ops, comparison.comparators, strict=True):
            boolean = None
            operand = None
            if isinstance(left, ast.Constant) and isinstance(left.value, bool):
                boolean = left.value
                operand = right
            elif isinstance(right, ast.Constant) and isinstance(right.value, bool):
                boolean = right.value
                operand = left
            if boolean is not None and isinstance(operator, (ast.Eq, ast.NotEq)):
                rendered = ast.unparse(ast.Compare(left=left, ops=[operator], comparators=[right]))
                if isinstance(operand, ast.Name):
                    positive = boolean == isinstance(operator, ast.Eq)
                    atom = operand.id if positive else f"not {operand.id}"
                    raise UnsupportedConstructError(
                        f"Temporal comparison {rendered!r} against a Boolean constant is "
                        f"unsupported; write the bare Boolean atom instead, for example "
                        f"always({atom})"
                    )
                raise UnsupportedConstructError(
                    f"Temporal comparison {rendered!r} against a Boolean constant is "
                    "unsupported; write the Boolean expression directly as an atom"
                )
            left = right


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


def valuations_over(
    atom_keys: Iterable[str], records: Iterable[Mapping[str, Any]]
) -> list[dict[str, bool]]:
    """Evaluate rendered atom expressions over records as Boolean valuations.

    External finite-trace procedures may use a propositional abstraction of this language.
    Re-parse each atom with the reference interpreter so a plug-in and the witness checker share
    the same treatment of missing values and Kleene ``UNKNOWN``.
    """
    nodes = [(key, parse_expression(key)) for key in atom_keys]
    return [
        {key: kleene_value(eval_expression(node, dict(record))) is True for key, node in nodes}
        for record in records
    ]


def _is_presence_only(node: ast.AST) -> bool:
    """True when a node is settled by `present()` atoms and boolean connectives over them alone.

    This is the shape a disjunct must have for the either/or exemption to reach it: whether such a
    branch holds is decided by which signals a record carries, so a system that supplies the other
    branch instead settles the formula without ever reading this one.
    """
    if isinstance(node, ast.Expression):
        return _is_presence_only(node.body)
    if isinstance(node, ast.BoolOp):
        return all(_is_presence_only(value) for value in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _is_presence_only(node.operand)
    return presence_atoms(node) is not None


def unconditional_signal_names(node: ast.AST) -> tuple[str, ...]:
    """The signal names a property cannot be evaluated without, sorted.

    Every name `signal_names` reports, except those a disjunction makes into an *alternative*:
    `present(a) or present(b)` is settled by whichever of the two a system supplies, so neither `a`
    nor `b` alone is a signal the property needs. The pack loader uses this, not `signal_names`, to
    decide which names a requirement's `requires` must gate — because `requires` is a conjunctive
    gate, and listing an alternative there reports a system that lawfully took the *other* branch
    unattainable without running it.

    Two conditions narrow the exemption, and neither is optional:

    - **Every disjunct must be settled by `present()` atoms alone** (`_is_presence_only`), or the
      disjunction exempts nothing. `(latency <= 30) or (latency <= 90)` gates `latency`: a magnitude
      has to be readable before either operand exists, so a system that cannot emit it is
      unattainable on the whole clause rather than run and reported not evaluated.
    - **A name occurring in every disjunct stays gated.** `(present(a) and present(b)) or
      (present(a) and present(c))` needs `a` whichever branch settles it, so only `b` and `c` are
      alternatives. The exemption is the names of the disjunction minus the names common to all of
      its branches.

    The rest of the walk reaches disjunctions through the boolean connectives and through calls —
    `always(a and (b or c))` exempts `b` and `c`, because a temporal operator quantifies its
    argument over the trace without making the signals inside it optional. An implication is not
    treated as conditional: `Implies(a, b)` still needs `b` to be readable before it can be settled
    at all, and narrowing the gate on evaluation order would be a claim this language does not make.
    A disjunction standing as an operand of a comparison or of arithmetic is not exempt for the same
    reason: that value has to be computed before the operand exists.
    """
    if isinstance(node, ast.Expression):
        return unconditional_signal_names(node.body)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.Or):
            if not all(_is_presence_only(value) for value in node.values):
                return signal_names(node)
            common: set[str] | None = None
            for value in node.values:
                branch = set(signal_names(value))
                common = branch if common is None else common & branch
            return tuple(sorted(common or set()))
        names: list[str] = []
        for value in node.values:
            names.extend(unconditional_signal_names(value))
        return tuple(sorted(set(names)))
    if isinstance(node, ast.Call):
        inner: list[str] = []
        for arg in node.args:
            inner.extend(unconditional_signal_names(arg))
        return tuple(sorted(set(inner)))
    return signal_names(node)


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


def _bare_boolean_parts(node: ast.AST) -> tuple[tuple[str, ...], tuple[bool, ...]]:
    names: set[str] = set()
    constants: set[bool] = set()

    def visit(current: ast.AST, boolean_position: bool = False) -> None:
        if isinstance(current, ast.Expression):
            visit(current.body, True)
        elif isinstance(current, ast.Name):
            if boolean_position:
                names.add(current.id)
        elif isinstance(current, ast.Constant):
            if boolean_position and isinstance(current.value, bool):
                constants.add(current.value)
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
            if name in TEMPORAL_OPERATORS or name in BOOLEAN_CONNECTIVE_CALLS:
                for argument in current.args:
                    visit(argument, True)
            elif name not in _SIGNAL_ARGUMENT_CALLS:
                for argument in current.args:
                    visit(argument)

    visit(node)
    return tuple(sorted(names)), tuple(sorted(constants))


def bare_boolean_names(node: ast.AST) -> tuple[str, ...]:
    """Signal names used directly where the property language requires a Boolean value."""
    return _bare_boolean_parts(node)[0]


def bare_boolean_constants(node: ast.AST) -> tuple[bool, ...]:
    """Boolean literals used directly where the property language requires a Boolean atom."""
    return _bare_boolean_parts(node)[1]


def _value_signal_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _SIGNAL_ARGUMENT_CALLS
    ):
        return set()
    names: set[str] = set()
    for child in ast.iter_child_nodes(node):
        if isinstance(node, ast.Call) and child is node.func:
            continue
        names.update(_value_signal_names(child))
    return names


def _flag_comparison(left: ast.AST, operator: ast.cmpop, right: ast.AST) -> bool:
    left_flag = (
        isinstance(left, ast.Name)
        and isinstance(operator, ast.GtE)
        and isinstance(right, ast.Constant)
        and not isinstance(right.value, bool)
        and right.value == FLAG_THRESHOLD
    )
    right_flag = (
        isinstance(right, ast.Name)
        and isinstance(operator, ast.LtE)
        and isinstance(left, ast.Constant)
        and not isinstance(left.value, bool)
        and left.value == FLAG_THRESHOLD
    )
    return left_flag or right_flag


def measured_magnitude_names(node: ast.AST) -> tuple[str, ...]:
    """Signals used in comparisons that require measured numeric magnitudes."""
    names: set[str] = set()
    for comparison in (item for item in ast.walk(node) if isinstance(item, ast.Compare)):
        left = comparison.left
        for operator, right in zip(comparison.ops, comparison.comparators, strict=True):
            if not _flag_comparison(left, operator, right):
                names.update(_value_signal_names(left))
                names.update(_value_signal_names(right))
            left = right
    return tuple(sorted(names))


def has_temporal_operator(node: ast.AST) -> bool:
    """True when a property reaches across records or requests event-time metric semantics."""
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id in (TEMPORAL_OPERATORS | {BOUNDED_RESPONSE_CALL})
        for child in ast.walk(node)
    )


def implication_antecedent(node: ast.AST) -> ast.AST | None:
    """The antecedent of a property that is one implication, or `None` for every other shape.

    This is the whole of the unreachable-trigger rule that is a fact about the *formula*, and it
    lives here for the reason the fragment classifier does: there is one property language, every
    engine parses the same `spec` through it, and the antecedent is the same subtree whatever
    domain the engine goes on to quantify over. Seven engines each guard the domain they built —
    an empty trace, an empty plan, unsatisfiable premises — and not one of them could see this,
    because a duty whose trigger fires nowhere has a domain that is full and evidence that is
    empty. The engines ask this one question and answer it with the machinery they already hold:
    the solver checks premises ∧ antecedent, the monitor scores the antecedent per position, the
    replay search evaluates it per replayed decision. What they do with the answer is
    `report.not_evaluated_for_unreachable_trigger`, so the sentence a reader gets is also written
    once.

    A top-level `always` is stripped first: over a finite trace `always(f)` holds exactly when `f`
    holds at every position, so an antecedent inside `f` that is true at no position leaves the
    quantification vacuous in the same sense. `eventually(f)` is deliberately not stripped — its
    vacuity is a different claim, about a position that never existed rather than a trigger that
    never fired — and neither is a conjunction of implications, whose antecedents are several and
    whose vacuity is per-conjunct. Both are limits stated in `docs/semantics.md` §4 rather than
    guessed at here.
    """
    if isinstance(node, ast.Expression):
        return implication_antecedent(node.body)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == ALWAYS_OPERATOR and len(node.args) == 1:
            return implication_antecedent(node.args[0])
        if node.func.id in ("implies", "Implies") and len(node.args) == 2:
            return node.args[0]
    return None


def classify_fragment(spec: str) -> str:
    """The narrowest fragment of this language `spec` belongs to.

    `counterfactual` when it is the one relational atom; `temporal` when anything in it reaches
    across records; `record` when it is a conjunction of presence atoms and nothing else; `logical`
    for every other well-formed state property. Raises `UnsupportedConstructError` for text that is
    not in the language at all.

    `counterfactual` is asked first and is exclusive: `validate_property` has already refused every
    shape mixing the atom with anything else, so a spec reaching here either *is* the atom or does
    not contain one. Classifying it into `logical` would be the whole defect — the fragment is what
    decides which engines may discharge a duty, and a trace cannot establish a counterfactual.
    """
    node = parse_property(spec)
    if statistical_atom(node) is not None:
        return "statistical"
    if counterfactual_atom(node) is not None:
        return "counterfactual"
    # `undetermined` is asked before everything else that follows, and it dominates: one atom no
    # engine settles leaves the whole formula unsettled, so a spec carrying one is not a `record`
    # duty with an asterisk. Classifying it by its presence conjuncts would answer the settleable
    # part and report the answer as the duty's, which is the substitution presence-as-a-proxy
    # already is and this construct exists to end.
    if has_undetermined_atom(node):
        return "undetermined"
    if has_degree_atom(node):
        return "graded"
    if has_temporal_operator(node):
        validate_temporal_property(node)
        return "temporal"
    return "record" if presence_atoms(node) is not None else "logical"


class _UnknownType:
    """Kleene 3-valued logic UNKNOWN sentinel."""

    def __repr__(self) -> str:
        return "UNKNOWN"

    def __bool__(self) -> bool:
        raise TypeError("Boolean value of UNKNOWN is undefined; use Kleene operators")


UNKNOWN = _UnknownType()


def is_unknown(val: Any) -> bool:
    """Whether `val` is the Kleene 3-valued logic UNKNOWN value."""
    return val is UNKNOWN


def kleene_value(val: Any) -> Any:
    """Read `val` as an element of the Kleene chain `F < U < T`.

    Every Kleene operator here reads its operands through this, so a truth *value* decides the
    table rather than an identity comparison against `True`/`False`. An atom of this language may
    return `0`, `1`, `""` or another falsy or truthy value the audited system supplied, and one of
    those tested by identity is neither `False` nor `UNKNOWN` and would fall through to the
    operator's unit — a genuine `True` off a falsy conjunct, and a genuine `False` off a truthy
    disjunct, at every rung that does not guard its atoms.
    """
    return UNKNOWN if is_unknown(val) else bool(val)


def kleene_not(val: Any) -> Any:
    if is_unknown(val):
        return UNKNOWN
    return not bool(val)


def kleene_and_binary(a: Any, b: Any) -> Any:
    return kleene_and((a, b))


def kleene_or_binary(a: Any, b: Any) -> Any:
    return kleene_or((a, b))


def kleene_and(vals: Iterable[Any]) -> Any:
    res: Any = True
    for val in vals:
        v = kleene_value(val)
        if v is False:
            return False
        if is_unknown(v):
            res = UNKNOWN
    return res


def kleene_or(vals: Iterable[Any]) -> Any:
    res: Any = False
    for val in vals:
        v = kleene_value(val)
        if v is True:
            return True
        if is_unknown(v):
            res = UNKNOWN
    return res


def kleene_implies(a: Any, b: Any) -> Any:
    return kleene_or_binary(kleene_not(a), b)


def kleene_iff(a: Any, b: Any) -> Any:
    return kleene_and_binary(kleene_implies(a, b), kleene_implies(b, a))


def eval_expression(node: ast.AST, env: dict[str, Any]) -> Any:
    """Evaluate a whitelisted expression AST against `env` under Kleene 3-valued logic."""
    if isinstance(node, ast.Expression):
        return eval_expression(node.body, env)

    if isinstance(node, ast.Constant):
        if node.value is None or isinstance(node.value, (bool, int, float, str)):
            return node.value
        raise UnsupportedConstructError(
            f"Unsupported constant type {type(node.value).__name__}: {node.value!r}"
        )

    if isinstance(node, ast.Name):
        if node.id in env and env[node.id] is not None and not is_unknown(env[node.id]):
            return env[node.id]
        return UNKNOWN

    if isinstance(node, ast.UnaryOp):
        operand = eval_expression(node.operand, env)
        if isinstance(node.op, ast.Not):
            return kleene_not(operand)
        if is_unknown(operand):
            return UNKNOWN
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise UnsupportedConstructError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = eval_expression(node.left, env)
        right = eval_expression(node.right, env)
        if is_unknown(left) or is_unknown(right):
            return UNKNOWN
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
            return kleene_and([eval_expression(value, env) for value in node.values])
        if isinstance(node.op, ast.Or):
            return kleene_or([eval_expression(value, env) for value in node.values])
        raise UnsupportedConstructError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = eval_expression(node.left, env)
        if is_unknown(left):
            return UNKNOWN
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            right = eval_expression(comparator, env)
            if is_unknown(right):
                return UNKNOWN
            if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                is_flag = _flag_comparison(node.left, op, comparator)
                if is_flag:
                    conv_left = (1.0 if left else 0.0) if isinstance(left, bool) else left
                    conv_right = (1.0 if right else 0.0) if isinstance(right, bool) else right
                else:
                    if isinstance(left, bool) or isinstance(right, bool):
                        return UNKNOWN
                    conv_left, conv_right = left, right
                if (
                    not isinstance(conv_left, (int, float))
                    or not isinstance(conv_right, (int, float))
                    or not (math.isfinite(conv_left) and math.isfinite(conv_right))
                ):
                    return UNKNOWN
                held = (
                    conv_left < conv_right
                    if isinstance(op, ast.Lt)
                    else conv_left <= conv_right
                    if isinstance(op, ast.LtE)
                    else conv_left > conv_right
                    if isinstance(op, ast.Gt)
                    else conv_left >= conv_right
                )
            elif isinstance(op, ast.Eq):
                held = left == right
            elif isinstance(op, ast.NotEq):
                held = left != right
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
            if len(node.args) != 1 or not isinstance(node.args[0], ast.Name):
                raise UnsupportedConstructError(
                    f"{PRESENCE_CALL}() takes one signal name: {ast.unparse(node)!r}"
                )
            return is_present(env.get(node.args[0].id))
        if name == CONTAINS_CALL:
            signal, phrase = contains_arguments(node)
            return contains_literal(env.get(signal), phrase)
        if name == STATISTICAL_CALL:
            outcome, group = statistical_atom(node) or ("", "")
            raise UnsupportedConstructError(
                f"{STATISTICAL_CALL}({outcome}, {group}) is a population measurement and cannot "
                "be evaluated against one decision record; use the statistical evaluator over the "
                "raw sample"
            )
        if name == COUNTERFACTUAL_CALL:
            outcome, protected = counterfactual_arguments(node)
            raise UnsupportedConstructError(
                f"{COUNTERFACTUAL_CALL}({outcome}, {protected}) cannot be evaluated against a "
                "decision record. A record is what the system decided; this atom asks what it "
                "would have decided had "
                f"{protected!r} differed and nothing else had. That is a property of a pair of "
                "executions, and it is established by encoding the declared rules twice or by "
                "replaying a paired input — never read off a log"
            )
        if name == UNDETERMINED_CALL:
            signal, predicate, authority = undetermined_arguments(node)
            raise UnsupportedConstructError(
                f"{UNDETERMINED_CALL}({signal}, {predicate!r}, {authority!r}) is a predicate the "
                "law states without a sharp boundary, and nothing here settles it. It is neither "
                f"true nor false of this record: {authority} settles it, and this tool reports "
                "that rather than guessing"
            )
        if name == DEGREE_CALL:
            signal, predicate = degree_arguments(node)
            raise UnsupportedConstructError(
                f"{DEGREE_CALL}({signal}, {predicate!r}) has a truth degree and not a truth value. "
                "It is read over the algebra the pack declares, against a grading whose source is "
                "declared beside it, and never off a decision record as a flag — see "
                "reasonsmith.manyvalued and docs/semantics.md §9"
            )
        args = [eval_expression(arg, env) for arg in node.args]
        if name in ("implies", "Implies"):
            _require_arity(name, args, 2)
            return kleene_implies(args[0], args[1])
        if name == EQUIVALENCE_CALL:
            _require_arity(name, args, 2)
            return kleene_iff(args[0], args[1])
        if name == "abs":
            _require_arity(name, args, 1)
            if is_unknown(args[0]):
                return UNKNOWN
            return abs(args[0])
        if name == "min":
            _require_arity(name, args, 2)
            if is_unknown(args[0]) or is_unknown(args[1]):
                return UNKNOWN
            return min(args[0], args[1])
        if name == "max":
            _require_arity(name, args, 2)
            if is_unknown(args[0]) or is_unknown(args[1]):
                return UNKNOWN
            return max(args[0], args[1])
        raise UnsupportedConstructError(f"Unsupported function call: {ast.unparse(node)!r}")

    raise UnsupportedConstructError(f"Unsupported language construct: {type(node).__name__}")


def _require_arity(name: str, args: list[Any], expected: int) -> None:
    if len(args) != expected:
        raise UnsupportedConstructError(f"{name} expects {expected} argument(s), got {len(args)}")


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


def eval_temporal_trace(node: ast.AST, records: list[dict[str, Any]]) -> list[Any]:
    """Evaluate a temporal or state property AST over a finite trace of decision records

    under Kleene 3-valued logic.
    Returns a list of 3-valued truth values `[b_0, b_1, ..., b_{N-1}]`, where each `b_i` is
    `True`, `False`, or `UNKNOWN`. The trace verdict is `b_0` for temporal properties or
    `kleene_and(b)` for state properties.
    """
    if isinstance(node, ast.Expression):
        return eval_temporal_trace(node.body, records)

    if not has_temporal_operator(node):
        return [kleene_value(eval_expression(node, r)) for r in records]

    n = len(records)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        sub = eval_temporal_trace(node.operand, records)
        return [kleene_not(b) for b in sub]

    if isinstance(node, ast.BoolOp):
        subs = [eval_temporal_trace(v, records) for v in node.values]
        if isinstance(node.op, ast.And):
            return [kleene_and([s[i] for s in subs]) for i in range(n)]
        if isinstance(node.op, ast.Or):
            return [kleene_or([s[i] for s in subs]) for i in range(n)]
        raise UnsupportedConstructError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name in IMPLICATION_CALLS:
            left = eval_temporal_trace(node.args[0], records)
            right = eval_temporal_trace(node.args[1], records)
            return [kleene_implies(left[i], right[i]) for i in range(n)]
        if name == EQUIVALENCE_CALL:
            left = eval_temporal_trace(node.args[0], records)
            right = eval_temporal_trace(node.args[1], records)
            return [kleene_iff(left[i], right[i]) for i in range(n)]
        if name == BOUNDED_RESPONSE_CALL:
            raise UnsupportedConstructError(
                f"{BOUNDED_RESPONSE_CALL}() requires the observed event-time metric evaluator"
            )
        if name in TEMPORAL_OPERATORS:
            if name == "always":
                sub = eval_temporal_trace(node.args[0], records)
                return [kleene_and(sub[i:n]) for i in range(n)]
            if name == "eventually":
                sub = eval_temporal_trace(node.args[0], records)
                return [kleene_or(sub[i:n]) for i in range(n)]
            if name == "historically":
                sub = eval_temporal_trace(node.args[0], records)
                return [kleene_and(sub[0 : i + 1]) for i in range(n)]
            if name == "once":
                sub = eval_temporal_trace(node.args[0], records)
                return [kleene_or(sub[0 : i + 1]) for i in range(n)]
            if name == "next":
                sub = eval_temporal_trace(node.args[0], records)
                return [sub[i + 1] if i + 1 < n else True for i in range(n)]
            if name == "prev":
                sub = eval_temporal_trace(node.args[0], records)
                return [sub[i - 1] if i > 0 else True for i in range(n)]
            if name == "rise":
                sub = eval_temporal_trace(node.args[0], records)
                return [
                    sub[0] if i == 0 else kleene_and_binary(sub[i], kleene_not(sub[i - 1]))
                    for i in range(n)
                ]
            if name == "fall":
                sub = eval_temporal_trace(node.args[0], records)
                return [
                    kleene_not(sub[0])
                    if i == 0
                    else kleene_and_binary(kleene_not(sub[i]), sub[i - 1])
                    for i in range(n)
                ]
            if name == "until":
                left = eval_temporal_trace(node.args[0], records)
                right = eval_temporal_trace(node.args[1], records)
                return [
                    kleene_or(
                        [kleene_and_binary(right[j], kleene_and(left[i:j])) for j in range(i, n)]
                    )
                    for i in range(n)
                ]
            if name == "since":
                left = eval_temporal_trace(node.args[0], records)
                right = eval_temporal_trace(node.args[1], records)
                return [
                    kleene_or(
                        [
                            kleene_and_binary(right[j], kleene_and(left[j + 1 : i + 1]))
                            for j in range(0, i + 1)
                        ]
                    )
                    for i in range(n)
                ]

    raise UnsupportedConstructError(f"Unsupported temporal construct: {ast.unparse(node)!r}")
