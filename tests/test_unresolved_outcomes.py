"""Machine-readable operational outcomes and strict unresolved automation."""

from __future__ import annotations

import re
from pathlib import Path

from reasonsmith.cli import main
from reasonsmith.report import RequirementResult
from reasonsmith.verdict import Strength, Verdict


def _semantics_outcomes() -> set[str]:
    """Read the operational vocabulary from the reader contract, not a second list."""
    text = Path("docs/semantics.md").read_text(encoding="utf-8")
    section = text.split("## 1. The report's five operational outcomes", 1)[1]
    table = section[section.index("| Outcome"):].split("\n\n", 1)[0]
    return {match.replace(" ", "_") for match in re.findall(r"\*\*([^*]+)\*\*", table)}


def _result(**kwargs) -> RequirementResult:
    values = dict(
        requirement_id="req", source_clause="Test", verdict=Verdict.INCONCLUSIVE,
        strength=None, signals_required=(),
    )
    values.update(kwargs)
    if values.get("strength") is Strength.UNATTAINABLE:
        values["signals_required"] = ("missing",)
        values["signals_missing"] = ("missing",)
    return RequirementResult(**values)


def test_outcome_field_uses_the_semantics_operational_vocabulary():
    expected = _semantics_outcomes()
    results = (
        _result(verdict=Verdict.SATISFIED, strength=Strength.OBSERVED),
        _result(verdict=Verdict.VIOLATED, strength=Strength.OBSERVED),
        _result(verdict=Verdict.NOT_APPLICABLE),
        _result(strength=None),
        _result(strength=Strength.UNATTAINABLE),
    )
    assert {result.outcome for result in results} == expected
    assert all(result.to_dict()["outcome"] in expected for result in results)


def _pack(tmp_path, *, domains=(), formalism="record", spec="present(signal)", requires=("signal",)):
    path = tmp_path / f"pack_{formalism}_{len(domains)}_{requires[0]}.toml"
    domains_toml = "[" + ", ".join(repr(value) for value in domains) + "]"
    requires_toml = "[" + ", ".join(repr(value) for value in requires) + "]"
    path.write_text(
        f'''[pack]
id = "strict_test_{formalism}_{len(domains)}"
title = "Strict test"
description = "Strict mode test pack."

[source]
document = "Test"
url = "https://example.invalid"

[[requirement]]
id = "strict_requirement"
source_document = "Test"
article_clause = "1"
verbatim_text = "Test clause"
stakeholder = "deployer"
formalism = "{formalism}"
spec = {spec!r}
rationale = "A test rationale."
requires = {requires_toml}
binding = true
scope = ""
domains = {domains_toml}
deontic_type = "obligation"
defeasibility = "strict"
''',
        encoding="utf-8",
    )
    return path


def _log(tmp_path, fields=("signal",)):
    path = tmp_path / "decisions.jsonl"
    path.write_text("{" + ", ".join(f'"{field}": true' for field in fields) + "}\n", encoding="utf-8")
    return path


def test_strict_mode_fails_for_each_unresolved_outcome(tmp_path, capsys):
    cases = (
        ("unattainable", _pack(tmp_path, spec="present(missing)", requires=("missing",)), _log(tmp_path)),
        (
            "not_evaluated",
            _pack(tmp_path, formalism="undetermined", spec='undetermined(signal, "predicate", "authority")'),
            _log(tmp_path),
        ),
        ("not_applicable", _pack(tmp_path, domains=("consumer-credit",)), _log(tmp_path)),
    )
    for outcome, pack, log in cases:
        assert main(["check", "--system", str(log), "--pack", str(pack), "--strict-unresolved"]) == 3
        captured = capsys.readouterr()
        assert f"strict unresolved: 1 {outcome.replace('_', ' ')}" in captured.out


def test_default_exit_stays_zero_for_unresolved_outcomes(tmp_path, capsys):
    pack = _pack(tmp_path, domains=("consumer-credit",))
    assert main(["check", "--system", str(_log(tmp_path)), "--pack", str(pack)]) == 0
    assert "strict unresolved" not in capsys.readouterr().out
