"""Demo-loop mode caption."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

CAPTIONS: dict[str, str] = {
    "auditor": "Auditor view: every requirement, every signal, every limit.",
    "developer": "Developer view: spec formulas, required signals, no statute.",
    "deployer": "Deployer view: provenance + counts only — no solver detail.",
    "regulator": "Regulator view: provenance + findings + limits — no signals.",
    "affected-individual": "Affected-individual view: only the system's own account.",
}


class SystemCaption(Static):
    """Caption line under the title that animates during the demo loop."""

    audience: reactive[str] = reactive("auditor")
    demo_running: reactive[bool] = reactive(False)

    def watch_demo_running(self, _: bool) -> None:
        self.refresh()

    def watch_audience(self, _: str) -> None:
        self.refresh()

    def render(self) -> str:
        mode = "[b][reverse] DEMO LOOP ENGAGED [/][/b]" if self.demo_running else "[b]READY[/b]"
        return f"{mode}   ·   {CAPTIONS.get(self.audience, self.audience)}"
