# Roadmap

This file exists so a contributor or a reviewer can see what is missing without access to anyone's
private backlog. Every objective below is a gap this repository's own documents already state, and
each one cites where. Nothing here is aspirational: an item is on this list because a committed
document names it as a limit, not because it would be nice to have.

Each objective gives a **measurable outcome** and what it **depends on**. An open objective names a
check that fails today and would pass when the objective is met; a closed objective records why the
same check now passes. Where the honest answer is that an objective is blocked, or deliberately not
started, that is written down rather than left as an implied "soon".

Current state, for scale: **5 packs, 29 requirements, 7 engines** (`record`, `observed`, `probed`,
`certificate` — also at `probed` — `proved`, the temporal proof engine, also at `proved`, and the
counterfactual engine, which spans both `proved` and `probed`).
`reasonsmith validate-pack ecoa eu_ai_act gdpr gpai table7` prints what each contains.

---

## 1. A temporal engine above `observed` — closed, for one shape of duty

**What closed it.** `engines/temporal.py` proves an `always(f)` whose `f` is a property of a single
decision, by the one reduction that is exact over a finite trace: `always(f)` holds iff `f` holds at
every position, and every position is a decision the system's exposed `logic()` admits. Of the two
temporal requirements this objective named, `ecoa_reg_b_1002_9_a_1_timing_of_notice` reports
`proved` against `reasonsmith.examples.symbolic_rules`. The second,
`gdpr_recital71_error_risk_minimised`, did too until objective 5 replaced its left-hand side with a
measurement: it is now settled against the inference artefact behind a decision or not at all, so
that rule set — which exposes no `artifact()` — is reported `unattainable` on it. The reduction is
unchanged and reaches it still; what moved is which engine may answer that duty, and
`engines/certificate.py` makes the same `always(f)` reduction, over the decisions it certifies, so
one spelling of the operator exists. `test_a_temporal_duty_never_rises_above_observed` was
replaced by `test_only_always_reaches_the_temporal_proof_rung`, which pins the new ceiling from both
sides. The soundness paragraph is [`docs/theory/05-decision-procedures.md`](docs/theory/05-decision-procedures.md) §5.1, *reference interpreter
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
`docs/theory/05-decision-procedures.md` §5.4 states what the backend does answer, and the two limits it arrived with — a
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
needing one is a finding to record in [`docs/theory/02-syntax.md`](docs/theory/02-syntax.md) first, not a
reason to widen the language until it fits — widening a property language to accommodate one
stubborn duty is how it becomes an untyped string again. What changed is that one duty was found
and one operator was added over the objection; what did not change is the rule, or the standard of
evidence the next operator has to meet.

## 3. A fairness property, anywhere — **met**

**What met it.** `ecoa_reg_b_1002_4_a_no_disparate_treatment` — counterfactual invariance under one
named protected variable, anchored to 12 CFR 1002.4(a), the disparate-*treatment* limb of
Regulation B. It is the first relational property in this repository: a property of a *pair* of
executions rather than of one decision record. It has a fragment of its own (`counterfactual`), a
soundness paragraph of its own (`docs/theory/04-decision-problems.md` §4.4), two rungs — self-composition
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

## 5. Evidence that a system's inference is the semantics it claims — closed, for one artefact family

**What closed it.** `gdpr_recital71_error_risk_minimised` now reads a deviation reasonsmith
*measures* instead of one the system declares. Its left-hand side is
`engines.certificate.SEMANTICS_VALUE_GAP` — the distance between the system's own engine's answer
and exact inference's answer to the same query on the same interpretation, both computed from the
inference artefact the system exposes. Its right-hand margin is measured too where that artefact
exposes a finite `decision_threshold`: reasonsmith uses the distance between the engine's answer and
that threshold, ignores the record's declared margin for that decision, and records the source. If
no threshold is exposed, the declared record margin remains the compatibility fallback; malformed
thresholds and non-finite answers are refused, never guessed. This is the A2 threshold-derived
margin reading of the existing `gap <= margin` property, not a separate sign-flip verdict. The
certificate engine is the only engine that may settle it. This is the repair of an existing duty and
not a new clause: the same Recital, the same quotation and the same property shape, with both
self-declared numerical sides made measurement-aware where the artefact exposes what is needed.

**The measurable outcome passes.** `test_two_systems_differing_only_in_their_inference_get_
different_verdicts` drives the A1 pair, while
`test_an_exposed_threshold_replaces_a_generous_declared_margin` drives the A2 falsifying case:
identical generated decisions and a flattering declared margin both pass on the fallback, but the
miscalibrated engine is violated when its exposed threshold yields the smaller measured margin; the
exact engine remains satisfied. The result records `details[decision_margins]` with the source and
reason for each certified decision.

**What it reaches, and it is one artefact family.** The measurement needs a declarative model
encoding exposed through `artifact()` whose own exact side computes the semantics the system claims.
Everything else is `unattainable`: a log-only system, the language-model adapter, a recounted reason
trace, and the five `nesyarena` provenances as adapted in `docs/build_nesyarena_report.py`. A duty
that silently answered only where it could measure, while looking like it answered everywhere, would
be worse than one that refuses out loud, so the reach is stated in the pack description, in
[`docs/theory/07-explanation.md`](docs/theory/07-explanation.md) §7.1 and in the fourth column of
[`docs/refinement.md`](docs/refinement.md). The existing `artifact_logs_decision_margin` capability
remains a conjunctive reach gate; threshold exposure is not an alternative declaration.

**What this cost, stated because it is not nothing.** The previous self-declared gap and margin are
no longer trusted where the artefact supplies their measurements. A system exposing no model
encoding remains unattainable, and a system exposing no threshold keeps the old record-margin
behavior exactly. The threshold field adds no perturbation to the deletion lattice and no new rung:
the duty remains `probed` on the `artifact` basis, bounded by the artefact and trace it actually
opens up. `top-1-proofs` and `min-max-prob` remain unattainable in the nesyarena conformance report,
because its adapter still does not hand their ground programs to reasonsmith.

**What is left, and it is outside this objective's artefact reading.** The semantics claim is bound
only to the closed vocabulary and one reference this build computes; a claim this tool cannot
reference remains *not evaluated*. The decision-domain self-declaration (finding 3) is reached by
nothing here and remains recorded in *Two axes of reach are modelled* in
[`docs/refinement.md`](docs/refinement.md), because no design answer found an artefact-side handle.
Candidate B remains a separate instrument rather than a requirement verdict. Its design answer is
recorded in [`docs/theory/07-explanation.md`](docs/theory/07-explanation.md) §§7.1 and 7.7: the
reversal of the old perturbation refusal made `semantic_laws.py` able to refute a false
`claimed_semantics` from the system's own answers alone, without a reference implementation, for
each deviating nesyarena provenance while refuting the exact one on none. It deliberately returns no
`RequirementResult`; laws over the system's own answers need a perturbation surface spanning
interpretations. This A2 field only measures a threshold already exposed by the artefact; no
additional semantics reference or law set is smuggled into the duty. The remaining adapter gap is
unchanged: the two nesyarena provenances whose decisions disagree with their claimed semantics still
do not hand their ground programs to `artifact()`, so this duty cannot catch them. That is an
adapter change rather than more certificate-engine work. The intake remains the Discussion
[*reasonsmith cleared two systems whose decisions are wrong — what should a pack do about it?*](https://github.com/eduardstan/reasonsmith/discussions/59).

**A companion measurement, and what it does not close.** `semantic_laws.py` refutes a false
`claimed_semantics` from the system's own answers alone, with no reference implementation anywhere
in the loop, and does it for every one of the four `nesyarena` provenances that deviates from what
it claims while refuting the exact one on nothing. It needed a perturbation the artefact protocol
refused in writing, so [`docs/theory/07-explanation.md`](docs/theory/07-explanation.md) §7.1 records
that reversal and §7.7 states the soundness of what replaced it. This remains a measurement rather
than a verdict: no requirement reads a semantic-law refutation, and it neither widens the one
artefact family the duty above can reach nor establishes a semantics claim. `claimed_semantics` is
now a name from the closed `spec.CLAIMED_SEMANTICS` vocabulary, but the certificate's reference side
computes only exact WMC; an admitted claim for which this build has no matching reference is *not
evaluated*, never compared against exact WMC as though it had claimed distribution semantics.

## 6. The first duty written with an open-textured predicate

**The gap.** [`docs/theory/08-evidence.md`](docs/theory/08-evidence.md) §8.4 opens by stating it: twenty-one of the
twenty-nine shipped requirements are presence checks, and the fourth column of
[`docs/refinement.md`](docs/refinement.md) says the same thing row after row — *meaningful*,
*sufficiently detailed*, *adequate*, *appropriate*, *without undue delay* were not modelled. Presence
is not a bad proxy for those predicates; it is a refusal to model them at all. §8.4 also states what is
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
deliberately does **not** depend on any further engine work: §8.4 states that neither fragment reaches
an engine and that no rung of the lattice means *graded*, and a duty landing on either construct is
reported *not evaluated* with its finding beside it. The pressure it put on the evidence scale — a
graded reading having no place on the strength lattice, alongside the counterfactual fragment's two
rungs and the certificate engine's single one — **has since been designed**, once, as the evidence
*basis* dimension of `docs/theory/08-evidence.md` §8.2 rather than as more links in the chain. A shipped
graded duty inherits the `assessment` basis and is counted apart from a duty an engine failed to
settle; nothing about it now waits on that design.

## 7. Witness-checked plug-in engines

**The gap.** [`src/reasonsmith/plugins.py`](src/reasonsmith/plugins.py) says exactly what the
installed-engine path does not provide: no bound on a plug-in's runtime, no subprocess boundary or
serialisation contract with which to impose one, and no check of the reasoning behind a result below
the plug-in's self-declared ceiling. [`docs/authoring-engines.md`](docs/authoring-engines.md), *What
this is worth*, consequently says that a `proved` result from an unfamiliar engine is worth the
installer's trust in that package. Provenance makes that trust visible; it does not turn it into a
checked proof.

**Measurable outcome.** An external engine's `proved` verdict is accepted as witness-checked only
when the witness it returns re-checks against reasonsmith's core: a counterexample is replayed by the
reference interpreter, and a proof or invariant is checked by the corresponding core checker. A
result with no checkable witness remains visible as a trusted-ceiling result, naming both the engine
and that provenance rather than borrowing the built-in engine's claim. No test today distinguishes a
witness-checked plug-in result from one trusted up to its declared ceiling; that is the check that
fails now and must pass for this objective to close. This is the certifying-algorithm discipline of
[McConnell et al. (2011)](https://doi.org/10.1016/j.cosrev.2010.09.009) — the answer travels with
evidence a simpler checker can validate — applied to the extension point. The witness validation of
[Beyer et al. (2015)](https://doi.org/10.1145/2786805.2786867) is the relevant SV-COMP interchange
precedent, not a claim that its format can be adopted unchanged.

**Depends on.** The witness-format design now under way: which fragments have a checkable witness,
how that witness serialises, and what the core checker is allowed to assume. That design is also the
precondition for moving a plug-in call into a bounded subprocess. A witness format cannot make an
arbitrary engine safe to execute, and a universal result whose proof language the core does not
understand remains trusted at its visible ceiling; neither case is silently promoted to
witness-checked.

## 8. Neural systems above `observed`

**The gap.** [`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) §4 pins the shipped
neural scorer to `observed`: a log-only system cannot rise further, while the strongest results need
an exposed inference. Objective 3 records the separate counterfactual limit. The language-model
adapter now declares a finite synthetic input space over which to vary the protected variable, and
the committed transcript
in [`docs/language-model.md`](docs/language-model.md) reports the no-disparate-treatment duty at
`probed`; `test_the_language_model_cannot_be_raised_above_probed` pins that ceiling. The remaining
checks that fail today are the external-verifier path for a neural artifact and the unchanged
log-only scorer ceiling, `test_the_neural_system_cannot_be_raised_above_observed`.

**Measurable outcome.** One shipped duty is discharged above `observed` against a neural system
under test by an external verifier, through a neural `artifact()` exposure with a declared ONNX or
VNN-LIB representation. The language-model adapter also reaches the counterfactual duty through a
declared input space, so the committed transcript no longer reports that row *not evaluated* for
lack of an admissible protected-variable intervention. Both changes must preserve the distinction
the current documents make: exposing a model or an input space changes the system being audited,
not the evidential value of its old log.

**Depends on.** The neural-SUT design now under way and objective 7's external-engine path. ONNX or
VNN-LIB exposure covers only the operators, input bounds and properties the chosen verifier can
check; a model outside that fragment remains at its existing ceiling. A declared language-model
input space is likewise a bounded intervention domain, not evidence that prompts represent a
population or that a sampled replay is a proof. The current neural artifact profile is embedded
ONNX with a generated VNN-LIB 1.0 query; it does not claim VNN-LIB-only artifact support.

**Slice-4 gate result (2026-08-15).** The pinned Marabou 2.0.0 open-source CPU source commit
`d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d` was attempted by pip as an optional, separate tool, but
its build did not produce a runnable verifier on the recorded Python 3.12.9 runner. The committed
finite SAT/UNSAT corpus and semantically equivalent query mutants therefore could not establish a
clean complete-mode run. Complete mode remains refused and Marabou remains `probed`-only; no
neural verdict moved. The evidence and exact hashes are in
[`docs/neural-soundness-corpus.md`](docs/neural-soundness-corpus.md). The stated fallback is
alpha-beta-CROWN as the first `proved` integration in slice 6, subject to its own explicit status
and soundness gate.

**Slice-6 gate result.** The independent alpha-beta-CROWN adapter and differential corpus are now
implemented. The upstream repository has no release tag; the adapter pins source commit
`e5c7e17bf0488843acb77b7519f59876717a49f4` (with auto_LiRPA submodule
`5a098e8f9fb5786a428a024981d833d303921f2d`). Installation was attempted on Python 3.12.9 but
pip refused its `~=3.11.0` requirement before dependency resolution. The adapter therefore remains
at its honest `probed` ceiling, complete mode is refused, and no neural verdict moved. Native
unsafe/safe-incomplete/complete-safe/timeout/unknown statuses remain distinct; disagreements are
diagnostic and block stronger results. See [`docs/neural-soundness-corpus.md`](docs/neural-soundness-corpus.md).

## 9. A safety-commitments pack

**The gap.** Objective 4 sets the admission bar itself: a sixth pack must say which duty reaches
above `record`, because another collection of presence checks would increase breadth without depth.
The GPAI pack establishes the legitimate narrower precedent — document-production commitments can
properly refine to `record` — but it does not remove that bar for the next pack.

**Measurable outcome.** One pack from a published AI-safety framework passes every gate objective 4
already names: a retrieval record in [`docs/legal-sources.md`](docs/legal-sources.md),
character-for-character quotations accepted by the verbatim-quote test, a live source covered by
the drift workflow, and one [`docs/refinement.md`](docs/refinement.md) row per duty naming what was
left out. At least one of those duties reaches above `record`; a proposed pack containing only
document-presence duties does not close the objective. The absence of a sixth pack meeting those
conditions is the check that fails today.

**Depends on.** The framework survey now under way and the captain's choice of framework. The
choice must precede formalisation because the source decides which commitments exist and which
authority, if any, stands behind them. What reasonsmith would check is the selected framework's
formalised commitments at the evidence basis and strength each property admits — not "alignment",
not the adequacy of the framework, and not safety outside the quoted commitments.

## 10. A statistical evidence basis — **second wave**

**This is a deliberate reversal.** Objective 3 says disparate impact is *not on this roadmap to be
built*, for three reasons: a rate over a trace carries no sampling claim, no statute supplies a
generic threshold, and criteria such as equalised odds and calibration need ground truth the SUT
protocol does not expose. The reversal keeps those reasons and turns them into admission
conditions. What changed is the decision to design for them; what did not change is that no current
verdict may be read as a population claim, and no threshold may be invented by a pack author.

**The design boundary.** `statistical` becomes an explicit member of the evidence-basis dimension
defined in [`docs/theory/08-evidence.md`](docs/theory/08-evidence.md) §8.2, carrying a declared
sampling assumption, confidence level and authority-named threshold. The candidate first threshold
is the four-fifths rule in
[29 CFR 1607.4(D)](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607/section-1607.4),
whose authority and scope travel with the measurement. A duty with no named authority remains *not
evaluated* with the statistical measurement beside it; a measured ratio alone never becomes a
verdict.

**Measurable outcome.** The first disparate-impact measurement duty ships with a named authority,
an explicit sampling assumption and a declared confidence level. Today §8.2 enumerates exactly
`behavioural`, `relational`, `artifact` and `assessment`; no basis named `statistical` exists. That
enumeration is the pin that fails now and must be deliberately widened, with the basis's admitted
rungs and result invariants, when this objective closes.

**Depends on.** Objectives 7–9 landing first: this is explicitly the **second wave**, and work on it
does not begin while any of those three remains open. It then needs a statistical-design review and
the legal source for the first threshold. The design does not promise representative data, infer
ground truth, generalise beyond its declared sampling model, or turn the four-fifths rule into a
threshold for authorities or duties that do not name it.

## Infrastructure

- **Pack templates — met:** `reasonsmith init pack <name>` now creates an installable package
  over the existing `reasonsmith.packs` entry point. The generated TOML is deliberately a
  source-backed TODO; validation remains the author's responsibility in
  [`docs/authoring-packs.md`](docs/authoring-packs.md).
- **Engine templates — met:** `reasonsmith init engine <name>` now creates an installable,
  explicitly declining engine over `reasonsmith.engines`, with its declared ceiling and the
  contract in [`docs/authoring-engines.md`](docs/authoring-engines.md).
- **CI packaging — met:** [`action.yml`](action.yml) packages the landed [GitHub Actions test
  matrix](.github/workflows/ci.yml), the CLI's `--strict-unresolved` policy and its JSON `outcome`
  field as a reusable Action, while [`Dockerfile`](Dockerfile) provides the matching lightweight
  container entrypoint. The Action smoke job exercises the shipped example and uploads JSON/HTML
  reports; neither integration changes what any outcome means.
- **Versioned JSON Schema — met:** `docs/schema/report-v2.schema.json` is generated by
  [`docs/build_report_schema.py`](docs/build_report_schema.py) from report serialisations and
  `report.JSON_SCHEMA_VERSION`; its shape is checked against `to_dict()` in the test suite.
- **Static registry:** render the installed pack and engine inventory already discoverable through
  [`src/reasonsmith/plugins.py`](src/reasonsmith/plugins.py) as a static registry page; discovery is
  the source, and the page is not an endorsement or an audit of a listed package.

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
