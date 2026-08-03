# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This file starts at 0.3.0:
releases before it predate the file and are not reconstructed here.

## [Unreleased]

### Added

- **The first fairness property this repository checks: counterfactual invariance under one named
  protected variable.** Hold every input fixed, move one variable, and the decision must not move.
  It closes `ROADMAP.md` objective 3, and it is the first *relational* property here — a property
  of a **pair** of executions, where all six existing soundness paragraphs are written over one.

  - **One atom, one fragment, no hyperproperty logic.**
    `counterfactually_invariant(outcome_signal, protected_signal)` takes two signal names, never
    expressions, and they must differ. It classifies into a new `counterfactual` fragment rather
    than into `logical`, and it is the whole of a `spec` or no part of one: a conjunction,
    negation or temporal quantification over it is a load error.
  - **No trace rung, enforced below the ladder.** `report._engine_ladder` gives the fragment two
    rungs — Z3 self-composition at `proved`, paired replay through `decide()` at `probed` — and
    nothing that reads a decision log, plug-ins included. A trace holds what a system decided and a
    counterfactual asks what it would have decided, so `rulelang.eval_expression` refuses the atom
    outright; every trace-reading engine evaluates through that interpreter, which makes this a
    fact about the code rather than a convention the ladder is trusted to keep.
  - **Unawareness is not a discharge.** A system that accepts the protected variable and whose
    rules provably never let it move the outcome is `satisfied` at `proved`. A system whose
    declared logic has *no notion* of the variable is `unattainable`, never satisfied. Without the
    `computes` direction declaration of 0.6.0 these are indistinguishable — in both, the name is a
    free constant the outcome does not depend on and the negation is `unsat` — so a system
    declaring no directions is reported not evaluated rather than guessed at.
  - **The pair witness is cross-checked and replayed on both halves.** The premise model is checked
    against the reference interpreter on *each* copy of the encoding, and a counterexample pair is
    replayed as both of its inputs with the outcomes compared, so this engine's runtime-agreement
    guarantee is no weaker than any other engine's while it claims the same rung.
  - **The protected variable is never read from the trace.** At `proved` the admissible values are
    every value the declared `constraints` admit; at `probed` they are enumerated from those same
    constraints. Nothing here is a reason to log a prohibited basis for anybody.
  - **The duty:** `ecoa_reg_b_1002_4_a_no_disparate_treatment`, anchored to 12 CFR 1002.4(a) — the
    disparate-*treatment* limb of Regulation B, retrieved and recorded in `docs/legal-sources.md`
    with its eCFR endpoint and re-fetchable by `python -m reasonsmith.drift`. Not GDPR Recital 71:
    that recital's limb is *discriminatory effects*, and effects is the limb a property of a pair
    of decisions cannot reach.
  - **What it cannot see, stated on every result it produces** (`TREATMENT_LIMIT`) and in a
    `docs/refinement.md` row: a proxy is invisible to it — a rule set that never reads the
    protected variable and decides by postcode is `satisfied` — it says nothing about disparate
    impact, it quantifies over the input space the system's own `constraints` declare, and it
    reaches exactly one of the nine prohibited bases 12 CFR 1002.2(z) lists.
  - `docs/refinement.md`'s sentence *no fairness property is checked by any requirement in this
    repository* was **narrowed rather than deleted**: no *distributional* fairness property is
    checked, and the one that is checked cannot see a disparate impact. `applicant_prohibited_basis`
    is the first shipped signal that is a fact about a natural person rather than about a system,
    so it sits outside the paper's four Section 6.3 categories and is pinned as the sole exception.

- **`reasonsmith.examples.truncating_credit_system` — the first shipped example that comes back
  `violated`.** Its three siblings all pass, so a reader who ran every shipped example never saw
  the tool report a breach, and a breach is the memorable result. It runs the demonstration's own
  `TruncatingCreditSystem` — imported from `reasonsmith.demo`, not reimplemented — against 12 CFR
  1002.9(b)(2)'s *content* duty and names the four reasons the system's inference used and its
  notice did not. `reasonsmith check --help` now ends in worked examples with that run first, and
  every command there works from a bare `pip install`.
- **[`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md)** — the four things this tool
  cannot do, stated together with the numbers, each citing the committed document that already
  states it: it takes a system's word about what it is, 21 of 28 shipped requirements are presence
  checks, a rung is not a grade, and the strongest rungs need a system that exposes its inference.

### Fixed

- **Breaking (verdicts move): a duty whose trigger never fired is reported *not evaluated*, at
  every rung.** A creditor whose rules assign `artifact_logs_reason_explanation = ""` on every path
  was reported, in one report, *violated* on 12 CFR 1002.9(a)(2) for giving neither reasons nor a
  disclosure and `satisfied` at **`proved`** on 12 CFR 1002.9(b)(2) for the specificity of the
  statement it never made. `unsat` on the negated property was read as a proof; it was the
  implication's antecedent being unreachable. The rule that replaced it: where a requirement's
  property is an implication and the engine's evidence domain contains no element satisfying its
  antecedent, the result is *not evaluated*, `strength=None`, naming the antecedent that never
  fired and the domain that was searched (`report.VACUOUS_TRIGGER_KEY`).

  - **One guard, expressed once.** The vacuity is a property of the *formula*, not of the evidence,
    which is why seven engine-local domain guards found it nowhere.
    `rulelang.implication_antecedent` names the subtree — one property language, one antecedent,
    whatever surface syntax the pack used — and
    `report.not_evaluated_for_unreachable_trigger` words the refusal against the result model.
  - **Every rung asks it of the domain it quantifies over.** `proved` checks premises ∧ antecedent
    satisfiable, which is the existing premise check one quantifier deeper and the same three lines
    `engines/counterfactual.py` already ran for its own fragment; `temporal` inherits it through the
    `always(f)` reduction; `observed` monitors the antecedent as a sub-formula per position;
    `probed` counts the replayed decisions that reached it, in the walk the interpreter already
    makes; the certificate rung counts the certified decisions that reached it, in the walk that
    already decides the property against the measured count. The replay rung is included because
    the engine ladder falls to it: guarding the proof rung alone moved the vacuous `satisfied` down
    a rung instead of removing it. The certificate rung is included because the ladder gives
    `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` that rung and no other, so nothing beneath
    it could have caught the same empty claim.
  - **Earned verdicts are untouched.** A satisfaction whose antecedent does fire still reaches
    `proved`; a violation never could be vacuous, so the guard runs on the satisfied path only; a
    property with no implication in it is unchanged at every rung.
  - **What it costs, accepted knowingly.** Duties that landed in the `satisfied` column land in
    *not evaluated*, and headline counts and exit codes move with them. A creditor lawfully on the
    12 CFR 1002.9(a)(2)(ii) disclosure branch is one of them: no longer accused, and no longer
    cleared either. `not applicable` remains the honest verdict there and remains unreachable — it
    is a per-record question and the result model has no per-record applicability. No shipped
    example, generated document or published number moved: every byte-pinned builder rewrote
    identical bytes, because every shipped demonstration system states reasons.
  - **Two shapes deliberately out of reach**, stated rather than guessed at: `eventually(f)` is not
    stripped the way `always(f)` is — its vacuity is about a position that never existed, not a
    trigger that never fired — and a conjunction of implications has a vacuity per conjunct that one
    `strength=None` cannot carry.

  `docs/semantics.md` §3 and §4 state it per rung; `tests/test_vacuous_trigger.py` holds it. The
  test that pinned the old behaviour as a known limit
  (`test_a_duty_whose_trigger_never_fires_is_satisfied_vacuously_and_the_report_cannot_say_so`) now
  pins the new one under the name
  `test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung`.

### Changed

- **The README leads with the deleted reasons.** The reason-deletion run, its transcript and the
  limits document are the first screen after the badges; *The state of the art, the gap, and what
  this adds* keeps every word and moves below the demonstration. A timed cold read of the repository
  found the strongest result four screens down and reachable from no `--help` string. Also corrects
  two stale counts against `validate-pack`'s own output: 21 of 28 requirements are presence checks
  (not 22 of 28), against three `temporal` (not two).
- `_Scope` in `engines/proved.py` takes a namespace, so one rule block can be encoded twice into
  one solver without the two copies collapsing into each other. An SSA label is `name#version`,
  unique within one execution and identical across two. The `logic()` reader and the
  decision-runner selection are shared with the new engine rather than duplicated; no existing
  message or verdict changed.

## [0.6.0] - 2026-08-03

### Changed

- **Breaking:** **An adapter declares which variables the system computes, and the proof engine
  uses that instead of guessing** ([#92](https://github.com/eduardstan/reasonsmith/pull/92)).
  `sut.logic()` may now carry `computes` beside `variables`, `rules` and `constraints`: the names
  the system *produces*, as against the ones its decision situation supplies. It is breaking
  because it widens what an adapter exposing logic is expected to say about itself, and because a
  system that declares it computes a name its exposed rules never settle now loses a proof it
  previously got.

  The gap it closes is in `_Scope.read`, which declares a free Z3 constant for any name it meets
  and keeps no record of where the name came from. It runs while encoding the *property*, so a duty
  that merely mentions a name manufactured an input out of nothing and everything downstream
  reasoned about a constant nobody computed. That is how
  `gdpr_recital71_error_risk_minimised` came to be reported `violated` at `proved` — the one
  verdict that exits non-zero — against a system whose rules never touch the two magnitudes it
  compares. Neither existing declaration could carry the fix: `variables` is a type table holding
  computed names beside free ones, and `declared_capabilities` is what a system can *emit* into a
  decision record, which is the opposite direction.

  `variables` and `computes` together split every name into three states, and
  `engines/proved.py`'s `_check_declared_directions` reads them: a name in `computes` is an output,
  a name in `variables` but not in `computes` is an input, and a name in neither is one the system
  has **no notion of**. A property reading a name in that third state is refused, and so is one
  reading a declared output the exposed rules do not settle on every path. A declared *input* is
  quantified over where the property also reads a name the rules settle, or reads its free names as
  flags rather than magnitudes — the fix below narrows that to what it always should have been —
  which is what keeps `income >= 30000 implies approved` and
  `gdpr_art22_1_no_prohibited_decision_for_any_input` provable, the latter's whole purpose being to
  range over flags no rule assigns.

  `RulesAdapter` derives `computes` from its own rules' assignment targets unless the caller
  overrides it, so no adapter in this repository is undeclared: the premise of that adapter is that
  its rules *are* the decision procedure, under which the names they assign are exactly the names
  the system computes. A declared name outside `variables` is refused at construction. Nothing
  second-guesses a declaration beyond that — an adapter calling an output an input is answered
  about the system it described, the same trust `system_domains` is given.

  0.5.1's sort heuristic, `_check_magnitudes_are_computed`, is **kept** rather than removed. It
  cuts along the wrong joint and its own docstring said so, but every alternative is worse:
  reading `variables` as "every variable is an input" hands back exactly the `violated`-at-`proved`
  verdict it was written to stop, and refusing every proof to logic predating the declaration would
  withdraw verdicts for a reason having nothing to do with the system. It runs **beside** the
  declaration guard rather than being scoped to logic that declares none — see the fix below, which
  corrects that in the same release.

  `docs/semantics.md` §3.5, *When the magnitudes are not the system's own*, is rewritten around the
  declaration and names the test behind every claim.

### Fixed

- **A decision whose reasons bounded proof enumeration never found buys no verdict, and never
  `satisfied`** ([#94](https://github.com/eduardstan/reasonsmith/pull/94)). The certificate engine
  read one number off the certificate — `len(cert.deleted)` — and never consulted the certificate's
  own verdict. With nothing enumerated that number is zero for the absence of a measurement rather
  than for a decision whose reasons the system's answer all depended on, and `uncertified`,
  `caveat` and `skipped` are empty too, so the engine reported a clean unqualified probe.

  Taking the demonstration's own `TruncatingCreditSystem`, which provably deletes four of five
  legally owed reasons behind `APP-1042`, and moving only the artefact's `exact_depth` from 1 to 0
  turned `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` from `violated` at `probed` (exit 2)
  into `satisfied` at `probed` (exit 0) — same rules, same trace, same reasons, same notices, with
  the budget line itself reading `reasons switched off: 0`. Weaker evidence bought the strongest
  verdict available on the duty, and it needs no intent: a misconfiguration, a program that grew a
  rule layer or a wrong query identifier produce the same artefact.

  `certificate.Certificate.verdict` already refuses to call an un-enumerated query a `PASS`, on the
  ground that a zero value gap on one is not agreement because exact inference never evaluated it.
  The engine now makes that refusal, through `conformance.measured(cert)` — this package's single
  predicate for whether a certificate measured anything at all, and the no-enumerated-reason clause
  of that property — rather than reading the count. Such a certificate is dropped from the certified
  set, counted in `decisions_without_an_enumerated_reason`, and named in the summary.

  A violation needs one witness; a satisfaction needs complete evidence. A breach measured on a
  decision that *was* enumerated is still reported `violated` at `probed`, naming the unmeasured
  decisions beside it, while a run that would otherwise be `satisfied` is *not evaluated* the moment
  one certified decision went unmeasured, naming `artifact_logs_deleted_reason_count` as unmeasured
  for it: satisfaction over a subset of the trace is not satisfaction over the trace. Anything
  weaker is defeated by the same move it was written to stop — declare `exact_depth=0` on every
  decision but one genuinely clean one. A system that genuinely enumerates reasons and deletes none
  still reaches `satisfied` at `probed`. `docs/semantics.md` §3's certificate guarantee now says
  enumeration found *at least one* reason on *every* decision the verdict covers, and states the
  asymmetry in the same words.

- **A declaration of what a system computes can no longer widen what it can be proved about**
  ([#95](https://github.com/eduardstan/reasonsmith/pull/95)). `_check_declared_directions` ran
  *instead of* `_check_magnitudes_are_computed` wherever `sut.logic()` declared `computes`, and it
  asked only whether a name was in `variables ∪ computes`. But `variables` is a **type table**: a
  caller listing a signal its system merely *logs* is naming a sort, not declaring an input the
  decision situation supplies, and the three declared states have no seat for that name. Read as an
  input, it made both `proved` verdicts a function of the caller's type table. A scorer deciding on
  a score alone, whose table names the two Recital 71 magnitudes, was reported `violated` at
  `proved` on the solver's own choice of `deviation = 1, margin = 0`; add one constraint restating
  the duty and the same system was reported `satisfied` at `proved`, on the strength of an
  assertion about itself that no rendering names — the self-declaration `docs/semantics.md` §3
  refuses everywhere else, arriving at the top rung. Stripping only the `computes` key from either
  system returned `inconclusive`, so both were new.

  Both guards now run wherever directions are declared: the declaration **narrows** what reaches
  the solver and can no longer widen it. That is the additional-filter route rather than a wider
  first refusal, because refusing a name the rules and constraints never read answers the first
  construction and not the second — a constraint restating the duty *does* read both magnitudes,
  and the false `satisfied` would have survived it. The sort heuristic answers both by asking what
  the property reads, and both refusals now fire after the property is encoded, so `present()`'s
  and `contains()`'s more specific messages still win.

  What does not change: a system whose rules genuinely compute a magnitude is still `violated` at
  `proved` where its declared deviation can exceed its own margin;
  `gdpr_art22_1_no_prohibited_decision_for_any_input` still quantifies over the Article 22 flags no
  rule assigns; a system with no notion of the magnitudes is still `inconclusive`; and a malformed
  `computes` is still refused before any solver call. The stated cost is in `docs/semantics.md`
  §3.5: a duty comparing declared-input magnitudes alone, reading no name the rules assign, cannot
  be `proved` even where the declaration is exact.

- **The README's conformance-check block is held to its builder** ([#93](https://github.com/eduardstan/reasonsmith/pull/93)).
  It was the one derived transcript byte-for-byte pins did not hold, and it went stale once already
  under a green suite. `tests/test_docs_readme_transcripts.py` loads `docs/build_readme_transcripts.py`
  and asserts the committed README equals the builder's own output, the same load-by-path, verbatim
  comparison the other pins use. `AGENTS.md`'s index now names the test.

- **A requirement identifier no longer renders under its own badges** ([#90](https://github.com/eduardstan/reasonsmith/pull/90)).
  The requirement card header is one flex row — identifier and citation left, badges right — and
  its left item had a zero flex basis with a 16rem floor, narrower than a requirement identifier.
  Between roughly 768px and 1000px the desktop row still applied and there was no room for a long
  identifier beside three badges, so the identifier overflowed *under* them and the two printed on
  top of each other. A tablet, a half-width desktop window and every frame in
  `docs/audiences.html` are in that band. The left item now has a real basis (`flex: 1 1 26rem`),
  so the badge group drops to its own line before anything can collide, and the identifier carries
  `overflow-wrap: anywhere` as the backstop for a phone width no reflow can rescue. Measured in
  Chrome from 375px to 1440px on both generated pages: no overlap at any width, no card overflow,
  no horizontal page scroll. `docs/report.html` and `docs/audiences.html` are regenerated.

- **The audience gallery opens where the documents differ** ([#90](https://github.com/eduardstan/reasonsmith/pull/90)).
  `docs/audiences.html` embeds one run rendered for five readers, and every frame opened at the top
  of its document — where the masthead, the headline banner and the dashboard are chrome no audience
  projection touches. Four of the five were byte-identical for their whole first screen and the
  first real difference sat below every frame's visible area, so the page claimed a difference it
  never showed. Each frame is now scrolled on load to `id="findings"`, the anchor `render_html`
  already carries for its own skip link, and `FRAME_HEIGHT` drops to 24rem so two frames fit one
  screen: the auditor's card carries the binding and domain chips, the lattice and the signals row;
  the developer's drops the chips; the regulator's and the deployer's drop the signals row; the
  affected individual's shows three whole cards where an expert reading shows one. One anchor and
  one height for all five, so this is a scroll position and not a crop — nothing cropped, restyled
  or reordered, every frame still holding its whole document, and with scripting off the frames open
  at the top exactly as before. `test_every_frame_opens_where_the_documents_differ` guards what the
  byte-for-byte pin cannot: an `id` renamed in `render_html` would return every frame to the top
  silently and the pin would still pass.

## [0.5.1] - 2026-08-02

### Added

- **The `--json` envelope names its own shape** ([#88](https://github.com/eduardstan/reasonsmith/pull/88)).
  `reasonsmith check --json` emitted eight keys and no version, so a consumer building on it could
  not tell one release's shape from another's. The envelope now leads with `schema_version`, an
  integer starting at `1`. It is deliberately not the package version — pinning it there would
  make every release look like a shape change to someone diffing it. It increments when a key is
  removed, renamed, or changes type or meaning, and not when one is added, because a parser
  reading the keys it knows is unaffected by a key it has never seen.
  `tests/test_json_schema_version.py` writes out the key set at both levels beside the number and
  checks set equality, so a shape change made without moving the version fails the suite. What
  that does not catch — a key whose meaning drifts while its name and type hold — is stated on
  `JSON_SCHEMA_VERSION` rather than built around.

### Fixed

- **The stylesheet comment explaining the report's serif is in English** ([#88](https://github.com/eduardstan/reasonsmith/pull/88)).
  It was written in Italian, alone in the repository. Translated with its reasoning and its
  upgrade path intact — it says why the report uses a system serif rather than the landing page's
  Newsreader, and what inlining that font would cost. A grep found no other non-English comment.

### Changed

- **The generated report dims** ([#88](https://github.com/eduardstan/reasonsmith/pull/88)).
  The dossier is the artefact people read at length and was the only document on their screen with
  no dark scheme. The palette was already token-driven, so this is a second set of values under
  `@media screen and (prefers-color-scheme: dark)` rather than a second stylesheet. `screen` is
  load-bearing and pinned by a test: the `@media print` block assumes the light token values, so a
  dark override matching print media would have printed white text on a white sheet. Two token
  pairs moved first. The report header was `background: var(--ink); color: var(--surface)` — an
  inversion of the page, which inverts back into a *light* band on a dark page — so it gains its
  own `--band`/`--band-ink`/`--band-faint`/`--band-line`/`--band-accent` tokens and stays a dark
  band in both schemes; the three hardcoded `oklch(...)` values inside it were the same assumption
  spelled literally and now read those tokens. Solid chips — the strength lattice's active step,
  the binding badge, the skip link — paired a solid fill with `color: var(--surface)`, which puts
  near-white text on a light green fill in a dark scheme, and now pair with `var(--paper)`, which
  inverts correctly in both directions. The key-finding section's own stylesheet in `demo.py` had
  both defects, plus a subtitle grey hardcoded for a dark band that landed on a light card; fixed
  there too. Satisfied-green and violated-red carry meaning in this document, so the dark values
  keep their hues (155 and 25) at chroma 0.13-0.14 against tinted grounds rather than desaturating
  toward a common grey, and `test_both_schemes_keep_the_verdict_colours_apart` pins the hue
  channel of `--ok` and `--accent-deep` in both blocks — a scheme collapsing the two hues would
  pass any contrast check and would still have destroyed the distinction the reader uses. Nothing
  external was added: `test_the_dark_page_is_still_self_contained` holds that.

- **The affected-individual report is derived for its reader, not the expert report with parts
  removed** ([#84](https://github.com/eduardstan/reasonsmith/pull/84)).
  `AudienceProjection` was eight booleans that only turned things off and `affected-individual`
  set all eight, so the person whose credit was declined received four machine identifiers, four
  statute citations, four verdict words, a 222-word disclaimer longer than all of it together,
  and not one sentence about the decision — a word set that was a strict subset of the developer
  view's, with an empty difference. In HTML every finding drew a verdict chip over an empty box.
  The projection gains one field that **emits**, `plain_account`, turning on
  `render._lay_sections`, and everything it prints is quoted rather than composed: the decision
  and the reason out of the trace the run already read, now carried on the report as
  `ConformanceReport.decisions`, and a reason left unstated out of the certificate engine's own
  measurement. No statute is paraphrased and no decision explained. Where there is nothing to
  quote it says so — a run that read no decision record, and a run where nothing measured whether
  the stated reasons were complete, both say that rather than going quiet, because silence there
  reads to this reader as a clean result. A card body is emitted only when something goes in it,
  and the limits stay whole for every audience while folding into a native `<details>` on the lay
  page alone, so a required disclaimer is no longer the largest thing on a page addressed to a
  layperson. `test_the_lay_view_derives_content_no_expert_view_carries` keeps the subset
  measurement as an assertion; the four expert projections are untouched, and every generated
  document regenerates byte-for-byte. `docs/semantics.md` §7 loses the limit it used to state and
  gains what replaces it.

### Documentation

- **The published dossier says what it is, and states an origin claim a reader can check**
  ([#85](https://github.com/eduardstan/reasonsmith/pull/85)).
  `docs/report.html` is a fixed exhibit — the `table7` pack against the committed sample log,
  and it stays that way — but nothing on the page said so, so a reader could not tell a
  capability the engine lacks from one this run does not exercise. A short passage now names
  four that are shipped and unexercised here, each beside the document that shows it: the
  `proved` rung via Z3, the `--audience` projections, the packs beyond `table7` including the
  EU AI Act's Articles 53 and 55, and engines and packs installed as plug-ins. The provenance
  bar also stopped reading as a defect. It said `Generated without an identified source commit`
  while a user's own `--html` run names one, and that gap cannot be closed with a hash: the
  commit carrying the page does not exist while the page is rendered, so any hash written there
  names another commit and breaks the byte-for-byte pin as soon as the page is committed. The
  page now names the command and the test that fails if re-running it in any checkout does not
  rewrite the page identically — the claim `docs/nesyarena-conformance-report.md` already
  carries. `render_html` gained a caller-owned, escaped `provenance_note` for origin claims the
  renderer cannot establish for itself.

- **The nesyarena findings document can no longer go stale silently**
  ([#82](https://github.com/eduardstan/reasonsmith/pull/82)).
  `docs/findings-nesyarena.md` is hand-written prose that quotes counts living in generated
  artefacts — the conformance report, the builder's `DECLARED_SIGNALS` / `UNDECLARED_SIGNALS`,
  and the per-formalism requirement census of the packs — and nothing held the prose to those
  sources, so every pack change sent the figures stale (three fix rounds in one earlier task,
  and two stale figures that predated even those). `tests/test_findings_nesyarena.py` now
  derives every quoted figure from the run the builder drives and fails when the prose
  disagrees, naming the figure and what to regenerate. Finding 2 is re-derived against the
  current counts: the ten unattainable results are the GDPR logical duty and the GDPR record
  duty `gdpr_art22_1_automated_decision_prohibition`, not the GDPR logical and ECOA timing
  duties the earlier account named, and the conclusion still holds — the Z3 proved engine and
  the replay probed engine never ran, because no `logical` duty reaches an engine in this run
  and the adapter exposes no real `logic()` or `decide()`. Finding 3's counterfactual is
  corrected too: a `consumer-credit` run would leave two ECOA duties unattainable, not one.

### Added

- **The audience projection is published working, not described**
  ([#87](https://github.com/eduardstan/reasonsmith/pull/87)). The most distinctive thing this tool
  does — the same verdicts reaching five readers as five documents — could be read about and not
  seen: `docs/report.html` publishes one run for one reader. `docs/audiences.html`, generated by
  `docs/build_audiences.py` and pinned byte-for-byte by `tests/test_docs_audiences.py`, publishes
  one run rendered five times. The run is the shipped `symbolic_rules` system against the `ecoa`
  pack, chosen because every projection has something to withhold in it: two duties `proved` by
  Z3, one `observed`, one `unattainable` for a named missing capability, and a plain-language
  account quoting the two decisions the system recorded. The regulator's document drops the
  missing-capability finding the developer's keeps, the deployer's drops the signal lists, and the
  affected individual's drops the strength lattice and half the page with it while saying plainly
  that nothing in the run measured whether the stated reasons were all the reasons. Every frame is
  a complete `render_html` document embedded verbatim; nothing on the page is transcribed. The
  page is itself a `render_html` page, because the design tokens live inside that function's
  stylesheet and are not exported — being a report is the only way the gallery styles itself
  without a second palette — and the test fails if it grows a `<style>` block, a colour literal, a
  font stack, a token the renderer does not define or a class it does not style.
- **A temporal duty reaches `proved`, where its shape reduces to a property of one decision**
  ([#81](https://github.com/eduardstan/reasonsmith/pull/81)). `ROADMAP.md` objective 1. Every
  `temporal` duty stopped at `observed` whatever a system exposed, because the solver and the replay
  search each reason about one decision at a time and had nothing to say about a formula quantified
  over a trace. One shape does have something to say to them, and it is the one both shipped
  temporal duties are written in. A conformance run reads a **finite** decision trace — LTLf, not
  LTL — and over a finite trace `always(f)` holds exactly when `f` holds at every position; every
  position of every trace a system can emit is a decision its exposed `logic()` produces from an
  input its own `constraints` admit. So proving `f` over that input space proves `always(f)` for
  every trace the system can emit, which is strictly more than the one trace a run reads.
  `engines/temporal.py` is that reduction and nothing else: it hands `f` to the proved engine and
  inherits every refusal that engine already makes. `eventually(f)` asserts that some position
  *exists* — a fact about the trace a system emitted rather than about the decisions its logic
  admits — so it does not reduce and stays at `observed`, as does every nested shape. **The two
  verdicts are not mirror images and the result says so:** satisfied is universal and covers every
  trace, violated is existential and names an admissible input whose decision breaches the property,
  which is a finding about the system as built and not about the trace supplied.
  `TRACE_SEMANTICS` travels on every result the engine returns, for the same reason the probe budget
  does. **No new dependency**, decided rather than defaulted: an LTLf decision procedure was priced
  first, and neither candidate installs from PyPI without a system package — `ltlf2dfa` shells out
  to a MONA binary its wheel does not carry, and PyPI's `spot` is an unrelated 2013 package rather
  than the Spot library — but this fragment needs neither, because `always` distributes over
  positions and what is left is a state property Z3 already decides here under guards that took
  several releases to write. It is vendored rather than shipped through the `reasonsmith.engines`
  entry-point group for the same reason: that surface exists so an *optional* dependency can stay
  optional, and there is no optional dependency here. `temporal` joins `BUILTIN_ENGINE_NAMES`, so an
  installed plug-in cannot take the name. `test_a_temporal_duty_never_rises_above_observed` is
  *replaced*, never deleted, by `test_only_always_reaches_the_temporal_proof_rung`, which pins the
  new ceiling from both sides; the soundness paragraph is `docs/semantics.md` §3, *`proved`, over a
  trace*. `examples/symbolic_rules.py` gains the notification and margin rules the two shipped
  temporal duties read — both duties reported `unattainable` against it before — and its docstring
  names the two of those rules that state a policy commitment rather than measure anything, because
  that is what the proof is worth.

- **A GPAI pack, and the first duties to use the `general-purpose` class**
  ([#80](https://github.com/eduardstan/reasonsmith/pull/80)). Eight requirements from Articles
  53(1)(a)-(d) and 55(1)(a)-(d) of Regulation (EU) 2024/1689 — the obligations of a provider of a
  general-purpose AI model, and the additional obligations where the model has systemic risk.
  `general-purpose` had been a member of `spec.REGULATORY_CLASSES` since the class gate landed and
  was used by zero shipped requirements, so the gate had a member no run had ever exercised; these
  eight exercise it. A system declaring the class gets verdicts, one declaring nothing is reported
  not applicable on all eight, and reasonsmith still never infers the class.

  The retrieval record came first. `docs/legal-sources.md` recorded CELEX `32024R1689` as a
  *document*, but its verbatim section held Articles 12 and 13 only, so Articles 53 and 55 were
  re-fetched from the same official Cellar XHTML endpoint on 2026-08-02 and transcribed before the
  pack quoted a word of either. `gpai` joins `drift.STATUTORY_PACKS` and the eight clauses join
  `PROVISIONS`, so the monthly statute-drift workflow re-verifies these quotes against the print;
  the AI Act fixture gains the `053.001` and `055.001` divisions and is renamed to stop claiming it
  holds only Articles 12 and 13.

  **Every requirement is a presence check, and the pack says so rather than implying otherwise.**
  For a duty to draw up a document, presence is the correct refinement and no stronger property
  exists to write; it is not a refinement of the adequacy words the same clauses attach — whether
  the technical documentation carries what Annex XI asks for, whether the training-content summary
  is *sufficiently detailed*, whether the copyright policy is honoured in practice, whether an
  evaluation *reflects the state of the art*. Each has its own row in `docs/refinement.md`, along
  with two limits that ride on the whole pack: these are duties about a model read off a decision
  record, and Article 55's systemic-risk trigger is not modelled, so declaring `general-purpose`
  reaches all eight duties.

  Article 55(1)(c)'s *without undue delay* limb is deliberately not formalised. A temporal property
  could bound a reporting latency the way the ECOA notice duty does, but that clause supplies its
  own 30 and 90 days and this one supplies no period at all; a constant chosen here would be a pack
  author's figure presented as the Act's, and a self-declared deadline signal would be the system
  grading itself. The duty is written on its three artefact limbs and the record states the
  consequence: a provider that reported a serious incident a year late is `satisfied` on it.

### Changed

- **The presence-check ratio moved the wrong way, and the documents that count it say so**
  ([#80](https://github.com/eduardstan/reasonsmith/pull/80)). 21 of 27 shipped requirements are now
  `record` duties, up from 13 of 19. `ROADMAP.md` objective 4 records that the fifth pack met its
  measurable outcome in full while leaving the judgement it names *less* settled than before —
  breadth bought this way is real breadth and it is not depth — and puts the ask on a sixth pack:
  say which of its duties reaches above `record`. The README's researcher paragraph carries the
  same number.

### Fixed

- **A proof needs a magnitude the system computes**
  ([#86](https://github.com/eduardstan/reasonsmith/pull/86)).
  `gdpr_recital71_error_risk_minimised` compares a declared deviation against a decision's own
  margin. Against a rule set that decides on a score alone and assigns neither name, both were free
  constants of the Z3 encoding, so the solver picked `deviation = 1, margin = 0` and the
  counterexample verification reproduced it — the reference interpreter is handed the same free
  inputs. A clean system was reported `violated` at `proved`, the one verdict that exits non-zero,
  on arithmetic over numbers nobody computed. `engines/proved.py` already refuses exactly this for
  `present()` and `contains()`, on the argument that a name the rules read and never write is a
  fact about the encoding; `_check_magnitudes_are_computed` is the third call site of that refusal.
  It is narrow — it fires only when the property reads no assigned name at all *and* reads some
  free name as a magnitude — and both conditions are load-bearing: `income >= 30000 implies
  approved == True` stays provable because it reads a computed `approved`, and
  `gdpr_art22_1_no_prohibited_decision_for_any_input` keeps its proof because its free names are
  Booleans, which that duty quantifies over on purpose. The refused duty falls to the engine that
  reads the trace, which measures the magnitudes where the decisions carry them. The cut by sort is
  a **heuristic**: the distinction that matters is an input to the decision situation against an
  output the system computes, and `logic()` declares sorts but not directions. `docs/semantics.md`
  §3.5, *When the magnitudes are not the system's own*, states that and states the principled
  closure — an adapter declaring the direction per variable — which widens a contract every
  existing adapter implements and is not made here. The temporal reduction that made this reachable
  is sound and is untouched.

## [0.5.0] - 2026-08-02

**Breaking:** the example systems and the sample decision log moved from `docs/adapters/` and
`docs/sample_decisions.jsonl` into the `reasonsmith.examples` package, so a command from 0.4.0's
README that names those paths must be updated — use `python -m reasonsmith.examples.<name>`,
`--system-module reasonsmith.examples.<name>:system_under_test`, and `python -m reasonsmith.examples`
for the log's directory.

### Documentation

- **The empty `stability_signals_` category is recorded rather than filled**
  ([#83](https://github.com/eduardstan/reasonsmith/pull/83)). `docs/authoring-packs.md` names four
  Section 6.3 signal-name prefixes; three are exercised by the shipped packs — `provenance_` by
  fourteen distinct signals, `artifact_logs_` by nineteen, `scope_statements_` by five — and
  `stability_signals_` by none, while `src/reasonsmith/examples/sample_decisions.jsonl` emits
  `stability_signals_artifact_drift` that no duty reads. `docs/refinement.md` now says why: **no
  statute this repository can source obliges stability, drift or consistency as a property of a
  decision record.** EU AI Act Articles 15(1), 15(3), 72(1)–(2) and 26(5), GDPR Recital 71 and
  Article 5(1)(d), and 12 CFR 1002.9 and 1002.12 were each read against the live official text and
  rejected — every one binds the design of a system, an accompanying document, or an organisation
  over time, never one decision. Recital 71 carries no regular-checking language; it was read in
  full for it.

  The section states the three things that would change the answer — a statute obliging a
  per-decision stability figure, a result model that can read an artefact that is not a decision
  record, or a verdict that is a property of a trace rather than of the records in it — and why a
  duty written today would be worse than the empty category: it would read a figure the system
  declares about itself with no clause requiring the figure, which is
  `gdpr_recital71_error_risk_minimised`'s documented weakness without that duty's saving grace of
  being bounded by another quantity the same record supplies. No pack changed, no signal was
  renamed, and the unread signal stays in the sample log.
- **The front page shows the audience view and says the tool is extensible**
  ([#78](https://github.com/eduardstan/reasonsmith/pull/78)). Two capabilities shipped and were
  invisible on `README.md`: `--audience` appeared nowhere on it, and neither did the engine and pack
  entry-point groups, so the answer to *can it use a different formalism?* was unfindable outside
  `docs/authoring-engines.md`. The README now *shows* the projection rather than describing it —
  the demonstration run rendered for a regulator and for the affected individual, both generated by
  `docs/build_readme_transcripts.py` alongside the transcripts already there — and states the
  feature's honest limit in the same breath: the affected-individual view carries the duties and the
  verdicts and none of the reasons for the decision. The architecture table gained `render.py`,
  `plugins.py`, `examples/` and `__init__.py`, and `docs/README.md`'s index row for
  `semantics.md` now names §7 so the audience table is findable from the index. No behaviour
  changed; the five audiences and the plug-in surface are unaltered.
- **The two audience lists are kept apart on purpose**
  ([#78](https://github.com/eduardstan/reasonsmith/pull/78)). `--audience` names five *readers of
  one report*; *Who could use this, and what is missing first* names four *parties who might adopt
  the project*, each with a committed blocker. They share two words and neither refines the other,
  so the second section now says which question it answers and why merging the lists would be
  wrong.

### Fixed

- **The documented commands run for someone who only ran `pip install reasonsmith`**
  ([#77](https://github.com/eduardstan/reasonsmith/pull/77)). Three commands on the
  README's first screens failed for exactly the audience the README is written for: the wheel
  shipped `table7.toml` and the packs and nothing else, so the sample decision log and the three
  example systems — the *one duty, three systems, three rungs* demonstration the project's
  argument rests on — were not on disk after an install, and `docs.adapters.…` could never resolve
  as a module from a distribution that carries no `docs/`. The four example systems and
  `sample_decisions.jsonl` now live in `src/reasonsmith/examples/` and ship in the wheel, so
  `python -m reasonsmith.examples.symbolic_rules`,
  `--system-module reasonsmith.examples.symbolic_rules:system_under_test` and the sample-log run
  all work with no checkout; `python -m reasonsmith.examples` prints the directory the log was
  installed into, which is what lets the README's `--system` command stay a literal command.
  `tests/test_packaged_examples.py` builds the wheel and reads what is inside it, because from a
  checkout every missing file was right there and nothing could see the defect.
- **`reasonsmith --version` prints the version instead of exiting 2**
  ([#77](https://github.com/eduardstan/reasonsmith/pull/77)). It reports
  `reasonsmith.__version__`, the number `tests/test_release_discipline.py` already holds to
  `pyproject.toml`, the changelog and `CITATION.cff`, so it cannot print a version the tree is not.

### Changed

- **The dossier's key finding is a conformance run, not a narrated pair**
  ([#75](https://github.com/eduardstan/reasonsmith/pull/75)). The exhibit beside `docs/report.html`
  drew an evidence record marked `COMPLETE` next to a reason-deletion certificate marked `FAIL` —
  computed live, so nothing on the page was false, but framed as it was before the certificate
  became an engine. `reasonsmith.demo.render_key_finding_html` now renders an actual `ecoa` run
  against the demonstration's own pipeline (`key_finding_report()`), and the two halves of 12 CFR
  1002.9(b)(2) come apart as verdicts: `ecoa_reg_b_1002_9_b_2_specific_reasons` **satisfied** at
  `observed` on the notice's form, `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` **violated**
  at `probed` on its content, carrying the deleted reasons and the probe budget the run itself
  produced. Every value is read off the run and none is typed beside it. The page's body is
  unchanged — it is still the `table7` dossier — and the section is still an `extra_section_html`
  the example page opts into rather than anything the CLI writes, for the reason it always was: it
  is about another system's decision. It now says so on the page, so the violated verdict is not
  read as belonging to the dossier's own system.

### Added

- **The README's social card is pinned to the card the website serves**
  ([#76](https://github.com/eduardstan/reasonsmith/pull/76)). `docs/assets/og.png` still carried
  the retired `eduardstan.github.io/reasonsmith` URL in its footer while the byte-identical file
  served live as the site's OpenGraph and Twitter card had been rebuilt with `reasonsmith.dev`;
  nothing checked that the two copies agree. The corrected image is copied across from
  `eduardstan/reasonsmith-site`, and `tests/test_social_card.py` pins its SHA-256 — the site
  repository is not available in CI, so the digest is the checkable side of the pair, and the
  failure message states the procedure: regenerate the card from `brand/og.html` in the site
  repository first, copy the result here, update the digest.

- **An engine and a pack can be installed rather than vendored**
  ([#74](https://github.com/eduardstan/reasonsmith/pull/74)). Engines and packs are discovered
  through `importlib.metadata.entry_points` — groups `reasonsmith.engines` and `reasonsmith.packs` —
  so a third party ships one as its own pip package and never touches this repository. The answer to
  *can reasonsmith use Prolog, ASP, or a different solver?* is now **yes, as a package you install**,
  not *send us a pull request*. `report._engine_ladder` merges discovered engines beside the four
  built-ins, and `spec.load_pack` resolves an installed pack through the existing lookup, so an
  externally provided pack is refused by exactly the checks an in-tree one is. The property language
  is untouched; only the set of engines that may discharge a duty is open. The substance is the
  discipline, because **reasonsmith does not audit a plug-in**: a plug-in declares its ceiling in
  `max_strength` and cannot report above it, refused in `RequirementResult.__post_init__` beside the
  probe-budget invariant so an overclaiming result cannot be constructed at all; a plug-in that
  raises, exhausts its own time bound, returns the wrong type or cannot be imported reports *not
  evaluated*, never satisfied and never violated, because a false violation from an unaudited
  package is as bad as a false pass; a plug-in taking a built-in's name is refused rather than
  namespaced, since a decorated name would leave the shadowing engine answering the same duty; and
  every plug-in result names its plug-in in `details` and in the evidence summary, failures
  included. There is no wall clock — killing a running call needs a subprocess and a serialisation
  contract, which is the plug-in framework this deliberately is not — so a plug-in bounds its own
  search, and the limit is stated in the new
  [`docs/authoring-engines.md`](docs/authoring-engines.md) rather than implied. With nothing
  installed, both groups are empty and the ladder is the built-in ladder, pinned by
  `test_with_no_plugin_installed_the_ladder_is_the_builtin_ladder`; `docs/semantics.md` §3.5 carries
  the four claims and names the test that falsifies each.
- **A language model as a system under test: `docs/adapters/language_model_notices.py` and
  `docs/language-model.md`.** A fourth runnable system beside the three of `docs/three-systems.md`,
  and deliberately not a fourth rung: a model you can call sits at `probed`, exactly where the
  probabilistic scorer sits. What it demonstrates is the axis underneath — which duties can be
  answered about a system at all. Run against the whole `ecoa` pack it comes back `observed` on the
  notice's timing and contents, `probed` on 12 CFR 1002.9(b)(2)'s specific-reasons duty carrying
  its search budget, and `unattainable` on the other half of that same clause, naming
  `artifact_logs_deleted_reason_count` as the signal it lacks — reason fidelity is measured from an
  inference artefact and a decoder has none to give. The adapter takes one
  `complete(prompt: str) -> str` and nothing else: no vendor SDK, no client wrapper, no network,
  and a deterministic stub so the committed transcript is reproducible from a fresh clone.
  `tests/test_docs_language_model.py` holds the transcript byte-for-byte and asserts the ceiling on
  the mechanism rather than on the printed word — `logic()` is `None`, so `proved` is structurally
  unreachable, and the adequacy duty is never answered by the presence check that shares its clause.
  ([#73](https://github.com/eduardstan/reasonsmith/pull/73))
- **One run, five artefacts: `reasonsmith check --audience {developer,deployer,auditor,regulator,affected-individual}`.**
  A conformance report had exactly one shape and every reader got it, but the questions differ — a
  regulator asks how far the claim reaches, a person refused credit asks what this does not tell
  them, a developer asks which signal is missing. The flag is a **projection over data the run
  already produced** and computes nothing per reader: an `AudienceProjection` in
  `src/reasonsmith/render.py` selects which parts of the one `ConformanceReport` each rendering
  draws. Three properties are pinned in `tests/test_audience_view.py` because the feature is
  unsafe without them — no audience sees a verdict another audience does not, no audience loses
  the limits or the duties-not-checked notice, and the affected-individual artefact carries no
  system internals (asserted as an *exclusion* over the run's own signal names, summaries, probe
  budgets and counterexample values, so a later leak fails rather than passes). A fourth test
  asserts two audiences differ by emitted content and not by framing, over the body with every
  heading excluded, so an implementation rendering one report under five titles fails. Omitting
  the flag renders the full report byte-for-byte as before — verified over 24 renderings, three
  adapters × four packs × two domain settings, in both text and HTML — which is also the auditor
  projection, by object identity. `--json` is deliberately unprojected: it stays the complete
  machine record, and a display flag must not quietly drop fields from a pipeline's input. The
  table of what each audience is shown, and the reasoning for every row, is authored rather than
  derived and is written down in `docs/semantics.md` §7, along with two limits — this artefact
  carries no reasons for the decision itself, and `--audience` is presentation, not redaction.
  ([#72](https://github.com/eduardstan/reasonsmith/pull/72))
- **One differential test holds the two implementations of the property language to one semantics.**
  `rulelang.eval_expression` and the Z3 encoding in `engines/proved.py` are two implementations of
  one language — `rulelang`'s docstring says so, and says why a gap between them is the worst defect
  available here: counterexample verification runs the interpreter against the solver's model, so a
  construct one side models and the other drops makes verification agree with itself about the wrong
  program. They were kept in step by hand and checked only by chosen examples.
  `tests/test_semantics_agreement.py` generates specs from the accepted grammar with Hypothesis and
  asserts both halves of the invariant — the same answer on the same assignment, and the same
  accepted set, so a spec `parse_property` accepts may only make the encoder raise its own
  deliberate `UnsupportedConstructError`. It drives the engine's own `_Scope`/`_encode_block`/
  `_ast_to_z3` over a synthetic rule block rather than a second harness, because `present()` and
  `contains()` both refuse a free input and so need an assignment to be reachable at all. A second
  test compares arithmetic on the value rather than the property: a connective above a diverging
  term hides it, and a deliberate break of `_python_mod` was invisible at 2000 property-level
  examples and caught at 200 value-level ones. The temporal fragment, division and float values
  whose rational and binary forms differ are out of scope and named in the test.
  ([#69](https://github.com/eduardstan/reasonsmith/pull/69))

### Changed

- **CI enforces the coverage floor it already measured.** Both `ci.yml` and `publish.yml` ran
  `pytest --cov=reasonsmith --cov-report=term-missing` and threw the number away: a silently
  falling total went unnoticed. The same command now carries `--cov-fail-under=93`, the suite's
  measured total, commented as a floor to be raised deliberately, never lowered.
  ([#71](https://github.com/eduardstan/reasonsmith/pull/71))

- **The rendering is out of `report.py`.** `ConformanceReport.render_html` was a ~1000-line method
  and its sibling `render_text`, together half the file, and two upcoming packages both edit that
  region. Their bodies move verbatim into the new `src/reasonsmith/render.py` as module-level
  `render_text(report)` / `render_html(report, ...)`, with the rendering-only helpers
  (`_budget_line`, `_source_checkout`, the presentation constants); the methods stay as thin
  delegates, so the public API and every byte of output are unchanged — 457 tests pass, and
  `docs/report.html`, the nesyarena report and the README transcripts all regenerate
  byte-identical.
  ([#70](https://github.com/eduardstan/reasonsmith/pull/70))

- **The front page carries both axes.** The three-rung table answers *how far a claim reaches* —
  one duty, three systems — and it never showed the other question a report answers: *what the
  property actually says*. Beside it now sits the run that separates the two halves of 12 CFR
  1002.9(b)(2) on one system: `ecoa_reg_b_1002_9_b_2_specific_reasons` **satisfied** on the form of
  the notice, `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` **violated** on its content, both
  on the demonstration's decision `APP-1042`. The section's transcript is CLI stdout regenerated by
  `python docs/build_readme_transcripts.py`, which now declares that command alongside the sample-log
  one; the hand-pasted evidence-record excerpt it replaces is unchanged in
  [docs/example-output.md](docs/example-output.md), where a builder test pins it byte-for-byte.
  ([#68](https://github.com/eduardstan/reasonsmith/pull/68))

### Fixed

- **The stale `docs/index.html` reference is corrected.** `AGENTS.md` (and `CLAUDE.md`, its
  symlink) said touching the renderer means regenerating `docs/index.html`; the generated dossier
  has been `docs/report.html` since the website moved to its own repository. The same stale
  reference in the `docs/build_nesyarena_report.py` docstring is corrected too. The
  `test_docs_index_html_matches_the_renderer` test name and the historical record in
  `docs/findings-nesyarena.md` are deliberately left as they are.
  ([#71](https://github.com/eduardstan/reasonsmith/pull/71))

- **The version guard reaches the fourth place it lives.** `CITATION.cff` carried `0.3.0` against a
  0.4.0 package: it was already stale when `tests/test_release_discipline.py` locked
  `pyproject.toml`, the topmost released `CHANGELOG.md` heading and `__version__` to one another,
  so the guard was written around the one file that had drifted. `CITATION.cff` is now `0.4.0` and
  `test_pyproject_changelog_and_package_version_agree` reads it too — by a regex anchored at column
  zero over its one top-level `version:` line, so one field costs no YAML dependency.
  `CONTRIBUTING.md`, *Versioning and Releases*, lists all four places as the release procedure.
  ([#67](https://github.com/eduardstan/reasonsmith/pull/67))

## [0.4.0] - 2026-08-02

### Added

- **The reason-deletion certificate is an engine.** `certificate.py` could measure which reasons an
  engine's answer stopped depending on, and it was reachable from no duty and no CLI verb — its
  only caller was the demonstration. The two halves of the package met in exactly one place, on
  decision `APP-1042`, and there they disagreed: the Table 7 evidence record reports COMPLETE while
  the certificate reports FAIL, so `reasonsmith check` reported the reason-giving duty *satisfied*
  on a decision this package proves has four of five legally owed reasons missing. Three pieces
  close it, and nothing else changes: one optional SUT method, `artifact(decision)`, returning the
  *inputs* to `certificate.certify` for the inference a decision came from (never a verdict — a
  self-declared completeness flag is what this refuses); one engine,
  `engines/certificate.py`, at strength `probed`, carrying the probes it ran as its budget; and one
  duty, `ecoa_reg_b_1002_9_b_2_principal_reasons_complete`, on the half of 12 CFR 1002.9(b)(2) that
  asks for the principal reason**s**. `reasonsmith check --system-module
  reasonsmith.demo:deployed_credit_system --pack ecoa` now reports that decision violated and exits
  2. See [docs/semantics.md](docs/semantics.md) §3, *certificate*.

  **What this means for an existing run:** the new duty is domain-limited to `consumer-credit` like
  the rest of the ECOA pack, and it gates on `artifact_logs_deleted_reason_count` — a signal
  reasonsmith *measures* rather than reads. A system that exposes no inference artefact is reported
  `unattainable` on it, which is not a breach and does not change an exit code. It is never
  silently downgraded to the presence check on the reason field: that substitution answers a
  different question under the same duty's name, so the duty is given an engine ladder of exactly
  one rung.
- `contains(signal, "phrase")`, a property-language atom that reads *what a statement says* rather
  than whether a field is blank. Its first argument is a signal name and its second a string
  literal, so the wording a duty forbids is fixed by the pack and never supplied by the system
  being audited. Comparison folds ASCII case and nothing else, and a non-ASCII phrase is refused at
  load time — the fold has to stay reproducible character-for-character by the Z3 encoding, so a
  fold that is not one-to-one would let the solver and the interpreter disagree about the same
  string. It is a substring test and claims to be nothing more: it does not model *specific*. See
  [docs/semantics.md](docs/semantics.md) §2 and [docs/authoring-packs.md](docs/authoring-packs.md),
  *a phrase in a `spec` is the clause's own words*.
  ([#64](https://github.com/eduardstan/reasonsmith/pull/64))

### Changed

- **A `logical` duty is now answered from a decision trace.** A `logical` property is a property of
  one decision record, so a trace of them is evidence about it; the build used to report *not
  evaluated* while that evidence sat in front of it, which was the fragment's label deciding what
  could be checked. `docs/semantics.md` §3.5 already stated the principle in its first bullet and
  contradicted it two bullets later. A presence conjunction still keeps the record engine and its
  per-signal, per-record diagnostics; every other state formula is monitored per record. The
  separate rule that a temporal duty never rises above `observed` is unchanged.

  **What this means for an existing run:** a `logical` duty against a system that exposes only a
  decision log used to be reported *not evaluated* and could now be reported `violated`, so a run
  that exited 0 can exit 2 on evidence it always had. Two shapes still cannot be monitored and stay
  not evaluated: a comparison against a Boolean constant, and an implication written
  `Implies(a, b)` rather than `(a) -> (b)` — the monitor renders the `spec` as the pack wrote it.
  ([#64](https://github.com/eduardstan/reasonsmith/pull/64))
- **12 CFR 1002.9(b)(2) checks the clause's own negative constraint, and carries its trigger.** The
  duty was a conjunction of `present()` atoms, so a reason of `"n/a"` satisfied it. It now also
  checks that the statement is not one of the two the clause itself calls insufficient, which makes
  it falsifiable against a plain decision log with no oracle. Its fragment moved from `record` to
  `logical`, so a log holding a single decision is now reported not evaluated on it rather than
  satisfied.

  The property is guarded by the trigger the clause states in its own first words — it governs the
  statement *required by paragraph (a)(2)(i)* — so a creditor that lawfully took the (a)(2)(ii)
  disclosure branch is **no longer reported violated**. The cost is stated rather than hidden:
  where a log carries no statement of reasons at all, the duty is `satisfied` vacuously and no
  report outcome distinguishes that from a trace that was checked and met
  ([docs/semantics.md](docs/semantics.md) §4).
  ([#64](https://github.com/eduardstan/reasonsmith/pull/64))

### Fixed

- The Z3 encoding of `present()`'s blankness rule now also governs `contains()`, so the solver and
  the reference interpreter agree that a value the record does not carry carries no phrase.
  ([#64](https://github.com/eduardstan/reasonsmith/pull/64))

## [0.3.0]

0.3.0 was numbered in the source tree but never published to PyPI, so its changes reach users in
0.4.0.

### Added

- A second applicability gate, `domains`, beside the existing regulatory-class `scope` gate. It
  records the *kind of decision* a duty is about, from `reasonsmith.spec.DECISION_DOMAINS`, and is
  matched by intersection against what a system declares. See
  [docs/authoring-packs.md](docs/authoring-packs.md) for the vocabulary rules and
  [docs/semantics.md](docs/semantics.md) §4 for what a not-applicable verdict on it does and does
  not say. ([#63](https://github.com/eduardstan/reasonsmith/pull/63))
- A report whose duties were skipped for a missing declaration says so: `render_text`,
  `render_html` and the CLI's stderr all carry a line naming how many duties were reported not
  applicable solely because the system declared no decision domain, and what to pass to check
  them. Exit codes are unchanged. ([#63](https://github.com/eduardstan/reasonsmith/pull/63))

### Changed — breaking

- **A requirement block without `domains` no longer loads.** Loading a pack that has one fails with
  `missing required field(s): domains`. Every externally authored pack must add `domains = [...]`
  naming the kinds of decision the duty is about, or `domains = []` for a duty that is about no
  particular kind of decision. There is deliberately no default: a wildcard reachable by
  forgetting the field would defeat the gate, so the omission is refused the way a missing
  `binding` or `scope` already is. ([#63](https://github.com/eduardstan/reasonsmith/pull/63))
- **An invocation that declares no decision domain now reports domain-limited duties
  `not_applicable` rather than checking them.** Declare what the system decides with
  `--system-domain <domain>` (repeatable), or set `system_domains` on an adapter. All three
  requirements of the shipped ECOA pack and two rows of the Table 7 pack are domain-limited today,
  so an existing ECOA run without the flag now checks nothing and reports every duty not
  applicable. `reasonsmith` never infers a system's decision domain.
  ([#63](https://github.com/eduardstan/reasonsmith/pull/63))
