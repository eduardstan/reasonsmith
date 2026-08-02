# Authoring an engine plug-in

reasonsmith discovers engines through `importlib.metadata.entry_points`. An engine you ship as
your own pip package joins the ladder the moment it is installed, and you never touch this
repository to do it. The answer to *can reasonsmith use Prolog, ASP, or a different solver?* is
**yes, as a package you install**, not *send us a pull request*.

The property language does not change. Your engine is handed the same `Requirement` the built-ins
are, written in the one language of `rulelang.py` ([`authoring-packs.md`](authoring-packs.md)),
and answers it or does not. What becomes open is the set of engines that may discharge a duty, and
nothing else.

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

- **`max_strength`** — a member of the strength lattice (`unattainable`, `observed`, `probed`,
  `proved`), naming the strongest evidence this engine can produce. It is both the rung the engine
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
`proved` or `certificate` is refused with a warning and the built-in stands. It is not namespaced
into `mypackage.proved` either, because namespacing would leave the shadowing engine running under
a decorated name — the same engine answering the same duty, with only the collision hidden. These
five names are what this repository's tests are about, and an installed package that could rebind
one would change what a published verdict means while every test here still passed.

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

**reasonsmith does not audit your plug-in.** It checks that the result is well-formed and that the
strength is within the ceiling the plug-in itself declared; it does not and cannot check that the
engine's reasoning is sound. A `proved` from an unfamiliar engine is therefore worth exactly what
the installer's trust in that package is worth — no more. That is a different kind of claim from a
`proved` produced by `engines/proved.py`, which this repository's suite is about, and a reader of a
report that mixes the two should be told which is which. The provenance in every plug-in result is
what makes that possible; reading it is the installer's job.

## Installing a pack the same way

The pack side is the same mechanism in the group `reasonsmith.packs`; see
[`authoring-packs.md`](authoring-packs.md), *Shipping a pack as its own package*.
