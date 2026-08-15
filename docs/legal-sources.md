# Official Statutory Text Findings & Provenance Report

## Document Overview
- **Purpose:** Provide exact, verbatim statutory texts for Reasonsmith's regulation packs from official legal sources, along with citation metadata, retrieval timestamps, notes on statutory hierarchy, and verbatim operative demands.
- **Date of Retrieval:** 2026-07-31

### Drift-check source formats
The statute-drift checker supports the recorded Cellar XHTML and eCFR XML formats above, and a
PDF route for future PDF-only sources. PDF retrieval keeps the fetched bytes and verifies the
SHA-256 beside each result as corroboration, then uses the optional, exactly pinned `pdfminer.six`
release to extract text deterministically. Only whitespace is normalized before the existing
character-for-character quote match; encrypted PDFs, PDFs without an extractable text layer,
extractor-version drift, and every extraction error are refused as `could-not-verify`. The route
never performs OCR, and a digest never substitutes for quotation matching.

---

## Provision 1: EU AI Act — Regulation (EU) 2024/1689

### Metadata & Citation
- **Document Title:** Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act)
- **CELEX Identifier:** `32024R1689` (Consolidated CELEX: `02024R1689-20240712`)
- **Official Source URL:** [EUR-Lex Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
- **Direct EU Cellar XHTML Endpoint:** `http://publications.europa.eu/resource/cellar/dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.03/DOC_1`
- **Publication Date:** 12 July 2024 (OJ L, 2024/1689)
- **Entry into Force Date:** 1 August 2024 (20 days after publication, under Article 113)
- **Retrieval Date & Time:** 2026-07-31 09:52:00 UTC+2
- **Re-retrieval for Articles 53 and 55 (quoted by `src/reasonsmith/packs/gpai.toml`):** 2026-08-02. The same Cellar XHTML endpoint was fetched again and the `053.001` and `055.001` divisions transcribed below. Articles 53 and 55 were **not** covered by the 2026-07-31 retrieval, which recorded Articles 12 and 13 only: the CELEX identifier being already recorded establishes the *document*, not any particular provision of it, so this record was extended before the GPAI pack quoted a word of either Article.
- **Uncertainty / Status Flag:** Verified against official EU Cellar XHTML. Direct EUR-Lex web frontend requests return a WAF HTTP 202 challenge; retrieved directly via official EU Publications Cellar XHTML API endpoint `dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.03/DOC_1`.

---

### Verbatim Text

#### Article 12
**Record-keeping**

1. High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system.

2. In order to ensure a level of traceability of the functioning of a high-risk AI system that is appropriate to the intended purpose of the system, logging capabilities shall enable the recording of events relevant for:
   (a) identifying situations that may result in the high-risk AI system presenting a risk within the meaning of Article 79(1) or in a substantial modification;
   (b) facilitating the post-market monitoring referred to in Article 72; and
   (c) monitoring the operation of high-risk AI systems referred to in Article 26(5).

3. For high-risk AI systems referred to in point 1 (a), of Annex III, the logging capabilities shall provide, at a minimum:
   (a) recording of the period of each use of the system (start date and time and end date and time of each use);
   (b) the reference database against which input data has been checked by the system;
   (c) the input data for which the search has led to a match;
   (d) the identification of the natural persons involved in the verification of the results, as referred to in Article 14(5).

---

#### Article 13
**Transparency and provision of information to deployers**

1. High-risk AI systems shall be designed and developed in such a way as to ensure that their operation is sufficiently transparent to enable deployers to interpret a system’s output and use it appropriately. An appropriate type and degree of transparency shall be ensured with a view to achieving compliance with the relevant obligations of the provider and deployer set out in Section 3.

2. High-risk AI systems shall be accompanied by instructions for use in an appropriate digital format or otherwise that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers.

3. The instructions for use shall contain at least the following information:
   (a) the identity and the contact details of the provider and, where applicable, of its authorised representative;
   (b) the characteristics, capabilities and limitations of performance of the high-risk AI system, including:
       (i) its intended purpose;
       (ii) the level of accuracy, including its metrics, robustness and cybersecurity referred to in Article 15 against which the high-risk AI system has been tested and validated and which can be expected, and any known and foreseeable circumstances that may have an impact on that expected level of accuracy, robustness and cybersecurity;
       (iii) any known or foreseeable circumstance, related to the use of the high-risk AI system in accordance with its intended purpose or under conditions of reasonably foreseeable misuse, which may lead to risks to the health and safety or fundamental rights referred to in Article 9(2);
       (iv) where applicable, the technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output;
       (v) when appropriate, its performance regarding specific persons or groups of persons on which the system is intended to be used;
       (vi) when appropriate, specifications for the input data, or any other relevant information in terms of the training, validation and testing data sets used, taking into account the intended purpose of the high-risk AI system;
       (vii) where applicable, information to enable deployers to interpret the output of the high-risk AI system and use it appropriately;
   (c) the changes to the high-risk AI system and its performance which have been pre-determined by the provider at the moment of the initial conformity assessment, if any;
   (d) the human oversight measures referred to in Article 14, including the technical measures put in place to facilitate the interpretation of the outputs of the high-risk AI systems by the deployers;
   (e) the computational and hardware resources needed, the expected lifetime of the high-risk AI system and any necessary maintenance and care measures, including their frequency, to ensure the proper functioning of that AI system, including as regards software updates;
   (f) where relevant, a description of the mechanisms included within the high-risk AI system that allows deployers to properly collect, store and interpret the logs in accordance with Article 12.

---

#### Article 53
**Obligations for providers of general-purpose AI models**

1. Providers of general-purpose AI models shall:
   (a) draw up and keep up-to-date the technical documentation of the model, including its training and testing process and the results of its evaluation, which shall contain, at a minimum, the information set out in Annex XI for the purpose of providing it, upon request, to the AI Office and the national competent authorities;
   (b) draw up, keep up-to-date and make available information and documentation to providers of AI systems who intend to integrate the general-purpose AI model into their AI systems. Without prejudice to the need to observe and protect intellectual property rights and confidential business information or trade secrets in accordance with Union and national law, the information and documentation shall:
       (i) enable providers of AI systems to have a good understanding of the capabilities and limitations of the general-purpose AI model and to comply with their obligations pursuant to this Regulation; and
       (ii) contain, at a minimum, the elements set out in Annex XII;
   (c) put in place a policy to comply with Union law on copyright and related rights, and in particular to identify and comply with, including through state-of-the-art technologies, a reservation of rights expressed pursuant to Article 4(3) of Directive (EU) 2019/790;
   (d) draw up and make publicly available a sufficiently detailed summary about the content used for training of the general-purpose AI model, according to a template provided by the AI Office.

---

#### Article 55
**Obligations of providers of general-purpose AI models with systemic risk**

1. In addition to the obligations listed in Articles 53 and 54, providers of general-purpose AI models with systemic risk shall:
   (a) perform model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing of the model with a view to identifying and mitigating systemic risks;
   (b) assess and mitigate possible systemic risks at Union level, including their sources, that may stem from the development, the placing on the market, or the use of general-purpose AI models with systemic risk;
   (c) keep track of, document, and report, without undue delay, to the AI Office and, as appropriate, to national competent authorities, relevant information about serious incidents and possible corrective measures to address them;
   (d) ensure an adequate level of cybersecurity protection for the general-purpose AI model with systemic risk and the physical infrastructure of the model.

---

### Factual Summary of Demands (Law's Operative Words)
- **What Article 12 demands be kept:**
  - Operative phrases: *"automatic recording of events (logs) over the lifetime of the system"*, *"recording of events relevant for: (a) identifying situations that may result in the high-risk AI system presenting a risk... or in a substantial modification; (b) facilitating the post-market monitoring...; and (c) monitoring the operation of high-risk AI systems"*.
  - For Annex III 1(a) systems: *"recording of the period of each use of the system (start date and time and end date and time of each use)"*, *"the reference database against which input data has been checked"*, *"the input data for which the search has led to a match"*, and *"the identification of the natural persons involved in the verification of the results"*.
- **What Article 13 demands be given:**
  - Operative phrases: *"instructions for use in an appropriate digital format or otherwise that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers"*.
  - Mandatory instructions content includes: *"identity and the contact details of the provider"*, *"characteristics, capabilities and limitations of performance"*, *"level of accuracy, including its metrics, robustness and cybersecurity"*, *"technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output"*, *"specifications for the input data, or any other relevant information in terms of the training, validation and testing data sets used"*, *"human oversight measures"*, and *"description of the mechanisms included within the high-risk AI system that allows deployers to properly collect, store and interpret the logs in accordance with Article 12"*.
- **What Article 53(1) demands be produced by a provider of a general-purpose AI model:**
  - Operative phrases: *"draw up and keep up-to-date the technical documentation of the model"*, *"draw up, keep up-to-date and make available information and documentation to providers of AI systems"*, *"put in place a policy to comply with Union law on copyright and related rights"*, and *"draw up and make publicly available a sufficiently detailed summary about the content used for training"*.
  - Each of the four is a duty to **produce an artefact**, which is why presence of the artefact is the refinement of the duty rather than a proxy for it. The adequacy words the clause attaches to those artefacts are separate demands that presence cannot reach: *"shall contain, at a minimum, the information set out in Annex XI"*, *"contain, at a minimum, the elements set out in Annex XII"*, *"identify and comply with, including through state-of-the-art technologies, a reservation of rights"*, and *"sufficiently detailed"* / *"according to a template provided by the AI Office"*.
- **What Article 55(1) additionally demands of a provider of a model with systemic risk:**
  - Operative phrases: *"perform model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing"*, *"assess and mitigate possible systemic risks at Union level, including their sources"*, *"keep track of, document, and report, without undue delay, to the AI Office"* relevant information about serious incidents and possible corrective measures, and *"ensure an adequate level of cybersecurity protection"* for the model and *"the physical infrastructure of the model"*.
  - **The timing limb names no period.** *"without undue delay"* is the whole of what point (c) says about when a report is owed; unlike 12 CFR 1002.9(a)(1)'s 30 and 90 days, there is no figure here for a pack to repeat, which is why `docs/refinement.md` records the limb as not formalised rather than bounding it with a number.

---

## Provision 2: GDPR — Regulation (EU) 2016/679

### Metadata & Citation
- **Document Title:** Regulation (EU) 2016/679 of the European Parliament and of the Council of 27 April 2016 on the protection of natural persons with regard to the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation)
- **CELEX Identifier:** `32016R0679` (Consolidated CELEX: `02016R0679-20160504`)
- **Official Source URL:** [EUR-Lex Regulation (EU) 2016/679](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679)
- **Direct EU Cellar XHTML Endpoint (original text and recitals):** `http://publications.europa.eu/resource/cellar/3e485e15-11bd-11e6-ba9a-01aa75ed71a1.0006.03/DOC_1`
- **Direct EU Cellar XHTML Endpoint (consolidated articles):** `http://publications.europa.eu/resource/cellar/5f2552c2-cc45-11e6-ad7c-01aa75ed71a1.0022.03/DOC_1`
- **Consolidation / Version Date:** 4 May 2016 (Corrigenda published 2016, 2018, 2021)
- **Retrieval Date & Time:** 2026-07-31 09:52:25 UTC+2
- **Re-verification (second paragraph of Recital 71, quoted by `gdpr_recital71_error_risk_minimised`):** 2026-08-01 17:37 UTC. `python -m reasonsmith.drift` fetched the endpoints above and reported `match` for all 12 pack quotations, that requirement included — the quotation is the official text as published, not a paraphrase of it.
- **Legal Hierarchy Distinction Note:**
  > [!IMPORTANT]
  > **Binding Nature vs. Recital Distinction:**
  > Articles of EU Regulations (such as Article 22) are directly applicable, binding legal norms creating enforceable legal obligations and rights across all EU Member States.
  > Recitals (such as Recital 71) are non-binding preamble text used as interpretive aids by courts (including the Court of Justice of the European Union) to elucidate the purpose and intent of the operative Articles. A recital cannot create an independent legal obligation where none exists in the Articles, but it explicitly informs the interpretation of ambiguous terms in the corresponding Articles (e.g., explaining what safeguards are intended under Article 22(3)). This distinction must be preserved in all Reasonsmith packs.
- **Uncertainty / Status Flag:** Verified against official EU Cellar XHTML (`3e485e15-11bd-11e6-ba9a-01aa75ed71a1.0006.03/DOC_1` for full original text including recitals; `5f2552c2-cc45-11e6-ad7c-01aa75ed71a1.0022.03/DOC_1` for consolidated text of articles). Note that EUR-Lex consolidated versions omit recitals; recitals remain as originally published in OJ L 119, 4.5.2016.

---

### Verbatim Text

#### Article 22
**Automated individual decision-making, including profiling**

1. The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her.

2. Paragraph 1 shall not apply if the decision:
   (a) is necessary for entering into, or performance of, a contract between the data subject and a data controller;
   (b) is authorised by Union or Member State law to which the controller is subject and which also lays down suitable measures to safeguard the data subject's rights and freedoms and legitimate interests; or
   (c) is based on the data subject's explicit consent.

3. In the cases referred to in points (a) and (c) of paragraph 2, the data controller shall implement suitable measures to safeguard the data subject's rights and freedoms and legitimate interests, at least the right to obtain human intervention on the part of the controller, to express his or her point of view and to contest the decision.

4. Decisions referred to in paragraph 2 shall not be based on special categories of personal data referred to in Article 9(1), unless point (a) or (g) of Article 9(2) applies and suitable measures to safeguard the data subject's rights and freedoms and legitimate interests are in place.

---

#### Recital 71
*(71) The data subject should have the right not to be subject to a decision, which may include a measure, evaluating personal aspects relating to him or her which is based solely on automated processing and which produces legal effects concerning him or her or similarly significantly affects him or her, such as automatic refusal of an online credit application or e-recruiting practices without any human intervention. Such processing includes ‘profiling’ that consists of any form of automated processing of personal data evaluating the personal aspects relating to a natural person, in particular to analyse or predict aspects concerning the data subject's performance at work, economic situation, health, personal preferences or interests, reliability or behaviour, location or movements, where it produces legal effects concerning him or her or similarly significantly affects him or her. However, decision-making based on such processing, including profiling, should be allowed where expressly authorised by Union or Member State law to which the controller is subject, including for fraud and tax-evasion monitoring and prevention purposes conducted in accordance with the regulations, standards and recommendations of Union institutions or national oversight bodies and to ensure the security and reliability of a service provided by the controller, or necessary for the entering or performance of a contract between the data subject and a controller, or when the data subject has given his or her explicit consent. In any case, such processing should be subject to suitable safeguards, which should include specific information to the data subject and the right to obtain human intervention, to express his or her point of view, to obtain an explanation of the decision reached after such assessment and to challenge the decision. Such measure should not concern a child.*

*In order to ensure fair and transparent processing in respect of the data subject, taking into account the specific circumstances and context in which the personal data are processed, the controller should use appropriate mathematical or statistical procedures for the profiling, implement technical and organisational measures appropriate to ensure, in particular, that factors which result in inaccuracies in personal data are corrected and the risk of errors is minimised, secure personal data in a manner that takes account of the potential risks involved for the interests and rights of the data subject and that prevents, inter alia, discriminatory effects on natural persons on the basis of racial or ethnic origin, political opinion, religion or beliefs, trade union membership, genetic or health status or sexual orientation, or that result in measures having such an effect. Automated decision-making and profiling based on special categories of personal data should be allowed only under specific conditions.*

---

### Factual Summary of Demands (Law's Operative Words)
- **What Article 22 demands be given / implemented:**
  - Operative phrases: *"suitable measures to safeguard the data subject's rights and freedoms and legitimate interests, at least the right to obtain human intervention on the part of the controller, to express his or her point of view and to contest the decision"*.
- **What Recital 71 states regarding explanation and safeguards:**
  - Operative phrases: *"suitable safeguards, which should include specific information to the data subject and the right to obtain human intervention, to express his or her point of view, to obtain an explanation of the decision reached after such assessment and to challenge the decision"*.
  - Additional operational principles: *"controller should use appropriate mathematical or statistical procedures for the profiling"*, *"implement technical and organisational measures appropriate to ensure, in particular, that factors which result in inaccuracies in personal data are corrected and the risk of errors is minimised"*, and *"prevents, inter alia, discriminatory effects on natural persons"*.

---

## Provision 3: ECOA / Regulation B — 12 CFR 1002.9

### Metadata & Citation
- **Document Title:** Title 12 — Banks and Banking, Chapter X — Bureau of Consumer Financial Protection, Part 1002 — Equal Credit Opportunity Act (Regulation B), Section 1002.9 — Notifications
- **Document Identifier / Citation:** `12 CFR 1002.9`
- **Official Source URL:** [eCFR Section 1002.9](https://www.ecfr.gov/current/title-12/chapter-X/part-1002/section-1002.9)
- **Direct eCFR API Endpoint:** `https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?part=1002&section=1002.9`
- **Effective / Latest Amendment Date:** August 29, 2023 (as published in eCFR versioner metadata)
- **Retrieval Date & Time:** 2026-07-31 09:51:02 UTC+2
- **Uncertainty / Status Flag:** Verified against official eCFR API (Title 12, Part 1002, Section 1002.9, latest amendment date 2023-08-29).

---

### Verbatim Text

#### 12 CFR 1002.9
**§ 1002.9 Notifications.**

(a) *Notification of action taken, ECOA notice, and statement of specific reasons*—(1) *When notification is required.* A creditor shall notify an applicant of action taken within:
(i) 30 days after receiving a completed application concerning the creditor's approval of, counteroffer to, or adverse action on the application;
(ii) 30 days after taking adverse action on an incomplete application, unless notice is provided in accordance with paragraph (c) of this section;
(iii) 30 days after taking adverse action on an existing account; or
(iv) 90 days after notifying the applicant of a counteroffer if the applicant does not expressly accept or use the credit offered.

(2) *Content of notification when adverse action is taken.* A notification given to an applicant when adverse action is taken shall be in writing and shall contain a statement of the action taken; the name and address of the creditor; a statement of the provisions of section 701(a) of the Act; the name and address of the Federal agency that administers compliance with respect to the creditor; and either:
(i) A statement of specific reasons for the action taken; or
(ii) A disclosure of the applicant's right to a statement of specific reasons within 30 days, if the statement is requested within 60 days of the creditor's notification. The disclosure shall include the name, address, and telephone number of the person or office from which the statement of reasons can be obtained. If the creditor chooses to provide the reasons orally, the creditor shall also disclose the applicant's right to have them confirmed in writing within 30 days of receiving the applicant's written request for confirmation.

(3) *Notification to business credit applicants.* For business credit, a creditor shall comply with the notification requirements of this section in the following manner:
(i) With regard to a business that had gross revenues of $1 million or less in its preceding fiscal year (other than an extension of trade credit, credit incident to a factoring agreement, or other similar types of business credit), a creditor shall comply with paragraphs (a)(1) and (2) of this section, except that:
(A) The statement of the action taken may be given orally or in writing, when adverse action is taken;
(B) Disclosure of an applicant's right to a statement of reasons may be given at the time of application, instead of when adverse action is taken, provided the disclosure contains the information required by paragraph (a)(2)(ii) of this section and the ECOA notice specified in paragraph (b)(1) of this section;
(C) For an application made entirely by telephone, a creditor satisfies the requirements of paragraph (a)(3)(i) of this section by an oral statement of the action taken and of the applicant's right to a statement of reasons for adverse action.
(ii) With regard to a business that had gross revenues in excess of $1 million in its preceding fiscal year or an extension of trade credit, credit incident to a factoring agreement, or other similar types of business credit, a creditor shall:
(A) Notify the applicant, within a reasonable time, orally or in writing, of the action taken; and
(B) Provide a written statement of the reasons for adverse action and the ECOA notice specified in paragraph (b)(1) of this section if the applicant makes a written request for the reasons within 60 days of the creditor's notification.

(b) *Form of ECOA notice and statement of specific reasons*—(1) *ECOA notice.* To satisfy the disclosure requirements of paragraph (a)(2) of this section regarding section 701(a) of the Act, the creditor shall provide a notice that is substantially similar to the following: The Federal Equal Credit Opportunity Act prohibits creditors from discriminating against credit applicants on the basis of race, color, religion, national origin, sex, marital status, age (provided the applicant has the capacity to enter into a binding contract); because all or part of the applicant's income derives from any public assistance program; or because the applicant has in good faith exercised any right under the Consumer Credit Protection Act. The Federal agency that administers compliance with this law concerning this creditor is [name and address as specified by the appropriate agency or agencies listed in appendix A of this part].

(2) *Statement of specific reasons.* The statement of reasons for adverse action required by paragraph (a)(2)(i) of this section must be specific and indicate the principal reason(s) for the adverse action. Statements that the adverse action was based on the creditor's internal standards or policies or that the applicant, joint applicant, or similar party failed to achieve a qualifying score on the creditor's credit scoring system are insufficient.

(c) *Incomplete applications*—(1) *Notice alternatives.* Within 30 days after receiving an application that is incomplete regarding matters that an applicant can complete, the creditor shall notify the applicant either:
(i) Of action taken, in accordance with paragraph (a) of this section; or
(ii) Of the incompleteness, in accordance with paragraph (c)(2) of this section.

(2) *Notice of incompleteness.* If additional information is needed from an applicant, the creditor shall send a written notice to the applicant specifying the information needed, designating a reasonable period of time for the applicant to provide the information, and informing the applicant that failure to provide the information requested will result in no further consideration being given to the application. The creditor shall have no further obligation under this section if the applicant fails to respond within the designated time period. If the applicant supplies the requested information within the designated time period, the creditor shall take action on the application and notify the applicant in accordance with paragraph (a) of this section.

(3) *Oral request for information.* At its option, a creditor may inform the applicant orally of the need for additional information. If the application remains incomplete the creditor shall send a notice in accordance with paragraph (c)(1) of this section.

(d) *Oral notifications by small-volume creditors.* In the case of a creditor that did not receive more than 150 applications during the preceding calendar year, the requirements of this section (including statements of specific reasons) are satisfied by oral notifications.

(e) *Withdrawal of approved application.* When an applicant submits an application and the parties contemplate that the applicant will inquire about its status, if the creditor approves the application and the applicant has not inquired within 30 days after applying, the creditor may treat the application as withdrawn and need not comply with paragraph (a)(1) of this section.

(f) *Multiple applicants.* When an application involves more than one applicant, notification need only be given to one of them but must be given to the primary applicant where one is readily apparent.

(g) *Applications submitted through a third party.* When an application is made on behalf of an applicant to more than one creditor and the applicant expressly accepts or uses credit offered by one of the creditors, notification of action taken by any of the other creditors is not required. If no credit is offered or if the applicant does not expressly accept or use the credit offered, each creditor taking adverse action must comply with this section, directly or through a third party. A notice given by a third party shall disclose the identity of each creditor on whose behalf the notice is given.

---

### Factual Summary of Demands (Law's Operative Words)
- **What 12 CFR 1002.9 demands be given when adverse action is taken:**
  - Operative phrases: *"in writing and shall contain a statement of the action taken; the name and address of the creditor; a statement of the provisions of section 701(a) of the Act; the name and address of the Federal agency that administers compliance with respect to the creditor; and either: (i) A statement of specific reasons for the action taken; or (ii) A disclosure of the applicant's right to a statement of specific reasons within 30 days, if the statement is requested within 60 days of the creditor's notification"*.
- **What makes a statement of specific reasons sufficient:**
  - Operative phrases: *"must be specific and indicate the principal reason(s) for the adverse action"*.
  - Operative standard for insufficiency: *"Statements that the adverse action was based on the creditor's internal standards or policies or that the applicant, joint applicant, or similar party failed to achieve a qualifying score on the creditor's credit scoring system are insufficient"*.
  - **Where this sentence lives, because it is easy to misattribute.** It is the second sentence of § 1002.9(b)(2) — the regulation itself, quoted verbatim above and re-verified against the eCFR API on 2026-08-02 — and **not** a comment in the Official Interpretation. That matters for what a pack quoting it is quoting: binding regulatory text, not agency interpretation of it. The Supplement I comments on this paragraph are recorded below and say something different.

### Official Interpretation — Supplement I to Part 1002, Paragraph 9(b)(2)

- **Document Identifier / Citation:** `12 CFR part 1002, Supplement I, comment 9(b)(2)`
- **Direct eCFR API Endpoint:** `https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?chapter=X&part=1002`
- **Retrieval Date & Time:** 2026-08-02
- **Uncertainty / Status Flag:** Verified against the official eCFR API for Title 12, Part 1002 (same amendment date, 2023-08-29, as the section text above).
- **Why it is recorded here:** no shipped pack quotes it. It is retrieved so that `docs/refinement.md` can name comment 9(b)(2)-2 as the part of this duty the formalisation deliberately leaves out, without that citation resting on memory.

Comments 1 and 4-7 concern how many reasons to give and how to select them from a scoring or judgmental system. The two that bear on what is and is not formalised here:

> 2. *Source of specific reasons.* The specific reasons disclosed under §§ 1002.9(a)(2) and (b)(2) must relate to and accurately describe the factors actually considered or scored by a creditor.

> 3. *Description of reasons.* A creditor need not describe how or why a factor adversely affected an applicant. For example, the notice may say “length of residence” rather than “too short a period of residence.”

---

## Provision 4: ECOA / Regulation B — 12 CFR 1002.4(a)

### Metadata & Citation
- **Document Title:** Title 12 — Banks and Banking, Chapter X — Bureau of Consumer Financial Protection, Part 1002 — Equal Credit Opportunity Act (Regulation B), Section 1002.4 — General rules
- **Document Identifier / Citation:** `12 CFR 1002.4`
- **Official Source URL:** [eCFR Section 1002.4](https://www.ecfr.gov/current/title-12/chapter-X/part-1002/section-1002.4)
- **Direct eCFR API Endpoint:** `https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?part=1002&section=1002.4`
- **Effective / Latest Amendment Date:** January 31, 2013 (78 FR 7248), as printed in the section's own source note; retrieved at the Part 1002 amendment date 2023-08-29 used for § 1002.9 above, so one recorded date serves both provisions.
- **Retrieval Date & Time:** 2026-08-03 12:41 UTC
- **Uncertainty / Status Flag:** Verified against official eCFR API (Title 12, Part 1002, Section 1002.4).

---

### Verbatim Text

#### 12 CFR 1002.4(a)
**§ 1002.4 General rules.**

(a) *Discrimination.* A creditor shall not discriminate against an applicant on a prohibited basis regarding any aspect of a credit transaction.

---

### Definition the clause depends on — 12 CFR 1002.2(z)

- **Document Identifier / Citation:** `12 CFR 1002.2(z)`
- **Direct eCFR API Endpoint:** `https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?part=1002&section=1002.2`
- **Retrieval Date & Time:** 2026-08-03 12:41 UTC
- **Why it is recorded here:** no shipped pack quotes it. It is retrieved so that the vocabulary of protected grounds rests on the print rather than on memory, and so that `docs/refinement.md` can say which grounds a duty naming one variable does not reach.

> (z) *Prohibited basis* means race, color, religion, national origin, sex, marital status, or age (provided that the applicant has the capacity to enter into a binding contract); the fact that all or part of the applicant's income derives from any public assistance program; or the fact that the applicant has in good faith exercised any right under the Consumer Credit Protection Act or any state law upon which an exemption has been granted by the Bureau.

---

### Findings & Interpretation

- **What 12 CFR 1002.4(a) forbids:**
  - Operative phrase: *"shall not discriminate against an applicant on a prohibited basis regarding any aspect of a credit transaction"*.
- **Why this clause and not GDPR Recital 71.** The recital's discrimination limb is *effects* language — *"prevents, inter alia, discriminatory effects on natural persons"*, recorded under Provision 2 above — and effects is disparate impact, which is a fact about outcomes across a population and not a property of any pair of decisions. § 1002.4(a) forbids discriminating *against an applicant* on a prohibited basis, which is disparate treatment, and treatment is the limb a counterfactual invariance property can see. Attaching the property to the recital would have been a refinement of a duty it does not formalise.
- **What this record does not settle.** Whether Regulation B's effects test is codified in the regulation or lives in the Official Interpretation was not retrieved, and no shipped duty rests on it; `docs/refinement.md` records disparate impact as unformalised without relying on where the effects test is printed.
