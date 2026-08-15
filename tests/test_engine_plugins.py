"""An engine and a pack can be installed rather than vendored — and cannot overclaim.

Every test here installs a throwaway distribution into a tmp_path on `sys.path`: a module file
plus a `.dist-info` directory carrying `entry_points.txt`, which is all
`importlib.metadata.entry_points` reads. Nothing is pip-installed and nothing outlives the test.

The four disciplines, one test each: a plug-in cannot report above the ceiling it declared; a
plug-in that misbehaves in any way reports *not evaluated*, never satisfied and never violated; a
plug-in shadowing a built-in name is refused rather than substituted; and every plug-in result
names the plug-in that produced it.
"""

from __future__ import annotations

import importlib
import warnings
from dataclasses import replace
from pathlib import Path

import pytest

from reasonsmith.plugins import ENGINE_GROUP, PACK_GROUP, engine_rungs, pack_path
from reasonsmith.report import (
    ENGINE_PLUGIN_KEY,
    WITNESS_KEY,
    RequirementResult,
    _engine_ladder,
    _EvaluationResources,
    evaluate_requirement,
)
from reasonsmith.spec import Requirement, load_pack
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

_DIST = 0


def _install(tmp_path: Path, monkeypatch, source: str, group: str, name: str, attr: str) -> str:
    """Install a throwaway distribution exposing `attr` under entry point `name` in `group`."""
    global _DIST
    _DIST += 1
    root = tmp_path / f"site{_DIST}"
    root.mkdir()
    module = f"rs_plugin_{_DIST}"
    (root / f"{module}.py").write_text(source, encoding="utf-8")
    dist = root / f"{module}-0.0.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {module}\nVersion: 0.0.0\n", encoding="utf-8"
    )
    (dist / "entry_points.txt").write_text(
        f"[{group}]\n{name} = {module}:{attr}\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(root))
    importlib.invalidate_caches()
    return module


def _engine_source(body: str, max_strength: str = "probed") -> str:
    return (
        "from reasonsmith.report import RequirementResult\n"
        "from reasonsmith.verdict import Strength, Verdict\n\n\n"
        "class Engine:\n"
        f"    max_strength = {max_strength!r}\n\n"
        "    @staticmethod\n"
        "    def evaluate(req, sut, records):\n"
        + "".join(f"        {line}\n" for line in body.strip().splitlines())
    )


_SATISFIED = """
return RequirementResult(
    requirement_id=req.id,
    source_clause=f"{req.source_document} {req.article_clause}",
    verdict=Verdict.SATISFIED,
    strength=Strength.PROBED,
    signals_required=tuple(req.requires),
    evidence_summary="Established by the dummy engine.",
    details={"probe_budget": {
        "trials": 1, "strategy": "dummy", "seed": 0, "input_space": "none",
    }},
    binding=req.binding,
    scope=req.scope,
)
"""


def _requirement() -> Requirement:
    return Requirement(
        id="r1",
        source_document="Doc",
        article_clause="Art. 1",
        verbatim_text="quoted text",
        stakeholder="deployer",
        formalism="record",
        spec="present(signal_a)",
        rationale="Why this duty exists, in English.",
        requires=("signal_a",),
        binding=True,
        scope="",
        domains=(),
        deontic_type="obligation",
        defeasibility="strict",
    )


class _SUT(BaseSUT):
    def __init__(self):
        super().__init__({"signal_a"})

    def decisions(self):
        return [{"signal_a": "a stated reason"}]


def _evaluate(records=None):
    return evaluate_requirement(_requirement(), _SUT(), records)


# --------------------------------------------------------------------------------------
# The plug-in reaches the ladder, discharges the duty, and says who it was
# --------------------------------------------------------------------------------------


def test_an_installed_engine_joins_the_ladder_and_discharges_a_duty(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, _engine_source(_SATISFIED), ENGINE_GROUP, "dummy", "Engine")

    result = _evaluate()

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED  # above the record engine's `observed` rung
    # Discipline 4: a reader of the verdict can see a third-party engine answered.
    assert result.details[ENGINE_PLUGIN_KEY]["name"] == "dummy"
    assert "engine plug-in 'dummy'" in result.evidence_summary
    assert "dummy" in result.to_dict()["details"][ENGINE_PLUGIN_KEY]["name"]


def test_a_satisfied_plugin_cannot_self_stamp_witness_checked(tmp_path, monkeypatch):
    witness = (
        '"witness": {"kind": "trace_position", "provenance": "witness-checked", '
        '"checker": "forged", "payload": {"index": 0}}'
    )
    source = _engine_source(
        _SATISFIED.replace('"probe_budget": {', f'{witness}, "probe_budget": {{')
    )
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "forger", "Engine")

    result = _evaluate()

    assert result.witness_provenance == "trusted-ceiling"
    assert result.details[WITNESS_KEY]["provenance"] == "trusted-ceiling"
    assert "checker" not in result.details[WITNESS_KEY]


def test_a_weaker_plugin_does_not_displace_a_builtin_verdict(tmp_path, monkeypatch):
    """A plug-in below the built-in rung answers only what the built-in left un-established."""
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_SATISFIED.replace("Strength.PROBED", "Strength.OBSERVED"), "observed"),
        ENGINE_GROUP,
        "weak",
        "Engine",
    )
    result = _evaluate()
    assert result.verdict == Verdict.SATISFIED
    assert ENGINE_PLUGIN_KEY not in result.details  # the built-in record engine answered


# --------------------------------------------------------------------------------------
# Discipline 1 — a plug-in cannot report above the ceiling it declared
# --------------------------------------------------------------------------------------


def test_a_result_claiming_above_the_declared_ceiling_is_refused():
    with pytest.raises(ValueError, match="declared a maximum strength of probed but reported"):
        RequirementResult(
            requirement_id="r1",
            source_clause="Doc Art. 1",
            verdict=Verdict.SATISFIED,
            strength=Strength.PROVED,
            signals_required=("signal_a",),
            details={ENGINE_PLUGIN_KEY: {"name": "overclaimer", "max_strength": "probed"}},
        )


def test_a_plugin_result_must_declare_a_ceiling():
    with pytest.raises(ValueError, match="must declare the maximum strength"):
        RequirementResult(
            requirement_id="r1",
            source_clause="Doc Art. 1",
            verdict=Verdict.SATISFIED,
            strength=Strength.OBSERVED,
            signals_required=("signal_a",),
            details={ENGINE_PLUGIN_KEY: {"name": "silent"}},
        )


def test_an_overclaiming_plugin_reports_not_evaluated_rather_than_proved(tmp_path, monkeypatch):
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_SATISFIED.replace("Strength.PROBED", "Strength.PROVED"), "probed"),
        ENGINE_GROUP,
        "overclaimer",
        "Engine",
    )
    result = _evaluate()
    assert result.verdict != Verdict.SATISFIED or result.strength != Strength.PROVED
    # The record engine still answers from the trace; the plug-in's rung established nothing.
    assert result.strength == Strength.OBSERVED
    assert ENGINE_PLUGIN_KEY not in result.details


# --------------------------------------------------------------------------------------
# Discipline 2 — a broken plug-in reports not evaluated, never satisfied and never violated
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("raise RuntimeError('boom')", id="raises"),
        pytest.param("raise TimeoutError('gave up')", id="times-out"),
        pytest.param("return 'satisfied'", id="wrong-type"),
        pytest.param("return None", id="returns-none"),
    ],
)
def test_a_broken_plugin_establishes_nothing(tmp_path, monkeypatch, body):
    _install(tmp_path, monkeypatch, _engine_source(body), ENGINE_GROUP, "broken", "Engine")

    rungs = engine_rungs(_requirement(), _SUT(), lambda: [{"signal_a": "x"}])
    assert [s for s, _ in rungs] == [Strength.PROBED]
    result = rungs[0][1]()

    assert result.strength is None
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.details[ENGINE_PLUGIN_KEY]["name"] == "broken"  # provenance survives the failure
    # And the whole evaluation still lands on the built-in rung rather than blowing up.
    assert _evaluate().verdict == Verdict.SATISFIED


def test_a_plugin_that_cannot_be_imported_is_skipped(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, "raise ImportError('no such thing')", ENGINE_GROUP, "bad", "E")

    with pytest.warns(RuntimeWarning, match="could not be imported"):
        assert engine_rungs(_requirement(), _SUT(), lambda: []) == []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        assert _evaluate().verdict == Verdict.SATISFIED


def test_a_plugin_without_a_declared_ceiling_gets_no_rung(tmp_path, monkeypatch):
    source = _engine_source(_SATISFIED).replace("    max_strength = 'probed'\n", "")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "unbounded", "Engine")

    with pytest.warns(RuntimeWarning, match="no usable max_strength"):
        assert engine_rungs(_requirement(), _SUT(), lambda: []) == []


def test_a_broken_plugin_cannot_fail_a_duty_the_builtin_satisfies(tmp_path, monkeypatch):
    """A false violation from an unaudited package is as bad as a false pass."""
    _install(
        tmp_path,
        monkeypatch,
        _engine_source("raise RuntimeError('boom')"),
        ENGINE_GROUP,
        "broken",
        "Engine",
    )
    result = _evaluate()
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED


# --------------------------------------------------------------------------------------
# Discipline 3 — a plug-in shadowing a built-in name is refused, and the built-in stands
# --------------------------------------------------------------------------------------


def test_a_plugin_shadowing_a_builtin_engine_is_refused(tmp_path, monkeypatch):
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_SATISFIED.replace("Verdict.SATISFIED", "Verdict.VIOLATED")),
        ENGINE_GROUP,
        "record",
        "Engine",
    )
    with pytest.warns(RuntimeWarning, match="shadows a built-in"):
        rungs = engine_rungs(_requirement(), _SUT(), lambda: [])
    assert rungs == []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = _evaluate()
    assert result.verdict == Verdict.SATISFIED  # the built-in record engine still answered
    assert ENGINE_PLUGIN_KEY not in result.details


def test_a_pack_shadowing_a_builtin_pack_name_is_refused(tmp_path, monkeypatch):
    shadow = tmp_path / "shadow.toml"
    shadow.write_text("[pack]\nid = 'not-gdpr'\n", encoding="utf-8")
    _install(
        tmp_path,
        monkeypatch,
        f"PACK = {str(shadow)!r}\n",
        PACK_GROUP,
        "gdpr",
        "PACK",
    )
    assert load_pack("gdpr").id == "gdpr"  # the built-in, not the shadow
    with pytest.warns(RuntimeWarning, match="shadows a built-in"):
        assert pack_path("gdpr", ("gdpr",)) is None


# --------------------------------------------------------------------------------------
# An installed pack resolves through the one loader
# --------------------------------------------------------------------------------------


_PACK_BODY = """
[pack]
id = "installed"
title = "An installed pack"

[[requirement]]
id = "installed_1"
source_document = "Doc"
article_clause = "Art. 1"
verbatim_text = "quoted text"
stakeholder = "deployer"
formalism = "record"
spec = "present(signal_a)"
rationale = "Why this duty exists, in English."
requires = ["signal_a"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
"""


def test_an_installed_pack_loads_by_name(tmp_path, monkeypatch):
    pack_file = tmp_path / "installed.toml"
    pack_file.write_text(_PACK_BODY, encoding="utf-8")
    _install(tmp_path, monkeypatch, f"PACK = {str(pack_file)!r}\n", PACK_GROUP, "installed", "PACK")

    pack = load_pack("installed")
    assert pack.id == "installed"
    assert [r.id for r in pack.requirements] == ["installed_1"]


def test_an_installed_pack_may_be_a_callable(tmp_path, monkeypatch):
    pack_file = tmp_path / "callable.toml"
    pack_file.write_text(_PACK_BODY, encoding="utf-8")
    _install(
        tmp_path,
        monkeypatch,
        f"def pack():\n    return {str(pack_file)!r}\n",
        PACK_GROUP,
        "callable_pack",
        "pack",
    )
    assert load_pack("callable_pack").id == "installed"


def test_an_installed_pack_is_held_to_every_rule_an_in_tree_one_is(tmp_path, monkeypatch):
    bad = tmp_path / "bad.toml"
    bad.write_text(_PACK_BODY.replace("domains = []", 'domains = ["not-a-domain"]'), "utf-8")
    _install(tmp_path, monkeypatch, f"PACK = {str(bad)!r}\n", PACK_GROUP, "bad_pack", "PACK")

    with pytest.raises(ValueError, match="not a known decision domain"):
        load_pack("bad_pack")


def test_an_installed_pack_naming_no_file_is_refused(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, "PACK = '/nowhere/absent.toml'\n", PACK_GROUP, "absent", "PACK")
    with pytest.raises(FileNotFoundError, match="which is not a file"):
        load_pack("absent")


# --------------------------------------------------------------------------------------
# Nothing installed behaves exactly as before
# --------------------------------------------------------------------------------------


def test_with_no_plugin_installed_the_ladder_is_the_builtin_ladder():
    req = _requirement()
    sut = _SUT()
    assert engine_rungs(req, sut, lambda: []) == []
    ladder = _engine_ladder(req, sut, None, _EvaluationResources(sut))
    # The proof rung (this SUT exposes `logic()`, which returns None) and the record engine.
    assert [s for s, _ in ladder] == [Strength.PROVED, Strength.OBSERVED]
    result = _evaluate()
    assert (result.verdict, result.strength) == (Verdict.SATISFIED, Strength.OBSERVED)
    assert ENGINE_PLUGIN_KEY not in result.details


def test_generic_engine_plugins_cannot_answer_counterfactual_requirements(tmp_path, monkeypatch):
    """Relational duties stay on audited pair-producing paths, never trace plug-ins."""
    source = _engine_source(_SATISFIED)
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "counterfactual-forger", "Engine")
    req = replace(
        _requirement(),
        formalism="counterfactual",
        spec="counterfactually_invariant(signal_a, protected)",
        requires=("signal_a",),
    )
    from reasonsmith.report import _EvaluationResources

    ladder = _engine_ladder(req, _SUT(), None, _EvaluationResources(_SUT()))
    assert [strength for strength, _ in ladder] == [Strength.PROVED, Strength.PROBED]
    result = ladder[0][1]()
    assert result.details.get(ENGINE_PLUGIN_KEY) is None

    certificate_req = replace(
        _requirement(), requires=("artifact_logs_deleted_reason_count",)
    )
    certificate_ladder = _engine_ladder(
        certificate_req, _SUT(), None, _EvaluationResources(_SUT())
    )
    assert [strength for strength, _ in certificate_ladder] == [Strength.PROBED]
    certificate_result = certificate_ladder[0][1]()
    assert certificate_result.details.get(ENGINE_PLUGIN_KEY) is None


# --------------------------------------------------------------------------------------
# Slice 1 — plug-in violation witnesses are independently re-checked
# --------------------------------------------------------------------------------------


def _violation_source(witness: str = "") -> str:
    details = (
        '{"probe_budget": {"trials": 1, "strategy": "dummy", "seed": 0, "input_space": "none"}'
    )
    if witness:
        details += ', "witness": ' + witness
    details += "}"
    return "\n".join(
        [
            "return RequirementResult(",
            "    requirement_id=req.id,",
            '    source_clause=f"{req.source_document} {req.article_clause}",',
            "    verdict=Verdict.VIOLATED,",
            "    strength=Strength.PROBED,",
            "    signals_required=tuple(req.requires),",
            '    evidence_summary="The dummy engine found a violation.",',
            f"    details={details},",
            "    binding=req.binding,",
            "    scope=req.scope,",
            ")",
        ]
    )


def test_a_witnessless_plugin_violation_is_trusted_at_its_ceiling(tmp_path, monkeypatch):
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_violation_source()),
        ENGINE_GROUP,
        "ceiling",
        "Engine",
    )
    result = engine_rungs(_requirement(), _SUT(), lambda: [{"signal_a": "stated"}])[0][1]()
    assert result.verdict is Verdict.VIOLATED
    assert result.witness_provenance == "trusted-ceiling"
    assert result.to_dict()["witness_provenance"] == "trusted-ceiling"


def test_a_rechecked_plugin_violation_is_witness_checked(tmp_path, monkeypatch):
    witness = (
        '{"kind": "presence_absence", "provenance": "trusted-ceiling", '
        '"checker": "dummy", "payload": {"indices": [0], '
        '"signals": ["signal_a"]}}'
    )
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_violation_source(witness)),
        ENGINE_GROUP,
        "checker",
        "Engine",
    )
    result = engine_rungs(_requirement(), _SUT(), lambda: [{"signal_a": None}])[0][1]()
    assert result.verdict is Verdict.VIOLATED
    assert result.witness_provenance == "witness-checked"
    assert result.details[WITNESS_KEY]["provenance"] == "witness-checked"


def test_a_refuted_plugin_witness_demotes_without_flipping(tmp_path, monkeypatch):
    witness = (
        '{"kind": "presence_absence", "provenance": "trusted-ceiling", '
        '"checker": "dummy", "payload": {"indices": [0], '
        '"signals": ["signal_a"]}}'
    )
    _install(
        tmp_path,
        monkeypatch,
        _engine_source(_violation_source(witness)),
        ENGINE_GROUP,
        "liar",
        "Engine",
    )
    result = engine_rungs(_requirement(), _SUT(), lambda: [{"signal_a": "stated"}])[0][1]()
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.details[WITNESS_KEY]["provenance"] == "refuted"
    assert "unverified_payload" in result.details[WITNESS_KEY]
