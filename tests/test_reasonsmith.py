"""The claims this package makes, as checks.

Nothing here asserts branding or presentation. Disclosure checks normally assert that the module's
constant travels with its artifact; the compliance-boundary test pins the constant's semantics.
"""

import json

import pytest
from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.ir import Atom, GroundProgram, Rule
from nesyarena.suts import ExactWMC, TopK, proof_score

from reasonsmith import certificate, conformance, evidence
from reasonsmith.certificate import certify
from reasonsmith.demo import (
    CLINICAL_QUERY,
    CLINICAL_REASONS,
    CREDIT_QUERY,
    CREDIT_REASONS,
    DRIFT_SIGNALS,
    NIST_THRESHOLDS,
    MiscalibratedAdapter,
    SilentDropAdapter,
    art12_event_log,
    art12_evidence_fields,
    art13_evidence_fields,
    build_case,
    certify_case,
    design_a,
    design_b,
    drift_windows,
    fda_evidence_fields,
    main,
    nist_evidence_fields,
    threshold_alerts,
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


def test_certificate_limits_exclude_compliance_certification():
    assert "not a compliance guarantee and is not legal advice" in certificate.LIMITS
    assert "does not certify the engine on any other input" in certificate.LIMITS


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


def test_record_json_cites_the_table_7_row_the_human_output_cites():
    rec = evidence.emit(ECOA, "APP-1", FULL)
    row = evidence.duty(ECOA)["table7_row"]
    assert rec.to_dict()["table7_row"] == row
    assert json.loads(rec.to_json())["table7_row"] == row


def test_record_json_stringifies_values_json_has_no_type_for():
    rec = evidence.emit(ECOA, "APP-1", {**FULL, "audit_ids": {"a", "b"}},
                        attachments={"model": object()})
    loaded = json.loads(rec.to_json())
    assert loaded["fields"]["audit_ids"] == str(rec.fields["audit_ids"])
    assert loaded["attachments"]["model"] == str(rec.attachments["model"])


def test_record_dict_does_not_hand_out_the_module_schema_to_mutate():
    rec = evidence.emit(ECOA, "APP-1", FULL)
    payload = rec.to_dict()
    payload["table7_source"]["paper"] = "REDACTED"
    payload["table7_source"]["columns"].append("invented")
    payload["symbolic_artifacts"].append("invented")
    payload["lifecycle_placement"].clear()

    assert rec.to_dict() == evidence.emit(ECOA, "APP-1", FULL).to_dict()
    assert evidence.SOURCE["paper"] != "REDACTED"
    assert "invented" not in evidence.SOURCE["columns"]
    assert "invented" not in evidence.duty(ECOA)["symbolic_artifacts"]
    assert evidence.duty(ECOA)["lifecycle_placement"]


def test_certificate_json_roundtrip_preserves_verdict_and_reasons():
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


# ------------------------------------ EU AI Act Art. 13 (Table 7 row 1) ----


def art13_case_and_cert(adapter):
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    return case, certify_case(case, adapter)


def test_art13_metrics_field_is_measured_not_claimed():
    case, cert = art13_case_and_cert(ReferenceAdapter(TopK(1)))
    metrics = art13_evidence_fields(case, cert)["fidelity_coverage_metrics"]
    assert f"{conformance.fidelity(cert):.4f}" in metrics
    assert f"{conformance.coverage(cert):.4f}" in metrics


def test_art13_record_is_complete_and_discloses_the_topk_gap():
    """Form and content part ways: every row-1 field is produced, and the produced numbers
    themselves report that the deployed engine states one reason of five."""
    case, cert = art13_case_and_cert(ReferenceAdapter(TopK(1)))
    record = evidence.emit("eu_ai_act_art13_transparency", case.case_id,
                           art13_evidence_fields(case, cert))
    assert record.complete
    assert conformance.coverage(cert) == pytest.approx(1 / len(CREDIT_REASONS))


def test_art13_exact_inference_reports_full_coverage():
    case, cert = art13_case_and_cert(ReferenceAdapter(ExactWMC()))
    assert conformance.coverage(cert) == 1.0
    assert conformance.fidelity(cert) == 1.0
    assert "1.0000" in art13_evidence_fields(case, cert)["fidelity_coverage_metrics"]


# ------------------------------------ EU AI Act Art. 12 (Table 7 row 2) ----


def art12_case_and_cert(adapter):
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    return case, certify_case(case, adapter)


def test_art12_log_records_the_chosen_branch_and_the_full_active_set():
    """The entry names the branch the engine chose and every constraint exact inference found
    active — the active-but-unused set is the part an answer-only log would lose."""
    case, cert = art12_case_and_cert(ReferenceAdapter(TopK(1)))
    log = art12_event_log(case, cert)
    assert "chosen branch/module: C01" in log
    for code, _text, _facts in CREDIT_REASONS:
        assert code in log                       # the whole active set, not just the choice
    assert f"{len(cert.deleted)} (recorded here" in log


def test_art12_hashes_are_deterministic_across_runs():
    """Two independently built runs of the same frozen decision produce byte-identical log
    entries, and the digests match the values recorded when the demo was written — a changed
    hash or a leaked timestamp breaks this test."""
    case_a, cert_a = art12_case_and_cert(ReferenceAdapter(TopK(1)))
    case_b, cert_b = art12_case_and_cert(ReferenceAdapter(TopK(1)))
    log_a, log_b = art12_event_log(case_a, cert_a), art12_event_log(case_b, cert_b)
    assert log_a == log_b
    assert "input sha256:673a324cc571" in log_a
    assert "output sha256:43b08d429368" in log_a


def test_art12_record_is_complete_with_log_from_certificate():
    case, cert = art12_case_and_cert(ReferenceAdapter(TopK(1)))
    record = evidence.emit("eu_ai_act_art12_record_keeping", case.case_id,
                           art12_evidence_fields(case, cert))
    assert record.complete


# ------------------------------------------ FDA GMLP (Table 7 row 5) ----


def fda_case_and_certs():
    case = build_case("PT-0731", "typical", CLINICAL_QUERY, CLINICAL_REASONS, 0.86)
    return (case,
            certify_case(case, ReferenceAdapter(TopK(1))),
            certify_case(case, ReferenceAdapter(ExactWMC())))


def test_fda_design_history_chain_links_requirement_test_and_artifact():
    case, cert_deployed, cert_exact = fda_case_and_certs()
    links = fda_evidence_fields(case, cert_deployed, cert_exact)["design_history_links"]
    assert "REQ-TRIAGE-07" in links
    assert "VER-TRIAGE-07" in links
    assert case.case_id in links                       # the artifact is this decision's certificate
    assert cert_deployed.verdict in links              # filed with its real verdict, not a pass


def test_fda_verification_log_carries_both_measured_verdicts():
    case, cert_deployed, cert_exact = fda_case_and_certs()
    log = fda_evidence_fields(case, cert_deployed, cert_exact)["verification_logs"]
    assert cert_deployed.verdict == "FAIL"
    assert cert_exact.verdict == "PASS"
    assert "verdict FAIL" in log and "verdict PASS" in log


def test_fda_record_is_complete_with_verdicts_from_certificates():
    case, cert_deployed, cert_exact = fda_case_and_certs()
    record = evidence.emit("fda_gmlp_samd", case.case_id,
                           fda_evidence_fields(case, cert_deployed, cert_exact))
    assert record.complete


# ------------------------------------------------ NIST AI RMF (Table 7 row 6) ----


def nist_windows(adapter):
    return drift_windows("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88,
                         DRIFT_SIGNALS, 6, adapter)


def test_stability_alert_fires_when_drift_replaces_the_stated_reason():
    certs = nist_windows(ReferenceAdapter(TopK(1)))
    stated = {tuple(v.label for v in c.live) for c in certs}
    assert len(stated) > 1                                   # the stated reason really changed
    alerts = {a["metric"]: a for a in threshold_alerts(certs, NIST_THRESHOLDS)}
    assert alerts["coverage"]["window"] == 0            # top-1 was under the floor from the start
    assert alerts["coverage"]["value"] == pytest.approx(1 / len(CREDIT_REASONS))
    assert alerts["stability"]["window"] == 2           # drift swaps the stated reason at window 2
    # the alert carries the value actually measured, not a restated one
    assert alerts["stability"]["value"] == conformance.stability(certs[:3])


def test_an_engine_within_the_floors_raises_no_alert():
    certs = nist_windows(ReferenceAdapter(ExactWMC()))
    assert all(conformance.coverage(c) == 1.0 for c in certs)
    assert conformance.stability(certs) == 1.0
    assert threshold_alerts(certs, NIST_THRESHOLDS) == []


def test_nist_record_is_incomplete_on_the_sign_off_it_cannot_produce():
    """A frozen synthetic run has no reviewer: reviews_and_sign_offs is reported NOT PRODUCED,
    never filled with a simulated signature."""
    certs = nist_windows(ReferenceAdapter(TopK(1)))
    fields = nist_evidence_fields(certs, threshold_alerts(certs, NIST_THRESHOLDS), NIST_THRESHOLDS)
    rec = evidence.emit("nist_ai_rmf_risk_evidence", "APP-1042", fields)
    assert rec.status == "INCOMPLETE"
    assert rec.missing == ("reviews_and_sign_offs",)
    assert "NOT PRODUCED" in rec.render()
