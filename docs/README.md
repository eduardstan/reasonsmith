# Reasonsmith documentation index

Each line points to the document that owns the subject; the numbered chapters are the mathematical
spine and `semantics.md` is the operational report-reading contract.

- [`semantics.md`](semantics.md) — report outcomes, evidence reading, audience projections, and operational boundaries.
- [`adopting.md`](adopting.md) — user-facing commands and system surfaces.
- [`authoring-packs.md`](authoring-packs.md) — pack schema and authoring rules.
- [`authoring-engines.md`](authoring-engines.md) — installed engine contract.
- [`refinement.md`](refinement.md) — one row for every clause-to-property refinement.
- [`legal-sources.md`](legal-sources.md) — statutory retrieval record.
- [`what-this-does-not-do.md`](what-this-does-not-do.md) — documented limits and hazards.
- [`three-systems.md`](three-systems.md) — neural, callable, and rule-system examples.
- [`language-model.md`](language-model.md) — language-model adapter example.
- [`example-output.md`](example-output.md) — generated demonstration transcript.
- [`findings-nesyarena.md`](findings-nesyarena.md) — findings from the conformance run.
- [`nesyarena-conformance-report.md`](nesyarena-conformance-report.md) — generated conformance dossier.
- [`autoformalization.md`](autoformalization.md) — challenge corpus and proposer workflow.
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

Each path reaches all nine numbered chapters; the surrounding documents answer the audience's
operational question before or after the mathematical spine.

- **Developer:** README → adopting → [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md) → authoring-engines → limits.
- **Deployer:** README → three-systems → adopting → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md) → semantics → limits.
- **Auditor:** example-output → semantics → [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md) → refinement → findings.
- **Regulator:** legal-sources → refinement → [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md) → semantics → limits.
- **Affected individual:** example-output → semantics → [`00`](theory/00-notation.md) → [`01`](theory/01-models.md) → [`02`](theory/02-syntax.md) → [`03`](theory/03-semantics.md) → [`04`](theory/04-decision-problems.md) → [`05`](theory/05-decision-procedures.md) → [`06`](theory/06-formalisation.md) → [`07`](theory/07-explanation.md) → [`08`](theory/08-evidence.md) → limits.

## Project records

- [`README`](../README.md) — project front door and install/run example.
- [`ROADMAP`](../ROADMAP.md) — public backlog.
- [`RESULTS`](../RESULTS.md) — measured results and reproduction commands.
