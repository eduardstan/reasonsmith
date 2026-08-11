"""The widened artefact perturbation, and the one measurement that needs it.

What this module is for:
  Two things, and the second is why the first was allowed to exist.

  `test_the_battery_refutes_every_deviating_provenance_and_never_the_exact_one` is the acceptance
  run: `semantic_laws.check_laws` over the five `nesyarena.suts.registry()` provenances on the 16
  generated instances `docs/build_nesyarena_report.py` drives. Four of the five do not implement the
  distribution semantics they claim; every one of those four is refuted, the one that does implement
  it is refuted on none, and no oracle is consulted anywhere in the loop — the reference side of
  every comparison is the system's own answer at another interpretation.

  `test_neither_one_directional_variant_refutes_a_top_k_engine` is the measured ground of the
  reversal recorded in `artifacts/__init__.py` and `docs/formal.md` §3.6. The protocol used to state
  that there is no `with_(fact)`; a perturbation that only lowers a fact's probability, or only
  raises it, refutes a top-`k` engine on **none** of the 16 instances, while the triple spanning
  `[0, 1]` refutes it on 8. Delete that test and the widening loses the evidence that it buys
  anything, which is the only thing that made reversing a published refusal defensible.

What a reader must not break:
  - The battery is generated, never hand-written, and the grid is `build_nesyarena_report.battery`'s
    own. `nesyarena` is a dependency under review and nothing here may modify it.
  - The exact-WMC row is the load-bearing one. A law set that refutes the four deviating
    provenances is worth nothing if it also refutes the one that is right, and that is the direction
    this repository is not allowed to fail in.
  - `test_the_deletion_probe_never_reaches_the_widened_perturbation` is what keeps the reversal
    narrow: it certifies through an artefact that raises on `at`, so a certificate path that started
    calling it would fail here rather than silently widening what `deleted` means.
"""

from __future__ import annotations

import pytest
from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.generators import chain_family, cyclic_family, overlap_family
from nesyarena.suts import registry

from reasonsmith.artifacts import NO_INTERPRETATION, admits_interpretation
from reasonsmith.artifacts.ground_program import GroundProgramArtifact
from reasonsmith.artifacts.reason_trace import ReasonTraceArtifact
from reasonsmith.certificate import certify_artifact
from reasonsmith.semantic_laws import (
    MONOTONICITY,
    MULTILINEARITY,
    SEMANTICS_WITH_LAWS,
    check_laws,
    law_refusal,
)
from reasonsmith.spec import CLAIMED_SEMANTICS

TOL = 1e-9

#: `docs/build_nesyarena_report.battery`'s grid, restated rather than imported: that module is
#: loaded by path in two other tests because it lives under `docs/`, and this file needs the
#: instances and none of the conformance machinery around them.
def battery():
    instances = []
    for p_count in (1, 2, 4):
        for length in (2, 3):
            for shared in (0, 1):
                instances.append(
                    (
                        f"G1-P{p_count}-L{length}-c{shared}",
                        overlap_family(P=p_count, L=length, c=shared, p=0.7),
                    )
                )
    for length in (2, 3, 4):
        instances.append((f"G2-chain-L{length}", chain_family(L=length, p=0.9)))
    instances.append(("G2-cyclic", cyclic_family()))
    return instances


def artefact_for(provenance, instance):
    """One decision of one provenance, as the artefact family this repository ships.

    `exact_depth` is the generator's own recorded depth and the adapter enumerates to the same
    bound, so both sides of every probe answer the same question.
    """
    depth = instance.params.get("depth", 1)
    return GroundProgramArtifact(
        instance.program,
        dict(instance.probs),
        instance.query,
        ReferenceAdapter(provenance, max_depth=depth),
        depth,
        monotone=True,
    )


def deviates(provenance, instance) -> bool:
    """Whether this provenance's answer differs from the semantics it claims, on this instance.

    The only place a `nesyarena` oracle is consulted, and it is consulted **outside** the battery:
    it populates the column the run is compared against and plays no part in any law.
    """
    return (
        abs(
            provenance.value(instance.proofs, instance.probs)
            - provenance.oracle(instance.proofs, instance.probs)
        )
        > TOL
    )


def test_the_battery_refutes_every_deviating_provenance_and_never_the_exact_one(capsys):
    instances = battery()
    rows = []
    for provenance in registry():
        deviating = refuted = 0
        counts = {MULTILINEARITY: 0, MONOTONICITY: 0}
        probes = 0
        for _label, instance in instances:
            if deviates(provenance, instance):
                deviating += 1
            report = check_laws(artefact_for(provenance, instance), tol=TOL)
            assert report is not None
            probes += report.probes
            refuted += bool(report.refuted)
            for violation in report.violations:
                counts[violation.law] += 1
        rows.append((provenance.name, deviating, refuted, counts, probes))

    with capsys.disabled():
        print(f"\n{len(instances)} generated instances, no oracle inside any law\n")
        print(f"{'provenance':<24}{'deviates':>10}{'refuted':>10}{'L2':>6}{'L3':>6}{'probes':>9}")
        for name, deviating, refuted, counts, probes in rows:
            print(
                f"{name:<24}{f'{deviating}/{len(instances)}':>10}"
                f"{f'{refuted}/{len(instances)}':>10}"
                f"{counts[MULTILINEARITY]:>6}{counts[MONOTONICITY]:>6}{probes:>9}"
            )

    by_name = {name: (deviating, refuted) for name, deviating, refuted, _, _ in rows}
    assert by_name["exact-wmc"] == (0, 0), (
        "the provenance that implements what it claims was refuted"
    )
    deviating_rows = {name: pair for name, pair in by_name.items() if name != "exact-wmc"}
    assert len(deviating_rows) == 4
    for name, (deviating, refuted) in deviating_rows.items():
        assert deviating > 0, f"{name} was expected to deviate from its claim on this battery"
        assert refuted > 0, f"{name} deviates from the semantics it claims and no law caught it"
        # Refutation is a lower bound on deviation and must stay on that side of it.
        assert refuted <= deviating, f"{name} was refuted on an instance where it does not deviate"


def _affine_over(artefact, low, high) -> int:
    """Facts where `E` is not affine between `low(p)` and `high(p)`, tested at the midpoint."""
    found = 0
    for fact in sorted({f for reason in artefact.reasons() for f in reason}, key=repr):
        probability = artefact.probability(fact)
        left, right = low(probability), high(probability)
        if right - left < 1e-12:
            continue
        ends = [artefact.at(fact, value).engine_value() for value in (left, right)]
        middle = artefact.at(fact, (left + right) / 2).engine_value()
        found += abs(middle - sum(ends) / 2) > TOL
    return found


def test_neither_one_directional_variant_refutes_a_top_k_engine(capsys):
    variants = {
        "DOWN {0, p/2, p}": (lambda p: 0.0, lambda p: p),
        "UP {p, (1+p)/2, 1}": (lambda p: p, lambda p: 1.0),
        "SPAN {0, p/2… 1}": (lambda p: 0.0, lambda p: 1.0),
    }
    instances = battery()
    measured = {}
    for provenance in registry():
        counts = dict.fromkeys(variants, 0)
        for _label, instance in instances:
            artefact = artefact_for(provenance, instance)
            for name, (low, high) in variants.items():
                counts[name] += bool(_affine_over(artefact, low, high))
        measured[provenance.name] = counts

    with capsys.disabled():
        print()
        print(f"{'provenance':<24}" + "".join(f"{name:>22}" for name in variants))
        for name, counts in measured.items():
            print(
                f"{name:<24}"
                + "".join(f"{f'{counts[v]}/{len(instances)}':>22}" for v in variants)
            )

    for engine in ("top-1-proofs", "top-3-proofs"):
        assert measured[engine]["DOWN {0, p/2, p}"] == 0
        assert measured[engine]["UP {p, (1+p)/2, 1}"] == 0
        assert measured[engine]["SPAN {0, p/2… 1}"] > 0, (
            "the full-range perturbation is what earns the reversal; if a one-directional "
            "variant now suffices, the widening is no longer paid for"
        )
    assert measured["exact-wmc"] == dict.fromkeys(variants, 0)


def test_a_family_that_offers_only_deletion_is_refused_and_the_refusal_names_the_tool():
    artefact = ReasonTraceArtifact(
        "approve",
        {"thin file": frozenset({"credit_history_months"})},
        lambda suppressed: 0.0 if suppressed else 1.0,
        engine_name="stub",
        claimed_semantics="distribution semantics",
        monotone=True,
    )
    assert not admits_interpretation(artefact)
    assert law_refusal(artefact) == NO_INTERPRETATION
    assert check_laws(artefact) is None


def test_the_law_sets_name_a_subset_of_the_shipped_vocabulary():
    """Two sets, and this module owns only the smaller one.

    `spec.CLAIMED_SEMANTICS` is what an artefact may claim and `spec.normalize_claimed_semantics`
    refuses anything else before it reaches here. `SEMANTICS_WITH_LAWS` is what this module can
    refute, and a member of it that is not a member of that would be a law nothing can ever claim.
    """
    assert set(SEMANTICS_WITH_LAWS) <= set(CLAIMED_SEMANTICS)
    assert set(CLAIMED_SEMANTICS) - set(SEMANTICS_WITH_LAWS), (
        "every admitted claim now has laws; the unlawed branch of `law_refusal` is unreachable "
        "and this test is no longer measuring anything"
    )


def test_an_admitted_claim_with_no_laws_is_refused_naming_the_claim():
    _label, instance = battery()[0]
    artefact = artefact_for(registry()[0], instance)
    unlawed = next(s for s in CLAIMED_SEMANTICS if s not in SEMANTICS_WITH_LAWS)
    artefact.adapter.claimed_semantics = unlawed
    refusal = law_refusal(artefact)
    assert refusal is not None
    assert unlawed in refusal
    assert check_laws(artefact) is None


def test_a_claim_outside_the_vocabulary_never_reaches_this_module():
    """It is refused one layer down, by the boundary #156 closed — not silently passed through."""
    _label, instance = battery()[0]
    artefact = artefact_for(registry()[0], instance)
    artefact.adapter.claimed_semantics = "max-join over proof scores"
    with pytest.raises(ValueError, match="not a known claimed semantics value"):
        law_refusal(artefact)


def test_an_artefact_declaring_no_semantics_is_refused_rather_than_crashing():
    """`law_refusal` promises a reason, so an absent declaration is one — not a `ValueError`."""
    _label, instance = battery()[0]
    inner = artefact_for(registry()[0], instance)

    class NoClaim:
        def __getattr__(self, name):
            if name == "claimed_semantics":
                raise AttributeError(name)
            return getattr(inner, name)

    artefact = NoClaim()
    assert admits_interpretation(artefact)
    refusal = law_refusal(artefact)
    assert refusal is not None
    assert all(semantics in refusal for semantics in SEMANTICS_WITH_LAWS)
    assert check_laws(artefact) is None


def test_an_accepted_claim_spelling_is_canonical_in_the_law_report():
    _label, instance = battery()[0]
    inner = artefact_for(registry()[0], instance)

    class RawClaim:
        claimed_semantics = " Distribution Semantics "

        def __getattr__(self, name):
            return getattr(inner, name)

    artefact = RawClaim()
    assert law_refusal(artefact) is None
    report = check_laws(artefact)
    assert report is not None
    assert report.claimed_semantics == "distribution semantics"


def test_the_monotonicity_law_fires_on_an_engine_that_falls_when_a_fact_is_raised():
    _label, instance = battery()[0]

    class Inverted:
        """An engine answering `1 − p` for one fact it reads. Affine in it, and decreasing."""

        name = "inverted"
        claimed_semantics = "distribution semantics"

        def __init__(self, fact):
            self.fact = fact

        def infer(self, program, base, queries):
            return {query: 1.0 - base[self.fact] for query in queries}

    artefact = GroundProgramArtifact(
        instance.program,
        dict(instance.probs),
        instance.query,
        Inverted(sorted(instance.probs, key=repr)[0]),
        instance.params.get("depth", 1),
        monotone=True,
    )
    report = check_laws(artefact)
    assert report is not None and report.refuted
    assert {violation.law for violation in report.violations} == {MONOTONICITY}
    assert "not non-decreasing" in report.violations[0].detail


def test_the_deletion_probe_never_reaches_the_widened_perturbation():
    """The reversal is one-directional: the certificate still calls `without` and nothing else."""

    class DeletionOnly(GroundProgramArtifact):
        def at(self, fact, probability):
            if probability != 0.0:
                raise AssertionError("the deletion probe reached the widened perturbation")
            return super().at(fact, probability)

    _label, instance = battery()[0]
    artefact = DeletionOnly(
        instance.program,
        dict(instance.probs),
        instance.query,
        ReferenceAdapter(registry()[0], max_depth=instance.params.get("depth", 1)),
        instance.params.get("depth", 1),
        monotone=True,
    )
    assert certify_artifact(artefact, TOL).verdict == "PASS"


def test_at_refuses_a_probability_outside_the_unit_interval():
    _label, instance = battery()[0]
    artefact = artefact_for(registry()[0], instance)
    fact = next(iter(instance.probs))
    for value in (-0.1, 1.5):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            artefact.at(fact, value)


def test_without_is_the_widened_perturbation_at_zero():
    _label, instance = battery()[0]
    artefact = artefact_for(registry()[0], instance)
    fact = next(iter(instance.probs))
    assert artefact.without(fact).probability(fact) == 0.0
    assert artefact.without(fact).engine_value() == artefact.at(fact, 0.0).engine_value()
    assert artefact.without(fact).reasons() == artefact.reasons()


def test_the_report_carries_its_limits_and_they_refuse_the_affirmative_reading():
    _label, instance = battery()[0]
    report = check_laws(artefact_for(registry()[0], instance))
    assert report is not None and not report.refuted
    assert "can never confirm it" in report.limits
    assert report.probes == 2 * report.facts + 1
