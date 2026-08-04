"""Textual application for exploring a conformance report."""

from __future__ import annotations

import json
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from reasonsmith.report import ConformanceReport
from reasonsmith.tui.data import TuiOptions, result_rows
from reasonsmith.tui.widgets import (
    AudienceTabs,
    CounterBar,
    InsightsBar,
    LimitsFooter,
    Sparkline,
    SystemCaption,
    TitleBar,
    VerdictBadge,
)

__all__ = ["ReasonsmithApp", "HelpScreen"]


class ReasonsmithApp(App[None]):
    """A keyboard-first report explorer composed of focused widgets."""

    TITLE = "reasonsmith · evidence explorer"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("/", "focus_filter", "Search"),
        Binding("a", "cycle_audience", "Audience"),
        Binding("j", "next_row", "Next"),
        Binding("k", "previous_row", "Previous"),
        Binding("g", "first_row", "Top"),
        Binding("G", "last_row", "Bottom"),
        Binding("p", "cycle_pack", "Pack"),
        Binding("e", "toggle_demo", "Demo"),
        Binding("r", "refresh_view", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("escape", "close_overlay", "Close"),
    ]
    AUDIENCES: tuple[str, ...] = (
        "auditor",
        "developer",
        "deployer",
        "regulator",
        "affected-individual",
    )
    PACKS: tuple[str, ...] = ("ecoa", "gdpr", "eu_ai_act", "gpai", "table7")

    audience_index: reactive[int] = reactive(0)
    pack_index: reactive[int] = reactive(0)
    filter_text: reactive[str] = reactive("")
    demo_running: reactive[bool] = reactive(False)

    def __init__(self, report: ConformanceReport, options: TuiOptions):
        super().__init__()
        self.report = report
        self.options = options
        try:
            self.audience_index = self.AUDIENCES.index(options.audience)
        except ValueError:
            self.audience_index = 0
        try:
            self.pack_index = self.PACKS.index(options.pack)
        except ValueError:
            self.pack_index = 0
        self.rows: list[dict[str, Any]] = list(result_rows(report))
        self._selected_index = 0

    @property
    def audience(self) -> str:
        return self.AUDIENCES[self.audience_index]

    @property
    def pack(self) -> str:
        return self.PACKS[self.pack_index]

    @property
    def selected(self) -> dict[str, Any] | None:
        if not self.rows:
            return None
        return self.rows[min(self._selected_index, len(self.rows) - 1)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            AudienceTabs(id="audience-tabs"),
            TitleBar(id="title-bar"),
            CounterBar(self.report),
            SystemCaption(id="system-caption"),
            id="hero",
        )
        yield Input(placeholder="Filter requirements by id or source — /", id="filter")
        with Horizontal(id="main-pane"):
            with Vertical(id="requirements-pane"):
                yield Label("REQUIREMENTS", classes="pane-title")
                yield DataTable(id="requirements", cursor_type="row", zebra_stripes=True)
            with TabbedContent(id="evidence-tabs"):
                with TabPane("Detail", id="tab-detail"):
                    yield Markdown(self._render_detail(), id="detail")
                with TabPane("Evidence", id="tab-evidence"):
                    yield Markdown(self._render_evidence(), id="evidence")
                with TabPane("Raw", id="tab-raw"):
                    yield Markdown(self._render_raw(), id="raw")
        yield LimitsFooter(self.report.limits)
        yield InsightsBar(id="insights-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._wire_components()
        self._refresh_table()
        self.set_interval(2.5, self._tick_insights)

    def _wire_components(self) -> None:
        tabs = self.query_one("#audience-tabs", AudienceTabs)
        tabs.current = self.audience

        title = self.query_one("#title-bar", TitleBar)
        title.system_name = self.report.system_name
        title.pack = self.pack
        title.audience = self.audience
        title.selected = self.selected

        counter = self.query_one("#hero CounterBar")
        del counter

        caption = self.query_one("#system-caption", SystemCaption)
        caption.audience = self.audience

        insights = self.query_one("#insights-bar", InsightsBar)
        insights.report = self.report
        insights.selected_id = self.selected["id"] if self.selected else "—"

    def _tick_insights(self) -> None:
        insights = self.query_one("#insights-bar", InsightsBar)
        insights.selected_id = self.selected["id"] if self.selected else "—"

    def _refresh_table(self) -> None:
        table = self.query_one("#requirements", DataTable)
        table.clear(columns=True)
        table.add_columns("Verdict", "Strength", "Requirement", "Source", "Spark")
        for index, row in enumerate(self.rows):
            if (
                self.filter_text
                and self.filter_text.lower() not in row["id"].lower()
                and self.filter_text.lower() not in row["source"].lower()
            ):
                continue
            spark_widget = Sparkline(row)
            table.add_row(
                row["verdict"].upper(),
                row["strength"],
                row["id"][:48],
                row["source"][:24],
                spark_widget.render(),
                key=str(index),
            )
        if self.rows:
            target = min(self._selected_index, max(len(table.rows) - 1, 0))
            table.move_cursor(row=target)

    @on(DataTable.RowHighlighted)
    def _on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        self._selected_index = int(str(event.row_key.value))
        self._refresh_panes()

    def _refresh_panes(self) -> None:
        title = self.query_one("#title-bar", TitleBar)
        title.selected = self.selected

        self.query_one("#detail", Markdown).update(self._render_detail())
        self.query_one("#evidence", Markdown).update(self._render_evidence())
        self.query_one("#raw", Markdown).update(self._render_raw())

        counter = self.query_one("#hero CounterBar")
        counter.refresh()

        insights = self.query_one("#insights-bar", InsightsBar)
        insights.selected_id = self.selected["id"] if self.selected else "—"

    @on(Input.Changed, "#filter")
    def _on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value.strip()
        self._refresh_table()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_toggle_filter(self) -> None:
        widget = self.query_one("#filter", Input)
        widget.display = not widget.display
        if widget.display:
            widget.focus()
        else:
            self.set_focus(None)

    def action_next_row(self) -> None:
        self.query_one("#requirements", DataTable).action_cursor_down()

    def action_previous_row(self) -> None:
        self.query_one("#requirements", DataTable).action_cursor_up()

    def action_first_row(self) -> None:
        self.query_one("#requirements", DataTable).move_cursor(row=0)

    def action_last_row(self) -> None:
        table = self.query_one("#requirements", DataTable)
        last = max(table.row_count - 1, 0)
        table.move_cursor(row=last)

    def action_cycle_pack(self) -> None:
        self.pack_index = (self.pack_index + 1) % len(self.PACKS)
        self._refresh_after_pack_change()
        self._flash(f"Pack → {self.pack}")

    def action_cycle_audience(self) -> None:
        self.audience_index = (self.audience_index + 1) % len(self.AUDIENCES)
        self._refresh_after_audience_change()
        self._flash(f"Audience → {self.audience}")

    def action_refresh_view(self) -> None:
        self._refresh_panes()
        self._flash("Refreshed")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_demo(self) -> None:
        self.demo_running = not self.demo_running
        caption = self.query_one("#system-caption", SystemCaption)
        caption.demo_running = self.demo_running

    def action_close_overlay(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()

    def _refresh_after_pack_change(self) -> None:
        title = self.query_one("#title-bar", TitleBar)
        title.pack = self.pack

    def _refresh_after_audience_change(self) -> None:
        tabs = self.query_one("#audience-tabs", AudienceTabs)
        tabs.current = self.audience
        title = self.query_one("#title-bar", TitleBar)
        title.audience = self.audience
        caption = self.query_one("#system-caption", SystemCaption)
        caption.audience = self.audience
        self._refresh_panes()

    def _flash(self, message: str) -> None:
        self.notify(message, title="reasonsmith tui")

    def _verdict_style(self, verdict: str) -> str:
        return {
            "proved": "green",
            "probed": "cyan",
            "observed": "blue",
            "violated": "red",
            "inconclusive": "yellow",
            "not_evaluated": "grey",
            "unattainable": "magenta",
            "not_applicable": "dim",
            "satisfied": "green",
        }.get(verdict, "white")

    def _audience_caption(self, audience: str) -> str:
        captions = {
            "auditor": "Auditor view: every requirement, every signal, every limit.",
            "developer": "Developer view: spec formulas, required signals, no statute.",
            "deployer": "Deployer view: provenance + counts only — no solver detail.",
            "regulator": "Regulator view: provenance + findings + limits — no signals.",
            "affected-individual": "Affected-individual view: only the system's own account.",
        }
        return captions.get(audience, audience)

    def _render_detail(self) -> str:
        row = self.selected
        if row is None:
            return "No requirements were reported."
        verdict = str(row.get("verdict", ""))
        strength = str(row.get("strength", ""))
        binding = bool(row.get("binding", False))
        verdict_style = self._verdict_style(verdict)
        lines = [
            f"# {row['id']}",
            f"**Verdict:** [{verdict_style}]{verdict}[/]   "
            f"**Strength:** [b]{strength}[/]   "
            f"**Binding:** {'yes' if binding else 'no'}",
            f"**Source:** {row.get('source', '')}",
            "",
            "## Evidence",
            str(row.get("evidence") or "No evidence summary was emitted."),
            "",
            "## Required signals",
            ", ".join(row.get("required") or []) or "None declared",
        ]
        missing = row.get("missing") or []
        if missing:
            lines.extend(["", "## Missing signals", ", ".join(missing)])
        badge = VerdictBadge(verdict).render()
        lines.extend(
            [
                "",
                "## Verdict badge",
                badge,
                "",
                f"## Audience · {self.audience}",
                self._audience_caption(self.audience),
            ]
        )
        return "\n".join(lines)

    def _render_evidence(self) -> str:
        row = self.selected
        if row is None:
            return "No requirements were reported."
        audience = self.audience
        cells = [
            ("verdict", row.get("verdict", "")),
            ("strength", row.get("strength", "")),
            ("binding", str(row.get("binding", False))),
            ("audience", audience),
        ]
        lines = ["# Evidence graph", "", "| field | value |", "| --- | --- |"]
        for field, value in cells:
            lines.append(f"| {field} | {value} |")
        spark_widget = Sparkline(row)
        lines.extend(
            [
                "",
                "## Sparkline widget",
                f"`{spark_widget.render()}`",
                "",
                "## Evidence badge",
                VerdictBadge(str(row.get("verdict", ""))).render(),
                "",
                "## Detail JSON",
                "```json",
                json.dumps(row, indent=2, default=str),
                "```",
            ]
        )
        return "\n".join(lines)

    def _render_raw(self) -> str:
        lines = ["# Raw report payload", ""]
        lines.append("```json")
        lines.append(
            json.dumps(
                {
                    "system": self.report.system_name,
                    "pack": self.pack,
                    "audience": self.audience,
                    "headline": self.report.headline,
                    "counts": self.report.counts,
                    "limits": self.report.limits,
                    "rows": self.rows,
                },
                indent=2,
                default=str,
            )
        )
        lines.append("```")
        return "\n".join(lines)


class HelpScreen(Static):
    """Full overlay showing every binding."""

    BINDINGS = [
        Binding("escape,q,?", "app.pop_screen", "Close"),
    ]

    def __init__(self) -> None:
        text = (
            "[b]reasonsmith tui[/b] · interactive evidence explorer\n\n"
            "[b]Navigation[/b]\n"
            "  j / k      next / previous requirement\n"
            "  g / G      first / last requirement\n"
            "  /          jump into the filter input\n"
            "  f          toggle the filter input\n\n"
            "[b]Lens[/b]\n"
            "  a          cycle audience projection\n"
            "  p          cycle regulation pack\n\n"
            "[b]Control[/b]\n"
            "  e          toggle demo loop (animated hero counter)\n"
            "  r          refresh detail panels\n"
            "  ?          open this help\n"
            "  q / esc    quit (or close the help overlay)\n\n"
            "The viewer never upgrades a verdict or omits LIMITS.\n"
        )
        super().__init__(text, id="help-screen")
