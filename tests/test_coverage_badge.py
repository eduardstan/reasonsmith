"""Behavioral contract for the repository-hosted measured coverage badge."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docs.build_coverage_badge import build_badge


def _report(path: Path, value: float) -> None:
    path.write_text(json.dumps({"totals": {"percent_covered": value}}), encoding="utf-8")


def test_badge_uses_measured_percentage_and_green_at_floor(tmp_path: Path):
    report = tmp_path / "coverage.json"
    badge = tmp_path / "coverage.svg"
    _report(report, 95.0)

    build_badge(report, badge)

    output = badge.read_text(encoding="utf-8")
    assert 'aria-label="coverage: 95.00%"' in output
    assert 'fill="#2da44e"' in output
    assert "95.00%" in output


def test_badge_marks_measurement_below_target_red(tmp_path: Path):
    report = tmp_path / "coverage.json"
    badge = tmp_path / "coverage.svg"
    _report(report, 94.999)

    build_badge(report, badge)

    assert 'aria-label="coverage: 95.00%"' in badge.read_text(encoding="utf-8")
    assert 'fill="#cf222e"' in badge.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "payload",
    [{}, {"totals": {}}, {"totals": {"percent_covered": "not-a-number"}}],
)
def test_badge_rejects_missing_or_invalid_measurement(tmp_path: Path, payload):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="coverage JSON"):
        build_badge(report, tmp_path / "coverage.svg")


def test_badge_rejects_impossible_measurement(tmp_path: Path):
    report = tmp_path / "coverage.json"
    _report(report, 101)

    with pytest.raises(ValueError, match="between 0 and 100"):
        build_badge(report, tmp_path / "coverage.svg")
