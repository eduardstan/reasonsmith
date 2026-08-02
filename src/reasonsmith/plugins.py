"""Engine and pack discovery through installed entry points.

What this module is for:
  Lets a third party ship an engine or a regulation pack as its own pip package, discovered
  through `importlib.metadata.entry_points` in the groups `reasonsmith.engines` and
  `reasonsmith.packs`, without touching this repository. `report._engine_ladder` merges the
  discovered engines into the ladder beside the built-ins, and `spec.load_pack` resolves a pack
  name an installed package provides. With nothing installed both groups are empty and every
  code path here returns nothing.

What a reader must not break:
  - A plug-in engine declares its ceiling in `max_strength` and cannot report above it. The
    refusal lives in `RequirementResult.__post_init__` (see `report.ENGINE_PLUGIN_KEY`), beside
    the other invariants of that kind, so a plug-in result claiming more than it declared cannot
    be *constructed* — not merely cannot be rendered.
    Why this matters: the ceiling is the only thing an installer can read before trusting a
    package. An engine that could quietly return `proved` having declared `probed` makes the
    declaration decorative.
  - A plug-in that cannot be imported, raises, returns the wrong type, or claims above its
    ceiling is reported *not evaluated*. Never satisfied, and never violated either: a false
    violation from a broken third-party engine is as bad as a false pass.
    Why this matters: an installed package must not be able to move a verdict by malfunctioning,
    in either direction.
  - A plug-in whose entry-point name is a built-in's is refused, with a warning, and the built-in
    stands. Not namespaced, not overridden.
    Why this matters: `proved` names a rung of the lattice, and the four built-in engines are what
    this repository's tests are about. An installed package that could rebind one of those names
    would redefine what a published verdict means while every test here still passed. Namespacing
    it instead would keep the shadowing engine running under a decorated name, which is the same
    engine answering the same duty — the refusal is the point.
  - Every result a plug-in produces carries the plug-in's name, in `details` and in the evidence
    summary.
    Why this matters: a verdict whose provenance is invisible is what this package refuses
    everywhere else. A reader must be able to see that a third-party engine answered.

What this module deliberately does not do:
  Bound a plug-in's runtime. There is no wall clock here: a plug-in that hangs hangs the run, and
  a plug-in wanting a time bound raises `TimeoutError` itself, which is reported not evaluated
  like any other failure. Killing a running call needs a subprocess, and a subprocess needs a
  serialisation contract for requirements, traces and results — a plug-in framework, which this
  is not. `docs/authoring-engines.md` states the limit to a plug-in author.
"""

from __future__ import annotations

import warnings
from dataclasses import replace
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

from reasonsmith.verdict import Strength, Verdict

ENGINE_GROUP = "reasonsmith.engines"
PACK_GROUP = "reasonsmith.packs"

#: The engine names this repository ships. An entry point claiming one of these is refused; see
#: the module docstring.
BUILTIN_ENGINE_NAMES = ("record", "observed", "probed", "proved", "certificate", "temporal")


def discover(group: str, builtin_names: tuple[str, ...] = ()) -> list[tuple[str, Any]]:
    """Load every entry point in `group`, skipping one that shadows a built-in or fails to import.

    Sorted by name so a run over two installed plug-ins is ordered by something other than which
    distribution the metadata finder happened to reach first.
    """
    found: list[tuple[str, Any]] = []
    for ep in sorted(entry_points(group=group), key=lambda e: e.name):
        if ep.name in builtin_names:
            warnings.warn(
                f"{group} entry point {ep.name!r} (from {ep.value}) shadows a built-in of that "
                "name and was refused; the built-in stands. Rename the entry point.",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        try:
            found.append((ep.name, ep.load()))
        except Exception as exc:  # noqa: BLE001 - a broken plug-in must not break the run
            warnings.warn(
                f"{group} entry point {ep.name!r} (from {ep.value}) could not be imported and was "
                f"skipped: {type(exc).__name__}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
    return found


def _plugin_details(name: str, ceiling: Strength) -> dict[str, Any]:
    return {"name": name, "max_strength": ceiling.value, "group": ENGINE_GROUP}


def _not_evaluated(req: Any, name: str, ceiling: Strength, why: str) -> Any:
    from reasonsmith.report import ENGINE_PLUGIN_KEY, RequirementResult

    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Not evaluated: the third-party engine plug-in {name!r} established nothing — {why}."
        ),
        details={ENGINE_PLUGIN_KEY: _plugin_details(name, ceiling)},
        binding=req.binding,
        scope=req.scope,
    )


def _run(
    req: Any, sut: Any, trace: Callable[[], Any], name: str, engine: Any, ceiling: Strength
) -> Any:
    from reasonsmith.report import ENGINE_PLUGIN_KEY, RequirementResult

    try:
        result = engine.evaluate(req, sut, trace())
        if not isinstance(result, RequirementResult):
            raise TypeError(
                f"evaluate() must return a RequirementResult, got {type(result).__name__}"
            )
        if result.requirement_id != req.id:
            raise ValueError(
                f"evaluate() answered requirement {result.requirement_id!r} when asked about "
                f"{req.id!r}"
            )
        # `replace` re-runs `RequirementResult.__post_init__`, which is where a strength above the
        # declared ceiling is refused. The refusal lands in the `except` below and is reported not
        # evaluated, like every other way a plug-in can misbehave.
        return replace(
            result,
            details={**result.details, ENGINE_PLUGIN_KEY: _plugin_details(name, ceiling)},
            evidence_summary=f"[engine plug-in {name!r}] {result.evidence_summary}",
        )
    except Exception as exc:  # noqa: BLE001 - a broken plug-in must not move a verdict
        return _not_evaluated(req, name, ceiling, f"{type(exc).__name__}: {exc}")


def engine_rungs(
    req: Any, sut: Any, trace: Callable[[], Any]
) -> list[tuple[Strength, Callable[[], Any]]]:
    """The ladder rungs installed engine plug-ins contribute, each at its declared ceiling.

    A plug-in that does not declare a usable `max_strength` gets no rung at all: without a ceiling
    there is no place on the ladder to put it and no claim to check its result against.
    """
    rungs: list[tuple[Strength, Callable[[], Any]]] = []
    for name, engine in discover(ENGINE_GROUP, BUILTIN_ENGINE_NAMES):
        try:
            ceiling = Strength.parse(engine.max_strength)
        except (AttributeError, TypeError, ValueError) as exc:
            warnings.warn(
                f"{ENGINE_GROUP} entry point {name!r} declares no usable max_strength and was "
                f"skipped: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        rungs.append(
            (
                ceiling,
                lambda n=name, e=engine, c=ceiling: _run(req, sut, trace, n, e, c),
            )
        )
    return rungs


def pack_path(name: str, builtin_names: tuple[str, ...] = ()) -> Path | None:
    """The TOML file an installed package provides under pack name `name`, or None.

    The entry point resolves to a path to a pack file, or to a zero-argument callable returning
    one — the second form is how a package that ships its pack inside a wheel points at it. What
    comes back is loaded by the same `load_pack` code path a built-in is, so an externally
    provided pack is held to every rule an in-tree one is.
    """
    for found_name, value in discover(PACK_GROUP, builtin_names):
        if found_name != name:
            continue
        if callable(value):
            value = value()
        if not isinstance(value, (str, Path)):
            raise ValueError(
                f"{PACK_GROUP} entry point {name!r} must resolve to a path to a pack TOML file, "
                f"or to a callable returning one; got {type(value).__name__}"
            )
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(
                f"{PACK_GROUP} entry point {name!r} names {path}, which is not a file"
            )
        return path
    return None


def pack_names(builtin_names: tuple[str, ...] = ()) -> list[str]:
    """The pack names installed packages provide, for an error message that can name them."""
    return [name for name, _ in discover(PACK_GROUP, builtin_names)]
