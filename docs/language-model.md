# A language model as a system under test

The three systems in [`three-systems.md`](three-systems.md) answer one question: *how far does a
claim reach?* One duty, three surfaces, three rungs — `observed`, `probed`, `proved`.

This document answers a different one, on an axis underneath that: **which duties can be answered
about this system at all?** The system is a hosted language model prompted to write the
adverse-action notice for a credit file — the shape a great many deployed systems now have — and
it is checked against the whole `ecoa` pack rather than against one duty.

It does not add a rung. A language model you can call sits at `probed`, exactly where the
probabilistic scorer sits, and for the same reason: it can be re-run on inputs it has never seen
and cannot be read. What it adds is the fourth outcome, and the fourth outcome is the point.

> A language model can be **observed** on its decision log and **probed** through replay on the
> form of its notices — and is **unattainable** on reason fidelity, because it cannot supply an
> inference artefact. reasonsmith says which of those it did, and refuses the third rather than
> passing the system on the easier question.

The two duties in the last sentence are **the same clause**, 12 CFR 1002.9(b)(2), split across two
requirements in the pack. `ecoa_reg_b_1002_9_b_2_specific_reasons` asks whether a statement of
reasons is there and is not one of the two wordings the clause itself calls insufficient — a
language model passes it, and passes it on 200 replayed inputs.
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete` asks the other half of the same sentence:
whether the reasons the notice states are *all* the reasons the decision's own inference had. That
count is measured, never read — `engines/certificate.py` enumerates a decision's reasons from an
inference artefact and switches each off in turn — and a decoder has no such artefact. So the row
comes back `unattainable`, naming `artifact_logs_deleted_reason_count` as the signal it lacks.

Everyone else reports *we evaluated the LLM*. This reports: checked on a sampled region of 200
inputs, not proved; and here is the duty it could not answer at all.

| duty | outcome | why that one |
|---|---|---|
| `1002.9(a)(1)` timing of notice | `observed` | temporal property — the one rung above `observed` for a temporal duty reduces `always(f)` against exposed `logic()`, and a model you can only call exposes none ([`semantics.md`](semantics.md) §3.5) |
| `1002.9(a)(2)` written statement | `observed` | same |
| `1002.9(b)(2)` specific reasons | `probed`, carrying its budget | a state property, and the model is callable, so the replay search runs |
| `1002.9(b)(2)` principal reasons complete | `unattainable` | needs an inference artefact the system has none of |
| `1002.4(a)` no disparate treatment | *not evaluated* | a counterfactual property, and the model declares no input space, so there is no admissible value of the protected variable to replay a twin decision against — and no engine reads one out of the log ([`semantics.md`](semantics.md) §3, *counterfactual*) |

## The system

[`reasonsmith/examples/language_model_notices.py`](../src/reasonsmith/examples/language_model_notices.py)
is complete and runnable, and ships inside the package, so the command below runs after
`pip install reasonsmith` with no checkout. It takes one argument — a
`complete(prompt: str) -> str` — and that is the entire
interface to the model. There is no vendor SDK here, no client wrapper and no network call: a
deterministic stub stands in so the transcript below is reproducible from any install, and a real
model is a two-line substitution at the call site, spelled out in the module docstring.

The block below is stdout pasted unedited from a real run.
`tests/test_docs_language_model.py` re-runs the command and holds the committed block to its real
stdout, and asserts the ceiling separately.

```sh
python -m reasonsmith.examples.language_model_notices
```

```text
CONFORMANCE REPORT
system: notice-writer (language model, called through one text completion)
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa
headline: 6 requirements · 6 binding: 1 probed, 2 observed, 1 not evaluated, 2 unattainable

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): satisfied
    requires: artifact_logs_decision_record, artifact_logs_notification_latency_days, artifact_logs_counteroffer_not_accepted
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    requires: artifact_logs_decision_record, provenance_model_version
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))' satisfied at every decision step.
  [PROBED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Probed: no counterexample to 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' in 200 input(s) replayed through the system's own decide() (seed 0, generated by perturbing 2 recorded decision(s) over 12 field(s)). This is a bounded search, not a proof: the property is unchecked outside the inputs this budget names.
    probe budget: 200 input(s) replayed, seed 0, input space: applicant_id (3 values), artifact_logs_counteroffer_not_accepted (3 values), artifact_logs_decision_record (3 values), artifact_logs_notification_latency_days (6 values), artifact_logs_reason_explanation (3 values), credit_history_months (11 values), credit_score (11 values), debt_to_income (11 values), decision (3 values), delinquencies_24m (7 values), provenance_model_version (2 values), scope_statements_local_vs_global (2 values). Strategy: the recorded decisions are replayed first unmodified; remaining inputs use seeded random perturbation of one recorded decision, replacing one or two fields with values drawn from that field's candidate pool (the values the trace shows for it, the numeric literals of the property, and their immediate neighbours)
  [UNATTAINABLE] ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): inconclusive
    evidence basis: artifact — this duty is measured against the inference artefact behind a decision rather than against what the system decided. No trace holds that artefact and the enumeration is exact only on the one artefact it ran over, so the rungs above unattainable are recounted and probed, and neither observed nor proved is reachable however much the system exposes. Which of the two a verdict reaches is a fact about the artefact and not about the search: probed measures a reason set enumerated from a model encoding, recounted measures one the system recounted about its own inference.
    requires: artifact_logs_reason_explanation, artifact_logs_deleted_reason_count
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_deleted_reason_count
    summary: Unattainable as built: the system declares no capability to emit artifact_logs_deleted_reason_count, so no amount of testing can discharge this requirement. Determined from declared capabilities alone; the system was not executed.
  [UNATTAINABLE] ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
    requires: artifact_logs_incompleteness_notice_sent
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_incompleteness_notice_sent
    summary: Unattainable as built: the system declares no capability to emit artifact_logs_incompleteness_notice_sent, so no amount of testing can discharge this requirement. Determined from declared capabilities alone; the system was not executed.
  [NOT EVALUATED] ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive
    evidence basis: relational — this duty is a property of a pair of executions, and a decision record holds one. No length of decision log observes it, so the rungs it can reach are probed and proved; a system exposing only a log cannot discharge it, and that is a fact about the kind of property and not about how much the system exposed.
    requires: artifact_logs_decision_record, applicant_prohibited_basis
    domain limit: consumer-credit
    summary: Not evaluated: the system declares no input space, so there is no admissible value of 'applicant_prohibited_basis' to replay a decision against. This search never takes a protected value from the trace — a decision record is what happened to one applicant, and reading a counterfactual value out of it would make this duty a reason to log a protected attribute. Limit of this duty: it is invariance under one named variable holding all others fixed, so it is a property of treatment and says nothing about effects. A proxy is invisible to it — a rule set that never reads the protected variable and decides by postcode is satisfied here — and a disparate impact is not a thing it can find. It also reaches exactly one variable: a system answerable on several prohibited bases is answered here about the one this duty names.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

## What the ceiling is, and why no adapter lifts it

`logic()` is `None` here, so `proved` is not merely unreached — it is structurally unreachable. A
prompt is not a rule set and a decoder is not a formula; handing the solver a hand-written
paraphrase of either would prove a property of the paraphrase, and the system nobody deployed. The
test asserts that on the mechanism, not on the printed word: `logic()` returns `None`, and the
adequacy duty reports `unattainable` naming its missing signal rather than falling back to the
presence check that shares its clause.

The tempting repair is the one to refuse. A system author could declare
`artifact_logs_deleted_reason_count` and emit whatever the model says about its own reasons. That
would make the row evaluate, and it would be exactly the substitution the duty exists to reject —
a notice that names *a* reason standing in for one that names *the* reasons, and a self-report
standing in for a measurement. [`semantics.md`](semantics.md) §3 is the argument in full.

Raising this ceiling means changing the *system*, and there are now two ways to do it and no third.
Exposing an inference artefact the reasons can be enumerated from reaches `probed`. Exposing the
reasons the model **recounts** for a decision, together with a way to re-run it with a fact
withheld, reaches `recounted` — the rung below, held there because a probe over a recounted set can
show the answer does not depend on a reason the model named and can never show the set was all of
them (`artifacts/reason_trace.py`; [`semantics.md`](semantics.md) §3, *The inference artefact*).
Neither is a number the model writes about itself, which is the repair refused above. Nothing in the
adapter can do either, and nothing in the adapter should try — this system as shipped does neither,
which is why the row above is still `unattainable`.

## From a shell

The transcript above runs the system's own `main()`. The CLI reaches the same system:

```sh
reasonsmith check --system-module reasonsmith.examples.language_model_notices:system_under_test --pack ecoa
```

**`--system-module` imports the named module, which executes it** — with the stub behind the call,
so this too makes no network request. See [`three-systems.md`](three-systems.md), *From a shell*,
for what the flag does and what it refuses.
