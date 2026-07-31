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
| **What is built** | Complete (v0.2 Core) | Evidence record emitter (`evidence.py`), reason-deletion certificates (`certificate.py`), Table 19 conformance suite (`conformance.py`), SUT capability protocol (`sut.py`), JSONL & callable adapters (`adapters/`), `record` & `observed` temporal engines (`engines/`), formal regulation packs (`packs/`), and CLI checker (`cli.py`). Text, JSON and self-contained HTML report renderers (`report.py`, `cli.py --html`), the latter published to GitHub Pages by `.github/workflows/pages.yml`. Demonstrations for ECOA credit (Table 7 row 4) and GDPR clinical (Table 7 row 3). |
| **What is next** | Active / Open Work | Demonstrations and engine integration for remaining Table 7 duties (**Issue 6**) and expanded temporal monitor rule sets. |
| **Deliberately NOT done** | Out of Scope | Web/GUI dashboards — the `--html` report is one static offline file, not a served application — reimplementing `nesyarena` IR or oracle engines, generating automated legal opinions, or making un-hedged legal compliance guarantees. |

### Concrete Open Work for Contributors

If you want to contribute, a great place to start is **Issue 6: End-to-end demonstrations for remaining Table 7 duties**. Specifically:
- **Row 1:** EU AI Act Art. 13 transparency and information to deployers.
- **Row 2:** EU AI Act Art. 12 record-keeping (event logging).
- **Row 5:** FDA GMLP Software as a Medical Device (SaMD) total product lifecycle transparency.
- **Row 6:** NIST AI RMF 1.0 continuous risk monitoring logs.

Building an end-to-end demo script or extending an engine for one of these duties is a concrete, high-impact contribution.

## Standing Rules for Changes

1. **Table 7 and Legal Quotes Are Verbatim:**
   `src/reasonsmith/table7.toml` and statutory text quotes in `src/reasonsmith/packs/*.toml` reproduce published papers and official statutory texts (`docs/legal-sources.md`). They are guarded by automated tests: `test_pack_matches_table7_transcription` holds the Table 7 pack to `table7.toml`, and `test_pack_quotes_found_verbatim_in_legal_sources_report` holds every statutory quote to `docs/legal-sources.md`. Do not tidy, modernize, or alter quotes of law or Table 7 wording.

2. **No Satisfied Verdicts on Absent Evidence:**
   Nothing in `reasonsmith` may report `satisfied` or `COMPLETE` on missing or incomplete evidence. Default values or fallbacks must never be substituted for missing fields.

3. **Three Distinct Non-Pass Concepts:**
   `verdict.py` defines `satisfied`, `violated`, `inconclusive` and `not_applicable`. The first two non-pass concepts below both read as `inconclusive` and are told apart by strength; the third is a separate verdict. Do not confuse or combine them:
   - **`unattainable`**: The system's capability set lacks a required signal name, so no amount of trace testing can discharge the requirement. This is the lowest rung of the strength lattice, and `RequirementResult` refuses to report it as anything but `inconclusive`.
   - **`not_evaluated`**: No engine exists for the requirement's formalism (`report.py:SUPPORTED_FORMALISMS`), or the trace was empty/too short. `strength=None` is recorded — deliberately not a rung on the lattice — and combining zero verdicts produces `inconclusive`, never `satisfied`.
   - **`not_applicable`**: The requirement carries a `scope` (`spec.py`) naming a regulatory class the system is not declared to be in, so `evaluate_requirement` never checks it. This is a statement about the duty's reach, not about the system: `reasonsmith` never infers a system's class, so an undeclared system is neither placed in scope nor cleared of the duty. The class is declared by the caller via `--system-scope` (`cli.py`), and the report prints a `declared scope:` line so a not-applicable result is always read next to it.

   A related distinction lives on the requirement itself: `binding = false` marks a recital or guidance item that informs interpretation but creates no duty of its own. Interpretive requirements are evaluated and reported with an `[INTERPRETIVE]` tag, and are counted separately from the binding headline counts. None of the three non-pass concepts, and no interpretive finding, changes the CLI exit code — only `violated` does.

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
4. Open a Pull Request targeting `main` describing your changes and referencing any open issue (e.g., `Fixes #6`).
5. **No AI co-author trailers:** Do not include automated co-author trailers in commit messages.
