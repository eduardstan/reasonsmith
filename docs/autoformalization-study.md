# Autoformalisation agreement study

**Measurement date:** 2026-08-15  
**Repository:** `6d30ee4d1397c578e8284fb9fee3559b9e085b61`  
**Model:** Claude Code CLI `2.1.231` (`claude-cli`)  
**Command:** `uv run python -m reasonsmith.proposer --claude --attempts 2`

This is the launch measurement of the existing autoformalisation harness against the hand-authored
packs as gold. The model received each duty's `verbatim_text`, `rationale`, required fragment, signal
names, and the descriptions and evidence of its gold challenge cases. Challenge labels were withheld.
The harness then parsed the one returned formula, ran the existing round-trip comparison against the
shipped `spec`, and ran every gold case. It made at most two model calls per duty: a failed first
candidate was followed by the harness's evidence-based repair prompt. The harness never rewrote a
formula, called a conformance engine, or produced a verdict.

The sample is the complete current corpus: 37 challenge sets (28 record-presence, 4 logical, 4
temporal, and 1 counterfactual). Agreement is counted over all 37 supported duties, including duties
for which the provider became unavailable. This makes provider failure visible rather than silently
removing hard cases from the denominator. `semantic-equivalent` includes exact matches; it is the
round-trip relation established by the existing checker, not a human judgement.

## Results

| Duty family | Duties | Exact-match | Semantic-equivalent (including exact) | Machine-cleared | Refused | Unavailable | Exact rate | Semantic rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Record-presence | 28 | 5 | 6 | 6 | 0 | 22 | 17.86% | 21.43% |
| Logical | 4 | 0 | 1 | 1 | 1 | 2 | 0.00% | 25.00% |
| Temporal | 4 | 3 | 3 | 3 | 0 | 1 | 75.00% | 75.00% |
| Counterfactual | 1 | 1 | 1 | 1 | 0 | 0 | 100.00% | 100.00% |
| **Overall** | **37** | **9** | **11** | **11** | **1** | **25** | **24.32%** | **29.73%** |

There were 12 duties with a model response that could be inspected: 11 cleared both machine gates and
one was refused by the parser. Conditional on receiving a usable candidate, semantic-equivalence was
11/12 (91.67%), but that conditional figure is supplementary: the primary all-duty agreement rate is
**11/37 (29.73%)**, and the exact-match rate is **9/37 (24.32%)**. The 25 unavailable duties are part of
the launch result, not discarded observations.

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
| `eu_ai_act_art13_transparency` | record-presence | unavailable | 0 |
| `eu_ai_act_art53_1_a_technical_documentation` | record-presence | unavailable | 0 |
| `eu_ai_act_art53_1_b_downstream_documentation` | record-presence | unavailable | 0 |
| `eu_ai_act_art53_1_c_copyright_policy` | record-presence | unavailable | 0 |
| `eu_ai_act_art53_1_d_training_content_summary` | record-presence | unavailable | 0 |
| `eu_ai_act_art55_1_a_model_evaluation` | record-presence | unavailable | 0 |
| `eu_ai_act_art55_1_b_systemic_risk_assessment` | record-presence | unavailable | 0 |
| `eu_ai_act_art55_1_c_serious_incident_reporting` | record-presence | unavailable | 0 |
| `eu_ai_act_art55_1_d_cybersecurity_protection` | record-presence | unavailable | 0 |
| `fda_gmlp_samd` | record-presence | unavailable | 0 |
| `gdpr_art22_1_automated_decision_prohibition` | record-presence | unavailable | 0 |
| `gdpr_art22_1_no_prohibited_decision_for_any_input` | logical | unavailable | 0 |
| `gdpr_art22_3_safeguards_human_intervention` | record-presence | unavailable | 0 |
| `gdpr_art22_meaningful_information` | record-presence | unavailable | 0 |
| `gdpr_recital71_error_risk_minimised` | temporal | unavailable | 0 |
| `gdpr_recital71_meaningful_explanation` | record-presence | unavailable | 0 |
| `nist_ai_rmf_risk_evidence` | record-presence | unavailable | 0 |
| `seoul_frontier_i_lifecycle_risk_assessment` | record-presence | unavailable | 0 |
| `seoul_frontier_ii_thresholds_and_breach_assessment` | record-presence | unavailable | 0 |
| `seoul_frontier_iii_risk_mitigation_process` | record-presence | unavailable | 0 |
| `seoul_frontier_iv_no_deployment_above_threshold` | logical | unavailable | 0 |
| `seoul_frontier_v_continuing_mitigation_monitoring` | record-presence | unavailable | 0 |
| `seoul_frontier_vi_governance_review_and_resources` | record-presence | unavailable | 0 |
| `seoul_frontier_vii_public_transparency` | record-presence | unavailable | 0 |
| `seoul_frontier_viii_external_involvement_explanation` | record-presence | unavailable | 0 |

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
- The remaining 25 rows were `unavailable` because the Claude subprocess exited non-zero before a
  candidate was returned. They are provider-availability failures, not evidence that those duties
  agree or disagree. No retry was made after the predeclared run.

## Limitations

This is one deterministic-temperature CLI run, not a capability estimate or a claim about Claude in
general. The two-attempt budget and the provider's availability bound the result. Gold cases are
lawyer-readable examples, not a proof that a candidate is correct; round-trip equivalence is only as
strong as the existing fragment-specific decision procedure, and temporal comparison can refuse when
its optional backend is unavailable. The hand-authored `spec` is the gold reference, so agreement
measures reproduction of this repository's formalisation, not legal correctness. Open-textured and
certificate duties are outside the challenge corpus. A machine-cleared proposal remains only a
candidate until the human sign-off in its `docs/refinement.md` row.
