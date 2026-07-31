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

*Note:* `nesyarena` is pinned to an immutable git commit in `pyproject.toml`. Do not point it at a local sibling checkout or branch when submitting PRs, as measurements must remain reconstructible.

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
| **What is built** | Complete (v0.2 Core) | Evidence record emitter (`evidence.py`), reason-deletion certificates (`certificate.py`), Table 19 conformance suite (`conformance.py`), SUT capability protocol (`sut.py`), JSONL & callable adapters (`adapters/`), `record` & `observed` temporal engines (`engines/`), formal regulation packs (`packs/`), and CLI checker (`cli.py`). Demonstrations for ECOA credit (Table 7 row 4) and GDPR clinical (Table 7 row 3). |
| **What is next** | Active / Open Work | Demonstrations and engine integration for remaining Table 7 duties (**Issue 6**), rendering formatters for compliance reports, and expanded temporal monitor rule sets. |
| **Deliberately NOT done** | Out of Scope | Web/GUI dashboards, reimplementing `nesyarena` IR or oracle engines, generating automated legal opinions, or making un-hedged legal compliance guarantees. |

### Concrete Open Work for Contributors

If you want to contribute, a great place to start is **Issue 6: End-to-end demonstrations for remaining Table 7 duties**. Specifically:
- **Row 1:** EU AI Act Art. 12(3) biometric identification logging.
- **Row 2:** EU AI Act Art. 13 deployer transparency instructions.
- **Row 5:** FDA GMLP Software as a Medical Device (SaMD) total product lifecycle transparency.
- **Row 6:** NIST AI RMF 1.0 continuous risk monitoring logs.

Building an end-to-end demo script or extending an engine for one of these duties is a concrete, high-impact contribution.

## Standing Rules for Changes

1. **Table 7 and Legal Quotes Are Verbatim:**
   `src/reasonsmith/table7.toml` and statutory text quotes in `src/reasonsmith/packs/*.toml` reproduce published papers and official statutory texts (`docs/legal-sources.md`). They are guarded by automated tests (`test_pack_matches_table7_transcription`). Do not tidy, modernize, or alter quotes of law or Table 7 wording.

2. **No Satisfied Verdicts on Absent Evidence:**
   Nothing in `reasonsmith` may report `satisfied` or `COMPLETE` on missing or incomplete evidence. Default values or fallbacks must never be substituted for missing fields.

3. **Three Distinct Non-Pass Concepts:**
   Do not confuse or combine these three distinct statuses:
   - **`not_applicable`**: The system's declared regulatory scope (e.g. non-high-risk) does not trigger the requirement.
   - **`unattainable`**: The system's capability set lacks a required signal name, so no amount of trace testing can discharge the requirement.
   - **`not_evaluated`**: No engine exists for the requirement's formalism, or the trace was empty/too short. `strength=None` is recorded and combining zero verdicts produces `inconclusive`, never `satisfied`.

4. **What Makes a Good Change:**
   - Minimal, focused diffs addressing a specific requirement or issue.
   - Accompanying unit tests in `tests/`.
   - Complete adherence to existing module docstring shapes and safety boundaries.

## Submitting Pull Requests

1. Create a focused topic branch (`git checkout -b my-feature-branch`).
2. Implement your change with tests.
3. Verify that `ruff check .`, `pytest`, and `python -m reasonsmith.demo` pass.
4. Open a Pull Request targeting `main` describing your changes and referencing any open issue (e.g., `Fixes #6`).
5. **No AI co-author trailers:** Do not include automated co-author trailers in commit messages.
