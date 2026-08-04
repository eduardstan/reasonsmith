"""Animated verdict counters strip."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from reasonsmith.report import ConformanceReport

VERDICT_COLORS = {
    "proved": "#7ad9a6",
    "probed": "#5dc4d8",
    "observed": "#3aa0c0",
    "violated": "#f08484",
    "inconclusive": "#e8c97e",
    "not_evaluated": "#9aa4b2",
    "unattainable": "#b08db5",
    "not_applicable": "#6f7d8c",
}


class CounterBar(Static):
    """A horizontal strip of verdict counters with subtle pulse shading."""

    pulse: reactive[float] = reactive(0.0)

    def __init__(self, report: ConformanceReport) -> None:
        super().__init__(id="counter-bar")
        self.report = report
        self._base_counts = dict(report.counts)

    def render(self) -> str:
        cells: list[str] = []
        counts = self._base_counts
        for key in (
            "proved",
            "probed",
            "observed",
            "violated",
            "inconclusive",
            "not_evaluated",
            "unattainable",
            "not_applicable",
        ):
            color = VERDICT_COLORS[key]
            label = key.replace("_", " ")
            cells.append(f"[{color}]●[/] [b]{counts[key]}[/] [dim]{label}[/]")
        return "   ".join(cells)

    def action_pulse(self, strength: float = 0.4) -> None:
        """Trigger a brief visual pulse on the bar."""
        self.pulse = strength
        self.set_class(self.pulse > 0, "active")
        self.refresh()
        self.set_timer(0.5, self._reset_pulse)

    def _reset_pulse(self) -> None:
        self.pulse = 0.0
        self.set_class(False, "active")
        self.refresh()
