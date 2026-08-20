"""A reason trace as one inference artefact — the second family, on the rung below.

What this module is for:
  The families of the paper's own taxonomy are a ground program, a knowledge graph, a reason trace,
  an extracted rule set and a decision tree. `artifacts/ground_program.py` was the only one shipped,
  and the reason it was the only one is written down in `docs/semantics.md` §3: a reason set the
  system *recounted* is not a set enumerated from a model encoding, a certificate over one claims
  strictly less, and the strength lattice could not say so. It can now — `Strength.RECOUNTED` — so
  this family is an adapter and no longer a decision about the lattice.

  A reason trace is what a system says about its own inference behind one decision: a set of named
  reasons, each a set of facts, with the weight the system reports for each. Two things make it
  usable evidence rather than a self-declared flag:

    - it is not the verdict. `engine_value()` re-runs the *system*, with the named facts suppressed,
      through a caller-supplied `answer` — so the probe compares what the system says it used
      against what its answer actually depends on. A reason the trace recounts that no deletion
      moves is a rationale item the decision did not turn on.
    - it is not read as an enumeration. `reasons_are_exact` is False, which is what caps every
      verdict measured from one at `recounted`: a rationale can be complete or can omit a reason the
      inference used, and no probe *of the rationale* can tell the two apart.

  That is the faithfulness question as the literature poses it — a self-explanation may be plausible
  and unfaithful (A. Jacovi, Y. Goldberg, ACL 2020, 4198–4205 — `[@jacovi-2020]`; M. Turpin,
  J. Michael, E. Perez, S. R. Bowman, NeurIPS 2023 — `[@turpin-2023]`) — measured the way that
  literature measures it, by erasure (J. DeYoung et al., *ERASER*, ACL 2020, 4443–4458 —
  `[@deyoung-2020]`). `docs/semantics.md` §3 is the contract.

What a reader must not break:
  - **`answer` re-runs the system and is never read off the trace.** A system that cannot be re-run
    with a fact suppressed cannot be certified here, and that limit is the honest one: without a
    second, independent measurement, `exact_value` and `engine_value` are the same self-report and
    every reason comes back live by construction.
    Why this matters: the cheap version of this family would score the rationale against itself and
    report a PASS for every system that writes one, which is the self-declared flag
    `docs/semantics.md` §3 refuses in every other place.
  - **`reasons_are_exact` stays False.** It is not a property of any particular trace: it is what
    this *family* is, and a subclass that flipped it would report at the ground program's rung on a
    rationale nothing enumerated.
    Why this matters: it is the whole of what separates the two shipped families, and the rung it
    selects is refused rather than trusted (`report.RequirementResult._validate_reason_set`).
  - **`without` suppresses a fact and re-scores the same recounted reasons.** It never re-reads the
    trace and never asks the system for a new rationale.
    Why this matters: the ground-program family's own rule, one concept over. Asking a language
    model to explain itself again under the perturbation would compare two answers to two questions,
    and the second rationale is not evidence about the first decision.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from reasonsmith.artifacts import default_label
from reasonsmith.spec import normalize_claimed_semantics

__all__ = ["ReasonTraceArtifact"]


class ReasonTraceArtifact:
    """The reasons a system recounts for one decision, tested against the answer it actually gives.

    `reasons` maps a reason's name — a reason code, a rationale line — to the facts the system says
    that reason rests on. `answer` is the system re-run: given the set of facts to suppress, it
    returns the answer the system gives, and `answer(frozenset())` is the answer the trace is about.

    `weights` is the weight the system reports for each reason, **on the scale of `answer`**. Where
    it reports none the unperturbed answer is split equally, which is the reading that makes the
    trace's side and the system's side commensurable: a rationale that names n reasons and no
    weights has said the answer rests on them and said nothing about how much each carries. The
    split is not a measurement and nothing here reports it as one — it decides only the order the
    certificate lists reasons in, and how large a drop each suppression is expected to cause.

    `monotone` is the declaration every artefact owes (`artifacts.InferenceArtifact`), with no
    default here for the reason the ground-program family has none: a decoder that consults a policy
    after generating a rationale is exactly the retracting engine the declaration exists to catch.
    An optional `decision_threshold` is carried when supplied, but this family still cannot ground
    a semantics-agreement duty because its exact side is a recounted rationale.
    """

    #: See the module docstring. Not a per-instance choice.
    reasons_are_exact = False

    def __init__(
        self,
        query: Any,
        reasons: Mapping[str, frozenset],
        answer: Callable[[frozenset], float],
        *,
        engine_name: str,
        claimed_semantics: str,
        monotone: bool | None = None,
        weights: Mapping[str, float] | None = None,
        recounted_by: str = "the system's own reason trace",
        _suppressed: frozenset = frozenset(),
        _baseline: float | None = None,
        decision_threshold: float | None = None,
    ):
        self.query = query
        self.engine_name = engine_name
        self.claimed_semantics = normalize_claimed_semantics(claimed_semantics)
        self.monotone = monotone
        self.recounted_by = recounted_by
        self._reasons = {name: frozenset(facts) for name, facts in reasons.items()}
        self._weights = dict(weights or {})
        self._answer = answer
        self.decision_threshold = decision_threshold
        self._suppressed = _suppressed
        #: The unperturbed answer, read once and carried into every perturbed copy: the equal split
        #: below must be a split of the answer this trace is about, not of the answer under whatever
        #: facts the probe has switched off by then.
        self._baseline = _baseline
        #: A reason trace names its reasons, so two reasons over the same facts would be one reason
        #: to every probe and two to the reader. Refused at construction rather than measured.
        by_facts: dict[frozenset, str] = {}
        for name, facts in self._reasons.items():
            if facts in by_facts:
                raise ValueError(
                    f"the reason trace recounts {name!r} and {by_facts[facts]!r} over the same "
                    "facts; a reason is identified by its facts here, so two of them cannot be "
                    "told apart by any probe and only one would be reported"
                )
            by_facts[facts] = name

    #: This bound is not a proof depth: nothing was enumerated. Stated as None so a reader of a
    #: certificate is not offered a number that would read as one.
    exact_depth = None

    #: And for the same reason this family computes no semantics reference. `exact_value()` below
    #: is the weight the *system* recounted, so the difference between it and the system's answer
    #: says how faithful the rationale is and nothing about which semantics the inference is.
    #: Stated rather than left absent: silence here already means None, and a family this close to
    #: the one that does compute a reference should say so out loud.
    exact_semantics = None

    @property
    def exact_inference(self) -> str:
        return (
            f"no enumeration — the reasons are recounted by {self.recounted_by}, and each is "
            "tested by suppressing its facts and re-running the system"
        )

    def reasons(self) -> tuple[frozenset, ...]:
        return tuple(self._reasons.values())

    def label(self, reason: frozenset) -> str:
        for name, facts in self._reasons.items():
            if facts == reason:
                return name
        return default_label(reason)

    def score(self, reason: frozenset) -> float:
        weight = self._weights.get(self.label(reason))
        if weight is not None:
            return float(weight)
        if self._baseline is None:
            self._baseline = float(self._answer(frozenset()))
        return self._baseline / len(self._reasons)

    def exact_value(self) -> float:
        """What the *trace* says the answer rests on: the weight of every reason still standing.

        This is the recounted side of the comparison, and calling it exact would be the overclaim
        this family's rung exists to refuse. It is exact about the rationale and about nothing else.
        """
        return sum(
            self.score(facts)
            for facts in self._reasons.values()
            if not (facts & self._suppressed)
        )

    def engine_value(self) -> float:
        """The system's own answer, re-run with the suppressed facts withheld."""
        return float(self._answer(self._suppressed))

    def without(self, fact: Any) -> ReasonTraceArtifact:
        return ReasonTraceArtifact(
            self.query,
            self._reasons,
            self._answer,
            engine_name=self.engine_name,
            claimed_semantics=self.claimed_semantics,
            monotone=self.monotone,
            weights=self._weights,
            recounted_by=self.recounted_by,
            _suppressed=self._suppressed | {fact},
            _baseline=self._baseline,
            decision_threshold=self.decision_threshold,
        )
