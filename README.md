# reasonsmith — audit-grade evidence records and reason-deletion certificates for symbolic decisions.

[![tests](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml)
[![Python >= 3.11](https://img.shields.io/badge/python->=3.11-blue.svg)](https://www.python.org/)
[![MIT licence](https://img.shields.io/github/license/eduardstan/reasonsmith)](https://github.com/eduardstan/reasonsmith/blob/main/LICENSE)

A decision that affects a person carries a legal duty to give reasons. `reasonsmith` turns that duty into machine-checkable records: given a decision, the symbolic artifact behind it, and the applicable regulatory duty, it emits the minimal evidence record required—and plainly reports any fields it could not produce. For proof-based systems, exact inference enumerates every reason so that reason-deletion certificates can compare actual engine behaviour against ground truth and attribute dropped reasons.

## Key Finding

**Form completeness does not imply truth or reason fidelity.**

In the credit demonstration (`python -m reasonsmith.demo`), `reasonsmith` produces an evidence record that is marked **COMPLETE** under Table 7 form checks while its reason-deletion certificate shows that **four of its five reasons are missing**.

Evaluating structural form alone can launder severe compliance and reasoning gaps into documents that appear authoritative. Reason-deletion certificates provide the ground-truth verification needed alongside regulatory evidence records.

Every number above is measured and reproduced in **[RESULTS.md](RESULTS.md)**, along with the exact environment and versions, both suites' pass/fail/skip counts with `torch` installed, and a byte-for-byte diff of two demo runs. Figures this README takes from the paper rather than from running code — the 273 primary studies, the six Table 7 duties — and the rough `~1GB` size of the `torch` download are not measurements and are not reproduced there.

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
- **`torch` is deliberately not a declared dependency of this package** (`pyproject.toml` is unaffected): it is an optional dependency of `nesyarena` (`learning`, ~1GB) and is not needed to run this package's own suite or demo, both of which stay pure-Python. It **has** been installed and measured in a separate environment, and `tests/test_e6_findings.py` and `tests/test_learning_parity.py` — the two `nesyarena` modules that could not even be collected without it — now collect and run there. The gaps that remain in `nesyarena`'s own suite are real and are not torch: they need `ltn`, `deeplog`, `deepproblog` (nesyarena's `backends` extra) and `problog` (its `oracles` extra), neither of which was installed. The exact counts, install commands, and complete pass/fail list are in [RESULTS.md](RESULTS.md#1-nesyarenas-own-suite-with-torch-present) — the one place those numbers live.

## What is in the box

Deliberately built as focused modules rather than a generic framework:

| File / Module | Description |
|---|---|
| `src/reasonsmith/table7.toml` | The six duties transcribed verbatim, with row-level traceability |
| `src/reasonsmith/evidence.py` | Minimal evidence record emitter and missing field reporter |
| `src/reasonsmith/certificate.py` | Reason-deletion certificates against exact inference oracle |
| `src/reasonsmith/conformance.py` | Table 19 checks, including stratified per-group evaluations |
| `src/reasonsmith/demo.py` | End-to-end demonstration (ECOA/Reg B credit and GDPR Art. 22 clinical) |
| `src/reasonsmith/verdict.py` | v0.2 core: the evidence strength lattice and the verdict vocabulary |
| `src/reasonsmith/spec.py` | v0.2 core: requirements with verbatim provenance, loaded from `packs/*.toml` |
| `src/reasonsmith/sut.py` | v0.2 core: the system-under-test protocol — declared capabilities and a decision trace |
| `src/reasonsmith/report.py` | v0.2 core: the unattainable analysis and the conformance report |
| `src/reasonsmith/packs/table7.toml` | The Table 7 rows restated as a requirement pack, derived from `table7.toml` |

### The Emitter (`evidence.py`)
`emit(duty_id, decision_id, fields)` returns a record that is either `COMPLETE` or `INCOMPLETE`. An `INCOMPLETE` record explicitly names the fields it lacks. Nothing is defaulted, inferred, or silently dropped. Keys outside the duty's Table 7 row are rejected, and non-Table 7 data is isolated in `attachments`.

### The Reason-Deletion Certificate (`certificate.py`)
Compares the reasons an engine actually used against exact inference ground truth (enumerated via WMC in `nesyarena`). Using deletion probes, it tests whether disabling isolated facts changes engine output. Two independent checks must pass: the deletion probe (every reason live) and the value check against the exact oracle. Reasons that cannot be probed in isolation are reported as uncertified (`INCONCLUSIVE`).

### The Strength Lattice (`verdict.py`, `report.py`) — v0.2, first slice only
A verdict carries the strength of the evidence behind it: `unattainable < observed < probed < proved`. Only the first two rungs exist here. `unattainable` is a set difference over the capabilities a system *declares*, so it is answerable before the system runs at all: a system that cannot emit reasons is reported unattainable on the requirements needing them, with the missing signals named and without being executed. `observed` reads a passive decision trace. `probed` and `proved` need engines this build does not have, so a requirement whose formalism no engine covers is reported as not evaluated — no strength and no verdict — rather than judged by a weaker check; combining zero verdicts is `inconclusive`, never vacuously `satisfied`. These are library modules: there is no CLI, no report renderer beyond text/JSON, and exactly one pack, the Table 7 one.

### Machine-Readable Output
Records and certificates also serialise: `to_dict()` returns plain Python, `to_json(indent=None)` returns a JSON string. Each carries the same facts as its text rendering, including its missing-field report and its own limits, so a downstream consumer cannot read a partial document as a complete one. Values outside JSON's own types are stringified rather than raising.

### Summary of Empirical Findings
- **Stratified checks**: Registered hypothesis that low-probability reasons are dropped first holds in one form, not another. Confidence scaling leaves reason ordering unchanged (flat per-group coverage, but shifting retained share/fidelity). Varying reasons per case does shift coverage. The cohorts are frozen synthetic ones built to separate the two mechanisms; whether real atypical cases trip more reasons is an empirical question this does not answer.
- **Signal stability**: Under top-1 settings, drift in a single signal can silently swap the reason given to an applicant on an unchanged file.

## Limits

**Status: early. Nothing here is a compliance guarantee, and none of it is legal advice.**

- A certificate speaks only about the specific program, base interpretation, and query tested.
- Table 7 completeness checks the **form** of a record, never the truth of its contents.

## Licence

[MIT](LICENSE)

