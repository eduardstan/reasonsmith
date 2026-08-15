"""Analysis of a requirement pack as a set of formulas, rather than of one system's evidence.

What this module is for:
  `check` asks what a system's evidence says about a duty. This module asks four questions about
  the duties themselves, none of which any other code path can answer:

  - **Satisfiability.** Is a pack's requirement set jointly satisfiable — is there any decision
    record at all that discharges every duty in it at once? A pack whose duties contradict each
    other reports every system violated for a reason that is the pack's and not the system's.
  - **Subsumption and equivalence.** Does one requirement's property entail another's? Two
    byte-identical properties cannot come apart in any report, and until now that was found by a
    human reading TOML and written into prose (`docs/refinement.md`, EU AI Act Article 12(2)).
  - **Vacuity.** Is a duty discharged without its own content doing any work — Kupferman and
    Vardi's question (`[@kupferman-2003]`, in the replacement formulation of `[@beer-2001]`),
    restricted to the fragments this repository ships. `docs/semantics.md` §8
    states the definition and what it costs; the existing
    `report.not_evaluated_for_unreachable_trigger` is the special case where the replaceable
    subformula is an implication's consequent, and the acceptance test
    `test_vacuity_coincides_with_the_unreachable_trigger_rule` holds the two together.
  - **Coverage.** Mutate a system's exposed `logic()`, re-run the pack, and record which duties
    notice. A duty no mutant moves has no discriminating power against these mutants.

What a reader must not break:
  - The Z3 encoding is `engines/proved.py`'s, reached through `_ast_to_z3` and `_Scope`, and there
    is no second one here. `_PackScope` overrides exactly two methods — the two atoms whose meaning
    genuinely differs when there is no system to assign anything — and every connective,
    comparison and arithmetic operator stays the engine's.
    Why this matters: a second encoding that disagrees with the first is the defect this
    repository already guards against between the solver and the interpreter for `contains()`. An
    analysis that reasons about a formula the engines do not implement reports findings about a
    pack nobody runs.
  - A question the encoding cannot reach is **skipped by name**, never answered. The
    `counterfactual` fragment is a property of a pair of executions and is not encoded here at
    all; a temporal spec that is not `always(state property)` is not reduced *by the Z3 encoding*.
    Why this matters: a silent omission reads as "nothing found", which is the overclaim this
    package exists to refuse. Every skip travels in `PackAnalysis.skipped`.
  - The temporal fragment is decided **as a formula of a finite-trace logic**, by `ltlf.py`, and
    that is a second decision procedure over a second abstraction rather than a widening of the
    first. Z3 keeps every magnitude and decides one record; LTLf keeps every position and abstracts
    every magnitude to an opaque atom. Neither subsumes the other, `LTLF_ABSTRACTION_LIMIT` says so
    on the answers that rest on it, and the backend is an **optional extra** whose absence is a
    note and never a weaker answer wearing the same words.
    Why this matters: before it, `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` — a shipped
    binding duty written with `until` — was skipped by every question this module asks.
  - The mutation score is **not a coverage claim**, and `MUTATION_LIMIT` says so on the analysis
    that carries one. It reaches only a system that exposes `logic()` as a rule block, which is
    not most audited systems, and it measures sensitivity to *these* mutants and to no others.
    Why this matters: a number rendered beside a pack invites being read as the pack's quality.
    What it measures is whether a duty can tell two rule sets apart.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from typing import Any, Optional

import z3

from reasonsmith.engines.proved import (
    UnsupportedConstructError,
    _as_bool,
    _ast_to_z3,
    _check_declared_directions,
    _Scope,
    encode_logic_domain,
)
from reasonsmith.engines.temporal import state_property_under_always
from reasonsmith.ltlf import (
    LTLF_ABSTRACTION_LIMIT,
    UNAVAILABLE_NOTE,
    Abstraction,
    available,
    entails,
    satisfiable,
    to_ltlf,
)
from reasonsmith.report import check_conformance
from reasonsmith.rulelang import (
    CONTAINS_CALL,
    COUNTERFACTUAL_CALL,
    PRESENCE_CALL,
    bare_boolean_names,
    parse_property,
)
from reasonsmith.spec import Pack, Requirement
from reasonsmith.sut import SystemUnderTest

__all__ = [
    "MUTATION_LIMIT",
    "MutationScore",
    "PackAnalysis",
    "Relation",
    "TemporalAnalysis",
    "VacuityFinding",
    "analyse_pack",
    "mutate_rules",
    "render_analysis",
    "vacuous_subformulas",
]

#: The limit every mutation score carries, stated on the analysis that makes the claim, for the
#: reason `REAL_ARITHMETIC_LIMIT` is stated on the proof that rests on it.
MUTATION_LIMIT = (
    "Limit of this score: mutation analysis reaches only a system that exposes its decision logic "
    "as a rule block through sut.logic(), which is not most audited systems — a decision log or an "
    "opaque scorer has nothing to mutate, and no duty gets a score at all. Where it does run, the "
    "score is sensitivity to the mutants generated below and to no others: it is not a measure of "
    "how much of the system a duty covers, and a duty scoring 1.0 is not thereby a good duty."
)

#: The atoms whose arguments name signals rather than expressions, and into whose arguments the
#: vacuity walk therefore does not descend: replacing the *name* inside `present(x)` is not
#: replacing a subformula.
_SIGNAL_ATOMS = (PRESENCE_CALL, CONTAINS_CALL, COUNTERFACTUAL_CALL)


@dataclass(frozen=True)
class Relation:
    """One requirement's property entails another's, in one direction or in both."""

    left: str
    right: str
    equivalent: bool


@dataclass(frozen=True)
class VacuityFinding:
    """A subformula of a requirement's spec that any other formula could replace."""

    requirement_id: str
    subformula: str
    domain: str


@dataclass(frozen=True)
class MutationScore:
    """How many mutants of a system's declared rules one requirement's verdict noticed."""

    requirement_id: str
    detected: int
    mutants: int

    @property
    def score(self) -> float:
        return self.detected / self.mutants if self.mutants else 0.0


@dataclass(frozen=True)
class TemporalAnalysis:
    """What the finite-trace decision procedure said about a pack's temporal duties.

    `decided` names every temporal requirement it rendered and answered; `unsatisfiable` names the
    ones no non-empty finite trace discharges, which is a defect in the pack and not in any system.
    `relations` carries entailments between two temporal duties, on the same reading `Relation`
    carries elsewhere and over the abstraction `LTLF_ABSTRACTION_LIMIT` states.
    """

    decided: tuple[str, ...] = ()
    unsatisfiable: tuple[str, ...] = ()
    relations: tuple[Relation, ...] = ()
    #: How many pairs of temporal duties were put to the procedure, and how many it refused for
    #: carrying more atoms than it builds an automaton for. Counted rather than inferred from
    #: `relations`, because "no pair entails another" and "no pair was decided" are different facts
    #: and the second must never render as the first.
    pairs_decided: int = 0
    pairs_refused: int = 0


@dataclass(frozen=True)
class PackAnalysis:
    """What the four questions answered, and every one skipped rather than answered."""

    pack_id: str
    satisfiable: Optional[bool]
    unsatisfiable_core: tuple[str, ...] = ()
    relations: tuple[Relation, ...] = ()
    vacuities: tuple[VacuityFinding, ...] = ()
    mutation: tuple[MutationScore, ...] = ()
    mutation_domain: str = ""
    skipped: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    #: `None` when the optional decision procedure is not installed, which is not the same fact as
    #: "it was installed and found nothing" and must not render as it.
    temporal: Optional[TemporalAnalysis] = None


class _PackScope(_Scope):
    """A signal model with no system in it: the two record atoms become uninterpreted Booleans.

    `_Scope.present` and `_Scope.contains` ask what the *declared rules* establish, which is the
    right question for a proof about a system and has no answer here — a pack is a set of formulas
    and there is no rule block to assign anything. So each `present(signal)` and each
    `contains(signal, "phrase")` becomes one Boolean constant, shared across every requirement of
    the pack, and the only relation asserted between them is the one `rulelang.contains_literal`
    itself implements: a value the record does not carry contains nothing.

    What that buys and what it costs is one thing said twice. Two properties this reports
    equivalent are equivalent under *every* interpretation of the atoms, so the finding holds for
    every system. Two it does not are not thereby distinguishable by any system: the abstraction is
    sound for the relations it reports and incomplete for the ones it does not.
    """

    def __init__(self, var_types: dict[str, str]):
        super().__init__(var_types)
        self.axioms: list[Any] = []
        self._atoms: dict[str, Any] = {}

    def _atom(self, label: str) -> Any:
        if label not in self._atoms:
            self._atoms[label] = z3.Bool(label)
        return self._atoms[label]

    def present(self, name: str) -> Any:
        return self._atom(f"{PRESENCE_CALL}({name})")

    def contains(self, signal: str, phrase: str) -> Any:
        atom = self._atom(f"{CONTAINS_CALL}({signal}, {phrase!r})")
        implication = z3.Implies(atom, self.present(signal))
        if not any(z3.eq(implication, existing) for existing in self.axioms):
            self.axioms.append(implication)
        return atom


def _state_property(req: Requirement) -> tuple[Optional[ast.Expression], str]:
    """The state property this analysis encodes for a requirement, or a reason it encodes none."""
    if req.formalism == "counterfactual":
        return None, (
            f"{req.id}: the counterfactual fragment is a property of a pair of executions, which "
            "this analysis does not encode"
        )
    if req.formalism == "undetermined":
        return None, (
            f"{req.id}: the duty rests on a predicate the law states without a sharp boundary, "
            "which no engine here settles and this two-valued encoding has no atom for. Whether it "
            "entails another duty is a question about a predicate nobody has applied"
        )
    if req.formalism == "graded":
        return None, (
            f"{req.id}: the graded fragment is read over a residuated lattice, and every question "
            "this analysis asks is a Boolean satisfiability question. Encoding a degree as one "
            "more uninterpreted Boolean would answer about a formula the pack did not write"
        )
    if req.formalism == "temporal":
        reduced = state_property_under_always(req.spec)
        if reduced is None:
            return None, (
                f"{req.id}: a temporal spec that is not `always(state property)` is not reduced "
                "to a state property for the Z3 questions above, on the same terms as "
                "engines/temporal.py — the finite-trace procedure answers it instead, where it is "
                "installed"
            )
        return parse_property(reduced), ""
    return parse_property(req.spec), ""


def _pack_scope(nodes: list[ast.Expression]) -> _PackScope:
    """One scope for a whole pack, giving every bare Boolean name the Boolean sort.

    A signal read as a bare Boolean atom is a flag and a signal compared as a magnitude is a
    number; `rulelang.validate_property` already refuses a spec that gives one name both roles, so
    reading the roles off the properties is reading a decision the pack already made.
    """
    var_types: dict[str, str] = {}
    for node in nodes:
        for name in bare_boolean_names(node):
            var_types[name] = "bool"
    return _PackScope(var_types)


def _encoded(node: ast.AST, scope: _Scope, what: str) -> Any:
    return _as_bool(_ast_to_z3(node, scope), what)


def _valid(assertions: list[Any], formula: Any, timeout_ms: int) -> Optional[bool]:
    """Whether `formula` holds everywhere the assertions admit; `None` if the solver cannot say."""
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(*assertions)
    solver.add(z3.Not(formula))
    result = solver.check()
    if result == z3.unsat:
        return True
    if result == z3.sat:
        return False
    return None


def _parents(tree: ast.AST) -> dict[int, tuple[ast.AST, str, Optional[int]]]:
    parents: dict[int, tuple[ast.AST, str, Optional[int]]] = {}
    for node in ast.walk(tree):
        for name, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        parents[id(item)] = (node, name, index)
            elif isinstance(value, ast.AST):
                parents[id(value)] = (node, name, None)
    return parents


def _subformula_positions(tree: ast.Expression) -> list[int]:
    """The walk-order positions of every subformula occurrence a replacement may target.

    An *occurrence* and not a subformula: each is one AST node, so each occurs exactly once, which
    is what makes the two-point check in `vacuous_subformulas` exact rather than an approximation.
    The walk does not descend into a signal atom's arguments, and a literal constant is not a
    subformula anything could usefully replace.
    """
    positions: list[int] = []
    skipped: set[int] = set()
    for index, node in enumerate(ast.walk(tree)):
        if id(node) in skipped or isinstance(node, (ast.Expression, ast.Constant)):
            continue
        if isinstance(node, ast.Call):
            # The callee is the operator's name and not a subformula, and encoding it would
            # declare a constant called `Implies`.
            skipped.add(id(node.func))
            if isinstance(node.func, ast.Name) and node.func.id in _SIGNAL_ATOMS:
                for argument in node.args:
                    for child in ast.walk(argument):
                        skipped.add(id(child))
        positions.append(index)
    return positions


def _replaced(tree: ast.Expression, position: int, value: bool) -> ast.AST:
    """A copy of `tree` with the node at walk-order `position` replaced by a Boolean constant."""
    clone = copy.deepcopy(tree)
    target = list(ast.walk(clone))[position]
    replacement = ast.Constant(value=value)
    parents = _parents(clone)
    parent, field_name, index = parents[id(target)]
    if index is None:
        setattr(parent, field_name, replacement)
    else:
        getattr(parent, field_name)[index] = replacement
    return ast.fix_missing_locations(clone)


def vacuous_subformulas(
    tree: ast.Expression,
    scope: _Scope,
    assertions: list[Any],
    timeout_ms: int = 5000,
) -> tuple[str, ...]:
    """The subformula occurrences any other formula could replace without changing the verdict.

    The definition is `docs/theory/04-decision-problems.md` §4.6, which is Kupferman and
    Vardi's (`[@kupferman-2003]`) restricted to the
    fragments this repository ships: a requirement is **vacuously discharged** on an evidence
    domain when some subformula of its `spec` can be replaced by *any* well-formed formula of the
    same fragment without changing the verdict.

    The check is the two-point one, and it is exact rather than a heuristic here for a reason worth
    stating. The target is one AST *occurrence*, so it occurs once, so the property is monotone or
    antitone in it; any replacement's value therefore lies between the two constants pointwise, and
    a verdict equal at both endpoints is equal throughout. `verdict` is the proof rung's own: the
    property holds at every point of the domain, or it does not.

    Only the **satisfied** side is reported, which is the same restriction the antecedent rule in
    `engines/proved.py` observes and for the same reason: a violated verdict names a witness, and a
    witness is evidence about the system whatever else in the property could have been different.
    """
    findings: list[str] = []
    nodes = list(ast.walk(tree))
    # A subformula of a replaceable subformula is replaceable too, and reporting it says nothing
    # the larger finding did not. Only the outermost occurrence is reported, and the walk is
    # breadth-first, so a reported node's descendants are still ahead of the cursor.
    reported: set[int] = set()
    parents = _parents(tree)
    for position in _subformula_positions(tree):
        if _has_reported_ancestor(nodes[position], parents, reported):
            continue
        try:
            # A subformula is a node the encoding gives a *Boolean*. Without this the walk reaches
            # the operand of a comparison, where substituting a Boolean constant produces an
            # expression neither the language nor the system has, and the two-point check answers
            # about it — a false alarm of exactly the kind that makes an analysis ignorable.
            if not z3.is_bool(_ast_to_z3(nodes[position], scope)):
                continue
            positive = _encoded(_replaced(tree, position, True), scope, "replacement")
            negative = _encoded(_replaced(tree, position, False), scope, "replacement")
        except UnsupportedConstructError:
            continue
        if _valid(assertions, positive, timeout_ms) and _valid(assertions, negative, timeout_ms):
            reported.add(id(nodes[position]))
            findings.append(ast.unparse(nodes[position]))
    return tuple(findings)


def _has_reported_ancestor(
    node: ast.AST,
    parents: dict[int, tuple[ast.AST, str, Optional[int]]],
    reported: set[int],
) -> bool:
    current = node
    while id(current) in parents:
        current = parents[id(current)][0]
        if id(current) in reported:
            return True
    return False


def _satisfiability_and_relations(
    pack: Pack, timeout_ms: int
) -> tuple[Optional[bool], tuple[str, ...], tuple[Relation, ...], list[str], list[str]]:
    """Encode every encodable requirement of a pack once, then ask the two formula questions."""
    skipped: list[str] = []
    encoded: list[tuple[str, ast.Expression]] = []
    for req in pack.requirements:
        node, reason = _state_property(req)
        if node is None:
            skipped.append(reason)
            continue
        encoded.append((req.id, node))

    scope = _pack_scope([node for _, node in encoded])
    formulas: dict[str, Any] = {}
    for req_id, node in encoded:
        try:
            formulas[req_id] = _encoded(node, scope, f"Requirement {req_id}")
        except UnsupportedConstructError as exc:
            skipped.append(f"{req_id}: {exc}")

    axioms = list(scope.axioms)
    notes: list[str] = []
    if not formulas:
        return None, (), (), skipped, notes

    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(*axioms)
    for req_id, formula in formulas.items():
        solver.assert_and_track(formula, req_id)
    outcome = solver.check()
    satisfiable: Optional[bool] = None
    core: tuple[str, ...] = ()
    if outcome == z3.sat:
        satisfiable = True
    elif outcome == z3.unsat:
        satisfiable = False
        core = tuple(sorted(str(item) for item in solver.unsat_core()))
    else:
        notes.append(
            "joint satisfiability: the solver returned unknown, so the pack is reported neither "
            "satisfiable nor unsatisfiable"
        )

    relations: list[Relation] = []
    ids = list(formulas)
    for i, left in enumerate(ids):
        for right in ids[i + 1 :]:
            forward = _valid(axioms + [formulas[left]], formulas[right], timeout_ms)
            backward = _valid(axioms + [formulas[right]], formulas[left], timeout_ms)
            if forward and backward:
                relations.append(Relation(left=left, right=right, equivalent=True))
            elif forward:
                relations.append(Relation(left=left, right=right, equivalent=False))
            elif backward:
                relations.append(Relation(left=right, right=left, equivalent=False))
    return satisfiable, core, tuple(relations), skipped, notes


def _temporal_analysis(pack: Pack) -> tuple[Optional[TemporalAnalysis], list[str], list[str]]:
    """Decide the pack's temporal duties as finite-trace formulas, or say why one was not.

    The whole fragment reaches this, not only the shapes the Z3 reduction misses: an entailment
    between the `until` duty and an `always` one is a question about both, and asking it of only
    half the fragment would answer it about a pack that is not this one. One `Abstraction` serves
    the whole pack, so the same subexpression is the same atom in every formula.
    """
    if not available():
        return None, [], [UNAVAILABLE_NOTE]

    skipped: list[str] = []
    abstraction = Abstraction()
    rendered: list[tuple[str, str]] = []
    for req in pack.requirements:
        if req.formalism != "temporal":
            continue
        try:
            rendered.append((req.id, to_ltlf(req.spec, abstraction)))
        except UnsupportedConstructError as exc:
            skipped.append(f"{req.id}: not decided as a finite-trace formula — {exc}")

    if not rendered:
        return TemporalAnalysis(), skipped, []

    decided: list[str] = []
    unsatisfiable: list[str] = []
    for req_id, formula in rendered:
        try:
            holds = satisfiable([formula], abstraction)
        except UnsupportedConstructError as exc:
            skipped.append(f"{req_id}: satisfiability not decided — {exc}")
            continue
        decided.append(req_id)
        if not holds:
            unsatisfiable.append(req_id)

    relations: list[Relation] = []
    refused = 0
    pairs_decided = 0
    for index, (left, left_formula) in enumerate(rendered):
        for right, right_formula in rendered[index + 1 :]:
            try:
                forward = entails(left_formula, right_formula, abstraction)
                backward = entails(right_formula, left_formula, abstraction)
            except UnsupportedConstructError:
                refused += 1
                continue
            pairs_decided += 1
            if forward and backward:
                relations.append(Relation(left=left, right=right, equivalent=True))
            elif forward:
                relations.append(Relation(left=left, right=right, equivalent=False))
            elif backward:
                relations.append(Relation(left=right, right=left, equivalent=False))
    return (
        TemporalAnalysis(
            decided=tuple(decided),
            unsatisfiable=tuple(unsatisfiable),
            relations=tuple(relations),
            pairs_decided=pairs_decided,
            pairs_refused=refused,
        ),
        skipped,
        [],
    )


#: The comparison swaps one mutant applies, each to one occurrence.
_COMPARISON_MUTATIONS = {
    ast.Lt: (ast.LtE, ast.Gt),
    ast.LtE: (ast.Lt, ast.Gt),
    ast.Gt: (ast.GtE, ast.Lt),
    ast.GtE: (ast.Gt, ast.Lt),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}


def mutate_rules(rules: list[str]) -> list[tuple[str, list[str]]]:
    """Every single-point mutant of a declared rule block, as (label, rules).

    Four kinds, chosen because each is a mistake a rule set can actually carry and each is visible
    to a different rung: a comparison swapped for its neighbour or its opposite (a boundary error),
    a conjunction for a disjunction (a policy widened), a number moved by one (an off-by-one
    threshold), and a recorded statement blanked (a record duty's whole subject). One occurrence is
    mutated per mutant, so a duty that notices a mutant noticed that one change.
    """
    mutants: list[tuple[str, list[str]]] = []

    def emit(rule_index: int, tree: ast.AST, label: str) -> None:
        mutated = list(rules)
        mutated[rule_index] = ast.unparse(ast.fix_missing_locations(tree))
        mutants.append((label, mutated))

    for rule_index, rule in enumerate(rules):
        try:
            original = ast.parse(rule, mode="exec")
        except SyntaxError:
            continue
        positions = list(ast.walk(original))
        for position, node in enumerate(positions):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                for replacement in _COMPARISON_MUTATIONS.get(type(node.ops[0]), ()):
                    clone = copy.deepcopy(original)
                    target = list(ast.walk(clone))[position]
                    target.ops = [replacement()]
                    emit(
                        rule_index,
                        clone,
                        f"rule {rule_index}: {ast.unparse(node)!r} -> "
                        f"{ast.unparse(target)!r}",
                    )
            elif isinstance(node, ast.BoolOp):
                clone = copy.deepcopy(original)
                target = list(ast.walk(clone))[position]
                target.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
                emit(
                    rule_index,
                    clone,
                    f"rule {rule_index}: {ast.unparse(node)!r} -> {ast.unparse(target)!r}",
                )
            elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if isinstance(node.value, bool):
                    continue
                clone = copy.deepcopy(original)
                target = list(ast.walk(clone))[position]
                target.value = node.value + 1
                emit(
                    rule_index,
                    clone,
                    f"rule {rule_index}: {node.value!r} -> {target.value!r}",
                )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
                clone = copy.deepcopy(original)
                target = list(ast.walk(clone))[position]
                target.value = ""
                emit(rule_index, clone, f"rule {rule_index}: {node.value!r} -> ''")
    return mutants


def _mutation_coverage(
    pack: Pack,
    sut: SystemUnderTest,
    system_domains: tuple[str, ...],
    system_scope: Optional[str],
) -> tuple[tuple[MutationScore, ...], str, list[str]]:
    """Re-run the pack against every mutant of the system's declared rules.

    The mutant is a `RulesAdapter` over the mutated rules and the system's own variables,
    constraints, capabilities and test inputs — never the original system with its `logic()`
    swapped, which would leave a `decide()` deciding by the unmutated rules and report the
    divergence rather than the mutation. The baseline is the same construction over the unmutated
    rules, so the comparison is like for like.
    """
    from reasonsmith.adapters.rules import RulesAdapter

    notes: list[str] = []
    logic_func = getattr(sut, "logic", None)
    logic_data = logic_func() if callable(logic_func) else None
    if not isinstance(logic_data, dict) or not logic_data.get("rules"):
        return (), "", [
            "mutation coverage: the system exposes no rule block through sut.logic(), so there is "
            "nothing to mutate and no duty gets a score"
        ]

    rules = list(logic_data["rules"])
    variables = dict(logic_data.get("variables") or {})
    constraints = list(logic_data.get("constraints") or [])
    capabilities = set(sut.capabilities())
    inputs = [dict(record) for record in sut.decisions()] or None
    # The mutant is judged in the system's own declared class and domains, or the run's, because
    # both gates decide whether a duty is reached at all and a mutant reached by fewer duties than
    # the baseline would score every one of them as undetected.
    domains = system_domains or tuple(getattr(sut, "system_domains", ()) or ())
    scope = system_scope or getattr(sut, "system_scope", getattr(sut, "declared_scope", None))

    def build(mutated: list[str]) -> Optional[RulesAdapter]:
        try:
            adapter = RulesAdapter(
                rules=mutated,
                variables=variables,
                constraints=constraints,
                declared_capabilities=capabilities,
                test_inputs=inputs,
                frontier_ai_status=getattr(sut, "frontier_ai_status", None),
            )
        except (ValueError, TypeError):
            return None
        adapter.system_domains = domains
        adapter.system_scope = scope
        return adapter

    baseline_sut = build(rules)
    if baseline_sut is None:
        return (), "", [
            "mutation coverage: the system's own rules do not rebuild as a RulesAdapter, so no "
            "baseline could be established"
        ]
    baseline = _verdict_map(pack, baseline_sut, scope, domains)

    detected: dict[str, int] = {req.id: 0 for req in pack.requirements}
    ran = 0
    for label, mutated in mutate_rules(rules):
        mutant = build(mutated)
        if mutant is None:
            notes.append(f"mutation coverage: mutant not built — {label}")
            continue
        try:
            verdicts = _verdict_map(pack, mutant, scope, domains)
        except Exception as exc:  # a mutant may be undecidable rather than merely wrong
            notes.append(f"mutation coverage: mutant raised and was not counted — {label}: {exc}")
            continue
        ran += 1
        for req_id, verdict in verdicts.items():
            if verdict != baseline.get(req_id):
                detected[req_id] += 1

    scores = tuple(
        MutationScore(requirement_id=req.id, detected=detected[req.id], mutants=ran)
        for req in pack.requirements
    )
    domain = f"{ran} single-point mutant(s) of the system's {len(rules)} declared rule(s)"
    return scores, domain, notes


def _verdict_map(
    pack: Pack,
    sut: SystemUnderTest,
    system_scope: Optional[str],
    system_domains: tuple[str, ...],
) -> dict[str, tuple[str, Optional[str]]]:
    report = check_conformance(
        sut, pack, system_scope=system_scope, system_domains=system_domains or None
    )
    return {
        result.requirement_id: (
            result.verdict.value,
            result.strength.value if result.strength is not None else None,
        )
        for result in report.results
    }


def analyse_pack(
    pack: Pack,
    sut: Optional[SystemUnderTest] = None,
    *,
    system_scope: Optional[str] = None,
    system_domains: tuple[str, ...] = (),
    timeout_ms: int = 5000,
) -> PackAnalysis:
    """Answer the four questions of the module docstring about `pack`, and name what was skipped.

    Without a system the answers are about the formulas alone: satisfiability and the entailment
    relations hold under every interpretation of the record atoms, and vacuity is asked over the
    unconstrained signal model, where it reports a subformula no evidence could ever make matter.
    With a system that exposes `logic()`, vacuity is asked again over the domain the proof rung
    itself quantifies over — the inputs the declared logic and constraints admit — which is where
    it coincides with `report.not_evaluated_for_unreachable_trigger`, and the mutation coverage
    runs.
    """
    jointly_satisfiable, core, relations, skipped, notes = _satisfiability_and_relations(
        pack, timeout_ms
    )
    temporal, temporal_skipped, temporal_notes = _temporal_analysis(pack)
    skipped.extend(temporal_skipped)
    notes.extend(temporal_notes)

    vacuities: list[VacuityFinding] = []
    domain_label = "every assignment to the signals the properties read"
    logic_scope: Optional[_Scope] = None
    logic_assertions: list[Any] = []
    declared_computes: Any = None
    if sut is not None:
        logic_func = getattr(sut, "logic", None)
        logic_data = logic_func() if callable(logic_func) else None
        if logic_data is not None:
            try:
                logic_scope, logic_solver, _, declared_computes = encode_logic_domain(
                    logic_data, timeout_ms
                )
                logic_assertions = list(logic_solver.assertions())
                domain_label = "the inputs the system's declared logic and constraints admit"
            except (UnsupportedConstructError, SyntaxError) as exc:
                notes.append(f"vacuity: the system's declared logic could not be encoded: {exc}")

    for req in pack.requirements:
        node, reason = _state_property(req)
        if node is None:
            continue
        if logic_scope is not None:
            scope: _Scope = logic_scope
            assertions = logic_assertions
        else:
            scope = _pack_scope([node])
            assertions = list(scope.axioms)
        try:
            # The proof rung's own refusal, asked here because the vacuity question inherits it:
            # a property naming something the system has no notion of would be answered from a
            # constant this encoding invented, whichever question was put to it.
            if declared_computes is not None and logic_scope is not None:
                _check_declared_directions(node, logic_scope, declared_computes)
            found = vacuous_subformulas(node, scope, assertions, timeout_ms)
        except UnsupportedConstructError as exc:
            skipped.append(f"{req.id}: vacuity not asked — {exc}")
            continue
        except z3.Z3Exception as exc:
            # A sort the property and the system disagree about. The engine answers such a duty
            # not evaluated; this says so rather than reporting a finding about the mismatch.
            skipped.append(f"{req.id}: vacuity not asked — the encoding refused it: {exc}")
            continue
        for subformula in found:
            vacuities.append(
                VacuityFinding(
                    requirement_id=req.id, subformula=subformula, domain=domain_label
                )
            )

    mutation: tuple[MutationScore, ...] = ()
    mutation_domain = ""
    if sut is not None:
        mutation, mutation_domain, mutation_notes = _mutation_coverage(
            pack, sut, system_domains, system_scope
        )
        notes.extend(mutation_notes)
    else:
        notes.append(
            "mutation coverage: no system was given, so no duty gets a score. "
            + MUTATION_LIMIT
        )

    return PackAnalysis(
        pack_id=pack.id,
        satisfiable=jointly_satisfiable,
        temporal=temporal,
        unsatisfiable_core=core,
        relations=relations,
        vacuities=tuple(vacuities),
        mutation=mutation,
        mutation_domain=mutation_domain,
        skipped=tuple(skipped),
        notes=tuple(notes),
    )


def render_analysis(analysis: PackAnalysis) -> str:
    """The one-line-per-fact rendering `validate-pack --analyse` prints."""
    lines = [f"analysis: {analysis.pack_id}"]

    if analysis.satisfiable is None:
        lines.append("  satisfiability: not decided")
    elif analysis.satisfiable:
        lines.append(
            "  satisfiability: the encodable requirements are jointly satisfiable — some record "
            "discharges all of them at once"
        )
    else:
        lines.append(
            "  satisfiability: NOT jointly satisfiable. No record discharges all of them at once, "
            "so at least one system will be reported violated for a reason that is this pack's"
        )
        lines.append(f"    core: {', '.join(analysis.unsatisfiable_core) or 'not reported'}")

    if analysis.relations:
        for relation in analysis.relations:
            if relation.equivalent:
                lines.append(
                    f"  equivalent: {relation.left} <=> {relation.right} — no system can satisfy "
                    "one and violate the other"
                )
            else:
                lines.append(
                    f"  subsumes: {relation.left} => {relation.right} — a system satisfying the "
                    "first satisfies the second"
                )
    else:
        lines.append("  entailment: no requirement entails another")

    if analysis.temporal is not None and analysis.temporal.decided:
        temporal = analysis.temporal
        if temporal.unsatisfiable:
            lines.append(
                f"  temporal: {len(temporal.decided)} temporal dut(ies) decided as finite-trace "
                f"formulas, of which {len(temporal.unsatisfiable)} NOT satisfiable"
            )
            for req_id in temporal.unsatisfiable:
                lines.append(
                    f"    NOT satisfiable: {req_id} — no non-empty finite trace discharges it, so "
                    "every system will be reported violated on it for a reason that is this pack's"
                )
        else:
            lines.append(
                f"  temporal: {len(temporal.decided)} temporal dut(ies) decided as finite-trace "
                "formulas, each satisfiable by some non-empty finite trace"
            )
        for relation in temporal.relations:
            verb = "<=>" if relation.equivalent else "=>"
            lines.append(f"  temporal entailment: {relation.left} {verb} {relation.right}")
        if not temporal.relations and temporal.pairs_decided:
            lines.append("  temporal entailment: no temporal duty entails another")
        if temporal.pairs_refused:
            total = temporal.pairs_decided + temporal.pairs_refused
            lines.append(
                f"  temporal entailment: {temporal.pairs_refused} of {total} pair(s) not decided "
                "either way — together they carry more propositional atoms than the installed "
                "decision procedure builds an automaton for in bounded time "
                "(reasonsmith.ltlf.ATOM_BUDGET)"
            )
        lines.append(f"  {LTLF_ABSTRACTION_LIMIT}")

    if analysis.vacuities:
        for finding in analysis.vacuities:
            lines.append(
                f"  vacuous: {finding.requirement_id} is discharged with {finding.subformula!r} "
                f"replaceable by any formula, over {finding.domain}"
            )
    else:
        lines.append("  vacuity: no requirement is vacuously discharged on this evidence domain")

    if analysis.mutation:
        lines.append(f"  mutation domain: {analysis.mutation_domain}")
        for score in analysis.mutation:
            lines.append(
                f"    {score.requirement_id}: {score.detected}/{score.mutants} "
                f"({score.score:.2f})"
            )
        blind = [s.requirement_id for s in analysis.mutation if s.detected == 0]
        if blind:
            lines.append(
                "    no discriminating power against these mutants: " + ", ".join(blind)
            )
        lines.append(f"  {MUTATION_LIMIT}")

    for reason in analysis.skipped:
        lines.append(f"  skipped: {reason}")
    for note in analysis.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)
