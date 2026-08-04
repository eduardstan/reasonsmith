"""Footer that surfaces the report LIMITS string at all times."""

from __future__ import annotations

from textual.widgets import Static


class LimitsFooter(Static):
    """A footer block that always quotes the report limits in full."""

    def __init__(self, limits: str) -> None:
        super().__init__(id="limits-footer")
        self._limits = limits

    def render(self) -> str:
        return f"[b][LIMITS][/b]  {self._limits}"
