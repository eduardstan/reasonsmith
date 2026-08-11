# Roadmap

This file exists so a contributor or a reviewer can see what is missing without access to anyone's
private backlog. Every objective below is a gap this repository's own documents already state, and
each one cites where. Nothing here is aspirational: an item is on this list because a committed
document names it as a limit, not because it would be nice to have.

Each objective gives a **measurable outcome** — a check that fails today and would pass when the
objective is met — and what it **depends on**. Where the honest answer is that an objective is
blocked, or deliberately not started, that is written down rather than left as an implied "soon".

Current state, for scale: **5 packs, 29 requirements, 7 engines** (`record`, `observed`, `probed`,
`certificate` — also at `probed` — `proved`, the temporal proof engine, also at `proved`, and the
counterfactual engine, which spans both `proved` and `probed`).
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

A finite-trace decision procedure is now installable (the BLACK solver binary from a system
package manager, driven by `src/reasonsmith/ltlf.py`; the `ltlf` extra declares no Python
dependency), which changes what this objective *depends on* and not what it is. That
backend decides a duty as a **formula**, for `validate-pack --analyse`; it is never given a system,
returns no `RequirementResult` and occupies no rung, so it establishes nothing about what any
system's logic admits. The condition still stands unchanged: a duty using the operator first, and
then a design answer for what would discharge it, on the same terms as objective 2.
`docs/semantics.md` §8 states what the backend does answer, and the two limits it arrived with — a
propositional reading of every magnitude, and no LTL₃ verdict, because the procedure exposes no
monitor construction and this repository will not synthesise one.

## 2. `until` and `since` in the temporal fragment — **met, and one half of it is a reversal**

**What met it.** `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out` — 12 CFR 1002.9(c)(2). A
sweep of every statute `docs/legal-sources.md` retrieved found the duty this objective was waiting
for: the creditor's obligation runs from a notice of incompleteness and ends one of two ways, the
designated period lapsing in silence or the information arriving. An obligation with an end as well
as a beginning is what `until` states and what no state property of one decision record can. The
duty is shipped in the `ecoa` pack, accepted by `load_pack`, classified `temporal`, monitored by
the observed engine, and carries its row in [`docs/refinement.md`](docs/refinement.md).

The implementation is a **syntax mapping and nothing else**: rtamt has parsed both operators as
infix all along, this language writes prefix calls because it parses through Python's `ast`, and
`engines/observed.to_stl` renders one spelling into the other. No temporal semantics is implemented
in this repository, and none may be.

**`since` was added without a qualifying duty, by the captain's explicit decision of 2026-08-04.**
The sweep found no clause in the retrieved corpus with the `since` shape. That was reported, and
the decision was taken anyway, to add the two as a dual pair. This paragraph is the record of it,
because a roadmap that quietly drops the condition it set is worse than one that never set it. It
is exercised only by a test (`test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it`), which
is the whole of what keeps it from rotting unrendered.

**The discipline this section describes still governs every operator after these two.** A pack
needing one is a finding to record in [`docs/semantics.md`](docs/semantics.md) §2 first, not a
reason to widen the language until it fits — widening a property language to accommodate one
stubborn duty is how it becomes an untyped string again. What changed is that one duty was found
and one operator was added over the objection; what did not change is the rule, or the standard of
evidence the next operator has to meet.

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
  run reports the duty `unattainable` for all three — and *not evaluated* for the language model of
  `docs/language-model.md`, which declares no input space to vary the variable over — and the
  provable-non-discrimination case lives in `tests/test_counterfactual_invariance.py` rather than
  in a transcript.

## 4. Breadth: more regulations than five

**The gap, and what a fifth pack did and did not settle.** Five packs now ship — Table 7, EU AI Act
(Art. 12 & 13), GPAI (EU AI Act Art. 53 & 55), GDPR, ECOA/Reg B — and four of them quote statute.
The GPAI pack met the outcome below in full and closed one thing the objective did not ask for: the
`general-purpose` member of `spec.REGULATORY_CLASSES` was wired and used by zero shipped
requirements, so the class gate had a member no run had ever exercised, and its eight duties are the
first to exercise it.

**What it did not settle, and the honest cost of it.** The judgement this objective names — whether
another pack is worth more than depth on the ones that ship — is *less* settled than before, not
more. Twenty-one of the twenty-nine shipped requirements are now presence checks, up from thirteen
of nineteen, because Article 53 and Article 55 are document-production duties for which presence is
the correct refinement and no stronger property exists to write
([`docs/refinement.md`](docs/refinement.md), *presence is not adequacy*). Breadth bought that way is
real breadth and it is not depth. **A sixth pack that is another eight presence checks makes this
worse, and a proposal should say which of its duties reaches above `record`.**

There is now a measurement beside that count rather than only the count.
`reasonsmith validate-pack <pack> --analyse --system-module …` mutates a system's declared rules
and reports how many mutants each duty notices; against the shipped symbolic rule set, six of the
ten ECOA and GDPR duties cannot tell any of thirty rule sets apart
([RESULTS.md](RESULTS.md), *Pack Analysis Note*). Read the limits there before quoting the number:
it reaches only a system that exposes its rules, which is one of the four systems this repository
ships, and it is not a coverage figure.

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

**What exists now, and it does not close this.** The design answer was written, and one half of one
of its two candidates is built: `semantic_laws.py` refutes a false `claimed_semantics` from the
system's own answers alone, with no reference implementation anywhere in the loop, and does it for
every one of the four `nesyarena` provenances that deviates from what it claims while refuting the
exact one on nothing. It needed a perturbation the artefact protocol refused in writing, so
[`docs/formal.md`](docs/formal.md) §3.6 now records that reversal and §3.7 states the soundness of
what replaced it. **The measurable outcome above still fails**, and deliberately: no requirement
reads the measurement, so the two reports the check drives are still identical on every requirement.
Closing this objective needs a duty, and a duty needs `claimed_semantics` to become a name from a
closed vocabulary first — today the certificate's reference side is hard-wired to exact WMC whatever
an artefact claims, so a system that *honestly documents* its truncation already measures a value
gap, and promoting that to a verdict before the claim binds would ship a false accusation.

## 6. The first duty written with an open-textured predicate

**The gap.** [`docs/semantics.md`](docs/semantics.md) §9 opens by stating it: twenty-one of the
twenty-nine shipped requirements are presence checks, and the fourth column of
[`docs/refinement.md`](docs/refinement.md) says the same thing row after row — *meaningful*,
*sufficiently detailed*, *adequate*, *appropriate*, *without undue delay* were not modelled. Presence
is not a bad proxy for those predicates; it is a refusal to model them at all. §9 also states what is
now true and what is not: **the machinery exists and no shipped duty uses it**
(`test_no_shipped_pack_uses_either_open_texture_construct`), because which statutory predicate
becomes the first `undetermined` or `graded` one is a legal reading and not an engineering decision.

Two questions stand between the machinery and a shipped duty, and neither is code:

- **Which clause, and which reading.** A predicate belongs in `undetermined()` when its application
  to facts is settled by an institution — and the pack must then be able to *name* that institution
  from the retrieval record, on the same discipline `docs/legal-sources.md` already imposes on a
  quotation. It belongs in `degree()` when the predicate is vague rather than merely unsettled, which
  is a claim about the clause and not about the evidence.
- **What a degree would have to come from.** A `Grading` names an authority, a scale and a method,
  and nothing in this repository supplies one. A shipped graded duty needs a real assessment behind
  it or it is a fixture with a statute's name on it.

**Measurable outcome.** One shipped requirement whose `formalism` is `undetermined` or `graded`,
with: its clause and the words of its open-textured predicate quoted in `verbatim_text`; the
authority named from a source `docs/legal-sources.md` retrieved, for the `undetermined` case; a
`docs/refinement.md` row whose fourth column names what is *still* left out after the construct is
used, since neither construct closes a gap by itself; and — for the `graded` case — a `[grading]`
algebra declared, with a paragraph in the pack description saying why that lattice and not another,
on the same terms this repository demands of an invented threshold.
`test_no_shipped_pack_uses_either_open_texture_construct` is the check that fails today and would
have to be rewritten, not deleted, when this closes: it is what keeps the machinery from acquiring a
duty by accident.

**Depends on.** A legal reading, which is the captain's, and an assessment for the graded case. It
deliberately does **not** depend on any further engine work: §9 states that neither fragment reaches
an engine and that no rung of the lattice means *graded*, and a duty landing on either construct is
reported *not evaluated* with its finding beside it. The pressure it put on the evidence scale — a
graded reading having no place on the strength lattice, alongside the counterfactual fragment's two
rungs and the certificate engine's single one — **has since been designed**, once, as the evidence
*basis* dimension of `docs/semantics.md` §10 rather than as more links in the chain. A shipped
graded duty inherits the `assessment` basis and is counted apart from a duty an engine failed to
settle; nothing about it now waits on that design.

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
