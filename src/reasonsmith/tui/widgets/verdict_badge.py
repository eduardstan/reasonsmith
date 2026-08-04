"""Verdict badge with color-coded label."""

from __future__ import annotations

from textual.widgets import Static

VERDICT_COLORS = {
    "proved": "#7ad9a6",
    "probed": "#5dc4d8",
    "observed": "#3aa0c0",
    "violated": "#f08484",
    "inconclusive": "#e8c97e",
    "not_evaluated": "#9aa4b2",
    "unattainable": "#b08db5",
    "not_applicable": "#6f7d8c",
    "satisfied": "#7ad9a6",
}


class VerdictBadge(Static):
    """Compact verdict badge that colors text and adds an emblem glyph."""

    def __init__(self, verdict: str) -> None:
        super().__init__(id="verdict-badge")
        self.verdict = verdict

    def render(self) -> str:
        value = self.verdict.lower()
        color = VERDICT_COLORS.get(value, "#cbd5e1")
        glyph = {
            "proved": "✓",
            "probed": "≈",
            "observed": "●",
            "violated": "✗",
            "inconclusive": "?",
            "unattainable": "▣",
            "not_evaluated": "–",
            "not_applicable": "—",
            "satisfied": "✓",
        }.get(value, "·")
        return f"[black on {color}] {glyph} {value.upper()} [/]"
