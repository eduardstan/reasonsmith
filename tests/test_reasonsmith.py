"""The claims this package makes, as checks.

Nothing here asserts wording, branding or presentation. Where a check needs a disclosure to be
present it asserts that the module's own constant appears, not what that constant says.
"""

import pytest
from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.ir import Atom, GroundProgram, Rule
from nesyarena.suts import ExactWMC, TopK, proof_score

from reasonsmith import certificate, conformance, evidence

from reasonsmith.certificate import certify
from reasonsmith.demo import (
    CREDIT_QUERY,
    CREDIT_REASONS,
    MiscalibratedAdapter,
    SilentDropAdapter,
    build_case,
    certify_case,
    design_a,
    design_b,
    main,
)

# ------------------------------------------------------------------ schema ----


def test_schema_is_the_six_rows_of_table_7():
    assert len(evidence.DUTIES) == 6
    assert sorted(d["table7_row"] for d in evidence.DUTIES.values()) == [1, 2, 3, 4, 5, 6]
    assert {d["legal_source"] for d in evidence.DUTIES.values()} == {
        "EU AI Act Art. 13",
        "EU AI Act Art. 12",
        "GDPR Art. 22 (and Rec. 71)",
        "ECOA / Reg B (12 CFR 1002.9)",
        "FDA GMLP; agency transparency guidance",
        "NIST AI RMF 1.0",
    }


def test_every_schema_entry_traces_to_the_table():
    """Each duty names its row, and each evidence key carries the verbatim cell text it stands for,
    so the schema can be checked against the printed table without the PDF."""
    report = evidence.traceability_report()
    for duty in evidence.DUTIES.values():
        assert duty["symbolic_artifacts"] and duty["lifecycle_placement"]
        keys = [f["key"] for f in duty["evidence_field"]]
        assert len(keys) == len(set(keys))
        for f in duty["evidence_field"]:
            assert f["table7_text"].strip()
            assert f["table7_text"] in report
            assert f["key"] in report


# ---------------------------------------------------------------- emitter ----

ECOA = "ecoa_reg_b_adverse_action"
FULL = {
    "stored_reasons_per_decision": "C01 — Income insufficient",
    "model_version": "v1",
    "score_factors": "C01 0.87",
    "audit_ids": "AAN-1",
    "retention_for_regulatory_lookback": "25 months",
}


def test_complete_record_is_complete():
    rec = evidence.emit(ECOA, "APP-1", FULL)
    assert rec.complete and rec.missing == ()


def test_withheld_field_is_reported_incomplete_and_named():
    withheld = {k: v for k, v in FULL.items() if k != "audit_ids"}
    rec = evidence.emit(ECOA, "APP-1", withheld)
    assert not rec.complete
    assert rec.missing == ("audit_ids",)
    assert any(line.startswith("audit_ids") for line in rec.missing_report())
    assert "audit_ids" in rec.render()


def test_blank_and_none_are_missing_not_present():
    for bad in (None, "", "   "):
        rec = evidence.emit(ECOA, "APP-1", {**FULL, "audit_ids": bad})
        assert rec.missing == ("audit_ids",)


def test_field_outside_the_row_is_rejected():
    with pytest.raises(ValueError):
        evidence.emit(ECOA, "APP-1", {**FULL, "vibes": "good"})


def test_attachments_do_not_fill_a_gap():
    withheld = {k: v for k, v in FULL.items() if k != "audit_ids"}
    rec = evidence.emit(ECOA, "APP-1", withheld, attachments={"audit_ids": "AAN-1"})
    assert not rec.complete and rec.missing == ("audit_ids",)


def test_every_record_carries_its_limits():
    for rec in (evidence.emit(ECOA, "APP-1", FULL),
                evidence.emit(ECOA, "APP-1", {})):
        assert evidence.LIMITS in rec.render()


def test_unknown_duty_is_refused():
    with pytest.raises(KeyError):
        evidence.emit("eu_ai_act_art_99", "APP-1", {})


# ------------------------------------------------------------ certificate ----


def credit_case():
    return build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)


def test_exact_inference_certifies_clean():
    cert = certify_case(credit_case(), ReferenceAdapter(ExactWMC()))
    assert cert.verdict == "PASS"
    assert len(cert.live) == len(CREDIT_REASONS)
    assert cert.deleted == []


def test_top_k_deletes_reasons_and_the_certificate_names_them():
    case = credit_case()
    cert = certify_case(case, ReferenceAdapter(TopK(1)))
    assert cert.verdict == "FAIL"
    assert len(cert.live) == 1
    assert len(cert.deleted) == len(CREDIT_REASONS) - 1

    # the deleted set is exactly the reasons top-1 discards: everything but the best-scoring proof
    ranked = sorted(case.program.proof_supports(case.query, 1),
                    key=lambda pr: -proof_score(pr, case.base))
    assert {v.reason for v in cert.deleted} == set(ranked[1:])
    assert set(cert.missing_reasons()) == {case.labels[r] for r in ranked[1:]}


def test_exact_inference_recovers_what_top_k_dropped():
    case = credit_case()
    dropped = set(certify_case(case, ReferenceAdapter(TopK(1))).missing_reasons())
    recovered = {v.label for v in certify_case(case, ReferenceAdapter(ExactWMC())).live}
    assert dropped and dropped <= recovered


def test_both_domains_lose_reasons_under_top_k():
    from reasonsmith.demo import CLINICAL_QUERY, CLINICAL_REASONS

    for pred, reasons in ((CREDIT_QUERY, CREDIT_REASONS), (CLINICAL_QUERY, CLINICAL_REASONS)):
        case = build_case("SUB-1", "typical", pred, reasons, 0.86)
        cert = certify_case(case, ReferenceAdapter(TopK(1)))
        assert len(cert.deleted) == len(reasons) - 1
        assert certify_case(case, ReferenceAdapter(ExactWMC())).verdict == "PASS"


def test_a_perturbed_engine_that_drops_a_reason_fails():
    cert = certify_case(credit_case(), SilentDropAdapter())
    assert cert.verdict == "FAIL"
    assert len(cert.deleted) == 1


def test_a_perturbed_engine_that_keeps_every_reason_still_fails_on_value():
    cert = certify_case(credit_case(), MiscalibratedAdapter())
    assert cert.verdict == "FAIL"
    assert cert.deleted == []           # the deletion probe alone would clear it
    assert abs(cert.value_gap) > cert.tol   # the value check is what catches it


def test_certificate_carries_its_limits():
    from reasonsmith import certificate

    assert certificate.LIMITS in certify_case(credit_case(), ReferenceAdapter(TopK(1))).render()


# ----------------------------------------- what the probe cannot certify ----


def test_a_reason_with_no_private_fact_is_not_certified_either_way():
    q, a, b, c = Atom("q"), Atom("a"), Atom("b"), Atom("c")
    program = GroundProgram((Rule(q, (a, b)), Rule(q, (a, b, c))))
    base = {a: 0.6, b: 0.5, c: 0.4}
    cert = certify(program, base, q, ReferenceAdapter(ExactWMC()), exact_depth=1)
    statuses = {frozenset(v.reason): v.status for v in cert.verdicts}
    assert statuses[frozenset({a, b})] == "unseparable"
    assert cert.verdict == "INCONCLUSIVE"   # never silently upgraded to PASS


def unmeasured_cert():
    """A certificate for a query exact inference finds no reason for: nothing was probed."""
    program = GroundProgram((Rule(Atom("q", ("APP-1",)), (Atom("a", ("APP-1",)),)),))
    return certify(program, {Atom("a", ("APP-1",)): 0.6}, Atom("q", ("APP-9999",)),
                   ReferenceAdapter(ExactWMC()), exact_depth=1)


def test_a_query_with_no_reason_is_never_a_pass():
    """Nothing enumerated means nothing probed and nothing compared, which is not a clean bill."""
    cert = unmeasured_cert()
    assert cert.verdicts == ()
    assert cert.verdict == "INCONCLUSIVE"


def test_an_engine_answer_with_no_enumerated_reason_is_attributed_to_the_gap():
    """The nothing-was-compared attribution must not sit under a header reporting a value gap."""
    case = credit_case()
    cert = certify(case.program, case.base, case.query, ReferenceAdapter(ExactWMC()),
                   exact_depth=0, labels=case.labels)
    assert cert.verdicts == ()
    assert abs(cert.value_gap) > cert.tol and cert.verdict == "FAIL"
    assert cert.attribution != unmeasured_cert().attribution


def test_no_check_scores_a_certificate_that_measured_nothing():
    """One predicate gates every metric, so not-checked cannot score as checked-and-sound."""
    cert = unmeasured_cert()
    assert not conformance.measured(cert)
    for metric in (conformance.fidelity, conformance.retained_share, conformance.coverage,
                   conformance.reason_set_size):
        assert metric(cert) is None
    assert conformance.reason_diversity([cert]) is None
    assert conformance.stability([cert]) is None
    stats = conformance.group_stats([cert])
    assert stats["n"] == 1 and stats["measured"] == 0
    assert all(v is None for k, v in stats.items() if k not in ("n", "measured"))


def test_an_unmeasured_group_never_wins_the_per_group_comparison():
    s = conformance.stratified({"real": [certify_case(credit_case(), ReferenceAdapter(TopK(1)))],
                                "unprovable": [unmeasured_cert()]})
    assert s["per_group"]["unprovable"]["fidelity"] is None
    assert s["per_group"]["unprovable"]["retained_share"] is None
    assert all(g["best"] != "unprovable" for g in s["gaps"].values())
    assert all(g["gap"] is None for g in s["gaps"].values())   # one measured group is no comparison
    conformance.render(s, size_cap=3)


def test_a_gap_needs_two_groups_that_produced_the_metric():
    one = {"typical": [certify_case(credit_case(), ReferenceAdapter(TopK(1)))]}
    assert all(g["gap"] is None for g in conformance.stratified(one)["gaps"].values())


def test_an_all_empty_cohort_reports_nothing_to_measure():
    s = conformance.stratified({"typical": [], "atypical": []})
    assert s["per_group"]["typical"]["n"] == 0
    assert s["per_group"]["typical"]["coverage"] is None
    assert all(g["gap"] is None for g in s["gaps"].values())
    conformance.render(s, size_cap=3)


def test_a_probe_with_no_signal_is_not_counted_as_live():
    q, a, b = Atom("q"), Atom("a"), Atom("b")
    program = GroundProgram((Rule(q, (a,)), Rule(q, (b,))))
    cert = certify(program, {a: 0.6, b: 0.0}, q, ReferenceAdapter(ExactWMC()), exact_depth=1)
    statuses = {frozenset(v.reason): v.status for v in cert.verdicts}
    assert statuses[frozenset({b})] == "inconclusive"
    assert cert.verdict == "INCONCLUSIVE"


# ------------------------------------------------------------ conformance ----


def strat(groups):
    topk = ReferenceAdapter(TopK(1))
    return conformance.stratified(
        {g: [certify_case(c, topk) for c in cases] for g, cases in groups.items()})


def test_registered_hypothesis_confidence_form_is_not_supported():
    """Varying confidence alone costs no reasons: coverage is flat, and the harm shows up only in
    the value metrics. Pinned so the negative result cannot drift away unnoticed."""
    s = strat(design_a("APP", CREDIT_QUERY, CREDIT_REASONS))
    assert s["gaps"]["coverage"]["gap"] == pytest.approx(0.0)
    assert s["gaps"]["retained_share"]["gap"] > 0.1
    assert s["gaps"]["retained_share"]["worst"] == "atypical"


def test_registered_hypothesis_multiplicity_form_is_supported():
    s = strat(design_b("APP", CREDIT_QUERY, CREDIT_REASONS))
    assert s["gaps"]["coverage"]["gap"] > 0.2
    assert s["gaps"]["coverage"]["worst"] == "atypical"


def test_coverage_and_fidelity_agree_with_the_certificate():
    cert = certify_case(credit_case(), ReferenceAdapter(TopK(1)))
    assert conformance.coverage(cert) == pytest.approx(1 / len(CREDIT_REASONS))
    assert conformance.reason_set_size(cert) == 1
    assert conformance.fidelity(cert) == pytest.approx(1 - abs(cert.value_gap))
    clean = certify_case(credit_case(), ReferenceAdapter(ExactWMC()))
    assert conformance.coverage(clean) == 1.0
    assert conformance.fidelity(clean) == pytest.approx(1.0)


def test_drift_moves_the_stated_reason_and_stability_reports_it():
    topk = ReferenceAdapter(TopK(1))
    certs = []
    for w in range(4):
        case = credit_case()
        base = {a: (round(min(0.99, p + 0.06 * w), 4)
                    if a.pred in ("delinquency_on_file", "bureau_record_matched") else p)
                for a, p in case.base.items()}
        certs.append(certify(case.program, base, case.query, topk, exact_depth=1,
                             labels=case.labels))
    assert len({frozenset(v.label for v in c.live) for c in certs}) > 1
    assert conformance.stability(certs) < 1.0
    assert conformance.stability(certs[:1]) == 1.0


def test_score_factors_are_the_measured_scores_or_absent():
    """The record's score factors are read off the certificate, never asserted beside it."""
    from reasonsmith.demo import score_factors

    cert = certify_case(credit_case(), ReferenceAdapter(TopK(1)))
    stated = [float(tok.split()[-1]) for tok in score_factors(cert).split(";")]
    assert stated == pytest.approx(sorted((v.score for v in cert.verdicts), reverse=True), abs=1e-4)

    program = GroundProgram((Rule(Atom("q", ("APP-1",)), (Atom("a", ("APP-1",)),)),))
    empty = certify(program, {Atom("a", ("APP-1",)): 0.6}, Atom("q", ("APP-9999",)),
                    ReferenceAdapter(ExactWMC()), exact_depth=1)
    assert score_factors(empty) is None
    record = evidence.emit(ECOA, "APP-9999", {**FULL, "score_factors": score_factors(empty)})
    assert record.missing == ("score_factors",)


def test_the_whole_report_runs():
    assert len(main()) > 5000


# ------------------------------------------------------------ json output ----


def test_record_json_roundtrip_preserves_incomplete_status_and_missing_fields():
    import json

    withheld = {k: v for k, v in FULL.items() if k != "audit_ids"}
    rec = evidence.emit(ECOA, "APP-1", withheld)

    dict_data = rec.to_dict()
    assert dict_data["status"] == "INCOMPLETE"
    assert dict_data["complete"] is False
    assert dict_data["missing"] == ["audit_ids"]
    assert any(m.startswith("audit_ids") for m in dict_data["missing_report"])
    assert evidence.LIMITS == dict_data["limits"]

    json_str = rec.to_json(indent=2)
    loaded = json.loads(json_str)
    assert loaded["status"] == "INCOMPLETE"
    assert loaded["complete"] is False
    assert loaded["missing"] == ["audit_ids"]
    assert loaded["limits"] == evidence.LIMITS


def test_certificate_json_roundtrip_preserves_verdict_and_reasons():
    import json

    case = credit_case()
    cert = certify_case(case, ReferenceAdapter(TopK(1)))

    dict_data = cert.to_dict()
    assert dict_data["verdict"] == "FAIL"
    assert len(dict_data["missing_reasons"]) > 0
    assert len(dict_data["verdicts"]) == len(cert.verdicts)
    assert "limits" in dict_data

    json_str = cert.to_json()
    loaded = json.loads(json_str)
    assert loaded["verdict"] == "FAIL"
    assert loaded["missing_reasons"] == cert.missing_reasons()
    assert loaded["limits"] == certificate.LIMITS


