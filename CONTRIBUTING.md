# Contributing to reasonsmith

Thank you for your interest in contributing to `reasonsmith`.

## Development Environment Setup

Follow the single pinned installation path:

```sh
git clone https://github.com/eduardstan/reasonsmith.git
cd reasonsmith
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

*Note:* `nesyarena` is pinned to `nesyarena==0.1.0` on PyPI in `pyproject.toml`. Do not point it at a local sibling checkout or branch when submitting PRs, as measurements must remain reconstructible.

## Running Tests and Linters

Before submitting a pull request, run all three verification commands:

```sh
ruff check .
pytest
python -m reasonsmith.demo
```

All three must pass cleanly with zero errors or warnings. Continuous integration (`.github/workflows/ci.yml`) runs exactly these steps on every push and PR.

## Roadmap & What to Work On

### Project Status & Roadmap

| Category | Status | Details |
|---|---|---|
| **What is built** | Complete (v0.2 Core) | The module inventory lives in the [`README.md`](README.md) architecture table — read it there rather than here. Beyond the modules: the HTML report is published to GitHub Pages by `.github/workflows/pages.yml`, and end-to-end demonstrations exist for all six Table 7 rows — the `demo.py` line of that same architecture table lists them. |
| **What is next** | Active / Open Work | Expanded temporal monitor rule sets — see the open work listed below. |
| **Deliberately NOT done** | Out of Scope | Web/GUI dashboards — the `--html` report is one static offline file, not a served application — reimplementing `nesyarena` IR or oracle engines, generating automated legal opinions, or making un-hedged legal compliance guarantees. |

### Concrete Open Work for Contributors

The demonstrations **Issue 6** asked for — rows 1, 2, 5 and 6 — have landed, so every Table 7 row now has one. What is still open:

- **Wider temporal monitor rule sets** for the `observed` rtamt engine.

Extending an engine, rather than adding another demo, is now the concrete, high-impact contribution.

## Standing Rules for Changes

1. **Table 7 and Legal Quotes Are Verbatim:**
   `src/reasonsmith/table7.toml` and statutory text quotes in `src/reasonsmith/packs/*.toml` reproduce published papers and official statutory texts (`docs/legal-sources.md`). They are guarded by automated tests: `test_pack_matches_table7_transcription` holds the Table 7 pack to `table7.toml`, and `test_pack_quotes_found_verbatim_in_legal_sources_report` holds every statutory quote to `docs/legal-sources.md`. Do not tidy, modernize, or alter quotes of law or Table 7 wording.

2. **No Satisfied Verdicts on Absent Evidence:**
   Nothing in `reasonsmith` may report `satisfied` or `COMPLETE` on missing or incomplete evidence. Default values or fallbacks must never be substituted for missing fields.

3. **Preserve the Non-Pass Distinctions:**
   Do not combine unattainable, not-evaluated, and not-applicable results or treat any of them as a
   pass. Their authoritative contracts and invariants live in `verdict.py` and `report.py`; the
   user-facing explanation lives in the README's Conformance Core section.

4. **What Makes a Good Change:**
   - Minimal, focused diffs addressing a specific requirement or issue.
   - Accompanying unit tests in `tests/`.
   - Complete adherence to existing module docstring shapes and safety boundaries.

## Reporting Issues

If you encounter a bug or have a question:
1. Check existing issues to see if it has already been discussed.
2. Note that **GitHub Discussions is disabled** for this repository. All questions, bug reports, and feature requests should be submitted as [GitHub Issues](https://github.com/eduardstan/reasonsmith/issues) — there is no second channel.
3. Provide clear reproduction steps, expected vs. actual behaviour, and details about your environment.

## Submitting Pull Requests

1. Create a focused topic branch (`git checkout -b my-feature-branch`).
2. Implement your change with tests.
3. Verify that `ruff check .`, `pytest`, and `python -m reasonsmith.demo` pass.
4. Open a Pull Request targeting `main` describing your changes and referencing any open issue it addresses (e.g., `Fixes #123`).
5. **No AI co-author trailers:** Do not include automated co-author trailers in commit messages.
