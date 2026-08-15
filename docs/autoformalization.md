# Autoformalisation verification harness

The model-facing proposer is optional (`reasonsmith.proposer`, via the empty `proposer` extra); it
uses a configured provider and is absent by default. Ollama is supported without a Python client,
and the installed Claude Code CLI is available through the same optional boundary:

```python
from reasonsmith.proposer import ClaudeModel, measure_agreement

measurement = measure_agreement(model=ClaudeModel(), model_name="claude-cli", max_attempts=2)
```

`ClaudeModel` invokes `claude -p PROMPT`; configure another executable with
`REASONSMITH_CLAUDE_COMMAND`. The command-line equivalent is
`python -m reasonsmith.proposer --claude --attempts 2`. Any provider can instead implement the
one-call `Model` protocol, or use `--command` for a program that reads the prompt on stdin. A
provider that cannot be reached is `unavailable`; an unparseable model response is `refused`, and
a parseable but non-equivalent proposal is `wrong`. These are not silently counted as disagreement.

The boundary is:

1. a candidate is parsed by `rulelang.py` and must have the requirement's exact fragment;
2. `reasonsmith.autoformalize.round_trip_check` compares its denotation with the shipped property
   using the solver helpers already used by `analysis.py`;
3. `reasonsmith.autoformalize.check_challenges` evaluates it on the requirement's gold cases; and
4. `reasonsmith.proposer` may retry a failed candidate within its fixed attempt budget, handing
   back only the round-trip finding (with a witness where that fragment provides one) and failing
   gold cases; it never rewrites a formula; and
5. a human records `Human sign-off: signed-off` in that requirement's row in
   [`refinement.md`](refinement.md).

Only semantic equivalence clears the round-trip gate. A model response that is not one complete
formula accepted by the repository parser is a refusal, not an extraction or guess. The proposer
measurement command is `python -m reasonsmith.proposer --model MODEL --attempts 3` (or
`--command COMMAND` for any provider adapter that reads a prompt on stdin); its result is
reported in the committed [`autoformalization-study.md`](autoformalization-study.md) and
[`RESULTS.md`](../RESULTS.md). A strictly stronger, strictly weaker or
incomparable formula is returned as a repair finding; record and logical comparisons include a
solver witness, temporal comparisons return the entailment relation without one, and differing
counterfactual atoms name the outcome/protected-signal mismatch. This harness never rewrites the
formula. Unsupported fragments and unavailable optional procedures are refusals, not guesses. The
result is not a conformance verdict and does not construct a report result.

## Gold cases

The corpus lives in the installed package at
`src/reasonsmith/challenges/`. `manifest.toml` is the selection record: every listed requirement
must have exactly one TOML set, while every set must name a shipped requirement. Schema version 2
records the requirement's formalism and gives each case exactly one evidence shape: a `signals` table
for record/logical duties, an ordered finite `trace` for temporal duties, or a list of paired
`left`/`right` executions for the counterfactual duty. Each case carries a plain-language
description, a `kind` (`satisfied`, `violated` or `near-miss`), an expected formula classification
and concrete evidence. The descriptions are for a lawyer reviewing the boundary; the parser is not
the authority for the legal clause, which remains the referenced pack and its refinement row.

The corpus covers all 37 shipped requirements: record and logical cases, four temporal finite traces,
and the one counterfactual paired-execution duty. Open-textured and certificate duties are not
approximated merely to increase coverage. Temporal round-trip equivalence still refuses without the
optional BLACK procedure, while the gold checker uses the shared finite-trace interpreter and does
not import an engine. Adding a set does not add a requirement or replace the refinement row.

The module has no model import and no path to a conformance engine or verdict. It is therefore
exercisable entirely with hand-written formulas, which is the intended review surface before a
proposer is introduced.

## The AI-assisted authoring path: one worked duty

The model proposes, the formal checker disposes: it never produces a verdict and no engine may call
it as one. Here is the complete path for the real EU AI Act Article 12(1) duty
`eu_ai_act_art12_1_automatic_logging`.

1. **Source quote and hand-authored gold.** The pack quotes: “High-risk AI systems shall
   technically allow for the automatic recording of events (logs) over the lifetime of the
   system.” The hand-authored gold in `packs/eu_ai_act.toml` is
   `present(artifact_logs_event_log) and present(provenance_model_version)`; the refinement row
   explains that lifetime, durability, and whether a log was automatically assembled remain outside
   this property.
2. **Proposal.** With the fixed two-attempt Claude measurement command, the proposer returned
   `present(artifact_logs_event_log) and present(provenance_model_version)` on its first attempt.
   The response is text only; it is not passed to an engine.
3. **Round-trip gate.** `round_trip_check` parsed the candidate and established
   `equivalent` against the shipped `spec` (the exact-match case).
4. **Gold-challenge gate.** `check_challenges` ran all four cases in
   `src/reasonsmith/challenges/eu_ai_act_art12_1_automatic_logging.toml`: the complete record
   passed, the missing-event-log violation passed, the blank-provenance near-miss passed, and the
   missing-both near-miss passed.
5. **Human gate.** The row in [`refinement.md`](refinement.md) is the audit record and currently
   says `Human sign-off: pending (gold set: ...; no candidate approved)`. A reviewer must inspect
   the quote, formula gap, round-trip evidence, and challenge evidence and change that row to
   `Human sign-off: signed-off` before this candidate is approved. Until then, it is only a
   machine-cleared proposal.

The measured results, including unavailable provider calls and semantic-only agreements, are in the
[agreement study](autoformalization-study.md).
