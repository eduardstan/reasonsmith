# Example Output

This document contains genuine captured execution output from `reasonsmith`.

- **Commit:** `5579c668560742380377086791ac5e78dcb10b7e`
- **Commands:** `python -m reasonsmith.demo` and `python -m reasonsmith.cli check`

---

## 1. Demonstration Output (`reasonsmith.demo`)

Captured verbatim by running `python -m reasonsmith.demo`:

```text
====================================================================================================
0. TABLE 7 TRACEABILITY REPORT
   Verbatim transcription of Table 7, Symbols and Neurons (JAIR 2026, p. 36:22)
====================================================================================================

ROW 1 | high-risk (Annex III 1(a)) biometric AI
  duty: Logging capabilities: start/end time, reference DB, matched input, human verifier IDs
  source: EU AI Act (Art. 12(3))
  symbolic artifact Table 7 asks for: Decision tree / rule-based audit trace of verification events
  where it fits: Biometric identification logging
  evidence fields Table 7 specifies:
    - automatic_event_logs: Automatic recording of events over system lifetime (Art. 12(1))
    - retention_schedule: Event log retention schedule and storage policy
    - signer: Identity of natural persons verifying matching results (Art. 12(3)(d))

ROW 2 | high-risk AI system deployer notice
  duty: Instructions for use: characteristics, capabilities, limitations, accuracy, robustness, cybersecurity, explanation capabilities, data specs, oversight, log collection
  source: EU AI Act (Art. 13)
  symbolic artifact Table 7 asks for: Monotone / eligibility constraints; rule sets; local feature attribution
  where it fits: Model documentation; instructions for deployers
  evidence fields Table 7 specifies:
    - model_and_data_version_ids: Model version, training/validation dataset IDs, performance metrics
    - extraction_timestamp: Timestamp of constraint / rule extraction
    - dataset_snapshot_hash: Cryptographic hash of underlying data snapshot
    - fidelity_coverage_metrics: Quantitative fidelity and coverage metrics of symbolic artifact
    - explanation_scope: Local vs global explanation scope declaration
    - linkage_from_decision_to_artifact: Audit link connecting specific decision ID to symbolic artifact version

ROW 3 | automated decision-making producing legal or similarly significant effects
  duty: Meaningful information about the logic involved; right to human intervention, point of view, contestation, and explanation
  source: GDPR (Art. 22, Rec. 71)
  symbolic artifact Table 7 asks for: Local decision-tree / rule extraction per case; counterfactual explanation
  where it fits: Data subject access request (DSAR) response; automated decision notification
  evidence fields Table 7 specifies:
    - per_decision_reason_string: Plain-language per-decision reason string
    - feature_to_named_concept_mapping: Feature-to-concept mapping table
    - dpia_cross_reference: DPIA cross-reference ID for automated processing

ROW 4 | adverse action credit decision
  duty: Specific principal reasons for adverse action; ECOA notice; creditor identity; administration agency
  source: ECOA / Reg B (12 CFR 1002.9)
  symbolic artifact Table 7 asks for: Rule-based “reason codes” mapped to standardized categories; monotone/eligibility constraints for fairness explanations
  where it fits: Adverse action notice (AAN) pipeline; compliance reporting
  evidence fields Table 7 specifies:
    - stored_reasons_per_decision: Stored reasons per decision
    - model_version: Model version
    - score_factors: Score factors
    - audit_ids: Audit IDs
    - retention_for_regulatory_lookback: Retention for regulatory lookback

ROW 5 | Software as a Medical Device (SaMD) AI/ML
  duty: Total product lifecycle transparency, change control, decision rationale, verification logs
  source: FDA GMLP / AI/ML Action Plan
  symbolic artifact Table 7 asks for: Constraint-satisfaction traces; clinical rule graphs; bounding boxes / saliency masks
  where it fits: 510(k) / PMA submission; Software Precert summary
  evidence fields Table 7 specifies:
    - design_history_links: Design history file (DHF) links
    - verification_logs: Verification logs
    - change_control: Change control protocol version

ROW 6 | AI system risk management
  duty: Continuous monitoring, risk identification, metric thresholds, risk governance sign-offs
  source: NIST AI RMF 1.0 (MAP / MEASURE / MANAGE)
  symbolic artifact Table 7 asks for: Risk-rule sets; failure-mode trees; bounds on performance degradation
  where it fits: AI risk register; periodic governance reviews
  evidence fields Table 7 specifies:
    - continuous_monitoring_logs: Continuous monitoring logs
    - metric_thresholds_and_alerts: Metric thresholds and alert triggers
    - reviews_and_sign_offs: Periodic risk review sign-offs
    - incident_tickets: Incident tracking tickets

====================================================================================================
1. EXACT INFERENCE vs TOP-K PROOF TRUNCATION (ECOA / Reg B credit decision APP-1042)
====================================================================================================

Exact inference (bounded proof enumeration + exact WMC):
  reasons found: 5
    - C01 — Income insufficient for amount of credit requested (score 0.765600)
    - C02 — Length of time credit has been established is too short (score 0.697200)
    - C03 — Delinquent past or present credit obligations (score 0.632000)
    - C04 — Too many recent inquiries on credit bureau report (score 0.600400)
    - C05 — Insufficient number of credit references provided (score 0.511200)
  exact value: 0.991399

Deployed top-1 engine (truncates to highest-scoring proof):
  reasons used: 1
    - C01 — Income insufficient for amount of credit requested (score 0.765600)
  engine value: 0.765600
  reasons deleted by proof truncation: 4 (C02, C03, C04, C05)

CERTIFYING THE EXACT INFERENCE ORACLE (sanity check: must PASS)
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [PASS]
    query: adverse_action(APP-1042)
    engine: reference:exact-wmc   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991399   engine value 0.991399   gap 0.000000   tolerance 1e-09
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

Read those two together. The record is COMPLETE — every field Table 7 lists for row 4 was produced.
A compliance audit examining record completeness alone would pass this decision.
The paired certificate reads FAIL: 4 of the applicant's 5 principal reasons were dropped.
Form completeness does not imply reason fidelity. That is why the certificate exists.

Contrast with a record that is missing a Table 7 required field (e.g. audit_ids withheld):

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
  [ ] audit_ids (audit IDs):
        [WITHHELD / MISSING]
  [x] retention_for_regulatory_lookback (retention for regulatory lookback):
        25 months from notice date, per lender policy

INCOMPLETE: 1 of 5 required fields could not be produced. This record does not carry the minimal evidence Table 7 specifies for this duty. Missing:
  - audit_ids: audit IDs

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

No default was substituted for audit_ids. The gap is named on the face of the record.

====================================================================================================
2. CLINICAL DEMONSTRATION (GDPR Art. 22 / Recital 71 medical decision PT-0731)
====================================================================================================

Exact inference (bounded proof enumeration + exact WMC):
  reasons found: 5
    - M01 — High risk score on secondary biomarker panel (score 0.731000)
    - M02 — History of adverse drug reaction in same drug class (score 0.684000)
    - M03 — Renal clearance below protocol safety threshold (score 0.612000)
    - M04 — Comorbid condition contraindicating primary therapy (score 0.589000)
    - M05 — Age-adjusted toxicity risk exceeds standard threshold (score 0.504000)
  exact value: 0.991424

Deployed top-1 engine:
  reasons used: 1
    - M01 — High risk score on secondary biomarker panel (score 0.731000)
  engine value: 0.731000
  reasons deleted: 4 (M02, M03, M04, M05)

EVIDENCE RECORD [COMPLETE]
decision: PT-0731
duty: Meaningful information about the logic involved; right to human intervention, point of view, contestation, and explanation
legal source: GDPR (Art. 22, Rec. 71)
source of the duty: Table 7 (row 3, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Local decision-tree / rule extraction per case; counterfactual explanation
where it fits: Data subject access request (DSAR) response; automated decision notification

minimal evidence retained:
  [x] per_decision_reason_string (Plain-language per-decision reason string):
          M01 — High risk score on secondary biomarker panel
  [x] feature_to_named_concept_mapping (Feature-to-concept mapping table):
        biomarker_panel_b -> M01; adr_class_c -> M02; egfr_under_45 -> M03
  [x] dpia_cross_reference (DPIA cross-reference ID for automated processing):
        DPIA-2026-CLINICAL-042 / Art-22-register-881

supporting material (NOT Table 7 evidence, and fills no gap above):
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: recommend_alternative(PT-0731)
    engine: reference:top-1-proofs   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991424   engine value 0.731000   gap -0.260424   tolerance 1e-09
    reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable
    
      [           used] M01 — High risk score on secondary biomarker panel  (score 0.731000)
                        facts: biomarker_panel_b_elevated(PT-0731), panel_b_verified(PT-0731)
                        deleting biomarker_panel_b_elevated(PT-0731) moves exact inference by -0.031120 and the engine by -0.075400: the engine's answer depends on this reason.
      [        DELETED] M02 — History of adverse drug reaction in same drug class  (score 0.684000)
                        facts: adr_class_c_matched(PT-0731), prior_reaction_on_file(PT-0731)
                        deleting adr_class_c_matched(PT-0731) moves exact inference by -0.021040 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M03 — Renal clearance below protocol safety threshold  (score 0.612000)
                        facts: egfr_under_45(PT-0731), lab_confirmed(PT-0731)
                        deleting egfr_under_45(PT-0731) moves exact inference by -0.006110 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M04 — Comorbid condition contraindicating primary therapy  (score 0.589000)
                        facts: comorbidity_flag_active(PT-0731), protocol_contraindicated(PT-0731)
                        deleting comorbidity_flag_active(PT-0731) moves exact inference by -0.004820 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M05 — Age-adjusted toxicity risk exceeds standard threshold  (score 0.504000)
                        facts: age_over_70(PT-0731), toxicity_tier_high(PT-0731)
                        deleting age_over_70(PT-0731) moves exact inference by -0.009410 but leaves the engine unchanged: the engine's answer does not depend on this reason.
    
    MISSING REASONS: the engine's answer does not depend on 4 reason(s) that exact inference found:
      - M02 — History of adverse drug reaction in same drug class: adr_class_c_matched(PT-0731), prior_reaction_on_file(PT-0731)
      - M03 — Renal clearance below protocol safety threshold: egfr_under_45(PT-0731), lab_confirmed(PT-0731)
      - M04 — Comorbid condition contraindicating primary therapy: comorbidity_flag_active(PT-0731), protocol_contraindicated(PT-0731)
      - M05 — Age-adjusted toxicity risk exceeds standard threshold: age_over_70(PT-0731), toxicity_tier_high(PT-0731)
    
    ATTRIBUTION: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.260424.
    
    LIMITS OF THIS CERTIFICATE
      This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

Contrast with a clinical record missing feature_to_named_concept_mapping:

EVIDENCE RECORD [INCOMPLETE]
decision: PT-0731
duty: Meaningful information about the logic involved; right to human intervention, point of view, contestation, and explanation
legal source: GDPR (Art. 22, Rec. 71)
source of the duty: Table 7 (row 3, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Local decision-tree / rule extraction per case; counterfactual explanation
where it fits: Data subject access request (DSAR) response; automated decision notification

minimal evidence retained:
  [x] per_decision_reason_string (Plain-language per-decision reason string):
          M01 — High risk score on secondary biomarker panel
  [ ] feature_to_named_concept_mapping (Feature-to-concept mapping table):
        [WITHHELD / MISSING]
  [x] dpia_cross_reference (DPIA cross-reference ID for automated processing):
        DPIA-2026-CLINICAL-042 / Art-22-register-881

INCOMPLETE: 1 of 3 required fields could not be produced. This record does not carry the minimal evidence Table 7 specifies for this duty. Missing:
  - feature_to_named_concept_mapping: Feature-to-concept mapping table

supporting material (NOT Table 7 evidence, and fills no gap above):
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: recommend_alternative(PT-0731)
    engine: reference:top-1-proofs   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991424   engine value 0.731000   gap -0.260424   tolerance 1e-09
    reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable
    
      [           used] M01 — High risk score on secondary biomarker panel  (score 0.731000)
                        facts: biomarker_panel_b_elevated(PT-0731), panel_b_verified(PT-0731)
                        deleting biomarker_panel_b_elevated(PT-0731) moves exact inference by -0.031120 and the engine by -0.075400: the engine's answer depends on this reason.
      [        DELETED] M02 — History of adverse drug reaction in same drug class  (score 0.684000)
                        facts: adr_class_c_matched(PT-0731), prior_reaction_on_file(PT-0731)
                        deleting adr_class_c_matched(PT-0731) moves exact inference by -0.021040 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M03 — Renal clearance below protocol safety threshold  (score 0.612000)
                        facts: egfr_under_45(PT-0731), lab_confirmed(PT-0731)
                        deleting egfr_under_45(PT-0731) moves exact inference by -0.006110 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M04 — Comorbid condition contraindicating primary therapy  (score 0.589000)
                        facts: comorbidity_flag_active(PT-0731), protocol_contraindicated(PT-0731)
                        deleting comorbidity_flag_active(PT-0731) moves exact inference by -0.004820 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [        DELETED] M05 — Age-adjusted toxicity risk exceeds standard threshold  (score 0.504000)
                        facts: age_over_70(PT-0731), toxicity_tier_high(PT-0731)
                        deleting age_over_70(PT-0731) moves exact inference by -0.009410 but leaves the engine unchanged: the engine's answer does not depend on this reason.
    
    MISSING REASONS: the engine's answer does not depend on 4 reason(s) that exact inference found:
      - M02 — History of adverse drug reaction in same drug class: adr_class_c_matched(PT-0731), prior_reaction_on_file(PT-0731)
      - M03 — Renal clearance below protocol safety threshold: egfr_under_45(PT-0731), lab_confirmed(PT-0731)
      - M04 — Comorbid condition contraindicating primary therapy: comorbidity_flag_active(PT-0731), protocol_contraindicated(PT-0731)
      - M05 — Age-adjusted toxicity risk exceeds standard threshold: age_over_70(PT-0731), toxicity_tier_high(PT-0731)
    
    ATTRIBUTION: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.260424.
    
    LIMITS OF THIS CERTIFICATE
      This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

====================================================================================================
3. PERTURBATION SENSITIVITY (proving why both checks are necessary)
====================================================================================================

Perturbation 1: SILENTLY TRUNCATED ENGINE (drops C04, does not report it)
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: adverse_action(APP-1042)
    engine: reference:silent-truncation   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991399   engine value 0.987233   gap -0.004166   tolerance 1e-09
    reasons: 5 found by exact inference, 4 used by the engine, 1 deleted, 0 not certifiable
    
      [           used] C01 — Income insufficient for amount of credit requested  (score 0.765600)
                        facts: dti_above_policy(APP-1042), income_verified(APP-1042)
                        deleting dti_above_policy(APP-1042) moves exact inference by -0.028093 and the engine by -0.028093: the engine's answer depends on this reason.
      [           used] C02 — Length of time credit has been established is too short  (score 0.697200)
                        facts: file_thin(APP-1042), history_under_24_months(APP-1042)
                        deleting file_thin(APP-1042) moves exact inference by -0.019804 and the engine by -0.019804: the engine's answer depends on this reason.
      [           used] C03 — Delinquent past or present credit obligations  (score 0.632000)
                        facts: bureau_record_matched(APP-1042), delinquency_on_file(APP-1042)
                        deleting delinquency_on_file(APP-1042) moves exact inference by -0.005262 and the engine by -0.005262: the engine's answer depends on this reason.
      [        DELETED] C04 — Too many recent inquiries on credit bureau report  (score 0.600400)
                        facts: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
                        deleting inquiries_over_policy(APP-1042) moves exact inference by -0.004166 but leaves the engine unchanged: the engine's answer does not depend on this reason.
      [           used] C05 — Insufficient number of credit references provided  (score 0.511200)
                        facts: application_complete(APP-1042), references_under_policy(APP-1042)
                        deleting application_complete(APP-1042) moves exact inference by -0.008995 and the engine by -0.008995: the engine's answer depends on this reason.
    
    MISSING REASONS: the engine's answer does not depend on 1 reason(s) that exact inference found:
      - C04 — Too many recent inquiries on credit bureau report: bureau_record_matched(APP-1042), inquiries_over_policy(APP-1042)
    
    ATTRIBUTION: The deletion probe caught 1 deleted reason (C04 — Too many recent inquiries on credit bureau report), responsible for a value gap of -0.004166. Deleting its fact (inquiries_over_policy(APP-1042)) moved exact inference by -0.004166 but left the engine unchanged.
    
    LIMITS OF THIS CERTIFICATE
      This certificate compares one engine's answer against exact inference on one ground program and one base interpretation. It is not a compliance guarantee and is not legal advice. A PASS means no reason was shown to be deleted and the engine's value matched the exact value on this input; it does not certify the engine on any other input, and it does not establish that the reasons themselves are correct, only that the engine used all of the ones exact inference found.

Perturbation 2: UNDECLARED CALIBRATION FACTOR (uses every reason, scales result)
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: adverse_action(APP-1042)
    engine: reference:calibrated-aggregation   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991399   engine value 0.961657   gap -0.297420   tolerance 1e-09
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

## 2. Conformance Report Output (`reasonsmith.cli`)

Captured verbatim by running `python -m reasonsmith.cli check --system decisions.jsonl --pack table7`:

```text
CONFORMANCE REPORT
system: CreditScoringPipeline
declared scope: undeclared
pack: table7
headline: 3 binding requirements · 1 observed · 2 not applicable · + 3 interpretive: 3 unattainable

REQUIREMENT FINDINGS:
  [NOT APPLICABLE] eu_ai_act_art13_transparency (EU AI Act Art. 13): not_applicable
    requires: model_and_data_version_ids, extraction_timestamp, dataset_snapshot_hash, fidelity_coverage_metrics, explanation_scope, linkage_from_decision_to_artifact
    scope limit: high-risk
    summary: Not applicable: requirement scope is 'high-risk', but system regulatory class is undeclared. reasonsmith never infers a system's regulatory class.
  [NOT APPLICABLE] eu_ai_act_art12_record_keeping (EU AI Act Art. 12): not_applicable
    requires: automatic_event_logs, retention_schedule, signer
    scope limit: high-risk
    summary: Not applicable: requirement scope is 'high-risk', but system regulatory class is undeclared. reasonsmith never infers a system's regulatory class.
  [UNATTAINABLE] [INTERPRETIVE] gdpr_art22_meaningful_information (GDPR Art. 22 (and Rec. 71)): inconclusive
    requires: per_decision_reason_string, feature_to_named_concept_mapping, dpia_cross_reference
    MISSING SIGNALS: dpia_cross_reference, feature_to_named_concept_mapping, per_decision_reason_string
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for dpia_cross_reference, feature_to_named_concept_mapping, per_decision_reason_string, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [OBSERVED] ecoa_reg_b_adverse_action (ECOA / Reg B 12 CFR 1002.9): satisfied
    requires: stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback
    summary: Observed over 1 decision(s): every required signal (stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.
  [UNATTAINABLE] [INTERPRETIVE] fda_gmlp_samd (FDA GMLP agency transparency guidance): inconclusive
    requires: design_history_links, verification_logs, change_control
    MISSING SIGNALS: change_control, design_history_links, verification_logs
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for design_history_links, verification_logs, change_control, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] [INTERPRETIVE] nist_ai_rmf_risk_evidence (NIST AI RMF 1.0): inconclusive
    requires: continuous_monitoring_logs, metric_thresholds_and_alerts, reviews_and_sign_offs, incident_tickets
    MISSING SIGNALS: continuous_monitoring_logs, incident_tickets, metric_thresholds_and_alerts, reviews_and_sign_offs
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for continuous_monitoring_logs, incident_tickets, metric_thresholds_and_alerts, reviews_and_sign_offs, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but cannot create an obligation on its own; interpretive requirements are evaluated for completeness and excluded from binding headline counts.
```
