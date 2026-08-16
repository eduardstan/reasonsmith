# Claim-to-test map

This cross-chapter registry preserves the executable warrant for the mathematical chapters. Each
claim is paired with the test that enforces it; chapter prose remains mathematical.

| Claim | Test |
|---|---|
| The grammar of Definition 2.2 names exactly the calls the language defines | `test_the_grammar_names_exactly_the_calls_the_language_defines` |
| Every spec the grammar generates is accepted, and lands in the fragment it was generated for | `test_every_spec_the_grammar_generates_is_accepted` |
| Every refusal Definition 2.5 names is refused, and every refusal the test knows is named | `test_every_documented_refusal_is_refused`, `test_every_refusal_the_grammar_test_knows_is_named_here` |
| The fragment order of Definition 2.6 is the order the classifier uses | `test_the_fragment_order_is_the_documented_order` |
| Numerals are Python's and every other constant type is refused | `test_the_numeral_syntax_is_pythons_and_the_other_constant_types_are_refused` |
| An identifier CPython normalises is caught by the `requires` gate rather than read as another signal | `test_an_identifier_the_tokenizer_normalises_is_refused_by_the_requires_gate` |
| The word arrow needs a space each side and the symbol arrows do not | `test_the_word_arrow_needs_a_space_on_each_side_and_the_symbol_arrows_do_not` |
| A call carrying keywords or unpacking is refused | `test_a_call_carrying_keywords_or_unpacking_is_refused` |
| Equivalence survives the rewriter as a connective and never as a comparison | `test_the_rewriter_never_collapses_equivalence_to_a_comparison`, `test_an_author_written_equality_is_still_a_comparison` |
| Over `𝔹` both readings of `Iff` are the truth table | `test_the_interpreter_reads_equivalence_as_the_truth_table`, `test_the_solver_reads_equivalence_as_the_truth_table` |
| Over a residuated lattice `Iff` is the biresiduum, `1` exactly when the degrees agree | `test_a_graded_equivalence_is_the_algebra_s_biresiduum`, `test_lukasiewicz_equivalence_is_one_minus_the_distance`, `test_the_biresiduum_is_one_exactly_when_the_degrees_agree` |
| Each shipped algebra is a residuated lattice, and the three disagree | `test_each_algebra_is_a_residuated_lattice_on_the_grid`, `test_the_three_algebras_disagree_about_a_conjunction_of_two_halves` |
| Quantification over a trace is the infimum, and `and` is not that operation | `test_the_degree_of_a_trace_is_the_infimum_of_its_records` |
| Division is true division and `%` is Python's remainder, on both implementations | `test_division_is_true_division_on_both_sides`, `test_modulo_follows_python_semantics_for_any_divisor`, `test_the_encoder_and_the_interpreter_compute_the_same_number` |
| The Z3 encoding and the reference interpreter answer the same, and accept the same set | `test_the_encoder_and_the_interpreter_answer_the_same` |
| A proof disagreeing with the reference interpreter on its own witness is not a proof | `test_encoding_disagreeing_with_the_interpreter_is_not_a_proof` |
| `present()` and `contains()` mean the same thing to the solver as to the reference reading | `test_the_solvers_blank_string_is_pythons_blank_string`, `test_the_solvers_fold_is_the_interpreters_fold`, `test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry` |
| The monitor agrees with the reference reading on every shape it renders | `test_the_monitor_agrees_with_the_reference_reading` |
| The four shapes it does not render soundly are still exactly those four, and still what Remark 3.1 records | `test_the_four_named_shapes_are_still_what_the_document_records` |
| A duty writing one of the three refused shapes is not evaluated, naming the construct | `test_a_duty_using_a_misread_shape_is_not_evaluated_and_names_the_construct` |
| Both spellings of equivalence reach the same refusal | `test_both_spellings_of_equivalence_reach_the_same_refusal` |
| rtamt still raises for every other construct the language admits, so the refusal list is still three long | `test_rtamt_still_behaves_the_way_the_refusals_assume` |
| No shipped pack writes one of those shapes | `test_no_shipped_spec_uses_a_shape_the_monitor_misrenders` |
| The LTLf backend and the monitor agree about every shipped temporal duty | `test_the_ltlf_backend_agrees_with_the_monitor` |
| The bounded response of Definition 3.9a closes at the deadline, and one second past it is a re-checkable violation | `test_exactly_at_the_closed_24_hour_boundary_is_satisfied`, `test_just_over_the_boundary_is_a_recheckable_violation` |
| Its instants are normalised to UTC before subtraction, and a calendar month clamps rather than guessing thirty days | `test_offsets_are_normalised_before_subtraction_including_a_dst_transition`, `test_leap_day_is_an_actual_elapsed_day`, `test_calendar_month_end_clamps_instead_of_guessing_thirty_days`, `test_event_metric_uses_calendar_month_deadline_without_day_guessing` |
| Missing, duplicate, uncorrelated or malformed event evidence is not evaluated, and an untriggered anchor is not a vacuous pass | `test_incomplete_or_ambiguous_event_evidence_is_not_evaluated`, `test_no_trigger_is_not_a_false_pass`, `test_an_unnamed_record_never_merges_with_a_case_spelled_like_its_index` |
| The event clock is never replaced by record positions or a logged latency, and a malformed clock is a refusal rather than a raise | `test_event_operator_never_falls_back_to_ordinal_or_logged_latency`, `test_explicit_ordinal_request_is_refused_for_metric_property`, `test_a_malformed_clock_is_refused_rather_than_raised_on_a_positional_duty`, `test_timestamp_and_duration_refuse_naive_or_invalid_values`, `test_a_bound_naming_an_unrepresentable_instant_is_refused_not_raised` |
| A trace that gained event timestamps loses no positional verdict it had | `test_existing_ordinal_property_is_unchanged_when_timestamps_are_added` |
| The metric operator has no LTLf spelling and is refused by name rather than rendered | `test_a_bounded_response_duty_is_refused_by_name_rather_than_rendered` |
| The LTLf weak-next abstraction agrees with the reference interpreter at generated boundaries | `test_generated_weak_next_boundaries_match_the_reference_interpreter` |
| LTLf questions are asked over a non-empty trace, so `⨅ ∅` is never the answer | `test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable` |
| An empty trace has no value, at every rung and on the graded scale | `test_an_empty_trace_is_not_evidence`, `test_a_graded_duty_with_no_grading_or_no_trace_is_not_evaluated` |
| `undetermined()` has no value in any algebra and names its authority instead | `test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority`, `test_an_undetermined_atom_is_refused_by_the_two_valued_interpreter`, `test_an_undetermined_duty_dominates_the_settleable_parts_of_its_formula` |
| A `degree()` atom the grading does not score has no value, and is not a degree of zero | `test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero` |
| There is no many-valued reading of a temporal operator, so a graded atom under one is refused | `test_a_graded_atom_under_a_temporal_operator_is_refused_at_load` |
| A `degree()` atom under a comparison or arithmetic states a threshold and is refused | `test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`, `test_a_graded_comparison_the_author_wrote_is_still_refused` |
| The crisp parts of a graded formula mean what they mean everywhere else | `test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else` |
| The relational atom is the whole of a spec or no part of one | `test_the_atom_is_the_whole_spec_or_no_part_of_one`, `test_the_atom_classifies_into_its_own_fragment_and_not_into_logical` |
| No engine evaluates the relational atom against a decision record, and its fragment has no trace rung | `test_no_engine_can_evaluate_the_atom_against_a_decision_record`, `test_the_ladder_for_this_fragment_carries_no_trace_rung`, `test_a_log_only_system_is_never_answered_from_its_trace` |
| The protected values come from the declaration and never from the trace | `test_paired_replay_takes_no_protected_value_from_the_trace` |
| Unawareness is unattainable and not satisfied | `test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`, `test_the_two_cases_reach_different_verdicts_on_the_same_rules` |
| A replayed subset can refute a universal claim and cannot establish one | `test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach` |
| Only `always(f)` reduces to the state property, and nesting does not | `test_only_always_reaches_the_temporal_proof_rung`, `test_a_nested_temporal_operator_does_not_reduce` |
| The prefix temporal calls are rendered into the syntax the monitor actually reads | `test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it` |
| The monitor reads the spec as written, so implication is spelled with an arrow | `test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow` |
| Pack text is data and is never executed as Python | `test_pack_text_is_never_executed_as_python` |
| Every test this document names exists | `test_every_test_named_in_the_language_doc_exists` |

## Chapter 6 — Formalisation

| Claim | Test or operational warrant |
|---|---|
| A statutory reading is recorded as clause, quotation, formula, gates, classifications, and explicit limits rather than as a legal verdict | `docs/refinement.md`; `tests/test_docs_refinement.py` |
| Open-textured predicates are not silently settled by presence, and the refinement records what remains outside the formula | `test_no_shipped_pack_uses_either_open_texture_construct`; [`docs/theory/08-evidence.md`](08-evidence.md) §8.5 |
| A refinement's legal adequacy is an assumption, not a theorem of conformance | `docs/refinement.md`, *How to read column four* |

## Chapter 7 — Explanation

| Claim | Test |
|---|---|
| Jointly necessary reasons are not reported deleted by singleton probing | `test_the_per_fact_probe_alone_still_cannot_tell_them_apart`, `test_two_jointly_necessary_reasons_are_no_longer_reported_deleted` |
| An ignored reason is deleted only when the measured explanation is complete, while shared or unresolved facts remain non-deleted | `test_the_reason_the_engine_really_ignores_is_still_reported_deleted`, `test_a_reason_the_probe_cannot_separate_is_never_promoted_to_deleted` |
| The deletion probe carries its budget and does not reach the widened perturbation surface | `test_the_certificate_verdict_carries_its_probe_budget`, `test_the_deletion_probe_never_reaches_the_widened_perturbation` |
| Claimed semantics laws are measurements that can refute but cannot certify the claim | `test_the_battery_refutes_every_deviating_provenance_and_never_the_exact_one`, `test_neither_one_directional_variant_refutes_a_top_k_engine` |


## Chapter 8 — Evidence

| Claim | Test |
|---|---|
| Strength is the strict chain defined by `Strength`, and `None` is not a rung | `test_strength_lattice_ordering`, `test_strength_comparison_rejects_foreign_types`, `test_result_cannot_claim_more_than_its_evidence` |
| Evidence basis is unordered, derived from the duty, and cannot carry a disallowed rung | `test_the_evidence_bases_are_not_ordered`, `test_a_basis_is_never_compared_against_a_strength`, `test_the_basis_is_derived_from_the_duty_and_never_declared`, `test_a_result_cannot_carry_a_rung_its_basis_does_not_admit` |
| `BASIS_RUNGS` is the admissibility relation and its rows agree with the engine ladders | `test_the_basis_admits_exactly_the_rungs_the_ladder_can_reach`, `test_every_basis_admits_unattainable_so_the_capability_gate_is_never_bypassed` |
| Recounted evidence is an artifact rung, not a fifth basis | `test_a_recounted_reason_set_reports_one_rung_below_an_enumerated_one`, `test_a_recounted_reason_set_cannot_be_reported_at_the_enumerated_rung` |
| Grading is third-party evidence, uses the trace infimum, and does not become a verdict | `test_each_algebra_is_a_residuated_lattice_on_the_grid`, `test_the_three_algebras_disagree_about_a_conjunction_of_two_halves`, `test_the_degree_of_a_trace_is_the_infimum_of_its_records`, `test_a_grading_must_state_who_fixed_the_scale`, `test_a_result_carrying_a_degree_cannot_carry_a_strength` |
| Open-texture and graded shapes refuse unsupported readings rather than guessing | `test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero`, `test_a_graded_atom_under_a_temporal_operator_is_refused_at_load`, `test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`, `test_an_assessment_duty_reaches_no_engine_at_all` |
