# One duty, three systems, three rungs

How does a model — neural, probabilistic, symbolic — get fed into this tool and have a legal
property verified on it? By writing an adapter that says what the system exposes. Nothing else
about the system matters, and nothing else is asked of it.

The three files in [`docs/adapters/`](adapters/) are complete, runnable systems. Each is a
plausible credit decisioner; each exposes a different surface; each is checked against the **same
binding duty**. They come back at three different rungs of the evidence lattice.

| system | file | what it exposes | rung reached |
|---|---|---|---|
| neural risk network, served behind an inference API | [`neural_scorer.py`](adapters/neural_scorer.py) | `decisions()` — an exported decision log, nothing else | `observed` |
| probabilistic log-odds scorer, in-process | [`probabilistic_scorer.py`](adapters/probabilistic_scorer.py) | `decisions()` + `decide(case)` replay | `probed`, carrying its search budget |
| symbolic underwriting rule set | [`symbolic_rules.py`](adapters/symbolic_rules.py) | `decisions()` + `logic()` | `proved`, over every input the constraints admit |

Every block below is stdout pasted unedited from a real run.
`tests/test_docs_three_systems.py` re-runs all three commands and holds each committed block to
its real stdout, and asserts the neural system's ceiling separately.

## The duty

**ECOA / Regulation B, 12 CFR 1002.9(b)(2)** — shipped as
`ecoa_reg_b_1002_9_b_2_specific_reasons` in the `ecoa` pack:

> The statement of reasons for adverse action required by paragraph (a)(2)(i) of this section must
> be specific and indicate the principal reason(s) for the adverse action.

Three things made it the right duty for this demonstration, and it is worth saying which:

- **It is binding.** `binding = true` in the pack: a statutory obligation on any creditor taking
  adverse action, not a recital. A headline table built on an interpretive item invites the reply
  that it is not even a legal obligation. This one is.
- **It is limited to no regulatory class.** `scope = ""`, so it reaches a system that has declared
  none, and the same duty genuinely applies to all three systems below. A duty scoped to
  `high-risk` would have come back *not applicable* for any system that did not declare itself
  into that class, and the table would have been about a declaration rather than about evidence.
- **Its property is a state property.** The spec is
  `present(artifact_logs_reason_explanation) and present(provenance_model_version) and
  present(scope_statements_local_vs_global)` — a formula about a single decision. That is what
  lets all three rungs be in play: the solver and the replay search each reason about one decision
  at a time. A temporal duty (`always(...)`) never rises above `observed` in this build, whatever
  the system exposes, because no engine here reasons over a trace-wide formula — see
  [`semantics.md`](semantics.md) §3.5.

## 1. Neural — `observed`

The risk network is served behind an inference API. The audit host holds the decision log the
serving stack exported and nothing else: no weights, no replay endpoint. There is no `logic()`
either, and not because the vendor is uncooperative — a weight matrix carries no formula for a
solver to reason over.

```sh
python docs/adapters/neural_scorer.py
```

```text
CONFORMANCE REPORT
system: risk-net (neural, served behind an inference API)
declared scope: undeclared
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 observed

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    summary: Observed over 3 decision(s): every required signal (artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded either because no regulatory class was declared for the system at all, or because the class that was declared is not the one the requirement is limited to. This tool never infers that class, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope line before reading a not-applicable result.
```

## 2. Probabilistic — `probed`

The log-odds scorer is in this process. The auditor can hand it an input it has never seen and
watch what it does, so the duty is checked against decisions the system never made — but only 200
of them, generated by perturbing the two it did make. It cannot be read: the posterior is
arithmetic over calibrated weights, and a hand-written paraphrase handed to the solver would prove
a property of the paraphrase.

Note what the transcript carries that the previous one did not: a **probe budget**. Trials, seed,
strategy, and the size of the pool each field was drawn from. `probed` is the rung most easily
misread as `proved`, so a probed verdict cannot be constructed at all without the bound that
produced it.

```sh
python docs/adapters/probabilistic_scorer.py
```

```text
CONFORMANCE REPORT
system: bayes-risk (probabilistic, replayable in-process)
declared scope: undeclared
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 probed

REQUIREMENT FINDINGS:
  [PROBED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    summary: Probed: no counterexample to 'present(artifact_logs_reason_explanation) and present(provenance_model_version) and present(scope_statements_local_vs_global)' in 200 input(s) replayed through the system's own decide() (seed 0, generated by perturbing 2 recorded decision(s) over 10 field(s)). This is a bounded search, not a proof: the property is unchecked outside the inputs this budget names.
    probe budget: 200 input(s) replayed, seed 0, input space: applicant_id (3 values), artifact_logs_reason_explanation (2 values), credit_history_months (11 values), credit_score (11 values), debt_to_income (11 values), decision (2 values), delinquencies_24m (7 values), posterior_default (11 values), provenance_model_version (2 values), scope_statements_local_vs_global (2 values). Strategy: the recorded decisions are replayed first unmodified; remaining inputs use seeded random perturbation of one recorded decision, replacing one or two fields with values drawn from that field's candidate pool (the values the trace shows for it, the numeric literals of the property, and their immediate neighbours)

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded either because no regulatory class was declared for the system at all, or because the class that was declared is not the one the requirement is limited to. This tool never infers that class, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope line before reading a not-applicable result.
```

## 3. Symbolic — `proved`

The underwriting policy *is* the system: an ordered rule set over declared variables, with the
admissible input space stated as constraints. `RulesAdapter` executes those same statements in
`decide()` and exposes them from `logic()`, so a proof and a replay cannot come to be about
different programs. The duty stops being a question about the decisions the system happened to
log.

Read the last sentence of the summary. The proof holds over the rationals, not over the float64
arithmetic the system actually runs — the engine states its own limit rather than letting the word
"proved" carry more than it earned.

```sh
python docs/adapters/symbolic_rules.py
```

```text
CONFORMANCE REPORT
system: underwriting-rules (symbolic, logic exposed)
declared scope: undeclared
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 proved

REQUIREMENT FINDINGS:
  [PROVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    summary: Proved for all inputs: formal solver verified requirement 'present(artifact_logs_reason_explanation) and present(provenance_model_version) and present(scope_statements_local_vs_global)' holds across all valid inputs under system constraints. Limit of this proof: `real` is the exact rationals to the solver and IEEE-754 float64 to the system, so this holds over the rationals and not over the arithmetic the system runs. A property that depends on rounding can be proved here and still fail in execution.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded either because no regulatory class was declared for the system at all, or because the class that was declared is not the one the requirement is limited to. This tool never infers that class, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope line before reading a not-applicable result.
```

## What the rung is, and what it is not

**The rung is a fact about what the system exposes.** `report._engine_ladder` collects every
engine the property's fragment *and* the system's exposed surface allow, and
`evaluate_requirement` takes the strongest evidence any of them actually produced. Which word a
pack author typed in `formalism` does not decide it; neither does the vendor's confidence in the
model.

**The rung is not a score.** The neural system is not failing. All three verdicts above are
`satisfied`. What differs is how far the claim reaches: `observed` reaches the three logged
decisions and no further, `probed` reaches 200 replayed inputs and no further, `proved` reaches
every input the declared constraints admit.

**The rung is not a grade of compliance.** Whether any of this discharges a legal duty is a
determination this tool does not make, and every transcript above says so in its own LIMITS
paragraph.

**The ceiling is real.** The neural system cannot reach `probed` or `proved` as built, and no
amount of care in writing its adapter will change that: `probed` needs something to re-run and
`proved` needs something to read. Getting it there means changing the *system* — exposing a replay
endpoint, or exporting a symbolic surrogate and auditing that surrogate for fidelity — not
changing the adapter. `test_the_neural_system_cannot_be_raised_above_observed` pins that ceiling so
nobody quietly lifts it later.

## Adapting your own system

Start from whichever of the three files is closest, and change the system, not the plumbing:

- a decision log and nothing else → [`JSONLAdapter`](../src/reasonsmith/adapters/jsonl.py); pass
  `declared_capabilities` when the system genuinely declares what it emits, and leave it out when
  the capability set is only what one sample trace happened to carry — the report words the two
  findings differently on purpose.
- a callable model, `predict()` or `decide()` or a plain function →
  [`CallableAdapter`](../src/reasonsmith/adapters/callable.py).
- a rule set, decision list or constraint system →
  [`RulesAdapter`](../src/reasonsmith/adapters/rules.py).

None of them asks you to declare a rung. You declare the signals your system emits; the tool works
out what can be established about them.
