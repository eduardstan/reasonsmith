<h1><img src="docs/assets/mark.svg" alt="" width="40" valign="middle"> reasonsmith — evidence records and reason-deletion certificates for decision systems</h1>

[![tests](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/eduardstan/reasonsmith/actions/workflows/ci.yml)
[![Python >= 3.11](https://img.shields.io/badge/python->=3.11-blue.svg)](https://www.python.org/)
[![MIT licence](https://img.shields.io/github/license/eduardstan/reasonsmith)](https://github.com/eduardstan/reasonsmith/blob/main/LICENSE)

**reasonsmith answers one question:** given a system and a regulatory context, what is the minimal audit artefact each stakeholder needs, mechanically derived from that system and bounded by its evidence?

![One reason stated, five used, four struck](docs/assets/showcase-figure.svg)

![A conformance command and its findings](docs/assets/showcase-cast.svg)

On decision `APP-1042`, the system stated one reason while its inference used five. reasonsmith re-ran that inference, switched reasons off, and measured the four the answer did not depend on. The figure is generated from the run, not typed beside it; regenerate all showcase artefacts with [`docs/build_showcase.py`](docs/build_showcase.py).


## The organising question

What can this system honestly establish about this duty, and what can each audience take away from the evidence? A clause becomes a recorded formal property, then meets the evidence surface the system actually exposes. The result is not a pipeline: applicability comes first, evidence branches by available surface, and one finding can be read five ways.

```mermaid
flowchart TB
    clause(["A clause of law"]) --> quote(["Its verbatim text — retrieved and recorded"])
    quote --> formula(["A formal property — one recorded judgement per clause"])

    subgraph exposed["What the system exposes"]
        log["a log of decisions"]
        callable["a decide() you can re-run"]
        rules["declared logic()"]
        artefact["an inference artefact"]
    end

    formula --> reach{"Does this duty reach this system?"}
    exposed --> reach

    reach -->|"nothing declared to place it in scope"| na{{"not applicable"}}
    reach -->|"cannot emit the evidence the duty needs"| un[/"unattainable"/]
    reach -->|"it reaches"| ladder(["Every engine the property and the surface both allow"])

    ladder --> observed["observed — from a trace"]
    ladder --> recounted["recounted — reasons re-run"]
    ladder --> probed["probed — bounded replay"]
    ladder --> proved["proved — a solver over declared rules"]

    observed --> verdict
    recounted --> verdict
    probed --> verdict
    proved --> verdict

    verdict[["The strongest evidence wins — how far it was pushed, and what it is about"]]
    verdict --> five[["Five projections: developer · deployer · auditor · regulator · affected individual"]]

    classDef law fill:#eef3fb,stroke:#1f4f8f,color:#16181d
    classDef surface fill:#f4f1fa,stroke:#5b4a8a,color:#16181d
    classDef notapp fill:#fff4d6,stroke:#9a6700,color:#16181d
    classDef unattainable fill:#fde2e2,stroke:#a33a3a,color:#16181d
    classDef rung fill:#eaf6ef,stroke:#1d6b45,color:#16181d
    classDef outcome fill:#ffffff,stroke:#16181d,color:#16181d

    class clause,quote,formula law
    class log,callable,rules,artefact surface
    class na notapp
    class un unattainable
    class observed,recounted,probed,proved rung
    class ladder,verdict,five outcome
```

The rung is decided by what the system exposes and what the property permits; an auditor cannot choose a stronger engine. **Unattainable** means the system cannot emit the evidence the duty needs. **Not applicable** means the system has not declared the regulatory class or decision domain to which the duty is limited. They are different answers, not interchangeable failures.

This tree ships **five packs**, **seven engines**, and **twenty-nine shipped requirements**. The machine-readable source and every destination are listed in [`docs/README.md`](docs/README.md).

## Five reading paths

The same evidence is projected for different duties:

- **Developer:** [`docs/adopting.md`](docs/adopting.md) → [`docs/language.md`](docs/language.md) → [`docs/semantics.md`](docs/semantics.md) → [`docs/formal.md`](docs/formal.md) → [`docs/refinement.md`](docs/refinement.md) → [`docs/authoring-engines.md`](docs/authoring-engines.md).
- **Deployer:** [`docs/adopting.md`](docs/adopting.md) → [`docs/three-systems.md`](docs/three-systems.md) → [`docs/semantics.md`](docs/semantics.md) → [`docs/authoring-packs.md`](docs/authoring-packs.md) → [`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md).
- **Auditor:** [`docs/example-output.md`](docs/example-output.md) → [`docs/semantics.md`](docs/semantics.md) → [`docs/sufficient-reasons.md`](docs/sufficient-reasons.md) → [`docs/refinement.md`](docs/refinement.md) → [`docs/findings-nesyarena.md`](docs/findings-nesyarena.md).
- **Regulator:** [`docs/legal-sources.md`](docs/legal-sources.md) → [`docs/refinement.md`](docs/refinement.md) → [`docs/formal.md`](docs/formal.md) → [`docs/semantics.md`](docs/semantics.md) → [`docs/findings-nesyarena.md`](docs/findings-nesyarena.md).
- **Affected individual:** [`docs/example-output.md`](docs/example-output.md) → [`docs/semantics.md`](docs/semantics.md) §7 → [`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) → [`docs/adopting.md`](docs/adopting.md).

## Install and run

Install from PyPI:

```sh
pip install reasonsmith
```

![Terminal interface preview](artifacts/tui/tui-check/preview.gif)

*The terminal interface is not part of the Python distribution and requires Bun.* [Watch the recording](artifacts/tui/tui-check/demo.mp4) · [View the layout report](docs/tui/layout-report.png)

`--system-module` **imports and executes** the module it names, so point it only at code you trust; `--system` reads a decision log and runs nothing.

For a committed, runnable conformance example, this command's stdout is pinned below and regenerated by `python docs/build_readme_transcripts.py`:

```sh
reasonsmith check --system-module reasonsmith.demo:deployed_credit_system --pack ecoa --system-name TruncatingCreditSystem --audience regulator
```

```text
CONFORMANCE REPORT
system: TruncatingCreditSystem
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa
headline: 6 requirements · 6 binding: 3 observed, 1 violated, 1 not evaluated, 1 unattainable

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): satisfied
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    domain limit: consumer-credit
    summary: Observed over 2 decision(s): state monitor for 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' satisfied at every decision step.
  [PROBED] ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): violated
    evidence basis: artifact — this duty is measured against the inference artefact behind a decision rather than against what the system decided. No trace holds that artefact and the enumeration is exact only on the one artefact it ran over, so the rungs above unattainable are recounted and probed, and neither observed nor proved is reachable however much the system exposes. Which of the two a verdict reaches is a fact about the artefact and not about the search: probed measures a reason set enumerated from a model encoding, recounted measures one the system recounted about its own inference.
    domain limit: consumer-credit
    summary: Violated on 1 of 2 certified decision(s): the stated reasons are not all the reasons. On decision #1 exact inference found 5 reason(s) and the deletion probe showed the system's answer does not depend on 4 of them — C05 — Insufficient number of credit references provided; C03 — Delinquent past or present credit obligations; C04 — Too many recent inquiries on credit bureau report; C02 — Length of time credit has been established is too short. Attribution: The deleted reasons are exactly the 4 lowest-scoring of the 5, and the engine kept the top 1. This is the signature of top-k proof truncation at k=1: top-k works by discarding proofs, so the dropped reasons are lost by configuration, not by error. The missing probability mass is 0.225799. Measured against the inference artefact the system exposed, not read from its decision log.
    certificate finding: FAIL (decision 1)
    probe budget: 13 input(s) replayed, seed none — the proof enumeration and the deletion probes are deterministic, input space: decisions certified (2 values), decisions whose joint search did not finish (0 values), facts switched off (10 values), joint deletion patterns tried (1 values). Strategy: for each decision the system exposed an inference artefact for, its reasons are enumerated exactly by bounded proof enumeration over the ground program and scored by exact weighted model counting; every fact of a reason that no other reason uses is then switched off alone and the system's own engine re-run on the perturbed interpretation. A reason a single deletion moves the engine on is one its answer depends on. A reason no single deletion moves is then put to a second search, because two reasons jointly necessary and individually removable look exactly like two dropped ones: the subset-minimal *joint* deletions the engine notices are enumerated over the remaining facts, and a reason is counted here only where that enumeration ran to exhaustion and met no fact of it. The probe only ever switches a fact off, never on
  [UNATTAINABLE] ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
    domain limit: consumer-credit
    summary: Unattainable as built: the system declares no capability to emit artifact_logs_incompleteness_notice_sent, so no amount of testing can discharge this requirement. Determined from declared capabilities alone; the system was not executed.
  [NOT EVALUATED] ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive
    evidence basis: relational — this duty is a property of a pair of executions, and a decision record holds one. No length of decision log observes it, so the rungs it can reach are probed and proved; a system exposing only a log cannot discharge it, and that is a fact about the kind of property and not about how much the system exposed.
    domain limit: consumer-credit
    summary: Not evaluated: the system exposes no decide(), so there is no twin decision to run. A counterfactual is what the system would have decided, and a decision log records only what it did — no trace, however long, establishes one. Limit of this duty: it is invariance under one named variable holding all others fixed, so it is a property of treatment and says nothing about effects. A proxy is invisible to it — a rule set that never reads the protected variable and decides by postcode is satisfied here — and a disparate impact is not a thing it can find. It also reaches exactly one variable: a system answerable on several prohibited bases is answered here about the one this duty names.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

The same run can be projected for the affected individual, or a packaged JSONL trace can be checked without a checkout:
```sh
reasonsmith check --system-module reasonsmith.demo:deployed_credit_system --pack ecoa --system-name TruncatingCreditSystem --audience affected-individual
```

```text
CONFORMANCE REPORT
system: TruncatingCreditSystem
pack: ecoa

WHAT THE SYSTEM RECORDED ABOUT THE 2 DECISIONS IT LOGGED
    the decision it recorded: "adverse action on APP-1043"
    the reason it stated: "C01 — Income insufficient for amount of credit requested"
    the decision it recorded: "adverse action on APP-1042"
    the reason it stated: "C01 — Income insufficient for amount of credit requested"

WHETHER THOSE WERE ALL THE REASONS
    4 further reason(s) the system's own answer depended on were not stated. Measured by re-running its inference, not inferred from its log:
    "C05 — Insufficient number of credit references provided"
    "C03 — Delinquent past or present credit obligations"
    "C04 — Too many recent inquiries on credit bureau report"
    "C02 — Length of time credit has been established is too short"

WHAT THIS REPORT COULD NOT CHECK
    1 duty: the system supplied nothing any check here could read, so it was not checked either way.
    1 duty: no check in this report could settle it, so it was left open rather than answered.

REQUIREMENT FINDINGS:
  ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): satisfied
  ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
  ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
  ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): violated
  ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
  ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

```sh
reasonsmith check --system "$(python -m reasonsmith.examples)/sample_decisions.jsonl" --pack ecoa --system-name CreditScoringPipeline --system-domain consumer-credit
```

```text
CONFORMANCE REPORT
system: CreditScoringPipeline
declared scope: undeclared
declared domains: consumer-credit
pack: ecoa
headline: 6 requirements · 6 binding: 3 observed, 1 not evaluated, 2 unattainable

REQUIREMENT FINDINGS:
  [OBSERVED] ecoa_reg_b_1002_9_a_1_timing_of_notice (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(1)): satisfied
    requires: artifact_logs_decision_record, artifact_logs_notification_latency_days, artifact_logs_counteroffer_not_accepted
    domain limit: consumer-credit
    summary: Observed over 3 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) -> ((artifact_logs_notification_latency_days <= 30) or ((artifact_logs_counteroffer_not_accepted >= 0.5) and (artifact_logs_notification_latency_days <= 90))))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_a_2_written_statement (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(a)(2)): satisfied
    requires: artifact_logs_decision_record, provenance_model_version
    domain limit: consumer-credit
    summary: Observed over 3 decision(s): temporal monitor for 'always(present(artifact_logs_decision_record) and present(provenance_model_version) and (present(artifact_logs_reason_explanation) or present(artifact_logs_right_to_reasons_disclosure)))' satisfied at every decision step.
  [OBSERVED] ecoa_reg_b_1002_9_b_2_specific_reasons (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): satisfied
    requires: artifact_logs_reason_explanation, provenance_model_version, scope_statements_local_vs_global
    domain limit: consumer-credit
    summary: Observed over 3 decision(s): state monitor for 'present(artifact_logs_reason_explanation) -> ( present(provenance_model_version) and present(scope_statements_local_vs_global) and not contains(artifact_logs_reason_explanation, "internal standards") and not contains(artifact_logs_reason_explanation, "internal policies") and not contains(artifact_logs_reason_explanation, "failed to achieve a qualifying score"))' satisfied at every decision step.
  [UNATTAINABLE] ecoa_reg_b_1002_9_b_2_principal_reasons_complete (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(b)(2)): inconclusive
    evidence basis: artifact — this duty is measured against the inference artefact behind a decision rather than against what the system decided. No trace holds that artefact and the enumeration is exact only on the one artefact it ran over, so the rungs above unattainable are recounted and probed, and neither observed nor proved is reachable however much the system exposes. Which of the two a verdict reaches is a fact about the artefact and not about the search: probed measures a reason set enumerated from a model encoding, recounted measures one the system recounted about its own inference.
    requires: artifact_logs_reason_explanation, artifact_logs_deleted_reason_count
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_deleted_reason_count
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_deleted_reason_count, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [UNATTAINABLE] ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out (ECOA / Regulation B (12 CFR 1002.9) 12 CFR 1002.9(c)(2)): inconclusive
    requires: artifact_logs_incompleteness_notice_sent
    domain limit: consumer-credit
    MISSING SIGNALS: artifact_logs_incompleteness_notice_sent
    summary: Unattainable on the evidence supplied: no record in the supplied decision trace carries a value for artifact_logs_incompleteness_notice_sent, and the system declared no capabilities, so nothing here can discharge this requirement. Read from that trace alone; a longer trace could show the system emitting these signals.
  [NOT EVALUATED] ecoa_reg_b_1002_4_a_no_disparate_treatment (ECOA / Regulation B (12 CFR 1002.4) 12 CFR 1002.4(a)): inconclusive
    evidence basis: relational — this duty is a property of a pair of executions, and a decision record holds one. No length of decision log observes it, so the rungs it can reach are probed and proved; a system exposing only a log cannot discharge it, and that is a fact about the kind of property and not about how much the system exposed.
    requires: artifact_logs_decision_record, applicant_prohibited_basis
    domain limit: consumer-credit
    summary: Not evaluated: the system exposes no decide(), so there is no twin decision to run. A counterfactual is what the system would have decided, and a decision log records only what it did — no trace, however long, establishes one. Limit of this duty: it is invariance under one named variable holding all others fixed, so it is a property of treatment and says nothing about effects. A proxy is invisible to it — a rule set that never reads the protected variable and decides by postcode is satisfied here — and a disparate impact is not a thing it can find. It also reaches exactly one variable: a system answerable on several prohibited bases is answered here about the one this duty names.

LIMITS OF THIS REPORT
  This report is not a compliance guarantee and is not legal advice. It assesses system capability information and trace evidence against formal specifications. Whether these findings discharge legal duties remains a determination this tool does not make and cannot make. A requirement reported without a strength was not evaluated or is not applicable, and no verdict on it should be read from this report. Recital and guidance items inform how statutory duties are interpreted but create no obligation of their own; interpretive requirements are evaluated and reported separately, and are never folded into the binding headline counts. A requirement reported not applicable was excluded on one of two independent gates. Either no regulatory class was declared for the system at all, or the class that was declared is not the one the requirement is limited to; or no decision domain was declared for the system at all, or none of the domains that were declared is one the requirement is about. This tool infers neither the class nor the domain, so an undeclared system is neither placed in scope nor cleared of the duty: read the declared scope and domain lines before reading a not-applicable result. The decision-domain vocabulary is written by the pack author and by no regulation, and a duty declaring no domain reaches every system it is run against.
```

`check` emits text, JSON, or self-contained HTML; it exits 2 for a violation, 1 for usage/input errors, and 0 otherwise.

## Limits

- This is an evidence checker, not a compliance guarantee or legal advice; whether a finding discharges a legal duty remains outside the tool.
- `unattainable`, `not applicable`, and `not evaluated` are distinct findings, not breaches or weaker satisfied results.
- `observed` speaks only about supplied records; `probed` is bounded replay; `proved` covers the declared logic's admitted inputs. A rung is evidence strength, not a compliance grade or confidence score.
- The system's declarations are trusted inputs. An inference artefact must declare monotonicity; a false declaration is reported not evaluated.
- Group-statistical fairness, proxies, disparate impact, open-textured predicates, and legal interpretation beyond the formalised clause are outside this evidence model.
- The certificate measures reason deletion only when the system exposes a suitable inference artefact; a log-only system cannot be upgraded by its adapter.

Read the full boundaries in [`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) and the soundness obligations in [`docs/semantics.md`](docs/semantics.md) §3.

The full destination map is [`docs/README.md`](docs/README.md); the live dossier is [reasonsmith.dev/report.html](https://reasonsmith.dev/report.html); empirical measurements are in [`RESULTS.md`](RESULTS.md), the backlog in [`ROADMAP.md`](ROADMAP.md), and contribution rules in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
