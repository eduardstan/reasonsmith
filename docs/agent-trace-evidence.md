# Agent trace-evidence pilot

This page documents the narrow pilot from [issue #273](https://github.com/eduardstan/reasonsmith/issues/273).
It is an evidence-boundary experiment, not a new conformance property and not a claim that an
agent is compliant.

## What the pilot establishes

The Article 50(5) duty already shipped in the EU AI Act pack has the temporal shape

```text
always(present(artifact_logs_natural_person_interaction)
       -> present(artifact_logs_ai_disclosure))
```

That shape is intentionally small: the existing temporal observed engine evaluates it over the
ordinary decision mappings. The pilot adds a stricter input contract before that engine is allowed
to read either field as evidence. A recorder-bounded single-agent execution record must declare:

- schema version `1` and one stable `execution_id`;
- the existing `__time_domain__` event clock, declared as `event` rather than a parallel clock;
- unique event identifiers and a correlation identifier shared by the interaction/disclosure pair;
- an event kind and explicit timestamp for each event; and
- source/provenance metadata for every event, including a boundary-recorder attestation, plus an
  explicit boolean `complete` declaration on every record.

`read_execution_record` in `reasonsmith.sut` validates that schema. The Article 50 trace path then
requires exactly one recorder-attested `natural_person_interaction` and exactly one recorder-attested
`ai_disclosure` event with the same correlation identifier, and requires that the corresponding
signal values are actually materialised in the trace. A non-blank field is not a substitute for
those events.

`reasonsmith.examples.agent_trace` is a deterministic fixture. `SyntheticAgent` returns a
subject-authored `disclosure_delivered` value, but `BoundaryRecorder` does not use it as proof. The
recorder observes one synthetic ingress and the user-visible disclosure response, and emits the
versioned record. The complete fixture reaches `satisfied` at `observed` for Article 50(5). A second
fixture omits the disclosure event. It is refused as `inconclusive`, rather than treated as either a
satisfied implication or a temporal violation.

The acceptance boundary is pinned by tests: a self-reporting trace containing both Article 50 signal
fields but no execution-record envelope cannot reach `observed`, and direct calls to the observed
engine enforce the same refusal. Missing completeness, a wrong schema version or clock, an agent
source, an uncorrelated pair, and an event omitted from the trace are all refusal cases.

The recorder is outside the subject in the fixture's architecture. That is the only reason the pilot
can distinguish “the agent says it disclosed” from “the boundary recorder observed a disclosure.”
The schema is a provenance contract, not a cryptographic signature or a trusted hardware claim; a
production recorder would need its own independently secured deployment and retention story.

## What the pilot does not establish

This is not evidence that a person saw, understood, or could act on a disclosure. The event says only
that the synthetic boundary recorder observed a user-visible disclosure artifact. It does not judge
whether the wording is clear, distinguishable, accessible, comprehensible, or effective. It does not
prove that the UI displayed the artifact to a person, that a person was present, or that the person
read it. It does not establish any fact the agent reports about itself merely because the report is
present in the same mapping.

It is not a finding that the agent, provider, deployer, or any organisation complies with Article 50.
Applicability is a declared input: this pilot never decides whether a system is intended to interact
directly with natural persons, whether a statutory obviousness exception applies, or whether an
authorised criminal-offence exception applies. The Article 50(5) formalisation also does not model
the separate Article 50(3) or 50(4) duties, the paragraphs 1–4 scope questions, or the legal role of
the duty bearer.

A two-record fixture is not lifetime evidence. It says nothing about retention, automatic logging on
paths the fixture did not exercise, tamper resistance, coverage of omitted interactions, or storage
under anyone's control. Those are why Article 12 record-keeping and retention remain outside this
pilot. It also says nothing about Article 14 competence, training, authority, effective oversight,
intervention or safe stopping, and it cannot discharge Article 72 post-market monitoring. GDPR
Article 22, disclosure accessibility and clarity, and any broad “the agent is compliant” statement are
outside the evidence supplied here as well.

Finally, this pilot does not add a temporal engine, a new property-language operator, a live-agent
adapter, a network call, or an external service. It reuses `TimeDomain`, `read_time_domain`, the
existing Article 50 pack row, and the existing observed engine. If a future deployment cannot
provide a genuinely independent boundary recorder, the honest result is this pilot's refusal or a
plain field check—not an `observed` result wearing recorder language.
