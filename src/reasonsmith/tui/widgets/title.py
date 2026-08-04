"""Title strip for the active requirement."""

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.widgets import Static

VERDICT_STYLES = {
    "proved": "green",
    "probed": "cyan",
    "observed": "blue",
    "violated": "red",
    "inconclusive": "yellow",
    "not_evaluated": "grey",
    "unattainable": "magenta",
    "not_applicable": "dim",
    "satisfied": "green",
}


class TitleBar(Static):
    """Live title bar that names the system, pack, audience and currently selected row."""

    system_name: reactive[str] = reactive("")
    pack: reactive[str] = reactive("")
    audience: reactive[str] = reactive("")
    selected: reactive[dict[str, Any] | None] = reactive(None)

    def watch_selected(self, _: Any) -> None:
        self.refresh()

    def watch_audience(self, _: Any) -> None:
        self.refresh()

    def watch_pack(self, _: Any) -> None:
        self.refresh()

    def render(self) -> str:
        row = self.selected
        if row is None:
            return (
                f"[b]{self.system_name}[/b] · pack [cyan]{self.pack}[/cyan] · "
                f"audience [cyan]{self.audience}[/cyan] · no selection"
            )

        verdict = str(row.get("verdict", ""))
        strength = str(row.get("strength", ""))
        binding = bool(row.get("binding", False))
        rid = str(row.get("id", ""))
        verdict_style = VERDICT_STYLES.get(verdict, "white")
        binding_style = "green" if binding else "red"
        binding_label = "yes" if binding else "no"
        line_one = (
            f"[b]{self.system_name}[/b] · pack [cyan]{self.pack}[/cyan] · "
            f"audience [cyan]{self.audience}[/cyan]"
        )
        line_two = (
            f"  viewing [b]{rid}[/b]   "
            f"[{verdict_style}]● {verdict.upper()}[/]   "
            f"strength [b]{strength}[/]   "
            f"binding [{binding_style}]{binding_label}[/]"
        )
        return f"{line_one}\n{line_two}"
