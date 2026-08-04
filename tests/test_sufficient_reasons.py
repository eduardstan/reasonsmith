"""Subset-minimal sufficient reasons, and the over-report they remove.

What this module is for:
  `docs/sufficient-reasons.md` defines what a reason the engine's answer depends on *is*, over the
  deletions `artifacts.InferenceArtifact` admits, and these tests hold the measurement to it. The
  defect being repaired is one of definition: the certificate switched each reason off **alone**, so
  two reasons jointly necessary and individually removable were both reported `deleted` and a
  system was accused of omitting two reasons its inference demonstrably used.

  `test_two_jointly_necessary_reasons_are_no_longer_reported_deleted` is the acceptance test, and
  `test_the_per_fact_probe_alone_still_cannot_tell_them_apart` is the same fixture measured the old
  way, kept beside it so the gap is visible rather than asserted.

What a reader must not break:
  - The fixture's two jointly-necessary reasons carry the **same** probability on purpose. A top-1
    engine falling back from one to an equally-weighted other returns the identical value, which is
    what makes each of them individually invisible to a single deletion. Give them different
    probabilities and the fallback moves the answer, the single probe sees it, and the fixture stops
    testing anything.
  - The fixture also carries a third reason the engine genuinely ignores. Without it, a
    reclassification that simply stopped reporting anything deleted would pass every test here.
  - A partial enumeration must degrade to `undetermined` and never to `deleted`. The budget test is
    the one that fails if that invariant is inverted, and inverting it is the only way this change
    could make the tool accuse a system it would otherwise have cleared.
"""

from __future__ import annotations

import pytest
from nesyarena.ir import Atom, GroundProgram, Rule
from nesyarena.oracle import wmc

from reasonsmith.certificate import certify
from reasonsmith.engines.certificate import DELETED_REASON_COUNT, CertificateEngine
from reasonsmith.explanations import contrastive_sets
from reasonsmith.report import PROBE_BUDGET_KEY
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

ADEQUACY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"

QUERY = Atom("adverse_action(APP-7)")
FIRST = Atom("references_under_policy(APP-7)")
SECOND = Atom("inquiries_over_policy(APP-7)")
THIRD = Atom("file_thin(APP-7)")

R1 = "R1 — the first of two the engine needs one of"
R2 = "R2 — the second of two the engine needs one of"
R3 = "R3 — the one the engine really does ignore"


class _KeepsOneProof:
    """An engine that reports the single highest-scoring proof still available to it.

    The ordinary shape of top-`k` truncation at `k = 1`, and the ordinary shape of joint necessity:
    with two equally-weighted proofs it falls back from either to the other without its answer
    moving at all, so no single deletion can see that it depends on them.
    """

    supports_grad = False
    name = "reference:top-1-proofs"
    claimed_semantics = "distribution semantics"

    def infer(self, program, base, queries):
        answers = {}
        for query in queries:
            available = [
                support
                for support in program.proof_supports(query, 1)
                if all(base.get(fact, 0.0) > 0.0 for fact in support)
            ]
            best = max(
                available,
                key=lambda support: (wmc([support], base), sorted(map(repr, support))),
                default=None,
            )
            answers[query] = wmc([best], base) if best else 0.0
        return answers


def _artifact(**overrides) -> dict:
    """Three reasons: two the engine needs one of, and one it ignores outright."""
    return {
        "program": GroundProgram(
            (Rule(QUERY, (FIRST,)), Rule(QUERY, (SECOND,)), Rule(QUERY, (THIRD,)))
        ),
        "base": {FIRST: 0.5, SECOND: 0.5, THIRD: 0.2},
        "query": QUERY,
        "adapter": _KeepsOneProof(),
        "exact_depth": 1,
        "monotone": True,
        "labels": {
            frozenset({FIRST}): R1,
            frozenset({SECOND}): R2,
            frozenset({THIRD}): R3,
        },
        **overrides,
    }


def _status(cert, label: str) -> str:
    return next(v.status for v in cert.verdicts if v.label == label)


# --------------------------------------------------------------------- the acceptance ----


def test_the_per_fact_probe_alone_still_cannot_tell_them_apart():
    """The gap, measured rather than asserted: switching each fact off alone moves nothing.

    This is exactly what the certificate used to read as three deleted reasons, and it is still
    what the first pass sees. What changed is that it is no longer the last word.
    """
    from reasonsmith.artifacts.ground_program import GroundProgramArtifact

    arguments = _artifact()
    artifact = GroundProgramArtifact(
        arguments["program"], arguments["base"], QUERY, arguments["adapter"], 1
    )
    exact, baseline = artifact.exact_value(), artifact.engine_value()
    for fact in (FIRST, SECOND, THIRD):
        alone = artifact.without(fact)
        assert alone.exact_value() < exact, f"{fact} carries no exact mass"
        assert alone.engine_value() == pytest.approx(baseline), (
            f"deleting {fact} alone moves the engine, so this fixture no longer holds the gap"
        )


def test_two_jointly_necessary_reasons_are_no_longer_reported_deleted():
    """The acceptance test. Two reasons the engine needs one of are `live`, not `deleted`.

    Each is individually removable — the engine falls back to the other and its answer does not
    move — and they are jointly necessary, which is a contrastive set of size two and invisible to
    any probe that switches one fact off at a time.
    """
    cert = certify(**_artifact())

    assert _status(cert, R1) == "live"
    assert _status(cert, R2) == "live"
    assert R1 not in cert.missing_reasons()
    assert R2 not in cert.missing_reasons()

    witnesses = {v.label: frozenset(v.joint_witness) for v in cert.jointly_necessary}
    assert witnesses == {R1: frozenset({FIRST, SECOND}), R2: frozenset({FIRST, SECOND})}, (
        "both reasons must name the same contrastive set: it is the joint deletion, and nothing "
        "either of them does alone, that the engine notices"
    )


def test_the_reason_the_engine_really_ignores_is_still_reported_deleted():
    """The other half of the acceptance: this is a repair, not an amnesty.

    A reclassification that simply stopped reporting anything deleted would pass the test above.
    """
    cert = certify(**_artifact())

    assert _status(cert, R3) == "deleted"
    assert cert.missing_reasons() == [R3]
    assert cert.search is not None and cert.search.exhaustive, (
        "`deleted` is universal over the contrastive sets and may be claimed only on an exhausted "
        "enumeration"
    )


def test_the_duty_no_longer_reports_this_system_violated_on_the_two_it_uses():
    """The verdict the definition change is for: an accusation withdrawn, at the engine.

    The system's notice states the two reasons its answer stands on and not the one it ignores, so
    the count of deleted reasons the duty reads is what decides it.
    """
    requirement = load_pack("ecoa").get_requirement(ADEQUACY)
    record = {
        "decision_id": "APP-7",
        "artifact_logs_reason_explanation": f"{R1}; {R2}",
        DELETED_REASON_COUNT: 0,
    }

    class _System:
        system_domains = ("consumer-credit",)

        def capabilities(self):
            return {"decision_id", "artifact_logs_reason_explanation", DELETED_REASON_COUNT}

        def decisions(self):
            return [record]

        def artifact(self, decision):
            return _artifact()

    result = CertificateEngine.evaluate(requirement, _System(), [record])
    assert result.verdict is Verdict.VIOLATED, (
        "the third reason is genuinely deleted, so this system is still in breach — the point is "
        "which reasons the breach names"
    )
    assert result.details["certificates"][0]["missing_reasons"] == [R3]
    assert result.details["reasons_live_only_jointly"] == 2


# ------------------------------------------------------------ the budget, and degrading ----


def test_a_partial_enumeration_degrades_to_undetermined_and_never_to_deleted():
    """The invariant that makes a bounded search safe: a shorter one names fewer missing reasons.

    One probe buys the whole-space question and nothing else, so nothing can be shown irrelevant.
    """
    cert = certify(**_artifact(budget=1))

    assert cert.search is not None and not cert.search.exhaustive
    assert cert.missing_reasons() == [], (
        "a search that did not finish may not report a reason deleted"
    )
    assert {v.status for v in cert.verdicts} == {"undetermined"}
    assert len(cert.uncertified) == 3


def test_no_budget_makes_this_instrument_name_more_missing_reasons_than_a_complete_search():
    """Stated as a sweep, because it is the one property a budget must not be able to invert."""
    complete = set(certify(**_artifact()).missing_reasons())
    for budget in range(0, 12):
        named = set(certify(**_artifact(budget=budget)).missing_reasons())
        assert named <= complete, (
            f"a {budget}-probe search named {named - complete} that a complete search does not"
        )


def test_the_joint_search_budget_travels_into_the_verdict():
    """`PROBE_BUDGET_FIELDS` already forces the bound onto a probed verdict; the joint search's own
    two numbers ride in the same envelope, because how far it got is the bound on every `deleted`.
    """
    requirement = load_pack("ecoa").get_requirement(ADEQUACY)
    record = {
        "decision_id": "APP-7",
        "artifact_logs_reason_explanation": f"{R1}; {R2}",
        DELETED_REASON_COUNT: 0,
    }

    class _System:
        system_domains = ("consumer-credit",)

        def capabilities(self):
            return {"decision_id", "artifact_logs_reason_explanation", DELETED_REASON_COUNT}

        def decisions(self):
            return [record]

        def artifact(self, decision):
            return _artifact(budget=1)

    result = CertificateEngine.evaluate(requirement, _System(), [record])
    space = result.details[PROBE_BUDGET_KEY]["input_space"]
    assert space["joint deletion patterns tried"] == 1
    assert space["decisions whose joint search did not finish"] == 1
    assert result.details["reasons_undetermined_by_the_joint_search"] == 3
    assert result.verdict is Verdict.SATISFIED and result.strength is Strength.PROBED
    assert "never more" in result.evidence_summary


# ------------------------------------------------------------------- the search itself ----


def test_deleting_everything_without_moving_the_engine_settles_the_lattice_in_one_probe():
    """`docs/sufficient-reasons.md` §4, Corollary 3, and the reason the demonstration costs one
    extra probe rather than an enumeration."""
    search = contrastive_sets(lambda deleted: False, ("a", "b", "c", "d"))

    assert search.probes == 1
    assert search.exhaustive and search.contrastive == () and search.relevant == frozenset()


def test_every_contrastive_set_found_is_subset_minimal_and_the_enumeration_is_complete():
    """Two independent joint necessities over four facts, neither visible to a single deletion."""
    pairs = [frozenset({"a", "b"}), frozenset({"c", "d"})]
    search = contrastive_sets(
        lambda deleted: any(pair <= deleted for pair in pairs), ("a", "b", "c", "d")
    )

    assert search.exhaustive
    assert set(search.contrastive) == set(pairs)
    assert search.relevant == frozenset({"a", "b", "c", "d"})


def test_a_fact_in_no_contrastive_set_is_reported_irrelevant():
    """The universal claim, and the only one an exhausted enumeration buys."""
    search = contrastive_sets(
        lambda deleted: frozenset({"a", "b"}) <= deleted, ("a", "b", "spectator")
    )

    assert search.exhaustive
    assert "spectator" not in search.relevant


def test_the_probes_a_search_spends_are_counted_and_capped():
    spent = []

    def moved(deleted):
        spent.append(deleted)
        return frozenset({"a", "b"}) <= deleted

    search = contrastive_sets(moved, ("a", "b", "c", "d", "e"), budget=3)
    assert search.probes == 3 == len(spent)
    assert not search.exhaustive


# ------------------------------------------------------- the three not-certified states ----


def test_the_three_not_certified_states_are_reported_apart():
    """`uncertified` was one bucket for three different facts about the evidence, and the third of
    them — a joint search that did not resolve a reason — had nowhere to be said at all."""
    shared = Atom("bureau_record_matched(APP-7)")
    program = GroundProgram(
        (
            Rule(QUERY, (shared, Atom("delinquency_on_file(APP-7)"))),
            Rule(QUERY, (shared, Atom("inquiries_over_policy(APP-7)"))),
            Rule(QUERY, (THIRD,)),
        )
    )
    base = {
        shared: 0.9,
        Atom("delinquency_on_file(APP-7)"): 0.0,
        Atom("inquiries_over_policy(APP-7)"): 0.0,
        THIRD: 0.5,
    }
    cert = certify(program, base, QUERY, _KeepsOneProof(), 1, monotone=True)

    assert [v.status for v in cert.inconclusive] == ["inconclusive", "inconclusive"]
    assert cert.uncertified == cert.unseparable + cert.inconclusive + cert.undetermined

    partial = certify(**_artifact(budget=1))
    assert len(partial.undetermined) == 3
    assert partial.unseparable == [] and partial.inconclusive == []


def test_a_reason_the_probe_cannot_separate_is_never_promoted_to_deleted():
    """`docs/semantics.md` §3 records this as a deliberate limit: a shared-fact reason is never
    promoted to `deleted` on the completeness of the enumeration alone.

    The fixture's `{a, b}` reason shares every fact with a sibling — no private fact — so it is
    `unseparable`. The engine answers a constant, so deleting anything at all leaves its answer
    where it is and the joint search is exhaustive in one probe: exactly the *complete enumeration*
    on which `docs/sufficient-reasons.md` §5 Definition 8 would license reporting such a reason
    `deleted` ("was not needed"). It must not be. The licence is deliberately unused, because its
    completeness rests on the artefact's self-declared monotonicity — a declaration nothing here
    confirms (`docs/semantics.md` §3, *The inference artefact*) — so promotion would mint an
    accusation out of it. The two siblings `{a, b}` shares its facts with are genuinely `deleted`,
    which is why the test is not an amnesty.
    """

    class _ConstantEngine:
        supports_grad = False
        name = "reference:constant-engine"
        claimed_semantics = "distribution semantics"

        def infer(self, program, base, queries):
            return {q: 0.5 for q in queries}

    q, a, b, c, d = Atom("q"), Atom("a"), Atom("b"), Atom("c"), Atom("d")
    program = GroundProgram((Rule(q, (a, b)), Rule(q, (a, c)), Rule(q, (b, d))))
    base = {a: 0.6, b: 0.5, c: 0.4, d: 0.3}
    cert = certify(program, base, q, _ConstantEngine(), 1, monotone=True)

    statuses = {frozenset(v.reason): v.status for v in cert.verdicts}
    assert statuses[frozenset({a, b})] == "unseparable"
    assert statuses[frozenset({a, c})] == "deleted"
    assert statuses[frozenset({b, d})] == "deleted"
    # The licence's own precondition is met — the enumeration terminated — and the rule still holds.
    assert cert.search is not None and cert.search.exhaustive
    assert frozenset({a, b}) not in [frozenset(v.reason) for v in cert.deleted]
