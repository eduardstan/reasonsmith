"""Component-level unit tests for the reasonsmith TUI widgets."""

from __future__ import annotations

from reasonsmith.tui.widgets import (
    AudienceTabs,
    CounterBar,
    InsightsBar,
    LimitsFooter,
    Sparkline,
    TitleBar,
    VerdictBadge,
)


class _StubReport:
    system_name = "StubSystem"

    def __init__(self, limits: str = "LIMITS TEST", counts: dict[str, int] | None = None):
        self.limits = limits
        self.counts = counts or {
            "proved": 0,
            "probed": 0,
            "observed": 1,
            "violated": 2,
            "inconclusive": 0,
            "not_evaluated": 1,
            "unattainable": 0,
            "not_applicable": 0,
        }


def test_verdict_badge_renders_color_label() -> None:
    badge = VerdictBadge("violated")
    assert "VIOLATED" in badge.render()
    assert "✗" in badge.render()


def test_sparkline_handles_missing_or_single_value() -> None:
    assert Sparkline({}).render() == "[dim]+[/]"
    single = Sparkline({"details": {"a": 1, "b": 1, "c": 1}}).render()
    assert single  # should produce some glyphs


def test_audience_tabs_highlights_current() -> None:
    tabs = AudienceTabs()
    tabs.current = "auditor"
    rendered = tabs.render()
    assert "tab-active" in rendered
    assert "auditor" in rendered


def test_counter_bar_contains_all_categories() -> None:
    bar = CounterBar(_StubReport())  # type: ignore[arg-type]
    rendered = bar.render()
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
        assert key.replace("_", " ") in rendered


def test_title_bar_with_no_selection() -> None:
    bar = TitleBar()
    bar.system_name = "Stub"
    bar.pack = "ecoa"
    bar.audience = "auditor"
    bar.selected = None
    assert "no selection" in bar.render()


def test_title_bar_highlights_active_row() -> None:
    bar = TitleBar()
    bar.system_name = "Stub"
    bar.pack = "ecoa"
    bar.audience = "auditor"
    bar.selected = {
        "id": "req-1",
        "verdict": "observed",
        "strength": "observed",
        "binding": True,
    }
    rendered = bar.render()
    assert "req-1" in rendered
    assert "OBSERVED" in rendered
    assert "yes" in rendered


def test_limits_footer_carries_full_text() -> None:
    assert "LIMITS TEST" in LimitsFooter("LIMITS TEST").render()


def test_insights_bar_uses_counts_and_id() -> None:
    bar = InsightsBar()
    bar.report = _StubReport()  # type: ignore[arg-type]
    bar.selected_id = "req-9"
    rendered = bar.render()
    assert "req-9" in rendered
    assert "proved 0" in rendered
