# Reasonsmith Documentation Index

Welcome to the documentation directory for `reasonsmith`.

## Documentation Files

| File | Description |
|---|---|
| [`semantics.md`](semantics.md) | What a reasonsmith verdict means: the objects, the property language, one soundness paragraph per engine (`record`, `observed`, `probed`, `proved`) stating what follows and what does not, the strength lattice, and the limits. Every claim names the test that enforces it; `test_docs_semantics.py` holds the document to that map. |
| [`legal-sources.md`](legal-sources.md) | Retrieval record and exact verbatim statutory text for EU AI Act (Art. 12 & 13), GDPR (Art. 22 & Recital 71), and ECOA / Regulation B (12 CFR 1002.9). Checked by automated tests. |
| [`authoring-packs.md`](authoring-packs.md) | Authoring guide for requirement packs: the exact `[[requirement]]` field set, `binding`/`scope` semantics, the verbatim-and-traceable rule, and how to validate a pack with `validate-pack`. |
| [`example-output.md`](example-output.md) | Execution transcripts, stdout pasted unedited, from running `python -m reasonsmith.demo` and `python -m reasonsmith.cli check`. Each block names the command that regenerates it. |
| [`sample_decisions.jsonl`](sample_decisions.jsonl) | Committed three-record decision trace from a credit-scoring pipeline, so the CLI commands in the README and in `example-output.md` run from a fresh clone with no data of your own. |
| [`index.html`](index.html) | Generated, not hand-maintained: the self-contained HTML report for `sample_decisions.jsonl` against the Table 7 pack, declared into the high-risk class, with the demonstration's key finding beside it. Regenerate it with `python docs/build_example.py`, which is the command the page names as its own provenance. |
| [`build_example.py`](build_example.py) | The script that generates `index.html`. It is not the CLI: the key-finding section belongs to the demonstration's case, so no report the CLI writes carries it. `test_docs_index_html_matches_the_renderer` runs this script and holds the committed page to it byte-for-byte. |
| `report-preview.png` | Screenshot of that page, shown at the top of the [`README.md`](../README.md). Retake it when the renderer's layout changes. |

## Related Project Artifacts

- **Live site:** the landing page at [reasonsmith.dev](https://reasonsmith.dev) and the self-contained conformance dossier at [reasonsmith.dev/report.html](https://reasonsmith.dev/report.html).
- [`README.md`](../README.md): Project overview, key findings, quick start, and module index.
- [`RESULTS.md`](../RESULTS.md): Full empirical measurement suite, test counts, torch environment details, and execution provenance.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md): Contributor on-ramp, roadmap, coding rules, and concrete open work.
