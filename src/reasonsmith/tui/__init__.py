"""Interactive terminal views for reasonsmith conformance reports.

The TUI is an optional presentation layer. It consumes the same frozen report objects as the
plain-text, JSON, and HTML renderers; it does not evaluate systems or reinterpret verdicts.
"""

from __future__ import annotations

from collections.abc import Sequence


def main(args: Sequence[str] | None = None) -> int:
    """Run the optional Textual application."""
    from reasonsmith.tui.app import ReasonsmithApp
    from reasonsmith.tui.data import load_report

    report, options = load_report(args)
    ReasonsmithApp(report, options=options).run()
    return 0


__all__ = ["main"]
