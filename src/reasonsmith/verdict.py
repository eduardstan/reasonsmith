"""The evidence strength lattice, the evidence basis, and the verdict vocabulary for reasonsmith.

What this module is for:
  Defines the formal evidence strength lattice
  (`unattainable < observed < recounted < probed < proved`), the
  evidence basis beside it (`EvidenceBasis`), and the verdict vocabulary (`satisfied`, `violated`,
  `inconclusive`, `not_applicable`) for compliance checking. Compliance claims carry a verdict
  (whether a property holds), a strength (how deeply the system exposed itself for verification)
  and a basis (what kind of thing the evidence is about).

  Strengths form a strict total order (the strength lattice):
    unattainable — The system cannot discharge the requirement as built (missing signals).
    observed     — The property holds over passive decision traces (monitors / record checks).
    recounted    — The property holds under active perturbation of a reason set the *system*
                   recounted, rather than one enumerated exactly from a model encoding.
    probed       — The property holds under active perturbation/replay.
    proved       — The property holds for all inputs via formal reasoning / solver proof.

  Verdicts record whether a property is met:
    satisfied      — Evidence proves or demonstrates the requirement holds.
    violated       — Evidence demonstrates a counterexample or breach.
    inconclusive   — Evidence is insufficient, incomplete, or unattainable.
    not_applicable — The requirement's scope does not reach the system, so it was never checked.

  Lineage & Section 6.3 Scope Statements:
    The strength lattice is the operational form of Section 6.3's scope statement ("Governance,
    Monitoring, and What to Record", Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:24 —
    `[@stan-2026]`).
    Section 6.3 asks whether an explanation "approximates or guarantees" behavior — which is
    precisely the observed / proved distinction, with probed between them and unattainable as
    the case the paper does not name: a system that cannot produce the required record at all.

What a reader must not break:
  - Do not alter the strict total order of the strength lattice
    (`UNATTAINABLE < OBSERVED < RECOUNTED < PROBED < PROVED`).
    Why this matters: Order guarantees that weaker passive evidence can never masquerade as
    active probing or formal proof.
  - `RECOUNTED` sits *below* `PROBED` and never beside it. Both rungs run the same deletion probe;
    they differ in where the reason set came from, and a set the system recounted is a claim
    nothing here can check as hard as an enumeration from a model encoding.
    Why this matters: this is the whole reason the member exists. `docs/semantics.md` §3 (*The
    inference artefact*) gated the second artefact family on the lattice being able to say it, and
    `report.RequirementResult._validate_reason_set` is where saying it became refusing it.
  - `EvidenceBasis` is a **classification and never a rank**: its members are deliberately not
    ordered, and comparing two of them raises rather than answering. The chain above ranks how far
    a claim about one kind of object was pushed; the basis says which kind of object, and the two
    are different questions.
    Why this matters: a reader handed `artifact` beside `probed` in an ordered list would read the
    basis as a fifth rung. `docs/semantics.md` §10 is the contract.
  - `BASIS_RUNGS` is the rungs each basis admits, and it is derived from what the engines can
    actually reach rather than asserted. Widen a row only when an engine for that rung exists.
    Why this matters: `RequirementResult` refuses a strength its basis does not admit, so a row
    widened ahead of an engine turns a structural refusal into a comment.
  - `RequirementResult` refuses to construct a result claiming more than it has (including
    `strength=None` for "no engine here evaluated this", which is deliberately not a strength on
    the lattice).
    Why this matters: Prevents un-evaluated or un-measured checks from being counted as satisfied
    or silently assigned a strength tier.
  - Nothing in this module asserts legal compliance or guarantees correctness beyond the formal
    bounds of the evidence provided.
    Why this matters: Technical checks measure evidence records against specifications, not legal
    counsel or guarantees.
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering
from typing import Iterable


@total_ordering
class Strength(Enum):
    """Evidence strength in the reasonsmith lattice."""

    UNATTAINABLE = "unattainable"
    OBSERVED = "observed"
    RECOUNTED = "recounted"
    PROBED = "probed"
    PROVED = "proved"

    @property
    def rank(self) -> int:
        ranks = {
            "unattainable": 0,
            "observed": 1,
            "recounted": 2,
            "probed": 3,
            "proved": 4,
        }
        return ranks[self.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Strength):
            return NotImplemented
        return self.rank < other.rank

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: str | Strength) -> Strength:
        if isinstance(value, cls):
            return value
        val_lower = str(value).strip().lower()
        for member in cls:
            if member.value == val_lower:
                return member
        raise ValueError(f"Unknown strength {value!r}; valid: {[m.value for m in cls]}")


class EvidenceBasis(Enum):
    """What kind of thing a duty's evidence is about — the second coordinate beside `Strength`.

    The strength lattice ranks *how far* a claim was pushed. It cannot rank *what the claim was
    about*, and three shipped duties are about something other than the system's own executions.
    Each of the three is a known class of specification with its own literature, and each is why
    that duty's ladder is the shape it is:

      behavioural — a property of the system's executions, one at a time: a *trace property* in the
        Alpern–Schneider sense (B. Alpern, F. B. Schneider, *Defining Liveness*, Information
        Processing Letters 21(4):181–185, 1985 — `[@alpern-1985]`). Every `record`, `logical` and
        `temporal` duty is one, and all four rungs are reachable: a trace observes one execution, a
        replay searches more of them, a solver quantifies over all the declared constraints admit.
      relational — a property of a *pair* of executions: a **2-safety property** (T. Terauchi,
        A. Aiken, *Secure Information Flow as a Safety Problem*, SAS 2005, LNCS 3672, 352–367 —
        `[@terauchi-2005]`) and so a hyperproperty rather than a trace property (M. R. Clarkson,
        F. B. Schneider, *Hyperproperties*, Journal of Computer Security 18(6):1157–1210, 2010 —
        `[@clarkson-2010]`). Self-composition is
        the proof method (G. Barthe, P. R. D'Argenio, T. Rezk, *Secure Information Flow by
        Self-Composition*, CSFW 2004, 100–114 — `[@barthe-2004]`) and `counterfactually_invariant`
        is the instance
        (M. J. Kusner, J. R. Loftus, C. Russell, R. Silva, *Counterfactual Fairness*, NeurIPS 2017,
        4066–4076 — `[@kusner-2017]`). **No trace rung exists**, and that is the literature's point
        rather than this
        tool's shortfall: a hyperproperty is not a property of any single execution, so no length
        of decision log holds a witness for one.
      artifact — evidence about the *inference behind* a decision rather than about what the system
        decided: the reasons the decision's own inference used, enumerated exactly from an
        inference artefact and each switched off in turn. This is the abductive-explanation reading
        (A. Ignatiev, N. Narodytska, J. Marques-Silva, *Abduction-Based Explanations for Machine
        Learning Models*, AAAI 2019, 1511–1519 — `[@ignatiev-2019]`; see
        `docs/theory/07-explanation.md` for
        the rest),
        and the model-precise rather than behaviour-sampled side of the distinction formal XAI
        draws (J. Marques-Silva, A. Ignatiev, *Delivering Trustworthy AI through Formal XAI*,
        AAAI 2022, 12342–12350 — `[@marques-silva-2022]`). No trace holds the artefact, and the
        enumeration is exact only on the one ground program and base interpretation it was run
        over, so it is bounded evidence and never a proof: `observed` is off this row and `proved`
        with it. The row has **two** rungs, and the lower one is `recounted` — a reason set the
        system *recounted* rather than one enumerated from a model encoding, tested by the same
        deletion probe. That is the faithfulness question of a self-reported rationale
        (A. Jacovi, Y. Goldberg, *Towards Faithfully Interpretable NLP Systems: How Should We
        Define and Evaluate Faithfulness?*, ACL 2020, 4198–4205 — `[@jacovi-2020]`), measured the
        way that literature
        measures it, by erasure (J. DeYoung, S. Jain, N. F. Rajani, E. Lehman, C. Xiong, R. Socher,
        B. C. Wallace, *ERASER: A Benchmark to Evaluate Rationalized NLP Models*, ACL 2020,
        4443–4458 — `[@deyoung-2020]`), on evidence a self-report can fail to be
        (M. Turpin, J. Michael, E. Perez,
        S. R. Bowman, *Language Models Don't Always Say What They Think: Unfaithful Explanations in
        Chain-of-Thought Prompting*, NeurIPS 2023 — `[@turpin-2023]`). Same object, less deeply —
        the claim is still
        about the inference behind the decision — which is what makes it a rung here and not a
        fifth basis.
      assessment — evidence about how an open-textured predicate applies, supplied by a named
        authority rather than measured from the system: a truth degree over a residuated lattice
        (P. Hájek, *Metamathematics of Fuzzy Logic*, Kluwer, 1998 — `[@hajek-1998]`), or the naming
        of the
        institution that would settle a predicate no computation does. **No rung at all**, because
        the lattice ranks methods of interrogating a system and no system was interrogated. A
        degree of truth is not a degree of belief and neither is a fraction of a proof
        (D. Dubois, H. Prade, *Possibility Theory, Probability Theory and Multiple-Valued Logics:
        A Clarification*, Annals of Mathematics and Artificial Intelligence 32:35–66, 2001 —
        `[@dubois-2001]`).
      statistical — evidence about a fixed-group sample and a declared sampling model, estimand and
        uncertainty procedure. The first wave is measurement-only: the payload carries counts and
        simultaneous Clopper–Pearson intervals beside `strength=None` and `inconclusive`, so no
        statistical measurement is a strength rung or a conformance verdict.

    The members carry **no order**. `<` and its siblings raise rather than answering, so a basis
    cannot be sorted into a ladder, compared against a strength, or rendered as a rung.
    """

    BEHAVIOURAL = "behavioural"
    RELATIONAL = "relational"
    ARTIFACT = "artifact"
    ASSESSMENT = "assessment"
    STATISTICAL = "statistical"

    @property
    def rungs(self) -> tuple[Strength, ...]:
        """The rungs of the strength lattice this basis admits, weakest first."""
        return BASIS_RUNGS[self]

    def admits(self, strength: Strength | str) -> bool:
        """Whether a result on this basis may carry `strength`."""
        return Strength.parse(strength) in self.rungs

    def __str__(self) -> str:
        return str(self.value)

    def _refuse_order(self, other: object) -> bool:
        raise TypeError(
            f"{type(self).__name__} members are not ordered: {self.value!r} and {other!r} name "
            "different kinds of evidence, not different amounts of it. The strength lattice ranks "
            "how far a claim was pushed; the basis says what the claim was about. See "
            "docs/semantics.md §10."
        )

    __lt__ = _refuse_order
    __le__ = _refuse_order
    __gt__ = _refuse_order
    __ge__ = _refuse_order

    @classmethod
    def parse(cls, value: str | EvidenceBasis) -> EvidenceBasis:
        if isinstance(value, cls):
            return value
        val_lower = str(value).strip().lower()
        for member in cls:
            if member.value == val_lower:
                return member
        raise ValueError(f"Unknown evidence basis {value!r}; valid: {[m.value for m in cls]}")


#: Which rungs each basis admits, weakest first. Every row is read off what an engine can actually
#: reach, and `RequirementResult.__post_init__` refuses a result outside its row — so this table is
#: the structural form of three sentences that were previously only prose.
#:
#: `unattainable` is in every row because it is not an engine's answer at all: the capability gate
#: is a set difference over declared signal names, identical for every duty, and it runs before any
#: basis is consulted. `observed` is absent from `relational` because a decision record holds one
#: execution and a 2-safety property needs two; `proved` is absent from `artifact` and every rung
#: from `assessment` for the reasons `EvidenceBasis` gives. `recounted` is on the `artifact` row
#: alone: it is the rung a reason set the system recounted reaches, and no other basis has a
#: second-hand reading of its own evidence to rank.
BASIS_RUNGS: dict[EvidenceBasis, tuple[Strength, ...]] = {
    EvidenceBasis.BEHAVIOURAL: (
        Strength.UNATTAINABLE,
        Strength.OBSERVED,
        Strength.PROBED,
        Strength.PROVED,
    ),
    EvidenceBasis.RELATIONAL: (Strength.UNATTAINABLE, Strength.PROBED, Strength.PROVED),
    EvidenceBasis.ARTIFACT: (Strength.UNATTAINABLE, Strength.RECOUNTED, Strength.PROBED),
    EvidenceBasis.ASSESSMENT: (Strength.UNATTAINABLE,),
    # Statistical evidence is a measurement in the first wave, not a strength rung.  The
    # capability-gate state remains the sole admissible lattice member; a computed measurement
    # carries ``strength=None`` and ``verdict=inconclusive``.
    EvidenceBasis.STATISTICAL: (Strength.UNATTAINABLE,),
}


class Verdict(Enum):
    """Verdict on whether a requirement is satisfied.

    NOT_APPLICABLE is a statement about the duty's reach, not about the system: the
    requirement is limited to a regulatory class the system is not declared to be in, so it
    was never checked. It is deliberately distinct from INCONCLUSIVE, which says a duty that
    does reach the system was not resolved.
    """

    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: str | Verdict) -> Verdict:
        if isinstance(value, cls):
            return value
        val_lower = str(value).strip().lower().replace(" ", "_")
        for member in cls:
            if member.value == val_lower:
                return member
        raise ValueError(f"Unknown verdict {value!r}; valid: {[m.value for m in cls]}")


def combine_verdicts(verdicts: Iterable[Verdict | str]) -> Verdict:
    """Combine multiple verdicts using worst-case propagation.

    Rules:
      1. If any verdict is VIOLATED, the combined result is VIOLATED.
      2. Else if any verdict is INCONCLUSIVE, the combined result is INCONCLUSIVE.
      3. Else if every verdict is NOT_APPLICABLE, the combined result is NOT_APPLICABLE.
      4. Else all remaining verdicts are SATISFIED or NOT_APPLICABLE, and the combined
         result is SATISFIED.
      5. An empty collection returns INCONCLUSIVE.

    Rule 3 stops one out-of-scope sub-property turning the whole into a claim that nothing
    applies; rule 4 lets the sub-properties that *were* checked carry the verdict.

    Rule 5 is deliberately *not* vacuous truth. Logically an empty conjunction is
    true, but a conformance verdict is a claim about evidence, and having checked
    nothing is not evidence that a requirement holds. Returning SATISFIED here
    would let a run that evaluated no sub-property report as compliant, which is
    the one failure mode this tool must never have.
    """
    v_list = [Verdict.parse(v) for v in verdicts]
    if not v_list:
        return Verdict.INCONCLUSIVE
    if any(v == Verdict.VIOLATED for v in v_list):
        return Verdict.VIOLATED
    if any(v == Verdict.INCONCLUSIVE for v in v_list):
        return Verdict.INCONCLUSIVE
    if all(v == Verdict.NOT_APPLICABLE for v in v_list):
        return Verdict.NOT_APPLICABLE
    return Verdict.SATISFIED


def min_strength(strengths: Iterable[Strength | str]) -> Strength:
    """Return the weakest strength in a collection (weakest-link principle).

    An empty collection raises ValueError.
    """
    s_list = [Strength.parse(s) for s in strengths]
    if not s_list:
        raise ValueError("Cannot compute min_strength of an empty collection")
    return min(s_list)


def max_strength(strengths: Iterable[Strength | str]) -> Strength:
    """Return the strongest strength in a collection.

    An empty collection raises ValueError.
    """
    s_list = [Strength.parse(s) for s in strengths]
    if not s_list:
        raise ValueError("Cannot compute max_strength of an empty collection")
    return max(s_list)
