"""Temporal proof engine for reasonsmith.

What this module is for:
  Discharges a `temporal` duty of the shape `always(f)` — with `f` a state property of one
  decision record — against a system that exposes its decision logic, at strength `proved`. It is
  the rung `docs/semantics.md` §3.5 said did not exist: before it, every `temporal` duty stopped at
  `observed` whatever the system exposed, because the solver and the replay search each reason
  about one decision at a time and had nothing to say about a formula quantified over a trace.

  The reasoning is one reduction and no new machinery. Over a **finite** decision trace — which is
  what a conformance run reads, and why LTLf rather than LTL is the semantics this engine claims —
  `always(f)` holds exactly when `f` holds at every position. Every position of every trace this
  system can emit is a decision its exposed `logic()` produces from an input its own `constraints`
  admit. So a proof that `f` holds over that whole input space is a proof of `always(f)` for every
  trace the system can emit, not merely for the one this run happened to read. The proof itself is
  `engines.proved.ProvedEngine` — the same Z3 encoding, the same premise-satisfiability check, the
  same interpreter cross-check, the same counterexample verification — asked about `f`.

  That is why this engine adds no dependency. An LTLf decision procedure was priced first
  (`pylogics` with `ltlf2dfa`, and Spot); both were rejected, and the PR that landed this records
  what each one needed. Neither is required for this fragment: `always` distributes over positions,
  so the formula the solver decides is a state property, and one of those this repository already
  decides.

What a reader must not break:
  - **Only `always(f)`, and only with `f` free of temporal operators.** Every other temporal shape
    is reported NOT EVALUATED, so the duty falls to `ObservedEngine` exactly as it did before this
    engine existed. `eventually(f)` is the one worth naming: it asserts that *some* position exists,
    which is a fact about the trace a system emitted and not about the decisions its logic admits,
    so no amount of reasoning about one decision at a time establishes it. Widening
    `state_property_under_always` to accept it would report `proved` for a claim nothing proved.
    (`test_only_always_reaches_the_temporal_proof_rung`)
  - **A `satisfied` verdict and a `violated` verdict here do not make symmetric claims, and the
    evidence summary must keep saying so.** Satisfied quantifies universally and therefore covers
    every trace the system can emit, this run's included. Violated is existential: the solver found
    an admissible input whose decision breaches `f`, verified to reproduce on the system, so *some*
    trace the system admits breaches the duty — which is a finding about the system as built and
    not a finding about the trace supplied here. That asymmetry is inherited from `ProvedEngine`,
    where it is already what `proved` means, and `TRACE_SEMANTICS` is where it is stated to the
    reader. (`test_a_temporal_violation_names_the_trace_it_is_and_is_not_about`)
  - Everything `ProvedEngine`'s own docstring forbids is forbidden here, because this engine's
    verdict is that engine's verdict: an `unknown` solver result, a timeout, unsatisfiable
    premises, an encoding that disagrees with the reference interpreter, or a counterexample that
    does not reproduce all still yield NOT EVALUATED rather than a rung.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from typing import Any, Optional

from reasonsmith.report import RequirementResult
from reasonsmith.rulelang import (
    ALWAYS_OPERATOR,
    UnsupportedConstructError,
    has_temporal_operator,
    parse_property,
)
from reasonsmith.spec import Requirement
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Verdict

__all__ = [
    "ALWAYS",
    "TRACE_SEMANTICS",
    "TemporalProofEngine",
    "state_property_under_always",
]

#: The one temporal operator this engine reduces. See the module docstring for why it is the only
#: one, and `rulelang.TEMPORAL_OPERATORS` for the rest of the fragment, which stays at `observed`.
#: It is the language's constant rather than a second spelling of it: `rulelang` strips the same
#: operator when it names an implication's antecedent, and two literals would be two places to
#: disagree about which operator distributes over positions.
ALWAYS = ALWAYS_OPERATOR

#: The trace semantics every verdict from this engine carries, because a `proved` temporal verdict
#: is a claim about a *set of traces* and a reader who cannot see which set cannot read it. Carried
#: on the result rather than left to the renderer, for the same reason the probe budget is.
TRACE_SEMANTICS = (
    "Trace semantics of this verdict: over a finite decision trace, `always(f)` holds exactly when "
    "`f` holds at every position, and every position of every trace this system can emit is a "
    "decision its exposed logic produces from an input its own constraints admit. A satisfied "
    "verdict is therefore universal — it covers every such trace, including the one this run read. "
    "A violated verdict is existential and weaker: it names an admissible input whose decision "
    "breaches the property, so some trace the system admits breaches the duty, which is not a "
    "finding about the trace supplied here."
)

_UNSET_LOGIC = object()


def state_property_under_always(spec: str) -> str | None:
    """The state property under a top-level `always(...)`, or None when there is not one.

    `None` for every other shape, including a spec that merely *contains* an `always` — the whole
    property has to be the quantification, because this engine's reduction is over the whole
    property. `None` too for `always(eventually(f))` and friends: the operand must be a state
    property, or what the solver decides is not what the duty says.

    Returns the operand as text rather than as an AST, so that `ProvedEngine` parses it through
    exactly the path a hand-written `spec` takes and no second parser exists to disagree with the
    first. Arrow forms survive that round trip as `Implies(...)`, which is in the language.
    """
    try:
        node = parse_property(spec)
    except UnsupportedConstructError:
        return None
    body = node.body
    if (
        isinstance(body, ast.Call)
        and isinstance(body.func, ast.Name)
        and body.func.id == ALWAYS
        and len(body.args) == 1
        and not has_temporal_operator(body.args[0])
    ):
        return ast.unparse(body.args[0])
    return None


class TemporalProofEngine:
    """Proves `always(f)` by deciding `f` over every decision the exposed logic admits."""

    @staticmethod
    def evaluate(
        req: Requirement,
        sut: SystemUnderTest,
        records: Optional[list[dict[str, Any]]] = None,
        timeout_ms: int = 5000,
        *,
        logic_data: Any = _UNSET_LOGIC,
    ) -> RequirementResult:
        from reasonsmith.engines.proved import ProvedEngine

        clause = f"{req.source_document} {req.article_clause}"
        inner = state_property_under_always(req.spec)
        if inner is None:
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not evaluated: {req.spec!r} is not an `always(f)` over a state property, and "
                    "that is the only temporal shape this engine reduces to something a solver "
                    "reasoning about one decision at a time can decide. The duty falls to the "
                    "engine that reads the trace."
                ),
                details={"reduction": "not_applicable_shape"},
                binding=req.binding,
                scope=req.scope,
            )

        kwargs = {} if logic_data is _UNSET_LOGIC else {"logic_data": logic_data}
        result = ProvedEngine.evaluate(
            replace(req, spec=inner), sut, records, timeout_ms, **kwargs
        )

        # The reduced property is quoted once, by `ProvedEngine`'s own summary, and not again
        # here: a reader who has to compare two renderings of the same formula to notice they
        # are the same formula is being made to do the engine's work.
        prefix = (
            f"Temporal duty {req.spec!r}, reduced to the state property under its `always` and "
            "put to the solver. "
        )
        summary = prefix + result.evidence_summary
        details: dict[str, Any] = {
            **result.details,
            "reduction": ALWAYS,
            "state_property": inner,
        }
        if result.strength is not None:
            summary = f"{summary} {TRACE_SEMANTICS}"
            details["trace_semantics"] = TRACE_SEMANTICS
        return replace(result, evidence_summary=summary, details=details)
