# GPAI Code of Practice mapping appendix

> **Non-executable appendix.** This document changes no verdict, duty, pack TOML, or executable
> surface. It is a navigation and honesty surface for `src/reasonsmith/packs/gpai.toml`.

This appendix maps the eight existing EU AI Act general-purpose-AI duties to measures in the
European Commission AI Office's voluntary General-Purpose AI Code of Practice. A mapping is not a
claim that the pack checks the Code measure: the pack remains the presence-only refinement recorded
in [`docs/refinement.md`](refinement.md). Measures listed in the final section have no corresponding
executable duty in the pack.

## Retrieval record

### General-Purpose AI Code of Practice — July 2025 edition

- **Document title:** *The General-Purpose AI Code of Practice* (three chapters: Transparency,
  Copyright, and Safety and Security).
- **Publisher:** European Commission, AI Office.
- **Edition / version identifier:** July 2025 publication, published 10 July 2025; chapter PDF
  document identifiers `118120` (Transparency), `118115` (Copyright), and `118119` (Safety and
  Security).
- **Official landing-page URL:** <https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai>
- **Retrieval date & time:** 2026-08-15 12:27 UTC.
- **Status:** The landing page identifies the Code as a voluntary tool and links the three chapter
  PDFs. The Code is guidance for demonstrating compliance; it is not itself an AI Act duty.

The chapter files were fetched from the official Commission newsroom endpoints below. The digests
cover the original PDF response bytes; no Code passage is quoted in this appendix, so no extracted
text is substituted for a pinned source.

| Chapter | Official PDF endpoint | Response | Raw SHA-256 |
|---|---|---|---|
| Transparency | <https://ec.europa.eu/newsroom/dae/redirection/document/118120> | HTTP 200, PDF, 441,142 bytes | `407e3a0a66327847a4bddb811fe619c8a588892ec451d23435d06485c20a4cf8` |
| Copyright | <https://ec.europa.eu/newsroom/dae/redirection/document/118115> | HTTP 200, PDF, 446,847 bytes | `cdb3c117e8e51282ab61fad8af9d5cd1acaf1773a5eadce178c3d10498ca864a` |
| Safety and Security | <https://ec.europa.eu/newsroom/dae/redirection/document/118119> | HTTP 200, PDF, 1,050,925 bytes | `d879f9b54c6068aae57ebaead9d90ddaa46f2503312b9185367a724fa8da2f4a` |

**Uncertainty / status flag:** The retrieval is verified against the official Commission landing page
and its linked PDF endpoints. PDF bytes were retained for the digest check. The appendix does not
reproduce the Code's prose; where a reader needs the operative wording, use the pinned chapter PDF.

## Existing duty to Code measure map

Measure names below are the chapter headings. The one-line rationale describes correspondence
only; it does not enlarge the executable property.

| Existing `gpai` duty | Code chapter and measure(s) | Why this corresponds |
|---|---|---|
| `eu_ai_act_art53_1_a_technical_documentation` | Transparency 1.1 — Drawing up and keeping up-to-date model documentation | Both concern maintaining the model documentation that records the provider's technical and evaluation information. |
| `eu_ai_act_art53_1_b_downstream_documentation` | Transparency 1.2 — Providing relevant information | Both concern making model information available to downstream providers and the authorities that may request it. |
| `eu_ai_act_art53_1_c_copyright_policy` | Copyright 1.1 — Draw up, keep up-to-date and implement a copyright policy; Copyright 1.3 — Identify and comply with rights reservations when crawling the World Wide Web | The policy and rights-reservation signals are the pack's narrow artefact counterpart to these two Code measures. |
| `eu_ai_act_art53_1_d_training_content_summary` | Transparency 1.2 — Providing relevant information | The measure discusses information that may be included in the public training-content summary; the correspondence is limited because the pack only checks summary and template artefacts. |
| `eu_ai_act_art55_1_a_model_evaluation` | Safety and Security 3.2 — Model evaluations | The evaluation-results and adversarial-testing records correspond to the Code's model-evaluation process. |
| `eu_ai_act_art55_1_b_systemic_risk_assessment` | Safety and Security 2.1 — Systemic risk identification process; Safety and Security 5.1 — Appropriate safety mitigations | The two pack artefacts name the assessment and mitigation activities, without testing their method, quality, or effect. |
| `eu_ai_act_art55_1_c_serious_incident_reporting` | Safety and Security 9.2 — Relevant information for serious incident tracking, documentation, and reporting | The incident record, report, and corrective-measures signals correspond to the Code's tracking, documentation, and reporting record. |
| `eu_ai_act_art55_1_d_cybersecurity_protection` | Safety and Security 6.1 — Security Goal; Safety and Security 6.2 — Appropriate security mitigations | The two protection statements correspond to defining the security objective and implementing mitigations, but presence does not assess adequacy. |

## Code measures with no corresponding executable duty

These measures are not silently treated as covered by a nearby presence check. Each gap is a
measure-level statement of why the existing pack cannot formalise it under its bar.

### Transparency chapter

| Code measure | Honest gap |
|---|---|
| Transparency 1.3 — Ensuring quality, integrity, and security of information | No executable duty checks document quality, integrity, retention as evidence, or protection from alteration; these are process and control claims. |

### Copyright chapter

| Code measure | Honest gap |
|---|---|
| Copyright 1.2 — Reproduce and extract only lawfully accessible copyright-protected content when crawling the World Wide Web | The measure depends on the crawler's conduct, access conditions, and changing external website and court/public-authority facts; the pack has no stable event or corpus signal for them. |
| Copyright 1.4 — Mitigate the risk of copyright-infringing outputs | Risk mitigation and output infringement require substantive, context-dependent assessment rather than the existence of the policy artefact. |
| Copyright 1.5 — Designate a point of contact and enable the lodging of complaints | A complaint channel, diligent handling, and reasonable-time response are process obligations with no stable pack trigger or decision-record witness. |

### Safety and Security chapter

| Code measure | Honest gap |
|---|---|
| Safety and Security 1.1 — Creating the Framework | A framework's state of the art, trigger design, acceptance criteria, and planned processes are governance prose, not a stable executable predicate. |
| Safety and Security 1.2 — Implementing the Framework | Continuous lifecycle assessment and trigger-point operation require process history and model-lifecycle events the pack does not receive. |
| Safety and Security 1.3 — Updating the Framework | Update timing, adequacy, material undermining, and changelog practice are process and self-assessment claims with no pack signal. |
| Safety and Security 1.4 — Framework notifications | Notification to the AI Office within a specified business-day period is a disclosure and timing duty; the pack has neither a recipient-confirmed event nor a reliable clock. |
| Safety and Security 2.2 — Systemic risk scenarios | Scenario completeness and relevance depend on open-ended risk analysis, not on the presence of the pack's assessment record. |
| Safety and Security 3.1 — Model-independent information | Literature, incident, market, expert, and participatory research inputs are an open-ended evidence-gathering process with no stable completeness boundary. |
| Safety and Security 3.3 — Systemic risk modelling | Modelling method and scenario quality are open-textured analytical judgements; a modelled-risk artefact would not establish either. |
| Safety and Security 3.4 — Systemic risk estimation | Probability, severity, uncertainty, and the accepted estimation format require a substantive risk assessment and authority, not a presence check. |
| Safety and Security 3.5 — Post-market monitoring | Monitoring methods, feedback, incidents, and near misses require an ongoing lifecycle trace and do not have a stable single-decision trigger. |
| Safety and Security 4.1 — Systemic risk acceptance criteria and acceptance determination | Acceptability thresholds, safety margins, and justifications are self-assessment-shaped and open-textured; the pack supplies no independent authority for them. |
| Safety and Security 4.2 — Proceeding or not proceeding based on systemic risk acceptance | The decision to proceed depends on the preceding risk determination and residual-risk judgement, neither of which the pack can independently settle. |
| Safety and Security 7.1 — Model description and behaviour | The required Model Report contents are broad descriptive documentation, including architecture, data, intended use, and specification; no stable executable boundary selects completeness. |
| Safety and Security 7.2 — Reasons for proceeding | Acceptability justifications and conditions under which they cease to hold are reasoned self-assessments, not a Boolean record property. |
| Safety and Security 7.3 — Documentation of systemic risk identification, analysis, and mitigation | The measure requires detailed results, assumptions, scores, comparisons, and descriptions; presence of an evaluation result cannot establish this content. |
| Safety and Security 7.4 — External reports | Whether external evaluators and reports exist, qualify, and may be published depends on facts and confidentiality conditions outside the pack evidence model. |
| Safety and Security 7.5 — Material changes to the systemic risk landscape | Materiality and changing state of the art require longitudinal technical assessment with no stable pack trigger. |
| Safety and Security 7.6 — Model Report updates | The update trigger is reasonable grounds that a justification was materially undermined, an open-textured and lifecycle-dependent judgement. |
| Safety and Security 7.7 — Model Report notifications | Providing an unredacted report to the AI Office, including the permitted delay, is a recipient-specific disclosure and timing process absent from the pack. |
| Safety and Security 8.1 — Definition of clear responsibilities | Organisational responsibility allocation is governance prose and is not evidenced by a model decision record. |
| Safety and Security 8.2 — Allocation of appropriate resources | The appropriateness of human, financial, information, and computational resources is a self-assessment with no objective threshold in the pack. |
| Safety and Security 8.3 — Promotion of a healthy risk culture | Risk culture, incentives, independence, and non-retaliation are organisational process claims with no stable executable trigger. |
| Safety and Security 9.1 — Methods for serious incident identification | The methods and third-party reporting channels used to identify incidents are process choices; the pack only records an incident artefact after the fact. |
| Safety and Security 9.3 — Reporting timelines | The Code supplies event-dependent reporting deadlines, while the existing duty deliberately does not invent a clock or accept a system-declared deadline. |
| Safety and Security 9.4 — Retention period | Five-year retention is a longitudinal records-management fact, not observable from the pack's single presence-oriented record. |
| Safety and Security 10.1 — Additional documentation | Architecture, integration, detailed evaluation strategies, mitigation choices, process decisions, and ten-year retention exceed the existing evaluation-record presence signals. |
| Safety and Security 10.2 — Public transparency | Publication, summaries, exceptions for risk and sensitive information, and update decisions are disclosure and judgement claims with no executable pack witness. |

This inventory is intentionally conservative. A future executable duty would need a stable,
verbatim-anchored trigger and an evidence surface that can answer it without turning a provider's own
self-assessment into the verdict.
