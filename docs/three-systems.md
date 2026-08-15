# One duty, three systems, three rungs

> **Demonstration only:** The reports below are demonstrations on frozen synthetic data — not evidence about any real decision.

How does a model — neural, probabilistic, symbolic — get fed into this tool and have a legal
property verified on it? By writing an adapter that says what the system exposes. Nothing else
about the system matters, and nothing else is asked of it.

The three files in [`reasonsmith.examples`](../src/reasonsmith/examples/) are complete, runnable
systems, and they ship inside the package, so every command below runs after `pip install
reasonsmith` with no checkout. Each is a
plausible credit decisioner; each exposes a different surface; each is checked against the **same
binding duty**. They come back at three different rungs of the evidence lattice.

| system | file | what it exposes | rung reached |
|---|---|---|---|
| neural risk network, served behind an inference API | [`neural_scorer.py`](../src/reasonsmith/examples/neural_scorer.py) | `decisions()` — an exported decision log, nothing else | `observed` |
| probabilistic log-odds scorer, in-process | [`probabilistic_scorer.py`](../src/reasonsmith/examples/probabilistic_scorer.py) | `decisions()` + `decide(case)` replay | `probed`, carrying its search budget |
| symbolic underwriting rule set | [`symbolic_rules.py`](../src/reasonsmith/examples/symbolic_rules.py) | `decisions()` + `logic()` | `proved`, over every input the constraints admit |

> **Produced with reasonsmith `0.9.2` — the version of the tree these blocks were generated
> from.** Every block below ran on that version, and the pins hold the page to it. If the same
> command prints differently under your own install, your `reasonsmith` is a different version
> than this page describes — check `pip show reasonsmith` before reading anything into the
> difference. A mismatch against an older release means this page is ahead of your package, not
> that your install is broken; upgrade to `0.9.2` or newer and re-run before comparing.

Every block below is stdout pasted unedited from a real run.
`tests/test_docs_three_systems.py` re-runs all three commands and holds each committed block to
its real stdout, and asserts the neural system's ceiling separately.

## The duty

**ECOA / Regulation B, 12 CFR 1002.9(b)(2)** — shipped as
`ecoa_reg_b_1002_9_b_2_specific_reasons` in the `ecoa` pack:

> The statement of reasons for adverse action required by paragraph (a)(2)(i) of this section must
> be specific and indicate the principal reason(s) for the adverse action. Statements that the
> adverse action was based on the creditor's internal standards or policies or that the applicant,
> joint applicant, or similar party failed to achieve a qualifying score on the creditor's credit
> scoring system are insufficient.

Three things made it the right duty for this demonstration, and it is worth saying which:

- **It is binding.** `binding = true` in the pack: a statutory obligation on any creditor taking
  adverse action, not a recital. A headline table built on an interpretive item invites the reply
  that it is not even a legal obligation. This one is.
- **It is limited to no regulatory class.** `scope = ""`, so it reaches a system that has declared
  none, and the same duty genuinely applies to all three systems below. A duty scoped to
  `high-risk` would have come back *not applicable* for any system that did not declare itself
  into that class, and the table would have been about a declaration rather than about evidence.
- **It is limited to one decision domain, and all three systems are in it.** `domains =
  ["consumer-credit"]`, and each of the three declares `system_domains = ("consumer-credit",)` —
  they are consumer lenders, so the declaration is true of them and the duty genuinely governs
  them. This is the one place the table *does* rest on a declaration, and it must: a system that
  declared no domain would be reported *not applicable* here rather than judged, which is the point
  of the gate (`docs/authoring-packs.md`, *the decision-domain vocabulary is yours, not the
  regulation's*). What must not be read into the three rungs below is that any of them was reached
  by declaring a domain — the domain decides whether the duty is answered at all, and the rung
  decides how strongly, from what the system exposes and nothing else.
- **Its property is a state property.** The spec is an implication about a *single decision*:
  where that decision carries a statement of reasons, the statement names the model version and the
  scope it speaks for and is not one of the two the clause itself calls insufficient. That is what
  lets all three rungs be in play — the solver and the replay search each reason about one decision
  at a time. A temporal duty reaches the solver only where it reduces to a property of one decision,
  which `always(f)` does and no other shape here does — see [`semantics.md`](semantics.md) §3.5 and
  §3, *`proved`, over a trace*.

  It is worth knowing what this duty used to be, because the change is the reason the demonstration
  is worth more than it was. Until recently the property was a conjunction of `present()` atoms:
  *the reason field is not blank*, and nothing else. All three systems below satisfied it, and a
  system whose every reason read `"n/a"` would have satisfied it too — so `proved` was a strong
  claim about a weak property. The clause supplies its own **negative** constraint, naming two
  statements that are insufficient, and the property now checks it, so the symbolic system's
  `proved` verdict says something a reader should care about: over every input its constraints
  admit, it never writes either of them. What no engine here decides is whether what it writes
  instead is *specific* — see [`refinement.md`](refinement.md), the 12 CFR 1002.9(b)(2) row.

  The antecedent is the trigger the clause states in its own first words: (b)(2) governs the
  statement *required by paragraph (a)(2)(i)*, so a creditor that lawfully disclosed the right to
  request reasons instead has none yet and is not in breach. Where that antecedent holds nowhere in
  the evidence an engine had, the duty is reported **not evaluated** rather than satisfied, naming
  the trigger that never fired — so a log that was checked and found clean never reads the same as
  one the duty imposed nothing on ([`semantics.md`](semantics.md) §4).

## 1. Neural — `observed`

The risk network is served behind an inference API. The audit host holds the decision log the
serving stack exported and nothing else: no weights, no replay endpoint. There is no `logic()`
either, and not because the vendor is uncooperative — a weight matrix carries no formula for a
solver to reason over.

```sh
python -m reasonsmith.examples.neural_scorer
```

```text
CONFORMANCE REPORT
system: risk-net (neural, served behind an inference API)
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 observed · all positives observed-only

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Observed over 3 decision(s): state monitor for 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' satisfied at every decision step.
    Scope of this positive result: this formal property was satisfied only on the supplied 3 decision records at the observed evidence rung; this run did not establish that the trace is complete, representative, or unfiltered, and it did not determine legal adequacy or compliance outside those records.
    Formalized subset only — see explain ecoa_reg_b_1002_9_b_2_specific_reasons rationale.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of the independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about; or the Seoul pack self-asserted frontier_ai_status is undeclared or not-frontier. This tool infers neither the class nor the domain, and it does not infer frontier status, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope, domain, and frontier-status lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against. A wrong frontier declaration remains an audited-system overclaim.
```

## 2. Probabilistic — `probed`

The log-odds scorer is in this process. The auditor can hand it an input it has never seen and
watch what it does, so the duty is checked against decisions the system never made — but only 200
of them, generated by perturbing the two it did make. It cannot be read: the posterior is
arithmetic over calibrated weights, and a hand-written paraphrase handed to the solver would prove
a property of the paraphrase.

The same system, from a shell and against the whole `ecoa` pack, is
`reasonsmith check --system-module reasonsmith.examples.probabilistic_scorer:system_under_test --pack ecoa`
— which **imports and executes** that module. See [From a shell](#from-a-shell) below.

Note what the transcript carries that the previous one did not: a **probe budget**. Trials, seed,
strategy, and the size of the pool each field was drawn from. `probed` is the rung most easily
misread as `proved`, so a probed verdict cannot be constructed at all without the bound that
produced it.

```sh
python -m reasonsmith.examples.probabilistic_scorer
```

```text
CONFORMANCE REPORT
system: bayes-risk (probabilistic, replayable in-process)
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 probed

REQUIREMENT FINDINGS:
  [PROBED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Probed: no counterexample to 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' in 200 input(s) replayed through the system's own decide() (seed 0, generated by perturbing 2 recorded decision(s) over 10 field(s)). This is a bounded search, not a proof: the property is unchecked outside the inputs this budget names.
    Scope of this positive result: this formal property was satisfied only on the bounded search (200 input(s) replayed, seed 0, input space: applicant_id (3 values), artifact_logs_reason_explanation (2 values), credit_history_months (11 values), credit_score (11 values), debt_to_income (11 values), decision (2 values), delinquencies_24m (7 values), posterior_default (11 values), provenance_model_version (2 values), scope_statements_local_vs_global (2 values); strategy: the recorded decisions are replayed first unmodified; remaining inputs use seeded random perturbation of one recorded decision, replacing one or two fields with values drawn from that field's candidate pool (the values the trace shows for it, the numeric literals of the property, and their immediate neighbours)) at the probed evidence rung; this run did not establish that the searched inputs are complete, representative, or unfiltered, and it did not determine legal adequacy or compliance outside that search.
    Formalized subset only — see explain ecoa_reg_b_1002_9_b_2_specific_reasons rationale.
    probe budget: 200 input(s) replayed, seed 0, input space: applicant_id (3 values), artifact_logs_reason_explanation (2 values), credit_history_months (11 values), credit_score (11 values), debt_to_income (11 values), decision (2 values), delinquencies_24m (7 values), posterior_default (11 values), provenance_model_version (2 values), scope_statements_local_vs_global (2 values). Strategy: the recorded decisions are replayed first unmodified; remaining inputs use seeded random perturbation of one recorded decision, replacing one or two fields with values drawn from that field's candidate pool (the values the trace shows for it, the numeric literals of the property, and their immediate neighbours)

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of the independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about; or the Seoul pack self-asserted frontier_ai_status is undeclared or not-frontier. This tool infers neither the class nor the domain, and it does not infer frontier status, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope, domain, and frontier-status lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against. A wrong frontier declaration remains an audited-system overclaim.
```

## 3. Symbolic — `proved`

The underwriting policy *is* the system: an ordered rule set over declared variables, with the
admissible input space stated as constraints. `RulesAdapter` executes those same statements in
`decide()` and exposes them from `logic()`, so a proof and a replay cannot come to be about
different programs. The duty stops being a question about the decisions the system happened to
log.

`logic()` also declares the *direction* of each variable — `computes` names the ones the system
produces, and the rest of `variables` are *at most* the ones the application supplies, since a type
table can also name a signal the system merely logs. `RulesAdapter` derives
that from the rules themselves, so this system says it computes what its rules assign and nothing
more. It is what lets the engine tell an input it may quantify over from a name the system has no
notion of, and refuse a proof about the latter rather than answer it from a constant the solver
invented ([`semantics.md`](semantics.md) §3.5).

The same system, from a shell and against the whole `ecoa` pack, is
`reasonsmith check --system-module reasonsmith.examples.symbolic_rules:system_under_test --pack ecoa`
— which **imports and executes** that module. See [From a shell](#from-a-shell) below.

Read the last sentence of the summary. The proof holds over the rationals, not over the float64
arithmetic the system actually runs — the engine states its own limit rather than letting the word
"proved" carry more than it earned.

```sh
python -m reasonsmith.examples.symbolic_rules
```

```text
CONFORMANCE REPORT
system: underwriting-rules (symbolic, logic exposed)
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa:ecoa_reg_b_1002_9_b_2_specific_reasons
headline: 1 requirements · 1 binding: 1 proved

REQUIREMENT FINDINGS:
  [PROVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Proved for all inputs: formal solver verified requirement 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' holds across all valid inputs under system constraints. Limit of this proof: `real` is the exact rationals to the solver and IEEE-754 float64 to the system, so this holds over the rationals and not over the arithmetic the system runs. A property that depends on rounding can be proved here and still fail in execution.
    Scope of this positive result: this formal property was satisfied only on all inputs admitted by the system's declared logic and constraints at the proved evidence rung; this run did not establish that those assumptions match production or the world, and it did not determine legal adequacy or compliance outside those assumptions.
    Formalized subset only — see explain ecoa_reg_b_1002_9_b_2_specific_reasons rationale.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of the independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about; or the Seoul pack self-asserted frontier_ai_status is undeclared or not-frontier. This tool infers neither the class nor the domain, and it does not infer frontier status, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope, domain, and frontier-status lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against. A wrong frontier declaration remains an audited-system overclaim.
```

## From a shell

The three transcripts above run each system's own `main()`, which narrows the pack to the one duty
so the reader sees one finding. The CLI reaches exactly the same systems, against a whole pack:

```sh
reasonsmith check --system-module reasonsmith.examples.symbolic_rules:system_under_test --pack ecoa
reasonsmith check --system-module reasonsmith.examples.probabilistic_scorer:system_under_test --pack ecoa
reasonsmith check --system-module reasonsmith.examples.neural_scorer:system_under_test --pack ecoa
```

**`--system-module` imports the named module, which executes it**, and takes the attribute after
the colon as the system under test — the `module:attribute` spelling pytest's `-p` and gunicorn's
application path use. The module is searched on `sys.path`, which includes the current directory —
the three modules above are installed with the package, so those commands need no checkout, and
your own module resolves the same way from the directory you run in. The attribute may be a
`SystemUnderTest` or, as in all three files here, a zero-argument factory returning one.

That is what makes `probed` and `proved` reachable from a shell at all: `--system <decisions.jsonl>`
constructs a log-reading adapter, which exposes neither `decide()` nor `logic()`, so it cannot rise
above `observed` whatever the system behind the log can do. The two flags name different systems and
refuse each other, as does `--capabilities`, which speaks for a log's adapter while an imported
system declares its own capabilities.

The rungs are unchanged by the route: run against the whole `ecoa` pack, the symbolic system still
comes back `proved` and the probabilistic one `probed` on `ecoa_reg_b_1002_9_b_2_specific_reasons`.
Of the pack's four other duties, `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` is unattainable
on all three systems, because none of these adapters exposes the inference artefact its
`artifact_logs_deleted_reason_count` is measured from — and that duty is never answered by anything
weaker (`docs/semantics.md` §3, *certificate*). The two `temporal` duties are unattainable on the
probabilistic and neural systems, which declare no `artifact_logs_decision_record`. The symbolic
system declares one, and there the two split on the shape of the property rather than on the
surface: `1002.9(a)(1)` is `always(f)` over a state property, so it reduces and the solver proves it,
while `1002.9(a)(2)` reads `artifact_logs_right_to_reasons_disclosure` — a signal these rules never
assign, so the presence atom cannot be proved and the duty lands on the trace at `observed`. The
pack's fifth duty is the one relational one: `1002.4(a)` comes back `unattainable` on all three
systems, and the engine reports that rather than `satisfied` — none of these lenders reads an
`applicant_prohibited_basis` the property could hold fixed, and unawareness of one is not a
discharge (`docs/semantics.md` §3, *counterfactual*). Two
temporal duties, one system, two different rungs, and neither of them a fact about the word
`temporal`.

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
