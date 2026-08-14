# Here is my system — what can you tell me about it?

This document is for the reader who arrives with a system of their own. It is not an authoring
guide: [`authoring-packs.md`](authoring-packs.md) is for someone writing duties and
[`authoring-engines.md`](authoring-engines.md) for someone writing an engine. It is also not
[`three-systems.md`](three-systems.md), which walks three *shipped example* systems to demonstrate
the evidence ladder. This one answers the adopter's question: what does this tool need from my
system, what will it then say about it, and what will it refuse to say.

Everything below points at the document that owns each claim rather than restating it. Where this
page and [`semantics.md`](semantics.md) appear to disagree, `semantics.md` is right — the same rule
[`refinement.md`](refinement.md) keeps.

## Read this before you trust a green report

**Every verdict here rests on what your system declares about itself, and nothing here checks those
declarations.** The signals it says it can emit, the semantics its inference claims to implement,
the regulatory class and decision domain you pass on the command line: all of them are taken at
their word.

The cost is measured, not hypothesised. Finding 1 of
[`findings-nesyarena.md`](findings-nesyarena.md), *The unflattering findings*,
reports two systems whose decisions contradict the semantics they declare — one returning a
different decision from its claimed semantics on half the battery — reported `satisfied` on every
checkable duty, with verdicts identical to an exact oracle's. It is right to, given what the packs
ask; a record duty asks whether a field is present, never whether the number the field explains is
the number the system claims to compute.

Read a satisfied row as *the record has the fields*, never as *the system computes what it says it
computes*. Objective 5 of [`ROADMAP.md`](../ROADMAP.md) closed this for **one artefact family**:
`gdpr_recital71_error_risk_minimised` reads an approximation error reasonsmith measures from the
inference artefact `artifact()` returns, not one the system wrote into its own record. Every other
system — a decision log, a callable, a language model, a recounted reason trace — is `unattainable`
on that duty, so for it the sentence above still holds in full.

No run here is a compliance determination. `reasonsmith.report.LIMITS` travels on every report and
says so in the report's own words; nothing on this page may be read past it.

## 1. Four ways a system comes in

What you can be told is decided by what your system exposes, and by nothing else — not by the
vendor's confidence in it, and not by which word a pack author typed in `formalism`
(`report._engine_ladder`; [`semantics.md`](semantics.md) §3.5).

| what you have | how it comes in | reaches | cannot reach |
|---|---|---|---|
| a decision log | `--system <file.jsonl>` | `observed` | anything about a decision the log does not hold; and no property of a *pair* of executions, at any log length |
| a callable you can re-run | `--system-module m:attr` exposing `decide(case)` | `probed` | a claim over every admissible input — the search is bounded and the bound travels on the verdict |
| declared rules | `--system-module m:attr` exposing `logic()` | `proved` | anything the declaration itself gets wrong, and anything that depends on rounding |
| an inference artefact | `--system-module m:attr` exposing `artifact(decision)` | `probed`, or `recounted` where the reasons are the system's own account | whether the reasons a notice states are adequate, correct, or the ones a person would call principal |

Each row is a ceiling on what can be *established*, never a grade: all four can be `satisfied`, and
what differs is how far the claim reaches ([`semantics.md`](semantics.md) §4, *What a comparison
does not mean*).

**A decision log.** `--system decisions.jsonl` constructs [`JSONLAdapter`](../src/reasonsmith/adapters/jsonl.py),
which exposes neither `decide()` nor `logic()`, so it cannot rise above `observed` whatever the
system behind the log can do. Pass `--capabilities <file>` when the system genuinely declares what
it emits: without it the capability set is derived from the trace, and the report words the two
findings differently on purpose (`cli.read_capability_declaration`). The worked example of the
ceiling is `neural_scorer.py` in [`three-systems.md`](three-systems.md), *Neural*, pinned
by `test_the_neural_system_cannot_be_raised_above_observed`.

**A callable you can re-run.** Wrap it in [`CallableAdapter`](../src/reasonsmith/adapters/callable.py)
and expose it through `--system-module`, which **imports and executes** the named module. The duty
is then checked against decisions your system never made, and a `probed` result cannot be
constructed at all without the search budget that produced it — trials, seed, strategy, input space
(`PROBE_BUDGET_KEY`). `probabilistic_scorer.py` is the worked case, and
[`language-model.md`](language-model.md) is the same rung reached by a language model behind one
`complete(prompt) -> str`: a model you can call adds no rung.

### A callable with an input space (and a fairness duty)

`CallableAdapter` is enough when the question is about the records your callable emits. Its public
constructor is exactly `CallableAdapter(target, declared_capabilities, test_inputs)`: the first
argument is the callable (or an object with `decide()`/`predict()`), the second is the set of
signals it emits, and the third is the finite set of cases to replay. This small, runnable example
shows the extra surface a counterfactual duty needs. Save it as a module and run it through
`--system-module`, or execute it directly.

    from dataclasses import replace

    from reasonsmith.adapters.callable import CallableAdapter
    from reasonsmith.report import check_conformance
    from reasonsmith.spec import load_pack


    class FairCallable(CallableAdapter):
        # CallableAdapter still supplies target, declared_capabilities and test_inputs.  This method
        # adds the declared input space that a counterfactual proof/replay needs.
        def logic(self):
            return {
                "variables": {
                    "income": "int",
                    "applicant_prohibited_basis": "int",
                    "artifact_logs_decision_record": "bool",
                },
                "constraints": [
                    "income >= 0",
                    "income <= 200000",
                    "applicant_prohibited_basis >= 0",
                    "applicant_prohibited_basis <= 1",
                ],
                "rules": [
                    "artifact_logs_decision_record = income >= 30000",
                ],
                "computes": ["artifact_logs_decision_record"],
            }


    def target(case):
        return {"artifact_logs_decision_record": case["income"] >= 30000}


    def system_under_test():
        sut = FairCallable(
            target,
            declared_capabilities={"artifact_logs_decision_record"},
            test_inputs=[{"income": 25000}, {"income": 50000}],
        )
        sut.system_domains = ("consumer-credit",)
        return sut


    def main():
        sut = system_under_test()
        pack = load_pack("ecoa")
        req = pack.get_requirement("ecoa_reg_b_1002_4_a_no_disparate_treatment")
        report = check_conformance(
            sut,
            replace(pack, id="one-duty", requirements=(req,)),
            system_name="fair-callable",
        )
        print(report.render_text())


    if __name__ == "__main__":
        main()


With the file saved as `fair_callable.py`, either run `python fair_callable.py` or let the CLI
import its factory (the module is imported and executed):

    python -m reasonsmith.cli check \
      --system-module fair_callable:system_under_test \
      --pack ecoa --system-domain consumer-credit

The `applicant_prohibited_basis` values `0` and `1` are admissible because `logic()` declares
that variable and constrains its input domain. They are **not** in `test_inputs`, in the returned
records, or in `declared_capabilities`: admissible protected values are part of the declared input
space, not production logging. The fairness duty additionally needs `logic()` to expose the rules,
the `variables`/`constraints` input space, and `computes` to identify the outcome. A plain
`CallableAdapter(target, declared_capabilities, test_inputs)` with no such `logic()` remains a
replayable callable and can reach `probed`, but is correctly not evaluated for this
counterfactual question. Declaring a protected variable is not a claim that a log contains it.

**Declared rules.** [`RulesAdapter`](../src/reasonsmith/adapters/rules.py) executes your rules in
`decide()` and exposes the same statements from `logic()`, so a proof and a replay cannot be about
different programs. This is the only route to a claim over every input your constraints admit. What
it does not reach: the proof is about the rules you declared, so a declaration that is not the
deployed decision procedure buys a proof about something else — and `real` is exact rationals to the
solver and IEEE-754 to your system, which the engine states in its own summary.
`symbolic_rules.py` is the worked case ([`three-systems.md`](three-systems.md), *Symbolic*).

**An inference artefact.** Two duties are measured against the inference *behind* a decision rather
than against what was decided — reason adequacy, and whether the system's answer is the semantics it
claims — and both need `artifact(decision)` returning an
[`InferenceArtifact`](../src/reasonsmith/artifacts/__init__.py). Their two signals are the only ones
reasonsmith measures rather than reads from a record. Two families ship:
[`GroundProgramArtifact`](../src/reasonsmith/artifacts/ground_program.py), whose reasons are
enumerated from a model encoding (`reasons_are_exact = True`, so `probed`), and
[`ReasonTraceArtifact`](../src/reasonsmith/artifacts/reason_trace.py), the reasons a system
*recounts* for one decision, each tested by suppressing its facts and re-running the system
(`recounted`). Silence claims the weaker rung. The artefact must also declare whether its inference
is monotone; one that does not is reported *not evaluated* and never downgraded to the presence
check sharing its clause ([`semantics.md`](semantics.md) §3, *The inference artefact*;
[`theory/07-explanation.md`](theory/07-explanation.md) for what a `deleted` reason is). The semantics duty
needs one thing more of the family and nothing more of you: the artefact's own `exact_value()` must
compute the semantics your adapter claims, which the ground-program family does for `distribution
semantics` and the recounted family does for none — so a reason trace is reported *unattainable*
there, and an adapter claiming any other member of `spec.CLAIMED_SEMANTICS` is reported *not
evaluated* naming the claim, never violated ([`semantics.md`](semantics.md) §3, *The first shipped
duty whose deviation is measured rather than declared*).

`--system` and `--system-module` name two different systems and refuse each other, as does
`--capabilities` against `--system-module`. Adapt from whichever of the four files under
[`../src/reasonsmith/examples/`](../src/reasonsmith/examples/) is closest, and change the system,
not the plumbing: none of them declares a rung.

## 2. What you must supply, and how to find out

A duty is reported `unattainable` when the signals it needs are not in your system's capability
set. That is a set difference and nothing more — `report.analyze_unattainable` computes it, and it
does so **without executing your system**.

So the practical loop is two commands. Run the pack and read the `MISSING SIGNALS` lines; then ask
any duty what it needs and why. (Every command on this page is spelled `python -m reasonsmith.cli`,
which is what the transcripts were produced with; an install also puts `reasonsmith` on your path,
so `reasonsmith explain ...` is the same command.)

```sh
python -m reasonsmith.cli explain ecoa_reg_b_1002_9_a_1_timing_of_notice
```

```text
REQUIREMENT ecoa_reg_b_1002_9_a_1_timing_of_notice
pack: ecoa

CLAUSE
  ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)
  "A creditor shall notify an applicant of action taken within: (i) 30 days after receiving a
  completed application concerning the creditor's approval of, counteroffer to, or adverse
  action on the application; (ii) 30 days after taking adverse action on an incomplete
  application, unless notice is provided in accordance with paragraph (c) of this section; (iii)
  30 days after taking adverse action on an existing account; or (iv) 90 days after notifying
  the applicant of a counteroffer if the applicant does not expressly accept or use the credit
  offered."

FORMULA
  always(present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))

RATIONALE
  Every decision the log records was notified within the deadline its own paragraph sets: 30
  days under (i)-(iii), or 90 days where the record says the applicant did not accept a
  counteroffer, which is the only case (iv) reaches. Both numbers are the clause's own; neither
  is this pack's.

FRAGMENT
  temporal

REQUIRES
  artifact_logs_decision_record
  artifact_logs_notification_latency_days
  artifact_logs_counteroffer_not_accepted

REFINEMENT
  What this formalisation does not capture, from docs/refinement.md:
  When the clock started. The clause counts from three different events; the property reads one
  latency number the system computes about itself, so which event it was measured from is the
  system's own claim and no engine checks it. A record may now *state* which event started its
  clock (`sut.TIME_DOMAIN_KEY`, `docs/semantics.md` §2), and this property still does not read
  it: the recorded events are evidence waiting for a metric semantics, not a check this row has
  gained. The paragraph (ii) exception — *unless notice is provided in accordance with paragraph
  (c)* — is not modelled, so a lawful incomplete-application notice under 1002.9(c) is still
  held to the 30-day bound. `artifact_logs_counteroffer_not_accepted` is read under the flag
  encoding of `docs/semantics.md` §2, where any present non-numeric value becomes true, so a
  record that carries prose in that field takes the 90-day branch. Both numbers are the clause's
  own, not this pack's (`docs/authoring-packs.md`, *a number in a spec*). **And the shipped
  example systems demonstrate the tool; none is a fixture for this duty, and none will be built
  to.** Against `reasonsmith.examples.symbolic_rules` this duty is proved satisfied with its
  trigger firing, and its ninety-day counteroffer branch is vacuously passed: that system's own
  seven-day batching bounds every notice under thirty days — `notification_queue_days <= 7`, and
  the notice lands a day after the batch, so `artifact_logs_notification_latency_days <= 8` —
  which makes the first disjunct true of every admissible input and the second (the only branch
  the 90-day bound reaches) replaceable by any formula whatsoever without moving the verdict. No
  shipped system exercises that branch, and none will be built to: a system engineered to light
  up a branch is a fixture, and a fixture becomes the thing the tool is tuned against — the
  failure this repository's whole design is arranged to avoid. The adapters of `docs/three-
  systems.md` and `docs/language-model.md` exist to demonstrate the tool, not to exercise the
  duties.
```

`REQUIRES` is the list your system has to emit for the duty to be answered at all; `FORMULA` is what
will be checked over it; `REFINEMENT` is what the formalisation deliberately left out, so you know
what a satisfied verdict on this duty will not have established. The command runs no engine, reads
no system and changes no verdict. `docs/` is not in the wheel, so a reader who only ran
`pip install reasonsmith` is *told* where the refinement record lives instead of being shown a blank
section.

Two things the capability set does not decide. `not applicable` is a different answer, reached by
two gates that are about reach rather than evidence: the regulatory class (`--system-scope`) and
the decision domain (`--system-domain`), neither of which reasonsmith ever infers. And a signal your
system can emit but never did in the log you supplied is `unattainable` on a *trace basis*, which
the summary distinguishes from a declared one — the instruction differs (§4 below).

## 3. A run that refuses, and the field that changes it

A log a notice service could plausibly export: two adverse actions, five fields each. Only
`decision_id` is not a pack signal — it is what lets a violated finding name the record it is about
instead of a step index.

`decisions.jsonl`, one JSON object per line:

```jsonl
{"decision_id": "APP-2201", "artifact_logs_decision_record": {"id": "APP-2201", "result": "adverse_action"}, "artifact_logs_reason_explanation": "Your application failed to achieve a qualifying score on our credit scoring system.", "provenance_model_version": "notice-svc-2026.06", "artifact_logs_notification_latency_days": 9}
{"decision_id": "APP-2202", "artifact_logs_decision_record": {"id": "APP-2202", "result": "adverse_action"}, "artifact_logs_reason_explanation": "Debt-to-income ratio above the policy limit for the amount requested.", "provenance_model_version": "notice-svc-2026.06", "artifact_logs_notification_latency_days": 14}
```

Save it beside the command and run:

```sh
python -m reasonsmith.cli check --system decisions.jsonl --pack ecoa --system-name notice-service --system-domain consumer-credit
```

```text
CONFORMANCE REPORT
system: notice-service
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa
headline: 6 requirements · 6 binding: 1 observed, 1 not evaluated, 4 unattainable

REQUIREMENT FINDINGS:
  [UNATTAINABLE] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): inconclusive
    requires: artifact_logs_decision_record, artifact_logs_notification_latency_days, artifact_logs_counteroffer_not_accepted
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_counteroffer_not_accepted
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_counteroffer_not_accepted, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    requires: artifact_logs_decision_record, provenance_model_version
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))' satisfied at every decision step.
  [UNATTAINABLE] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): inconclusive
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    MISSING SIGNALS: scope_statements_local_vs_global
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for scope_statements_local_vs_global, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): inconclusive
    evidence basis: artifact — this duty is measured against the inference artefact behind a decision rather than against what the system decided. No trace holds that artefact and the enumeration is exact only on the one artefact it ran over, so the rungs above unattainable are recounted and probed, and neither observed nor proved is reachable however much the system exposes. Which of the two a verdict reaches is a fact about the artefact and not about the search: probed measures a reason set enumerated from a model encoding, recounted measures one the system recounted about its own inference.
    requires: artifact_logs_reason_explanation, artifact_logs_deleted_reason_count
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_deleted_reason_count
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_deleted_reason_count, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
    requires: artifact_logs_incompleteness_notice_sent
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_incompleteness_notice_sent
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_incompleteness_notice_sent, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [NOT EVALUATED] ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive
    evidence basis: relational — this duty is a property of a pair of executions, and a decision record holds one. No length of decision log observes it, so the rungs it can reach are probed and proved; a system exposing only a log cannot discharge it, and that is a fact about the kind of property and not about how much the system exposed.
    requires: artifact_logs_decision_record, applicant_prohibited_basis
    domain limit: consumer-credit
    summary: Not evaluated: the system exposes no decide(), so there is no twin decision to run. A counterfactual is what the system would have decided, and a decision log records only what it did — no trace, however long, establishes one. Limit of this duty: it is invariance under one named variable holding all others fixed, so it is a property of treatment and says nothing about effects. A proxy is invisible to it — a rule set that never reads the protected variable and decides by postcode is satisfied here — and a disparate impact is not a thing it can find. It also reaches exactly one variable: a system answerable on several prohibited bases is answered here about the one this duty names.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

Six duties, one answered. The run exits **0**, and nothing on it is a finding against the system:

- **four `unattainable`** — the notice service does not log a counteroffer flag, a scope statement,
  an incompleteness notice, or an inference artefact. Each names the signal it wanted. The last of
  them is not a logging omission: `artifact_logs_deleted_reason_count` is measured from an artefact
  a decision log has none of, which is the fourth row of §1's table.
- **one `not evaluated`** — 1002.4(a) is a property of a *pair* of executions, and no length of log
  holds a second one. More log will not help; a replayable `decide()` would.
- **one `observed` satisfied** — over the two decisions supplied and no further.

Now supply one more field, `scope_statements_local_vs_global`, in the same file and change
nothing else:

```jsonl
{"decision_id": "APP-2201", "artifact_logs_decision_record": {"id": "APP-2201", "result": "adverse_action"}, "artifact_logs_reason_explanation": "Your application failed to achieve a qualifying score on our credit scoring system.", "provenance_model_version": "notice-svc-2026.06", "artifact_logs_notification_latency_days": 9, "scope_statements_local_vs_global": "local"}
{"decision_id": "APP-2202", "artifact_logs_decision_record": {"id": "APP-2202", "result": "adverse_action"}, "artifact_logs_reason_explanation": "Debt-to-income ratio above the policy limit for the amount requested.", "provenance_model_version": "notice-svc-2026.06", "artifact_logs_notification_latency_days": 14, "scope_statements_local_vs_global": "local"}
```

Same command again:

```sh
python -m reasonsmith.cli check --system decisions.jsonl --pack ecoa --system-name notice-service --system-domain consumer-credit
```

```text
CONFORMANCE REPORT
system: notice-service
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa
headline: 6 requirements · 6 binding: 1 observed, 1 violated, 1 not evaluated, 3 unattainable

REQUIREMENT FINDINGS:
  [UNATTAINABLE] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): inconclusive
    requires: artifact_logs_decision_record, artifact_logs_notification_latency_days, artifact_logs_counteroffer_not_accepted
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_counteroffer_not_accepted
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_counteroffer_not_accepted, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    requires: artifact_logs_decision_record, provenance_model_version
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): violated
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Violated over 2 decision(s): state property 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' failed at decision step(s) [0].
    offending record: decision APP-2201 (step 0)
  [UNATTAINABLE] ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): inconclusive
    evidence basis: artifact — this duty is measured against the inference artefact behind a decision rather than against what the system decided. No trace holds that artefact and the enumeration is exact only on the one artefact it ran over, so the rungs above unattainable are recounted and probed, and neither observed nor proved is reachable however much the system exposes. Which of the two a verdict reaches is a fact about the artefact and not about the search: probed measures a reason set enumerated from a model encoding, recounted measures one the system recounted about its own inference.
    requires: artifact_logs_reason_explanation, artifact_logs_deleted_reason_count
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_deleted_reason_count
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_deleted_reason_count, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
    requires: artifact_logs_incompleteness_notice_sent
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_incompleteness_notice_sent
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_incompleteness_notice_sent, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [NOT EVALUATED] ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive
    evidence basis: relational — this duty is a property of a pair of executions, and a decision record holds one. No length of decision log observes it, so the rungs it can reach are probed and proved; a system exposing only a log cannot discharge it, and that is a fact about the kind of property and not about how much the system exposed.
    requires: artifact_logs_decision_record, applicant_prohibited_basis
    domain limit: consumer-credit
    summary: Not evaluated: the system exposes no decide(), so there is no twin decision to run. A counterfactual is what the system would have decided, and a decision log records only what it did — no trace, however long, establishes one. Limit of this duty: it is invariance under one named variable holding all others fixed, so it is a property of treatment and says nothing about effects. A proxy is invisible to it — a rule set that never reads the protected variable and decides by postcode is satisfied here — and a disparate impact is not a thing it can find. It also reaches exactly one variable: a system answerable on several prohibited bases is answered here about the one this duty names.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

One field, and the run now exits **2**: `APP-2201`'s notice says the applicant *failed to achieve a
qualifying score*, one of the two statements 12 CFR 1002.9(b)(2) itself calls insufficient. The
breach was there in the first run and the tool could not see it, because a signal the duty needed
was missing from the log.

That is the shape of an adoption. The first report was not a clean bill of health; it was mostly a
list of questions the evidence could not answer, and the exit code — 0 — said only that nothing
was *proved* wrong. Only a violation fails a `check` run (`cli.main`); unattainable, not applicable
and not evaluated all exit 0 and are findings to read, never verdicts against the system.

## 4. The four outcomes, and which one you are looking at

[`semantics.md`](semantics.md) §4, *Four outcomes that must never collapse*, is the authority: it
carries the table of `not applicable` (both gates), `unattainable` (both bases), `not evaluated` and
`violated`, and for each one what happened and **what to do next**. Read it there rather than here;
this page will not restate it, because a second copy is a copy that goes stale.

Two things about it are worth an adopter's attention specifically.

**`unattainable` is a strength, not a verdict.** It sits at the bottom of the lattice
`unattainable < observed < recounted < probed < proved` ([`semantics.md`](semantics.md) §4), and
the verdict beside it is `inconclusive`. It says *this system, on this evidence, cannot show me* —
which is why its two bases send you to two different places: a declared-basis miss means change the
system, a trace-basis miss means supply a longer trace or a capability declaration first.

**`not evaluated` is a gap in the audit, not a finding about the system.** Some of them are fixed by
better evidence, and some cannot be fixed by any amount of the same *kind* of evidence — the
counterfactual duty over a log-only system is the second sort. The summary says which.

## Where to go next

- [`what-this-does-not-do.md`](what-this-does-not-do.md) — the four things this tool cannot do, before you scope an adoption around it.
- [`three-systems.md`](three-systems.md) and [`language-model.md`](language-model.md) — the worked systems behind §1's table.
- [`refinement.md`](refinement.md) — per duty, what the formalisation left out; `reasonsmith explain` prints the same column.
- [`authoring-packs.md`](authoring-packs.md) — once your system answers the shipped packs and you need a duty they do not carry.

One further command exists and is **not** part of adopting a system: `reasonsmith published-counts`
emits this tree's own counts — packs, requirements, verbatim statutory quotes, rungs — as JSON, with
the provenance of every date, and `--output FILE` writes it instead of printing it. It reads no
system, runs no engine and reports no duty; it exists so the website and this repository cannot
disagree about how many duties ship. The committed artefact is
[`published-counts.json`](published-counts.json). Nothing on this page needs it.
