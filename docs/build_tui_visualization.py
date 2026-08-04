"""Capture the reasonsmith TUI as a terminal-native SVG visualization.

Run after installing the optional extra:

    python docs/build_tui_visualization.py

The script uses Textual's built-in headless screenshot pipeline, so it does not require a terminal
or browser and remains deterministic enough for documentation review.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from reasonsmith.cli import load_system_module
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack
from reasonsmith.tui.app import ReasonsmithApp
from reasonsmith.tui.data import TuiOptions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "tui.svg"


async def build() -> None:
    sut = load_system_module("reasonsmith.examples.truncating_credit_system:system_under_test")
    report = check_conformance(
        sut,
        load_pack("ecoa"),
        system_name="TruncatingCreditSystem",
        system_domains=("consumer-credit",),
    )
    options = TuiOptions(
        pack="ecoa",
        system=None,
        system_module="reasonsmith.examples.truncating_credit_system:system_under_test",
        system_name="TruncatingCreditSystem",
        system_scope=None,
        system_domains=("consumer-credit",),
        audience="auditor",
    )
    app = ReasonsmithApp(report, options)
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause()
        svg = app.export_screenshot(title="reasonsmith TUI · evidence explorer")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(OUT)


asyncio.run(build())
