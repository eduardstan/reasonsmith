# Assurance crosswalk: NIST AI RMF 1.0 and ISO/IEC 42001:2023

> **Navigation only.** This is a pointer from two assurance frameworks to reasonsmith's
> existing packs and evidence machinery. It is **not** a conformance claim, certification
> support, or legal advice. It changes no verdict and cannot replace either framework's
> governance, assessment, or management work.

A reference in this document means that a reasonsmith run can produce evidence useful to a
reader of that framework. It does not mean that the framework's outcome has been achieved.
`partially` is intentional: the table names the missing part in the same line. A reasonsmith
`Strength` (`observed`, `recounted`, `probed`, or `proved`) is an evidence rung, not a
confidence score or an assurance-framework maturity level. `EvidenceBasis` (`behavioural`,
`relational`, `artifact`, or `assessment`) says what the evidence is about; it is not another
rank. `satisfied`, `violated`, `not applicable`, `unattainable`, and `not evaluated` retain the
meanings in [`semantics.md`](semantics.md), and none is a certification result.

## Retrieval records

### NIST AI RMF 1.0

- **Document:** *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*,
  NIST AI 100-1 (January 2023).
- **Publisher and official source:** National Institute of Standards and Technology,
  [NIST AI RMF 1.0 PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf),
  DOI [`10.6028/NIST.AI.100-1`](https://doi.org/10.6028/NIST.AI.100-1).
- **Retrieved:** 2026-08-15 12:26 UTC.
- **Retrieval status:** the official PDF returned successfully; SHA-256 of the retrieved
  bytes was `7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1`.
- **Use here:** the four function, category, and subcategory identifiers and titles below
  are transcribed from Tables 1–4. The mapping is reasonsmith's assessment of scope, not a
  NIST-produced profile.

### ISO/IEC 42001:2023

- **Document:** *ISO/IEC 42001:2023 Information technology — Artificial intelligence —
  Management system*.
- **Publisher and official source:** International Organization for Standardization,
  [ISO standard record](https://www.iso.org/standard/81230.html).
- **Retrieved:** 2026-08-15 12:26 UTC.
- **Retrieval status:** the ISO landing page and publicly available title indexes were
  reachable, but the complete ISO/IEC 42001 text was **not retrievable** here because it is
  paywalled. This document therefore pins only publicly available clause and Annex A
  identifiers and titles. It reproduces no paywalled normative text and does not paraphrase
  the paywalled standard from memory.
- **Public title index used for Annex A identifiers/titles:** [ISO 42001 Annex A control
  index](https://iso42001toolkit.com/iso-42001-annex-a-controls.html), retrieved 2026-08-15
  12:26 UTC. This is a title index, not an ISO source or an authority for interpretation.

## NIST AI RMF 1.0 crosswalk

The strongest direct anchor is the shipped Table 7 row
`nist_ai_rmf_risk_evidence`: `continuous_monitoring_logs`,
`metric_thresholds_and_alerts`, `reviews_and_sign_offs`, and `incident_tickets`. It is a
`record` duty and therefore normally reaches the `observed` behavioural rung when those
fields are present in the supplied evidence. Table 7's `lifecycle_placement` names RMF
`Govern–Map–Measure–Manage` as the placement; that label does not turn the row into an RMF
assessment. The other shipped packs provide narrower technical properties: `ecoa`, `gdpr`,
`eu_ai_act`, `gpai`, `seoul_frontier_ai_safety_2024`, and `table7`.

The rows below cover every AI RMF 1.0 subcategory. “No coverage” means no shipped duty or
engine checks that framework activity. “Partial” means the named reasonsmith evidence may be
an input to that activity, but something material remains outside the tool.

| Function / category | Subcategory (NIST title) | What reasonsmith offers |
|---|---|---|
| GOVERN 1 | GOVERN 1.1 — Legal and regulatory requirements | **Partial:** pack `source`/`verbatim_text`, `docs/legal-sources.md`, and `docs/refinement.md` preserve a formalisation trail; no organizational legal register or implementation process. |
| GOVERN 1 | GOVERN 1.2 — Characteristics of trustworthy AI in policies | **No coverage:** packs formalize selected duties; no policy control. |
| GOVERN 1 | GOVERN 1.3 — Risk-management activity by risk tolerance | **No coverage:** no risk-tolerance procedure or activity sizing. |
| GOVERN 1 | GOVERN 1.4 — Transparent risk-management policies and controls | **Partial:** report JSON/text/HTML exposes checked duties, limits, and evidence; no organizational policy or control framework. |
| GOVERN 1 | GOVERN 1.5 — Monitoring and periodic review of risk management | **No coverage:** a run is not a recurring governance review. |
| GOVERN 1 | GOVERN 1.6 — AI-system inventory | **No coverage:** reasonsmith does not inventory deployments. |
| GOVERN 1 | GOVERN 1.7 — Safe decommissioning and phasing out | **No coverage:** no decommissioning control or operational procedure. |
| GOVERN 2 | GOVERN 2.1 — Documented roles, responsibilities, and communication | **No coverage:** adapters and report audiences are not organizational accountability structures. |
| GOVERN 2 | GOVERN 2.2 — AI risk-management training | **No coverage:** no training register or competence check. |
| GOVERN 2 | GOVERN 2.3 — Executive responsibility | **No coverage:** a `signer` field in a Table 7 record is evidence of a supplied field, not executive accountability. |
| GOVERN 3 | GOVERN 3.1 — Diverse teams inform lifecycle decisions | **No coverage:** no workforce or participation assessment. |
| GOVERN 3 | GOVERN 3.2 — Human–AI roles and oversight | **Partial:** `ecoa` has a counterfactual treatment property and the packs can require human-intervention fields; no oversight design or operating process. |
| GOVERN 4 | GOVERN 4.1 — Critical-thinking and safety-first culture | **No coverage:** no culture assessment. |
| GOVERN 4 | GOVERN 4.2 — Documentation and communication of risks and impacts | **Partial:** pack rationale, source, refinement rows, and report findings document selected formal risks; no broad impact communication. |
| GOVERN 4 | GOVERN 4.3 — Testing, incidents, and information sharing | **Partial:** engines test declared properties and can emit witnesses; incident management and information-sharing processes are absent. |
| GOVERN 5 | GOVERN 5.1 — External feedback on individual and societal impacts | **No coverage:** no consultation or feedback channel. |
| GOVERN 5 | GOVERN 5.2 — Incorporation of adjudicated feedback | **No coverage:** no adjudication workflow. |
| GOVERN 6 | GOVERN 6.1 — Third-party AI risks and rights | **No coverage:** no supplier or third-party risk process. |
| GOVERN 6 | GOVERN 6.2 — Third-party failure and incident contingency | **No coverage:** no contingency plan. |
| MAP 1 | MAP 1.1 — Intended purposes, uses, context, laws, and expectations | **Partial:** pack `scope`, `domains`, `rationale`, and source fields state a selected duty's context; the system's real context and impacts are not validated. |
| MAP 1 | MAP 1.2 — Interdisciplinary actors and competencies | **No coverage:** no team or expertise record. |
| MAP 1 | MAP 1.3 — Mission and relevant AI goals | **No coverage:** no organizational mission mapping. |
| MAP 1 | MAP 1.4 — Business value or business-use context | **No coverage:** no business-use assessment. |
| MAP 1 | MAP 1.5 — Organizational risk tolerances | **No coverage:** pack thresholds are property inputs, not an organizational risk tolerance. |
| MAP 1 | MAP 1.6 — Requirements and socio-technical design implications | **Partial:** `spec`/`rationale` and `docs/refinement.md` make selected formal requirements explicit; no socio-technical requirements process. |
| MAP 2 | MAP 2.1 — Tasks and methods supported by the AI system | **Partial:** `formalism`, adapters, and system declarations describe the evidence surface, not a complete task/model categorization. |
| MAP 2 | MAP 2.2 — Knowledge limits and human use/oversight | **Partial:** report limits, missing signals, budgets, and refusal semantics state what the run cannot establish; no deployment-use documentation. |
| MAP 2 | MAP 2.3 — Scientific integrity and TEVV considerations | **Partial:** `proved`, `probed`, `observed`, and `certificate` procedures are reproducible machinery; no data representativeness or construct-validation program. |
| MAP 3 | MAP 3.1 — Potential benefits and performance | **No coverage:** no benefit assessment. |
| MAP 3 | MAP 3.2 — Potential costs of errors and trustworthiness | **Partial:** violated witnesses and `semantic_laws`/certificate measurements expose selected technical failures; no cost or risk-tolerance analysis. |
| MAP 3 | MAP 3.3 — Targeted application scope | **Partial:** `system_domains` and regulatory-class gates state declared reach; reasonsmith does not validate the declarations against deployment. |
| MAP 3 | MAP 3.4 — Operator proficiency and standards | **No coverage:** no proficiency or certification process. |
| MAP 3 | MAP 3.5 — Human oversight processes | **No coverage:** no oversight procedure assessment. |
| MAP 4 | MAP 4.1 — Technology, legal, and third-party component risks | **Partial:** pack sources and `provenance_*` signals support traceability; no component or supplier risk map. |
| MAP 4 | MAP 4.2 — Internal controls for system components | **Partial:** formal properties and evidence requirements are checkable controls for selected duties; no complete component control inventory. |
| MAP 5 | MAP 5.1 — Likelihood and magnitude of impacts | **No coverage:** no population impact or likelihood model. |
| MAP 5 | MAP 5.2 — Engagement and feedback on impacts | **No coverage:** no engagement process. |
| MEASURE 1 | MEASURE 1.1 — Methods and metrics selected and applied | **Partial:** each pack `spec` selects a property and the report records its engine/rung/basis; no organization-level metric-selection process. |
| MEASURE 1 | MEASURE 1.2 — Metric and control effectiveness reviewed | **Partial:** `validate-pack --analyse` can perform pack analysis and mutation findings for rule systems; it is not regular control review. |
| MEASURE 1 | MEASURE 1.3 — Independent and domain-expert assessment | **No coverage:** no independence or consultation control. |
| MEASURE 2 | MEASURE 2.1 — TEVV sets, metrics, and tools documented | **Partial:** report details, probe budgets, witnesses, and the evidence machinery identify how a duty was answered; no general TEVV dossier. |
| MEASURE 2 | MEASURE 2.2 — Representative human-subject evaluation | **No coverage:** traces are not shown to be representative and no human-subject review exists. |
| MEASURE 2 | MEASURE 2.3 — Performance/assurance criteria in deployment conditions | **Partial:** `observed`, `probed`, and `proved` answer selected properties at their evidence boundaries; no deployment validation or generalization claim. |
| MEASURE 2 | MEASURE 2.4 — Production functionality and behavior monitoring | **Partial:** a supplied trace can reach `observed`, and Table 7 names continuous-monitoring logs; reasonsmith does not operate the monitor or establish continuity. |
| MEASURE 2 | MEASURE 2.5 — Validity, reliability, and generalizability | **Partial:** rule/artefact semantics can be compared by `semantic_laws` and the GDPR deviation duty; no general reliability or generalizability study. |
| MEASURE 2 | MEASURE 2.6 — Safety and safe failure | **No coverage:** no safety case or fail-safe test. |
| MEASURE 2 | MEASURE 2.7 — Security and resilience | **No coverage:** no security or resilience assessment. |
| MEASURE 2 | MEASURE 2.8 — Transparency and accountability risks | **Partial:** EU AI Act, GDPR, ECOA, GPAI, and Table 7 packs check selected explanation, provenance, logging, and record fields; field presence is not transparency adequacy. |
| MEASURE 2 | MEASURE 2.9 — Explanation and contextual interpretation | **Partial:** explanation duties and `GroundProgramArtifact`/`ReasonTraceArtifact` measure selected reasons; no human comprehension or complete explanation assessment. |
| MEASURE 2 | MEASURE 2.10 — Privacy risk | **No coverage:** a privacy-related legal duty is not a privacy-risk assessment. |
| MEASURE 2 | MEASURE 2.11 — Fairness and bias | **Partial:** ECOA `ecoa_reg_b_1002_4_a_no_disparate_treatment` checks one-variable counterfactual invariance at `probed`/`proved` relational evidence; no disparate impact, proxy, group statistics, or calibration. |
| MEASURE 2 | MEASURE 2.12 — Environmental impact and sustainability | **No coverage:** no environmental measurement. |
| MEASURE 2 | MEASURE 2.13 — Effectiveness of TEVV metrics and processes | **No coverage:** pack analysis is not an evaluation of the RMF TEVV program. |
| MEASURE 3 | MEASURE 3.1 — Tracking existing, unanticipated, and emergent risks | **Partial:** repeated runs can be compared and reports retain witnesses; no risk register or emergent-risk process. |
| MEASURE 3 | MEASURE 3.2 — Risks difficult to measure or lacking metrics | **Partial:** `undetermined` and `graded` constructs refuse unsupported predicates rather than inventing a metric; no RMF risk-tracking method. |
| MEASURE 3 | MEASURE 3.3 — User/community problem reporting and appeal | **No coverage:** audience projections quote records but provide no appeal or feedback channel. |
| MEASURE 4 | MEASURE 4.1 — Contextual, expert-informed measurement approaches | **Partial:** pack authors record source, rationale, and deliberate omissions; no consultation-based measurement design. |
| MEASURE 4 | MEASURE 4.2 — Trustworthiness results validated by actors | **No coverage:** no actor validation. |
| MEASURE 4 | MEASURE 4.3 — Contextual improvement or decline | **Partial:** report and pack-analysis outputs can be inputs to a human comparison; reasonsmith does not attribute changes or document consultation. |
| MANAGE 1 | MANAGE 1.1 — Proceed/stop determination against intended purpose | **Partial:** a `violated` result is a technical finding that may inform a decision; reasonsmith does not make the organizational go/no-go determination. |
| MANAGE 1 | MANAGE 1.2 — Prioritized treatment of documented risks | **No coverage:** no prioritization or resource allocation. |
| MANAGE 1 | MANAGE 1.3 — Planned and documented responses | **Partial:** witnesses, limits, and remediation-oriented summaries identify what needs attention; no response plan. |
| MANAGE 1 | MANAGE 1.4 — Negative residual risks documented | **No coverage:** no aggregate residual-risk calculation. |
| MANAGE 2 | MANAGE 2.1 — Resources and non-AI alternatives | **No coverage:** no resource or alternative-system analysis. |
| MANAGE 2 | MANAGE 2.2 — Mechanisms sustaining deployed-system value | **No coverage:** no operational sustainment process. |
| MANAGE 2 | MANAGE 2.3 — Response and recovery from unknown risks | **No coverage:** no incident response or recovery process. |
| MANAGE 2 | MANAGE 2.4 — Supersede, disengage, or deactivate inconsistent systems | **No coverage:** no deployment control. |
| MANAGE 3 | MANAGE 3.1 — Third-party risk and benefit monitoring | **No coverage:** no third-party monitoring. |
| MANAGE 3 | MANAGE 3.2 — Monitoring pre-trained models | **No coverage:** no model-maintenance monitoring. |
| MANAGE 4 | MANAGE 4.1 — Post-deployment monitoring, appeal, incident, recovery, and change plans | **Partial:** Table 7 and report surfaces can carry logs, alerts, tickets, and change-control evidence; no plan, appeal, incident, or recovery workflow is checked. |
| MANAGE 4 | MANAGE 4.2 — Continual improvement with interested parties | **No coverage:** no continual-improvement system or engagement. |
| MANAGE 4 | MANAGE 4.3 — Communication and recovery for incidents/errors | **Partial:** report witnesses and `artifact_logs_serious_incident_*` fields can evidence selected records; no communication or recovery process. |

## ISO/IEC 42001:2023 crosswalk

ISO/IEC 42001 is an AI management-system standard. The AIMS clauses below are named for
navigation only; the full normative text was not retrieved (see the retrieval record above).
Reasonsmith can supply a technical evidence attachment for selected risks or controls, but it
does not implement an AIMS, a Statement of Applicability, or an ISO audit.

### AIMS clauses 4–10

| Clause | Public clause title | What reasonsmith offers |
|---|---|---|
| 4.1 | Understanding the organization and its context | **No coverage:** no organizational-context analysis. |
| 4.2 | Understanding the needs and expectations of interested parties | **No coverage:** no interested-party register or consultation. |
| 4.3 | Determining the scope of the AIMS | **Partial:** pack `scope`, regulatory class, `domains`, and system declarations make the run's declared scope visible; no AIMS scope determination. |
| 4.4 | AI management system | **No coverage:** reasonsmith is an evidence checker, not a management system. |
| 5.1 | Leadership and commitment | **No coverage:** no leadership process. |
| 5.2 | AI policy | **No coverage:** no policy authoring or approval. |
| 5.3 | Organizational roles, responsibilities, and authorities | **No coverage:** adapter declarations and report audiences do not assign organizational authority. |
| 6.1.1 | General | **No coverage:** no AIMS planning process. |
| 6.1.2 | AI risk assessment | **Partial:** formal pack properties, counterfactual checks, and artefact measurements assess selected technical questions; this is not an organizational AI risk assessment. |
| 6.1.3 | AI risk treatment | **No coverage:** no treatment plan. |
| 6.1.4 | AI system impact assessment | **Partial:** selected formal properties can be evidence for a technical question; reasonsmith does not assess impacts from intended use or foreseeable misuse. |
| 6.2 | AI objectives and planning to achieve them | **No coverage:** no objectives register or implementation plan. |
| 7.1 | Resources | **No coverage:** no AIMS resource planning. |
| 7.2 | Competence | **No coverage:** no competence or training evidence. |
| 7.3 | Awareness | **No coverage:** no awareness program. |
| 7.4 | Communication | **Partial:** report renderings and audience projections communicate a run's results and limits; no AIMS communication plan. |
| 7.5.1 | General (documented information) | **Partial:** reports, pack sources, refinement rows, and evidence records are durable technical information; no controlled AIMS document set. |
| 7.5.2 | Creating and updating documented information | **Partial:** generated documents and byte-pinned builders make selected project records reproducible; no organization document-control process. |
| 7.5.3 | Control of documented information | **Partial:** JSON schema, provenance notes, and generated-output tests control reasonsmith artifacts; no AIMS information-control process. |
| 8.1 | Operational planning and control | **No coverage:** no operational control process. |
| 8.2 | AI risk assessment | **Partial:** a run evaluates specified properties against a supplied evidence surface; it does not perform the AIMS risk-assessment cycle. |
| 8.3 | AI risk treatment | **No coverage:** no treatment implementation or follow-up. |
| 9.1 | Monitoring, measurement, analysis, and evaluation | **Partial:** the report records engine, `Strength`, `EvidenceBasis`, budgets, witnesses, and unresolved states; no management-system KPI program. |
| 9.2 | Internal audit | **No coverage:** a reasonsmith run is not an independent AIMS internal audit. |
| 9.3 | Management review | **No coverage:** no management review or decisions log. |
| 10.1 | Continual improvement | **No coverage:** no continual-improvement process. |
| 10.2 | Nonconformity and corrective action | **Partial:** `violated` findings and counterexamples identify selected technical nonconformities; no corrective-action workflow or effectiveness review. |

### Annex A control references

The following are the publicly indexed Annex A control titles only. Reasonsmith does not decide
which controls apply, does not produce a Statement of Applicability, and does not interpret the
paywalled control text.

| Control | Public control title | What reasonsmith offers |
|---|---|---|
| A.2.2 | AI policy | **No coverage:** no policy. |
| A.2.3 | Alignment with other organisational policies | **No coverage:** no policy-alignment review. |
| A.2.4 | Review of the AI policy | **No coverage:** no policy review cycle. |
| A.3.2 | AI roles and responsibilities | **No coverage:** no organizational role assignment. |
| A.3.3 | Reporting of concerns | **No coverage:** no concern-reporting channel. |
| A.4.2 | Resource documentation | **Partial:** provenance fields and report details document selected technical evidence; no complete resource register. |
| A.4.3 | Data resources | **Partial:** Table 7 and `eu_ai_act` duties can check supplied data/version/hash fields; no data-resource governance. |
| A.4.4 | Tooling resources | **No coverage:** no tooling inventory. |
| A.4.5 | System and computing resources | **No coverage:** no infrastructure inventory. |
| A.4.6 | Human resources | **No coverage:** no human-resource competence record. |
| A.5.2 | AI system impact assessment process | **No coverage:** a counterfactual property is not an impact-assessment process. |
| A.5.3 | Documentation of AI system impact assessments | **No coverage:** no impact-assessment record. |
| A.5.4 | Assessing AI system impacts on individuals or groups | **Partial:** ECOA counterfactual invariance checks one protected-variable treatment property; it does not assess impacts on people or groups. |
| A.5.5 | Assessing societal impacts of AI systems | **No coverage:** no societal-impact assessment. |
| A.6.1.2 | Objectives for responsible development of AI systems | **No coverage:** no development objectives. |
| A.6.1.3 | Processes for responsible design and development | **No coverage:** no design/development process. |
| A.6.2.2 | AI system requirements and specification | **Partial:** pack `spec` values are explicit test properties, not the system's complete requirements specification. |
| A.6.2.3 | Documentation of AI system design and development | **Partial:** `RulesAdapter`, `logic()`, inference artefacts, provenance, and Table 7 design-history fields can be inspected; no lifecycle documentation set. |
| A.6.2.4 | AI system verification and validation | **Partial:** `observed`, `probed`, and `proved` engines verify selected properties; no complete V&V program. |
| A.6.2.5 | AI system deployment | **No coverage:** no deployment control. |
| A.6.2.6 | AI system operation and monitoring | **Partial:** traces and Table 7 monitoring evidence can be checked; reasonsmith does not operate or continuously monitor the system. |
| A.6.2.7 | AI system technical documentation | **Partial:** pack sources, refinements, reports, and provenance provide selected technical documentation; not a complete technical file. |
| A.6.2.8 | AI system event logs | **Partial:** `eu_ai_act_art12_1_automatic_logging`, `eu_ai_act_art12_2_traceability_monitoring`, and Table 7 `eu_ai_act_art12_record_keeping` check selected log fields; no event-log control system. |
| A.7.2 | Data for development and enhancement of AI systems | **No coverage:** no development-data governance. |
| A.7.3 | Acquisition of data | **No coverage:** no lawful data-acquisition process. |
| A.7.4 | Quality of data for AI systems | **Partial:** data snapshot/hash and provenance fields can be required; no data-quality or representativeness assessment. |
| A.7.5 | Data provenance | **Partial:** `provenance_*`, model/data version IDs, and dataset snapshot hashes provide selected traceability; no full lineage process. |
| A.7.6 | Data preparation | **No coverage:** no preparation or labelling process. |
| A.8.2 | System documentation and information for users | **Partial:** EU AI Act/GDPR/ECOA and Table 7 explanation/documentation duties check selected records; no user-information adequacy determination. |
| A.8.3 | External reporting | **No coverage:** no external reporting process. |
| A.8.4 | Communication of incidents | **Partial:** GPAI incident-record/report fields can be checked for presence; no incident communication workflow. |
| A.8.5 | Information for interested parties | **Partial:** report renderings communicate findings to named audiences; no stakeholder-information program. |
| A.9.2 | Processes for responsible use of AI systems | **No coverage:** no responsible-use process. |
| A.9.3 | Objectives for responsible use of AI systems | **No coverage:** no responsible-use objectives. |
| A.9.4 | Intended use of the AI system | **Partial:** pack rationale, `scope`, `domains`, and system declarations expose the declared use relevant to a run; reasonsmith does not validate intended use or foreseeable misuse. |
| A.10.2 | Allocation of responsibilities | **No coverage:** no value-chain responsibility allocation. |
| A.10.3 | Suppliers | **No coverage:** no supplier-management process. |
| A.10.4 | Customers | **No coverage:** no customer-responsibility process. |

## Deliberate non-coverage inventory

These are not missing rows waiting for a hidden engine. They are boundaries of the product and of
the evidence model.

- **Organizational governance and policy:** reasonsmith checks formalized properties of a
  supplied system and record; it cannot establish leadership, roles, training, risk appetite,
  policy approval, or a management-system scope.
- **Risk ceremonies and prioritization:** no risk register, risk-owner meeting, treatment
  decision, residual-risk acceptance, management review, or corrective-action workflow is
  created by a report.
- **Lifecycle operations:** no procurement, design review, deployment approval, monitoring
  service, change board, decommissioning plan, incident response, recovery, or supplier
  oversight is operated or audited.
- **Impact assessment:** a formal property is not a fundamental-rights, societal, environmental,
  privacy, safety, or human-subject impact assessment. The single ECOA counterfactual duty is
  treatment invariance, not disparate impact; statistical fairness and proxy effects remain
  outside the shipped evidence model.
- **Population claims:** traces are not established as representative, and the `observed` rung
  is not a sampling confidence statement. A stronger evidence rung is not a stronger assurance
  framework claim.
- **Interpretive adequacy:** most shipped record duties check `present(signal)`. Presence of a
  reason, log, document, or metric is not proof that it is correct, sufficient, complete,
  comprehensible, or continuously maintained. Open-textured predicates remain refused or
  `not evaluated` rather than guessed.
- **System truth and declarations:** capabilities, domains, and claimed semantics are supplied
  by the audited system/adapter. `semantic_laws` and the artefact deviation duty measure some
  mismatches where the required artefact exists; they do not validate every declaration.
- **Certification and audit opinions:** report surfaces (`render_text`, JSON, HTML, and
  audience projections) expose results, limits, budgets, and witnesses. They are not an ISO
  certificate, an NIST profile attestation, an auditor independence statement, or a legal
  conclusion.

For the operational evidence contract, see [`semantics.md`](semantics.md). For the formal
strength/basis boundary, see [`theory/08-evidence.md`](theory/08-evidence.md). For the pack
refinements and their omissions, see [`refinement.md`](refinement.md). For the standing limits,
see [`what-this-does-not-do.md`](what-this-does-not-do.md).
