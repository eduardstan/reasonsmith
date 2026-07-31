# Example Output

Every block below is stdout pasted unedited from a real run, not a hand-written illustration of
what the tool would print. Regenerate any block by running the command shown above it.

- **Captured at:** commit `ea4bf3711abbd6922dcf4f1448cb177807bbe3d6` (branch `fm/rs-readable-repo`)
- **Environment:** Python 3.12.9, Linux, `nesyarena` at the commit `pyproject.toml` pinned when
  these transcripts were captured (`57720fa212834689692e171882272140f1d1fed7`); re-run since
  against the PyPI release `nesyarena==0.1.0` now pinned, byte-for-byte identical
- **Demo transcript:** 561 lines, `md5sum` `c5976971e24a86886f1e0ad54f0b9ce9` — the same length and
  hash [RESULTS.md](../RESULTS.md) reports, which is what lets the two files be checked against
  each other

What a transcript is not: a compliance result. Each block carries its own LIMITS paragraph, and
those limits travel with the numbers above them.

---

## 1. Demonstration Output

```sh
python -m reasonsmith.demo
```

```text

====================================================================================================
0. TRACEABILITY — every schema entry against the Table 7 text it came from
====================================================================================================

Table 7. Checklist that ties symbolic artifacts to legal/assurance duties and the associated logging.
Symbols and Neurons: A Review of Symbolic XAI in Deep Learning — Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
Section 5.3 Alignment with Regulatory and Governance Requirements, p. 36:22. Columns: Requirement, Legal source, Symbolic artifact(s) to provide, Minimal evidence to retain, Where it fits.

row 1: eu_ai_act_art13_transparency
  Requirement                     : Transparency and information to deployers
  Legal source                    : EU AI Act Art. 13
  Symbolic artifact(s) to provide : Rule lists/decision paths; clause truth-value tables; KG path rationales; constraint compliance summaries
  Minimal evidence to retain      :
      model_and_data_version_ids             <- Model and data version IDs
      extraction_timestamp                   <- extraction timestamp
      dataset_snapshot_hash                  <- dataset snapshot hash
      fidelity_coverage_metrics              <- fidelity/coverage metrics
      explanation_scope                      <- explanation scope
      linkage_from_decision_to_artifact      <- linkage from decision to artifact
  Where it fits                   : Technical documentation (Art. 11); user information package; conformity/assurance file

row 2: eu_ai_act_art12_record_keeping
  Requirement                     : Record–keeping (event logging)
  Legal source                    : EU AI Act Art. 12
  Symbolic artifact(s) to provide : Per-decision traces (activated rules, tree paths, module layouts); constraint satisfaction/violation records
  Minimal evidence to retain      :
      automatic_event_logs                   <- Automatic event logs (timestamp, input/output hashes, chosen branch/module, violated/active constraints)
      retention_schedule                     <- retention schedule
      signer                                 <- signer
  Where it fits                   : Logging subsystem; post-market monitoring; quality management system

row 3: gdpr_art22_meaningful_information
  Requirement                     : Automated decisions: “meaningful information about the logic involved”
  Legal source                    : GDPR Art. 22 (and Rec. 71)
  Symbolic artifact(s) to provide : Human-readable rule summaries; monotonicity statements; concept/ontology flow graphs; rationale templates
  Minimal evidence to retain      :
      per_decision_reason_string             <- Per-decision reason string referencing rule(s)/constraint(s)
      feature_to_named_concept_mapping       <- mapping from model features to named concepts
      dpia_cross_reference                   <- DPIA cross-reference
  Where it fits                   : Data protection impact assessment (DPIA); user-facing notices; model cards

row 4: ecoa_reg_b_adverse_action
  Requirement                     : Adverse action reasons in credit decisions
  Legal source                    : ECOA / Reg B (12 CFR 1002.9)
  Symbolic artifact(s) to provide : Rule-based “reason codes” mapped to standardized categories; monotone/eligibility constraints for fairness explanations
  Minimal evidence to retain      :
      stored_reasons_per_decision            <- Stored reasons per decision
      model_version                          <- model version
      score_factors                          <- score factors
      audit_ids                              <- audit IDs
      retention_for_regulatory_lookback      <- retention for regulatory lookback
  Where it fits                   : Adverse action notice (AAN) pipeline; compliance reporting

row 5: fda_gmlp_samd
  Requirement                     : Good ML Practice/transparency for SaMD
  Legal source                    : FDA GMLP; agency transparency guidance
  Symbolic artifact(s) to provide : Explainability specification; constraint definitions tied to hazards; proof/trace exemplars (e.g., clause activations)
  Minimal evidence to retain      :
      design_history_links                   <- Design history links from requirement to test to artifact
      verification_logs                      <- verification logs
      change_control                         <- change control (e.g., PCCP)
  Where it fits                   : Design history file; quality system records; post-market surveillance

row 6: nist_ai_rmf_risk_evidence
  Requirement                     : Risk evidence and continuous monitoring
  Legal source                    : NIST AI RMF 1.0
  Symbolic artifact(s) to provide : Risk evidence register: explanation coverage and stability metrics; constraint dashboards; rule drift reports
  Minimal evidence to retain      :
      continuous_monitoring_logs             <- Continuous monitoring logs
      metric_thresholds_and_alerts           <- metric thresholds and alerts
      reviews_and_sign_offs                  <- reviews and sign-offs
      incident_tickets                       <- incident tickets
  Where it fits                   : RMF Govern–Map–Measure–Manage artifacts; model registry

====================================================================================================
1. CREDIT — ECOA / Reg B (12 CFR 1002.9), Table 7 row 4
====================================================================================================

The deployed engine keeps the single best proof.

REASON-DELETION CERTIFICATE [FAIL]
query: adverse_action(APP-1042)
engine: reference:top-1-proofs   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991399   engine value 0.765600   gap -0.225799   tolerance 1e-09
reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable

  [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                    facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                    deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.068400: the engine's answer depends on this reason.
  [        DELETED] C02 — Length of time credit has been established is too short  (score 0.697200)
                    facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                    deleting file_thin(APP-1042) moves exact inference by -0.019804 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] C03 — Delinquent past or present credit obligations  (score 0.632000)
                    facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                    deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                    facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                    deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] C05 — Insufficient number of credit references provided  (score 0.511200)
                    facts: application_complete(APP-1042), references_under_policy(APP-1042)
                    deleting application_complete(APP-1042) moves exact inference by -0.008995 but leaves the engine unchanged: the engine's answer does not depend on this reason.

MISSING REASONS: the engine's answer does not depend on 4 reason(s) that exact inference found:
  - C02 — Length of time credit has been established is too short: file_thin(APP-1042), history_under_24_months(APP-1042)
  - C03 — Delinquent past or present credit obligations: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
  - C04 — Too many recent inquiries on credit bureau report: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
  - C05 — Insufficient number of credit references provided: application_complete(APP-1042), references_under_policy(APP-1042)

ATTRIBUTION: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.225799.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

Exact inference on the same program and the same base interpretation recovers every one of them:

REASON-DELETION CERTIFICATE [PASS]
query: adverse_action(APP-1042)
engine: reference:exact-wmc   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991399   engine value 0.991399   gap +0.000000   tolerance 1e-09
reasons: 5 found by exact inference, 5 used by the engine, 0 deleted, 0 not certifiable

  [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                    facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                    deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.028093: the engine's answer depends on this reason.
  [           used] C02 — Length of time credit has been established is too short  (score 0.697200)
                    facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                    deleting file_thin(APP-1042) moves exact inference by -0.019804 and the engine by -0.019804: the engine's answer depends on this reason.
  [           used] C03 — Delinquent past or present credit obligations  (score 0.632000)
                    facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                    deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 and the engine by -0.005262: the engine's answer depends on this reason.
  [           used] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                    facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                    deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 and the engine by -0.004166: the engine's answer depends on this reason.
  [           used] C05 — Insufficient number of credit references provided  (score 0.511200)
                    facts: application_complete(APP-1042), references_under_policy(APP-1042)
                    deleting application_complete(APP-1042) moves exact inference by -0.008995 and the engine by -0.008995: the engine's answer depends on this reason.

ATTRIBUTION: The engine used every reason exact inference found, and its value matched the exact value within tolerance. No inference setting is implicated on this input.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

The adverse action notice pipeline emits its Table 7 record:

EVIDENCE RECORD [COMPLETE]
decision: APP-1042
duty: Adverse action reasons in credit decisions
legal source: ECOA / Reg B (12 CFR 1002.9)
source of the duty: Table 7 (row 4, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Rule-based “reason codes” mapped to standardized categories; monotone/eligibility constraints for fairness explanations
where it fits: Adverse action notice (AAN) pipeline; compliance reporting

minimal evidence retained:
  [x] stored_reasons_per_decision (Stored reasons per decision):
          C01 — Income insufficient for amount of credit requested
  [x] model_version (model version):
        credit-scoring-2026.03.1 / rules cs-rules-2026.03
  [x] score_factors (score factors):
        C01 0.7656; C02 0.6972; C03 0.6320; C04 0.6004; C05 0.5112
  [x] audit_ids (audit IDs):
        AAN-2026-0731-1042 / trace-9f3c1b
  [x] retention_for_regulatory_lookback (retention for regulatory lookback):
        25 months from notice date, per lender policy

supporting material (NOT Table 7 evidence, and fills no gap above):
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: adverse_action(APP-1042)
    engine: reference:top-1-proofs   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991399   engine value 0.765600   gap -0.225799   tolerance 1e-09
    reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable
    
      [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                        facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                        deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.068400: the engine's answer depends on this reason.
      [        DELETED] C02 — Length of time credit has been established is too short  (score 0.697200)
                        facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                        deleting file_thin(APP-1042) moves exact inference by -0.019804 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] C03 — Delinquent past or present credit obligations  (score 0.632000)
                        facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                        deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                        facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                        deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] C05 — Insufficient number of credit references provided  (score 0.511200)
                        facts: application_complete(APP-1042), references_under_policy(APP-1042)
                        deleting application_complete(APP-1042) moves exact inference by -0.008995 but leaves the engine unchanged: the engine's answer does not depend on this reason.
    
    MISSING REASONS: the engine's answer does not depend on 4 reason(s) that exact inference found:
      - C02 — Length of time credit has been established is too short: file_thin(APP-1042), history_under_24_months(APP-1042)
      - C03 — Delinquent past or present credit obligations: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
      - C04 — Too many recent inquiries on credit bureau report: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
      - C05 — Insufficient number of credit references provided: application_complete(APP-1042), references_under_policy(APP-1042)
    
    ATTRIBUTION: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.225799.
    
    LIMITS OF THIS CERTIFICATE
      This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

LIMITS OF THIS RECORD
  This record is not a compliance guarantee and is not legal advice. It reproduces the minimal evidence fields that one peer-reviewed review (Table 7 of the source named above) associates with the cited duty. Whether those fields discharge the duty, and whether the values supplied for them are accurate, are determinations this tool does not make and cannot make.

Read those two together. The record is COMPLETE — every field Table 7 lists for row 4 was produced.
The certificate says the stored reasons are not all the reasons. Table 7 completeness is a check on the
form of the record, not on the truth of what it contains; under 12 CFR 1002.9 the notice must state the
specific principal reasons, and 4 of 5 are absent from this one.

Withholding one required field — the audit IDs — is refused loudly rather than papered over:

EVIDENCE RECORD [INCOMPLETE]
decision: APP-1042
duty: Adverse action reasons in credit decisions
legal source: ECOA / Reg B (12 CFR 1002.9)
source of the duty: Table 7 (row 4, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Rule-based “reason codes” mapped to standardized categories; monotone/eligibility constraints for fairness explanations
where it fits: Adverse action notice (AAN) pipeline; compliance reporting

minimal evidence retained:
  [x] stored_reasons_per_decision (Stored reasons per decision):
          C01 — Income insufficient for amount of credit requested
  [x] model_version (model version):
        credit-scoring-2026.03.1 / rules cs-rules-2026.03
  [x] score_factors (score factors):
        C01 0.7656; C02 0.6972; C03 0.6320; C04 0.6004; C05 0.5112
  [ ] audit_ids (audit IDs): NOT PRODUCED
  [x] retention_for_regulatory_lookback (retention for regulatory lookback):
        25 months from notice date, per lender policy

INCOMPLETE: 1 of 5 required fields could not be produced. This record does not carry the minimal evidence Table 7 specifies for this duty. Missing:
  - audit_ids — audit IDs

LIMITS OF THIS RECORD
  This record is not a compliance guarantee and is not legal advice. It reproduces the minimal evidence fields that one peer-reviewed review (Table 7 of the source named above) associates with the cited duty. Whether those fields discharge the duty, and whether the values supplied for them are accurate, are determinations this tool does not make and cannot make.

====================================================================================================
2. CLINICAL — GDPR Art. 22 and Rec. 71, Table 7 row 3
====================================================================================================

REASON-DELETION CERTIFICATE [FAIL]
query: withhold_fast_track(PT-0731)
engine: reference:top-1-proofs   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991424   engine value 0.731000   gap -0.260424   tolerance 1e-09
reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable

  [           used] H01 — Comorbidity burden above the fast-track ceiling  (score 0.731000)
                    facts: comorbidity_index_high(PT-0731), history_coded(PT-0731)
                    deleting comorbidity_index_high(PT-0731) moves exact inference by -0.023306 and the engine by -0.066800: the engine's answer depends on this reason.
  [        DELETED] H02 — Renal function below the protocol floor  (score 0.664200)
                    facts: egfr_below_floor(PT-0731), labs_within_window(PT-0731)
                    deleting egfr_below_floor(PT-0731) moves exact inference by -0.016964 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] H03 — Interacting medication on the active list  (score 0.600600)
                    facts: interacting_drug_active(PT-0731), medication_list_current(PT-0731)
                    deleting interacting_drug_active(PT-0731) moves exact inference by -0.012897 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] H04 — Vital-sign instability in the observation window  (score 0.540200)
                    facts: monitoring_continuous(PT-0731), vitals_unstable(PT-0731)
                    deleting monitoring_continuous(PT-0731) moves exact inference by -0.010076 but leaves the engine unchanged: the engine's answer does not depend on this reason.
  [        DELETED] H05 — Imaging finding outside the automated-review scope  (score 0.483000)
                    facts: imaging_finding_out_of_scope(PT-0731), imaging_reported(PT-0731)
                    deleting imaging_finding_out_of_scope(PT-0731) moves exact inference by -0.008012 but leaves the engine unchanged: the engine's answer does not depend on this reason.

MISSING REASONS: the engine's answer does not depend on 4 reason(s) that exact inference found:
  - H02 — Renal function below the protocol floor: egfr_below_floor(PT-0731), labs_within_window(PT-0731)
  - H03 — Interacting medication on the active list: interacting_drug_active(PT-0731), medication_list_current(PT-0731)
  - H04 — Vital-sign instability in the observation window: monitoring_continuous(PT-0731), vitals_unstable(PT-0731)
  - H05 — Imaging finding outside the automated-review scope: imaging_finding_out_of_scope(PT-0731), imaging_reported(PT-0731)

ATTRIBUTION: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.260424.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

Exact inference recovers the reasons the top-k setting discarded:

REASON-DELETION CERTIFICATE [PASS]
query: withhold_fast_track(PT-0731)
engine: reference:exact-wmc   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991424   engine value 0.991424   gap +0.000000   tolerance 1e-09
reasons: 5 found by exact inference, 5 used by the engine, 0 deleted, 0 not certifiable

  [           used] H01 — Comorbidity burden above the fast-track ceiling  (score 0.731000)
                    facts: comorbidity_index_high(PT-0731), history_coded(PT-0731)
                    deleting comorbidity_index_high(PT-0731) moves exact inference by -0.023306 and the engine by -0.023306: the engine's answer depends on this reason.
  [           used] H02 — Renal function below the protocol floor  (score 0.664200)
                    facts: egfr_below_floor(PT-0731), labs_within_window(PT-0731)
                    deleting egfr_below_floor(PT-0731) moves exact inference by -0.016964 and the engine by -0.016964: the engine's answer depends on this reason.
  [           used] H03 — Interacting medication on the active list  (score 0.600600)
                    facts: interacting_drug_active(PT-0731), medication_list_current(PT-0731)
                    deleting interacting_drug_active(PT-0731) moves exact inference by -0.012897 and the engine by -0.012897: the engine's answer depends on this reason.
  [           used] H04 — Vital-sign instability in the observation window  (score 0.540200)
                    facts: monitoring_continuous(PT-0731), vitals_unstable(PT-0731)
                    deleting monitoring_continuous(PT-0731) moves exact inference by -0.010076 and the engine by -0.010076: the engine's answer depends on this reason.
  [           used] H05 — Imaging finding outside the automated-review scope  (score 0.483000)
                    facts: imaging_finding_out_of_scope(PT-0731), imaging_reported(PT-0731)
                    deleting imaging_finding_out_of_scope(PT-0731) moves exact inference by -0.008012 and the engine by -0.008012: the engine's answer depends on this reason.

ATTRIBUTION: The engine used every reason exact inference found, and its value matched the exact value within tolerance. No inference setting is implicated on this input.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

With exact inference behind it the Art. 22 record can state the whole logic:

EVIDENCE RECORD [COMPLETE]
decision: PT-0731
duty: Automated decisions: “meaningful information about the logic involved”
legal source: GDPR Art. 22 (and Rec. 71)
source of the duty: Table 7 (row 3, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Human-readable rule summaries; monotonicity statements; concept/ontology flow graphs; rationale templates
where it fits: Data protection impact assessment (DPIA); user-facing notices; model cards

minimal evidence retained:
  [x] per_decision_reason_string (Per-decision reason string referencing rule(s)/constraint(s)):
        H01 — Comorbidity burden above the fast-track ceiling
        H02 — Renal function below the protocol floor
        H03 — Interacting medication on the active list
        H04 — Vital-sign instability in the observation window
        H05 — Imaging finding outside the automated-review scope
  [x] feature_to_named_concept_mapping (mapping from model features to named concepts):
        comorbidity_index_high -> H01: Comorbidity burden above the fast-track ceiling
        history_coded -> H01: Comorbidity burden above the fast-track ceiling
        egfr_below_floor -> H02: Renal function below the protocol floor
        labs_within_window -> H02: Renal function below the protocol floor
        interacting_drug_active -> H03: Interacting medication on the active list
        medication_list_current -> H03: Interacting medication on the active list
        vitals_unstable -> H04: Vital-sign instability in the observation window
        monitoring_continuous -> H04: Vital-sign instability in the observation window
        imaging_finding_out_of_scope -> H05: Imaging finding outside the automated-review scope
        imaging_reported -> H05: Imaging finding outside the automated-review scope
  [x] dpia_cross_reference (DPIA cross-reference):
        DPIA-2026-014 s.4.2 (automated triage, Art. 22 assessment)

supporting material (NOT Table 7 evidence, and fills no gap above):
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [PASS]
    query: withhold_fast_track(PT-0731)
    engine: reference:exact-wmc   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991424   engine value 0.991424   gap +0.000000   tolerance 1e-09
    reasons: 5 found by exact inference, 5 used by the engine, 0 deleted, 0 not certifiable
    
      [           used] H01 — Comorbidity burden above the fast-track ceiling  (score 0.731000)
                        facts: comorbidity_index_high(PT-0731), history_coded(PT-0731)
                        deleting comorbidity_index_high(PT-0731) moves exact inference by -0.023306 and the engine by -0.023306: the engine's answer depends on this reason.
      [           used] H02 — Renal function below the protocol floor  (score 0.664200)
                        facts: egfr_below_floor(PT-0731), labs_within_window(PT-0731)
                        deleting egfr_below_floor(PT-0731) moves exact inference by -0.016964 and the engine by -0.016964: the engine's answer depends on this reason.
      [           used] H03 — Interacting medication on the active list  (score 0.600600)
                        facts: interacting_drug_active(PT-0731), medication_list_current(PT-0731)
                        deleting interacting_drug_active(PT-0731) moves exact inference by -0.012897 and the engine by -0.012897: the engine's answer depends on this reason.
      [           used] H04 — Vital-sign instability in the observation window  (score 0.540200)
                        facts: monitoring_continuous(PT-0731), vitals_unstable(PT-0731)
                        deleting monitoring_continuous(PT-0731) moves exact inference by -0.010076 and the engine by -0.010076: the engine's answer depends on this reason.
      [           used] H05 — Imaging finding outside the automated-review scope  (score 0.483000)
                        facts: imaging_finding_out_of_scope(PT-0731), imaging_reported(PT-0731)
                        deleting imaging_finding_out_of_scope(PT-0731) moves exact inference by -0.008012 and the engine by -0.008012: the engine's answer depends on this reason.
    
    ATTRIBUTION: The engine used every reason exact inference found, and its value matched the exact value within tolerance. No inference setting is implicated on this input.
    
    LIMITS OF THIS CERTIFICATE
      This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

LIMITS OF THIS RECORD
  This record is not a compliance guarantee and is not legal advice. It reproduces the minimal evidence fields that one peer-reviewed review (Table 7 of the source named above) associates with the cited duty. Whether those fields discharge the duty, and whether the values supplied for them are accurate, are determinations this tool does not make and cannot make.

Withhold the feature-to-concept mapping and the record says so:

EVIDENCE RECORD [INCOMPLETE]
decision: PT-0731
duty: Automated decisions: “meaningful information about the logic involved”
legal source: GDPR Art. 22 (and Rec. 71)
source of the duty: Table 7 (row 3, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Human-readable rule summaries; monotonicity statements; concept/ontology flow graphs; rationale templates
where it fits: Data protection impact assessment (DPIA); user-facing notices; model cards

minimal evidence retained:
  [x] per_decision_reason_string (Per-decision reason string referencing rule(s)/constraint(s)):
        H01 — Comorbidity burden above the fast-track ceiling
        H02 — Renal function below the protocol floor
        H03 — Interacting medication on the active list
        H04 — Vital-sign instability in the observation window
        H05 — Imaging finding outside the automated-review scope
  [ ] feature_to_named_concept_mapping (mapping from model features to named concepts): NOT PRODUCED
  [x] dpia_cross_reference (DPIA cross-reference):
        DPIA-2026-014 s.4.2 (automated triage, Art. 22 assessment)

INCOMPLETE: 1 of 3 required fields could not be produced. This record does not carry the minimal evidence Table 7 specifies for this duty. Missing:
  - feature_to_named_concept_mapping — mapping from model features to named concepts

LIMITS OF THIS RECORD
  This record is not a compliance guarantee and is not legal advice. It reproduces the minimal evidence fields that one peer-reviewed review (Table 7 of the source named above) associates with the cited duty. Whether those fields discharge the duty, and whether the values supplied for them are accurate, are determinations this tool does not make and cannot make.

====================================================================================================
3. PERTURBED ENGINES — does the certificate catch a broken one?
====================================================================================================

REASON-DELETION CERTIFICATE [FAIL]
query: adverse_action(APP-1042)
engine: perturbed:silent-drop-lowest-reason   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991399   engine value 0.982404   gap -0.008995   tolerance 1e-09
reasons: 5 found by exact inference, 4 used by the engine, 1 deleted, 0 not certifiable

  [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                    facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                    deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.019098: the engine's answer depends on this reason.
  [           used] C02 — Length of time credit has been established is too short  (score 0.697200)
                    facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                    deleting file_thin(APP-1042) moves exact inference by -0.019804 and the engine by -0.010809: the engine's answer depends on this reason.
  [           used] C03 — Delinquent past or present credit obligations  (score 0.632000)
                    facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                    deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 and the engine by +0.003733: the engine's answer depends on this reason.
  [           used] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                    facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                    deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 and the engine by +0.004829: the engine's answer depends on this reason.
  [        DELETED] C05 — Insufficient number of credit references provided  (score 0.511200)
                    facts: application_complete(APP-1042), references_under_policy(APP-1042)
                    deleting application_complete(APP-1042) moves exact inference by -0.008995 but leaves the engine unchanged: the engine's answer does not depend on this reason.

MISSING REASONS: the engine's answer does not depend on 1 reason(s) that exact inference found:
  - C05 — Insufficient number of credit references provided: application_complete(APP-1042), references_under_policy(APP-1042)

ATTRIBUTION: The deleted reasons are exactly the 1 lowest-scoring of the 5, and the engine kept the top 4. This is the signature of top-k proof truncation at k=4: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.008995.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

REASON-DELETION CERTIFICATE [FAIL]
query: adverse_action(APP-1042)
engine: perturbed:undeclared-calibration(x0.97)   claims: distribution semantics
exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
exact value 0.991399   engine value 0.961657   gap -0.029742   tolerance 1e-09
reasons: 5 found by exact inference, 5 used by the engine, 0 deleted, 0 not certifiable

  [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                    facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                    deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.027250: the engine's answer depends on this reason.
  [           used] C02 — Length of time credit has been established is too short  (score 0.697200)
                    facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                    deleting file_thin(APP-1042) moves exact inference by -0.019804 and the engine by -0.019210: the engine's answer depends on this reason.
  [           used] C03 — Delinquent past or present credit obligations  (score 0.632000)
                    facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                    deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 and the engine by -0.005104: the engine's answer depends on this reason.
  [           used] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                    facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                    deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 and the engine by -0.004041: the engine's answer depends on this reason.
  [           used] C05 — Insufficient number of credit references provided  (score 0.511200)
                    facts: application_complete(APP-1042), references_under_policy(APP-1042)
                    deleting application_complete(APP-1042) moves exact inference by -0.008995 and the engine by -0.008725: the engine's answer depends on this reason.

ATTRIBUTION: No reason was deleted, but the engine's value differs from exact inference by -0.029742. The responsible setting is the engine's aggregation over the reasons it kept, not proof truncation: every reason still moves the answer.

LIMITS OF THIS CERTIFICATE
  This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

An instrument that passed a corrupted engine would be worthless, so both perturbations must fail, and by
different routes: the silent drop is caught by the deletion probe, which names the reason that stopped
mattering; the undeclared calibration keeps every reason live and is caught only by the value check against
the exact oracle. Neither check subsumes the other, which is why the certificate requires both.

====================================================================================================
4. STRATIFIED PER-GROUP CHECKS (Table 19: minority over-smoothing)
====================================================================================================

Registered hypothesis, stated before the measurement: low-probability reasons are dropped first, so
atypical cases lose reasons faster. Two cohort designs separate the two things that could drive that.

design A: confidence varies, reason structure fixed

CONFORMANCE CHECKS (Table 19: fidelity, coverage, reason-set size,
                    stratified per-group checks, reason diversity;
                    stability is reported separately, over windows)

  group                       n         measured    reasons_found     reasons_used  reasons_deleted         coverage         fidelity   retained_share reason_diversity
  typical                     4                4           3.0000           1.0000           2.0000           0.3333           0.7807           0.7731           0.3333
  atypical                    4                4           3.0000           1.0000           2.0000           0.3333           0.7272           0.4929           0.3333

  per-group gaps (best group minus worst):
    fidelity           +0.0535   (best typical, worst atypical)
    retained_share     +0.2802   (best typical, worst atypical)
    coverage           +0.0000   (best typical, worst typical)
    reasons_used       +0.0000   (best typical, worst typical)
    reason_diversity   +0.0000   (best typical, worst typical)

  reason-set size cap 3: typical mean 1.00 within; atypical mean 1.00 within

LIMITS OF THESE MEASUREMENTS
  These are measurements on the cases supplied, not a compliance guarantee and not legal advice. A per-group figure is only as representative as the cases behind it, and a group with few cases carries a correspondingly weak measurement.

design B: reason multiplicity varies, confidence fixed

CONFORMANCE CHECKS (Table 19: fidelity, coverage, reason-set size,
                    stratified per-group checks, reason diversity;
                    stability is reported separately, over windows)

  group                       n         measured    reasons_found     reasons_used  reasons_deleted         coverage         fidelity   retained_share reason_diversity
  typical                     4                4           2.0000           1.0000           1.0000           0.5000           0.7831           0.7292           0.5000
  atypical                    4                4           5.0000           1.0000           4.0000           0.2000           0.6360           0.6163           0.2000

  per-group gaps (best group minus worst):
    fidelity           +0.1472   (best typical, worst atypical)
    retained_share     +0.1129   (best typical, worst atypical)
    coverage           +0.3000   (best typical, worst atypical)
    reasons_used       +0.0000   (best typical, worst typical)
    reason_diversity   +0.3000   (best typical, worst atypical)

  reason-set size cap 3: typical mean 1.00 within; atypical mean 1.00 within

LIMITS OF THESE MEASUREMENTS
  These are measurements on the cases supplied, not a compliance guarantee and not legal advice. A per-group figure is only as representative as the cases behind it, and a group with few cases carries a correspondingly weak measurement.

OUTCOME OF THE REGISTERED HYPOTHESIS

  Design A — confidence varies, reason structure fixed:
    coverage         no gap (typical 0.3333, atypical 0.3333)
    retained_share   gap 0.2802, worse for atypical (typical 0.7731, atypical 0.4929)
    fidelity         gap 0.0535, worse for atypical (typical 0.7807, atypical 0.7272)

  Design B — reason multiplicity varies, confidence fixed:
    coverage         gap 0.3000, worse for atypical (typical 0.5000, atypical 0.2000)
    retained_share   gap 0.1129, worse for atypical (typical 0.7292, atypical 0.6163)
    fidelity         gap 0.1472, worse for atypical (typical 0.7831, atypical 0.6360)

  In its confidence form the hypothesis is NOT supported. Lowering confidence alone does not cost a case any
  reasons: top-k keeps a fixed number of proofs, and scaling every score down leaves their order unchanged, so
  coverage is identical across the two groups of design A. The atypical group is still worse off, but on the
  value metrics rather than the reason count — it keeps a smaller share of the answer it would have had under
  exact inference.

  In its multiplicity form it is supported: a case that trips five reasons and is told one keeps a fifth of its
  reasons, a case that trips two keeps half. Coverage moves in design B and not in design A, which locates the
  mechanism in how many reasons a case trips, not in how confident the model is about them.

  Both readings were registered in advance and both are reported. The negative half is the more useful one: a
  per-group coverage check will not detect confidence-driven harm at all, so a deployment watching coverage alone
  would have seen design A as clean. Retained share is what caught it.

  The limit that matters most: these are frozen synthetic cohorts, built to separate two mechanisms. Whether real
  atypical cases trip more reasons than typical ones is an empirical question about data this does not have.

====================================================================================================
5. STABILITY ACROSS WINDOWS (Table 19)
====================================================================================================

One decision, four monitoring windows, one drifting signal: the bureau's delinquency evidence strengthens
window by window. Nothing about the program changes, and the applicant's other evidence does not change.
  window 0: reason given = C01 — Income insufficient for amount of credit requested
  window 1: reason given = C01 — Income insufficient for amount of credit requested
  window 2: reason given = C03 — Delinquent past or present credit obligations
  window 3: reason given = C03 — Delinquent past or present credit obligations

  stability across the four windows: 0.3333 (1.0 would mean the same reasons every window)

  The applicant's file did not change, and the reason they are given did. Under a top-1 setting the reason
  stated is whichever proof currently scores highest, so drift in one signal silently replaces the stated
  reason with another. Exact inference has nothing to reorder — it gives all of them in every window.
```

---

## 2. Conformance Report Output

Both runs below read [`sample_decisions.jsonl`](sample_decisions.jsonl), the committed
three-record decision trace from a credit-scoring pipeline. Neither run declares capabilities, so
both are read from that trace alone, and both reports say so on their face.

### 2.1 ECOA / Reg B pack — every requirement observed (exit code 0)

```sh
python -m reasonsmith.cli check --system docs/sample_decisions.jsonl --pack ecoa --system-name CreditScoringPipeline
```

```text
CONFORMANCE REPORT
system: CreditScoringPipeline
declared scope: undeclared
pack: ecoa
headline: 3 requirements · 3 binding: 3 observed

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): satisfied
    requires: artifact_logs_decision_record, artifact_logs_notification_latency_days, artifact_logs_counteroffer_not_accepted
    summary: Observed over 3 decision(s): temporal monitor for 'always((artifact_logs_decision_record >= 0.5) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))' satisfied across all time steps.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    requires: artifact_logs_reason_explanation, artifact_logs_decision_record, provenance_model_version
    summary: Observed over 3 decision(s): every required signal (artifact_logs_reason_explanation, artifact_logs_decision_record, provenance_model_version) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    summary: Observed over 3 decision(s): every required signal (artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded either because no regulatory class was declared for the system at all, or because the class that was declared is not the one the requirement is limited to. This tool never infers that class, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope line before reading a not-applicable result.
```

### 2.2 Table 7 pack — nothing discharged on this trace (exit code 0)

The same log checked against the Table 7 pack discharges nothing. That pack names Table 7's own
evidence-field keys, and this trace carries none of them, so every requirement whose duty reaches
this system is reported unattainable with its missing signals named rather than violated. The two
EU AI Act rows are limited to the high-risk class and no scope was declared on the command line, so
they are reported not applicable — `reasonsmith` never infers that class. Nothing here is a breach,
so the CLI exits 0.

```sh
python -m reasonsmith.cli check --system docs/sample_decisions.jsonl --pack table7 --system-name CreditScoringPipeline
```

```text
CONFORMANCE REPORT
system: CreditScoringPipeline
declared scope: undeclared
pack: table7
headline: 6 requirements · 4 binding: 2 observed, 2 not applicable · 2 interpretive: 2 unattainable

REQUIREMENT FINDINGS:
  [NOT APPLICABLE] eu_ai_act_art13_transparency (EU AI Act Art. 13): not_applicable
    requires: model_and_data_version_ids, extraction_timestamp, dataset_snapshot_hash, fidelity_coverage_metrics, explanation_scope, linkage_from_decision_to_artifact
    scope limit: high-risk
    summary: Not applicable: requirement scope is 'high-risk', but system regulatory class is undeclared. reasonsmith never infers a system's regulatory class.
  [NOT APPLICABLE] eu_ai_act_art12_record_keeping (EU AI Act Art. 12): not_applicable
    requires: automatic_event_logs, retention_schedule, signer
    scope limit: high-risk
    summary: Not applicable: requirement scope is 'high-risk', but system regulatory class is undeclared. reasonsmith never infers a system's regulatory class.
  [OBSERVED] gdpr_art22_meaningful_information (GDPR Art. 22 (and Rec. 71)): satisfied
    requires: per_decision_reason_string, feature_to_named_concept_mapping, dpia_cross_reference
    summary: Observed over 3 decision(s): every required signal (per_decision_reason_string, feature_to_named_concept_mapping, dpia_cross_reference) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.
  [OBSERVED] ecoa_reg_b_adverse_action (ECOA / Reg B 12 CFR 1002.9): satisfied
    requires: stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback
    summary: Observed over 3 decision(s): every required signal (stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.
  [UNATTAINABLE] [INTERPRETIVE] fda_gmlp_samd (FDA GMLP agency transparency guidance): inconclusive
    requires: design_history_links, verification_logs, change_control
    MISSING SIGNALS: change_control, design_history_links, verification_logs
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for change_control, design_history_links, verification_logs, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] [INTERPRETIVE] nist_ai_rmf_risk_evidence (NIST AI RMF 1.0): inconclusive
    requires: continuous_monitoring_logs, metric_thresholds_and_alerts, reviews_and_sign_offs, incident_tickets
    MISSING SIGNALS: continuous_monitoring_logs, incident_tickets, metric_thresholds_and_alerts, reviews_and_sign_offs
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for continuous_monitoring_logs, incident_tickets, metric_thresholds_and_alerts, reviews_and_sign_offs, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded either because no regulatory class was declared for the system at all, or because the class that was declared is not the one the requirement is limited to. This tool never infers that class, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope line before reading a not-applicable result.
```
