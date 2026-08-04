from __future__ import annotations

from textual.app import App

from reasonsmith.report import ConformanceReport
from reasonsmith.tui.app import ReasonsmithApp
from reasonsmith.tui.data import TuiOptions


def test_app_compose_contains_limits() -> None:
    report = ConformanceReport("demo", "system", (), limits="LIMITS TEST")
    options = TuiOptions("demo", None, None, "system", None, (), "auditor")
    app = ReasonsmithApp(report, options)
    assert app.report.limits == "LIMITS TEST"
    assert isinstance(app, App)
    assert app.CSS_PATH == "styles.tcss"


def test_report_rows_preserve_non_pass_categories() -> None:
    from reasonsmith.report import RequirementResult
    from reasonsmith.tui.data import result_rows
    from reasonsmith.verdict import Verdict

    report = ConformanceReport(
        "demo",
        "system",
        (
            RequirementResult(
                "req",
                "source",
                Verdict.INCONCLUSIVE,
                None,
                ("signal",),
            ),
        ),
    )
    row = result_rows(report)[0]
    assert row["verdict"] == "inconclusive"
    assert row["strength"] == "not evaluated"
    assert row["missing"] == ()
