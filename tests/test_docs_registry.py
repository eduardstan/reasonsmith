"""Pins the generated discovery registry to its builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "registry.html"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_registry", ROOT / "docs" / "build_registry.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_html_matches_builder():
    assert PAGE.read_text(encoding="utf-8") == _builder().build()


def test_registry_disclaimer_and_inventory():
    page = PAGE.read_text(encoding="utf-8")
    assert _builder().DISCLAIMER in page
    for name in ("ecoa", "gdpr", "record", "proved"):
        assert name in page
