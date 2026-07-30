# reasonsmith — audit-grade evidence records and reason-deletion certificates for symbolic decisions.

[![tests](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml)
[![Python >= 3.11](https://img.shields.io/badge/python->=3.11-blue.svg)](https://www.python.org/)
[![MIT licence](https://img.shields.io/github/license/eduardstan/reasonsmith)](https://github.com/eduardstan/reasonsmith/blob/main/LICENSE)

A decision that affects a person carries a legal duty to give reasons. `reasonsmith` turns that duty into machine-checkable records: given a decision, the symbolic artifact behind it, and the applicable regulatory duty, it emits the minimal evidence record required—and plainly reports any fields it could not produce. For proof-based systems, exact inference enumerates every reason so that reason-deletion certificates can compare actual engine behaviour against ground truth and attribute dropped reasons.

## Key Finding

**Form completeness does not imply truth or reason fidelity.**

In the credit demonstration (`python -m reasonsmith.demo`), `reasonsmith` produces an evidence record that is marked **COMPLETE** under Table 7 form checks while its reason-deletion certificate shows that **four of its five reasons are missing**.

Evaluating structural form alone can launder severe compliance and reasoning gaps into documents that appear authoritative. Reason-deletion certificates provide the ground-truth verification needed alongside regulatory evidence records.

## Where the duties come from

The duty-to-artifact mapping is Table 7 of *Symbols and Neurons: A Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026), a review of 273 primary studies tying symbolic artifacts to duties under the EU AI Act, GDPR, ECOA/Reg B, FDA GMLP, and NIST AI RMF.

Table 7 is transcribed verbatim into `src/reasonsmith/table7.toml`. That file is data, not code: every duty records its row number, and every machine key sits next to the exact cell text it stands for. `traceability_report()` prints the table side by side. Where a design decision and Table 7 disagree, Table 7 wins.

## Quick Start

From a fresh clone (requires Python 3.11+ and git):

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
python -m reasonsmith.demo
```

This single install path is used by CI (`.github/workflows/ci.yml`).

### Dependencies & PyPI
- **`nesyarena`**: Supplies the ground-program IR, bounded proof enumeration, exact oracle, and adapter protocol. It is pinned to an immutable git commit in `pyproject.toml` so measurements stay reconstructible.
- **`torch` is deliberately omitted**: It is an optional dependency of `nesyarena` (`learning`, ~1GB) and is not needed for this test suite or demo. Known consequence, reported rather than hidden: in `nesyarena`'s own suite 98 tests pass while `tests/test_e6_findings.py` and `tests/test_learning_parity.py` fail to collect without `torch`. Those modules live in `nesyarena`'s repository, are not collected here, and are a pre-existing environment gap not fixed here; run them there with `pip install "nesyarena[learning]"`.

## What is in the box

Deliberately built as focused modules rather than a generic framework:

| File / Module | Description |
|---|---|
| `src/reasonsmith/table7.toml` | The six duties transcribed verbatim, with row-level traceability |
| `src/reasonsmith/evidence.py` | Minimal evidence record emitter and missing field reporter |
| `src/reasonsmith/certificate.py` | Reason-deletion certificates against exact inference oracle |
| `src/reasonsmith/conformance.py` | Table 19 checks, including stratified per-group evaluations |
| `src/reasonsmith/demo.py` | End-to-end demonstration (ECOA/Reg B credit and GDPR Art. 22 clinical) |

### The Emitter (`evidence.py`)
`emit(duty_id, decision_id, fields)` returns a record that is either `COMPLETE` or `INCOMPLETE`. An `INCOMPLETE` record explicitly names the fields it lacks. Nothing is defaulted, inferred, or silently dropped. Keys outside the duty's Table 7 row are rejected, and non-Table 7 data is isolated in `attachments`.

### The Reason-Deletion Certificate (`certificate.py`)
Compares the reasons an engine actually used against exact inference ground truth (enumerated via WMC in `nesyarena`). Using deletion probes, it tests whether disabling isolated facts changes engine output. Two independent checks must pass: the deletion probe (every reason live) and the value check against the exact oracle. Reasons that cannot be probed in isolation are reported as uncertified (`INCONCLUSIVE`).

### Summary of Empirical Findings
- **Stratified checks**: Registered hypothesis that low-probability reasons are dropped first holds in one form, not another. Confidence scaling leaves reason ordering unchanged (flat per-group coverage, but shifting retained share/fidelity). Varying reasons per case does shift coverage. The cohorts are frozen synthetic ones built to separate the two mechanisms; whether real atypical cases trip more reasons is an empirical question this does not answer.
- **Signal stability**: Under top-1 settings, drift in a single signal can silently swap the reason given to an applicant on an unchanged file.

## Limits

**Status: early. Nothing here is a compliance guarantee, and none of it is legal advice.**

- A certificate speaks only about the specific program, base interpretation, and query tested.
- Table 7 completeness checks the **form** of a record, never the truth of its contents.

## Licence

[MIT](LICENSE)

