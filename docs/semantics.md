# What a reasonsmith verdict means

This is the short, operational contract for reading a reasonsmith report. It does not restate the
mathematics: the numbered chapters are authoritative for the objects, language, denotation,
decision problems, procedures, refinement, explanation, and evidence.

- [00 — notation](theory/00-notation.md) is the symbol table for the chapters.
- [01 — models](theory/01-models.md), [02 — syntax](theory/02-syntax.md), and
  [03 — semantics](theory/03-semantics.md) define the records, property language, and denotation.
- [04 — decision problems](theory/04-decision-problems.md) and [05 — decision procedures](theory/05-decision-procedures.md)
  state the questions and procedures.
- [06 — formalisation](theory/06-formalisation.md) and [07 — explanation](theory/07-explanation.md)
  state refinement and inference-artefact mathematics.
- [08 — evidence](theory/08-evidence.md) states the strength chain, evidence basis, admissibility
  relation, and graded-reading boundary.
- [claim map](theory/claim-map.md) pairs the chapter claims with executable warrants.

This page is for the reader of a report: what category appeared, what to do next, and which
projection is intended. Where this page and the implementation disagree, the implementation is
right and this page has a defect.

## 1. The report's five operational outcomes

The five report outcomes below must not be collapsed. The evidence chapter defines
strength and basis; this table gives the operational instruction attached to each outcome.

| Outcome | What the report says | What a reader should do |
|---|---|---|
| **satisfied** | An engine established the formal property at the named evidence strength and basis. | Read the property, evidence boundary and limits; this is not a legal-compliance guarantee outside that evidence. |
| **violated** | An engine produced a witness: a record, trace step, input, or other counterexample to the property. | Fix the system. In the default mode, this is the only one of these five outcomes that fails a `check` run; `--strict-unresolved` can also fail on unresolved outcomes. |
| **not applicable** | The duty's declared regulatory class or decision-domain gate did not reach this system. Nothing about the system was checked; reasonsmith never infers the missing declaration. | Declare the class/domain and re-run, or establish that the duty genuinely does not reach the system. This is not clearance. |
| **unattainable** | The system cannot supply a signal required by the duty according to the capability basis used by the run. No engine evaluated the duty. | Change the system, or—when the basis is only the supplied trace—supply a longer trace or explicit capability declaration. |
| **not evaluated** | The duty reached the system, but no engine established a result: for example, evidence was empty, a construct was refused, a trigger never fired, or the required evidence kind was unavailable. | Read the summary. Improve the evidence or expose the capability the question needs. This is neither a finding nor compliance. |

`inconclusive` is the result-model spelling used for the `not evaluated` outcome. It is not the
same as `not_applicable`: the former says a duty that reached the system was not settled, while the
latter says the duty's reach was not established. JSON result objects carry an additive `outcome`
field using the five table names above; the compatibility `verdict` and `strength` fields remain
unchanged. `satisfied` is reserved for an engine-established positive result, and `violated` carries
a witness. The distinctions are enforced by
`RequirementResult.__post_init__` and by the report category table
(`test_the_four_unresolved_outcomes_are_four_distinct_report_categories`).

A trigger that never fired is not evidence that its consequent was met. The report names the
trigger and the searched evidence domain and returns `not evaluated` on the satisfied path
(`test_vacuity_coincides_with_the_unreachable_trigger_rule`). A violation already supplies a firing witness.

## 2. How to read evidence

The label beside a result is a method of evidence, not a confidence score. Read the full
[Evidence chapter](theory/08-evidence.md) for the ordered strength coordinate, the unordered basis
coordinate, and the `BASIS_RUNGS` relation. In particular, `strength=None` means that no engine
settled the duty; it is not an extra rung and never supports a positive or negative claim.

A `probed` result carries the search budget that bounds what was replayed. An `unattainable` result
names missing signals. A result with no strength is not a weak result: it is a different report
state, and its summary says whether the gap was applicability, capability, evidence, or an
unsupported evidence kind (`test_result_cannot_claim_more_than_its_evidence`).

## 3. Who the report is for

One conformance run can be rendered for five audiences. `AudienceProjection` changes what is shown,
never what is claimed (`test_no_audience_sees_a_different_verdict_from_another`). The default and
`auditor` views are the full report; the other views select fields for a reader's task.

| Audience | Primary question | Shown emphasis |
|---|---|---|
| **developer** | What signal or implementation path is missing? | Verdicts, strengths, required and missing signals, summaries, budgets, counterexamples, and witnesses. |
| **deployer** | Does this duty reach the deployment, and what must be declared or procured? | Verdicts, limits, legal classification, capability gaps, summaries, and budgets; not raw witnesses. |
| **auditor** | What is the complete evidentiary record? | Every report field except the affected individual's plain-language account. |
| **regulator** | Which duties were checked, and how far does each claim reach? | Verdicts, strengths, legal limits, summaries, budgets, and unresolved-duty notices. |
| **affected individual** | What did the system record about this decision? | The verdict, limits, and a quoted plain-language account; no strength, system internals, or witness data. |

The projections are presentation views over the one `ConformanceReport`; they do not recompute a
duty. The affected-individual view is the only one that emits a plain-language account, and that
account quotes the decision and reason already present in the run. It does not paraphrase law,
explain the decision, or turn an absent finding into completeness
(`test_the_affected_individual_view_leaks_no_system_internals`).

## 4. Operational boundaries

- A trace is evidence supplied by the system or adapter. reasonsmith does not establish that it is
  representative, complete, or unfiltered.
- Applicability has two independent gates—regulatory class and decision domain. An undeclared gate
  is not inferred and is never silently treated as clearance.
- A duty can require an evidence kind the system does not expose. More records cannot establish a
  counterfactual property, and a log cannot establish an inference-artefact certificate.
- Open-textured predicates are deliberately not guessed. The machinery and its presentation limits
  are stated in [08 — evidence](theory/08-evidence.md); the shipped packs use neither open-texture
  construct (`test_no_shipped_pack_uses_either_open_texture_construct`).
- This report is not legal advice or a compliance guarantee. It reports the formal property and the
  evidence the run could obtain; legal adequacy remains a human determination.

For the executable claim-to-test registry, see [`theory/claim-map.md`](theory/claim-map.md). For
pack-to-property readings, see [`refinement.md`](refinement.md); for the boundaries this tool does
not attempt, see [`what-this-does-not-do.md`](what-this-does-not-do.md).
