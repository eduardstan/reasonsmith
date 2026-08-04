"""Audience ribbon tab strip."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static


class AudienceTabs(Static):
    """A pill-style ribbon that exposes all five audiences, highlighting the current one."""

    audiences: tuple[str, ...] = (
        "auditor",
        "developer",
        "deployer",
        "regulator",
        "affected-individual",
    )
    current: reactive[str] = reactive("auditor")

    def watch_current(self, new_value: str) -> None:
        self.refresh()

    def render(self) -> str:
        chips: list[str] = []
        for name in self.audiences:
            label = name.replace("-", " ")
            style = "tab-active" if name == self.current else "tab-idle"
            chips.append(f"[{style}] {label} [/]")
        return "   ".join(chips)
