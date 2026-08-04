"""Compact sparkline widget for requirement evidence."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

GLYPHS: tuple[str, ...] = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")


class Sparkline(Static):
    """Single-row sparkline glyphs."""

    def __init__(self, row: dict[str, Any], width: int = 8) -> None:
        super().__init__(id="sparkline")
        self.row = row
        self.width = width

    def render(self) -> str:
        values = self._values()
        if not values:
            return "[dim]+[/]"
        lo, hi = min(values), max(values)
        if hi == lo:
            return "".join("■" for _ in range(min(len(values), self.width)))
        chars: list[str] = []
        for value in values[: self.width]:
            ratio = (value - lo) / (hi - lo)
            level = int(ratio * (len(GLYPHS) - 1))
            chars.append(GLYPHS[level])
        if len(values) > self.width:
            chars.append("…")
        return "".join(chars)

    def _values(self) -> list[float]:
        values: list[float] = []
        for key in ("proved", "probed", "observed", "violated"):
            if key in self.row:
                values.append(float(self.row.get(key, 0) or 0))
        details = self.row.get("details")
        if isinstance(details, dict):
            for value in details.values():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    values.append(float(value))
        return values
