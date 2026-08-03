# The refinement record: from a clause of law to a formal property

Every requirement in this repository was written by someone reading a clause of law and deciding
what formula stands for it. That step — refinement — is where the legal meaning is either preserved
or quietly lost, and it is the step no pack file records. `docs/authoring-packs.md` documents the
*fields* of a requirement. This document is the record of the *judgement*: for each of the 28 shipped
requirements, the clause, the duty it states, the property it became, and — the column that matters —
what the refinement deliberately did not capture.

**What this document is not.** It does not restate what a verdict means. `docs/semantics.md` is the
authority on that, one engine at a time, with every claim naming the test that fails if it becomes
false. Where the fourth column below leans on a limit that document already states, it cites the
section rather than paraphrasing it. Where this document and `docs/semantics.md` appear to disagree,
`docs/semantics.md` is right.

`tests/test_docs_refinement.py` reads the shipped packs and fails if a pack gains a requirement this
record does not name, or if this record names one no pack ships.

---

## How to read column four

A `satisfied` verdict is a statement about a formula, never about a duty. reasonsmith does not
determine whether a legal duty is discharged — that is in `reasonsmith.report.LIMITS`, it travels on
every emitted report, and `docs/semantics.md` §5 states it. The distance between the formula and the
duty is different for every requirement, and column four is where it is written down.

Four kinds of gap recur, and naming them once keeps the table short:

- **Presence is not adequacy.** Twenty-one of the twenty-eight shipped duties are `record` duties: a
  conjunction of `present(signal)` atoms, and a twenty-second is the same presence check quantified
  over the trace. A reason field containing `"n/a"` is present
  (`docs/semantics.md` §3, *record*). Every clause whose content is an adjective — *meaningful*,
  *suitable*, *concise, complete, correct and clear*, *sufficiently detailed*, *adequate* — meets a
  check that can see only whether a field is non-empty.

  **The GPAI pack is where this ratio got worse, and the eight rows below say why that was the right
  trade for those eight duties and not a licence to keep making it.** Article 53(1) and Article 55(1)
  are duties to *produce artefacts* — draw up documentation, put a policy in place, document an
  evaluation, report an incident. For a duty of that shape presence is the **correct** refinement
  rather than a proxy: a duty to draw up a document is discharged by the document existing, and there
  is no stronger property to write. What presence does not reach is the adequacy words the same
  clauses attach to those artefacts — *at a minimum, the information set out in Annex XI*,
  *sufficiently detailed*, *reflecting the state of the art*, *adequate* — and each of those is
  named in its own row. A reader who takes "the documentation exists" for "the documentation is
  adequate" has read a verdict this pack does not offer.

  **Two duties are no longer among them, and each escapes for its own reason.**
  12 CFR 1002.9(b)(2) names two statements that are *insufficient*, so
  `ecoa_reg_b_1002_9_b_2_specific_reasons` can check that neither was made without anyone here
  defining *specific* (`contains()`, `docs/semantics.md` §2). That is not a general escape from
  this gap: it is available exactly where a clause supplies its own negative constraint, and it
  establishes only that a named insufficiency was avoided — never that what was said instead was
  adequate. The same clause's `ecoa_reg_b_1002_9_b_2_principal_reasons_complete` escapes by
  measurement rather than by wording: it compares the reasons a notice states against the reasons
  the decision's own inference used, counted by the reason-deletion certificate over an artefact
  the system exposes (`docs/semantics.md` §3, *certificate*). That escape is available only to a
  system that can be opened up, and every system that cannot is reported `unattainable` on it —
  never returned to the presence check, which would answer a different question under the same
  duty's name.
- **The trace is a sample.** An `observed` or `record` verdict covers exactly the records supplied,
  and nothing establishes that they are representative, complete or unfiltered
  (`docs/semantics.md` §1). Any clause whose duty runs over the lifetime of a system —
  record retention, continuous monitoring — is met by a check over one supplied run. One escape
  exists and reaches only one shape of duty: an `always(f)` whose `f` is a property of a single
  decision is proved over every input a system's exposed logic admits, so the verdict covers every
  trace that system can emit rather than the sampled one (`docs/semantics.md` §3, *`proved`, over a
  trace*). It is still a claim about the logic the system exposed, and a system that cannot expose
  any is left with the sample.
- **Organisational facts are outside every engine.** A controller's legal basis, a staffed appeals
  desk, a signed instruction manual: no decision record witnesses these. Where a clause turns on
  one, the property reads a flag the system sets about itself, and reasonsmith checks what a system
  says, not whether it was honest (`docs/semantics.md` §3, *the assumption all seven share*).
- **The property's reach is not the clause's scope.** Most clauses below are triggered — by adverse
  action, by a decision under Article 22(2)(a) or (c), by the system being high-risk. A property
  evaluated over every record in a trace is checked outside that trigger too. Two axes of a
  clause's scope are modelled — the regulatory class (`scope`, used by six of the nineteen duties)
  and the decision domain (`domains`, used by six) — and both are gates about the *system*. A
  trigger *inside* a decision is not a gate at all: the two 12 CFR 1002.9(b)(2) duties carry their
  own in the property, at the price of being reported *not evaluated* where it never fires.

## Two axes of reach are modelled, and the trigger is still not one

A duty reaches a system when it passes two gates. `scope` is a *regulatory class* from the EU AI
Act's own five-member vocabulary; fourteen duties use it — six `high-risk` (the four in
`packs/eu_ai_act.toml` and the two Article 12 and 13 rows of Table 7) and the eight
`general-purpose` duties of `packs/gpai.toml`, which are the first requirements in this repository
to use that class at all. `domains` is
the *kind of decision* the duty is about — the ECOA rows and the Table 7 ECOA and FDA rows use it,
six duties in all — and it is
matched by intersection against what the system declares. A system that declares neither is reported
`not_applicable` on every duty that limits either, never `satisfied`, and reasonsmith infers neither
(`docs/semantics.md` §4).

The domain gate closed a specific defect. An adverse-action notice duty under 12 CFR 1002.9 used to
reach a graph-reachability benchmark that issues no credit and notifies nobody and report it
`satisfied`; that was not hypothetical, it happened in the run behind
`docs/findings-nesyarena.md`, finding 3, and the only hint in the output was an unattainable verdict
on a *different* requirement, arriving for the wrong reason. Those four ECOA duties now come back
not applicable against all five of that run's systems.

**What the gate still does not do, and every row in the ECOA and GDPR tables below inherits it.**
It is stated once, here, rather than nineteen times:

- **The vocabulary is this repository's, not any regulation's.** `DECISION_DOMAINS` is a coarse,
  openly-authored list, and it is wrong somewhere: no statute defines a list of decision domains,
  the GDPR is not domain-limited at all, and the AI Act works from Annex III use-cases. Placing
  `ecoa_reg_b_1002_9_a_2_written_statement` in `consumer-credit` is *this pack author's* reading of
  the clause, published in the pack description as such (`docs/authoring-packs.md`, *the
  decision-domain vocabulary is yours, not the regulation's*). A verdict of not applicable is
  therefore a statement about a classification someone here made, not a finding that Regulation B
  does not govern a particular lender.
- **What the system declares is a self-declaration.** Nothing checks that a system that says
  `consumer-credit` issues credit, the same way nothing checks the flags of the Article 22(2) bases
  (`docs/semantics.md` §3, *the assumption all seven share*). The gate stops a duty reaching a system
  that said nothing; it does not stop one that said the wrong thing.
- **The trigger inside a decision is still not modelled *as a gate*, and that is the larger
  remaining gap.** 12 CFR 1002.9 is triggered by *adverse action having been taken*, not by the
  creditor being in consumer credit. A domain declaration puts the whole trace within the clause's
  subject matter and the property is then evaluated over every record in it, approvals included.
  Every "the clause is triggered, the property is not" note in column four below is untouched by
  this gate — see the (a)(2) row in particular.

  One trigger *is* now carried, and only because the property language could express it, not
  because a gate learned to. 12 CFR 1002.9(b)(2) governs the statement of reasons *required by
  paragraph (a)(2)(i)*, so the (b)(2) property is an implication whose antecedent is
  `present(artifact_logs_reason_explanation)`, and a creditor lawfully on the disclosure branch is
  no longer reported violated. That is worth having and it is not the gate the bullet asks for:
  where the antecedent holds nowhere in the evidence an engine had, the duty is reported **not
  evaluated**, naming the trigger that never fired and the domain that was searched
  (`docs/semantics.md` §4). That is the truthful report of a duty nothing was learned about, and it
  is still not the truthful verdict — `not applicable`, per decision, is, and a real per-decision
  applicability gate would need a `not_applicable` verdict a *record* can carry, which is a change
  to the result model rather than to a pack.

## One of the four signal categories is empty, and no sourced statute fills it

`docs/authoring-packs.md` names four Section 6.3 signal-name prefixes. Three are exercised by the
shipped packs — `provenance_` by fourteen distinct signals, `artifact_logs_` by nineteen,
`scope_statements_` by five — and the fourth, `stability_signals_`, by **none**. The demonstration
log `src/reasonsmith/examples/sample_decisions.jsonl` even emits `stability_signals_artifact_drift`,
a number no duty in any pack reads. The category is empty on purpose, and this is the reason.

**No statute this repository can source obliges stability, drift or consistency over time as a
property of a decision record.** Four candidates were read against the live official text and
rejected, each for a reason that is about the *subject* of the duty rather than about the
expressiveness of the property language:

- **EU AI Act Article 15(1)** — high-risk systems "shall be designed and developed in such a way
  that they achieve an appropriate level of accuracy, robustness, and cybersecurity, and that they
  perform consistently in those respects throughout their lifecycle". The consistency is real, and
  its subject is the *design and development* of a system over its lifecycle. No decision record
  witnesses it, and a trace of records is a sample of one run (*the trace is a sample*, above).
- **EU AI Act Article 15(3)** — accuracy levels and metrics "shall be declared in the accompanying
  instructions of use". This is the closest of the four to expressible, and it is still not this
  duty: its subject is a document that accompanies the system, not the decision record, and the
  only thing reasonsmith could check is that some accuracy number appears in each record — which
  Article 15(3) does not require of any record. Writing that would be inventing a duty to fill a
  column.
- **EU AI Act Article 72(1)–(2) and Article 26(5)** — the provider "shall establish and document a
  post-market monitoring system", which "shall actively and systematically collect, document and
  analyse relevant data … on the performance of high-risk AI systems throughout their lifetime";
  the deployer "shall monitor the operation of the high-risk AI system on the basis of the
  instructions for use". Both bind an organisation over time. They are the paradigm case of
  *organisational facts are outside every engine* (above): the artefact that discharges them is a
  monitoring system, not a decision.
- **GDPR Recital 71 and Article 5(1)(d)** — the Recital's error-minimisation sentence is already
  refined, by `gdpr_recital71_error_risk_minimised`, and it is about the error in *one* decision,
  not about drift between decisions; the Recital carries no regular-checking language (it was read
  in full for it, and there is none). Article 5(1)(d) obliges personal data to be "accurate and,
  where necessary, kept up to date" — a duty about the input data, not about the stability of a
  model or of an explanation.

Regulation B was read too and has nothing of this shape: 12 CFR 1002.9 is triggered by an adverse
action taken on one application, and the record-retention rule of 12 CFR 1002.12 obliges records to
be *kept*, not to stay consistent.

**What would change the answer.** Any one of these, and none of them is in this repository's gift:

1. A statute — a delegated act, a harmonised standard given legal effect, or a supervisory
   authority's binding guidance — that obliges a *per-decision* stability figure, so the duty's
   subject is the record reasonsmith reads. Article 15(2)'s benchmarks and measurement
   methodologies are the plausible route to one, and none exists yet.
2. A result model in which a duty can be evaluated against an artefact that is not a decision
   record — a monitoring report, a model card, an instructions-of-use document. Article 72 would
   then have somewhere to land. That is a change to what the tool reads, not to a pack.
3. A verdict that can be a property of a *trace* rather than of the records in it. Drift is a
   relation between decisions; every property here is evaluated per record and then quantified.

Until then, a duty written to use `stability_signals_` would read a number the system declares about
itself and grade the system on its own homework, and it would do so without a clause requiring the
number. This repository already carries one duty that reads a self-declared figure —
`gdpr_recital71_error_risk_minimised`, whose bound is the decision's own margin rather than
an invented threshold, and whose weakness is named in its row below. A second one, backed by no
clause, would be worse than an empty category. **The honest state of the taxonomy is three
categories used and one empty**, and an author who finds this section should extend it with the
clause they rejected rather than delete it with a duty they invented.

---

## GDPR (Regulation (EU) 2016/679) — `src/reasonsmith/packs/gdpr.toml`

All five duties carry `scope = ""` and `domains = []`. The empty domain list is a classification
and not an omission: Article 22 governs a solely-automated decision with legal or similarly
significant effects *whatever the decision is about*, so these duties reach every system they are
run against, including one that has declared no domain. Limiting them would be this pack author
narrowing a regulation that does not narrow itself.

| The clause | The informal duty | The formal property | What was deliberately not captured |
|---|---|---|---|
| GDPR Article 22(1)<br>`gdpr_art22_1_automated_decision_prohibition` | A person has the right not to be subject to a decision based solely on automated processing that produces legal or similarly significant effects. | `record`: `present(artifact_logs_decision_record) and present(provenance_active_exceptions)` | The prohibition itself. This property witnesses that the system keeps a decision record and records which exceptions were active — it is a logging duty standing in for a substantive one. A system that makes exactly the decision Article 22(1) protects against satisfies it, provided it logs that decision. Nothing here witnesses the data subject's right, its exercise, or the controller's response. The prohibition is carried by the next row, and only against a system that exposes its rules. |
| GDPR Article 22(1)<br>`gdpr_art22_1_no_prohibited_decision_for_any_input` | Same clause, read as a constraint on the decision rules: no admissible input may yield a solely-automated, significantly-affecting decision without an Article 22(2) basis, and under points (a) and (c) without the Article 22(3) route open. | `logical`: `(artifact_logs_solely_automated and artifact_logs_significant_effect) -> ((provenance_basis_contract or provenance_basis_union_or_member_state_law or provenance_basis_explicit_consent) and ((provenance_basis_contract or provenance_basis_explicit_consent) -> artifact_logs_human_intervention_route))` | Whether any of those flags is true of the world. Each Article 22(2) basis is a legal fact about the controller — a contract that is necessary, a Union or Member State law that authorises, consent that is explicit and freely given — and the property reads a Boolean the system sets about itself. The pack description says so; `docs/semantics.md` §3 (*proved*) states that a proof is a claim about the logic exposed through `logic()`, not about the deployed artifact. Also not captured: Article 22(3)'s *suitable measures* collapse to one flag, so a route that is unstaffed, untimely or powerless to change the decision reads the same as a real one; Article 22(2)(b)'s requirement that the authorising law itself lay down safeguards is not modelled; Article 22(4)'s restriction on special-category data is not formalised anywhere in this pack. The implication is spelled with `->` rather than the equivalent `Implies(...)`: the two are the same property to every engine that parses the spec, and only the arrow is renderable by the rtamt monitor that now reads this duty off a trace, so the prefix form would leave it not evaluated against a log for a reason having nothing to do with the clause (`docs/semantics.md` §3.5). |
| GDPR Article 22(3)<br>`gdpr_art22_3_safeguards_human_intervention` | The controller must implement suitable measures safeguarding the data subject — at least human intervention, expressing a point of view, and contesting the decision. | `record`: `present(artifact_logs_decision_record) and present(scope_statements_local_vs_global)` | All three named rights. Neither conjunct witnesses human intervention, a point of view or a contest; `scope_statements_local_vs_global` is a statement of explanation scope, chosen by the pack author as a proxy for *the safeguard can say what this decision rested on*. That proxy is editorial and the clause does not name it. *Suitable* is an adequacy judgement no engine here makes. And the clause is limited to cases under points (a) and (c) of Article 22(2), while the property is checked against every record in the trace — its reach is wider than the clause's. |
| GDPR Recital 71<br>`gdpr_recital71_meaningful_explanation` | Suitable safeguards should include specific information, human intervention, a point of view, an explanation of the decision reached, and a challenge to it. | `record`: `present(artifact_logs_reason_explanation) and present(scope_statements_explanation_scope) and present(provenance_model_version)` | *Meaningful*, which is the entire content of the recital. Presence sees a non-empty string; `"n/a"` is present (`docs/semantics.md` §3, *record*). Nothing checks that the explanation is about the decision it accompanies, that a lay reader could act on it, or that the model version named is the one that ran. A recital creates no obligation of its own, which is what `binding = false` records — the row is an interpretive reading, not a duty. As above, the reach is every record rather than only Article 22 processing. |
| GDPR Recital 71<br>`gdpr_recital71_error_risk_minimised` | The controller should use appropriate procedures and measures so that inaccuracies are corrected, the risk of errors is minimised, data is secured, and discriminatory effects on the listed protected grounds are prevented. | `temporal`: `always(scope_statements_declared_deviation <= artifact_logs_decision_margin)` | Every limb but one. The property formalises *the risk of errors is minimised* and nothing else: correcting inaccuracies in personal data, security, and the prevention of discriminatory effects on racial or ethnic origin, political opinion, religion, trade union membership, genetic or health status or sexual orientation are not formalised here or anywhere in the shipped packs — **no *distributional* fairness property is checked by any requirement in this repository; the one fairness property that is checked is counterfactual invariance under a single named variable (`ecoa_reg_b_1002_4_a_no_disparate_treatment`), and it cannot see a disparate impact.** That duty is anchored to a disparate-*treatment* clause of Regulation B and not to this recital, for the reason `docs/legal-sources.md` records under Provision 4: the recital's own words are *discriminatory effects*, and effects is the limb a property of a pair of decisions cannot reach. What the error limb itself does and does not claim is stated in full in `docs/semantics.md` §3 (*the first shipped duty that reads a declared approximation error*), including that the deviation is a self-declaration no engine verifies, that the bound is the system's own margin and not a figure the recital states, and that an exact tie is reported satisfied. |

## EU AI Act (Regulation (EU) 2024/1689) — `src/reasonsmith/packs/eu_ai_act.toml`

All four duties carry `scope = "high-risk"`. A system that declares no class is reported
`not_applicable` on all four, and reasonsmith never infers the class (`docs/semantics.md` §4).

| The clause | The informal duty | The formal property | What was deliberately not captured |
|---|---|---|---|
| EU AI Act Article 12(1)<br>`eu_ai_act_art12_1_automatic_logging` | A high-risk system must technically allow automatic recording of events over the system's lifetime. | `record`: `present(artifact_logs_event_log) and present(provenance_model_version)` | *Over the lifetime of the system*, and *automatic*. The check reads the trace supplied for one run — a sample chosen by whoever produced it (`docs/semantics.md` §1) — so retention period, log durability and whether records survive a model update are all outside it. A log hand-assembled for the audit is indistinguishable from an automatically recorded one. Article 12(3)'s minimum content for the logs, and Article 19's retention obligation, are not formalised. This property is byte-identical to the Article 12(2) property below, and the next row records why the two are not told apart. |
| EU AI Act Article 12(2)<br>`eu_ai_act_art12_2_traceability_monitoring` | Logging must enable recording of events relevant to identifying risk situations and substantial modifications, to post-market monitoring, and to Article 26(5) operation monitoring. | `record`: `present(artifact_logs_event_log) and present(provenance_model_version)` | The three limbs, individually and together. The property is byte-identical to the Article 12(1) property, so **no system can satisfy one of these two duties and violate the other** — they cannot come apart in any report, and a reader must not take two agreeing verdicts for two independent checks. *Appropriate to the intended purpose* is an adequacy judgement nothing here makes. The overlap is **recorded rather than repaired, and this is the reasoning.** What separates the two clauses is *relevance*: 12(1) asks that events be recorded at all, 12(2) that the events recorded be the ones relevant to identifying a risk situation or a substantial modification, to post-market monitoring under Article 72, and to Article 26(5) operation monitoring. Nothing in the Section 6.3 signal vocabulary (`sut.CAPABILITY_TAXONOMY`) stands for the relevance of a logged event to any of those three ends, and no per-decision record witnesses it — relevance is a property of a logging *design* judged against an intended purpose, not a field a decision carries. A signal minted for it here would be this pack author's reading of the Article shipped as the Article's, the same objection `docs/authoring-packs.md` (*a number in a spec*) makes to an invented threshold, and it would report every system that does not declare the invented signal unattainable on 12(2) — trading a visible overlap for an invisible one. The pack description carries this so a reader of the tool's own output meets it too. |
| EU AI Act Article 13(1)<br>`eu_ai_act_art13_1_transparency_deployers` | Operation must be sufficiently transparent for deployers to interpret the output and use it appropriately. | `record`: `present(scope_statements_explanation_scope) and present(artifact_logs_reason_explanation) and present(provenance_model_version)` | *Sufficiently transparent to enable deployers to interpret* — a claim about a human reader's comprehension, which no engine here evaluates. Presence of a scope statement is not comprehension of it. The clause's second sentence ties the required degree of transparency to compliance with the provider's and deployer's Section 3 obligations; none of those obligations is in this pack, so the cross-reference is not modelled. |
| EU AI Act Article 13(2)<br>`eu_ai_act_art13_2_instructions_for_use` | The system must be accompanied by instructions for use containing concise, complete, correct and clear information, relevant, accessible and comprehensible to deployers. | `record`: `present(scope_statements_approximation_vs_guarantee) and present(provenance_constraint_set)` | Every adjective in the clause — concise, complete, correct, clear, relevant, accessible, comprehensible — all seven of which are adequacy judgements presence cannot see. More structurally: instructions for use are a *document accompanying the system*, not a per-decision record, and this property reads per-decision signals. A system shipping no instruction manual at all satisfies it if its decision records carry those two fields. Article 13(3)'s enumerated contents (provider identity, performance characteristics, human oversight measures, expected lifetime, and the rest) are not formalised. |

## EU AI Act, general-purpose AI models (Articles 53 & 55) — `src/reasonsmith/packs/gpai.toml`

All eight duties carry `scope = "general-purpose"` and `domains = []`. They are the first
requirements in this repository to use the `general-purpose` class, so until this pack shipped the
class gate had a member no shipped duty exercised. The empty domain list is a classification and not
an omission: a general-purpose AI model is by definition not a model of a particular kind of
decision, and limiting these duties to a decision domain would be this pack author narrowing an
Article that does not narrow itself.

**One caveat governs the whole table and is stated once here.** Every property below is a presence
conjunction, and for these clauses that is the right refinement rather than a weak one — Article
53(1) and Article 55(1) are duties to *produce artefacts*, and an artefact duty is discharged by the
artefact existing. But two structural limits ride along with every row and are not repeated in
each. First, **these are duties about a model, and the properties read a decision record.** A
technical-documentation duty is not a per-decision fact; the check is that the records the system
supplies carry the fields, which a system with no documentation at all can do by populating fields.
Second, **the systemic-risk trigger is not modelled.** Article 55 applies only to a general-purpose
model *with systemic risk*, which Article 51 defines by high-impact capability and the Article 52
designation procedure. Nothing here decides whether a model has systemic risk: declaring
`general-purpose` reaches all eight duties, so a model without systemic risk is judged against the
four Article 55 duties too. That is the same class of gap as *the property's reach is not the
clause's scope* above, at the level of the Article rather than the decision, and closing it would
need a sixth regulatory class the Act's own five-member vocabulary does not supply.

| The clause | The informal duty | The formal property | What was deliberately not captured |
|---|---|---|---|
| EU AI Act Article 53(1)(a)<br>`eu_ai_act_art53_1_a_technical_documentation` | The provider must draw up and keep up-to-date the model's technical documentation, including its training and testing process and the results of its evaluation, containing at a minimum the information set out in Annex XI. | `record`: `present(provenance_technical_documentation) and present(artifact_logs_training_and_testing_process) and present(artifact_logs_model_evaluation_results)` | **Annex XI, entirely.** The clause's operative content is *which* information the documentation must contain — Annex XI's list of tasks, architecture, parameter count, training data provenance, energy consumption and the rest — and presence sees only that three fields are non-empty. Nothing here reads Annex XI, and no requirement in this repository formalises any item of it. *Keep up-to-date* is not captured either: presence has no notion of when the documentation was written, so documentation four model versions stale reads the same as current documentation, and the trace is one sample in any case (`docs/semantics.md` §1). *Upon request, to the AI Office and the national competent authorities* is a duty to disclose to a named recipient; no signal witnesses a disclosure ever having been made to anyone. |
| EU AI Act Article 53(1)(b)<br>`eu_ai_act_art53_1_b_downstream_documentation` | The provider must draw up, keep up-to-date and make available information and documentation to downstream providers integrating the model, enabling them to understand its capabilities and limitations, and containing at a minimum the elements of Annex XII. | `record`: `present(provenance_downstream_provider_documentation) and present(scope_statements_capabilities_and_limitations)` | **Annex XII, and point (i)'s comprehension standard.** As with Annex XI above, no element of Annex XII is read by anything here. Point (i) asks that the documentation *enable providers of AI systems to have a good understanding* — a claim about a downstream human reader, the same adequacy judgement `eu_ai_act_art13_1_transparency_deployers` cannot make, and `scope_statements_capabilities_and_limitations` present means a capabilities-and-limitations field is filled, not that any downstream provider understood it. *Make available* is not captured: a document that exists and is disclosed to nobody satisfies this property. The clause's *without prejudice to* proviso on intellectual property and trade secrets is not modelled at all, so this property cannot distinguish documentation lawfully redacted under it from documentation that is simply missing content. |
| EU AI Act Article 53(1)(c)<br>`eu_ai_act_art53_1_c_copyright_policy` | The provider must put in place a policy to comply with Union copyright law, and in particular to identify and comply with a rights reservation expressed under Article 4(3) of Directive (EU) 2019/790, including through state-of-the-art technologies. | `record`: `present(provenance_copyright_policy) and present(provenance_rights_reservation_identification)` | **Whether the policy is honoured in practice**, which is the whole substance of *comply with*. A policy document existing is evidence that a policy was written, and nothing in a decision record witnesses a single training item having been excluded because a rights holder reserved. Whether the identification uses *state-of-the-art technologies* is an adequacy judgement no engine here makes, and it is one that changes with the state of the art, so even a threshold would go stale. The cross-reference into Article 4(3) of Directive (EU) 2019/790 — what counts as a reservation expressed in an appropriate manner — is not modelled; that Directive is not a source recorded in `docs/legal-sources.md` and nothing here quotes it. |
| EU AI Act Article 53(1)(d)<br>`eu_ai_act_art53_1_d_training_content_summary` | The provider must draw up and make publicly available a sufficiently detailed summary of the content used for training, according to a template provided by the AI Office. | `record`: `present(provenance_training_content_summary) and present(provenance_training_content_summary_template)` | **`Sufficiently detailed`, which is the clause's only quality standard and the reason this row is the sharpest instance of *presence is not adequacy* in the pack.** A summary reading `"web data"` is present. Nothing here reads the summary's contents, compares it against the training corpus, or has any notion of how much detail is enough — and inventing one would be this pack legislating a standard the Act leaves to the AI Office (`docs/authoring-packs.md`, *a number in a spec*). *According to a template provided by the AI Office* is reached only as far as a template being named: `provenance_training_content_summary_template` present means the record cites some template, not that it is the AI Office's, not that the summary conforms to it, and the AI Office template is not a document this repository has retrieved or quoted. *Make publicly available* is not captured — nothing witnesses publication — so a summary held privately satisfies this property. |
| EU AI Act Article 55(1)(a)<br>`eu_ai_act_art55_1_a_model_evaluation` | A provider of a model with systemic risk must perform model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing with a view to identifying and mitigating systemic risks. | `record`: `present(artifact_logs_model_evaluation_results) and present(artifact_logs_adversarial_testing_record)` | **`Reflecting the state of the art`, and `standardised protocols and tools`.** The clause's demand is about the *method* of the evaluation, and presence sees only that a result and a testing record exist. No engine here knows which protocols are standardised, which are current, or whether the adversarial testing performed was more than a single benign prompt; a record of adversarial testing is evidence that testing was documented and nothing about its strength. *With a view to identifying and mitigating systemic risks* is a purpose clause, and a purpose is not a field. The clause's cross-reference to Article 51's definition of systemic risk is untouched, per the caveat above the table. |
| EU AI Act Article 55(1)(b)<br>`eu_ai_act_art55_1_b_systemic_risk_assessment` | Such a provider must assess and mitigate possible systemic risks at Union level, including their sources, stemming from development, placing on the market, or use of the model. | `record`: `present(artifact_logs_systemic_risk_assessment) and present(artifact_logs_systemic_risk_mitigation)` | **Whether any risk was found, and whether any mitigation worked.** Both conjuncts are records of an activity, so an assessment concluding "no risks" and a mitigation field reading `"n/a"` satisfy this property (`docs/semantics.md` §3, *record*). *At Union level* and *including their sources* name the scope and depth the assessment must reach, and presence sees neither. The three named origins — development, placing on the market, use — are not distinguished by any signal, so an assessment covering one of the three is indistinguishable from one covering all three. There is no fairness, safety or capability property anywhere in this repository that could stand behind this row: the single fairness property that ships is counterfactual invariance under one named variable in a consumer-credit duty, it is a property of a pair of decisions and not of a model's systemic risk, and it sees no disparate impact (GDPR Recital 71 row above). |
| EU AI Act Article 55(1)(c)<br>`eu_ai_act_art55_1_c_serious_incident_reporting` | Such a provider must keep track of, document, and report — without undue delay — relevant information about serious incidents and possible corrective measures to the AI Office and, as appropriate, national competent authorities. | `record`: `present(artifact_logs_serious_incident_record) and present(artifact_logs_serious_incident_report) and present(artifact_logs_corrective_measures)` | **`Without undue delay` — the timing limb — and the decision to leave it out is the deliberate one in this row.** A `temporal` property could bound a reported latency the way `ecoa_reg_b_1002_9_a_1_timing_of_notice` bounds a notification latency, and it is not written here because it could not be written honestly. 12 CFR 1002.9(a)(1) supplies its own numbers, 30 and 90 days, so the property repeats the clause's figures; Article 55(1)(c) supplies none. That leaves two ways to write it and both are refused for reasons this repository already states: a constant chosen here would be a pack author's figure presented as the Act's (`docs/authoring-packs.md`, *a number in a spec*), and a `systemic_risk_report_deadline_days` signal the provider declares about itself would make the verdict a restatement of the system's own opinion of its own deadline — the objection `docs/authoring-packs.md` raises against a `reason_is_specific` flag, *never ask the system to grade itself*. The `gdpr_recital71_error_risk_minimised` escape — bound the quantity by another quantity the record supplies — has no counterpart here: there is no second, independently-meaningful duration in a serious-incident record to compare a reporting latency against. So the duty is written on its three artefact limbs and the timing limb is recorded as not captured, which means **a provider that reported a serious incident a year late is `satisfied` on this requirement.** Also not captured: *serious incident* is defined in Article 3(49) and nothing here checks that what was logged meets that definition, an incident that was never noticed leaves no record and so cannot be missed by a presence check, and the two named recipients — the AI Office, and national competent authorities *as appropriate* — are not distinguished, so a report to neither is indistinguishable from a report to both. |
| EU AI Act Article 55(1)(d)<br>`eu_ai_act_art55_1_d_cybersecurity_protection` | Such a provider must ensure an adequate level of cybersecurity protection for the model and for the physical infrastructure of the model. | `record`: `present(provenance_cybersecurity_protection) and present(provenance_physical_infrastructure_protection)` | **`Adequate`, and every control either statement describes.** This is a duty about the security of a system, and the property reads two declared statements — no engine in this repository tests a control, probes a boundary, or verifies a claim about infrastructure, and none is proposed. So the row establishes that the provider said something about cybersecurity and said something about physical infrastructure, on the same standing as every other self-declaration here (`docs/semantics.md` §3, *the assumption all five share*): reasonsmith checks what a system says, not whether it was honest. *Adequate* is an adequacy judgement, and it is one this repository is structurally unable to make even in principle, because the evidence would be an audit of a deployment rather than a record of a decision. |

## ECOA / Regulation B (12 CFR §§ 1002.4, 1002.9) — `src/reasonsmith/packs/ecoa.toml`

All five duties carry `scope = ""` — Regulation B knows nothing of the AI Act's classes — and
`domains = ["consumer-credit"]`. A system that declares no decision domain is reported
`not_applicable` on all five, and the limits of that classification are in *two axes of reach are
modelled* above.

| The clause | The informal duty | The formal property | What was deliberately not captured |
|---|---|---|---|
| 12 CFR 1002.9(a)(1)<br>`ecoa_reg_b_1002_9_a_1_timing_of_notice` | A creditor must notify an applicant of action taken within 30 days of a completed application, an incomplete application, or an existing account — or within 90 days of a counteroffer the applicant did not accept. | `temporal`: `always(present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))` | When the clock started. The clause counts from three different events; the property reads one latency number the system computes about itself, so which event it was measured from is the system's own claim and no engine checks it. The paragraph (ii) exception — *unless notice is provided in accordance with paragraph (c)* — is not modelled, so a lawful incomplete-application notice under 1002.9(c) is still held to the 30-day bound. `artifact_logs_counteroffer_not_accepted` is read under the flag encoding of `docs/semantics.md` §2, where any present non-numeric value becomes true, so a record that carries prose in that field takes the 90-day branch. Both numbers are the clause's own, not this pack's (`docs/authoring-packs.md`, *a number in a spec*). |
| 12 CFR 1002.9(a)(2)<br>`ecoa_reg_b_1002_9_a_2_written_statement` | An adverse-action notification must be in writing and contain the action taken, the creditor's name and address, the ECOA § 701(a) statement, the administering federal agency's name and address, and either specific reasons or a disclosure of the right to obtain them. | `temporal`: `always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))` | Four of the five enumerated contents, unchanged: the creditor's name and address, the § 701(a) statement and the federal agency's details are not represented by any signal, and *in writing* is not modelled. What the disjunction now captures is only that *one of* the two branches left a record; **which** branch was lawful for that notification is not checked, and nothing here reads point (ii)'s own contents — the 30-day and 60-day windows it names, or the name, address and telephone number the disclosure must carry, none of which has a signal. `artifact_logs_right_to_reasons_disclosure` is present when a field is non-empty, so a disclosure reading `"see letter"` discharges the branch. Neither branch signal appears in `requires`, because gating one would report a creditor that lawfully took the other unattainable; the cost is stated in the pack description — a system declaring neither branch signal is judged on its trace and reported violated rather than unattainable. Holding the disjunction also costs the short trace: the property is quantified over the trace, so the observed engine needs at least two decisions to establish the sampling period it reasons over, and a log holding exactly one decision is reported not evaluated rather than satisfied or violated — a one-record log was enough while this was a `record` duty (`test_a_single_decision_trace_is_not_evaluated_never_satisfied`). And the whole clause is triggered only when adverse action is taken, while the property runs over every record in the trace, approvals included. |
| 12 CFR 1002.9(b)(2)<br>`ecoa_reg_b_1002_9_b_2_specific_reasons` | The statement of reasons required by (a)(2)(i) must be specific and indicate the principal reasons for the adverse action, and statements resting on the creditor's internal standards or policies, or on the applicant's failure to achieve a qualifying score, are insufficient. | `logical`: `present(artifact_logs_reason_explanation) -> (present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))` | *Specific* and *principal*, still — the property does not define them and no engine here can. What it now checks is the clause's own **negative** constraint, quoted in `verbatim_text` and retrieved in `docs/legal-sources.md`: two named statements that are insufficient. So a reason reading `"failed to achieve a qualifying score"` is reported violated on a plain decision log, with no oracle, no exposed logic and no replay — but a reason reading `"n/a"` or `"credit policy"` is still satisfied, because it is neither of the statements the clause names and inventing a third would be this pack legislating (`test_the_property_does_not_decide_whether_any_other_statement_is_specific`). The check is a substring test with ASCII case folding and nothing more: it does not paraphrase, so `"you did not reach our cut-off"` says the same thing in the world and passes here, and it is not a defence against a creditor wording around it — reasonsmith checks what a system says, not whether it was honest (`docs/semantics.md` §3). One of the three phrases is a reading rather than a quotation: the clause writes `internal standards or policies`, one adjective over two coordinated nouns, and the property distributes it (`test_the_forbidden_wordings_are_the_clauses_own`). **Commentary not formalised:** Official Interpretation comment 9(b)(2)-2 requires the reasons to *relate to and accurately describe the factors actually considered or scored*. Nothing in a decision record witnesses which factors a model actually scored, so checking it needs an oracle over the system's own attributions and is out of scope here. Comments 9(b)(2)-1 and -4 to -7, on how many reasons to give and how to select them from a scoring or judgmental system, are likewise not formalised. **The rest of (a)(2) not formalised:** the four other enumerated contents of the notification — the action taken, the creditor's name and address, the § 701(a) statement and the federal agency's details — and *in writing*, all as recorded in the (a)(2) row above. **Retained from the previous refinement:** `scope_statements_local_vs_global` is the pack author's proxy for a reason being about *this* decision rather than the model in general, and the regulation names nothing of the kind. **The false violation this row used to record is gone.** (b)(2) is triggered only where a statement of reasons is *required by paragraph (a)(2)(i)*, and that trigger is now the property's antecedent, so a creditor lawfully on branch (ii) is no longer reported violated (`test_a_creditor_who_took_the_disclosure_branch_is_not_violated`). The previous entry rejected exactly this repair on the ground that it would be *vacuously satisfied* for a system that gives no reasons at all, and that objection was right about the fact and wrong about the remedy: the vacuity is real, and it was reported `satisfied` — at `proved` against a system exposing its rules, so a creditor whose rules state no reasons on any path was reported *violated* on (a)(2) and clean here in the same report. It is now reported **not evaluated** at every rung, naming the antecedent that never fired and the domain searched (`docs/semantics.md` §4, `test_a_duty_whose_trigger_never_fires_is_not_evaluated_at_any_rung`). What remains unreachable is the *verdict* that case deserves: `not applicable`, per decision, which the result model cannot carry. Modelling the trigger *properly* would still need a signal for the applicant's request under (a)(2)(ii) — a fact about correspondence after the notification that nothing in a decision record witnesses. **Two costs of leaving the record fragment:** the property is an implication, not a conjunction of `present()` atoms, so the record engine cannot name which signal was missing from which decision, and the monitor that answers it needs two samples, so a log holding one decision is reported not evaluated rather than satisfied or violated (`test_a_single_decision_log_is_not_evaluated_never_satisfied`). A one-record log answered this duty before the trigger was formalised. And the clause is triggered by adverse action, while the property runs over every record in the trace, approvals included. |
| 12 CFR 1002.9(b)(2)<br>`ecoa_reg_b_1002_9_b_2_principal_reasons_complete` | The same clause, read on the other half of its first sentence: the statement must indicate the principal reason**s** for the adverse action — all of them, not one of them. | `logical`: `present(artifact_logs_reason_explanation) -> (artifact_logs_deleted_reason_count <= 0)` | **Whether the reasons are the right ones.** The count is measured by `engines/certificate.py`, which enumerates the decision's reasons exactly from the inference artefact the system exposes through `artifact()`, switches each one off in turn, and counts the reasons the system's own answer turns out not to depend on. So the property captures *the notice states every reason this decision's inference used* and nothing beyond it: it does not check that those reasons are correct, that they are the reasons a person would call principal, or that the enumeration found the reasons a different depth bound would find. The threshold is zero and is not this pack's invention — the clause asks for the principal reason(s) for the action taken — but the bound on the enumeration is the artefact's own `exact_depth`, supplied by the system, and a reason lying past it is a reason nothing here looks for — but a bound that found *no* reason at all measures nothing rather than zero, so such a decision buys no verdict here and a run holding one is never reported satisfied. **A reason the probe could not isolate is counted neither way:** where every fact of a reason is shared with another reason it cannot be switched off alone, so dependency is neither shown nor assumed, and the result reports how many such reasons there were (`docs/semantics.md` §3, *certificate*). **What this row exists to remove:** the sibling `ecoa_reg_b_1002_9_b_2_specific_reasons` reads the same clause and answers a weaker question — that a statement is there and is none of the two wordings the clause calls insufficient — and on the demonstration's own decision `APP-1042` it is *satisfied* while four of five legally owed reasons are missing. This duty is what makes that decision report violated, and it is deliberately given a single-rung engine ladder so no trace, no replay and no proof over exposed rules can answer it in the weaker duty's place (`test_the_adequacy_duty_is_never_downgraded_to_the_presence_check`). **The cost:** a system that cannot expose an inference artefact is reported `unattainable` on it — every system a plain decision log describes, including the three shipped adapters of `docs/three-systems.md`, the language model of `docs/language-model.md` and all five nesyarena provenances — so this duty is checkable on strictly fewer systems than any other in the pack. That is the intended trade: unattainable says *this system cannot show me*, and the presence check it replaces said *satisfied*. **The trigger, retained from the sibling row:** the antecedent is the statement of reasons paragraph (a)(2)(i) requires, so a creditor lawfully on the (a)(2)(ii) disclosure branch is not held to it, at the cost of the duty being reported *not evaluated* where no statement exists rather than answered either way (`docs/semantics.md` §4). And the clause is triggered by adverse action, while the property runs over every decision the trace holds, approvals included. |
| 12 CFR 1002.4(a)<br>`ecoa_reg_b_1002_4_a_no_disparate_treatment` | A creditor must not discriminate against an applicant on a prohibited basis regarding any aspect of a credit transaction. | `counterfactual`: `counterfactually_invariant(artifact_logs_decision_record, applicant_prohibited_basis)` | **Every route to a discriminatory outcome that does not run through the named variable.** The property is invariance under one variable holding all others fixed, so a proxy — postcode, employer, an interaction term — is invisible to it: a rule set that never reads the prohibited basis and decides by postcode is `satisfied` here (`test_a_system_accepting_the_protected_variable_and_ignoring_it_is_satisfied` pins the verdict; nothing pins the proxy, because there is nothing to pin). It is a *treatment* property and says nothing about *effects*: disparate impact — the theory Regulation B's effects test and GDPR Recital 71's *discriminatory effects* limb are about — is a fact about outcomes across a population, is not a property of any pair of decisions, and remains unformalised in this repository, as the Recital 71 row above now says in narrowed form. It quantifies over the input space the system's own `constraints` declare, so **a narrowed constraint set narrows the claim**: a system that declares `640 <= credit_score <= 700` is proved fair over that band and over nothing else, and no engine here checks that the declared band is the deployed one (`docs/semantics.md` §3, *counterfactual*). In the degenerate case of that bound — a declaration admitting no pair that differs in the protected variable at all, because the constraints pin it or the rules assign it — the duty is reported *not evaluated* rather than satisfied, since an `unsat` meaning "no pair exists" is not evidence of "no pair disagrees" (`test_constraints_pinning_the_protected_variable_are_not_a_proof`, `test_rules_assigning_the_protected_variable_are_not_a_proof`). At `probed` the claim is narrower still — the pairs the budget names, built from the decisions the system logged and the values the constraints admit, and nothing outside them (`test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach`). **It reaches exactly one variable.** 12 CFR 1002.2(z) lists nine prohibited bases — race, colour, religion, national origin, sex, marital status, age, public-assistance income and the good-faith exercise of a Consumer Credit Protection Act right — and this duty names one signal. A creditor answerable on several is answered here about the one it exposes under that name, and reasonsmith neither knows nor checks which basis that is. **Interactions are not reached either**: moving two protected variables together is a different property, and the atom is deliberately not composable (`test_the_atom_is_the_whole_spec_or_no_part_of_one`). **A system with no notion of the variable is `unattainable`, never satisfied** — unawareness is not a discharge of this duty, and telling the two apart is what the `computes` direction declaration is consulted for (`test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`). **And the trigger, as everywhere else in this pack, is not modelled**: § 1002.4(a) governs a creditor in a credit transaction, and no gate here checks that the system under test is one. **`applicant_prohibited_basis` is the first shipped signal that is a fact about a natural person rather than about a system**, so it is outside the paper's four Section 6.3 categories (`sut.CAPABILITY_TAXONOMY`) and named as the sole exception by `test_exactly_one_shipped_signal_is_outside_the_paper_s_taxonomy`. It is an input the decision procedure accepts and **not** a field a decision record must carry: the duty asks whether the procedure uses it, and neither engine ever takes its value from the trace, so nothing here is a reason to log a prohibited basis for anybody. |


## Table 7 — `src/reasonsmith/packs/table7.toml`

This pack is different in kind, and the difference is the largest single item in its column four.
Its rows are transcribed from Table 7 of *Symbols and Neurons* (Stan, Sciavicco & Napoletano, JAIR
2026, p. 36:22), not from a statute. So:

- `verbatim_text` is the table's **Requirement** cell — a duty *label* such as "Record–keeping (event
  logging)" — not statutory text. A quotation here cannot be checked against a print of the law,
  and `drift.py` does not check these rows against a live source the way it checks the three
  statutory packs.
- `requires` is the paper's own **evidence-field keys**, in the printed order, held there by
  `test_pack_matches_table7_transcription`. Each `spec` is therefore the presence of the paper's
  *minimal evidence checklist* for that duty — deliberately a restatement of a checklist, and never
  a formalisation of the underlying clause.
- The refinement step for this pack was largely performed by the paper's authors, in choosing which
  evidence fields stand for which duty. Only `stakeholder` and `spec` are editorial here; the pack
  header says so.

| The clause | The informal duty | The formal property | What was deliberately not captured |
|---|---|---|---|
| EU AI Act Art. 13<br>`eu_ai_act_art13_transparency` | Transparency and information to deployers. | `record`: presence of `model_and_data_version_ids`, `extraction_timestamp`, `dataset_snapshot_hash`, `fidelity_coverage_metrics`, `explanation_scope`, `linkage_from_decision_to_artifact` | Transparency, as distinct from the retained evidence of it: satisfying this row says the six artefacts exist, not that any deployer could interpret anything. `fidelity_coverage_metrics` present means a fidelity number was recorded, not that it is *high* — there is no threshold, deliberately, since a threshold here would be the pack author's figure presented as the Act's (`docs/authoring-packs.md`). `linkage_from_decision_to_artifact` present means a link field is filled, not that the link resolves to the artefact that produced that decision. This row and `eu_ai_act_art13_1_transparency_deployers` formalise the same Article over disjoint signal vocabularies and can disagree about one system. |
| EU AI Act Art. 12<br>`eu_ai_act_art12_record_keeping` | Record-keeping (event logging). | `record`: `present(automatic_event_logs) and present(retention_schedule) and present(signer)` | Whether anything was retained or signed. `retention_schedule` present means a schedule was declared, not that it was honoured or that its period is long enough for the Act. `signer` present means a signer field is non-empty; **no cryptographic signature is verified anywhere in this repository**, so a signer name typed into a field is evidence of the same weight as a real one. *Automatic* is not distinguishable from hand-assembled, as in the statutory Article 12 row above. |
| GDPR Art. 22 (and Rec. 71)<br>`gdpr_art22_meaningful_information` | Automated decisions: "meaningful information about the logic involved". | `record`: `present(per_decision_reason_string) and present(feature_to_named_concept_mapping) and present(dpia_cross_reference)` | *Meaningful*, again, and the accuracy of the mapping: `feature_to_named_concept_mapping` present means a mapping exists, not that its named concepts correspond to what the model uses. `dpia_cross_reference` present is a pointer to a data protection impact assessment — not evidence that the assessment exists, is current, or reached any conclusion. The row cites Article 22 and Recital 71 together, as the paper prints it, and carries `binding = true` because Article 22 is directly applicable; the clause-by-clause split, and the recital's non-binding status, live in `packs/gdpr.toml`. |
| ECOA / Reg B 12 CFR 1002.9<br>`ecoa_reg_b_adverse_action` | Adverse action reasons in credit decisions. | `record`: presence of `stored_reasons_per_decision`, `model_version`, `score_factors`, `audit_ids`, `retention_for_regulatory_lookback` | Specificity, as in the statutory ECOA rows: `score_factors` present is not a check that the factors stored are the *principal* reasons for the action. `retention_for_regulatory_lookback` present means the record names a retention arrangement, not that a record actually survives the 25-month period of 1002.12(b). The adverse-action trigger is not modelled, so the row is checked over approvals too. And this row carries `domains = ["consumer-credit"]`, so it no longer reaches a system that has not said it decides in consumer credit — but the adverse-action trigger it does not model is the part of the clause's reach that gate cannot recover. |
| FDA GMLP, agency transparency guidance<br>`fda_gmlp_samd` | Good Machine Learning Practice and transparency for Software as a Medical Device. | `record`: `present(design_history_links) and present(verification_logs) and present(change_control)` | The guidance itself. GMLP is a set of guiding principles, not a rule with a compliance test, which is what `binding = false` records; none of the ten principles — multidisciplinary expertise, good software engineering practice, representative data sets, independence of training and test sets, and the rest — is formalised. `article_clause` here is a description, not a citation: there is no clause to quote, so `verbatim_text` cannot be verified against a print and the drift check has no source to re-fetch. `change_control` present means a field is filled, not that a change went through a predetermined change control plan. This row carries `domains = ["healthcare"]` — the paper's Table 7 has no such column, so the classification is this pack author's, and it means a system that has not declared a healthcare decision domain is reported not applicable here rather than judged against guidance for medical-device software. |
| NIST AI RMF 1.0<br>`nist_ai_rmf_risk_evidence` | Risk evidence and continuous monitoring. | `record`: presence of `continuous_monitoring_logs`, `metric_thresholds_and_alerts`, `reviews_and_sign_offs`, `incident_tickets` | *Continuous*, and the framework's structure. The AI RMF is voluntary and organised around the GOVERN, MAP, MEASURE and MANAGE functions rather than testable duties, so `article_clause = "1.0"` is a framework version, not a clause — the same non-citation problem as the row above, and `binding = false` records the voluntariness. `metric_thresholds_and_alerts` present means thresholds were declared, not that any of them is appropriate or that an alert ever fired; `reviews_and_sign_offs` present means a sign-off field is non-empty, not that a reviewer with authority read anything. Continuity cannot be established from a supplied trace at all (`docs/semantics.md` §1). |

---

## What this record obliges an author to do

A new requirement is not finished when the loader accepts it. Before shipping one, write its row
here: the clause, the duty, the property, and what the property does not capture. If the fourth
column is hard to write, that is the refinement being examined for the first time, which is the
point. If it comes out as "some aspects are not captured", it is not written yet — name the aspect.

Two things belong elsewhere, not in this column. A property that cannot be written in the language
at all is a finding for `docs/semantics.md` (`docs/authoring-packs.md`, *one property language*). A
threshold that is the pack author's rather than the regulation's must be declared in the pack
description as well as here (`docs/authoring-packs.md`, *a number in a spec*).
