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

**The record.** Eight signals, each computed from that system's own inference on that instance:
the decision record, an event-log entry, the per-decision reason, the model version, the
constraint set (the program's ground rules), the local-vs-global scope statement, the
explanation-scope statement, and the approximation-vs-guarantee statement carrying the measured
deviation from the semantics the system claims.

Nine further pack signals were **not** declared, because the system genuinely cannot emit them —
`provenance_active_exceptions` (definite Horn programs have no defeater mechanism),
`artifact_logs_notification_latency_days` and `artifact_logs_counteroffer_not_accepted` (no
notification exists in this domain), and the six Article 22 signals that are facts about a
controller's legal position or about the pipeline the system is embedded in, not about an
inference. Filling any of those in would have made a duty checkable that this system cannot
discharge, which is the failure this whole exercise exists to avoid.

**No regulatory class was declared.** `nesyarena`'s provenances are reference implementations in
a measurement harness, not an AI system placed on the market in an Annex III use. Declaring
`high-risk` to make the EU AI Act pack bite would have been a fabrication.

## The headline

55 results — 5 systems × 11 requirements across the three packs:

| outcome | count |
| --- | ---: |
| satisfied, at strength `observed` | 17 |
| violated, at strength `observed` | 3 |
| inconclusive, `unattainable` | 15 |
| not applicable (no class declared) | 20 |
| satisfied at `probed` | 0 |
| satisfied at `proved` | 0 |

## The violation

`add-mult(clamped)` is reported **violated** on three requirements —
`ecoa_reg_b_1002_9_a_2_written_statement` and `ecoa_reg_b_1002_9_b_2_specific_reasons` (both
binding) and `gdpr_recital71_meaningful_explanation` (interpretive) — on the same evidence: 4 of
its 16 decisions carry no reason at all. The counterexamples are instances `G1-P4-L2-c0`,
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
eight applicants approved by the semantics the system claims to implement are denied by the
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

### 2. The top two rungs of the evidence lattice were unreachable

Zero results at `probed`, zero at `proved`. There is no probe budget to report in this run because
no probed verdict was produced.

Across all three packs there is exactly one `logical` requirement
(`gdpr_art22_1_no_prohibited_decision_for_any_input`) and one `temporal` one
(`ecoa_reg_b_1002_9_a_1_timing_of_notice`). Both came back `unattainable` for all five systems,
so the Z3 proved engine and the replay probed engine never ran. The logical duty needs six
signals; the system can emit none of them, because five are facts about a controller's legal
basis or about a human-intervention route and one is about the effect a decision has on a person.
The temporal duty needs a notification latency the system has no concept of.

The generalisation is uncomfortable and worth stating plainly: **for any system that knows only
its own inference, the strongest evidence reasonsmith's shipped packs can produce is `observed`.**
The proved and probed engines exist and are tested, but reaching them requires a pack whose
logical properties are about the inference itself rather than about the organisation deploying
it. No such pack ships.

### 3. ECOA reached a system it has no business reaching

Four of the five systems came back `satisfied` on `ecoa_reg_b_1002_9_a_2_written_statement` — an
adverse-action notice duty under 12 CFR 1002.9 — for a graph-reachability benchmark that issues no
credit and notifies nobody.

The cause is structural: all three ECOA requirements and all four GDPR requirements carry
`scope = ""`, so they are not class-limited and reach every system. Only the EU AI Act pack uses
the regulatory-class gate. reasonsmith has no notion of *decision domain* at all — nothing in a
pack can say "this duty is about consumer credit" — so a domain mismatch is invisible where a
class mismatch is caught. The unattainable verdict on the timing requirement is the only hint in
the ECOA output that the domain does not fit, and it arrives for the wrong reason: a missing
signal, not a missing domain.

### 4. The AI Act pack said nothing at all

20 of the 55 results — every AI Act requirement for every system — are `not_applicable` because
no regulatory class was declared. That is the designed behaviour and the report says so in full,
but the honest summary is that running the AI Act pack against this system produced no
information. The gate is binary: declare `high-risk` and all four duties are checked, declare
nothing and none are. There is no middle position for "this is a component that could end up
inside a high-risk system", which is what a provenance library actually is.

### 5. One declared signal is only honest because nesyarena is a measurement harness

`scope_statements_approximation_vs_guarantee` carries a *measured* deviation — e.g.
`approximation: value deviates from the distribution semantics oracle it claims by +0.347356 on
this input` — because nesyarena ships the exact WMC oracle beside the approximate provenance and
`Provenance.error()` computes the difference on every call.

The measured approximate provenances would not, standing alone, have such an oracle at inference
time. They could honestly state *approximation*; they could not state *by how much*. Do not read
this run as evidence that a production neuro-symbolic system can emit that field with a number in
it. Where the tool looks strongest here, it is standing on a property of the research harness
rather than of a deployable one.

### 6. The reason rule decided the only violation in the run

Full disclosure, because it is the one judgement call that changed a verdict. The reason field was
defined before the run as *the facts the system's own gradient gives non-zero influence*. Under
that rule, `add-mult(clamped)`'s saturated decisions carry no reason and are violations.

Had the reason been defined instead as *the proof supports enumerated for the query* — also a
defensible reading, and non-empty on every instance in this battery — the run would have produced
**zero violations** and 20 satisfied results. The rule was fixed first and applied identically to
all five systems, and it is stated in the builder as `REASON_RULE` so a reader can disagree with
it in the open. But an adopter should know that reasonsmith checks the field the adapter author
decided to fill, and that the decision of what counts as a reason sits with that author, not with
the tool.

## What would need to change to publish this on the site

Nothing here touches `docs/report.html` or `docs/index.html`; PRs #33 and #34 restyle exactly
those files and this work deliberately stays out of their way. To put this run on the published
site later:

- `.github/workflows/pages.yml` copies a single committed `docs/index.html` into `_site/`. It
  would need a second copy step, or a `_site/` layout with more than one page.
- The report here is Markdown, not `ConformanceReport.render_html` output. `render_html` renders
  one report; this run has 15. A page would need a composition script like
  `docs/build_example.py` that lays out 15 reports plus the measured-inference table, and a
  byte-for-byte test to match — the pattern `test_docs_index_html_matches_the_renderer` already
  establishes.
- Whatever nav or link the restyled `index.html` settles on after #33/#34 land would need an entry
  pointing at it. That decision belongs to those pull requests, not to this one.

## Reproducing it

```sh
pip install -e ".[dev]"
python docs/build_nesyarena_report.py
```

The report is regenerated in place. `pytest tests/test_nesyarena_conformance.py` fails if the
committed file and the script disagree by a single byte.
