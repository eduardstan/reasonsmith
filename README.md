# reasonsmith — audit-grade evidence records and reason-deletion certificates for symbolic decisions

[![tests](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml)
[![Python >= 3.11](https://img.shields.io/badge/python->=3.11-blue.svg)](https://www.python.org/)
[![MIT licence](https://img.shields.io/github/license/eduardstan/reasonsmith)](https://github.com/eduardstan/reasonsmith/blob/main/LICENSE)

`reasonsmith` turns legal reason-giving duties into machine-checkable evidence records and reason-deletion certificates. Given a decision, the symbolic artifact behind it, and an applicable regulatory duty, it evaluates structural record completeness and attributes dropped reasons by comparing actual engine behavior against ground-truth exact inference.

## Key Finding: Form Completeness Does Not Imply Reason Fidelity

Evaluating structural form alone can launder severe compliance and reasoning gaps into documents that appear authoritative. In the ECOA/Reg B credit demonstration (`python -m reasonsmith.demo`), `reasonsmith` emits an evidence record that reads **`COMPLETE`** while its paired certificate reads **`FAIL`** because four of its five principal reasons were dropped by proof truncation:

```text
EVIDENCE RECORD [COMPLETE]
decision: APP-1042
duty: Adverse action reasons in credit decisions
legal source: ECOA / Reg B (12 CFR 1002.9)
source of the duty: Table 7 (row 4, p. 36:22), Symbols and Neurons: A Review of Symbolic XAI in Deep Learning, Stan, Sciavicco & Napoletano, Journal of Artificial Intelligence Research, Vol. 86, Article 36, July 2026
symbolic artifact(s) Table 7 asks for: Rule-based “reason codes” mapped to standardized categories; monotone/eligibility constraints for fairness explanations
where it fits: Adverse action notice (AAN) pipeline; compliance reporting

minimal evidence retained:
  [x] stored_reasons_per_decision (Stored reasons per decision):
          C01 — Income insufficient for amount of credit requested
  [x] model_version (model version):
        credit-scoring-2026.03.1 / rules cs-rules-2026.03
  [x] score_factors (score factors):
        C01 0.7656; C02 0.6972; C03 0.6320; C04 0.6004; C05 0.5112
  [x] audit_ids (audit IDs):
        AAN-2026-0731-1042 / trace-9f3c1b
  [x] retention_for_regulatory_lookback (retention for regulatory lookback):
        25 months from notice date, per lender policy

supporting material (NOT Table 7 evidence, and fills no gap above):
  reason-deletion certificate:
    REASON-DELETION CERTIFICATE [FAIL]
    query: adverse_action(APP-1042)
    engine: reference:top-1-proofs   claims: distribution semantics
    exact inference: bounded proof enumeration to depth 1 (nesyarena ground-program IR) + exact weighted model counting
    exact value 0.991399   engine value 0.765600   gap -0.225799   tolerance 1e-09
    reasons: 5 found by exact inference, 1 used by the engine, 4 deleted, 0 not certifiable
```

### Automated Conformance Checking Excerpt

`reasonsmith` also checks decision logs against formal regulation packs (`python -m reasonsmith.cli check`), producing structured reports with clear verdict strengths:

```text
CONFORMANCE REPORT
system: CreditScoringPipeline
declared scope: undeclared
pack: table7
headline: 3 binding requirements · 1 observed · 2 not applicable · + 3 interpretive: 3 unattainable

REQUIREMENT FINDINGS:
  [NOT APPLICABLE] eu_ai_act_art13_transparency (EU AI Act Art. 13): not_applicable
    requires: model_and_data_version_ids, extraction_timestamp, dataset_snapshot_hash, fidelity_coverage_metrics, explanation_scope, linkage_from_decision_to_artifact
    scope limit: high-risk
    summary: Not applicable: requirement scope is 'high-risk', but system regulatory class is undeclared. reasonsmith never infers a system's regulatory class.
  [UNATTAINABLE] [INTERPRETIVE] gdpr_art22_meaningful_information (GDPR Art. 22 (and Rec. 71)): inconclusive
    requires: per_decision_reason_string, feature_to_named_concept_mapping, dpia_cross_reference
    MISSING SIGNALS: dpia_cross_reference, feature_to_named_concept_mapping, per_decision_reason_string
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for dpia_cross_reference, feature_to_named_concept_mapping, per_decision_reason_string, and the system declared no capabilities, so nothing here can discharge this requirement.
  [OBSERVED] ecoa_reg_b_adverse_action (ECOA / Reg B 12 CFR 1002.9): satisfied
    requires: stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback
    summary: Observed over 1 decision(s): every required signal (stored_reasons_per_decision, model_version, score_factors, audit_ids, retention_for_regulatory_lookback) carries a value in every record. Holds on the trace supplied; nothing here extends the claim to decisions not in it.
```

*(See [`docs/example-output.md`](docs/example-output.md) for the full 561-line demo transcript and complete CLI reports.)*

## Quick Start

Run the full verification suite and demonstration in one block:

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
python -m reasonsmith.demo
python -m reasonsmith.cli check --system tests/fixtures/sample_decisions.jsonl --pack ecoa
```

*Note:* This single installation path is used by CI (`.github/workflows/ci.yml`). Full empirical environment measurements and torch test counts are documented in **[RESULTS.md](RESULTS.md)**.

## Where the Duties Come From

The duty-to-artifact mapping is Table 7 of *Symbols and Neurons: A Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:22), reviewing 273 primary studies across five regulatory frameworks: EU AI Act, GDPR, ECOA/Reg B, FDA GMLP, and NIST AI RMF.

Table 7 is transcribed verbatim into `src/reasonsmith/table7.toml`. That file is data, not code: every duty records its row number, and every machine key sits next to the exact cell text it stands for. `traceability_report()` prints the table side by side. Where a design decision and Table 7 disagree, Table 7 wins. Statutory texts are backed by retrieval records in [`docs/legal-sources.md`](docs/legal-sources.md).

## What Is in the Box

### Package Architecture

| File / Module | Description |
|---|---|
| `src/reasonsmith/table7.toml` | The six Table 7 duties transcribed verbatim, with row-level traceability |
| `src/reasonsmith/evidence.py` | Minimal evidence record emitter and missing field reporter |
| `src/reasonsmith/certificate.py` | Reason-deletion certificates against exact inference oracle (`nesyarena`) |
| `src/reasonsmith/conformance.py` | Table 19 checks, including stratified per-group evaluations |
| `src/reasonsmith/demo.py` | End-to-end demonstration (ECOA/Reg B credit and GDPR Art. 22 clinical) |
| `src/reasonsmith/verdict.py` | Core lattice: evidence strength lattice (`unattainable < observed < probed < proved`) and verdict vocabulary |
| `src/reasonsmith/spec.py` | Core requirement loader & specification structures from `packs/*.toml` |
| `src/reasonsmith/sut.py` | System-under-test protocol — declared capability set and decision trace interface |
| `src/reasonsmith/report.py` | Conformance report skeleton, headline builder, and static unattainable analysis |
| `src/reasonsmith/adapters/` | SUT protocol adapters for JSONL decision logs and Python callables |
| `src/reasonsmith/engines/` | Verification engines: `record` completeness check and `observed` rtamt temporal monitor |
| `src/reasonsmith/cli.py` | Command-line interface: `check --system <log.jsonl> --pack <name>` |
| `src/reasonsmith/packs/table7.toml` | Table 7 rows restated as a formal requirement pack |
| `src/reasonsmith/packs/{eu_ai_act,gdpr,ecoa}.toml` | Statutory requirement packs with verbatim quotes from [`docs/legal-sources.md`](docs/legal-sources.md) |

### Core Components

- **The Emitter (`evidence.py`):** `emit(duty_id, decision_id, fields)` returns a record that is either `COMPLETE` or `INCOMPLETE`. An `INCOMPLETE` record explicitly names the fields it lacks. Nothing is defaulted, inferred, or silently dropped. Keys outside the duty's Table 7 row are rejected, and non-Table 7 data is isolated in `attachments`.
- **The Reason-Deletion Certificate (`certificate.py`):** Compares the reasons an engine actually used against exact inference ground truth (enumerated via WMC in `nesyarena`). Using deletion probes, it tests whether disabling isolated facts changes engine output. Two independent checks must pass: the deletion probe (every reason live) and the value check against the exact oracle. Reasons that cannot be probed in isolation are reported as uncertified (`INCONCLUSIVE`).
- **The Conformance Core (`verdict.py`, `report.py`):** A verdict carries the strength of the evidence behind it: `unattainable < observed < probed < proved`. This stage produces only the first two. `unattainable` is a set difference over SUT capabilities computed without running the system: a system that cannot emit reasons is reported unattainable on the requirements needing them, with the missing signals named. `observed` evaluates passive decision traces. `probed` and `proved` need engines this build does not have, so a requirement whose formalism no engine covers is reported as not evaluated — no strength and no verdict — rather than judged by a weaker check. Combining zero verdicts is `inconclusive`, never vacuously `satisfied`. Two engines exist: `record` (completeness over a decision trace) and `temporal` (rtamt monitors); `logical` requirements have no engine here.
- **Binding vs interpretive duties and regulatory scope:** Each requirement records whether it is a legally binding duty or an interpretive recital/guidance item, and any regulatory class it is limited to. The headline names both halves — `6 requirements · 4 binding: 2 observed, 2 unattainable · 2 interpretive: 2 observed` — so an interpretive item is reported without being counted as compliance evidence. A class-limited requirement is checked only against a system declared to be in that class via `--system-scope`; the class is never inferred, so an undeclared system has those requirements reported not applicable. Classes come from one fixed vocabulary — `prohibited`, `high-risk`, `limited-risk`, `minimal-risk`, `general-purpose` — which both a pack's `scope` and a declared `--system-scope` are checked against, after trimming whitespace and lowercasing and with nothing else guessed. A value outside it is a usage error naming what would have been accepted, so a misspelling on either side cannot become a duty that quietly never matches. A class the vocabulary knows but the chosen pack does not target is not an error: those duties are reported not applicable as a declared mismatch.
- **The CLI (`cli.py`):** Four packs ship — Table 7, EU AI Act, GDPR, ECOA/Reg B — and `reasonsmith.cli` runs one against a JSONL decision log:

  ```sh
  python -m reasonsmith.cli check --system decisions.jsonl --pack ecoa [--json]
  python -m reasonsmith.cli check --system decisions.jsonl --pack eu_ai_act --system-scope high-risk
  ```

  It exits 2 when a requirement is violated, 1 on a usage or input error, and 0 otherwise. Unattainable, not applicable and not evaluated are findings to read in the report, not breaches, so none of them changes the exit code. There is no report renderer beyond text/JSON. The CLI takes no capability declaration: it reads capabilities from the supplied log, and a result resting on that says so rather than speaking for the system. To declare them instead, construct `JSONLAdapter(path, declared_capabilities={...})` in Python.
- **Machine-Readable Output:** Records, certificates, and reports serialize to dicts (`to_dict()`) and JSON (`to_json(indent=None)`). Each carries the same facts as its text rendering, including its missing-field report and its own limits, so a downstream consumer cannot read a partial document as a complete one. Values outside JSON's own types are stringified rather than raising.
- **Dependencies:** `nesyarena` supplies ground-program IR, proof enumeration, and exact WMC (pinned to an immutable commit in `pyproject.toml`). `rtamt` supplies STL temporal monitoring. `torch` is an optional dependency of `nesyarena` (~1GB) and is deliberately not a declared dependency of `reasonsmith`.

### Summary of Empirical Findings

| Metric / Finding | Observed Result | Rationale & Mechanism |
|---|---|---|
| **Stratified Checks (Design A: Confidence Varies)** | Coverage gap: 0.0000<br>Fidelity gap: +0.0535<br>Retained share gap: +0.2802 | Top-k proof truncation keeps fixed proof count regardless of confidence scaling. Coverage remains identical across groups; retained share catches the atypical group's loss of value. |
| **Stratified Checks (Design B: Reason Multiplicity Varies)** | Coverage gap: +0.3000<br>Fidelity gap: +0.1472<br>Retained share gap: +0.1129 | Cases with more reasons suffer lower coverage under fixed k=1 truncation (a case with 5 reasons retains 1/5th; a case with 2 retains 1/2). |
| **Signal Stability (Drift across windows)** | Stability score: 0.3333 | Under top-1 settings, drift in a single signal silently swaps the stated reason across windows on an unchanged applicant file. |

## Limits

**Status: Early research software. Nothing here is a compliance guarantee, and none of it is legal advice.**

- A certificate speaks only about the specific program, base interpretation, and query tested.
- Table 7 completeness checks the **form** of a record, never the truth or accuracy of its contents.
- Static capability analysis (`unattainable`) checks declared or trace-derived signal names, not operational runtime correctness.

## Licence

[MIT](LICENSE)
