"""Textual application for exploring a conformance report."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Markdown, Static

from reasonsmith.report import ConformanceReport
from reasonsmith.tui.data import TuiOptions, result_rows


class ReasonsmithApp(App[None]):
    """A keyboard-first report explorer with an evidence graph view."""

    TITLE = "reasonsmith · evidence explorer"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "cycle_audience", "Audience"),
        Binding("j", "next_row", "Next"),
        Binding("k", "previous_row", "Previous"),
        Binding("r", "refresh_view", "Refresh"),
        Binding("?", "help", "Help"),
    ]
    AUDIENCES = ("auditor", "developer", "deployer", "regulator", "affected-individual")

    def __init__(self, report: ConformanceReport, options: TuiOptions):
        super().__init__()
        self.report = report
        self.options = options
        self.audience_index = self.AUDIENCES.index(options.audience)
        self.rows = result_rows(report)

    @property
    def audience(self) -> str:
        return self.AUDIENCES[self.audience_index]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._overview(), id="overview")
        with Horizontal(id="main-pane"):
            with Vertical(id="requirements-pane"):
                yield Label("REQUIREMENTS", classes="pane-title")
                yield DataTable(id="requirements")
            with Vertical(id="detail-pane"):
                yield Label("EVIDENCE GRAPH", classes="pane-title")
                yield Markdown(self._detail(0), id="detail")
        yield Static(self.report.limits, id="limits")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#requirements", DataTable)
        table.add_columns("Verdict", "Strength", "Requirement", "Source")
        for row in self.rows:
            table.add_row(
                row["verdict"].upper(),
                row["strength"],
                row["id"],
                row["source"],
                key=row["id"],
            )
        table.cursor_type = "row"
        if self.rows:
            table.move_cursor(row=0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        row_index = next(
            (index for index, row in enumerate(self.rows) if row["id"] == event.row_key.value),
            0,
        )
        self.query_one("#detail", Markdown).update(self._detail(row_index))

    def action_next_row(self) -> None:
        self.query_one("#requirements", DataTable).action_cursor_down()

    def action_previous_row(self) -> None:
        self.query_one("#requirements", DataTable).action_cursor_up()

    def action_cycle_audience(self) -> None:
        self.audience_index = (self.audience_index + 1) % len(self.AUDIENCES)
        self.query_one("#overview", Static).update(self._overview())
        self.query_one("#detail", Markdown).update(self._detail(0))

    def action_refresh_view(self) -> None:
        self.query_one("#overview", Static).update(self._overview())

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def _overview(self) -> str:
        counts = self.report.counts
        return (
            f"[b]{self.report.system_name}[/b]  ·  pack [cyan]{self.report.pack_id}[/cyan]  ·  "
            f"audience [cyan]{self.audience}[/cyan]\n"
            f"{self.report.headline}\n"
            f"proved={counts['proved']}  probed={counts['probed']}  observed={counts['observed']}  "
            f"violated={counts['violated']}  inconclusive={counts['inconclusive']}  "
            f"not-evaluated={counts['not_evaluated']}  unattainable={counts['unattainable']}  "
            f"not-applicable={counts['not_applicable']}"
        )

    def _detail(self, index: int) -> str:
        if not self.rows:
            return "No requirements were reported."
        row = self.rows[min(index, len(self.rows) - 1)]
        details = row["details"]
        lines = [
            f"# {row['id']}",
            f"**Verdict:** `{row['verdict']}`  **Strength:** `{row['strength']}`",
            f"**Source:** {row['source']}",
            "",
            "## Evidence",
            row["evidence"] or "No evidence summary was emitted.",
            "",
            "## Required signals",
            ", ".join(row["required"]) or "None declared",
        ]
        if row["missing"]:
            lines.extend(["", "## Missing signals", ", ".join(row["missing"])])
        if details:
            lines.extend(["", "## Evidence graph metadata", "```json", _json(details), "```"])
        if self.audience == "affected-individual":
            lines.extend(
                [
                    "",
                    "## Reader boundary",
                    "This view shows the system's own account and engine measurements only.",
                ]
            )
        return "\n".join(lines)


class HelpScreen(Static):
    """Small built-in help overlay."""

    def __init__(self) -> None:
        super().__init__(
            "[b]reasonsmith tui[/b]\n\n"
            "j/k  move through requirements\n"
            "a    cycle audience projection\n"
            "r    refresh the report view\n"
            "q    quit\n\n"
            "The evidence graph never upgrades a verdict or hides LIMITS.\n\n"
            "Press escape to close.",
            id="help-screen",
        )

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.remove()


def _json(value: object) -> str:
    import json

    return json.dumps(value, indent=2, default=str)
