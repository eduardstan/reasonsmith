# Reasonsmith Documentation Index

Welcome to the documentation directory for `reasonsmith`.

## Documentation Files

| File | Description |
|---|---|
| [`legal-sources.md`](legal-sources.md) | Retrieval record and exact verbatim statutory text for EU AI Act (Art. 12 & 13), GDPR (Art. 22 & Recital 71), and ECOA / Regulation B (12 CFR 1002.9). Checked by automated tests. |
| [`example-output.md`](example-output.md) | Execution transcripts, stdout pasted unedited, from running `python -m reasonsmith.demo` and `python -m reasonsmith.cli check`. Each block names the command that regenerates it. |
| [`sample_decisions.jsonl`](sample_decisions.jsonl) | Committed three-record decision trace from a credit-scoring pipeline, so the CLI commands in the README and in `example-output.md` run from a fresh clone with no data of your own. |
| [`index.html`](index.html) | Generated, not hand-maintained: the self-contained HTML report for `sample_decisions.jsonl` against the Table 7 pack. `test_docs_index_html_matches_the_renderer` holds it byte-for-byte to `render_html()`, and the regeneration command is in that test's docstring. |
| `report-preview.png` | Screenshot of that page, shown at the top of the [`README.md`](../README.md). Retake it when the renderer's layout changes. |

## Related Project Artifacts

- [`README.md`](../README.md): Project overview, key findings, quick start, and module index.
- [`RESULTS.md`](../RESULTS.md): Full empirical measurement suite, test counts, torch environment details, and execution provenance.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md): Contributor on-ramp, roadmap, coding rules, and concrete open work.
