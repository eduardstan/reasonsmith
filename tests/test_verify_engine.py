"""The shipped gold-triple conformance kit refuses overclaim and bad witnesses."""

from __future__ import annotations

from test_engine_plugins import _install

from reasonsmith.plugins import ENGINE_GROUP
from reasonsmith.verdict import Strength
from reasonsmith.verify_engine import verify_engine


def _engine_source(body: str, ceiling: str = "proved") -> str:
    return (
        "from reasonsmith.report import RequirementResult\n"
        "from reasonsmith.verdict import Strength, Verdict\n"
        "class Engine:\n"
        f"    max_strength = {ceiling!r}\n"
        "    @staticmethod\n"
        "    def evaluate(req, sut, records):\n"
        + "".join(f"        {line}\n" for line in body.strip().splitlines())
    )


def _result(verdict: str, strength: str | None = None, details: str = "{}"):
    return (
        "return RequirementResult(\n"
        "    requirement_id=req.id, source_clause='',\n"
        f"    verdict=Verdict.{verdict.upper()}, "
        f"strength={('None' if strength is None else 'Strength.' + strength.upper())},\n"
        "    signals_required=tuple(req.requires), details="
        + details
        + ", binding=req.binding, scope=req.scope)"
    )


def test_verify_engine_passes_a_known_good_engine_that_declines_everything(tmp_path, monkeypatch):
    source = _engine_source(_result("inconclusive"))
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-good", "Engine")

    rows, ceiling = verify_engine("gold-good")

    assert ceiling is Strength.PROVED
    assert len(rows) == 8
    assert all(row.passed for row in rows)


def test_verify_engine_fails_a_ceiling_violation(tmp_path, monkeypatch):
    source = _engine_source(_result("satisfied", "proved"), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-overclaim", "Engine")

    rows, _ = verify_engine("gold-overclaim")

    assert not all(row.passed for row in rows)
    assert all("engine call failed" in row.reason for row in rows)
    assert all(not row._strength_within_ceiling() for row in rows)


def test_verify_engine_fails_wrong_verdicts(tmp_path, monkeypatch):
    source = _engine_source(_result("satisfied", "observed"), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-wrong", "Engine")

    rows, _ = verify_engine("gold-wrong")

    assert not all(row.passed for row in rows)
    assert any("expected" in row.reason for row in rows)


def test_verify_engine_fails_a_refuted_witness(tmp_path, monkeypatch):
    witness = (
        '{"witness": {"kind": "trace_position", "provenance": "trusted-ceiling", '
        '"payload": {"index": 0}}}'
    )
    source = _engine_source(_result("violated", "observed", witness), ceiling="observed")
    _install(tmp_path, monkeypatch, source, ENGINE_GROUP, "gold-refuted", "Engine")

    rows, _ = verify_engine("gold-refuted")

    assert not all(row.passed for row in rows)
    assert any(row.provenance == "refuted" for row in rows)
    assert any(row.provenance == "refuted" for row in rows)
