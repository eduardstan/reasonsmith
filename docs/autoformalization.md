# Autoformalisation verification harness

The model-facing proposer is optional (`reasonsmith.proposer`, via the empty `proposer` extra); it
uses a configured Ollama model and is absent by default. The boundary is:

1. a candidate is parsed by `rulelang.py` and must have the requirement's exact fragment;
2. `reasonsmith.autoformalize.round_trip_check` compares its denotation with the shipped property
   using the solver helpers already used by `analysis.py`;
3. `reasonsmith.autoformalize.check_challenges` evaluates it on the requirement's gold cases; and
4. `reasonsmith.proposer` may retry a failed candidate within its fixed attempt budget, handing
   back only the round-trip witness and failing gold cases; it never rewrites a formula; and
5. a human records `Human sign-off: signed-off` in that requirement's row in
   [`refinement.md`](refinement.md).

Only semantic equivalence clears the round-trip gate. A model response that is not one complete
formula accepted by the repository parser is a refusal, not an extraction or guess. The proposer
measurement command is `python -m reasonsmith.proposer --model MODEL --attempts 3`; its result is
reported in [`RESULTS.md`](../RESULTS.md). A strictly stronger, strictly weaker or
incomparable formula is returned as a repair finding with a solver witness; this harness never
rewrites it. Unsupported fragments and unavailable optional procedures are refusals, not guesses.
The result is not a conformance verdict and does not construct a report result.

## Gold cases

The initial corpus is deliberately small and lives in the installed package at
`src/reasonsmith/challenges/`. `manifest.toml` is the selection record: every listed requirement
must have exactly one TOML set, while every set must name a shipped requirement. Each case carries a
plain-language description, a `kind` (`satisfied`, `violated` or `near-miss`), an expected formula
classification and a concrete `signals` table. The descriptions are for a lawyer reviewing the
boundary; the parser is not the authority for the legal clause, which remains the referenced pack
and its refinement row.

The starting subset is three duties with sharp, testable boundaries: a record conjunction, the ECOA
clause's named forbidden phrases, and a GDPR implication with explicit lawful-basis branches. Open-
textured, certificate, counterfactual and general temporal duties are not approximated merely to
increase coverage. Adding a set does not add a requirement or replace the refinement row.

The module has no model import and no path to a conformance engine or verdict. It is therefore
exercisable entirely with hand-written formulas, which is the intended review surface before a
proposer is introduced.
