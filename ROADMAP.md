# Roadmap

This file exists so a contributor or a reviewer can see what is missing without access to anyone's
private backlog. Every objective below is a gap this repository's own documents already state, and
each one cites where. Nothing here is aspirational: an item is on this list because a committed
document names it as a limit, not because it would be nice to have.

Each objective gives a **measurable outcome** — a check that fails today and would pass when the
objective is met — and what it **depends on**. Where the honest answer is that an objective is
blocked, or deliberately not started, that is written down rather than left as an implied "soon".

Current state, for scale: **5 packs, 27 requirements, 6 engines** (`record`, `observed`, `probed`,
`certificate` — also at `probed` — `proved`, and the temporal proof engine, also at `proved`).
`reasonsmith validate-pack ecoa eu_ai_act gdpr gpai table7` prints what each contains.

---

## 1. A temporal engine above `observed` — closed, for one shape of duty

**What closed it.** `engines/temporal.py` proves an `always(f)` whose `f` is a property of a single
decision, by the one reduction that is exact over a finite trace: `always(f)` holds iff `f` holds at
every position, and every position is a decision the system's exposed `logic()` admits. The two
temporal requirements this objective named — `ecoa_reg_b_1002_9_a_1_timing_of_notice` and
`gdpr_recital71_error_risk_minimised` — now report `proved` against
`reasonsmith.examples.symbolic_rules`, and `test_a_temporal_duty_never_rises_above_observed` was
replaced by `test_only_always_reaches_the_temporal_proof_rung`, which pins the new ceiling from both
sides. The soundness paragraph is [`docs/semantics.md`](docs/semantics.md) §3, *`proved`, over a
trace*.

**What is left, and it is not this objective.** The rung reaches exactly one temporal shape.
`eventually(f)` asserts that some position *exists*, which is a fact about the trace a system emitted
rather than about the decisions its logic admits, so nothing reasoning about one decision at a time
establishes it and it stays at `observed`. Closing *that* needs the reasoning this objective did not
need — a bounded search over generated traces, or a finite-trace decision procedure — and no shipped
duty uses the operator, so it waits for one, on the same terms as objective 2.

## 2. `until` and `since` in the temporal fragment

**The gap.** `TEMPORAL_OPERATORS` holds the prefix call forms a Python parser accepts, so rtamt's
infix `until` and `since` are not in this property language.

Stated in [`docs/semantics.md`](docs/semantics.md) §2.

**Measurable outcome.** A shipped requirement whose `spec` uses one of the two, accepted by
`load_pack`, monitored by the observed engine, and carrying its own row in `docs/refinement.md`.

**Depends on — and is deliberately blocked by — objective 4.** No shipped duty needs either
operator. `docs/semantics.md` §2 says a pack needing one is a finding to record there, not a reason
to widen the language until it fits, because widening a property language to accommodate one
stubborn duty is how it becomes an untyped string again. So this objective waits for a real duty
that cannot be written without it. It is on the roadmap to be found, not to be started.

## 3. A fairness property, anywhere — **met**

**What met it.** `ecoa_reg_b_1002_4_a_no_disparate_treatment` — counterfactual invariance under one
named protected variable, anchored to 12 CFR 1002.4(a), the disparate-*treatment* limb of
Regulation B. It is the first relational property in this repository: a property of a *pair* of
executions rather than of one decision record. It has a fragment of its own (`counterfactual`), a
soundness paragraph of its own (`docs/semantics.md` §3, the seventh), two rungs — self-composition
in Z3 at `proved`, paired replay through `decide()` at `probed` — and deliberately **no trace rung**,
because a trace holds what a system decided and a counterfactual asks what it would have decided.

The measurable outcome is met literally: the property compares an outcome across groups — the same
applicant under two values of the protected variable — rather than checking that a field is
non-empty; `docs/refinement.md` carries its row; and the sentence that objective quoted has stopped
being true and was **narrowed rather than deleted**. It now reads that no *distributional* fairness
property is checked, that the one that is checked is counterfactual invariance under a single named
variable, and that it cannot see a disparate impact.

**What is still open, and it is most of the subject.**

- **Disparate impact — GDPR Recital 71's own *discriminatory effects* limb — is not formalised and
  is not on this roadmap to be built.** No group-statistical criterion can earn a verdict on this
  evidence model: a rate over a trace is an estimate of a population quantity with no sampling claim
  behind it, no statute supplies the threshold, equalised odds and calibration need a ground truth
  the SUT protocol has no method for, and the `proved` rung quantifies over a measure-free domain
  where a probability has no denominator. `docs/authoring-packs.md` documents the hazard, because a
  pack author can write the bad version today and reach `violated` at `proved` on arithmetic over
  numbers nobody computed.
- **A proxy is invisible to the duty that shipped.** A rule set that never reads the protected
  variable and decides by postcode is `satisfied`. `TREATMENT_LIMIT` says so on every result the
  engine returns, which is a mitigation and not a fix.
- **One variable per duty, and no interaction.** 12 CFR 1002.2(z) lists nine prohibited bases; the
  shipped duty names one signal, and the atom is deliberately not composable.
- **No shipped example system exercises the `satisfied` case.** None of the three systems of
  `docs/three-systems.md` declares a protected variable, and none should: a decision record carrying
  a fact about a natural person is a collection cost this repository does not create. So the ECOA
  run reports the duty `unattainable` for every shipped system, and the provable-non-discrimination
  case lives in `tests/test_counterfactual_invariance.py` rather than in a transcript.

## 4. Breadth: more regulations than five

**The gap, and what a fifth pack did and did not settle.** Five packs now ship — Table 7, EU AI Act
(Art. 12 & 13), GPAI (EU AI Act Art. 53 & 55), GDPR, ECOA/Reg B — and four of them quote statute.
The GPAI pack met the outcome below in full and closed one thing the objective did not ask for: the
`general-purpose` member of `spec.REGULATORY_CLASSES` was wired and used by zero shipped
requirements, so the class gate had a member no run had ever exercised, and its eight duties are the
first to exercise it.

**What it did not settle, and the honest cost of it.** The judgement this objective names — whether
another pack is worth more than depth on the ones that ship — is *less* settled than before, not
more. Twenty-one of the twenty-eight shipped requirements are now presence checks, up from thirteen
of nineteen, because Article 53 and Article 55 are document-production duties for which presence is
the correct refinement and no stronger property exists to write
([`docs/refinement.md`](docs/refinement.md), *presence is not adequacy*). Breadth bought that way is
real breadth and it is not depth. **A sixth pack that is another eight presence checks makes this
worse, and a proposal should say which of its duties reaches above `record`.**

**Measurable outcome.** Each additional pack lands with: a retrieval record in
[`docs/legal-sources.md`](docs/legal-sources.md); verbatim quotes that
`test_pack_quotes_found_verbatim_in_legal_sources_report` accepts character-for-character; a live
source `python -m reasonsmith.drift` can re-fetch, so the monthly statute-drift workflow covers it;
and one `docs/refinement.md` row per requirement, whose fourth column names a specific gap rather
than saying "some aspects are not captured".

**Depends on.** Proposals, which is the one item on this list a stranger unblocks rather than
waits on. The intake is the Discussion
[*Which regulation should the next pack cover?*](https://github.com/eduardstan/reasonsmith/discussions/54)
and the [pack proposal template](.github/ISSUE_TEMPLATE/pack_proposal.yml); the rules a pack must
satisfy are in [`docs/authoring-packs.md`](docs/authoring-packs.md).

## 5. Evidence that a system's inference is the semantics it claims

**The gap.** A system declares what it computes; nothing here checks that the declaration is true.
Every verdict this tool reaches stands on a claim the system makes about itself — the semantics its
inference implements, the deviation it reports from that semantics, the decision domain it operates
in — and no engine measures any of them against the system's behaviour. The measured consequence is
finding 1 of [`docs/findings-nesyarena.md`](docs/findings-nesyarena.md): two provenances whose
decisions disagree with the semantics they claim, one on half the battery, were reported satisfied
on every duty this tool could check, with verdicts identical to the exact oracle's. The same shape
is stated twice more in that document — the error-risk duty "rewards the measurement, not the
accuracy" (finding 1, *What has not changed*), and "a declaration is a self-declaration" about the
domain gate (finding 3).

**Measurable outcome.** A check in the suite that drives two systems differing *only* in whether
their inference agrees with the semantics they declare — the same pack, the same inputs, the same
declared semantics, one implementing it and one deviating from it — and fails unless the two reports
differ on at least one requirement. Such a check cannot be written to pass today: the two reports
are identical, which is what finding 1 measures rather than predicts. When it passes, finding 1's
*What changed since this finding* section gains the row that says so; the finding itself stays as
written, because it is the reason the objective exists.

**Depends on.** A design answer before any code, on the same terms as objective 3, and the question
is narrower than it looks: **what would a system have to expose for reasonsmith to establish
agreement rather than take its word?** `engines/certificate.py` is the precedent worth studying — it
took a claim previously read out of a log and made it something the tool measures against an
artefact the system exposes — and the trap it avoided is the one to avoid here. A `semantics_matches`
flag would be a second self-declaration wearing an engine's clothes; so would any design that needs
the system to hand over the very number in dispute. It also depends on not assuming an oracle:
finding 5 of the same document records that the deviation figures in that run exist because
`nesyarena` ships an exact oracle beside each approximate provenance, which a deployed system does
not have, so a design reachable only with one closes nothing outside a measurement harness. And it
depends on the four-outcome discipline of [`docs/semantics.md`](docs/semantics.md) §4 holding: a
system exposing nothing that grounds its claim must report *not evaluated*, never `satisfied`.
The intake is the Discussion
[*reasonsmith cleared two systems whose decisions are wrong — what should a pack do about it?*](https://github.com/eduardstan/reasonsmith/discussions/59).

---

## What is deliberately not on this roadmap

Kept here so a proposal for one of these gets an answer rather than silence:

- **Web or GUI dashboards.** The `--html` report is one static offline file, not a served
  application.
- **Reimplementing `nesyarena`'s IR or oracle engines.** They are depended on, pinned to
  `nesyarena==0.1.0`, never vendored.
- **Automated legal opinions, or any un-hedged compliance guarantee.** reasonsmith reports what a
  specification asks and how a verdict was reached. Whether a legal duty is discharged is a
  determination it does not make; that sentence travels on every emitted report.

`CONTRIBUTING.md` has the development setup, the verification commands, and the standing rules a
change must respect.
