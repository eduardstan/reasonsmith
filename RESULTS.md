# RESULTS — measured, not asserted

This is the evidence artifact for `reasonsmith`'s own claims: an environment was actually built, `torch` and `nesyarena[learning]` were actually installed, both suites were actually run, and the demo was executed twice and diffed.

## Summary of Measured Numbers

| Category | Target / Metric | Measured Result | Details / Status |
|---|---|---|---|
| **`reasonsmith` Suite** | `pytest` | **35 passed**, 0 failed, 0 skipped | Counts the v0.1 suite as it stood at the measured commit — **stale by construction**, see the note under this table |
| | `ruff check .` | **0 findings** | All linter checks passed cleanly |
| **`nesyarena` Suite** | Pytest Header | **107 collected items** / 3 skipped modules | Measured with `torch` & `torchvision` installed |
| *(with torch present)* | Pytest Summary | **1 failed, 100 passed, 5 skipped, 4 errors** | Execution time: 23.04s |
| | `test_learning_parity.py` | 5 passed, 2 skipped | Skipped tests require `ltn` (`backends` extra) |
| | `test_e6_findings.py` | 4 errors | Error fixture requires `ltn.fuzzy_ops` |
| | `test_oracle.py` | 1 failed | Failed test requires `problog` (`oracles` extra) |
| | Uncollected modules | 3 skipped | `deeplog`, `deepproblog`, `problog_kbest` |
| **Demo Execution** | Determinism (2 runs) | **Byte-identical** (0 diff lines) | `md5sum`: `c5976971e24a86886f1e0ad54f0b9ce9` (561 lines) |
| | ECOA Credit (`APP-1042`) | Record: **`COMPLETE`** (5/5 fields)<br>Certificate: **`FAIL`** (gap -0.225799) | 5 reasons found by exact WMC, 1 used by top-1 engine, 4 deleted by truncation |
| | GDPR Clinical (`PT-0731`) | Record: **`COMPLETE`** (3/3 fields)<br>Certificate: **`FAIL`** (gap -0.260424) | 5 reasons found by exact WMC, 1 used by top-1 engine, 4 deleted by truncation |
| **Table 19 Conformance** | Design A (Confidence Varies) | Coverage gap: **0.0000**<br>Fidelity gap: **+0.0535**<br>Retained share gap: **+0.2802** | Typical: cov 0.3333, fid 0.7807, ret 0.7731<br>Atypical: cov 0.3333, fid 0.7272, ret 0.4929 |
| | Design B (Multiplicity Varies) | Coverage gap: **+0.3000**<br>Fidelity gap: **+0.1472**<br>Retained share gap: **+0.1129** | Typical: cov 0.5000, fid 0.7831, ret 0.7292<br>Atypical: cov 0.2000, fid 0.6360, ret 0.6163 |
| | Signal Stability | **0.3333** across 4 windows | Delinquency signal drift swaps stated reason from C01 to C03 |

**What the `35 passed` figure does and does not count.** Every number in this file is a measurement taken at `reasonsmith` commit `9411ca60a70c0d4f72f12a038e01d9d65c70c03f`, and none of them is re-measured by later work — that is what makes them reconstructible, and it is also what makes this one stale. Section 2's `35 passed` counts the suite as it stood then, and the v0.2 work added since (`verdict.py`, `spec.py`, `sut.py`, `report.py`, `adapters/`, `engines/`, `cli.py`, the `packs/` requirement packs, and `tests/test_v02_core.py` plus `tests/test_v02_stage2.py`) adds tests to that number. Read `35` as the v0.1 suite's count at that commit, never as the current suite's: for the current count, run `pytest` yourself. Those v0.2 files are new alongside v0.1 rather than changes to it — `evidence.py`, `certificate.py`, `conformance.py` and `demo.py` are untouched — so section 1 (nesyarena's suite) and section 3 (the demo output) still describe the code as it is today.

---

## Environment & Provenance

Every number in this file is copied from a command's real output. The exact commands are given so a stranger can reproduce every one of them from `reasonsmith` commit `9411ca60a70c0d4f72f12a038e01d9d65c70c03f` (branch `fm/rs-prove-it`), the commit every measurement below was taken at. Every number here is that commit's and is not re-measured by later work.

| Component / Tool | Version / Hash Details |
|---|---|
| **Date of Measurement** | 2026-07-31 |
| **Operating System** | Linux 7.0.0-28-generic |
| **Python** | 3.12.9 |
| **numpy** | 2.5.1 |
| **torch** | 2.13.0+cu130 |
| **torchvision** | 0.28.0+cu130 |
| **pytest** | 9.1.1 |
| **ruff** | 0.16.1 |
| **reasonsmith** | `0.1.0` (editable install), commit `9411ca60a70c0d4f72f12a038e01d9d65c70c03f` |
| **nesyarena** | `0.1.0.dev0`, pinned commit `fdf0d5eb54c7af181e15b94d3b68d5d6bb7712ec` (repinned to `57720fa212834689692e171882272140f1d1fed7`, see note below) |

### Repin Note (2026-07-31)

The measurements below were taken against `nesyarena` commit `fdf0d5eb54c7af181e15b94d3b68d5d6bb7712ec`. `nesyarena`'s owner then rewrote its git history to strip AI co-authorship trailers, which gave every commit a new hash: that old commit is no longer reachable from `nesyarena`'s default branch `main`, so `pip install` can no longer resolve it from there and `pyproject.toml` now pins `57720fa212834689692e171882272140f1d1fed7` instead, which is reachable from `main`.

(The old commit currently survives on the temporary rollback ref `refs/heads/backup/pre-coauthor-strip`, which is expected to be deleted; nothing here relies on it — reconstructibility stands on `main` alone.)

The hash changed, the content did not: both commits' `git cat-file -p <sha> | grep tree` report the identical tree `d050c86ef83b01bac972a0af3afa6f629a4a9972`, verified directly against both commits before this note was written. The figures below are still the original run's, quoted unedited. What was re-run against the new pin is exactly this and nothing more: `reasonsmith`'s own `pytest` suite (35 passed), `ruff check .` (no findings), and `python -m reasonsmith.demo` (561 lines, two runs, identical) — see "Full transcript"; none of those moved. Section 1's figures are `nesyarena`'s *own* suite (`collected 107 items / 3 skipped`, `1 failed, 100 passed, 5 skipped, 4 errors`), measured under the old pin `fdf0d5eb54c7af181e15b94d3b68d5d6bb7712ec` in the separate torch environment, and they were **not** re-run against `57720fa212834689692e171882272140f1d1fed7`. They are expected to be unchanged because the two commits share the tree `d050c86ef83b01bac972a0af3afa6f629a4a9972` and so install identical content — but that is an expectation from tree identity, not a measurement. The old pin is kept in the table above for the historical record of what was actually run.

### Build and Reproduction Commands

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                                   # reasonsmith + pinned nesyarena, no torch

# nesyarena's own suite needs its tests/ and experiments/ directories, which the pip-installed
# wheel does not carry (pip installs the built package, not the whole git repo). To run
# nesyarena's own suite at the exact pinned commit, its repo is cloned separately and checked
# out to that commit, then its optional extras are installed into the same venv:
git clone https://github.com/eduardstan/nesyarena /path/to/nesyarena-src
cd /path/to/nesyarena-src && git checkout 57720fa212834689692e171882272140f1d1fed7  # was fdf0d5e..., same tree
pip install -e ".[learning,reporting,dev]"   # torch, torchvision + pyyaml/matplotlib needed
                                              # only so tests/test_e6_findings.py can *collect*
```

`nesyarena[learning]` (`torch>=2.4`, `torchvision>=0.20`) is what the task and the README's prior caveat named. `reporting` (`pyyaml`, `matplotlib`) was added on top of that because `tests/test_e6_findings.py` imports `yaml` at module scope — without it the module still fails to collect, for a reason that has nothing to do with torch. Two further nesyarena extras, `oracles` (`problog`, `pysdd`) and `backends` (`ltn`, `deeplog`, `deepproblog`), were **not** installed — that was not in scope here, and the gaps it leaves are reported below rather than papered over.

`reasonsmith`'s own `pyproject.toml` is untouched: `torch` is not a declared dependency of this package, only of the separate nesyarena checkout used to measure nesyarena's own suite.

---

## 1. `nesyarena`'s Own Suite, with Torch Present

```sh
cd /path/to/nesyarena-src && python -m pytest -q -rA
```

The same suite, invoked as `python -m pytest -o addopts=""`, printed these two lines, quoted verbatim — so the counts here are pytest's own, not derived:

```text
collected 107 items / 3 skipped
============= 1 failed, 100 passed, 5 skipped, 4 errors in 23.04s ==============
```

The 3 in `107 items / 3 skipped` are whole modules skipped at collection time, which pytest counts separately from the 107 collected items; the 5 in the summary line is those 3 plus the 2 tests skipped while running, both of them listed by file and line in the transcript below.

Both modules the README used to say could not even be collected — `tests/test_e6_findings.py` and `tests/test_learning_parity.py` — collect and run now. `test_learning_parity.py` runs 5 tests to a pass; `test_e6_findings.py` is the one module that still cannot complete, and not because of torch:

- **`test_learning_parity.py`**: 5 passed, 2 skipped (`could not import 'ltn'`) — those two need the `backends` extra (LTNtorch), not `learning`.
- **`test_e6_findings.py`**: 4 errors, all `ModuleNotFoundError: No module named 'ltn'` — the module collects fine, but every test shares a fixture that calls `run_treatment`, which reaches `BatchStructure.ltn_prod`, which lazy-imports `ltn.fuzzy_ops`. Same missing dependency as above.
- **`test_oracle.py::test_wmc_against_problog_battery`**: 1 failed, `ModuleNotFoundError: No module named 'problog'` — needs the `oracles` extra.
- **3 whole modules skipped at collection time**: `test_deeplog_adapter.py` (`deeplog`) and `test_deepproblog_standalone.py` (`deepproblog`), both in the `backends` extra, and `test_problog_kbest.py` (`problog`), in the `oracles` extra. These are the `/ 3 skipped` in pytest's collection header, not part of the 107 collected items.

Full pass/fail list (`pytest -q -rA`, one line per test):

```text
...................EEEE..................................ss............. [ 67%]
..................F................                                      [100%]
=========================== short test summary info ============================
PASSED tests/test_adapters.py::test_reference_adapter_satisfies_protocol
PASSED tests/test_adapters.py::test_reference_adapter_infer_matches_direct_path
PASSED tests/test_adapters.py::test_reference_adapter_on_recursive_program
PASSED tests/test_adapters.py::test_scallop_compile_g1_shape
PASSED tests/test_adapters.py::test_scallop_compile_recursive_tc_keeps_constants_quoted
PASSED tests/test_adapters.py::test_fact_key_is_atom_repr
PASSED tests/test_adapters.py::test_render_idb_zero_arity
PASSED tests/test_benchmarks.py::test_expected_batteries_and_counts
PASSED tests/test_benchmarks.py::test_proofs_rederive_from_programs
PASSED tests/test_benchmarks.py::test_oracle_values_recompute
PASSED tests/test_benchmarks.py::test_oracle_gradients_recompute
PASSED tests/test_benchmarks.py::test_anchor_values
PASSED tests/test_benchmarks.py::test_atom_roundtrip
PASSED tests/test_e1_regression.py::test_registered_crossover_endpoints
PASSED tests/test_e1_regression.py::test_h3_ranking_flips_between_c1_and_c2
PASSED tests/test_e1_regression.py::test_opposite_monotone_sensitivities
PASSED tests/test_e2_regression.py::test_registered_horizons_n_plus_one
PASSED tests/test_e2_regression.py::test_registered_chain8_values
PASSED tests/test_e2_regression.py::test_registered_h7_divergence_value
PASSED tests/test_engine.py::test_cyclic_history_parity_with_toy
PASSED tests/test_engine.py::test_chain8_truncation_parity_with_toy
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[0]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[1]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[2]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[3]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[4]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[5]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[6]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[7]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[8]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[9]
PASSED tests/test_engine.py::test_theorem1_iterates_equal_proof_aggregation_nonidempotent[10]
PASSED tests/test_engine.py::test_theorem1_on_chain_maxprod
PASSED tests/test_engine.py::test_prop4_truncation_zero_below_horizon_exact_at_horizon
PASSED tests/test_engine.py::test_converge_on_idempotent_algebras
PASSED tests/test_engine.py::test_sumprod_on_cyclic_diverges_past_one
PASSED tests/test_generators.py::test_g1_parity_with_toy_fixtures
PASSED tests/test_generators.py::test_g1_proofs_derived_from_program_one_per_rule
PASSED tests/test_generators.py::test_chain_family_structure
PASSED tests/test_generators.py::test_cyclic_family_is_the_section5_instance
PASSED tests/test_generators.py::test_surrogate_scores_drive_the_bias_law
PASSED tests/test_ir.py::test_edb_idb_partition
PASSED tests/test_ir.py::test_g1_proofs_are_one_per_rule_at_depth_1
PASSED tests/test_ir.py::test_chain_proof_depth_equals_length
PASSED tests/test_ir.py::test_cyclic_enumeration_terminates_and_loops_add_support
PASSED tests/test_ir.py::test_multiplicity_view_keeps_repeated_facts
PASSED tests/test_ir.py::test_explosion_guard
PASSED tests/test_ir.py::test_deterministic_support_order
PASSED tests/test_learning_parity.py::test_value_and_grad_parity_with_reference_suts
PASSED tests/test_learning_parity.py::test_clamp_blackout_in_autograd
PASSED tests/test_learning_parity.py::test_batched_equals_per_sample
PASSED tests/test_learning_parity.py::test_truth_matches_wmc_at_extremes
PASSED tests/test_learning_parity.py::test_straight_through_clamp_matches_f3_semantics
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[0]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[1]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[2]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[3]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[4]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[5]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[6]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[7]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[8]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[9]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[10]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[11]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[12]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[13]
PASSED tests/test_oracle.py::test_wmc_value_parity_with_toy[14]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[0]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[1]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[2]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[3]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[4]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[5]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[6]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[7]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[8]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[9]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[10]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[11]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[12]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[13]
PASSED tests/test_oracle.py::test_wmc_grad_parity_with_toy[14]
PASSED tests/test_oracle.py::test_analytic_grad_equals_finite_difference
PASSED tests/test_oracle.py::test_empty_and_certain_proofs
PASSED tests/test_oracle.py::test_graph_oracle_parity_with_toy
PASSED tests/test_suts.py::test_sut_value_and_grad_parity_with_toy
PASSED tests/test_suts.py::test_lse_parity_with_toy
PASSED tests/test_suts.py::test_prop1_addmult_overcounts_within_bonferroni
PASSED tests/test_suts.py::test_prop1_clamp_blackout
PASSED tests/test_suts.py::test_prop2_topk_undercounts_by_at_most_dropped_mass
PASSED tests/test_suts.py::test_prop3_lse_bias_law_exact_for_equal_scores
PASSED tests/test_suts.py::test_prop3_lse_bias_bounded_for_unequal_scores
PASSED tests/test_suts.py::test_minmax_subgradient_is_one_hot
PASSED tests/test_suts.py::test_exact_wmc_is_zero_error_by_definition
PASSED tests/test_witness_metrics.py::test_witness_parity_with_toy
PASSED tests/test_witness_metrics.py::test_exact_wmc_has_no_witness
PASSED tests/test_witness_metrics.py::test_fidelity_profile_ordering
PASSED tests/test_witness_metrics.py::test_depth_horizon_is_n_plus_one
PASSED tests/test_witness_metrics.py::test_gradient_liveness_semantics
SKIPPED [1] tests/test_deeplog_adapter.py:7: could not import 'deeplog': No module named 'deeplog'
SKIPPED [1] tests/test_deepproblog_standalone.py:9: could not import 'deepproblog': No module named 'deepproblog'
SKIPPED [1] tests/test_problog_kbest.py:7: could not import 'problog': No module named 'problog'
SKIPPED [1] tests/test_learning_parity.py:101: could not import 'ltn': No module named 'ltn'
SKIPPED [1] tests/test_learning_parity.py:123: could not import 'ltn': No module named 'ltn'
ERROR tests/test_e6_findings.py::test_exact_transfers_near_zero_on_treatment
ERROR tests/test_e6_findings.py::test_addmult_harmed_on_treatment - ModuleNot...
ERROR tests/test_e6_findings.py::test_exact_equals_addmult_exactly_on_control
ERROR tests/test_e6_findings.py::test_top1_harmed_on_control - ModuleNotFound...
FAILED tests/test_oracle.py::test_wmc_against_problog_battery - ModuleNotFoun...
```

(Pasted verbatim from an 80-column terminal output.)

---

## 2. `reasonsmith`'s Own Suite

```sh
cd reasonsmith && ruff check . && python -m pytest -q -rA
```

`ruff check .`: **All checks passed!**

`pytest`: **35 passed, 0 failed, 0 skipped** — the progress line and the `-rA` report that command printed, verbatim. This is the v0.1 suite at the measured commit and is not the current count; see "What the `35 passed` figure does and does not count" above.

```text
...................................                                      [100%]
==================================== PASSES ====================================
=========================== short test summary info ============================
PASSED tests/test_reasonsmith.py::test_schema_is_the_six_rows_of_table_7
PASSED tests/test_reasonsmith.py::test_every_schema_entry_traces_to_the_table
PASSED tests/test_reasonsmith.py::test_complete_record_is_complete
PASSED tests/test_reasonsmith.py::test_withheld_field_is_reported_incomplete_and_named
PASSED tests/test_reasonsmith.py::test_blank_and_none_are_missing_not_present
PASSED tests/test_reasonsmith.py::test_field_outside_the_row_is_rejected
PASSED tests/test_reasonsmith.py::test_attachments_do_not_fill_a_gap
PASSED tests/test_reasonsmith.py::test_every_record_carries_its_limits
PASSED tests/test_reasonsmith.py::test_unknown_duty_is_refused
PASSED tests/test_reasonsmith.py::test_exact_inference_certifies_clean
PASSED tests/test_reasonsmith.py::test_top_k_deletes_reasons_and_the_certificate_names_them
PASSED tests/test_reasonsmith.py::test_exact_inference_recovers_what_top_k_dropped
PASSED tests/test_reasonsmith.py::test_both_domains_lose_reasons_under_top_k
PASSED tests/test_reasonsmith.py::test_a_perturbed_engine_that_drops_a_reason_fails
PASSED tests/test_reasonsmith.py::test_a_perturbed_engine_that_keeps_every_reason_still_fails_on_value
PASSED tests/test_reasonsmith.py::test_certificate_carries_its_limits
PASSED tests/test_reasonsmith.py::test_a_reason_with_no_private_fact_is_not_certified_either_way
PASSED tests/test_reasonsmith.py::test_a_query_with_no_reason_is_never_a_pass
PASSED tests/test_reasonsmith.py::test_an_engine_answer_with_no_enumerated_reason_is_attributed_to_the_gap
PASSED tests/test_reasonsmith.py::test_no_check_scores_a_certificate_that_measured_nothing
PASSED tests/test_reasonsmith.py::test_an_unmeasured_group_never_wins_the_per_group_comparison
PASSED tests/test_reasonsmith.py::test_a_gap_needs_two_groups_that_produced_the_metric
PASSED tests/test_reasonsmith.py::test_an_all_empty_cohort_reports_nothing_to_measure
PASSED tests/test_reasonsmith.py::test_a_probe_with_no_signal_is_not_counted_as_live
PASSED tests/test_reasonsmith.py::test_registered_hypothesis_confidence_form_is_not_supported
PASSED tests/test_reasonsmith.py::test_registered_hypothesis_multiplicity_form_is_supported
PASSED tests/test_reasonsmith.py::test_coverage_and_fidelity_agree_with_the_certificate
PASSED tests/test_reasonsmith.py::test_drift_moves_the_stated_reason_and_stability_reports_it
PASSED tests/test_reasonsmith.py::test_score_factors_are_the_measured_scores_or_absent
PASSED tests/test_reasonsmith.py::test_the_whole_report_runs
PASSED tests/test_reasonsmith.py::test_record_json_roundtrip_preserves_incomplete_status_and_missing_fields
PASSED tests/test_reasonsmith.py::test_record_json_cites_the_table_7_row_the_human_output_cites
PASSED tests/test_reasonsmith.py::test_record_json_stringifies_values_json_has_no_type_for
PASSED tests/test_reasonsmith.py::test_record_dict_does_not_hand_out_the_module_schema_to_mutate
PASSED tests/test_reasonsmith.py::test_certificate_json_roundtrip_preserves_verdict_and_reasons
```

---

## 3. `python -m reasonsmith.demo`, Twice, Diffed

```sh
python -m reasonsmith.demo > run1.txt
python -m reasonsmith.demo > run2.txt
diff run1.txt run2.txt          # empty
md5sum run1.txt run2.txt        # c5976971e24a86886f1e0ad54f0b9ce9 for both
```

**The two runs are byte-identical: `diff` produces no output, both files hash to `c5976971e24a86886f1e0ad54f0b9ce9`.** The module docstring's "reproducible byte for byte" claim holds, measured, not assumed.

### Empirical Details of Key Finding Figures

From the credit demonstration (ECOA/Reg B, Table 7 row 4), decision `APP-1042`:

- **Exact inference** (bounded proof enumeration + exact WMC) finds **5 reasons**.
- The **deployed top-1 engine** uses **1** of them.
- **4 of the 5 are deleted** — named individually (C02–C05), each with the exact-inference probability mass it carries (0.019804, 0.005262, 0.004166, 0.008995) and confirmation that deleting each one's fact leaves the engine's output unchanged.
- The Table 7 evidence record for the decision is emitted as **`EVIDENCE RECORD [COMPLETE]`** — all 5 required fields are present.
- The paired reason-deletion certificate for the decision is **`REASON-DELETION CERTIFICATE [FAIL]`** — exact value 0.991399, engine value 0.765600, gap −0.225799 (tolerance 1e-9).

The same pattern reproduces on the clinical demonstration (GDPR Art. 22, Table 7 row 3, decision `PT-0731`): 5 reasons found, 1 used, 4 deleted, record `COMPLETE`, certificate `FAIL` (exact 0.991424 vs. engine 0.731000, gap −0.260424).

### Conformance / Table 19 Figures

#### Design A — Confidence Varies, Reason Structure Fixed

| Group | n | Measured | Reasons Found | Reasons Used | Reasons Deleted | Coverage | Fidelity | Retained Share | Diversity |
|---|---|---|---|---|---|---|---|---|---|
| **typical** | 4 | 4 | 3.0000 | 1.0000 | 2.0000 | 0.3333 | 0.7807 | 0.7731 | 0.3333 |
| **atypical** | 4 | 4 | 3.0000 | 1.0000 | 2.0000 | 0.3333 | 0.7272 | 0.4929 | 0.3333 |

Gaps (best group minus worst):
- `fidelity`: **+0.0535** (best typical, worst atypical)
- `retained_share`: **+0.2802** (best typical, worst atypical)
- `coverage`: **+0.0000** (no gap)

#### Design B — Reason Multiplicity Varies, Confidence Fixed

| Group | n | Measured | Reasons Found | Reasons Used | Reasons Deleted | Coverage | Fidelity | Retained Share | Diversity |
|---|---|---|---|---|---|---|---|---|---|
| **typical** | 4 | 4 | 2.0000 | 1.0000 | 1.0000 | 0.5000 | 0.7831 | 0.7292 | 0.5000 |
| **atypical** | 4 | 4 | 5.0000 | 1.0000 | 4.0000 | 0.2000 | 0.6360 | 0.6163 | 0.2000 |

Gaps (best group minus worst):
- `fidelity`: **+0.1472** (best typical, worst atypical)
- `retained_share`: **+0.1129** (best typical, worst atypical)
- `coverage`: **+0.3000** (best typical, worst atypical)

#### Registered Hypothesis Outcome

- **Confidence Form (Design A):** NOT supported (coverage gap 0.0000 — top-k keeps a fixed proof count regardless of confidence scaling).
- **Multiplicity Form (Design B):** Supported (coverage gap 0.3000 — a case tripping 5 reasons and told 1 keeps 1/5th; a case tripping 2 keeps 1/2).

### Stability Across Windows

One unchanged applicant file, four windows, a strengthening delinquency signal: the top-1 stated reason changes from `C01` (windows 0–1) to `C03` (windows 2–3). **Stability across the four windows: 0.3333** (1.0 would mean the same reason every window).

### Full Transcript Provenance

The complete, unedited output of both demo runs (identical to each other) is 561 lines, available in [`docs/example-output.md`](docs/example-output.md). Regenerate it with `python -m reasonsmith.demo` from commit `9411ca60a70c0d4f72f12a038e01d9d65c70c03f`.

**Re-checked after repin to nesyarena `57720fa212834689692e171882272140f1d1fed7` (2026-07-31):** `python -m reasonsmith.demo`, run twice against the new pin, still produces the same 561 identical lines, `pytest` still reports 35 passed, and `ruff check .` still reports no findings.

---

## What Changed From Prior Torch Caveats

The README used to say `torch` was never installed and that, without it, "98 tests pass while `tests/test_e6_findings.py` and `tests/test_learning_parity.py` fail to collect". That caveat is now replaced by the measured numbers above: torch is installed in the environment used to produce this file, both named modules collect and run, and pytest collects 107 items (plus 3 modules skipped at collection time), not 98.

Two nesyarena tests still cannot pass here — not for lack of torch, but for lack of `ltn` (LTNtorch) and `problog`, which live behind nesyarena's separate `backends` and `oracles` extras and were out of scope for this task. `torch` remains outside reasonsmith's own declared dependencies (`pyproject.toml` is unchanged); it was installed only in the separate environment used to measure nesyarena's suite here.
