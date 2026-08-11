# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This file starts at 0.3.0:
releases before it predate the file and are not reconstructed here.

## [Unreleased]

### Added

- **The JSON envelope carries the undeclared-domain notice.** `ConformanceReport.to_dict()` now
  emits `undeclared_domain_notice` beside the existing top-level keys, preserving the distinction
  between a duty's answer and a missing decision-domain declaration. The value is the same notice
  shown in human renderings, or `null` when no duty was skipped, so consumers have a defined value
  in both cases. `JSON_SCHEMA_VERSION` remains **2** because this is an additive key under the
  envelope's compatibility convention, not a removal, rename or change of meaning or type; no
  audience projection suppresses it because the JSON record is complete machine output rather than
  an audience-filtered finding set.

- **When the counterfactual duty's two rungs disagree, the report names the cause rather than the symptom.**
  The `proved` and `probed` rungs of `counterfactually_invariant(o, p)` do not range over the same object: the first asks whether the *declared rules* treat alike every pair the *declared constraints* admit, the second whether the *implementation* treated alike the pairs built from the decisions the system logged. So their disagreement is evidence in its own right, and [`docs/formal.md`](docs/formal.md) §6.6 now states the relation — `R ⊆ P` and `decide_S` agreeing with the declared logic on the declared space together make `probed = violated` imply `proved = violated` — with the contrapositive that is the whole feature: `proved = satisfied` beside `probed = violated` eliminates one of those two hypotheses. The lower rung is therefore run whenever the higher one reached a verdict, and a disagreement is reported as the **disjunct it eliminates** under `engines.counterfactual.RUNG_DISAGREEMENT_KEY`. `proved = violated` with `probed = satisfied` is the relation holding rather than a defect, and what it names is the log: it does not exercise what the rules permit. The other direction discharges the cheap hypothesis first, by evaluating the declared constraints on the replayed pair — a pair the declared input space does not admit is named as such and the declaration is not impeached, and only a pair *inside* that space leaves the residual finding, that the system's `decide()` does not implement the `logic()` it declared. A record that leaves a declared constraint unsettled eliminates neither and says so. Nothing here moves a verdict, a strength or a witness; no shipped system reaches either rung on the one shipped counterfactual duty, so no shipped verdict moved. `tests/test_counterfactual_invariance.py` carries a witness per direction, including the second one the item allowed might be unreachable — it is reachable, and the fixture is a rule set whose `decide()` deliberately departs from what it declares. No new shipped example system, and no shipped record holding a protected attribute about a natural person.

- **The proposition the finite-trace decision procedure rests on is in the mathematics document, with its proof.**
  0.8.0 re-encoded `ltlf.accepts(φ, σ)` as satisfiability over the characteristic formula `pin(σ)`, and the soundness of that move — `L(pin(σ)) = {σ}`, without which the solver is answering about a set of traces while the tool reports an answer about the one it was given — was stated only in `src/reasonsmith/ltlf.py`'s own docstring. [`docs/formal.md`](docs/formal.md) §6.11 now states and proves it in the document's notation, with the two corollaries the production surface uses, and records three things the proposition depends on that were previously implicit: why the completeness of each `λᵢ` over `AP` is load-bearing, that the non-emptiness the proof assumes comes from BLACK's own finite-trace semantics rather than from the `NON_EMPTY` guard 0.8.0 deleted (and the one reachable shape — an atom-free formula — where it bites), and that `ATOM_BUDGET` counts *distinct* atoms, which `pin(σ)` adds none of, so the encoding's growth with the trace length is in literal occurrences and not in the count the budget refuses on. `[@biere-1999]` and `[@geatti-2021]` join the bibliography as the bounded-model-checking move and the finite-trace interpretation the section relies on. `test_pin_characteristic_formula_accepts_sigma_and_rejects_neighbors` now asks the solver about **every** trace one Hamming step from σ rather than two of the four, and no verdict, engine or rung moved.

- **`reasonsmith explain <requirement-id>` shows how a clause of law became a formula.**
  Every requirement already carried its clause, its formula, its rationale and the signals it needs as fields of the pack, and none of it reached a reader through the tool: `validate-pack` prints one index line per requirement, so someone asking how a clause became a property had to open the pack TOML, [`docs/refinement.md`](docs/refinement.md) and [`docs/language.md`](docs/language.md) and hold three files in their head. The command prints those fields under `CLAUSE`, `FORMULA`, `RATIONALE`, `FRAGMENT` and `REQUIRES`, and adds `REFINEMENT` — the fourth column of the refinement record, what the formalisation deliberately did not capture. It runs no engine and reads no system, so it changes no verdict. The id resolves against every built-in pack, or against the packs `--pack` names, a TOML path included; an id nothing ships is a usage error naming the packs searched, never an empty frame. `docs/` is not in the wheel, so an absent refinement record is *named* and pointed at the repository rather than silently dropped. No rung ceiling is printed: which rung a duty reaches is decided at run time by whichever engine serves it, not by its fragment, and a table of fragment-to-rung here would be a hand-maintained claim nothing holds to the dispatch. `tests/test_explain_command.py` explains every shipped requirement and holds both halves of the refinement section; `tests/test_docs_refinement.py` now reads the record through the same parser the command uses, rather than keeping a second copy.

- **[`docs/adopting.md`](docs/adopting.md): the document for a reader who arrives with a system of their own.**
  There was an authoring guide for someone writing duties and one for someone writing an engine, and none for the adopter, whose question is "here is my system — what can you tell me about it?". [`docs/three-systems.md`](docs/three-systems.md) walks three systems, but they are *shipped example* systems and it demonstrates the evidence ladder rather than being an on-ramp. The new page arranges what the repository already documents for that reader: the four surfaces a system can come in through and the honest ceiling of each, the pairing of `reasonsmith explain` (which duty needs which signals, and what its formalisation left out) with `report.analyze_unattainable` (what happens when the system does not emit them), and a worked run on a log a notice service could plausibly export — four duties reported unattainable and one not evaluated, before one added field turns an unanswerable duty into a reported violation and the exit code from 0 to 2. It states the limit first rather than last: every verdict rests on declarations nothing here checks, measured by finding 1 of [`docs/findings-nesyarena.md`](docs/findings-nesyarena.md) and open as objective 5 of [`ROADMAP.md`](ROADMAP.md). It cites [`docs/semantics.md`](docs/semantics.md) §4 for the four outcomes rather than keeping a second copy of that table. `tests/test_docs_adopting.py` re-runs every command on the page and compares stdout byte-for-byte, and holds §2's set-difference claim to `analyze_unattainable` itself, including that it answers without executing the system.

### Fixed

- **The coverage gate no longer trips Hypothesis's per-example deadline under instrumentation on a busy machine.**
  Two property tests ran with Hypothesis's stock 200&nbsp;ms deadline: `test_strict_comparison_boundary.py`'s random-trace differential against rtamt and `test_language_definition.py`'s grammar-acceptance sweep. Each example sits an order of magnitude under the default when the machine is idle, but coverage's tracer roughly triples it and contention on a shared machine multiplies that again, so an example sporadically exceeded the deadline; Hypothesis then aborts the whole property, its lines go uncovered, and the total falls below the 92.5 floor even though CI — always idle — passes. Both tests now carry the same per-example `deadline=timedelta(seconds=30)` the Z3-backed agreement tests in `test_semantics_agreement.py` already had, which keeps a per-example bound in force while giving the probe and the load the headroom they need. No engine, verdict, pack or rung moved; the 92.59% total across the full suite is byte-identical before and after.

## [0.8.0] - 2026-08-07

### Changed

- **Replaced `flloat` with BLACK solver behind a subprocess boundary in `src/reasonsmith/ltlf.py`.**
  The finite-trace decision procedure for temporal formulas now invokes `BLACK` (`https://www.black-sat.org`, MIT licensed) via a subprocess call rather than depending on `flloat` (LGPLv3+). `accepts(φ, σ)` is re-encoded as satisfiability over `pin(σ)`, standard LTLf non-empty trace semantics are used natively, and `ATOM_BUDGET` is raised to 100 as an explicitly unmeasured bound, on the change of encoding — `pin(σ)` grows linearly in `n*|AP|` where flloat built a powerset automaton — and not on a benchmark.

### Fixed

- **Kleene operators read a truth value rather than an identity.**
  `rulelang`'s Kleene operators compared operands with `is True` / `is False`, so an atom returning a falsy or truthy non-`bool` — `0`, `1`, `""`, whatever the decision record carried — matched neither branch and fell through to the operator's unit, producing a genuine `True` off a falsy conjunct and a genuine `False` off a truthy disjunct at the `probed` and `certificate` rungs, which guard no atom. Every operand is now read through `rulelang.kleene_value`, and `eval_temporal_trace` normalises each position of the trace the same way, so an identity test against a trace value at a call site is sound. `tests/test_kleene_three_valued.py` checks the tables cell by cell.

- **A misbehaving solver is refused on its question instead of crashing the analysis.**
  `ltlf._run_black` raised a bare `RuntimeError` — which nothing catches — for a binary that passes identification and then prints both `SAT` and `UNSAT`, prints nothing, exits nonzero or dies on a signal. The module's docstring described each of these as a refusal; in practice `validate-pack --analyse` exited 1 with a traceback and took down the whole analysis, including the Z3 half that never touched the solver. They now raise `UnsupportedConstructError`, the class the timeout and the atom budget already raise and the one every call site in `analysis.py` turns into a named entry in `PackAnalysis.skipped`.

- **§1.7's exhaustiveness claim is narrowed to the scope its pin has.**
  [`docs/language.md`](docs/language.md) §1.7 said one refusal in `rulelang` has no row and cannot have one. At least five have none, and three of them are not defensive branches: `classify_fragment` accepts the specification and assigns it a fragment, and the refusal fires later, at evaluation, for `counterfactually_invariant()`, `undetermined()` and `degree()`. The claim now states what the pin actually holds — the refusals reachable from `classify_fragment`, which is the entry point every witness runs through — names the three evaluation-time refusals as outside the table's scope, and points at `docs/semantics.md` §3 and §9 where each is documented. No row was added for them: a witness for one would have to run through an engine, so a row would be a rule the pin cannot check, which is the hollow-pin failure this release already had to repair once.

- **§4's `not evaluated` row covers the case an engine uses it for.**
  [`docs/semantics.md`](docs/semantics.md) §4 defined `not evaluated` as evidence of the wrong quality — an empty trace, an unparseable formula, a solver timeout — and told a reader to fix the evidence and re-run. That is the wrong instruction for `engines/counterfactual.py`'s log-only case, where the evidence is of the wrong *kind*: no trace, however long, establishes what a system would have decided, so no better log will ever settle the duty. The row now names both cases and gives the instruction that applies to each.

- **The certificate rung counts a trigger by its truth value rather than by identity.**
  `engines/certificate.py` tested an implication's antecedent with `eval_expression(...) is True`, which reads the record's raw value as an object: a trigger signal logged as `1`, `"yes"`, `1.0` or a numpy bool — the ordinary shape of a JSONL log, a pandas column or a SQL `TINYINT` — matched nothing and was counted as never fired. The duty was then reported as an unreachable trigger and left the audit entirely, neither satisfied nor violated, on a trace whose every record made the antecedent true and against which the same engine had evaluated the same implication with the antecedent true one line above. The value is now read through `rulelang.kleene_value` before it is tested, which is the reading every operator in the language already uses. `tests/test_trigger_counting_is_differential.py` drives one trace twice, once with a `bool` trigger and once with an `int`, and requires every rung that counts a trigger to count the same triggers.

- **A trailing comma no longer refuses a specification for text it did not drop.**
  `rulelang._normalize_tokens_for_read_whole` counted a call's trailing comma, which `ast.unparse` normalises away exactly as it normalises the redundant parentheses the check already exempted. An idiomatic multi-line `implies(\n  a,\n  b,\n)` therefore failed the token-count comparison in `verify_parsed_whole` and was refused as "dropping text from the input" when nothing had been dropped — and because the refusal is raised out of `load_pack`, the whole pack failed to load and every duty in it left the audit at once. The comma is now skipped beside the parens, on the same ground. The check still fires for the two shapes that do drop text, a `#` comment and implicit string concatenation.

- **`present()` no longer reports the unknown sentinel as a value.**
  `rulelang.is_present` had no case for `UNKNOWN` and fell through to `True`, so `present(x)` answered true for a value whose whole meaning is *no value was determined* while a bare `x` in the same language answered unknown — the two atoms disagreeing about the same object. `RulesAdapter` writes whatever the interpreter returned straight into the decision record, so a rule whose inputs were not all supplied puts the sentinel into the log an auditor is handed, and a `record` duty over that log came back `satisfied` at strength `observed` with the summary "every required signal carries a value in every record". `is_present` now answers `False` for the sentinel.

- **A tokenizer failure no longer reports a specification read whole.**
  `rulelang._normalize_tokens_for_read_whole` swallowed every exception and returned the partial token list collected so far, so a failure part-way through the input made the token-count comparison in `verify_parsed_whole` pass — the failure direction that check exists to close. It now raises `UnsupportedConstructError`.

- **Specification read-whole verification across all engines.**
  `rulelang.parse_expression` now verifies that Python's parser read the whole specification text (`verify_parsed_whole`) without silently dropping comments (`# ...`) or unparsed tokens (such as implicit string literal concatenation `a and "b" "c"`). A specification that is not read whole is refused when the pack is loaded — `spec._check_spec` turns the `UnsupportedConstructError` into a `ValueError` naming the requirement — so the pack does not load and no engine runs on it at all, which is how an incomplete formula is kept from being answered.

- **Temporal verdict derived from Boolean semantics.**
  The temporal engine (`engines/observed.py`) now derives requirement verdicts from the Boolean semantics over finite traces (`rulelang.eval_temporal_trace`) rather than from quantitative robustness sign alone. Robustness remains reported as the quantitative margin in `evaluation_scores`. This resolves strict comparison boundary issues at robustness zero (e.g. `always(b > 0)` at `b = 0.0` now evaluates to `VIOLATED` rather than `SATISFIED`).

- **Unreachable trigger vacuity guard uses Kleene 3-valued Boolean semantics.**
  The temporal engine (`engines/observed.py`) now evaluates implication antecedents under Kleene 3-valued logic over the trace (`rulelang.eval_temporal_trace`) rather than using quantitative robustness comparisons (`rob < 0`). An antecedent that is false at every position is reported as an unreachable trigger (`verdict=INCONCLUSIVE`), an antecedent that is unknown anywhere and never true is reported as not evaluated (`verdict=INCONCLUSIVE`), and negative zero robustness (`-0.0`) can no longer bypass the guard.

- **Silent wrong answers closed in the temporal backend.**
  A temporal formula that the backend parser did not read whole (due to dropped lexer tokens like `%` or multi-statement inputs like `'a b > 1'`) is now reported `not evaluated` (`verdict=INCONCLUSIVE`) rather than answered from an incomplete parse. Implemented via a strict lexer subclass (`F1`) that attaches rtamt's raising error listener to the lexer and a postcondition assertion (`F2`) that the backend parser produced exactly one statement. Every formula in every shipped pack was swept and verified to parse to rendering exactly one statement.

### Added

- **The mathematics is stated once, and the repository has a bibliography that the build enforces.**
  [`docs/formal.md`](docs/formal.md) gathers what was scattered across four documents and a dozen
  module docstrings into one notation: the objects, the denotation `⟦·⟧_{M,A}`, the sufficient-reason
  definitions and the deletion certificate, the strength chain beside the evidence basis, the
  residuated lattices and the three t-norms, and one soundness statement per engine. It introduces no
  construct, engine, rung, basis or verdict, and every claim in it names the test that falsifies it.
  It also carries the repository's first **bibliography** — 26 entries, every one of them a work the
  tree already relied on, the densest concentration of which was inside `src/reasonsmith/verdict.py`
  where nobody looking for references would find them. The bibliography is a **registry**, not a
  list: a citation is a backticked pandoc key (`` `[@hajek-1998]` ``), and
  `tests/test_docs_formal.py` fails the build when a key resolves to no entry, when an entry is
  cited by no claim, or when a paragraph anywhere in `docs/` or `src/reasonsmith/` names a
  publication venue and carries no key. Every existing citation site was keyed in the same change,
  and `docs/sufficient-reasons.md` §9 — the one reference list the repository had — now points at
  the registry instead of carrying its own. The anti-drift mechanism for the definitions is the
  same one the other documents already use and is why a fourth document is safe: every definition
  the code also defines is generated from the code in each document that states it, so
  `formal.md`, `semantics.md` and `language.md` cannot disagree with each other about the chain
  (`Strength`), the rung table (`BASIS_RUNGS`), the fragments (`rulelang.FRAGMENTS`) or the algebras
  (`manyvalued.ALGEBRAS`). No verdict, engine, duty, pack or parser changed.

- **The `--json` envelope declares the projection it was asked for, and never applies one.**
  `--audience <reader> --json` still emits the complete machine record with every field — a
  display flag hides nothing from a consumer — but the envelope now carries a top-level
  `audience` block naming the requested audience and every flag of its resolved
  `AudienceProjection`, exactly the way the text renderer already names a projection with
  `audience=None`. `--audience` omitted emits `name: null` with the full projection; an unknown
  name fails through the renderer's own `_projection` refusal, not a new error path. The flags
  are derived from `dataclasses.fields(AudienceProjection)` — one field per dataclass field,
  never a hand-listed second copy of the authored `AUDIENCES` table that would drift when a flag
  is added. `results` stay byte-identical across every audience (the property that makes the
  declaration safe), it is additive only, so `JSON_SCHEMA_VERSION` stays at 2 unchanged (the
  decision was made in `tests/test_json_schema_version.py` rather than skipped, and
  `tests/test_json_audience.py` pins the block field-by-field against the dataclass rather than
  against literals). Nothing is filtered from the JSON for any audience; no verdict, rung,
  basis, engine, duty, pack or parser behaviour changes; no byte-pinned document moved — none
  of them embeds the `audience` block.

- **The `--json` machine record is complete: every result carries its `verbatim_text` and the
  deletion certificate's reason identities.** Two keys added, purely additive, so
  `JSON_SCHEMA_VERSION` stays at 2 unchanged (addition is not a shape change; the decision was
  made in `tests/test_json_schema_version.py` rather than skipped). `verbatim_text` is the
  statutory quotation the duty restates, carried through from the pack **unchanged** — never
  reflowed, truncated or whitespace-normalised — so a detail pane that names
  `12 CFR 1002.9(b)(2)` can show its words. `details.certificate` carries, for each decision the
  deletion probe certified, the full per-reason verdict: `status` verbatim (`live`, `deleted`,
  `unseparable`, `inconclusive`, `undetermined`) beside each reason's `score`, `exact_drop`,
  `engine_drop` and `detail`, so the difference between *deleted* and *we could not separate this
  one* — a finding and a guess — cannot be collapsed by a rendering. The project's headline
  finding — one stated reason, five found, four deleted — could previously be read only from a
  rendering; it is now in the machine record. It is present only where a certificate exists and
  absent otherwise. (The evidence `basis` coordinate was already part of the record, shipped in
  [#123](https://github.com/eduardstan/reasonsmith/pull/123); this change only pins it in a test.)
  Nothing is removed, renamed or retyped; nothing
  besides these two keys is added; no verdict, rung, basis or engine moved, and
  `details.certificate` is a list — a certificate exists per certified decision, and a single
  record would present one decision's measurement as the whole. No shipped verdict moved and no
  byte-pinned document changed: none of them embeds the `--json` result record.
- **The strength lattice gains a rung, and the inference-artefact protocol gains a second family.**
  `Strength.RECOUNTED` sits between `observed` and `probed` and is the rung a reason-adequacy verdict
  reaches when the reason set the deletion probe ran over is one the *system recounted about its own
  inference*, rather than one enumerated from a model encoding. That is the **faithfulness** question
  as the literature poses it (Jacovi & Goldberg, ACL 2020), measured the way that literature measures
  it — by erasure (DeYoung et al., *ERASER*, ACL 2020) — on evidence a self-report demonstrably fails
  to be (Turpin, Michael, Perez & Bowman, NeurIPS 2023). It is a rung on the `artifact` row and not a
  fifth basis, by the test [`docs/semantics.md`](docs/semantics.md) §10 now states: evidence about a
  different object is a basis, evidence about the same object less deeply is a rung. The rule that
  gated the widening — a certificate over a reason trace claims strictly less than one over a ground
  program and must not report at the same strength — was previously prose in §3 and is now a refusal
  `RequirementResult.__post_init__` fires. A family declares `reasons_are_exact` and **silence claims
  the weaker rung**, the opposite default from `monotone` and for a stated reason.
  `artifacts/reason_trace.py` is the second family: the reasons a system recounts for one decision,
  each tested by suppressing its facts and re-running the system. It widens what can be certified from
  systems that expose a ground program to systems that recount their reasons and can be re-run with a
  fact withheld — it does **not** reach a system that is only a log, so the README's auditors blocker
  is narrowed and not closed. No shipped example system uses the new family, and **no shipped verdict
  moved**; the generated documents change by one sentence, the one that words the `artifact` basis.

- **The property language has a formal semantics, and it is a checked one.**
  `validate-pack --analyse` asks whether a requirement set is jointly satisfiable, whether one duty
  subsumes another, and whether a subformula is replaceable without changing a verdict — relations
  between formulas of a language, meaningful only once the language is defined. It existed as a
  whitelist in `rulelang.py` and four separate translations out of it.
  [`docs/language.md`](docs/language.md) defines it: an EBNF grammar checked against the parser
  rather than written beside it, and the denotation the captain's decision record settled —
  `⟦·⟧_{M,A} : Spec → (𝒫(Trace_M) ⇀ A)`, parameterised by the structure `M` (a finite trace, or an
  input space) and the algebra `A` (`𝔹` as a degenerate instance of a residuated lattice, not a
  separate system), over sets of traces uniformly so that the counterfactual atom is typed as the
  2-safety property it is. The four encodings — the `rulelang` interpreter, the Z3 encoding, the
  rtamt rendering and the LTLf mapping — are recast as implementations of that one denotation, with
  the differential tests that already existed named as their conformance evidence. Three things the
  code does that read as policy are now consequences of the definition: a `degree()` atom under a
  temporal operator is refused because there is no many-valued reading of a temporal operator; an
  empty trace has no value because the tool refuses the lattice top the mathematics would give it;
  and unawareness is `unattainable` rather than `satisfied` because the relational atom quantifies
  over pairs of admissible inputs and an unaware system admits none. `tests/test_language_definition.py`
  generates from the grammar, refuses every refusal the document names by id, and holds the
  document's claim-to-test map to the suite. **Nothing in the language changed and no shipped
  verdict moved.**

- **Reported: four shapes on which the trace-rung implementation and the definition disagree.**
  Writing the denotation down found three, beside one already documented, all at `observed` and all
  **latent** — no shipped pack writes any of them, and a test now keeps that true. rtamt's lexer has
  no `%` and ANTLR error-recovers by dropping the token without raising, so the monitor answers
  about a formula nobody wrote; rtamt left-associates a chained comparison over robustness values,
  where the language and the Z3 encoding read it as a conjunction; and rtamt's `iff` robustness is
  negative whenever the two sides' margins differ, so an equivalence between two false operands is
  reported violated. The fourth is the known exact-tie boundary. Each is reported rather than fixed
  — which side moves is a decision about an engine's contract — and each is pinned twice, excluded
  by name from the new conformance test and asserted to still diverge, so neither a silent addition
  nor a landed fix leaves the list stale. See `docs/language.md` §4.

- **Equivalence became a connective the graded fragment can read, instead of a comparison the
  author never wrote.** `preprocess_spec` rewrote `φ <=> ψ` into `(φ) == (ψ)` textually, before the
  Python parse. Over the Booleans that is sound — equivalence *is* equality of truth values — but
  over the residuated lattices of §9 it is not, and because the rewriter had already destroyed the
  distinction by the time anything checked, a graded `<=>` was refused as a *threshold*, naming a
  construct the author never typed. `implies` was spared only by being spelled as a call rather
  than as an arrow: an accident of text substitution, not a decision. The rewriter now emits a
  distinct `Iff(φ, ψ)` node on the same footing `Implies(φ, ψ)` already had. The two-valued
  evaluator reads it as equality of truth values, so every existing spec means exactly what it
  meant — held to the truth table in the interpreter and in the Z3 encoding rather than by eyeball.
  The graded evaluator reads it over `Algebra.biresiduum`, `(φ → ψ) ⊗ (ψ → φ)`, derived from the
  residuum each algebra already stores rather than added as a fourth independent operation; under
  Łukasiewicz that is `1 − |x − y|`. A crisp `==` the author actually wrote is still a comparison
  and is still refused under a graded atom, naming `==`. This is a prerequisite for the settled
  formal semantics — one denotation parameterised by the algebra, with `𝔹` as the two-element
  Boolean algebra rather than a separate system — which obliges every connective to have a reading
  in the algebra, and equivalence had none because it was not a connective by the time anything
  looked. **No shipped pack uses either spelling and no shipped verdict changed.**

- **The evidence scale gained a second coordinate, and the strength lattice did not move.**
  `unattainable < observed < probed < proved` is a chain, and three shipped situations were not on
  that axis: a `counterfactual` duty is a property of a *pair* of executions and so has no trace
  rung, the certificate duty is measured against an inference artefact and so has a ladder of
  exactly one, and a graded duty (§9) was `inconclusive` at `strength=None` and therefore
  indistinguishable, in the counts and in the headline, from a duty an engine merely failed to
  settle. `verdict.EvidenceBasis` is the dimension beside the chain: `behavioural`, `relational`,
  `artifact`, `assessment` — a trace property, a 2-safety property, an abductive explanation over a
  model encoding, and a truth degree over a residuated lattice, each named after published work
  rather than after this repository (`docs/semantics.md` §10 carries the citations). Four things are
  structural rather than conventional. **A basis is a kind and never a rank**: the members carry no
  order and comparing two of them, or one against a `Strength`, raises rather than answering.
  **A result cannot carry a rung its basis does not admit**, so a counterfactual duty cannot be
  reported `observed` and a certificate duty cannot be reported `proved` — three sentences that
  lived in three module docstrings became one refusal in `RequirementResult.__post_init__`.
  **The basis is derived from the duty and never declared**: a function of the requirement alone,
  so no pack field and no adapter can widen what a duty may claim. **No rendering draws a basis as
  a rung**: `render.basis_sentence` is the only place any surface words one, on the discipline
  `render.degree_sentence` already carries, and the affected-individual projection is shown no
  basis at all. What moved in the output: the text report and HTML dossier gained one sentence per
  non-behavioural duty naming the rungs it cannot reach and why, the dossier's strength-lattice
  track now draws only those rungs rather than showing a system as one exposure away from a rung
  nothing can reach, the counts gained `on_an_assessment` split out of `not evaluated`, and every
  JSON result gained a `basis` key (an addition, so `JSON_SCHEMA_VERSION` did not move). **No
  shipped verdict and no shipped strength changed.**

- **Machinery for open-textured predicates — the words the law states without a sharp boundary —
  and no shipped duty that uses it.** Twenty-one of twenty-nine shipped requirements are presence
  checks, and the fourth column of `docs/refinement.md` says the same thing row after row:
  *meaningful*, *sufficiently detailed*, *adequate*, *appropriate* were not modelled. Two new
  fragments answer different halves of that. `undetermined(signal, "predicate", "authority")` is a
  predicate **no engine settles**, reported *not evaluated* and naming who resolves it, reusing the
  path `not_evaluated_for_unreachable_trigger` established rather than a mechanism beside it — one
  such atom leaves the whole formula unsettled, so its presence conjuncts are no longer answered and
  reported as the duty's. `degree(signal, "predicate")` is a **truth degree**, read over a residuated
  lattice in `src/reasonsmith/manyvalued.py` — Łukasiewicz, Gödel and product, each stored with its
  residuum and checked against the residuation law rather than asserted to satisfy it. Four
  constraints are structural rather than conventional. **The algebra is declared**: a pack shipping a
  graded duty without `[grading] algebra` is refused at load, naming what is missing, and the
  declaration reaches that pack's graded requirements and no others. **The degree has a declared
  source**: it comes from a `manyvalued.Grading` a caller passes to `check_conformance` — never from
  the audited system, which would be the `reason_is_specific` self-declaration wearing a lattice's
  clothes — and `RequirementResult` refuses a degree that does not carry the authority, scale and
  method that fixed it, the shape `PROBE_BUDGET_FIELDS` already forces. **A degree is a distinct
  evidence basis and never a rescaled verdict**: `render.degree_sentence` is the only place any
  rendering formats one, a result carrying a degree carries no `strength`, and the
  affected-individual projection is shown the duty as unsettled in words and never the number. **A
  two-valued duty cannot acquire a degree**: `classify_fragment` gates it exactly as it gates the
  counterfactual atom, and a `degree()` atom under a comparison — which is a compliance threshold,
  the pack author's number presented as the regulation's — or under a temporal operator is a load
  error. A graded duty is reported *not evaluated* with its degree carried beside it as a
  measurement: turning one into `satisfied` needs a threshold no statute states, and that is a legal
  reading this tool does not make. **The strength lattice did not move**, no engine was added, and no
  shipped verdict changed — the two fragments are dispatched after the capability gate, so a system
  that can show nothing is `unattainable` exactly as it was and never a low degree. `docs/semantics.md`
  §9 is the contract, including the presentation rule; `ROADMAP.md` objective 6 is what a first
  shipped duty would have to bring.

- **`validate-pack --analyse` has a decision procedure for temporal duties, beside rtamt rather
  than instead of it.** The analysis decided a pack's questions with Z3 over one decision record,
  so a `temporal` spec reached it only through the `always(state property)` reduction and every
  other shape was skipped by name — including `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out`,
  a shipped binding duty written with `until` that no question the analysis asks could reach at all.
  `src/reasonsmith/ltlf.py` now renders the whole fragment into linear temporal logic over finite
  traces and puts satisfiability and entailment to an installed decision procedure. **It is a syntax
  mapping and an emptiness question, on the same terms `engines/observed.to_stl` is one for rtamt:
  no temporal semantics, automaton construction, tableau or monitor is implemented in this
  repository.** The two backends cannot disagree, and that is the acceptance test —
  `test_the_ltlf_backend_agrees_with_the_monitor` walks a generated corpus of traces per shipped
  temporal duty and fails at the first one on which rtamt's robustness and the automaton's
  acceptance part, in the shape `test_the_solvers_fold_is_the_interpreters_fold` already gives the
  `contains()` atom. The backend is an **optional extra** (`pip install reasonsmith[ltlf]`): nothing
  in `check`, in any engine or in any shipped example touches it, `pip install reasonsmith` stays a
  two-command demo, and with it absent the analysis prints that it is absent rather than answering
  from a weaker substitute. Four costs are stated in `docs/semantics.md` §8 rather than left to be
  found: the reading is propositional so every magnitude is an opaque atom and satisfiability is
  reported only in the affirmative; it is future-only, so a past operator is skipped by name; every
  question is asked over a non-empty trace, because the logic admits the empty one on which every
  `always` duty holds; and a question over the procedure's atom ceiling is refused by name rather
  than run, which today is every *pair* of shipped temporal duties. **No three-valued finite-trace
  verdict is computed**: the installed procedure exposes an automaton and no monitor construction
  over it, so the Bauer/Leucker/Schallhart distinction is reported unavailable rather than
  synthesised, and nothing on the strength lattice moved. No engine, no rung and no shipped verdict
  changed.

- **`until` and `since` in the property language, on a real duty and a recorded reversal.** Both
  are written as binary prefix calls — `until(left, right)`, `since(left, right)` — classified into
  the `temporal` fragment and rendered to rtamt's infix form by `engines/observed.to_stl`. **The
  mapping is the whole of it: rtamt has parsed both operators all along, and no temporal semantics
  is implemented in this repository.** `until` shipped on the evidence
  `ROADMAP.md` §2 demanded — `ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out`, 12 CFR
  1002.9(c)(2), whose obligation runs from a notice of incompleteness and ends when the applicant
  supplies the information or when the designated period lapses. `since` shipped **without** such a
  duty, by an explicit decision of 2026-08-04, and §2 of the roadmap now records that as a reversal
  rather than dropping the condition it set. The new requirement is the second in any shipped pack
  whose clause states a defeater the property carries, so `docs/refinement.md`'s census moves to 2;
  it is `unattainable` on every shipped example system, and no existing verdict moved.

- **Every shipped requirement now says what kind of duty it is and whether the law states an
  exception to it, and the recurring "the general rule is formalised, the exception is not" claim
  is a number rather than an impression.** `[[requirement]]` blocks carry two new required fields
  with no default, `deontic_type` (`obligation`, `permission`, `prohibition`, `reparation`) and
  `defeasibility` (`strict`, `defeasible-modelled`, `defeasible-unmodelled`, `trigger-unmodelled`),
  refused at load time outside those vocabularies. **No engine reads either field**; they are
  carried so `docs/refinement.md`, *The defeasibility census*, can be derived from the packs and
  held to them by `tests/test_docs_refinement.py`. The measurement: of the 28 shipped requirements,
  **3** have an exception the law states and the property does not carry — 12 CFR 1002.9(a)(1)'s
  paragraph (c) notice, GDPR Article 22(2)'s three bases, and Article 53(1)(b)'s *without
  prejudice* proviso — **1** has one the property does carry, in the propositional structure the
  language already has, and **12** have an unmodelled *trigger*, which is a missing signal rather
  than a missing construct. On this evidence rebuilding the property language on prioritized
  defaults is not justified, and the census states the three limits of that conclusion rather than
  leaving them to be found. `deontic_type` came out 23 obligations, 4 prohibitions, 1 reparation
  (Article 55(1)(c), whose antecedent is a harm and not the violation of any duty in any shipped
  pack) and **no** permissions.

- **A pack can be checked against itself: `reasonsmith validate-pack <pack> --analyse`.**
  `src/reasonsmith/analysis.py` reads a pack as a set of formulas and answers four questions no
  `check` run can, reusing the Z3 encoding in `engines/proved.py` rather than building a second
  one: whether the requirement set is **jointly satisfiable** (with an unsatisfiable core naming
  the duties that cannot hold together); which requirements **entail or are equivalent to** which —
  the EU AI Act Article 12(1)/12(2) overlap `docs/refinement.md` recorded in prose after a human
  read the TOML is now found by the tool; which are **vacuously discharged**, on the
  Kupferman–Vardi definition restricted to the fragments this repository ships and stated in
  `docs/semantics.md` §8; and, with `--system-module`, a **mutation score per duty** over
  single-point mutants of the system's declared rules. Findings do not change the exit code: a pack
  the loader accepts is a valid pack. The vacuity rule coincides with the existing
  `report.not_evaluated_for_unreachable_trigger` on the case that rule already handles — that
  agreement is `test_vacuity_coincides_with_the_unreachable_trigger_rule` and is the acceptance
  test of the definition — and the general rule additionally catches vacuous *passes*, which the
  special case cannot. The mutation score reaches **only a system exposing its decision logic as a
  rule block**, which is not most audited systems; `analysis.MUTATION_LIMIT` says so on every
  analysis carrying one, and `RESULTS.md` (*Pack Analysis Note*) carries the measured figures.
- **A subset-minimal sufficient reason is defined, and the certificate measures it.** The deletion
  probe switched each reason off *alone*, so two reasons jointly necessary and individually
  removable were both reported `deleted` and this tool accused a system of omitting two reasons its
  inference demonstrably used — unsoundness in the direction that matters. `docs/sufficient-
  reasons.md` is the definition: Ignatiev, Narodytska and Marques-Silva's abductive explanation and
  its contrastive dual, specialised to the deletions `artifacts.InferenceArtifact` admits, with the
  Reiter minimal-hitting-set duality it rests on and the published sources it comes from.
  `reasonsmith.explanations` is the measurement — the MARCO seed/shrink/grow enumeration with Z3 as
  the oracle over the subset lattice and the system's own engine as the membership oracle — and
  `certificate.certify_artifact` now decides every candidate-`deleted` reason against it. The
  monotonicity declaration [#112](https://github.com/eduardstan/reasonsmith/pull/112) added for a
  soundness reason turns out to be the precondition the
  theory needs; it is one premise and not two.
- **A reason the joint search does not resolve is `undetermined`, and the search's bound travels.**
  `deleted` is universal over the contrastive sets and is claimed only where the enumeration ran to
  exhaustion; `live` is existential and one contrastive set establishes it. So a shorter search
  names *fewer* missing reasons than a complete one and never more, and there is no setting of the
  budget at which this rung accuses a system it would otherwise have cleared. The probes spent and
  whether the enumeration finished ride in `details[PROBE_BUDGET_KEY]` under the discipline
  `PROBE_BUDGET_FIELDS` already forces.

- **A decision trace can state its own clock.** A record may carry `sut.TIME_DOMAIN_KEY` — a
  mapping of event kind to the timestamp that event happened at — so *when the clock started* is a
  recorded fact rather than something a latency number the system computes about itself implies.
  The three events 12 CFR 1002.9(a)(1) counts from are told apart by their event kinds, which is
  the case that made this worth having (`docs/refinement.md`,
  `ecoa_reg_b_1002_9_a_1_timing_of_notice`).
- **The monitor's time domain is a stated parameter.** `ObservedEngine.evaluate` takes a
  `sut.TimeDomain`, defaulting to `sut.ORDINAL_DOMAIN`, and `TimeDomain.ticks` is the only source
  of the `time` series. A metric or interval semantics is now a new domain and a new branch rather
  than a re-reading of every property; none is added here.
- **An inference artefact is reasonsmith's own abstraction, and a ground program is one adapter.**
  `reasonsmith.artifacts.InferenceArtifact` states what a reason-bearing artefact is, what it must
  expose for the deletion probe to measure reasons from it, and — the load-bearing part — whether
  its **inference is monotone in its facts**. `artifacts/ground_program.py` is one family
  satisfying it, wrapping a nesyarena `GroundProgram`; nesyarena is unchanged, unvendored and
  unre-pinned, and neither the protocol nor `certificate.py` imports it any more. The knowledge
  graphs, reason traces, extracted rule sets and decision trees of the paper's taxonomy are now
  adapters rather than special cases; none is implemented here, and a family whose reasons are
  extracted rather than enumerated exactly still needs a decision about the strength lattice before
  it needs an adapter (`docs/semantics.md` §3, *The inference artefact*).

### Changed

- **The README leads with its own result, and the result ships as two generated artefacts.**
  `docs/build_showcase.py` writes three files from one run — a figure putting what the applicant was
  told beside what the decision's own inference used, with the four reasons the answer did not depend
  on struck; an animated terminal recording of two commands and the violation appearing; and
  `docs/showcase.html`, a page carrying both above the conformance report they came from. Every
  number on both is read off `demo.key_finding_report()`, the run
  [`docs/build_example.py`](docs/build_example.py) already composes the committed dossier's key
  finding from, and `tests/test_docs_showcase.py` holds all three byte-for-byte and asserts that no
  reason label appears in the builder's own source. The cast's timings are synthesised from the row
  index, which is what lets a terminal recording be pinned at all; it is a deliberate placeholder for
  the interactive explorer proposed in
  [#120](https://github.com/eduardstan/reasonsmith/pull/120). The README's first screen is now the
  figure, the result, `pip install` plus one command and that recording. Nothing was deleted: the
  forty-line transcript that used to sit there is [`docs/example-output.md`](docs/example-output.md)
  §3, where the transcripts live and where the suite re-runs them, and everything else moved down the
  page or one link away. No behaviour changed — no engine, duty, pack, verdict, rung, basis or
  parser.

- **`uncertified` was one bucket doing three jobs.** `Certificate.unseparable`,
  `.inconclusive` and `.undetermined` report apart — a reason with no fact of its own, a probe that
  carried no exact signal, and a reason the joint search left open — and `uncertified` stays their
  union, because all three mean the same thing to a verdict. One consequence is visible in the
  shipped transcripts: a reason called `deleted` off one private fact while a *shared* fact of it
  moves the engine now reads `not certifiable`, because the old label asserted the answer did not
  depend on a reason a deletion of whose facts moved the answer.
- **A reason is no longer measured under a definition that does not apply to it.** The reason-
  adequacy duty `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` reports *not evaluated*, naming
  why, for an artefact that declares its inference non-monotone, declares nothing at all, or
  declares itself monotone where the probe measured a deletion that raised the system's answer —
  never `violated`, never `satisfied`, and never handed down to the presence check that shares the
  clause. This replaces the disclosure below with a refusal: a creditor whose policy exceptions
  lawfully retract reasons was reported violated for having stated its reasons correctly. It is
  *not evaluated* rather than *unattainable* because the gap is in this tool, which has one
  definition of a reason and it does not survive defeat. No verdict moves for a system that
  declares itself monotone, and the shipped demonstration is unchanged; an adapter exposing
  `artifact()` must now declare `monotone`, and one that does not is reported not evaluated rather
  than measured.

- `--json` envelope `schema_version` is **2**. It gains `time_domain`, the clock the trace a run
  read stated. The bump is for meaning, not for the key: under version 1 a temporal bound counted
  records and the document did not say so.

- **The deletion probe states its direction, and keeps the one fingerprint of an engine that
  breaks it.** `certificate.LIMITS` and `docs/semantics.md` §3 (*certificate*) now say that the
  probe only switches facts off, never on: `deleted` means *the answer did not depend on this
  reason under this interpretation*, and on a system whose reasons can be retracted by an added
  fact — a policy exception evaluated after the rules fire — a lawfully withdrawn reason is
  reported deleted exactly as a dropped one is, and can drive `violated` against a creditor whose
  notice was right. The limit is disclosed rather than repaired. What is repaired is the signal:
  the sign of `engine_drop` is no longer taken in absolute value, so a deletion that moves the
  engine's answer *up* is reported as `non_monotone` on the reason verdict, on the certificate, and
  in the engine's own summary and `details`. A defeated reason is still counted deleted — it was
  probed cleanly — and is deliberately not moved into an inconclusive bucket, which would lose the
  flag.

- **The certificate probes every private fact of a reason, not one of them.** Coverage was decided
  by `repr` sort order, so two systems alike but for a field name got materially different probes.
  The probe budget now counts *facts switched off* rather than *reasons switched off*, and its
  trial count rises accordingly (the shipped demonstration goes from 6 to 9 replayed inferences).
  No shipped verdict moves.

### Notes

- Nothing shipped changes verdict. A log that states no clock is `"ordinal"` and is answered on the
  record index exactly as before, a log that gained event timestamps keeps the verdict it had, and
  a duty asked for on any other domain is reported *not evaluated*, never `satisfied`
  (`docs/semantics.md` §2, §5; `tests/test_time_domain.py`).

## [0.7.0] - 2026-08-04

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

- **The coverage floor never failed, so a green CI job was read as the floor holding.**
  `--cov-fail-under=93` is decided by `coverage.results.should_fail_under`, which compares
  `round(total, precision)` against the floor, and pytest-cov defaults `precision` to 0. At 0 the
  suite's real 92.79% rounded to 93 and the job exited 0 — while pytest-cov's own summary compares
  the *unrounded* total and printed `FAIL Required test coverage of 93% not reached. Total
  coverage: 92.79%` into the same log. `[tool.coverage.report] precision = 2` in `pyproject.toml`
  makes the comparison the one the printed figure states, for both workflows and for a local run,
  and `test_the_coverage_floor_fails_a_total_below_it` asks the real function whether a total a
  tenth below each workflow's own floor fails, so the two cannot drift apart again.

  Enforcing it made the gap visible, and the gap was then **decided rather than closed**: on
  2026-08-04 the measured 92.79% was accepted as the project's coverage level — explicitly not
  chased with tests written for the number — and the floor was lowered once, from 93 to **92.5**,
  in both workflows. 92.5 sits under the measured total so it passes, above the ~0.5% band the
  rounding bug silently tolerated, and with slack enough that an ordinary refactor does not turn
  `main` red. The step comment in `.github/workflows/ci.yml` is the record of that decision, and
  the floor is not to be lowered again without one of the same kind.
- **`probed` reported `satisfied` over a domain part of which it could not measure, and then
  stated a replay count that was not true.** `engines/certificate.py` states the rule — *a
  violation needs one witness; a satisfaction needs complete evidence* — and `record`, `observed`,
  `proved` and `counterfactual` all keep it by construction. `probed` was the rung that did not.

  - **A search in which any planned input raised is now reported not evaluated, never satisfied**,
    naming how many inputs went unmeasured and what was found in the rest. A lender that answered
    correctly up to 40000 and raised above it was reported `satisfied` on
    `income >= 30000 -> approved` over a domain a quarter of which it had refused to be measured
    on. The inputs a system raises on are not a random sample of the search space: they are the
    band its author put outside what the system answers for, which is where a property is most at
    risk. The refusal is asked on the satisfied path alone — a counterexample that reproduced is a
    witness, and it stands however many inputs raised beside it — and it is asked *before* the
    unreachable-antecedent guard, because where inputs raised, "the antecedent fired nowhere" is a
    claim about the measured part while the unmeasured part is exactly what might have reached it.
  - **The replay count was false in the data, not only in the rendering.** `evidence_summary`
    travels into `--json` and therefore into every downstream consumer, and it read *"no
    counterexample … in 35 input(s) replayed"* where 26 had been. The summary now counts the
    inputs the property was actually read over, and `render._budget_line` — shared by the text and
    HTML renderings — names `inputs_errored` beside the replay count. This also resolves a
    self-contradiction the trigger guard had introduced, two counts of one search printed four
    lines apart: the guard's domain string subtracted the errored inputs and the budget line did
    not.
  - **No verdict, strength or count moves for a system that errors on nothing**, which is every
    shipped example: all three document builders regenerate byte-identically and no published
    probe budget changes.

- **Two summaries described a measurement the engine did not make.** Neither is a verdict change;
  both were sentences a reader would have checked a system against.

  - **The certificate rung's satisfied summary counted decisions it had set aside.** A creditor
    lawfully on the 12 CFR 1002.9(a)(2)(ii) disclosure branch for one decision and stating its
    reason on the other read "Probed over 2 certified decision(s): … so no reason was shown
    deleted" — on a run where the deletion probe measured **four** reasons deleted behind the
    first and the duty set that decision aside, its antecedent being false. The engine had a clause
    for a decision it could not certify and a clause for a reason it could not separate, and none
    for a decision it measured and the duty does not ask about. The summary now names how many
    certified decisions the trigger reached, how many it did not, and how many reasons were
    measured deleted behind those, and says that this verdict speaks to none of them; the counts
    travel in `details` as `decisions_whose_trigger_never_fired` and
    `deleted_reasons_behind_an_untriggered_decision`. The verdict is unchanged: what the clause
    reaches is a question about the duty, not one an engine answers by rewording a summary.
  - **The paired-replay summary presented the values it sampled as the values the constraints
    admit.** `DEFAULT_MAX_VALUES` bounds the enumeration at four, so over a declared
    `0 <= applicant_prohibited_basis <= 8` the summary named four of nine as the admitted set. It
    now says what was searched and out of what — every admitted value, or that many of them with
    the declaration admitting more.

- **Breaking (verdicts move): a protected variable the declaration does not type as an integer is
  reported *not evaluated*.** One word in the variable table cleared a system that discriminates at
  category 2: typed `real`, the replay rung enumerated 0, 0.125, 0.25 and 0.5 — four points in the
  bottom sixteenth of a band running to 8, none of them a category — and reported `satisfied`. A
  prohibited basis is a category, not a magnitude, and over a dense sort the values between the
  categories are admissible too, so the proof rung's witness pair may be one the system can never
  be given. Both rungs of `engines/counterfactual.py` now refuse before they encode or enumerate
  anything, naming the variable and the sort it was declared as. The same system typed `int`
  reaches its verdict unchanged. This is the four-outcome discipline applied to an authoring
  mistake the tool accepted in silence.

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
