# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## The authority

`src/reasonsmith/table7.toml` is a verbatim transcription of Table 7 of *Symbols and Neurons: A
Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:22), whose
first author owns this repository. The conformance checks come from Table 19 of the same paper. The
paper is the authority: where a design and the table disagree, the table wins, or the disagreement
is reported as a finding. Do not improve, extend or modernise the wording — the transcription's
value is that a lawyer can check it against the print.

## Dependency

nesyarena supplies the ground-program IR, bounded proof enumeration, the exact WMC oracle and the
adapter protocol. Depend on it; do not reimplement any of those. `pyproject.toml` pins
`nesyarena==0.1.0` from PyPI — `pip install reasonsmith` is the user install, and
`pip install -e ".[dev]"` in a venv is the contributor install, the one CI
(`.github/workflows/ci.yml`) runs. Never point it at a sibling checkout, tag, or a
branch: the measured numbers must stay reconstructible. `torch` is
deliberately not a declared dependency of *this* package (see README, "Dependencies & PyPI") but
has been installed and measured in a separate environment — see [RESULTS.md](RESULTS.md) for the
exact commands and counts, and do not re-litigate that caveat from stale memory of "torch was never
installed here". `tests/conftest.py` puts `src` on the path so this package itself needs no
install, but nesyarena does. `pip install`ing nesyarena only gets the built package, not its
`tests/`/`experiments/` directories — to run nesyarena's *own* suite (as opposed to depending on
it), clone `github.com/eduardstan/nesyarena` separately and check out
`22b539bad6c3510fe457aa751141c5c4aa1483ea`, the commit 0.1.0 was built from (RESULTS.md, "PyPI
Release Note", records how that was verified; the repo publishes no tag).

## Two rules that shaped the code

- No emitted record, certificate or measurement may present itself as complete when it is not, and
  every one carries its own limits. See the module docstrings in `evidence.py` and `certificate.py`
  for why each check exists before changing one.
- No check asserts branding or presentation. Limits tests pin semantic boundary clauses, not full
  prose.

The reason-deletion probe is **one-directional** — it switches a fact off, never on — so `deleted`
means *the answer did not depend on this reason under this interpretation*, and on an engine that is
not monotone in its inputs a lawfully retracted reason is indistinguishable from a dropped one. That
premise is now **declared rather than assumed**. `artifacts/` is reasonsmith's own abstraction of an
inference artefact — what a reason-bearing artefact is, what it must expose for the probe to measure
reasons from it, and whether its inference is monotone — and `artifacts/ground_program.py` is one
adapter over a nesyarena `GroundProgram`, which is why neither `artifacts/__init__.py` nor
`certificate.py` imports nesyarena any more. A second family (knowledge graph, reason trace,
extracted rule set, decision tree) is an adapter and not a branch in the core; none is implemented,
and one whose reasons are *extracted* rather than enumerated exactly cannot take this rung until the
strength lattice can say so — that is a captain decision, stated in `docs/semantics.md` §3 rather
than slipped in. `engines/certificate.py` asks the declaration before it certifies and again of the
measurement afterwards, and reports **not evaluated** — never violated, never satisfied, never
downgraded to the presence check sharing the clause — for an artefact declaring non-monotone,
declaring nothing, or declaring monotone where a deletion raised the system's answer. One refused
artefact refuses the run. It is *not evaluated* and deliberately not *unattainable*: the gap is in
this tool, and telling a creditor to stop having lawful policy exceptions is the wrong instruction.
Four things must not be undone: the declaration is **required**, not defaulted to True, for the
reason `engines/counterfactual.py` refuses undeclared `computes` — a defeasible artefact and a
monotone one produce the same probe and the same count; the sign of `engine_drop` is kept, so a
deletion that raises the engine's answer is flagged `non_monotone` on the verdict and the
certificate, and that flag is now what *refutes* a false declaration rather than decorating a
verdict — it can refute and never confirm, since a defeater holding no fact of any enumerated reason
is never switched off at all; a defeated reason is still counted `deleted` wherever a certificate is
produced and must never be moved into the `unseparable`/inconclusive bucket, which would lose the
flag; and **every** private fact of a reason is switched off, not the first in `repr` order, because
coverage decided by a field's name gave two otherwise identical systems different probes. The budget
therefore counts facts switched off, not reasons. `tests/test_artifact_protocol.py` holds all of it
and `docs/semantics.md` §3 (*The inference artefact*) is the contract.

In v0.2 the first rule becomes structural. A verdict carries the strength of the evidence behind it
(`verdict.py`), and `RequirementResult.__post_init__` refuses to construct a result that claims more
than it has — including `strength=None` for "no engine here evaluated this", which is deliberately
not a strength on the lattice. Three consequences worth knowing before editing `report.py`: combining
zero verdicts is `inconclusive`, never vacuously `satisfied`; `SUPPORTED_FORMALISMS` is the list
of formalisms an engine actually exists for — widen it when the engine lands, not before; and a
`probed` result cannot be constructed without the search budget that produced it
(`PROBE_BUDGET_KEY` / `PROBE_BUDGET_FIELDS`), so the bound travels with the verdict into every
rendering instead of being a rendering convention.

Which engine a requirement reaches is decided by what the system exposes — for *every* fragment,
not just `logical`, since the property-language unification. `rulelang.py` is the one property
language: every `spec` is a formula in it (presence atoms `present(signal)`, the phrase atom
`contains(signal, "literal")`, comparisons, connectives, temporal operators), `formalism` names
which fragment the formula belongs to, `load_pack` classifies the spec and refuses a mismatch or
prose, and the English lives in the required `rationale` field. `report._engine_ladder` then
collects every engine the fragment *and* the exposed surface allow and takes the strongest evidence
produced: `logic()` gets Z3, `decide()` gets the replay search, and a trace gets the record engine
for a presence conjunction and the observed engine for **every other fragment, `logical`
included** — a state property is a property of one decision record, so a trace of them is evidence
about it, and declining to read one was a defect the label caused rather than the evidence. A
temporal duty reaches Z3 in exactly one shape: `engines/temporal.py` reduces `always(f)` — with `f`
free of temporal operators — to `f` and hands it to the proved engine, which is exact because over a
finite trace `always(f)` holds iff `f` holds at every position and every position is a decision the
exposed logic admits. `eventually(f)` and every nested shape stay at `observed`, deliberately, and
the asymmetry between a universal satisfied verdict and an existential violated one travels on the
result as `TRACE_SEMANTICS` (`docs/semantics.md` §3, *`proved`, over a trace*). Two limits of the trace
rung are stated rather than silent: rtamt cannot render a comparison against a Boolean constant, and
it reads the `spec` as written, so implication in a pack must be spelled `->` and never
`Implies(...)`. Read `docs/semantics.md` §2 and §3.5 before editing any of it — they state the rule,
the atom encodings, and the one case the ladder does not resolve (exposed logic disagreeing with the
trace).

One rule cuts across every rung and is deliberately written **outside** all of them: an implication
whose antecedent nothing in an engine's evidence domain satisfies is *not evaluated*, `strength=None`,
naming the antecedent and the domain. It is a fact about the **formula**, which is why seven local
domain guards never found it and why the fix is not an eighth: `rulelang.implication_antecedent`
names the subtree (stripping a top-level `always`, never an `eventually`) and
`report.not_evaluated_for_unreachable_trigger` words the refusal once against the result model. Each
rung then answers it with what it already holds — `proved` checks premises ∧ antecedent satisfiable
(the premise check one quantifier deeper), `temporal` inherits it through the reduction, `observed`
monitors the antecedent per position, `probed` counts the replays that reached it, and
`certificate` counts the certified decisions that reached it in the walk that already decides the
property against the measured count — and `probed` is
in that list because the ladder falls to it, so guarding the proof rung alone only moves a vacuous
`satisfied` down a rung, while `certificate` is in it for the opposite reason: the ladder gives
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete` that rung and no other, so nothing beneath it
could catch the same empty claim. Every rung asks it on the *satisfied* path alone: a violation names a
witness whose antecedent fired. What this cost is stated in `docs/semantics.md` §4 and must not be
quietly undone: a creditor lawfully on the 12 CFR 1002.9(a)(2)(ii) disclosure branch is now neither
accused nor cleared, because `not applicable` per decision is the honest verdict and the result model
has no per-record applicability.

`counterfactual` is the fourth fragment and the only **relational** one — a property of a *pair* of
executions. `counterfactually_invariant(outcome, protected)` is its single atom, it is the whole of
a `spec` or no part of one, and `engines/counterfactual.py` is the whole of its ladder: Z3
self-composition at `proved` (the rules encoded twice under `_Scope` namespaces, every free input
held equal but the protected one), paired replay at `probed`, and **no trace rung, ever**. The
refusal lives in `rulelang.eval_expression`, not in `_engine_ladder`, because every trace-reading
engine evaluates through that interpreter — move it and the guarantee becomes a convention. Two
cases must never merge, and telling them apart is the only reason `computes` is consulted here: a
system that accepts the protected variable and provably ignores it is `satisfied`; a system with no
notion of it is `unattainable`. Without the declaration both encode identically and both come back
`unsat`, which would certify an unaware system as provably fair. Two further `unsat`s mean *no pair
exists* rather than *no pair disagrees*, and the proof rung refuses both before it reads the
negation: a declaration that pins the protected variable (the replay rung already refused that
system, so the ladder was publishing the engine that asked less), and rules that assign the
protected name while `computes` omits it — checked on the encoding (`is_definitely_assigned`,
`scope.inputs`), because that route is invisible to the declaration. A third refusal is about the
**sort**: a protected variable the declaration does not type as an integer is *not evaluated* at both
rungs, naming the variable and its declared sort, because a prohibited basis is a category and over a
dense sort the replay search samples fractions between the categories (0, 0.125, 0.25, 0.5 over a band
running to 8) while the proof rung's witness may be a pair the system can never be given. It lives in
`_direction_refusal`, so both rungs inherit it. `TREATMENT_LIMIT` rides on every
result because the duty cannot see a proxy or a disparate impact, and neither rung ever takes the
protected value from the trace — a decision record holding a fact about a natural person is a
collection cost this repository does not create, which is also why no shipped example system
declares one. For the same reason the protected argument is the one name
`report.analyze_unattainable` does not subtract from `capabilities()`: that set is what a system can
*emit* into a record, this duty needs what its procedure *accepts*, and gating on it would report a
creditor whose log carries a prohibited basis for nobody unattainable and tell it to start logging
one per decision. The name stays in `requires` because it is what the engine names as missing when a
system's declared logic has no notion of it.
`applicant_prohibited_basis` is the first shipped signal outside the paper's four Section 6.3
categories; `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy` keeps it the only one.
Read `docs/semantics.md` §3 (*counterfactual*) and the `docs/refinement.md` row before touching any
of it. Group-statistical fairness — parity, equalised odds, calibration — is unreachable on this
evidence model and is documented as a hazard in `docs/authoring-packs.md`; do not build one.

The proof rung refuses a property built out of names the declared rules never assign, on the ground
that such a name is a free constant of the encoding — for `present()`, for `contains()`, and (since
the temporal reduction made it reachable) for a comparison of magnitudes. The third refusal is the
one that needed a **direction**, so `sut.logic()` may declare `computes` beside `variables`: the
names the system produces, as against the ones its situation supplies. The two together give three
states — computed, input, *no notion of* — and `_check_declared_directions` refuses a property
reading a name in the third state, or a declared output the rules do not settle on every path.
A declared **input** is quantified over where the property also reads a name the rules settle, or
reads its free names as flags rather than magnitudes — which is what keeps
`income >= 30000 implies approved` and `gdpr_art22_1_no_prohibited_decision_for_any_input` provable.
`RulesAdapter` derives `computes` from its rules' assignment targets — the premise of that adapter
is that the rules *are* the decision procedure — so no adapter here is undeclared, and a `computes`
name outside `variables` is refused at construction. Nothing second-guesses the declaration: an
adapter calling an output an input is answered about the system it described, the same trust
`system_domains` gets. What a declaration may **not** do is widen what reaches the solver, so
`_check_magnitudes_are_computed` runs beside `_check_declared_directions` and never instead of it:
`variables` is a type table, a caller may list a name the system merely logs, and reading such a
name as an input made both `proved` verdicts a function of the caller's type table — `violated` over
numbers nobody computes, and `satisfied` where a constraint of the system's own restates the duty.
`docs/semantics.md` §3.5, *When the magnitudes are not the system's own*, states all of it, names
every test, and states the cost: a duty comparing declared-input magnitudes alone cannot be
`proved`.

`contains(signal, "phrase")` is the one atom that reads *what a statement says* rather than whether a
field is blank, and it exists because a duty settled by `present()` alone accepts a reason of
`"n/a"`. It must keep agreeing across all three encodings — the rulelang interpreter, the synthetic
per-record flag fed to rtamt, and the Z3 regular language — which is why the case fold is ASCII-only
and one-to-one and a non-ASCII phrase is refused; `test_the_solvers_fold_is_the_interpreters_fold`
is the differential check, the counterpart of the blank-string one for `present()`. Only a clause
that states its own negative constraint may use it: the shipped example,
`ecoa_reg_b_1002_9_b_2_specific_reasons`, checks the two statements 12 CFR 1002.9(b)(2) itself calls
insufficient and decides nothing about whether any other statement is specific. Do not add a phrase
the regulation does not supply, and never push the judgement into the adapter as a self-declared
`reason_is_specific` flag — `docs/semantics.md` §3 is why. That duty also carries the clause's
trigger as an implication, which removed a false violation against a creditor lawfully on the
(a)(2)(ii) disclosure branch; where that antecedent fires nowhere the duty is *not evaluated*, under
the cross-cutting rule stated above and in `docs/semantics.md` §4.
`docs/findings-nesyarena.md` shows those ECOA duties landing on a real system.

`requires` is a conjunctive gate, so a branch of an either/or clause must not be listed in it: the
loader (`spec._check_spec`, via `rulelang.unconditional_signal_names`) exempts a signal read only
inside a disjunction, because gating one branch reports a system that lawfully took the other
`unattainable` without running it. The exemption is narrow on purpose — every branch must be
settled by `present()` atoms, and a name every branch reads stays gated — so a disjunction over
magnitudes does not quietly widen the gate. `ecoa_reg_b_1002_9_a_2_written_statement` is the worked
example and `docs/authoring-packs.md`, *An either/or clause*, is the rule, including the three costs
it buys: a system declaring neither branch is judged on its trace rather than reported unattainable,
a typo inside a disjunct is not caught at load time, and the duty leaves the `record` fragment, so
a log holding a single decision is reported not evaluated on it.

A duty reaches a system through **two** gates, on two axes that are not the same question, and both
are required fields with no default (`spec.REQUIREMENT_FIELDS`). `scope` is a regulatory class from
`REGULATORY_CLASSES` — the EU AI Act's own five-member vocabulary. `domains` is the *kind of
decision* the duty is about, from `DECISION_DOMAINS`, matched by intersection against what a system
declares (`--system-domain`, or a `system_domains` attribute on an adapter), with `[]` meaning "not
domain-limited" and reaching every system. `report._inapplicability` is the one place both are
decided, so `check_conformance`'s plan and `evaluate_requirement` cannot drift apart, and
`evaluate_requirement` stamps `domains` onto the result once rather than threading it through four
engines. An undeclared system is `not_applicable`, never `satisfied` — the argument for that over
`inconclusive` is in `docs/semantics.md` §4, and `tests/test_domain_gate.py` holds all of it.
The one thing to keep straight before touching any of it: **`DECISION_DOMAINS` is this repository's
list and no regulation's**, because no statute defines one. A pack limiting a duty to a domain owes
its description a sentence saying so — `test_every_shipped_pack_classifies_every_requirement`
enforces it — the same discipline `docs/authoring-packs.md` applies to an invented threshold. What
the gate buys is exactly one guarantee, and not a taxonomy: a system that has not declared its
domain is never reported satisfied on a domain-limited duty. It does not model the *trigger* inside
a decision (12 CFR 1002.9 fires on adverse action, not on being a creditor), and it does not check
that a system declaring `consumer-credit` issues credit.

An engine and a pack can be **installed rather than vendored**. `plugins.py` is the whole of it —
`importlib.metadata.entry_points` over `reasonsmith.engines` and `reasonsmith.packs` — and it is
deliberately not a plug-in framework: no registry, no lifecycle, no manifest. A discovered engine
joins `_engine_ladder` at the rung its `max_strength` declares and cannot report above it
(`RequirementResult.__post_init__`, `ENGINE_PLUGIN_KEY`); one that raises, times out, returns the
wrong type or will not import reports *not evaluated*, never satisfied and never violated; one
taking a built-in's name is refused rather than namespaced; and every plug-in result names its
plug-in. `load_pack` resolves an installed pack through the same lookup and the same checks, with
built-ins winning a name collision. There is no wall clock — a plug-in that hangs hangs the run, and
that limit is stated in `docs/authoring-engines.md` rather than papered over. Read that document and
`docs/semantics.md` §3.5 (*An engine that was installed rather than vendored*) before widening any
of it; nothing here audits a plug-in, so its declared ceiling is the only bound on what it claims.

`src/reasonsmith/packs/*.toml` are derived, not authored. The EU AI Act, GDPR and ECOA packs quote
`docs/legal-sources.md`, which is the retrieval record for the official statutory text and the one
place a quote is checked against the law. The Table 7 pack restates the rows of
`src/reasonsmith/table7.toml`, and `test_pack_matches_table7_transcription` holds it to the print:
quoted text character-for-character, both halves of the legal source, and the paper's own
evidence-field keys as the signal names. Do not rename a signal to something tidier — that test is
the only thing keeping the pack attached to the paper.

`docs/refinement.md` is the refinement record: one row per shipped requirement giving the clause,
the informal duty, the formal property, and what the formalisation deliberately left out. A new
requirement means a new row in the same commit — `tests/test_docs_refinement.py` reads the packs and
fails if one gains a requirement the record does not name. It also carries, once rather than
eighteen times, what the two applicability gates still do not reach — *Two axes of reach are
modelled, and the trigger is still not one*, whose largest remaining item is the trigger inside a
decision that no system-level gate can close.

The first shipped duty whose verdict comes from a value a system declares about its own approximation
error is `gdpr_recital71_error_risk_minimised`. It compares
`scope_statements_declared_deviation` against `artifact_logs_decision_margin`, so a nonzero declared
error fails when it is larger than the decision's own margin. The bound is the system's own margin
on purpose — no threshold in a shipped pack may be a number invented for it and presented as the
regulation's. Exact equality is a checked limit, not a breach: rtamt gives it zero robustness and
the observed engine breaches only on negative robustness. What the verdict does and does not claim
is in `docs/semantics.md` §3; why it exists is finding 1 of `docs/findings-nesyarena.md`.

`docs/example-output.md` is derived too. `tests/test_docs_example_output.py` re-runs every command
block in it and compares stdout byte-for-byte, and cross-checks the header's line count and
`md5sum` against RESULTS.md. So anything that changes what the demo or the CLI prints — a wording
tweak included — means regenerating the transcripts and updating both files' headers together.
Both `docs/example-output.md` and `docs/three-systems.md` also state, near the top, the
`reasonsmith` version they were generated with, and each document's pin holds that note to
`reasonsmith.__version__`: the tree runs ahead of the last release, so a reader who installed
from PyPI and sees different output must be able to tell a stale page from a broken install. The
number is only worth anything while it is the version the tree actually is, so a version bump
means regenerating the note in the same change, or the pin fails.
The README's own CLI block is derived too, and `tests/test_docs_readme_transcripts.py` holds it
byte-for-byte to `python docs/build_readme_transcripts.py` the way the other pins hold their
documents: anything a wording change moves fails there. The builder raises rather than writing
when a command it names matches no block, because the ad-hoc helper it replaced reported success
having substituted nothing and left the front page showing a verdict the tool no longer prints.
`docs/report.html` is generated as well, but not by the CLI: `docs/build_example.py` composes it — the
Table 7 run declared into the high-risk class, beside the demonstration's key finding, which no
report the CLI writes may carry — and `test_docs_index_html_matches_the_renderer` holds the
committed page byte-for-byte to that script. Touching the renderer means regenerating the page with
`python docs/build_example.py`, the command the page names as its own provenance. That page names
no commit and cannot be made to: the commit carrying it does not exist while it is rendered, so a
hash written there would name another commit and break the byte pin the moment the page was
committed. It names the check that reproduces it instead (`PROVENANCE_NOTE` in the builder), the
same shape of claim `docs/nesyarena-conformance-report.md` carries — do not add a hash back to
either. The renderer
itself lives in `render.py` — module-level `render_text`/`render_html`, with the presentation
constants and `_source_checkout` — and `ConformanceReport`'s methods of the same names are thin
delegates to it, so a rendering edit is a `render.py` edit and nothing in `report.py`. One such
convention bears stating: the text renderer names the offending decision record of a violated
finding by the record's own `decision_id` — the same identifier the JSON
(`details.offending_trace_segment`) and HTML (witness table) renderings already use — and falls
back to the step index only when a record carries no identifier, so a reader is never handed an
empty name. That line lives on the text surface (`render_text`) and was deliberately not moved
into an engine summary, because `evidence_summary` travels into the JSON; editing an engine to
fix a redaction therefore changes a second rendering. The website
(landing, vendored libraries, fonts, assets) lives in the separate private `reasonsmith-site`
repo and deploys to Vercel — see [#35](https://github.com/eduardstan/reasonsmith/pull/35); this
repo only generates the dossier that gets published there as `report.html`, and the audience
gallery published there as `audiences.html`. Both files travel through the same hourly
`sync-dossier.yml` in the site repo.

`docs/audiences.html` is the second generated page and the only one that publishes more than one
rendering of a run: `docs/build_audiences.py` runs the shipped `symbolic_rules` system against the
`ecoa` pack — the run that mixes verdicts and strengths most, two duties `proved`, one `observed`
and two `unattainable` (no `probed` rung), so each projection has something to withhold — and
embeds all five `--audience` renderings verbatim as `srcdoc` frames inside a sixth, full
`render_html` page. That shell is not decoration:
the design tokens live inside `render_html`'s stylesheet and are not exported, so being a report
page is the only way the gallery can style itself without a second palette.
`tests/test_docs_audiences.py` holds the page byte-for-byte to the builder and fails if the
gallery grows a `<style>` block, a colour literal, a font stack, a `var(--token)` the renderer
does not define or a class it does not style. Regenerate with `python docs/build_audiences.py`.
Each frame is scrolled on load to `render_html`'s own `id="findings"` and is 24rem tall
(`FRAME_ANCHOR` / `FRAME_HEIGHT`), because opened at the top four of the five renderings are
identical for a whole screen — masthead, headline and dashboard are chrome no projection touches —
and the page demonstrated nothing. Renaming or dropping that `id` in `render.py` returns every
frame to the top while the byte-for-byte pin still passes, so
`test_every_frame_opens_where_the_documents_differ` asserts the anchor exists in all five
renderings.

The page's stylesheet is two token blocks, and three rules keep them from drifting. The dark block
is `@media screen and (prefers-color-scheme: dark)` — the `screen` is load-bearing, because the
`@media print` block below it overrides a handful of declarations and otherwise assumes the light
values, so a dark override reaching print media prints white on white
(`test_the_dark_scheme_is_screen_only_so_print_stays_light`). A solid chip pairs its fill
(`--ink`, `--ok`, `--warn`, `--accent`) with `var(--paper)`, never `var(--surface)`: that pairing
inverts with the scheme, and `--surface` puts near-white text on a light green fill in the dark
block. The report header is not an inversion of the page — it is a dark band in both schemes, so
it and the key-finding banner read `--band`/`--band-ink`/`--band-faint`/`--band-line`/
`--band-accent` rather than swapping `--ink` and `--surface`. Satisfied-green and violated-red
carry meaning here, so `test_both_schemes_keep_the_verdict_colours_apart` pins the hue channel of
`--ok` and `--accent-deep` in both blocks: a scheme that desaturates them toward a common grey
passes every contrast check and still destroys the distinction. `demo.py` carries its own
stylesheet for the key-finding section that `docs/build_example.py` composes in, and it is subject
to all three rules.

`ConformanceReport.to_dict()` leads with `schema_version` (`report.JSON_SCHEMA_VERSION`), the
`--json` envelope's shape version. It is not the package version, it increments only when a key is
removed, renamed or changes type or meaning, and `tests/test_json_schema_version.py` writes out the
key set at both levels beside the number so a shape change without a bump fails. Adding a key fails
it too, deliberately: the convention says that is not a bump, and the test exists to make the
decision be made rather than skipped.

`AudienceProjection` has one field that emits rather than suppresses: `plain_account`, on for
`affected-individual` alone, turning on `render._lay_sections`. Everything it prints is quoted —
the decision and the reason out of `ConformanceReport.decisions` (the trace `check_conformance`
already read, carried on the report and deliberately absent from `to_dict`, which is the findings
record), and a reason left unstated out of the certificate engine's own measurement. It paraphrases
no statute and explains no decision; `docs/semantics.md` §7 is the rule and the four tests in
`tests/test_audience_view.py` are the enforcement, including the one that fails if the view ever
becomes a subset of an expert view again. The `--audience` transcripts in `README.md` are derived
and held by the same `tests/test_docs_readme_transcripts.py`, so a wording change there means
`python docs/build_readme_transcripts.py`.

`docs/assets/og.png` is generated from `brand/og.html` in the site repository, is served live as the
site's social card, and must never be edited here — regenerate there, copy here, update the pinned
digest in `tests/test_social_card.py`.

`docs/three-systems.md` and the three files in `src/reasonsmith/examples/` are the answer to "how
does any model get into this tool?": a neural black box (`JSONLAdapter`, log only), a probabilistic
scorer (`CallableAdapter`, replayable) and a rule set (`RulesAdapter`, logic exposed), all checked against
the one binding duty `ecoa_reg_b_1002_9_b_2_specific_reasons` and reaching `observed`, `probed` and
`proved` respectively. `tests/test_docs_three_systems.py` holds each transcript byte-for-byte the
way `test_docs_example_output.py` does, asserts the three rungs are still three, and pins the
neural system's ceiling. That ceiling is the point of the artefact: raising it means changing the
*system*, never the adapter, and the README carries the same table.

A fifth example, `truncating_credit_system.py`, is the only one that comes back **violated**, and
that is its whole job: the other four pass, so before it a reader who ran every shipped example
never saw the tool report a breach. It imports `reasonsmith.demo`'s `TruncatingCreditSystem` rather
than reimplementing it — that system's output is also the README transcript, `docs/example-output.md`
and the committed dossier, so a second copy would be a fourth thing to keep in step. It checks the
clause's *content* duty (`..._principal_reasons_complete`), never the *form* duty its siblings
check, which this same system satisfies. `reasonsmith check --help`'s epilogue names it first;
`test_a_shipped_example_reports_a_violation_and_help_names_it` in `tests/test_adoption_surface.py`
pins both halves. The README's first screen after the badges is that run and its transcript, then
[`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) — the theory sections live below
the demonstration and nothing may move them back above it.

They live under `src/` and not under `docs/` for one reason: **a documented command must run for
someone who only ran `pip install reasonsmith`**, and no wheel carries `docs/`. So a command a
document prints names either a shipped module (`python -m reasonsmith.examples.<name>`,
`--system-module reasonsmith.examples.<name>:system_under_test`) or a file inside the installed
package, whose directory `python -m reasonsmith.examples` prints — which is why the README's
sample-log command carries a `$(…)` substitution and why `docs/build_readme_transcripts.py`
expands that one substitution before running the command in-process. A new data file the
documentation names needs a pattern in `pyproject.toml`'s `package-data`; a `.py` module ships by
being a module. `tests/test_packaged_examples.py` builds the wheel and reads what is in it,
because this defect once shipped invisibly: from a checkout every missing file was right there.

`docs/language-model.md` and the fourth adapter
`src/reasonsmith/examples/language_model_notices.py` are a
different axis, and the filename `three-systems.md` was left alone rather than made false. A
language model you can call adds **no rung** — it sits at `probed` beside the probabilistic
scorer — so do not write "four systems, four rungs". What it demonstrates is which duties a system
can be answered on at all: run against the whole `ecoa` pack it is `observed`, `probed` and
`unattainable` in one report, the last on `ecoa_reg_b_1002_9_b_2_principal_reasons_complete`,
whose `artifact_logs_deleted_reason_count` is measured from an inference artefact a decoder has
none of. The adapter takes one `complete(prompt: str) -> str` — never a vendor SDK, never a
network call — behind a deterministic stub, because `tests/test_docs_language_model.py` pins the
transcript byte-for-byte and asserts the ceiling on the mechanism: `logic()` is `None`, and the
adequacy duty is never downgraded to the presence check sharing its clause.

`docs/nesyarena-conformance-report.md` is the third generated document, and the only run against a
real system rather than a demonstration fixture: `docs/build_nesyarena_report.py` drives the five
`nesyarena.suts.registry()` provenances over generated ground programs against the GDPR, EU AI Act
and ECOA packs, and `test_nesyarena_report_matches_the_builder` holds the committed file to it
byte-for-byte. Anything that moves `render_text`'s wording, the nesyarena version or the builder's
own constants means regenerating with `python docs/build_nesyarena_report.py`. Like
`docs/report.html`, it names its build command and deliberately carries no commit hash; reproducibility
is owned by the byte-for-byte builder test, so do not add a hash back. Its adapter declares only
signals a provenance genuinely emits, so a set of pack signals is deliberately undeclared — the
census and the count live in `docs/findings-nesyarena.md`, which pins them — and
neither a regulatory class nor a decision domain is declared — these systems decide graph
reachability and Sudoku validity, so there is nothing to declare; the resulting unattainable and
not-applicable verdicts are the finding, not a gap to close, and naming a domain to make the ECOA
rows evaluate again would put finding 3's false positive back by hand.
`docs/findings-nesyarena.md` is the written account of that report, held to it by
`tests/test_findings_nesyarena.py`: every figure the prose quotes is derived from the run the
builder drives — the report, the declared/undeclared signal census, the per-formalism requirement
census — and a failure names the figure and what to regenerate, so a pack change that moves a
count fails the build until the prose is re-derived. Two sharp edges: the pack loader refuses a
`formalism` that does not match a requirement's spec, so pin breaks must come from the builder's
census or the document, never from a duty reclassification; and historical claims (the first
run's 11 requirements and 8 signals, the pre-domain-gate ECOA column of 8 satisfied / 2 violated
/ 5 unattainable) are not derivable and are verified against git history instead.

`docs/semantics.md` states what each verdict means and what it does not, and every claim in it names
the test that fails if the claim becomes false. `tests/test_docs_semantics.py` checks that mapping,
so **renaming or deleting a test breaks the build if that test is named there** — update the
document in the same commit. It is also where a claim the code cannot support belongs: report the
gap in the document rather than describing a tool that does not exist.

## The web home and the install surface

The live home is `https://reasonsmith.dev` (landing) with the conformance dossier at
`https://reasonsmith.dev/report.html`; the old `eduardstan.github.io/reasonsmith` Pages URL is
superseded and nothing should reintroduce it. `reasonsmith` is published on PyPI — the
README's Quick Start and *Dependencies & PyPI* paragraphs own that claim and the install
commands, and this file names no version, because one written here goes stale at the
next release. The forbidden string appears here deliberately:
this paragraph is the statement of the rule, and a rule that cannot name what it forbids
is not a rule — any repository-wide check for it must exclude this file.

The release discipline lives in `CONTRIBUTING.md`, *Versioning and Releases*, and is enforced by
`tests/test_release_discipline.py` (the version lives in **four** places — the pyproject
`version`, the topmost released `CHANGELOG.md` heading, `__version__` in
`src/reasonsmith/__init__.py` and `version` in `CITATION.cff`, the one the guard originally
missed — and they must agree; no tracked markdown may carry a bare `#NN` outside code and
anchors) and by the tag check in `.github/workflows/publish.yml`
(a release whose tag is not `v` plus the pyproject version never builds). Bumping the version
means closing `[Unreleased]` and opening a fresh one in the same change. The same module pins
prose counts against the shipped tree — the README's pack and engine counts, `ROADMAP.md`'s
"Current state, for scale" line, and the same claims where the prose restates them spelled out —
derived at test time from `spec.list_packs()` and the modules under `engines/` (never
`BUILTIN_ENGINE_NAMES` alone, which once missed an entry). A new pack, engine or requirement
means updating those sentences in the same change, or the pin fails.

## The front door

Before editing the CLI, read the maintenance contracts in `src/reasonsmith/cli.py`'s module
docstring. README, "The CLI", owns user-facing usage, and `docs/authoring-packs.md` owns the
pack-authoring rules.

`ROADMAP.md` is the public backlog and the one document that may state what is *missing*: four
numbered objectives, each citing the committed document that names the gap, with a measurable
outcome that fails today and its dependencies. Nothing goes on it that no document already states —
find the gap in `docs/refinement.md`, `docs/semantics.md` or `docs/findings-nesyarena.md` first, or
write it there first. Closing an objective means deleting the sentence it quotes from that source
document in the same commit; the README's four-audience section ("Who could use this, and what is
missing first") cites the same gaps and goes stale with it. `CONTRIBUTING.md` defers its roadmap
table here rather than keeping a second list.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
