# What reasonsmith found in a real neuro-symbolic system

Every conformance report this project has shipped so far ran against a system written to
illustrate a point. This one does not. It runs against
[`nesyarena`](https://github.com/eduardstan/nesyarena) 0.1.0 — the package `reasonsmith` already
depends on for its exact WMC oracle, whose `suts.py` holds reference implementations of
provenance semantics that deployed neuro-symbolic frameworks actually use — checked against the
shipped GDPR, EU AI Act and ECOA / Regulation B packs, unchanged.

The evidence is in [`nesyarena-conformance-report.md`](nesyarena-conformance-report.md), generated
by `python docs/build_nesyarena_report.py` and held to that script byte-for-byte by
`tests/test_nesyarena_conformance.py`. This document is the account of what it found. The
unflattering parts are the longer half, and they are the point.

## What was run

**Systems.** All five provenances in `nesyarena.suts.registry()`, taken whole rather than
picked: `exact-wmc` (exact weighted model counting), `add-mult(clamped)` (the over-counting proof
sum, clamped to 1), `top-1-proofs` and `top-3-proofs` (exact WMC restricted to the k
highest-scoring proofs), and `min-max-prob` (max over proofs of min over facts). All five *claim*
distribution semantics. Four of them do not compute it.

**Instances.** 16 ground programs from `nesyarena.generators`: the full cross product
`P ∈ {1,2,4} × L ∈ {2,3} × c ∈ {0,1}` of the overlap family at `p = 0.7`, the chain family at
`L ∈ {2,3,4}`, `p = 0.9`, and the cyclic recursion instance `a ↔ b → c`. Bounded proof
enumeration at the depth each generator itself records. Nothing was chosen after seeing a result.

**The decision.** Each provenance aggregates the proofs of one instance and the value is
thresholded at `0.5` into approve/deny. The threshold was fixed before the run and not moved.

**The record.** Ten signals, each computed from that system's own inference on that instance:
the decision record, the decision's margin from the approve threshold, an event-log entry, the
per-decision reason, the model version, the constraint set (the program's ground rules), the
local-vs-global scope statement, the explanation-scope statement, the approximation-vs-guarantee
statement carrying the measured deviation from the semantics the system claims, and that deviation
as a number. The decision margin and numeric deviation are the two signals added for the duty below;
its property compares them, and its capability declaration also requires the existing approximation
statement. The first run carried eight signals and no duty read the deviation at all.

Thirteen further pack signals were **not** declared, because the system genuinely cannot emit them —
`provenance_active_exceptions` (definite Horn programs have no defeater mechanism),
`artifact_logs_notification_latency_days` and `artifact_logs_counteroffer_not_accepted` (no
notification exists in this domain), `artifact_logs_right_to_reasons_disclosure` (the system issues
no adverse-action notice; it is the ungated branch of the either/or of 12 CFR 1002.9(a)(2), so its
absence makes no duty unattainable), `artifact_logs_deleted_reason_count` (the one signal
reasonsmith *measures* from an inference artefact rather than reads from a record, and no
provenance here exposes one through `artifact()`), `applicant_prohibited_basis` (a fact about a
natural person, and no applicant exists for a graph solver to accept one about),
`artifact_logs_incompleteness_notice_sent` (the system receives no application, so nothing about
one is incomplete and no notice of incompleteness exists to send), and the six
Article 22 signals that are facts about a controller's legal position or about the pipeline the
system is embedded in, not about an inference. Filling any of those in would have made a duty checkable that this system cannot
discharge, which is the failure this whole exercise exists to avoid.

**No regulatory class was declared.** `nesyarena`'s provenances are reference implementations in
a measurement harness, not an AI system placed on the market in an Annex III use. Declaring
`high-risk` to make the EU AI Act pack bite would have been a fabrication.

**No decision domain was declared either.** These provenances decide graph reachability and Sudoku
validity. They issue no credit, hire nobody and treat no patient, so there is nothing to declare,
and the six ECOA duties come back not applicable rather than checked. That is finding 3 below,
and it is the reason the gate exists.

## The headline

75 results — 5 systems × 15 requirements across the three packs:

| outcome | count |
| --- | ---: |
| satisfied, at strength `observed` | 12 |
| violated, at strength `observed` | 3 |
| inconclusive, `unattainable` | 10 |
| not applicable (no class declared) | 20 |
| not applicable (no decision domain declared) | 30 |
| satisfied at `probed` | 0 |
| satisfied at `proved` | 0 |

One of the three violations is the missing-reason finding below, which the first run of this
battery already produced against 11 requirements. The other two are the twelfth requirement, added
after that run to read the declared deviation rather than the field that explains it — see
[what changed](#what-changed-since-this-finding), under finding 1.

The whole ECOA column moved to *not applicable* when the decision-domain gate landed: 8 satisfied,
2 violated and 5 unattainable results became 15 not-applicable ones. Nothing about these systems
changed. What changed is that a duty about consumer credit stopped being answered against a graph
solver — finding 3. The column is 30 results rather than 15 today only because the pack has since
gained a fourth, a fifth and a sixth duty; the gate did what that sentence says it did to the three that
existed then.

## The violation

`add-mult(clamped)` is reported **violated** on `gdpr_recital71_meaningful_explanation`
(interpretive), on this evidence: 4 of its 16 decisions carry no reason at all. It used to be
reported violated on `ecoa_reg_b_1002_9_a_2_written_statement` and
`ecoa_reg_b_1002_9_b_2_specific_reasons` (both binding) on exactly the same records; those two are
now not applicable, because 12 CFR 1002.9 is about consumer-credit decisions and this system
decides graph reachability. The evidence is unchanged and so is the defect — what went away is a
finding reported against a duty that does not govern the system. The counterexamples are instances `G1-P4-L2-c0`,
`G1-P4-L2-c1`, `G1-P4-L3-c0` and `G1-P4-L3-c1` (record indices 8–11).

This is not a bug in the adapter and it is not a contrived input. On those four instances naive
add-mult proof enumeration over-counts overlapping proofs, the raw proof sum exceeds 1, the clamp
saturates the value at exactly `1.000000`, and `AddMult.grad` returns zero for every input fact —
nesyarena's source calls this the *gradient blackout*. The system made a decision and then
reported that no fact influenced it. Under the reason rule fixed before the run — *the input
facts the system's own gradient gives non-zero influence, with their weights* — there is nothing
to write, so the record carries an empty reason and reasonsmith says so.

Note what did **not** happen: over-counting moved no decision. `add-mult(clamped)` deviates from
the distribution semantics it claims on 8 of 16 instances, by as much as `+0.347356`, and still
lands on the same approve/deny as `exact-wmc` on all 16 at this threshold. What it lost was the
explanation, not the outcome.

## The unflattering findings

### 1. The tool cleared two systems whose decisions are wrong

This is the most important thing in this run.

| system | max abs. deviation from its claimed semantics | instances deviating | decisions differing from `exact-wmc` | conformance verdicts |
| --- | ---: | ---: | ---: | --- |
| `exact-wmc` | 0.000000 | 0/16 | 0/16 | all checkable duties satisfied |
| `add-mult(clamped)` | 0.347356 | 8/16 | 0/16 | 3 violated |
| `top-1-proofs` | 0.470679 | 8/16 | **8/16** | all checkable duties satisfied |
| `top-3-proofs` | 0.097273 | 4/16 | 0/16 | all checkable duties satisfied |
| `min-max-prob` | 0.357000 | **16/16** | 4/16 | all checkable duties satisfied |

`top-1-proofs` returns a different decision from the exact semantics on **half the battery** —
eight instances approved by the semantics the system claims to implement are denied by the
system that claims it. `min-max-prob` deviates on every single instance and flips four decisions
the other way, approving four that the claimed semantics deny. reasonsmith reported both as
`satisfied` at strength `observed` on every duty it could check, with verdicts identical to the
exact oracle's.

It is right to, given what the shipped packs ask. Every record duty in GDPR, ECOA and the AI Act
asks whether a field is *present*, never whether the number the field explains is the number the
system claims to compute. The one shipped requirement that reads
`scope_statements_approximation_vs_guarantee` is EU AI Act Article 13(2) — and it is
`high-risk`-scoped, so on an unclassified system it is `not_applicable` and never read. The
deviation is measured, it is in every one of these records, and in this run **nothing looked at
it**.

An adopter should read the satisfied rows here as exactly this: *the record has the fields*. Not:
*the system computes what it says it computes*.

#### What changed since this finding

The finding above is left as it was written, because it is the reason the duty below exists. What
follows is what the current run does differently.

`gdpr_recital71_error_risk_minimised` is a twelfth requirement, interpretive, quoting the second
paragraph of GDPR Recital 71 — *"the controller should use appropriate mathematical or statistical
procedures for the profiling, implement technical and organisational measures appropriate to ensure
... that the risk of errors is minimised"*. It is not class-limited, so unlike EU AI Act Article
13(2) it reaches a system that declares no regulatory class. Its property is

```text
always(scope_statements_declared_deviation <= artifact_logs_decision_margin)
```

— the deviation a system declares about its own approximation, against the distance between that
decision and its own threshold. No number in it is invented: the bound is the system's own margin,
so the duty fails exactly when a system's *declared* error is larger than the margin.

Against this battery:

| system | max declared deviation | decisions where the declared deviation exceeds the margin | verdict |
| --- | ---: | ---: | --- |
| `exact-wmc` | 0.000000 | 0/16 | satisfied |
| `add-mult(clamped)` | 0.347356 | 0/16 | satisfied |
| `top-1-proofs` | 0.470679 | **8/16** | **violated** |
| `top-3-proofs` | 0.097273 | 0/16 | satisfied |
| `min-max-prob` | 0.357000 | **5/16** | **violated** |

The two systems the finding names are the two the duty flags, and the exact oracle is untouched:
its declared deviation is `0.000000` on every instance, and `0.0 <= margin` holds even where the
margin is zero. `add-mult(clamped)` and `top-3-proofs` stay satisfied on this duty and are right to
— both deviate, neither ever declares a deviation larger than the decision margin. `min-max-prob`
breaches on five decisions where the four it actually flips are a subset: a declared deviation can
exceed the margin without having flipped the decision, and the duty reports the risk, not the flip.

What has **not** changed, and what an adopter must still read the same way:

- The duty reads a **self-declaration**. Nothing in reasonsmith verifies the number. A system that
  silently under-reports its own error passes; a system honest enough to report a large one is the
  only kind this duty can flag. It rewards the measurement, not the accuracy.
- Silence is still not compliance, but it is not a violation either: a system that declares no
  deviation is `unattainable` on the signal and one that declares an unmeasured statement is not
  evaluated. Neither is `satisfied`, and neither is a finding about the system's accuracy.
- An exact equality is a checked limit: rtamt gives it zero robustness, so the observed engine
  reports it satisfied and cannot detect a decision that turns on an exact threshold tie without
  signed evidence and the system's own tie-break.
- Finding 5 below now carries twice the weight: this duty is checkable here only because nesyarena
  ships the exact oracle beside the approximate provenance. A deployed neuro-symbolic system would
  come back `unattainable`, and that is the honest outcome rather than a gap in the pack.
- Every satisfied record-formalism row in this report still means only *the record has the fields*.
- **The "conformance verdicts" column above is the run as it stood then.** The decision-domain gate
  of finding 3 has since moved every ECOA result to *not applicable*, so `add-mult(clamped)` is
  violated on one duty rather than three and "all checkable duties satisfied" now covers a smaller
  set of duties. Nothing in the *evidence* moved. Fewer duties reaching a system is not the same as
  more of them being discharged, and a reader comparing the two runs must not read it as an
  improvement in any system.

### 2. The top two rungs of the evidence lattice were unreachable

Zero results at `probed`, zero at `proved`. There is no probe budget to report in this run because
no probed verdict was produced.

Across all three packs there are three `logical` requirements
(`gdpr_art22_1_no_prohibited_decision_for_any_input`, `ecoa_reg_b_1002_9_b_2_specific_reasons` and
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete`) and four `temporal` requirements
(`ecoa_reg_b_1002_9_a_1_timing_of_notice`, `ecoa_reg_b_1002_9_a_2_written_statement`,
`ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` and
`gdpr_recital71_error_risk_minimised`), beside the one `counterfactual` requirement
(`ecoa_reg_b_1002_4_a_no_disparate_treatment`), which reaches neither rung here for the reason the
ECOA duties below do not: the domain gate answers it before any engine runs, and a run that did
declare `consumer-credit` would report it *not evaluated*, because these provenances expose neither
`decide()` nor `logic()` and no length of decision log establishes what a system would have decided.
The capability gate does not answer it either: the protected variable is an input the decision
procedure accepts rather than a field a decision record carries, so it is the one name that gate
does not subtract (`docs/semantics.md` §3, *counterfactual*). Two duties came back `unattainable` for all five systems —
the whole unattainable column of ten: the GDPR logical duty
`gdpr_art22_1_no_prohibited_decision_for_any_input` and the GDPR record duty
`gdpr_art22_1_automated_decision_prohibition`. The logical duty needs six signals; the system can
emit none of them, because five are facts about a controller's legal basis or about a
human-intervention route and one is about the effect a decision has on a person. The record duty
needs `provenance_active_exceptions`, and definite Horn programs have no defeater mechanism to
record as active. The ECOA *timing* duty is not `unattainable` in this run at all — it is one of
the twenty-five not-applicable results, because the domain gate of finding 3 reports it without running
it. It needs a notification latency and a counteroffer signal the system has no concept of, so a
run that declared `consumer-credit` would report it `unattainable`, but this run is not that run.

The two ECOA `logical` duties and the ECOA content duty produce no `probed` or `proved` verdict
for the same reason the ECOA timing duty produces no `unattainable` one: the domain gate reports
them not applicable without running any engine, so their rung is decided by finding 3 rather than
by the evidence ladder. The GDPR error-risk duty is the one temporal duty this run checks, and it
produces `observed` verdicts; temporal monitoring does not reach either of the top two rungs, and
no engine in this build reasons about a formula quantified over a trace (`docs/semantics.md` §3.5).

**The conclusion still holds, against the current counts: the Z3 proved engine and the replay
probed engine never ran.** Z3 never ran because no `logical` duty reaches an engine in this run —
the GDPR one is `unattainable` before any engine is asked, and the two ECOA ones are not applicable
on the domain gate — and even a checkable `logical` duty would have found no `logic()` to reason
over. The replay search never ran because no system in the battery exposes `decide()`.

`ecoa_reg_b_1002_9_a_2_written_statement` is temporal only since the either/or of 12 CFR
1002.9(a)(2) was formalised; it was a `record` duty when this run was first made, and its verdicts
here are the same either way — the five systems supply `artifact_logs_reason_explanation` or they
do not, and none of them discloses a right to request reasons.

That leaves the seven `record` duties these three packs hold, and there is a second cause behind
them that this finding originally mistook for the first. When this run was first made, a `record` duty could never exceed
`observed` for *any* system: `formalism` both named the property and picked the engine, so a human
typing `record` in a TOML file capped the rung regardless of what the system exposed. That defect
is fixed — a presence property is now discharged by the strongest engine the system's exposed
surface allows, and the same property reaches `proved` against exposed `logic()`. **Re-running the
builder after the fix changes nothing in this report.** The counts above are unmoved, and that is
the correct answer rather than a leftover of the defect: `NesyArenaSUT` implements `decisions()`
and nothing else, so there is no `decide()` to replay a perturbed input through and no `logic()` to
reason over. Of the seven record duties, four are the AI Act's and are not applicable on the scope
gate, one — `gdpr_art22_1_automated_decision_prohibition` — reaches no engine at all, and the two
that do, `gdpr_art22_3_safeguards_human_intervention` and `gdpr_recital71_meaningful_explanation`,
stay `observed`, because a bare trace is all the evidence this system offers, which is what
`observed` means.

Giving the adapter a `decide()` would move the number and would be dishonest: the probe engine
perturbs *record fields*, and this system's inputs are a ground program and its fact
probabilities, not the strings and floats its records carry. A `decide()` that accepted a perturbed
record and answered from the unperturbed instance would report a search that never searched.

The generalisation is uncomfortable and worth stating plainly: **for any system that exposes only a
decision trace, the strongest evidence reasonsmith can produce is `observed`, whatever the pack
asks.** The proved and probed engines exist and are tested, and after the dispatch fix a record
duty can reach either — but only against a system that can be re-run or reasoned over. nesyarena's
provenances, as adapted here, are neither.

### 3. ECOA reached a system it has no business reaching

Four of the five systems came back `satisfied` on `ecoa_reg_b_1002_9_a_2_written_statement` — an
adverse-action notice duty under 12 CFR 1002.9 — for a graph-reachability benchmark that issues no
credit and notifies nobody.

The cause is structural: all four ECOA requirements and all five GDPR requirements carry
`scope = ""`, so they are not class-limited and reach every system. Only the EU AI Act pack uses
the regulatory-class gate. reasonsmith has no notion of *decision domain* at all — nothing in a
pack can say "this duty is about consumer credit" — so a domain mismatch is invisible where a
class mismatch is caught. The unattainable verdict on the timing requirement is the only hint in
the ECOA output that the domain does not fit, and it arrives for the wrong reason: a missing
signal, not a missing domain.

#### What changed since this finding

**Fixed, and this is what fixing it cost.** A `domains` field now sits beside `scope` on every
requirement, naming the kinds of decision a duty is about, and it is matched by intersection against
what a system declares (`--system-domain`, or `system_domains` on an adapter). The six ECOA duties
carry `domains = ["consumer-credit"]`; this run declares no domain; all thirty ECOA results are now
`not_applicable`, where four of the five systems were `satisfied` on
`ecoa_reg_b_1002_9_a_2_written_statement` before. The GDPR results did **not** move, and that is the
right answer rather than a gap: Article 22 governs a solely-automated decision whatever the decision
is about, so the five GDPR duties carry `domains = []` and reach every system, including this one.
The gate is not the only thing standing between these systems and the fourth of those duties:
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete` gates on `artifact_logs_deleted_reason_count`, a
count reasonsmith *measures* from an inference artefact a system exposes through the optional
`artifact()` method rather than reads from a log, so even a run declaring `consumer-credit` would
report it `unattainable` on all five provenances. It would not be alone: the timing duty would be
`unattainable` too, on the notification latency and counteroffer signals it gates on, and so would
the incompleteness-notice duty of 12 CFR 1002.9(c)(2), which gates on a notice this system sends
nobody. But the
counterfactual duty added since is *not evaluated* rather than unattainable:
`applicant_prohibited_basis` is an input a decision procedure accepts and not a field a decision
record carries, so it is the one name the capability gate does not subtract, and the duty reaches
the engines — which answer that these provenances expose neither `decide()` nor `logic()`, and no
length of decision log establishes what a system would have decided. So three of the six duties
would stay unattainable, one would come back not evaluated, and the other two — the
written-statement and specific-reasons duties — would become checkable.

Three things this did not fix, in descending order of how much they should worry a reader:

- **The vocabulary is this repository's, not any regulation's.** `DECISION_DOMAINS` is a coarse
  eight-member list written here because no statute defines one. Placing 12 CFR 1002.9 in
  `consumer-credit` is a pack author's reading; a not-applicable verdict on this gate says *this
  classification does not match what the system declared*, never *this statute does not govern this
  system*. `docs/authoring-packs.md` requires a pack limiting a duty to a domain to say so in its
  own description, so a reader of the tool's output meets the claim too.
- **A declaration is a self-declaration.** Nothing checks that a system declaring `consumer-credit`
  issues credit. The gate stops a duty reaching a system that said nothing; it does nothing about
  one that said the wrong thing — the same standing as the Article 22(2) basis flags
  (`docs/semantics.md` §3, *the assumption all seven share*).
- **The trigger inside a decision is still not modelled.** 12 CFR 1002.9 is triggered by adverse
  action having been taken, not by the creditor being in consumer credit. Against a system that
  *does* declare `consumer-credit`, the property still runs over every record in the trace,
  approvals included. That is the reach gap `docs/refinement.md` names in column four, and no gate
  at the system level can close it.

And the observation this finding made about the *output* is now less true but not gone: the
unattainable verdict on the timing requirement was the only hint the domain did not fit. It has been
replaced by twenty results that name the domain mismatch directly. What has not been replaced is
any way to tell, from the report alone, whether the classification behind them was a good one.

### 4. The AI Act pack said nothing at all

20 of the 65 results — every AI Act requirement for every system — are `not_applicable` because
no regulatory class was declared. That is the designed behaviour and the report says so in full,
but the honest summary is that running the AI Act pack against this system produced no
information. The gate is binary: declare `high-risk` and all four duties are checked, declare
nothing and none are. There is no middle position for "this is a component that could end up
inside a high-risk system", which is what a provenance library actually is.

### 5. One declared signal is only honest because nesyarena is a measurement harness

`scope_statements_approximation_vs_guarantee` carries a *measured* deviation — e.g.
`approximation: value deviates from the distribution semantics oracle it claims by +0.347356 on
this input` — because nesyarena ships the exact WMC oracle beside the approximate provenance and
the builder computes the difference for every instance.

The duty added since — `gdpr_recital71_error_risk_minimised`, above — stands on that same property,
so this caveat is now load-bearing for a verdict rather than only for a field.

The measured approximate provenances would not, standing alone, have such an oracle at inference
time. They could honestly state *approximation*; they could not state *by how much*. Do not read
this run as evidence that a production neuro-symbolic system can emit that field with a number in
it. Where the tool looks strongest here, it is standing on a property of the research harness
rather than of a deployable one.

### 6. The reason rule decided three of the five violations in the run

Full disclosure, because it is the one judgement call responsible for three verdicts. The reason
field was defined before the run as *the facts the system's own gradient gives non-zero influence*.
Under that rule, `add-mult(clamped)`'s saturated decisions carry no reason and are violations.

Had the reason been defined instead as *the proof supports enumerated for the query* — also a
defensible reading, and non-empty on every instance in this battery — the run would have produced
**two remaining violations** and 23 satisfied results. Those two deviation-duty violations do not
depend on the reason rule. The rule was fixed first and applied identically to all five systems, and
it is stated in the builder as `REASON_RULE` so a reader can disagree with it in the open. But an
adopter should know that reasonsmith checks the field the adapter author decided to fill, and that
the decision of what counts as a reason sits with that author, not with the tool.

## What would need to change to publish this on the site

Nothing here touches `docs/report.html` or `docs/index.html`; PRs
[#33](https://github.com/eduardstan/reasonsmith/pull/33) and
[#34](https://github.com/eduardstan/reasonsmith/pull/34) restyle exactly
those files and this work deliberately stays out of their way. To put this run on the published
site later:

- `.github/workflows/pages.yml` copies a single committed `docs/index.html` into `_site/`. It
  would need a second copy step, or a `_site/` layout with more than one page.
- The report here is Markdown, not `ConformanceReport.render_html` output. `render_html` renders
  one report; this run has 15. A page would need a composition script like
  `docs/build_example.py` that lays out 15 reports plus the measured-inference table, and a
  byte-for-byte test to match — the pattern `test_docs_index_html_matches_the_renderer` already
  establishes.
- Whatever nav or link the restyled `index.html` settles on after
  [#33](https://github.com/eduardstan/reasonsmith/pull/33) and
  [#34](https://github.com/eduardstan/reasonsmith/pull/34) land would need an entry
  pointing at it. That decision belongs to those pull requests, not to this one.

## Reproducing it

```sh
pip install -e ".[dev]"
python docs/build_nesyarena_report.py
```

The report is regenerated in place. `pytest tests/test_nesyarena_conformance.py` fails if the
committed file and the script disagree by a single byte.
