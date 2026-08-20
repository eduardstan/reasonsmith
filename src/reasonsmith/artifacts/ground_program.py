"""The nesyarena ground program as one inference artefact.

What this module is for:
  One family satisfying `artifacts.InferenceArtifact`, and the only one shipped: a nesyarena
  `GroundProgram` with a base interpretation, a query and the engine that answered it. Everything
  nesyarena supplies — the ground-program IR, bounded proof enumeration, the exact WMC oracle and
  the adapter protocol `infer` belongs to — is *depended on* here and reimplemented nowhere. This
  module is the whole of reasonsmith's coupling to it on the certificate path: `certificate.py`
  names no nesyarena type, and neither does the protocol this class satisfies.

What a reader must not break:
  - **`without` and `at` re-score the reasons the base enumeration found, and never re-enumerate.**
    The perturbed artefact carries its parent's reason set.
    Why this matters: the probe compares exact inference's answer before and after one fact is
    switched off. Enumerating again would compare two answers to two questions, and a family whose
    enumeration is sensitive to a zeroed fact would report drops that are an artefact of the
    instrument.
  - **The monotonicity declaration is about the *engine*, not about the program or the oracle.**
    A definite Horn program has no defeater mechanism and the WMC oracle is monotone in every fact
    by construction, so neither can supply the answer: the defeat lives where it lives in a
    deployment, in the engine that runs after the rules fire. It is therefore a required argument
    with no default, and `certify(...)` passes None through to be refused rather than guessing.
    Why this matters: reading monotonicity off the representation would certify the defeasible
    system of `docs/semantics.md` §3 as monotone on the strength of the positive program its
    exception is not written in.
"""

from __future__ import annotations

from typing import Any

from nesyarena.ir import Atom, GroundProgram
from nesyarena.oracle import wmc
from nesyarena.suts import proof_score

from reasonsmith.artifacts import default_label
from reasonsmith.spec import normalize_claimed_semantics

__all__ = ["GroundProgramArtifact"]


class GroundProgramArtifact:
    """The inference behind one decision, as a ground program the exact oracle can enumerate.

    `program`, `base` and `query` are exactly what the system's own adapter and the oracle both
    consume — that shared input is the invariant nesyarena's adapter protocol exists to hold.
    `exact_depth` bounds proof enumeration; `labels` maps a reason's fact set to a human name, such
    as a reason code; `decision_threshold` is an optional finite threshold exposed for the
    semantics-agreement margin measurement and is not inferred here.
    """

    #: This family enumerates its reasons, so it reaches `Strength.PROBED`. Bounded by `exact_depth`
    #: and exact within that bound, which is a different claim from a set the system recounted —
    #: `artifacts.reason_trace` is the family on the rung below, and `artifacts.RECOUNTED_REASONS`
    #: is what separates them.
    reasons_are_exact = True

    #: And `exact_value()` below is exact weighted model counting over that enumeration, which is
    #: the distribution semantics of the ground program. Named from `spec.CLAIMED_SEMANTICS` so a
    #: duty can hold the adapter's claim against it rather than against a string nobody can compare.
    exact_semantics = "distribution semantics"

    def __init__(
        self,
        program: GroundProgram,
        base: dict,
        query: Atom,
        adapter: Any,
        exact_depth: int,
        labels: dict | None = None,
        monotone: bool | None = None,
        _reasons: tuple[frozenset, ...] | None = None,
        *,
        decision_threshold: float | None = None,
    ):
        self.program = program
        self.base = base
        self.query = query
        self.adapter = adapter
        self.exact_depth = exact_depth
        self.labels = labels or {}
        self.monotone = monotone
        # Optional and intentionally not inferred from the query or the record. The protocol
        # reader validates it only when a semantics-agreement duty consumes the field.
        self.decision_threshold = decision_threshold
        self._reasons = (
            tuple(program.proof_supports(query, exact_depth)) if _reasons is None else _reasons
        )

    @property
    def engine_name(self) -> str:
        return self.adapter.name

    @property
    def claimed_semantics(self) -> str:
        return normalize_claimed_semantics(self.adapter.claimed_semantics)

    @property
    def exact_inference(self) -> str:
        return (
            f"bounded proof enumeration to depth {self.exact_depth} (nesyarena ground-program IR) "
            "+ exact weighted model counting"
        )

    def reasons(self) -> tuple[frozenset, ...]:
        return self._reasons

    def label(self, reason: frozenset) -> str:
        return self.labels.get(reason, default_label(reason))

    def score(self, reason: frozenset) -> float:
        return proof_score(reason, self.base)

    def exact_value(self) -> float:
        return wmc(self._reasons, self.base)

    def engine_value(self) -> float:
        # Preserve malformed answers until the certificate engine validates them. Valid numeric
        # values retain the old float-normalising API, while a caller assembling its decision trace
        # can still hand bools, non-finite values or other malformed scalars to that refusal path.
        raw = self.adapter.infer(self.program, self.base, [self.query])[self.query]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return raw
        try:
            return float(raw)
        except (TypeError, ValueError, OverflowError):
            return raw

    def probability(self, fact: Atom) -> float:
        """This fact's probability under the base interpretation — half of the wider surface."""
        return float(self.base[fact])

    def at(self, fact: Atom, probability: float) -> GroundProgramArtifact:
        """The same inference at `probability` for `fact`, and the same reason set to score it over.

        The widened perturbation. It re-scores what the base enumeration found and never
        re-enumerates, for the reason `without` does not: a family whose enumeration moved with the
        interpretation would compare two answers to two questions.
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"probability must lie in [0, 1], got {probability!r}")
        return GroundProgramArtifact(
            self.program,
            {**self.base, fact: float(probability)},
            self.query,
            self.adapter,
            self.exact_depth,
            self.labels,
            self.monotone,
            _reasons=self._reasons,
            decision_threshold=self.decision_threshold,
        )

    def without(self, fact: Atom) -> GroundProgramArtifact:
        """The same inference with `fact` at probability zero — the deletion probe's one call."""
        return self.at(fact, 0.0)
