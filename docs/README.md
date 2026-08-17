# Reasonsmith documentation index

Start with the operational contract, then follow the mathematical spine. The nine numbered chapters
state reasonsmith's mathematics once, in one notation. [`theory/00-notation.md`](theory/00-notation.md)
is the machine-checked symbol table; [`theory/bibliography.md`](theory/bibliography.md) is the
repository-wide citation registry; [`theory/claim-map.md`](theory/claim-map.md) ties the chapters to
tests. `semantics.md` remains the operational report-reading contract.

Each line below points to the document that owns its subject. This index links rather than repeating
what those documents say.

- [`architecture.md`](architecture.md) — orientation map from regulation and system surfaces through the trusted core to the five report projections.
- [`semantics.md`](semantics.md) — report outcomes, evidence reading, audience projections, and operational boundaries.
- [`assurance-crosswalk.md`](assurance-crosswalk.md) — navigation crosswalk to NIST AI RMF 1.0 and ISO/IEC 42001:2023.
- [`gpai-code-of-practice-appendix.md`](gpai-code-of-practice-appendix.md) — non-executable mapping from the GPAI duties to the EU AI Office Code of Practice.
- [`adopting.md`](adopting.md) — user-facing commands and system surfaces.
- [`../notebooks/`](../notebooks/) — runnable demonstrations: [quickstart reason deletion](../notebooks/01_quickstart_reason_deletion.ipynb), [three systems and three rungs](../notebooks/02_three_systems_three_rungs.ipynb), [bring your own pack and engine](../notebooks/03_bring_your_own_pack_engine.ipynb), and [one system across US and EU jurisdictions](../notebooks/04_one_system_two_jurisdictions.ipynb).
- [`authoring-packs.md`](authoring-packs.md) — pack schema and authoring rules.
- [`authoring-engines.md`](authoring-engines.md) — installed engine contract, witness provenance, and the `verify-engine` conformance kit.
- [`authoring-scaffolds.md`](authoring-scaffolds.md) — copy/paste walkthrough from `reasonsmith init` to an installed, entry-point-discovered pack or engine; every command on the page runs in CI.
- [`neural-verifiers.md`](neural-verifiers.md) — optional ONNX query/oracle adapters and their refusal-first subprocess boundary.
- [`neural-soundness-corpus.md`](neural-soundness-corpus.md) — pinned Marabou and alpha-beta-CROWN soundness-gate evidence.
- [`registry.html`](registry.html) — generated pack and engine discovery registry.
- [`refinement.md`](refinement.md) — one row for every clause-to-property refinement.
- [`legal-sources.md`](legal-sources.md) — statutory retrieval record.
- [`what-this-does-not-do.md`](what-this-does-not-do.md) — documented limits and hazards.
- [`three-systems.md`](three-systems.md) — neural, callable, and rule-system examples.
- [`language-model.md`](language-model.md) — language-model adapter example.
- [`example-output.md`](example-output.md) — generated demonstration transcript.
- [`findings-nesyarena.md`](findings-nesyarena.md) — findings from the conformance run.
- [`nesyarena-conformance-report.md`](nesyarena-conformance-report.md) — generated conformance dossier.
- [`autoformalization.md`](autoformalization.md) — challenge corpus and proposer workflow.
- [`autoformalization-study.md`](autoformalization-study.md) — measured agreement against the hand-authored gold packs.
- [`theory/00-notation.md`](theory/00-notation.md) — global mathematical notation registry.
- [`theory/01-models.md`](theory/01-models.md) — records, traces, declarations, and structures.
- [`theory/02-syntax.md`](theory/02-syntax.md) — grammar, validation, and fragment assignment.
- [`theory/03-semantics.md`](theory/03-semantics.md) — denotation, algebras, temporal semantics, and graded state readings.
- [`theory/04-decision-problems.md`](theory/04-decision-problems.md) — the questions the tool asks.
- [`theory/05-decision-procedures.md`](theory/05-decision-procedures.md) — procedures and their soundness boundaries.
- [`theory/06-formalisation.md`](theory/06-formalisation.md) — clause-to-requirement refinement.
- [`theory/07-explanation.md`](theory/07-explanation.md) — deletion lattices, reasons, certificates, and semantic-law measurements.
- [`theory/08-evidence.md`](theory/08-evidence.md) — strength, basis, admissibility, and graded evidence.
- [`theory/claim-map.md`](theory/claim-map.md) — cross-chapter claim-to-test registry.
- [`theory/bibliography.md`](theory/bibliography.md) — repository-wide citation registry.

## Five audience reading paths

Each invitation reaches all nine numbered chapters; the surrounding documents answer the audience's
operational question before or after the mathematical spine.

- **Developer:** Want to build or extend a check? Begin at README → adopting, walk [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md), then finish at authoring-engines → limits.
- **Deployer:** Choosing an evidence surface? Compare three-systems → adopting, walk [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md), then finish at semantics → limits.
- **Auditor:** Reading a finding? Start at example-output → semantics, walk [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md), then finish at refinement → findings.
- **Regulator:** Checking the legal path? Start at legal-sources → refinement, walk [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md), then finish at semantics → limits.
- **Affected individual:** Want the plain account? Start at [`example-output`](example-output.md) → [`semantics`](semantics.md) → [`limits`](what-this-does-not-do.md). The [`affected-individual audience gallery`](audiences.html) shows the same run in the shortest reader view. The numbered theory chapters are **optional technical background**, not part of this route.

## Project records

- [`README`](../README.md) — project front door and install/run example.
- [`ROADMAP`](../ROADMAP.md) — public backlog.
- [`RESULTS`](../RESULTS.md) — measured results and reproduction commands.
