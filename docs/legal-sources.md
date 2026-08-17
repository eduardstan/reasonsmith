# Official Statutory Text Findings & Provenance Report

## Document Overview
- **Purpose:** Provide exact, verbatim statutory texts for Reasonsmith's regulation packs from official legal sources, along with citation metadata, retrieval timestamps, notes on statutory hierarchy, and verbatim operative demands.
- **Date of Retrieval:** 2026-07-31

### Drift-check source formats
The statute-drift checker supports the recorded Cellar XHTML, eCFR XML, and GOV.UK HTML formats above, and a
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
- **Re-retrieval for Article 50 (quoted by `src/reasonsmith/packs/eu_ai_act.toml`):** 2026-08-17. The same Cellar XHTML endpoint was fetched again and the `050.001` through `050.007` divisions transcribed below. Articles 50(2) and 50(5) were not covered by the earlier retrievals, which recorded Articles 12, 13, 53, 55 and 86 only: the CELEX identifier establishes the document and not any particular provision.
- **Re-retrieval for Article 86 (quoted by `src/reasonsmith/packs/eu_ai_act.toml`) and Article 113:** 2026-08-14. The same Cellar XHTML endpoint was fetched again and the `086.001`, `086.002` and `086.003` divisions transcribed below, on the same ground the Articles 53 and 55 extension records: the CELEX identifier establishes the document and not the provision. All three paragraphs of Article 86 are transcribed although the pack quotes only Article 86(1), because paragraphs (2) and (3) are the clause's own carve-outs and a defeasibility classification may only be written from a retrieved clause. Article 113 was fetched in the same pass, to support the applicability derivation below, and it is recorded differently from every other provision here for two reasons. It has **no numbered paragraph divisions**: Articles 12, 13, 53, 55 and 86 carry `012.001`-style ids, while Article 113's paragraphs are bare `<p>` elements inside the `art_113` subdivision, so the whole article is one selector. And registering it in `drift.PROVISIONS` would buy nothing, because that registry is keyed by a requirement's `article_clause` and no requirement quotes Article 113 — it is retrieved to support a claim about another Article's applicability, not to be quoted. So this one transcription is outside the monthly re-fetch, and a reader checking it against the print has only the retrieval date below to go on.
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

#### Article 50
**Transparency obligations for providers and deployers of certain AI systems**

1.   Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system, unless this is obvious from the point of view of a natural person who is reasonably well-informed, observant and circumspect, taking into account the circumstances and the context of use. This obligation shall not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, unless those systems are available for the public to report a criminal offence.

2.   Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, shall ensure that the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated. Providers shall ensure their technical solutions are effective, interoperable, robust and reliable as far as this is technically feasible, taking into account the specificities and limitations of various types of content, the costs of implementation and the generally acknowledged state of the art, as may be reflected in relevant technical standards. This obligation shall not apply to the extent the AI systems perform an assistive function for standard editing or do not substantially alter the input data provided by the deployer or the semantics thereof, or where authorised by law to detect, prevent, investigate or prosecute criminal offences.

3.   Deployers of an emotion recognition system or a biometric categorisation system shall inform the natural persons exposed thereto of the operation of the system, and shall process the personal data in accordance with Regulations (EU) 2016/679 and (EU) 2018/1725 and Directive (EU) 2016/680, as applicable. This obligation shall not apply to AI systems used for biometric categorisation and emotion recognition, which are permitted by law to detect, prevent or investigate criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, and in accordance with Union law.

4.   Deployers of an AI system that generates or manipulates image, audio or video content constituting a deep fake, shall disclose that the content has been artificially generated or manipulated. This obligation shall not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offence. Where the content forms part of an evidently artistic, creative, satirical, fictional or analogous work or programme, the transparency obligations set out in this paragraph are limited to disclosure of the existence of such generated or manipulated content in an appropriate manner that does not hamper the display or enjoyment of the work. Deployers of an AI system that generates or manipulates text which is published with the purpose of informing the public on matters of public interest shall disclose that the text has been artificially generated or manipulated. This obligation shall not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences or where the AI-generated content has undergone a process of human review or editorial control and where a natural or legal person holds editorial responsibility for the publication of the content.

5.   The information referred to in paragraphs 1 to 4 shall be provided to the natural persons concerned in a clear and distinguishable manner at the latest at the time of the first interaction or exposure. The information shall conform to the applicable accessibility requirements.

6.   Paragraphs 1 to 4 shall not affect the requirements and obligations set out in Chapter III, and shall be without prejudice to other transparency obligations laid down in Union or national law for deployers of AI systems.

7.   The AI Office shall encourage and facilitate the drawing up of codes of practice at Union level to facilitate the effective implementation of the obligations regarding the detection and labelling of artificially generated or manipulated content. The Commission may adopt implementing acts to approve those codes of practice in accordance with the procedure laid down in Article 56 (6). If it deems the code is not adequate, the Commission may adopt an implementing act specifying common rules for the implementation of those obligations in accordance with the examination procedure laid down in Article 98(2).

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

#### Article 86
**Right to explanation of individual decision-making**

1. Any affected person subject to a decision which is taken by the deployer on the basis of the output from a high-risk AI system listed in Annex III, with the exception of systems listed under point 2 thereof, and which produces legal effects or similarly significantly affects that person in a way that they consider to have an adverse impact on their health, safety or fundamental rights shall have the right to obtain from the deployer clear and meaningful explanations of the role of the AI system in the decision-making procedure and the main elements of the decision taken.

2. Paragraph 1 shall not apply to the use of AI systems for which exceptions from, or restrictions to, the obligation under that paragraph follow from Union or national law in compliance with Union law.

3. This Article shall apply only to the extent that the right referred to in paragraph 1 is not otherwise provided for under Union law.

---

#### Article 113
**Entry into force and application**

This Regulation shall enter into force on the twentieth day following that of its publication in the Official Journal of the European Union.

It shall apply from 2 August 2026.

However:
(a) Chapters I and II shall apply from 2 February 2025;
(b) Chapter III Section 4, Chapter V, Chapter VII and Chapter XII and Article 78 shall apply from 2 August 2025, with the exception of Article 101;
(c) Article 6(1) and the corresponding obligations in this Regulation shall apply from 2 August 2027.

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
- **What Article 86 demands be given to an affected person:**
  - Operative phrases: *"shall have the right to obtain from the deployer clear and meaningful explanations of the role of the AI system in the decision-making procedure and the main elements of the decision taken"*.
  - **Applicability.** Derived directly from the two transcriptions above: Article 86 sits in Chapter IX, Section 4 (Remedies) — verified in the same Cellar document, whose `art_86` division is inside `<div id="cpt_IX.sct_4">`, titled *Remedies* — and none of Article 113's three staged exceptions reaches it: point (a) names Chapters I and II (2 February 2025) and point (b) names Chapter III Section 4, Chapters V, VII and XII and Article 78 (2 August 2025), neither of which includes Chapter IX; and point (c) provides that *"Article 6(1) and the corresponding obligations in this Regulation shall apply from 2 August 2027"*. An Article 86(1) right does not fall inside point (c) because Article 6(1) is the Annex I route to high-risk classification (a safety component of a product covered by Union harmonisation legislation), while Article 86(1) reaches Annex III systems only, minus point 2 — so the right is not a "corresponding obligation" of Article 6(1). Because none of the exceptions applies, Article 86 is governed by Article 113's general application rule and applies from 2 August 2026.
  - **Four limbs, and only one of them is about the explanation itself.** *"Any affected person subject to a decision which is taken by the deployer on the basis of the output from a high-risk AI system listed in Annex III, with the exception of systems listed under point 2 thereof"* is a classification of the system; *"produces legal effects or similarly significantly affects that person in a way that they consider to have an adverse impact on their health, safety or fundamental rights"* is a test about the decision's effect on a natural person; *"shall have the right to obtain"* makes the duty run on a request. None of the three is a fact a decision record carries, which is why `docs/refinement.md` records them as outside what any run establishes.
  - **The clause carries its own two carve-outs**, both of which are paragraphs of the same Article rather than external instruments, and neither of which can be settled from this document because both defer outward: *"Paragraph 1 shall not apply to the use of AI systems for which exceptions from, or restrictions to, the obligation under that paragraph follow from Union or national law in compliance with Union law"* (86(2)), and *"This Article shall apply only to the extent that the right referred to in paragraph 1 is not otherwise provided for under Union law"* (86(3)). Both are retrieved here so the defeasibility classification of the shipped requirement rests on the print rather than on memory.

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


---

## Provision 5: Uniform Guidelines on Employee Selection Procedures — 29 CFR 1607.4(D)

### Metadata & Citation
- **Document Title:** Title 29 — Labor, Subtitle B — Regulations Relating to Labor,
  Chapter XIV — Equal Employment Opportunity Commission, Part 1607 — Uniform Guidelines
  on Employee Selection Procedures, § 1607.4 Information on impact.
- **Document Identifier / Citation:** `29 CFR 1607.4(D)`.
- **Official Source URL:** https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607/section-1607.4
- **Direct eCFR API Endpoint:** `https://www.ecfr.gov/api/versioner/v1/full/2017-01-03/title-29.xml?part=1607&section=1607.4`
- **Version metadata endpoint:** `https://www.ecfr.gov/api/versioner/v1/versions/title-29.json?part=1607&section=1607.4`
- **Effective / latest amendment date:** 2017-01-03 (substantive=true; removed=false in
  the section-specific Versioner response); source note cites 43 FR 38295, 38312 (Aug. 25,
  1978), as amended at 46 FR 63268 (Dec. 31, 1981).
- **Retrieval Date & Time:** 2026-08-15 08:48 UTC.
- **Response:** HTTP 200, `text/xml`, 6,778 bytes; raw SHA-256
  `0b70dc7befc9eddc68a8707a4be03d0e34f305c2cee89f9ca888e2889786d3a3`.
- **Uncertainty / Status Flag:** Verified against official eCFR Versioner XML. XML was decoded
  using its UTF-8 declaration; presentation whitespace around `<FR>` was normalized for the
  quotation, while the hash covers the original response. Scope is employment selection only;
  this is not an ECOA/Regulation B source.

### Verbatim Text

#### 29 CFR 1607.4(D)
D. Adverse impact and the “four-fifths rule.” A selection rate for any race, sex, or ethnic group which is less than four-fifths (4/5) (or eighty percent) of the rate for the group with the highest rate will generally be regarded by the Federal enforcement agencies as evidence of adverse impact, while a greater than four-fifths rate will generally not be regarded by Federal enforcement agencies as evidence of adverse impact. Smaller differences in selection rate may nevertheless constitute adverse impact, where they are significant in both statistical and practical terms or where a user's actions have discouraged applicants disproportionately on grounds of race, sex, or ethnic group. Greater differences in selection rate may not constitute adverse impact where the differences are based on small numbers and are not statistically significant, or where special recruiting or other programs cause the pool of minority or female candidates to be atypical of the normal pool of applicants from that group. Where the user's evidence concerning the impact of a selection procedure indicates adverse impact but is based upon numbers which are too small to be reliable, evidence concerning the impact of the procedure over a longer period of time and/or evidence concerning the impact which the selection procedure had when used in the same manner in similar circumstances elsewhere may be considered in determining adverse impact. Where the user has not maintained data on adverse impact as required by the documentation section of applicable guidelines, the Federal enforcement agencies may draw an inference of adverse impact of the selection process from the failure of the user to maintain such data, if the user has an underutilization of a group in the job category, as compared to the group's representation in the relevant labor market or, in the case of jobs filled from within, the applicable work force.

This is an employment-selection enforcement guideline and not a generic fairness threshold, legal-compliance verdict, or source for ECOA/GDPR distributional questions. Those questions remain `undetermined()` until their own authority supplies a scoped rule.
## Provision 6 — Frontier AI Safety Commitments, AI Seoul Summit 2024 (GOV.UK)

### Metadata & Citation
- **Document:** *Frontier AI Safety Commitments, AI Seoul Summit 2024*.
- **Publisher:** UK Department for Science, Innovation and Technology, GOV.UK.
- **Edition:** page updated **7 February 2025**; this pack freezes that edition. Later editions use
  the immutable ID convention `seoul_frontier_ai_safety_2024__updated_YYYY-MM-DD` and open a review
  finding rather than mutating this pack.
- **Official source URL:** `https://www.gov.uk/government/publications/frontier-ai-safety-commitments-ai-seoul-summit-2024/frontier-ai-safety-commitments-ai-seoul-summit-2024`
- **Retrieval:** 2026-08-15 08:47:47 UTC; recorded HTML SHA-256
  `e19e0ecc72113970f63b03f08c269fe0dcc40da802815b1ae8d236c6d7c394ac` (81,418 bytes at retrieval).
  GOV.UK HTML carries dynamic presentation tokens, so this digest corroborates the retrieval record;
  the rendered edition marker is the immutable sentinel.
- **Licence/status:** Open Government Licence v3.0; voluntary commitments by named organisations.
- **Extraction:** `main .gem-c-govspeak p`, numbered paragraphs beginning `I.` through `VIII.`;
  linked footnote `<sup>` nodes (`fnref:2`, `fnref:3`) and only their presentation whitespace
  before punctuation are removed, then remaining whitespace is collapsed. Navigation, licence,
  footnotes, and “Outcome” prose are excluded. The source kind is `govuk-html` and the sentinel is
  `Updated 7 February 2025`.

### Operative commitment passages

> **Commitment I:** Assess the risks posed by their frontier models or systems across the AI lifecycle, including before deploying that model or system, and, as appropriate, before and during training. Risk assessments should consider model capabilities and the context in which they are developed and deployed, as well as the efficacy of implemented mitigations to reduce the risks associated with their foreseeable use and misuse. They should also consider results from internal and external evaluations as appropriate, such as by independent third-party evaluators, their home governments, and other bodies their governments deem appropriate.

> **Commitment II:** Set out thresholds at which severe risks posed by a model or system, unless adequately mitigated, would be deemed intolerable. Assess whether these thresholds have been breached, including monitoring how close a model or system is to such a breach. These thresholds should be defined with input from trusted actors, including organisations’ respective home governments as appropriate. They should align with relevant international agreements to which their home governments are party. They should also be accompanied by an explanation of how thresholds were decided upon, and by specific examples of situations where the models or systems would pose intolerable risk.

> **Commitment III:** Articulate how risk mitigations will be identified and implemented to keep risks within defined thresholds, including safety and security-related risk mitigations such as modifying system behaviours and implementing robust security controls for unreleased model weights.

> **Commitment IV:** Set out explicit processes they intend to follow if their model or system poses risks that meet or exceed the pre-defined thresholds. This includes processes to further develop and deploy their systems and models only if they assess that residual risks would stay below the thresholds. In the extreme, organisations commit not to develop or deploy a model or system at all, if mitigations cannot be applied to keep risks below the thresholds.

> **Commitment V:** Continually invest in advancing their ability to implement commitments i-iv, including risk assessment and identification, thresholds definition, and mitigation effectiveness. This should include processes to assess and monitor the adequacy of mitigations, and identify additional mitigations as needed to ensure risks remain below the pre-defined thresholds. They will contribute to and take into account emerging best practice, international standards, and science on AI risk identification, assessment, and mitigation.

> **Commitment VI:** Adhere to the commitments outlined in I-V, including by developing and continuously reviewing internal accountability and governance frameworks and assigning roles, responsibilities and sufficient resources to do so.

> **Commitment VII:** Provide public transparency on the implementation of the above (I-VI), except insofar as doing so would increase risk or divulge sensitive commercial information to a degree disproportionate to the societal benefit. They should still share more detailed information which cannot be shared publicly with trusted actors, including their respective home governments or appointed body, as appropriate.

> **Commitment VIII:** Explain how, if at all, external actors, such as governments, civil society, academics, and the public are involved in the process of assessing the risks of their AI models and systems, the adequacy of their safety framework (as described under I-VI), and their adherence to that framework.

### Findings & interpretation

The commitments are voluntary. This pack uses `general-purpose` as the nearest existing scope
class and adds an explicit, self-asserted `frontier_ai_status` applicability gate: undeclared and
`not-frontier` systems are reported **not applicable**, not cleared or evaluated. A wrong
`frontier` declaration remains the audited system’s overclaim; reasonsmith does not independently
verify it. Commitment IV is formalised as a four-signal logical implication; the other seven rows
are record-presence approximations. “Adequately mitigated”, “intolerable”, and “sufficient
resources” remain refinement gaps, with no invented authority or open-textured engine.

---

## Provision 8: Cyber Resilience Act — Regulation (EU) 2024/2847

### Metadata & Citation
- **Document Title:** Regulation (EU) 2024/2847 of the European Parliament and of the Council of 23 October 2024 on horizontal cybersecurity requirements for products with digital elements and amending Regulations (EU) No 168/2013 and (EU) 2019/1020 and Directive (EU) 2020/1828 (Cyber Resilience Act)
- **CELEX Identifier:** `32024R2847` (consolidated version: `02024R2847-20241120`)
- **Official Source URL:** [EUR-Lex Regulation (EU) 2024/2847](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng)
- **Direct EU Cellar XHTML Endpoint:** `http://publications.europa.eu/resource/cellar/21b7d4eb-a6e2-11ef-85f0-01aa75ed71a1.0006.03/DOC_1`
- **Publication date:** 20 November 2024 (OJ L, 2024/2847)
- **Retrieval date:** 16 August 2026
- **Uncertainty / status flag:** Retrieved from the official EUR-Lex page and verified against the official EU Publications Cellar XHTML endpoint.

### Verbatim Text

#### Article 14(2)(a)

an early warning notification of an actively exploited vulnerability, without undue delay and in any event within 24 hours of the manufacturer becoming aware of it, indicating, where applicable, the Member States on the territory of which the manufacturer is aware that their product with digital elements has been made available;

### Factual Summary of Demands (Law's Operative Words)
- The bounded event-time property measures only the explicit **within 24 hours of awareness** limb.
- **Actively exploited** and **without undue delay** remain open-textured or applicability predicates; the pack does not replace either with an invented test or number.
