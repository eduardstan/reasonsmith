from __future__ import annotations

import math

import pytest

from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import Requirement
from reasonsmith.statistical import (
    AUTHORITY_REQUIRED_FIELDS,
    PROXY_BLINDNESS_LIMIT,
    SAMPLING_REQUIRED_FIELDS,
    clopper_pearson,
    measure_selection_rates,
    ratio_enclosure,
    validate_measurement_payload,
    validate_sampling_plan,
)
from reasonsmith.sut import BaseSUT


def plan():
    value = dict.fromkeys(SAMPLING_REQUIRED_FIELDS, "declared")
    value.update(design="iid_binomial", weights="none", clustering="none")
    return value


def authority():
    return dict.fromkeys(AUTHORITY_REQUIRED_FIELDS, "declared")


def rows():
    return [
        {"group": "a", "outcome": 1, "unit": 1},
        {"group": "a", "outcome": 0, "unit": 2},
        {"group": "b", "outcome": 1, "unit": 3},
        {"group": "b", "outcome": 1, "unit": 4},
    ]


def test_cp_is_exact_at_boundaries_and_matches_scratch_fixture():
    assert clopper_pearson(0, 10, 0.05)[0] == 0
    assert clopper_pearson(10, 10, 0.05)[1] == 1
    low, high = clopper_pearson(40, 100, 0.025)
    assert low == pytest.approx(0.2908066463)
    assert high == pytest.approx(0.5168566215)


def test_cp_rejects_bad_counts_and_alpha():
    for args in [
        (True, 2, 0.05),
        (1, True, 0.05),
        (1.0, 2, 0.05),
        (1, 0, 0.05),
        (3, 2, 0.05),
        (1, 2, 0),
        (1, 2, 1),
    ]:
        with pytest.raises((TypeError, ValueError)):
            clopper_pearson(*args)


def test_ratio_enclosure_and_zero_denominator_refusal():
    result = ratio_enclosure({"a": (0.2908066463, 0.5168566215), "b": (0.4831433785, 0.7091933537)})
    assert result == pytest.approx((0.4100526954, 1.0))
    with pytest.raises(ValueError):
        ratio_enclosure({})
    with pytest.raises(ValueError):
        ratio_enclosure({"a": (0, 0), "b": (0, 0)})
    with pytest.raises(ValueError):
        ratio_enclosure({"a": (1, 0)})
    with pytest.raises(ValueError):
        ratio_enclosure({"a": (0, 0.5, 0.7)})


def test_plan_validation_is_explicit_and_never_inferred():
    assert validate_sampling_plan(None)[0] is False
    assert validate_sampling_plan({"status": "absent", "description": "none"})[0] is False
    with pytest.raises(TypeError):
        validate_sampling_plan("records")
    with pytest.raises(ValueError):
        validate_sampling_plan({})
    bad = plan()
    bad["design"] = "weighted"
    with pytest.raises(ValueError):
        validate_sampling_plan(bad)
    bad = plan()
    bad["weights"] = True
    with pytest.raises(ValueError):
        validate_sampling_plan(bad)
    bad = plan()
    bad["clustering"] = True
    with pytest.raises(ValueError):
        validate_sampling_plan(bad)


def test_descriptive_measurement_without_plan_has_no_confidence_claim():
    measurement = measure_selection_rates(
        rows(), groups=("a", "b"), group_field="group", outcome_field="outcome"
    )
    assert measurement["status"] == "descriptive_only"
    assert measurement["confidence"]["level"] is None
    assert measurement["metric"]["point_estimate"] == 0.5
    assert measurement["decision_rule"] is None
    assert measurement["proxy_blindness_limit"] == PROXY_BLINDNESS_LIMIT


def test_valid_plan_without_authority_keeps_cp_beside_not_evaluated():
    measurement = measure_selection_rates(
        rows(),
        groups=("a", "b"),
        group_field="group",
        outcome_field="outcome",
        sampling_assumption=plan(),
    )
    assert measurement["status"] == "measurement_no_authority"
    assert measurement["confidence"]["interval_method"] == "clopper_pearson_simultaneous_bonferroni"
    assert measurement["authority_provenance"] is None
    assert measurement["threshold"] is None


def test_valid_authority_and_threshold_are_carried_without_a_decision_rule():
    threshold = {"value": 0.8, "meaning": "four-fifths screening threshold", "comparison": "strict"}
    measurement = measure_selection_rates(
        rows(),
        groups=("a", "b"),
        group_field="group",
        outcome_field="outcome",
        sampling_assumption=plan(),
        authority_provenance=authority(),
        threshold=threshold,
    )
    assert measurement["status"] == "measurement"
    assert measurement["threshold"] == threshold
    assert measurement["decision_rule"] is None


def test_raw_record_failures_are_not_silently_dropped():
    for bad in [
        [{"group": "a", "outcome": 1}],
        [{"group": "a", "outcome": 1, "unit": 1}, {"group": "a", "outcome": 0, "unit": 1}],
        [{"group": "c", "outcome": 1}],
        [{"group": "a", "outcome": 2}],
        [{"group": "a", "outcome": 1}, {"group": "b", "outcome": 0}],
    ]:
        with pytest.raises(ValueError):
            measure_selection_rates(
                bad,
                groups=("a", "b"),
                group_field="group",
                outcome_field="outcome",
                unit_field="unit",
            )
    with pytest.raises(ValueError):
        measure_selection_rates([], groups=("a", "b"), group_field="group", outcome_field="outcome")
    with pytest.raises(ValueError):
        measure_selection_rates(
            rows(), groups=("a", "a"), group_field="group", outcome_field="outcome"
        )
    with pytest.raises(ValueError):
        measure_selection_rates(rows(), groups=("a",), group_field="group", outcome_field="outcome")


def test_payload_validator_reconciles_counts_and_requires_closed_shape():
    measurement = measure_selection_rates(
        rows(),
        groups=("a", "b"),
        group_field="group",
        outcome_field="outcome",
        sampling_assumption=plan(),
    )
    validate_measurement_payload(measurement)
    for key in (
        "groups",
        "counts",
        "metric",
        "confidence",
        "decision_rule",
        "status",
        "refusal",
        "proxy_blindness_limit",
    ):
        malformed = dict(measurement)
        malformed.pop(key)
        with pytest.raises(ValueError):
            validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["n"] = 99
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["proxy_blindness_limit"] = "short"
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["decision_rule"] = {"rule": "ratio"}
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["counts"] = {"a": {"n": 2, "successes": 1}}
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["metric"] = {"rates": {"a": math.inf, "b": 0.5}}
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)


def test_authority_and_threshold_shapes_are_not_guessed():
    with pytest.raises(ValueError):
        measure_selection_rates(
            rows(),
            groups=("a", "b"),
            group_field="group",
            outcome_field="outcome",
            sampling_assumption=plan(),
            authority_provenance={},
        )
    measurement = measure_selection_rates(
        rows(), groups=("a", "b"), group_field="group", outcome_field="outcome"
    )
    malformed = dict(measurement)
    malformed["threshold"] = {"value": 0.8}
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)
    malformed = dict(measurement)
    malformed["authority_provenance"] = {}
    with pytest.raises(ValueError):
        validate_measurement_payload(malformed)


def test_statistical_requirement_dispatch_and_rendering():
    from reasonsmith.report import _evaluate_statistical_requirement
    from reasonsmith.spec import Requirement
    from reasonsmith.verdict import EvidenceBasis, Verdict

    req = Requirement(
        id="stat",
        source_document="Guide",
        article_clause="29 CFR 1607.4(D)",
        verbatim_text="quoted",
        stakeholder="employer",
        formalism="statistical",
        spec="selection_rate_ratio(outcome, group)",
        rationale="Measure selection rates.",
        requires=("outcome", "group"),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    plan_data = {
        "groups": ("a", "b"),
        "sampling_assumption": plan(),
        "confidence_level": 0.95,
        "authority_provenance": authority(),
    }
    result = _evaluate_statistical_requirement(req, rows(), plan_data)
    assert result.basis is EvidenceBasis.STATISTICAL
    assert result.verdict is Verdict.INCONCLUSIVE and result.strength is None
    # Exercise the real renderer through a minimal report.
    from reasonsmith.report import ConformanceReport

    report = ConformanceReport(pack_id="p", system_name="s", results=(result,))
    assert "selection-rate ratio estimate" in report.render_text()
    assert "not called representative" in report.render_html()
    assert report.counts["on_a_statistical_measurement"] == 1
    bad = _evaluate_statistical_requirement(req, rows(), {"groups": ("a", "b")})
    assert bad.details["statistical_measurement"]["status"] == "descriptive_only"
    assert bad.outcome == "not_evaluated"
    refused = _evaluate_statistical_requirement(req, [], {"groups": ("a", "b")})
    assert refused.details["statistical_measurement"]["status"] == "refused"


def test_statistical_validator_refuses_bad_shapes_and_boundary_plans():
    from reasonsmith.statistical import _authority_complete

    with pytest.raises(TypeError):
        _authority_complete("not a mapping")
    incomplete = authority()
    incomplete.pop("api_endpoint")
    incomplete.pop("official_api_endpoint", None)
    incomplete.pop("official_url", None)
    with pytest.raises(ValueError):
        _authority_complete(incomplete)
    with pytest.raises(TypeError):
        validate_measurement_payload([])
    measurement = measure_selection_rates(
        rows(), groups=("a", "b"), group_field="group", outcome_field="outcome"
    )
    with pytest.raises(ValueError):
        validate_measurement_payload({**measurement, "groups": []})
    with pytest.raises(ValueError):
        validate_measurement_payload({**measurement, "groups": ["a", "a"]})
    with pytest.raises(ValueError):
        validate_measurement_payload(
            {
                **measurement,
                "counts": {"a": {"n": 0, "successes": 0}, "b": {"n": 2, "successes": 2}},
            }
        )
    with pytest.raises(ValueError):
        validate_measurement_payload({**measurement, "metric": None})
    bad_conf = plan()
    with pytest.raises(ValueError):
        measure_selection_rates(
            rows(),
            groups=("a", "b"),
            group_field="group",
            outcome_field="outcome",
            sampling_assumption=bad_conf,
            confidence_level=1,
        )
    zero = [{"group": "a", "outcome": 0}, {"group": "b", "outcome": 0}]
    measured = measure_selection_rates(
        zero,
        groups=("a", "b"),
        group_field="group",
        outcome_field="outcome",
        sampling_assumption=plan(),
    )
    assert measured["metric"]["point_estimate"] is None
    assert measured["confidence"]["ratio_interval"] == [0.0, 1.0]


def test_statistical_numeric_and_refusal_edges():
    import reasonsmith.statistical as statistical

    assert statistical._regularized_beta(1, 1, 0) == 0
    assert statistical._regularized_beta(1, 1, 1) == 1
    assert statistical._beta_quantile(0, 1, 1) == 0
    assert statistical._beta_quantile(1, 1, 1) == 1
    assert statistical.validate_sampling_plan(None)[0] is False
    assert statistical._authority_complete(None) is False
    with pytest.raises(ValueError):
        measure_selection_rates(
            [{}], groups=("a", "b"), group_field="group", outcome_field="outcome"
        )
    boolean_measure = measure_selection_rates(
        [{"group": "a", "outcome": True}, {"group": "b", "outcome": False}],
        groups=("a", "b"),
        group_field="group",
        outcome_field="outcome",
    )
    assert boolean_measure["metric"]["rates"] == {"a": 1.0, "b": 0.0}
    original = statistical.ratio_enclosure
    statistical.ratio_enclosure = lambda _intervals: (_ for _ in ()).throw(
        ValueError("not identified")
    )
    try:
        measured = measure_selection_rates(
            rows(),
            groups=("a", "b"),
            group_field="group",
            outcome_field="outcome",
            sampling_assumption=plan(),
        )
        assert measured["confidence"]["ratio_interval"] is None
    finally:
        statistical.ratio_enclosure = original


@pytest.mark.parametrize(
    "threshold",
    [
        {"value": "", "meaning": "", "comparison": ""},
        {"value": False, "meaning": 0, "comparison": []},
        {"value": float("nan"), "meaning": "threshold", "comparison": "strict"},
        {"value": 0.8, "meaning": "", "comparison": "strict"},
    ],
)
def test_threshold_provenance_rejects_empty_nonsemantic_and_nonfinite_values(threshold):
    with pytest.raises(ValueError):
        measure_selection_rates(
            rows(),
            groups=("a", "b"),
            group_field="group",
            outcome_field="outcome",
            sampling_assumption=plan(),
            authority_provenance=authority(),
            threshold=threshold,
        )


def test_authority_provenance_rejects_garbage_even_when_all_keys_are_present():
    bad = authority()
    bad.update(
        authority=True,
        citation=42,
        official_url=object(),
        retrieval_timestamp=float("nan"),
        quoted_passage=[],
        scope=False,
    )
    with pytest.raises(ValueError):
        measure_selection_rates(
            rows(),
            groups=("a", "b"),
            group_field="group",
            outcome_field="outcome",
            sampling_assumption=plan(),
            authority_provenance=bad,
        )


class _StatisticalSUT(BaseSUT):
    def __init__(self):
        super().__init__({"group", "outcome"})

    def decisions(self):
        return rows()


@pytest.mark.parametrize(
    "malformed_plan",
    [
        {"groups": 3},
        {"groups": None},
        {"groups": ["a", "b"], "sampling_assumption": "bad"},
        {"groups": ["a", "b"], "authority_provenance": "bad"},
        {"groups": ["a", "b"], "threshold": "bad"},
        {"groups": [["a"], "b"]},
    ],
)
def test_malformed_statistical_plan_is_a_closed_refusal_not_an_audit_exception(malformed_plan):
    req = Requirement(
        id="stat-malformed",
        source_document="Guide",
        article_clause="29 CFR 1607.4(D)",
        verbatim_text="quoted",
        stakeholder="employer",
        formalism="statistical",
        spec="selection_rate_ratio(outcome, group)",
        rationale="Measure selection rates.",
        requires=("outcome", "group"),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )
    result = evaluate_requirement(req, _StatisticalSUT(), statistical_plan=malformed_plan)
    payload = result.details["statistical_measurement"]
    assert result.verdict.value == "inconclusive" and result.strength is None
    assert payload["status"] == "refused"
    validate_measurement_payload(payload)



def test_statistical_refusal_builder_survives_hostile_plan_mappings_and_bad_atoms():
    from dataclasses import replace

    from reasonsmith.report import _evaluate_statistical_requirement

    req = replace(
        Requirement(
            id="stat-hostile",
            source_document="Guide",
            article_clause="29 CFR 1607.4(D)",
            verbatim_text="quoted",
            stakeholder="employer",
            formalism="statistical",
            spec="selection_rate_ratio(outcome, group)",
            rationale="Measure selection rates.",
            requires=("outcome", "group"),
            binding=True,
            scope="",
            domains=(),
            deontic_type="obligation",
            defeasibility="strict",
        ),
        spec="present(group)",
    )
    bad_atom = _evaluate_statistical_requirement(req, rows(), {})
    assert bad_atom.details["statistical_measurement"]["status"] == "refused"
    bad_plan_type = _evaluate_statistical_requirement(
        replace(req, spec="selection_rate_ratio(outcome, group)"), rows(), 3
    )
    assert bad_plan_type.details["statistical_measurement"]["status"] == "refused"

    class HostilePlan(dict):
        def get(self, _key, _default=None):
            raise RuntimeError("plan mapping failed")

    hostile = _evaluate_statistical_requirement(
        replace(req, spec="selection_rate_ratio(outcome, group)"), rows(), HostilePlan(groups=["a"])
    )
    assert hostile.details["statistical_measurement"]["status"] == "refused"



def test_statistical_validator_checks_optional_authority_aliases_and_threshold_shape():
    from reasonsmith.statistical import _authority_complete

    optional_none = authority()
    optional_none["official_url"] = None
    assert _authority_complete(optional_none)
    bad_scope = authority()
    bad_scope["scope"] = False
    with pytest.raises(ValueError):
        _authority_complete(bad_scope)
    measurement = measure_selection_rates(
        rows(), groups=("a", "b"), group_field="group", outcome_field="outcome"
    )
    with pytest.raises(ValueError):
        validate_measurement_payload({**measurement, "threshold": "bad"})
