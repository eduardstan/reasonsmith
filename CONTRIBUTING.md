# Contributing to reasonsmith

Thank you for your interest in contributing to `reasonsmith`.

## Development Environment Setup

Follow the single pinned installation path described in [README.md#quick-start](README.md#quick-start). There is no second route, and it is the one CI runs.

## Running Tests and Linters

Before submitting a change, run the same `ruff check .`, `pytest` and `python -m reasonsmith.demo` steps listed in [README.md#quick-start](README.md#quick-start). All three must pass without errors or warnings; continuous integration (`.github/workflows/ci.yml`) runs exactly those steps on every push and pull request.

## Critical Requirement: Table 7 Immutability

`src/reasonsmith/table7.toml` is a verbatim transcription of a published table — see [README.md#where-the-duties-come-from](README.md#where-the-duties-come-from) for the source and why it is data, not code.

Changing a duty, an artifact, or an evidence field is therefore not a refactoring: it is a claim about what a published paper says, and the printed table wins. Do not alter, extend, modernise, or "fix" the wording in `table7.toml` unless you are correcting a literal transcription typo against the print.

## Reporting Issues

If you encounter a bug or have a question:
1. Check existing issues to see if it has already been discussed.
2. Note that **GitHub Discussions is disabled** for this repository. All questions, bug reports, and feature requests should be submitted as [GitHub Issues](https://github.com/eduardstan/reasonsmith/issues).
3. Provide clear reproduction steps, expected vs. actual behaviour, and details about your environment.

## Submitting Pull Requests

1. Create a focused topic branch (`git checkout -b my-feature-branch`).
2. Make your changes, keeping them minimal and targeted.
3. Ensure the checks under "Running Tests and Linters" above pass.
4. Submit a Pull Request targeting the `main` branch with a clear explanation of your changes.
