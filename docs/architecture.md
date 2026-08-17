# Reasonsmith architecture

This page is the zoomed view of the [README organising question](../README.md#the-organising-question). The macro is the 30-second orientation; each section then opens one component without changing what a verdict means.

## At a glance

```mermaid
flowchart TB
    reg["Your regulation — a pack: statute, quote, formal duty"]
    sut["Your system — log, decide(), logic(), neural model, inference artefact"]
    engine["Your engine — plug-in; core rechecks violation witness"]
    core["Trusted core — applicability first, then strongest evidence permitted"]
    ladder["Evidence ladder — unattainable → observed → recounted → probed → proved"]
    report["Refusal-honest report — holds, evidence, refusals"]
    five["Five projections — developer · deployer · auditor · regulator · affected individual"]

    reg --> core
    sut --> core
    engine --> core
    core --> ladder --> report --> five

    classDef open fill:#e5f2f8,stroke:#1f6f8f,color:#16181d
    classDef trusted fill:#ffffff,stroke:#16181d,color:#16181d
    classDef rung fill:#eaf6ef,stroke:#1d6b45,color:#16181d
    classDef report fill:#fff8e7,stroke:#9a6700,color:#16181d

    class reg,sut,engine open
    class core trusted
    class ladder rung
    class report,five report
```

The three blue joints are deliberately open: bring your own regulation, system, and engine. The trusted core checks what they provide, stops at the strongest evidence the property and surface permit, and keeps refusals visible.

## From statute to formal duty

```mermaid
flowchart LR
    statute["Statute clause"] --> retrieval["Retrieval record — verbatim quote, pinned source"]
    retrieval --> duty["Formal property — one recorded judgement per clause"]
    duty --> refinement["Refinement row — what formalisation leaves out"]
    refinement --> drift["Drift watch — quote stays honest"]
    drift --> edition["Immutable pack edition"]

    classDef law fill:#eef3fb,stroke:#1f4f8f,color:#16181d
    classDef record fill:#fff4d6,stroke:#9a6700,color:#16181d
    classDef boundary fill:#ffffff,stroke:#16181d,color:#16181d
    class statute,duty law
    class retrieval,refinement record
    class drift,edition boundary
```

A pack keeps the legal path inspectable: the quote is retrieved and pinned before it becomes a formal property, and a refinement row records what that formalisation does not decide. Editions are immutable rather than silently rewritten. The repository currently carries seven packs and 41 duties. See [pack authoring](authoring-packs.md), the [legal retrieval record](legal-sources.md), and the [refinement record](refinement.md).

## What the system exposes

```mermaid
flowchart LR
    log["Decision log"] --> surfaces["Evidence surfaces"]
    decide["decide()"] --> surfaces
    logic["Declared logic()"] --> surfaces
    artifact["Inference artefact"] --> surfaces
    neural["Neural ONNX + declared input space"] --> query["Core-compiled VNN-LIB query"]
    query --> subprocess["Marabou / α,β-CROWN subprocess"]
    subprocess --> replay["Replayed witness or honest refusal"]
    replay --> oracle["Separate neural oracle — no conformance verdict yet"]
    oracle --> surfaces

    classDef surface fill:#f4f1fa,stroke:#5b4a8a,color:#16181d
    classDef extension fill:#e5f2f8,stroke:#1f6f8f,color:#16181d
    class log,decide,logic,artifact,surfaces surface
    class neural,query,subprocess,replay,oracle extension
```

A subject contributes the surface it actually exposes: a log, replayable decision procedure, declared rules, a neural model with its input space, or an inference artefact. The neural path is a separate oracle: the core compiles the query, a subprocess searches it, and a SAT witness is replayed; an honest refusal is not a conformance verdict. Compare the [three systems](three-systems.md), [neural verifier boundary](neural-verifiers.md), and [language-model adapter](language-model.md).

## Applicability and the evidence ladder

```mermaid
flowchart TB
    reach["Applicability and capability reach gate"] --> notapp["Not applicable — scope or domain was not declared"]
    reach --> unattainable["Unattainable — required evidence cannot be emitted"]
    reach --> ladder["Evidence ladder — strongest permitted rung wins"]
    ladder --> observed["Observed — decision record or trace"]
    observed --> recounted["Recounted — reasons are re-run"]
    recounted --> probed["Probed — bounded replay"]
    probed --> proved["Proved — solver over declared rules"]
    ladder -. second axis .-> basis["Evidence basis — behavioural · relational · artifact · assessment · statistical"]

    classDef decision fill:#fff8e7,stroke:#9a6700,color:#16181d
    classDef refusal fill:#fde2e2,stroke:#a33a3a,color:#16181d
    classDef rung fill:#eaf6ef,stroke:#1d6b45,color:#16181d
    classDef basis fill:#f6edf8,stroke:#8b4a8b,color:#16181d
    class reach,ladder decision
    class notapp,unattainable refusal
    class observed,recounted,probed,proved rung
    class basis basis
```

The reach gate separates **not applicable** from **unattainable**. After it, the property and the exposed surface jointly determine the ceiling: observed, recounted, probed, or proved. The strongest permitted rung wins; an auditor cannot choose a more convenient one. Evidence basis is a second axis, not another rung: it says whether the claim is behavioural, relational, artifact-based, an assessment, or statistical. Read the operational [semantics](semantics.md) and the [evidence theory](theory/08-evidence.md).

## Bring your own engine, checked

```mermaid
flowchart LR
    installed["Installed engine"] --> ceiling["Result at declared ceiling"]
    ceiling --> replay["Trusted core replays violation witness"]
    replay --> provenance["Core writes witness-checked or trusted-ceiling provenance"]
    provenance --> kit["verify-engine conformance kit"]

    classDef extension fill:#e5f2f8,stroke:#1f6f8f,color:#16181d
    classDef trusted fill:#ffffff,stroke:#16181d,color:#16181d
    classDef check fill:#eaf6ef,stroke:#1d6b45,color:#16181d
    class installed,ceiling extension
    class replay,provenance trusted
    class kit check
```

An installed engine may contribute a result only at its declared ceiling. When it supplies a violation witness, the trusted core replays it and writes the provenance; without a usable witness, the result is marked `trusted-ceiling` rather than presented as independently checked. The `verify-engine` kit exercises this boundary. It was adversarially hardened in 0.10.0. See [authoring engines](authoring-engines.md).

## Statistical measurement, beside the verdict

```mermaid
flowchart TB
    verdict["Verdict path"]
    selection["selection_rate_ratio(...)"] --> intervals["Simultaneous Clopper–Pearson intervals under a declared plan"]
    intervals --> rule["decision_rule = null"]
    rule --> measurement["Measurement beside verdict path — never inside"]

    classDef measurement fill:#f6edf8,stroke:#8b4a8b,color:#16181d
    classDef boundary fill:#ffffff,stroke:#16181d,color:#16181d
    class selection,intervals,rule,measurement measurement
    class verdict boundary
```

Statistical evidence is measurement-only. A declared plan produces simultaneous Clopper–Pearson intervals, but `decision_rule = null` means the measurement stays beside the verdict path and is never turned into satisfied or violated. See [evidence theory](theory/08-evidence.md).

## The report and its five readers

```mermaid
flowchart TB
    verdict["Verdict — strongest evidence, pushed-to rung, evidence basis"]
    developer["Developer — detail"]
    deployer["Deployer — ceiling"]
    auditor["Auditor — finding"]
    regulator["Regulator — source"]
    individual["Affected individual"]

    verdict --> developer
    verdict --> deployer
    verdict --> auditor
    verdict --> regulator
    verdict --> individual
    developer ~~~ deployer ~~~ auditor ~~~ regulator ~~~ individual

    classDef outcome fill:#fff8e7,stroke:#9a6700,color:#16181d
    classDef audience fill:#ffffff,stroke:#16181d,color:#16181d
    class verdict outcome
    class developer,deployer,auditor,regulator,individual audience
```

The core produces one refusal-honest finding, then projects only what each reader needs: implementation detail for the developer, the evidence ceiling for the deployer, finding and provenance for the auditor, clause and source for the regulator, and a plain account for the affected individual. The report retains how far the claim was pushed and what evidence it is about; it does not fill an evidence gap with a stronger-sounding sentence. Read the operational [semantics](semantics.md).
