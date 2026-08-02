# Reasonsmith Documentation Index

Welcome to the documentation directory for `reasonsmith`.

## Documentation Files

| File | Description |
|---|---|
| [`semantics.md`](semantics.md) | What a reasonsmith verdict means: the objects, the property language, one soundness paragraph per engine (`record`, `observed`, `probed`, `proved`) stating what follows and what does not, the strength lattice, and the limits. Every claim names the test that enforces it; `test_docs_semantics.py` holds the document to that map. |
| [`legal-sources.md`](legal-sources.md) | Retrieval record and exact verbatim statutory text for EU AI Act (Art. 12 & 13), GDPR (Art. 22 & Recital 71), and ECOA / Regulation B (12 CFR 1002.9). Checked by automated tests. |
| [`refinement.md`](refinement.md) | The refinement record: for every requirement in every shipped pack, the clause, the informal duty, the formal property it became, and what the refinement deliberately did not capture — including what the regulatory-class and decision-domain gates still leave unreached, the trigger inside a decision above all. `test_docs_refinement.py` reads the packs and fails if one gains a requirement the record does not name. |
| [`authoring-packs.md`](authoring-packs.md) | Authoring guide for requirement packs: the exact `[[requirement]]` field set, `binding`/`scope`/`domains` semantics, the verbatim-and-traceable rule, and how to validate a pack with `validate-pack`. |
| [`authoring-engines.md`](authoring-engines.md) | Authoring guide for an engine shipped as its own pip package and discovered through the `reasonsmith.engines` entry-point group: what a plug-in must supply, the ceiling it declares and cannot exceed, what happens when it misbehaves, and why a `proved` from an engine this repository never audited is worth exactly the installer's trust in that package. |
| [`example-output.md`](example-output.md) | Execution transcripts, stdout pasted unedited, from running `python -m reasonsmith.demo` and `python -m reasonsmith.cli check`. Each block names the command that regenerates it. |
| [`../src/reasonsmith/examples/sample_decisions.jsonl`](../src/reasonsmith/examples/sample_decisions.jsonl) | Committed three-record decision trace from a credit-scoring pipeline, so the CLI commands in the README and in `example-output.md` run with no data of your own. It ships in the wheel, and `python -m reasonsmith.examples` prints the directory it was installed into. |
| [`report.html`](report.html) | Generated, not hand-maintained: the self-contained HTML report for `sample_decisions.jsonl` against the Table 7 pack, declared into the high-risk class, with the demonstration's key finding beside it. Regenerate it with `python docs/build_example.py`, which is the command the page names as its own provenance. |
| [`findings-nesyarena.md`](findings-nesyarena.md) | What reasonsmith found when pointed at a real neuro-symbolic system rather than a demonstration fixture: the five `nesyarena` provenances against the GDPR, EU AI Act and ECOA packs. Includes the unflattering findings — notably that two systems whose decisions differ from the semantics they claim were reported satisfied on every checkable duty. |
| [`nesyarena-conformance-report.md`](nesyarena-conformance-report.md) | Generated, not hand-maintained: the evidence behind `findings-nesyarena.md` — measured inference for 5 systems × 16 generated ground programs, 15 conformance reports, and the counterexamples behind every violated verdict. Regenerate it with `python docs/build_nesyarena_report.py`, the command the report names as its own provenance. |
| [`build_nesyarena_report.py`](build_nesyarena_report.py) | The script that generates `nesyarena-conformance-report.md`, including the system-under-test adapter over `nesyarena.suts`. `test_nesyarena_conformance.py` runs it and holds the committed report to it byte-for-byte. |
| [`three-systems.md`](three-systems.md) | One duty — ECOA / Reg B specific reasons — checked against a neural, a probabilistic and a symbolic system, reaching three different rungs of the evidence lattice (`observed`, `probed`, `proved`). `test_docs_three_systems.py` holds the walkthrough to the adapters byte-for-byte. |
| [`language-model.md`](language-model.md) | A language model prompted to write adverse-action notices, checked against the whole `ecoa` pack. It adds no rung — a callable model sits at `probed` — and is about the axis underneath: which duties a system can be answered on at all. `observed`, `probed`, and `unattainable` on reason fidelity, in one run. `test_docs_language_model.py` holds the transcript and the ceiling. |
| [`../src/reasonsmith/examples/`](../src/reasonsmith/examples/) | The four adapter files `three-systems.md` and `language-model.md` walk through (`neural_scorer.py`, `probabilistic_scorer.py`, `symbolic_rules.py`, `language_model_notices.py`): complete, runnable systems shipped inside the package, each on its own with `python -m reasonsmith.examples.<name>`. |
| [`build_example.py`](build_example.py) | The script that generates `report.html`. It is not the CLI: the key-finding section belongs to the demonstration's case, so no report the CLI writes carries it. `test_docs_index_html_matches_the_renderer` runs this script and holds the committed page to it byte-for-byte. |
| [`build_readme_transcripts.py`](build_readme_transcripts.py) | The script that regenerates the CLI transcripts committed in [`README.md`](../README.md). It raises rather than writing when a command it names matches no block in the document: the block it exists to update went stale once because a helper matched nothing and reported success. |
| `report-preview.png` | Screenshot of that page, shown at the top of the [`README.md`](../README.md). Retake it when the renderer's layout changes. |

## Related Project Artifacts

- **Live site:** the landing page at [reasonsmith.dev](https://reasonsmith.dev) and the self-contained conformance dossier at [reasonsmith.dev/report.html](https://reasonsmith.dev/report.html).
- [`README.md`](../README.md): Project overview, key findings, quick start, and module index.
- [`RESULTS.md`](../RESULTS.md): Full empirical measurement suite, test counts, torch environment details, and execution provenance.
- [`ROADMAP.md`](../ROADMAP.md): The public backlog — four numbered objectives, each with the gap it closes, a measurable outcome that fails today, and what it depends on, plus what is deliberately not planned.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md): Contributor on-ramp, coding rules, and concrete open work.
- [`CHANGELOG.md`](../CHANGELOG.md): Notable changes per release, starting at 0.3.0 — including the breaking ones an externally authored pack or an existing CLI invocation has to answer for.
