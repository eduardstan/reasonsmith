"""The gold-triple conformance kit for installed engine plug-ins.

``verify-engine`` deliberately checks a finite, named set of examples.  It is a conformance
smoke-test, not a second engine: plug-ins are run through the same witness checker used by the
normal report ladder, and a declined result is an honest answer rather than a failure.\n"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, replace
from typing import Any

from reasonsmith.plugins import BUILTIN_ENGINE_NAMES, ENGINE_GROUP, discover
from reasonsmith.report import ENGINE_PLUGIN_KEY, RequirementResult
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.verdict import Strength, Verdict

# The witness-validator source named by the contract is registered as `[@beyer-2022]`.
# These are intentionally prose constants.  The command and the authoring guide must carry the
# same contract, including its limits, rather than replacing it with a reassuring summary.
WHAT_PASSING_PROVES = (
    "1. On these eight inputs, the engine's verdict and strength agree with the built-in ladder, "
    "or it declined.\n"
    "2. It never reported above its declared max_strength — already enforced at "
    "report.py:698-722, but the kit exercises it deliberately rather than incidentally.\n"
    "3. Where it answered on a witness-bearing direction (§1), the witness it emitted was "
    "re-checked by the core and confirmed.\n"
    "4. Every result named its plug-in (plugins.py:31-34)."
)

# Citation for the validator caveat: `[@beyer-2022]`.
WHAT_PASSING_CANNOT_PROVE = (
    "- **Eight triples are eight points.** Agreement on a gold set is not soundness, and no size "
    "of gold set becomes soundness. The SV-COMP witness-validation experience is that validators "
    "and verifiers disagree, that a confirmation is a *second opinion* rather than a proof, and "
    "that unconfirmed results are common and often the validator's fault rather than the "
    "verifier's (Beyer & Strejček, *Case Study on Verification-Witness Validators: Where We Are "
    "and Where We Go*, SAS 2022, LNCS 13790, 160–174). The kit inherits every one of those "
    "caveats.\n"
    "- **The kit cannot see the direction the gold set does not go.** An engine that answers these "
    "eight correctly and answers a ninth duty wrongly passes.\n"
    "- **A confirmed violation witness certifies the witness, not the search.** The engine may "
    "have missed ten other violations. Nothing in reasonsmith ever claimed otherwise — that is "
    "what `probed` means and why `PROBE_BUDGET_FIELDS` is compulsory — but a *passing* "
    "conformance kit is exactly the kind of artefact a reader over-reads, so `verify-engine`'s "
    "own output must carry the limit the way `MUTATION_LIMIT` and `TREATMENT_LIMIT` ride on "
    "their results.\n"
    "- **The kit says nothing about safety.** A plug-in is imported and executed "
    "(`plugins.py:87` `ep.load()`); the trusted-code warning in the README's *Install and run* "
    "governs it, and passing the kit does not soften that."
)


def limit_sentence(count: int) -> str:
    return (
        f"The kit reports agreement on {count} named triples and confirms the witnesses those "
        "runs produced; it is not an audit of the engine and does not bound what the engine does "
        "on any duty not listed above."
    )


@dataclass(frozen=True)
class GoldTriple:
    number: int
    system: str
    requirement_id: str
    verdict: str
    strength: str | None
    witness_required: bool = False


GOLD_TRIPLES: tuple[GoldTriple, ...] = (
    GoldTriple(
        1,
        "reasonsmith.examples.symbolic_rules:system_under_test",
        "ecoa_reg_b_1002_9_a_1_timing_of_notice",
        "satisfied",
        "proved",
    ),
    GoldTriple(
        2,
        "reasonsmith.examples.symbolic_rules:system_under_test",
        "ecoa_reg_b_1002_9_b_2_specific_reasons",
        "satisfied",
        "proved",
    ),
    GoldTriple(
        3,
        "reasonsmith.examples.probabilistic_scorer:system_under_test",
        "ecoa_reg_b_1002_9_b_2_specific_reasons",
        "satisfied",
        "probed",
    ),
    GoldTriple(
        4,
        "reasonsmith.examples.neural_scorer:system_under_test",
        "ecoa_reg_b_1002_9_b_2_specific_reasons",
        "satisfied",
        "observed",
    ),
    GoldTriple(
        5,
        "reasonsmith.demo:deployed_credit_system",
        "ecoa_reg_b_1002_9_b_2_principal_reasons_complete",
        "violated",
        "probed",
    ),
    GoldTriple(
        6,
        "reasonsmith.examples.symbolic_rules:system_under_test",
        "ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out",
        "unattainable",
        None,
    ),
    GoldTriple(
        7,
        "reasonsmith.examples.symbolic_rules:system_under_test",
        "ecoa_reg_b_1002_4_a_no_disparate_treatment",
        "unattainable",
        None,
    ),
    GoldTriple(
        8,
        "reasonsmith.examples.symbolic_rules_timing_violation:system_under_test",
        "ecoa_reg_b_1002_9_a_1_timing_of_notice",
        "violated",
        "proved",
        True,
    ),
)


@dataclass(frozen=True)
class VerificationRow:
    triple: GoldTriple
    passed: bool
    verdict: str | None
    strength: str | None
    provenance: str | None
    declared_ceiling: str | None = None
    reason: str = ""

    def _strength_within_ceiling(self) -> bool:
        if self.strength is None or self.declared_ceiling is None:
            return True
        return Strength.parse(self.strength) <= Strength.parse(self.declared_ceiling)

    def to_dict(self) -> dict[str, Any]:
        return {
            "triple": self.triple.number,
            "system": self.triple.system,
            "requirement_id": self.triple.requirement_id,
            "expected": {"verdict": self.triple.verdict, "strength": self.triple.strength},
            "actual": {"verdict": self.verdict, "strength": self.strength},
            "witness_provenance": self.provenance,
            "verdict_match": self.verdict == self.triple.verdict,
            "strength_within_declared_ceiling": self._strength_within_ceiling(),
            "passed": self.passed,
            **({"reason": self.reason} if self.reason else {}),
        }


def _load_object(spec: str) -> Any:
    module_name, separator, attr = spec.rpartition(":")
    if not separator:
        module = importlib.import_module(spec)
        for candidate in ("engine", "Engine", "ENGINE", "engine_under_test"):
            if hasattr(module, candidate):
                return getattr(module, candidate)
        raise ValueError(
            f"engine module {spec!r} has no engine, Engine, ENGINE or engine_under_test attribute"
        )
    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise ValueError(f"engine module {module_name!r} has no attribute {attr!r}") from exc


def load_engine(name: str) -> tuple[str, Any]:
    """Resolve an entry-point name, with ``module:attribute`` as a local testing escape hatch."""
    for found_name, engine in discover(ENGINE_GROUP, BUILTIN_ENGINE_NAMES):
        if found_name == name:
            return found_name, engine
    if ":" in name or "." in name:
        return name, _load_object(name)
    raise ValueError(
        f"no installed {ENGINE_GROUP} entry point named {name!r}; use an installed entry-point "
        "name or module:attribute"
    )


def _result_for(
    engine: Any,
    plugin_name: str,
    ceiling: Strength,
    req: Requirement,
    sut: Any,
    records: list[dict[str, Any]],
) -> tuple[RequirementResult | None, str | None]:
    """Call and stamp an engine.

    Failures remain findings so the kit does not mistake them for declines.
    """
    result: RequirementResult | None = None
    try:
        result = engine.evaluate(req, sut, records)
        if not isinstance(result, RequirementResult):
            raise TypeError(
                f"evaluate() must return a RequirementResult, got {type(result).__name__}"
            )
        if result.requirement_id != req.id:
            raise ValueError(
                f"evaluate() answered requirement {result.requirement_id!r} when asked about "
                f"{req.id!r}"
            )
        stamped = replace(
            result,
            details={
                **result.details,
                ENGINE_PLUGIN_KEY: {
                    "name": plugin_name,
                    "max_strength": ceiling.value,
                    "group": ENGINE_GROUP,
                },
            },
            evidence_summary=f"[engine plug-in {plugin_name!r}] {result.evidence_summary}",
        )
        from reasonsmith.witness import check_plugin_result

        return check_plugin_result(req, sut, records, stamped), None
    except Exception as exc:  # a kit finding must name the plug-in failure, not abort the report
        return result, f"engine call failed: {type(exc).__name__}: {exc}"


def _one(triple: GoldTriple, engine: Any, plugin_name: str, ceiling: Strength) -> VerificationRow:
    from reasonsmith.cli import load_system_module

    try:
        sut = load_system_module(triple.system)
        pack = load_pack("ecoa")
        req = pack.get_requirement(triple.requirement_id)
        records = list(sut.decisions())
    except Exception as exc:
        return VerificationRow(
            triple=triple,
            passed=False,
            verdict=None,
            strength=None,
            provenance=None,
            declared_ceiling=ceiling.value,
            reason=f"gold triple setup failed: {type(exc).__name__}: {exc}",
        )
    result, error = _result_for(engine, plugin_name, ceiling, req, sut, records)
    if error:
        if not isinstance(result, RequirementResult):
            return VerificationRow(triple, False, None, None, None, ceiling.value, error)
        return VerificationRow(
            triple,
            False,
            result.outcome,
            result.strength.value if result.strength is not None else None,
            result.witness_provenance,
            ceiling.value,
            error,
        )
    assert result is not None
    verdict = result.outcome
    strength = result.strength.value if result.strength is not None else None
    provenance = result.witness_provenance
    witness = result.details.get("witness")
    if isinstance(witness, dict) and witness.get("provenance") == "refuted":
        return VerificationRow(
            triple,
            False,
            verdict,
            strength,
            "refuted",
            ceiling.value,
            witness.get("failure", "witness refuted"),
        )
    if result.verdict is Verdict.INCONCLUSIVE and result.strength is None:
        # Declining is expressly a passing answer, except for a refuted witness above.
        return VerificationRow(
            triple, True, verdict, strength, provenance, ceiling.value, "declined"
        )
    if triple.verdict == "unattainable" and verdict == "unattainable":
        # The built-in capability gate may answer this row before an engine is reached.  A
        # plug-in returning the same gate result is compatible with the gold outcome; a positive
        # or negative engine verdict is not.
        return VerificationRow(triple, True, verdict, strength, provenance, ceiling.value)
    if triple.witness_required and provenance != "witness-checked":
        return VerificationRow(
            triple,
            False,
            verdict,
            strength,
            provenance,
            ceiling.value,
            "the required violation witness was not core-checked",
        )
    passed = verdict == triple.verdict and strength == triple.strength
    reason = (
        "" if passed else f"expected {triple.verdict}/{triple.strength}, got {verdict}/{strength}"
    )
    return VerificationRow(triple, passed, verdict, strength, provenance, ceiling.value, reason)


def verify_engine(name: str) -> tuple[list[VerificationRow], Strength]:
    plugin_name, engine = load_engine(name)
    try:
        ceiling = Strength.parse(engine.max_strength)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"engine {name!r} declares no usable max_strength: {exc}") from exc
    return [_one(triple, engine, plugin_name, ceiling) for triple in GOLD_TRIPLES], ceiling


def render(rows: list[VerificationRow], name: str, ceiling: Strength, as_json: bool = False) -> str:
    import json

    passed = sum(row.passed for row in rows)
    payload = {
        "engine": name,
        "max_strength": ceiling.value,
        "passed": all(row.passed for row in rows),
        "passed_triples": passed,
        "triple_count": len(rows),
        "results": [row.to_dict() for row in rows],
        "what_passing_proves": WHAT_PASSING_PROVES,
        "what_passing_cannot_prove": WHAT_PASSING_CANNOT_PROVE,
        "limit": limit_sentence(len(rows)),
    }
    if as_json:
        return json.dumps(payload, indent=2)
    lines = [f"engine: {name}", f"declared max_strength: {ceiling.value}", ""]
    for row in rows:
        status = "PASS" if row.passed else "FAIL"
        actual = f"{row.verdict}/{row.strength}" if row.verdict else "error"
        expected = f"{row.triple.verdict}/{row.triple.strength or 'declined'}"
        lines.append(
            f"[{status}] triple {row.triple.number}: {row.triple.requirement_id} — "
            f"expected {expected}, got {actual}; witness: {row.provenance or 'none'}"
        )
        lines.append(
            f"      verdict match: {'yes' if row.verdict == row.triple.verdict else 'no'}; "
            f"strength within declared ceiling: "
            f"{'yes' if row._strength_within_ceiling() else 'no'}"
        )
        if row.reason:
            lines.append(f"      {row.reason}")
    lines += [
        "",
        f"summary: {passed}/{len(rows)} triples passed",
        "",
        "What passing proves:",
        WHAT_PASSING_PROVES,
        "",
        "What passing cannot prove:",
        WHAT_PASSING_CANNOT_PROVE,
        "",
        limit_sentence(len(rows)),
    ]
    return "\n".join(lines)
