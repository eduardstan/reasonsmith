# Autoformalisation agreement study

**Measurement date:** 2026-08-15  
**Repository:** `6d30ee4d1397c578e8284fb9fee3559b9e085b61`  
**Model:** Claude Code CLI `2.1.231` (`claude-cli`)  
**Command:** `uv run python -m reasonsmith.proposer --claude --attempts 2`

This is the first run of the existing autoformalisation harness against the hand-authored
packs as gold; the dated completion run below adds the 25 rows that were provider-unavailable. The model received each duty's `verbatim_text`, `rationale`, required fragment, signal
names, and the descriptions and evidence of its gold challenge cases. Challenge labels were withheld.
The harness then parsed the one returned formula, ran the existing round-trip comparison against the
shipped `spec`, and ran every gold case. It made at most two model calls per duty: a failed first
candidate was followed by the harness's evidence-based repair prompt. The harness never rewrote a
formula, called a conformance engine, or produced a verdict.

The sample was the complete corpus measured before Article 86: 37 challenge sets (28 record-presence, 4 logical, 4
temporal, and 1 counterfactual). Both the interrupted first-run rate and the completed rate are
counted over all 37 duties in that measured cohort. The first run included its provider-unavailable rows rather
than silently removing them from the denominator; the second run completed exactly those rows.
`semantic-equivalent` includes exact matches; it is the round-trip relation established by the
existing checker, not a human judgement.

The executable gold corpus now contains **39** challenge sets: the CRA Article 14(2)(a) event-time
set was added with the duty, including exact-boundary, one-second-over, and one-second-under cases.
It is a coverage addition, not a retroactive claim about the 2026-08-15 provider measurement above;
the historical rates remain denominated over the 37-duty cohort measured before Article 86.

## Results

| Duty family | Duties | Exact-match | Semantic-equivalent (including exact) | Machine-cleared | Refused | Unavailable | Exact rate | Semantic rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Record-presence | 28 | 25 | 28 | 28 | 0 | 0 | 89.29% | 100.00% |
| Logical | 4 | 1 | 2 | 2 | 1 | 0 | 25.00% | 50.00% |
| Temporal | 4 | 4 | 4 | 4 | 0 | 0 | 100.00% | 100.00% |
| Counterfactual | 1 | 1 | 1 | 1 | 0 | 0 | 100.00% | 100.00% |
| **Overall** | **37** | **31** | **36** | **36** | **1** | **0** | **83.78%** | **97.30%** |

The first run yielded 12 inspectable responses: 11 cleared both machine gates and one was refused by
the parser; 25 were unavailable after the provider quota was reached. Conditional on receiving a usable
candidate in that first run, semantic-equivalence was 11/12 (91.67%). That first-run conditional figure
is retained for auditability, but the completed all-duty result supersedes its partial denominator below.

### Per-duty outcome record

This is the complete outcome list, including the provider failures.

| Requirement | Family | Outcome | Attempts |
|---|---|---|---:|
| `ecoa_reg_b_1002_4_a_no_disparate_treatment` | counterfactual | agreed (exact) | 1 |
| `ecoa_reg_b_1002_9_a_1_timing_of_notice` | temporal | agreed (exact) | 1 |
| `ecoa_reg_b_1002_9_a_2_written_statement` | temporal | agreed (exact) | 1 |
| `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` | logical | agreed (semantic-equivalent) | 1 |
| `ecoa_reg_b_1002_9_b_2_specific_reasons` | logical | refused | 2 |
| `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` | temporal | agreed (exact) | 2 |
| `ecoa_reg_b_adverse_action` | record-presence | agreed (exact) | 2 |
| `eu_ai_act_art12_1_automatic_logging` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art12_2_traceability_monitoring` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art12_record_keeping` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art13_1_transparency_deployers` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art13_2_instructions_for_use` | record-presence | agreed (semantic-equivalent) | 1 |
| `eu_ai_act_art13_transparency` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art53_1_a_technical_documentation` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art53_1_b_downstream_documentation` | record-presence | agreed (exact) | 2 |
| `eu_ai_act_art53_1_c_copyright_policy` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art53_1_d_training_content_summary` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art55_1_a_model_evaluation` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art55_1_b_systemic_risk_assessment` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art55_1_c_serious_incident_reporting` | record-presence | agreed (exact) | 1 |
| `eu_ai_act_art55_1_d_cybersecurity_protection` | record-presence | agreed (exact) | 1 |
| `fda_gmlp_samd` | record-presence | agreed (exact) | 1 |
| `gdpr_art22_1_automated_decision_prohibition` | record-presence | agreed (exact) | 1 |
| `gdpr_art22_1_no_prohibited_decision_for_any_input` | logical | agreed (semantic-equivalent) | 1 |
| `gdpr_art22_3_safeguards_human_intervention` | record-presence | agreed (exact) | 1 |
| `gdpr_art22_meaningful_information` | record-presence | agreed (exact) | 1 |
| `gdpr_recital71_error_risk_minimised` | temporal | agreed (exact) | 1 |
| `gdpr_recital71_meaningful_explanation` | record-presence | agreed (exact) | 1 |
| `nist_ai_rmf_risk_evidence` | record-presence | agreed (exact) | 1 |
| `seoul_frontier_i_lifecycle_risk_assessment` | record-presence | agreed (exact) | 1 |
| `seoul_frontier_ii_thresholds_and_breach_assessment` | record-presence | agreed (exact) | 1 |
| `seoul_frontier_iii_risk_mitigation_process` | record-presence | agreed (semantic-equivalent) | 1 |
| `seoul_frontier_iv_no_deployment_above_threshold` | logical | agreed (exact) | 1 |
| `seoul_frontier_v_continuing_mitigation_monitoring` | record-presence | agreed (semantic-equivalent) | 1 |
| `seoul_frontier_vi_governance_review_and_resources` | record-presence | agreed (exact) | 1 |
| `seoul_frontier_vii_public_transparency` | record-presence | agreed (exact) | 1 |
| `seoul_frontier_viii_external_involvement_explanation` | record-presence | agreed (exact) | 1 |

## Second run completing the first (2026-08-15)

The Claude 5-hour quota reset at 14:40Z. This completion run used the same predeclared Claude
transport and two-attempt budget as the first run (`--claude --attempts 2`), and selected **only** the
25 rows recorded as `unavailable` above. The 11 agreed rows and the one refused row were not sent to
the provider again. To enforce that restriction, a selector invoked the existing `propose` path for
those 25 IDs only; no verification or model call was repeated for a settled outcome.

All 25 previously unavailable duties returned a candidate and cleared both machine gates: 24 on the
first attempt and one after one repair attempt (26 provider calls total). The outage remains part of
the record: the first run's 25 unavailable statuses were caused by the quota cap, rather than being
quietly presented as model refusals or excluded observations. The second run changed those 25 rows to
25 agreed outcomes, with 22 exact matches and 3 additional semantic-equivalent matches.

The completed study therefore has 36 machine-cleared proposals, one parser refusal, and no unavailable
rows. Across all 37 duties in the measured cohort, the final rates are **31/37 (83.78%) exact-match** and **36/37 (97.30%)
semantic-equivalence**. Of the 36 duties with a usable candidate, semantic-equivalence is **36/36
(100%)** and exact-match is **31/36 (86.11%)**. The earlier first-run conditional figure, 11/12
(91.67%), remains above as a record of the quota-interrupted run.

## Disagreements and refusals

- `ecoa_reg_b_1002_9_b_2_principal_reasons_complete`: the proposal used
  `Implies(present(artifact_logs_reason_explanation), artifact_logs_deleted_reason_count <= 0)`
  instead of the shipped arrow spelling. The solver established semantic equivalence; this is a
  defensible syntactic variation, not a wrong property.
- `eu_ai_act_art13_2_instructions_for_use`: the proposal commuted the two conjuncts. The solver
  established equivalence; this is defensibly different syntax with the same denotation.
- `ecoa_reg_b_1002_9_b_2_specific_reasons`: after two responses, the model supplied a construct the
  repository parser rejected (`Implies(...)` in a language position requiring the accepted arrow
  syntax). This is a correctly refused proposal, not a semantic disagreement.
- The first run's 25 `unavailable` rows were provider-availability failures: the Claude subprocess
  exited non-zero after its 5-hour quota cap, before candidates were returned. The dated completion
  run retried only those rows after the 14:40Z reset, and all 25 then cleared; the outage remains
  disclosed rather than being mistaken for a model disagreement.
- `gdpr_art22_1_no_prohibited_decision_for_any_input`, `seoul_frontier_iii_risk_mitigation_process`,
  and `seoul_frontier_v_continuing_mitigation_monitoring` were semantic-equivalent but not exact in
  the completion run. The existing solver established equivalence; these are defensibly different
  formulas, not wrong properties.

## Limitations

This is a two-run deterministic-temperature CLI measurement, not a capability estimate or a claim
about Claude in general. The two-attempt budget and the quota outage bound the first run; the second
run completes only the 25 unavailable rows and does not erase that outage from the provenance. Gold
cases are lawyer-readable examples, not a proof that a candidate is correct; round-trip equivalence
is only as strong as the existing fragment-specific decision procedure, and temporal comparison can
refuse when its optional backend is unavailable. The hand-authored `spec` is the gold reference, so
agreement measures reproduction of this repository's formalisation, not legal correctness.
Open-textured and certificate duties are outside the challenge corpus. A machine-cleared proposal
remains only a candidate until the human sign-off in its `docs/refinement.md` row.
