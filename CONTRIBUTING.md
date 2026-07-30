# Contributing to reasonsmith

Thank you for your interest in contributing to `reasonsmith`.

## Development Environment Setup

Please follow the single pinned installation path described in [README.md#quick-start](README.md#quick-start).

Using Python 3.11+ and a virtual environment ensures that dependencies—including `nesyarena`, which is pinned to an immutable commit SHA in `pyproject.toml`—are resolved consistently.

## Running Tests and Linters

Before submitting a change, run the test suite and linter locally exactly as CI does:

```sh
ruff check .
pytest
python -m reasonsmith.demo
```

All three commands must pass without errors or warnings. Continuous integration (`.github/workflows/ci.yml`) executes these exact steps on every push and pull request.

## Critical Requirement: Table 7 Immutability

`src/reasonsmith/table7.toml` is a verbatim transcription of Table 7 from the published paper:
*Symbols and Neurons: A Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026).

- **`table7.toml` is data, not code.**
- Changing a duty, an artifact, or an evidence field is not a code refactoring—it is a claim about what a published paper says, and the published table wins.
- Do not alter, extend, modernise, or "fix" the wording in `table7.toml` unless correcting a literal transcription typo against the printed paper.

## Reporting Issues

If you encounter a bug or have a question:
1. Check existing issues to see if it has already been discussed.
2. Note that **GitHub Discussions is disabled** for this repository. All questions, bug reports, and feature requests should be submitted as [GitHub Issues](https://github.com/eduardstan/reasonsmith/issues).
3. Provide clear reproduction steps, expected vs. actual behavior, and details about your environment.

## Submitting Pull Requests

1. Create a focused topic branch (`git checkout -b my-feature-branch`).
2. Make your changes, keeping them minimal and targeted.
3. Ensure linter (`ruff check .`), tests (`pytest`), and demo (`python -m reasonsmith.demo`) pass.
4. Submit a Pull Request targeting the `main` branch with a clear explanation of your changes.
