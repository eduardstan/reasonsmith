"""A live insights footer strip that updates asynchronously."""

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.widgets import Static

from reasonsmith.report import ConformanceReport


class InsightsBar(Static):
    """A one-line summary that surfaces the report's hero counts and the active row."""

    report: reactive[ConformanceReport | None] = reactive(None)
    selected_id: reactive[str] = reactive("—")

    def watch_report(self, _: Any) -> None:
        self.refresh()

    def watch_selected_id(self, _: Any) -> None:
        self.refresh()

    def render(self) -> str:
        report = self.report
        if report is None:
            return "Loading insights…"
        counts = report.counts
        return (
            f"[b]Now:[/b] {self.selected_id} · "
            f"[b]Hero counts:[/b] proved {counts['proved']} · "
            f"observed {counts['observed']} · "
            f"violated {counts['violated']} · "
            f"unattainable {counts['unattainable']}"
        )
