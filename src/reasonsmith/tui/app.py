"""Textual application for exploring a conformance report."""

from __future__ import annotations

import json
import time
from typing import Any, Iterable

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


SPARK = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")


class ReasonsmithApp(App[None]):
    """A keyboard-first report explorer with an evidence graph view."""

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
    AUDIENCES = ("auditor", "developer", "deployer", "regulator", "affected-individual")
    PACKS = ("ecoa", "gdpr", "eu_ai_act", "gpai", "table7")

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
        self._last_update = time.monotonic()

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
            Static(self._audience_tabs(), id="audience-tabs"),
            Static(self._title_line(), id="title-line"),
            Static(self._counters(), id="counters"),
            Static(self._system_caption(), id="system-caption"),
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
        yield Static(self._limits_widget(), id="limits")
        yield Static(self._insights(), id="insights")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_table()
        self.set_interval(0.4, self._tick_clock)
        self.set_interval(2.5, self._tick_insights)

    def _tick_clock(self) -> None:
        if self.demo_running:
            self.query_one("#counters", Static).update(self._counters())

    def _tick_insights(self) -> None:
        self.query_one("#insights", Static).update(self._insights())

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
            table.add_row(
                row["verdict"].upper(),
                row["strength"],
                row["id"][:48],
                row["source"][:24],
                _sparkline_for(row),
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
        self.query_one("#title-line", Static).update(self._title_line())
        self.query_one("#detail", Markdown).update(self._render_detail())
        self.query_one("#evidence", Markdown).update(self._render_evidence())
        self.query_one("#raw", Markdown).update(self._render_raw())
        self.query_one("#counters", Static).update(self._counters())

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
        self.query_one("#title-line", Static).update(self._title_line())
        self._flash(f"Pack → {self.pack}")

    def action_cycle_audience(self) -> None:
        self.audience_index = (self.audience_index + 1) % len(self.AUDIENCES)
        self.query_one("#audience-tabs", Static).update(self._audience_tabs())
        self._refresh_panes()
        self._flash(f"Audience → {self.audience}")

    def action_refresh_view(self) -> None:
        self._refresh_panes()
        self._flash("Refreshed")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_demo(self) -> None:
        self.demo_running = not self.demo_running
        self.query_one("#system-caption", Static).update(self._system_caption())

    def action_close_overlay(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()

    def _flash(self, message: str) -> None:
        self.notify(message, title="reasonsmith tui")

    def _flash_class(self) -> str:
        return "flash-on" if (time.monotonic() - self._last_update) < 0.8 else "flash-off"

    def _audience_tabs(self) -> str:
        active = self.audience
        rendered: list[str] = []
        for name in self.AUDIENCES:
            style = "tab-active" if name == active else "tab-idle"
            rendered.append(f"[{style}] {name} [/]")
        return "  ".join(rendered)

    def _title_line(self) -> str:
        row = self.selected
        if row is None:
            return f"[b]{self.report.system_name}[/b] · [cyan]{self.pack}[/cyan] · no selection"
        verdict_style = self._verdict_style(row["verdict"])
        return (
            f"[b]{self.report.system_name}[/b]  ·  pack [cyan]{self.pack}[/cyan]  ·  "
            f"audience [cyan]{self.audience}[/cyan]\n"
            f"  viewing [b]{row['id']}[/b]   "
            f"[{verdict_style}]● {row['verdict'].upper()}[/]   "
            f"strength [b]{row['strength']}[/]   "
            f"binding {'[green]yes[/]' if row['binding'] else '[red]no[/]'}"
        )

    def _system_caption(self) -> str:
        mode = "DEMO LOOP ENGAGED" if self.demo_running else "READY"
        scope = self._audience_caption(self.audience)
        return f"[b]{mode}[/b]   ·   {scope}"

    def _audience_caption(self, audience: str) -> str:
        captions = {
            "auditor": "Auditor view: every requirement, every signal, every limit.",
            "developer": "Developer view: spec formulas, required signals, no statute.",
            "deployer": "Deployer view: provenance + counts only — no solver detail.",
            "regulator": "Regulator view: provenance + findings + limits — no signals.",
            "affected-individual": "Affected-individual view: only the system's own account.",
        }
        return captions.get(audience, audience)

    def _counters(self) -> str:
        counts = self.report.counts
        cells: list[str] = []
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
            cells.append(f"[{color}]●[/] [b]{counts[key]}[/] [dim]{key.replace('_', ' ')}[/]")
        return "   ".join(cells)

    def _render_detail(self) -> str:
        row = self.selected
        if row is None:
            return "No requirements were reported."
        verdict_style = self._verdict_style(row["verdict"])
        lines = [
            f"# {row['id']}",
            f"**Verdict:** [{verdict_style}]{row['verdict']}[/]   "
            f"**Strength:** [b]{row['strength']}[/]   "
            f"**Binding:** {'yes' if row['binding'] else 'no'}",
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
        lines.extend(
            [
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
        cells = [
            ("verdict", row["verdict"]),
            ("strength", row["strength"]),
            ("binding", str(row["binding"])),
            ("audience", self.audience),
        ]
        lines = ["# Evidence graph", "", "| field | value |", "| --- | --- |"]
        for field, value in cells:
            lines.append(f"| {field} | {value} |")
        spark = _sparkline_for(row)
        lines.extend(
            [
                "",
                "## Sparkline",
                f"`{spark}`",
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

    def _limits_widget(self) -> str:
        return f"[LIMITS]  {self.report.limits}"

    def _insights(self) -> str:
        counts = self.report.counts
        total = sum(int(counts[k]) for k in counts)
        if total == 0:
            return "No findings to summarize."
        sample = self.selected
        highlight = sample["id"] if sample else "—"
        return (
            f"[b]Now:[/b] {highlight} · "
            f"[b]Hero counts:[/b] proved {counts['proved']} · "
            f"observed {counts['observed']} · "
            f"violated {counts['violated']} · "
            f"unattainable {counts['unattainable']}"
        )

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
        }.get(verdict, "white")


def _sparkline_for(row: dict[str, Any]) -> str:
    values: list[float] = []
    for key in ("proved", "probed", "observed", "violated"):
        if key in row:
            values.append(float(row.get(key, 0) or 0))
    if isinstance(row.get("details"), dict):
        for value in row["details"].values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
    if not values:
        return _spark_block("+")
    lo, hi = min(values), max(values)
    if hi == lo:
        return _spark_block("■")
    bars: list[str] = []
    for v in values:
        idx = int((v - lo) / (hi - lo) * (len(SPARK) - 1))
        bars.append(SPARK[idx])
    return "".join(bars)


def _spark_block(chars: Iterable[str]) -> str:
    return "".join(list(chars)[:8])


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
