# Authoring an engine plug-in

reasonsmith discovers engines through `importlib.metadata.entry_points`. An engine you ship as
your own pip package joins the ladder the moment it is installed, and you never touch this
repository to do it. The answer to *can reasonsmith use Prolog, ASP, or a different solver?* is
**yes, as a package you install**, not *send us a pull request*.

The property language does not change. Your engine is handed the same `Requirement` the built-ins
are, written in the one language of `rulelang.py` ([`authoring-packs.md`](authoring-packs.md)),
and answers it or does not. What becomes open is the set of engines that may discharge a duty, and
nothing else.

## Where the implementation contract lives

The numbered theory chapters are **conceptual and non-implementational**: they define the language,
denotation, and evidence model, but they are not a standalone constructor or dispatch
specification. For an executable extension, use these authoritative modules and their tests:

- `spec.py` defines `Requirement`/`Pack` loading and the closed vocabularies
  `DEONTIC_TYPES = {obligation, permission, prohibition, reparation}` and
  `DEFEASIBILITY_CLASSES = {strict, defeasible-modelled, defeasible-unmodelled, trigger-unmodelled}`;
- `sut.py` defines the required `capabilities()`, `decisions()`, and `logic()` protocol, while
  `adapters/callable.py` (`CallableAdapter(target, declared_capabilities, test_inputs=None, decisions=None)`)
  and `adapters/rules.py` are the reference constructors;
- `report.py` defines `RequirementResult` and refuses a result whose verdict/strength, evidence
  basis, probe budget, or applicability fields are inconsistent. In particular, an engine must
  return the requested `requirement_id`, must not claim above its `max_strength`, and must return
  `strength=None` with an inconclusive verdict when it cannot answer;
- `plugins.py` defines entry-point discovery and `report.py`'s `_engine_ladder` defines dispatch:
  installed engines are offered reached requirements at their declared ceiling, the strongest
  valid evidence wins, and import/call/type/ceiling failures are `not evaluated`, never a verdict.

This page is the public extension guide; the modules above, not a theory chapter or an inferred
vocabulary, are the authority when the two descriptions need a detail.

## What a plug-in must supply

An entry point in the group `reasonsmith.engines`, resolving to any object with two attributes:

```toml
# your package's pyproject.toml
[project.entry-points."reasonsmith.engines"]
prolog = "my_package.engine:PrologEngine"
```

```python
from reasonsmith.report import RequirementResult
from reasonsmith.verdict import Strength, Verdict


class PrologEngine:
    #: The strongest rung this engine may ever report. See "What it may claim" below.
    max_strength = "proved"

    @staticmethod
    def evaluate(req, sut, records) -> RequirementResult:
        ...
```

- **`max_strength`** — a member of the strength lattice (`unattainable`, `observed`, `recounted`,
  `probed`, `proved`), naming the strongest evidence this engine can produce. It is both the rung the engine
  occupies on the ladder and the ceiling on what it may report.
- **`evaluate(req, sut, records)`** — the same signature the built-in engines have
  (`src/reasonsmith/engines/record.py` is the shortest one to read). `records` is the system's
  decision trace. Return a `RequirementResult` whose `requirement_id` is `req.id`, with
  `strength=None` and `verdict=inconclusive` for anything your engine cannot answer — which is the
  right answer for a requirement in a fragment you do not handle. Your engine is offered every
  requirement that reached the ladder, so declining is normal and costs nothing: the ladder simply
  takes the next rung down.

A plug-in that declares no usable `max_strength` gets no rung at all, with a warning. Without a
ceiling there is no place on the ladder to put it and no claim to check its result against.

## What it may claim

**Not more than it declared.** A result carrying a strength above `max_strength` is refused in
`RequirementResult.__post_init__` — the same place the probe budget and the not-applicable
invariants are enforced — so an engine that declares `probed` and returns `proved` cannot
*construct* the result, not merely cannot render it. The refusal is reported as *not evaluated*,
and the duty lands on the strongest built-in rung that did produce evidence.

**A `probed` result still owes its search budget.** Every rule in
[`semantics.md`](semantics.md) applies to your result exactly as it applies to a built-in's; the
plug-in surface adds a ceiling and takes nothing away.

## What happens when it misbehaves

A plug-in that raises, returns the wrong type, answers a different requirement than it was asked
about, claims above its ceiling, or cannot be imported at all is reported **not evaluated**. Never
`satisfied` — and never `violated` either: a false violation from an unaudited package is as bad
as a false pass, and neither is a way an installed package may move a verdict. The failure is named
in the evidence summary, and the built-in ladder answers the duty as though the plug-in were not
installed.

**A plug-in cannot take a built-in's name.** An entry point named `record`, `observed`, `probed`,
`proved`, `certificate`, `temporal` or `counterfactual` is refused with a warning and the built-in
stands. It is not
namespaced into `mypackage.proved` either, because namespacing would leave the shadowing engine
running under a decorated name — the same engine answering the same duty, with only the collision
hidden. These seven names are what this repository's tests are about, and an installed package that
could rebind one would change what a published verdict means while every test here still passed.

**There is no time limit.** reasonsmith does not bound how long your `evaluate` runs: a plug-in
that hangs hangs the run. Killing a running call needs a subprocess, and a subprocess needs a
serialisation contract for requirements, traces and results — a plug-in framework, which this
deliberately is not. Bound your own search and raise `TimeoutError` when it is exhausted; that is
reported not evaluated like any other failure.

## What a reader sees

Every result a plug-in produces carries the plug-in's name, in `details["engine_plugin"]` and as a
`[engine plug-in 'name']` prefix on the evidence summary — including a result the plug-in failed to
produce. A verdict whose provenance is invisible is what this project refuses everywhere else.

## What this is worth

**reasonsmith does not audit your plug-in's whole reasoning.** For a plug-in result that reports
`violated` on the `record`, `logical`, `temporal` or `counterfactual` fragments, reasonsmith can
re-derive the violation from the witness the plug-in supplied, using the reference interpreter and
the system's own replay surface. Such a result is marked `witness-checked`; a witness the core
refutes is demoted to `not evaluated`, never silently treated as a trusted finding. A plug-in result
with no checkable witness remains `trusted-ceiling`. In particular, a `satisfied` result at the
`proved` ceiling (including a counterfactual proof) still rests on the installer's trust: this
package deliberately does not check a Z3 proof term or invent a correctness certificate. Read the
per-result provenance in a report that mixes these claims; it is the installer's job to act on it.

## Verifying an engine before publishing it

Install your engine package, then run the shipped conformance kit against its entry-point name:

```console
$ reasonsmith verify-engine my-engine
```

For local development, `module:attribute` is accepted in place of an installed entry point. The
command runs eight named gold triples drawn from the shipped example systems, reports the expected
and actual verdict/strength for each, shows witness provenance, and exits `0` only when every row
passes (an honest decline is a pass); findings exit `2`. Use `--json` for machine-readable output.
The timing-violation example is shipped as `reasonsmith.examples.symbolic_rules_timing_violation`,
so this command needs no checkout data.

### What passing proves

1. On these eight inputs, the engine's verdict and strength agree with the built-in ladder, or it
declined.
2. It never reported above its declared `max_strength` — already enforced at
`report.py:698-722`, but the kit exercises it deliberately rather than incidentally.
3. Where it answered on a witness-bearing direction (§1), the witness it emitted was re-checked by
the core and confirmed.
4. Every result named its plug-in (`plugins.py:31-34`).

### What passing cannot prove, stated plainly

<!-- The witness-validator source is registered as `[@beyer-2022]`. -->
- **Eight triples are eight points.** Agreement on a gold set is not soundness, and no size of gold
set becomes soundness. The SV-COMP witness-validation experience is that validators and verifiers
disagree, that a confirmation is a *second opinion* rather than a proof, and that unconfirmed
results are common and often the validator's fault rather than the verifier's (Beyer & Strejček,
*Case Study on Verification-Witness Validators: Where We Are and Where We Go*, SAS 2022, LNCS
13790, 160–174). The kit inherits every one of those caveats.
- **The kit cannot see the direction the gold set does not go.** An engine that answers these eight
correctly and answers a ninth duty wrongly passes.
- **A confirmed violation witness certifies the witness, not the search.** The engine may have
missed ten other violations. Nothing in reasonsmith ever claimed otherwise — that is what `probed`
means and why `PROBE_BUDGET_FIELDS` is compulsory — but a passing conformance kit is exactly the
kind of artefact a reader over-reads, so `verify-engine`'s own output must carry the limit the way
`MUTATION_LIMIT` and `TREATMENT_LIMIT` ride on their results.
- **The kit says nothing about safety.** A plug-in is imported and executed (`plugins.py:87`
`ep.load()`); the trusted-code warning in the README's *Install and run* governs it, and passing
the kit does not soften that.

The kit reports agreement on eight named triples and confirms the witnesses those runs produced; it
is not an audit of the engine and does not bound what the engine does on any duty not listed above.

## Installing a pack the same way

The pack side is the same mechanism in the group `reasonsmith.packs`; see
[`authoring-packs.md`](authoring-packs.md), *Shipping a pack as its own package*.
