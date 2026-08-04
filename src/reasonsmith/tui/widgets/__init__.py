"""Textual widgets exported by the reasonsmith TUI."""

from reasonsmith.tui.widgets.audience_tabs import AudienceTabs
from reasonsmith.tui.widgets.caption import SystemCaption
from reasonsmith.tui.widgets.counters import VERDICT_COLORS, CounterBar
from reasonsmith.tui.widgets.insights import InsightsBar
from reasonsmith.tui.widgets.limits import LimitsFooter
from reasonsmith.tui.widgets.sparkline import Sparkline
from reasonsmith.tui.widgets.title import TitleBar
from reasonsmith.tui.widgets.verdict_badge import VerdictBadge

__all__ = [
    "AudienceTabs",
    "CounterBar",
    "InsightsBar",
    "LimitsFooter",
    "Sparkline",
    "SystemCaption",
    "TitleBar",
    "VERDICT_COLORS",
    "VerdictBadge",
]
