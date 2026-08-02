"""Tests for the statute drift check (src/reasonsmith/drift.py).

The recorded fixtures under `tests/fixtures/drift/` are byte-faithful slices of the official
documents fetched from the endpoints recorded in `docs/legal-sources.md` (see the run book kept in
the drift check's commit message): the AI Act Article 12, 13, 53 and 55 divisions, GDPR Article 22
(consolidated) and Recital 71 (original), and the whole 12 CFR 1002.9 section. Tests substitute a
fixture fetcher for the network, so the suite never touches the live sources.
"""

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest

import reasonsmith.drift as drift
from reasonsmith.drift import (
    SOURCES,
    STATUTORY_PACKS,
    DriftFetchError,
    DriftReport,
    DriftResult,
    check_statute_drift,
    classify,
    extract_passage,
    normalize_whitespace,
)
from reasonsmith.spec import load_pack

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "drift"

FIXTURE_BY_KEY = {
    "ai_act": "eu_ai_act_art12_13_53_55.xhtml",
    "gdpr_consolidated": "gdpr_consolidated_art22.xhtml",
    "gdpr_original": "gdpr_original_rct71.xhtml",
    "ecoa": "ecoa_1002_9.xml",
}

STATUTORY_REQUIREMENT_COUNT = sum(len(load_pack(name).requirements) for name in STATUTORY_PACKS)


def fixture_fetcher(source: drift.SourceDocument) -> str:
    return (FIXTURE_DIR / FIXTURE_BY_KEY[source.key]).read_text(encoding="utf-8")


def _minimal_pack(tmp_path, *, clause: str, verbatim: str) -> str:
    pack_file = tmp_path / "drift_test.toml"
    pack_file.write_text(
        f"""[pack]
id = "drift_test"
title = "Drift check test pack"
description = "Temporary pack used to exercise the drift checker off the recorded fixtures."

[source]
document = "Test"
url = "http://example.invalid/"

[[requirement]]
id = "test_req_1"
source_document = "Test"
article_clause = {clause!r}
verbatim_text = {verbatim!r}
stakeholder = "regulator"
formalism = "record"
spec = "present(artifact_logs_event_log)"
rationale = "Why this duty exists."
requires = ["artifact_logs_event_log"]
binding = true
scope = ""
domains = []
""",
        encoding="utf-8",
    )
    return str(pack_file)


class TestNormalize:
    def test_collapses_nbsp_and_newlines_to_single_spaces(self):
        assert normalize_whitespace("a\xa0\xa0\n   b\t\tc") == "a b c"

    def test_changes_nothing_else(self):
        assert normalize_whitespace("a  'b'  c.  -d;") == "a 'b' c. -d;"

    def test_empty_text_stays_empty(self):
        assert normalize_whitespace("") == ""
        assert normalize_whitespace(" \t ") == ""


class TestClassify:
    def test_whitespace_wrapping_is_still_a_match(self):
        quote = "automatic recording of events (logs) over the lifetime of the system."
        passage = (
            "1.\xa0\xa0\xa0High-risk AI systems shall technically allow for the automatic\n"
            "recording of events (logs) over the lifetime of the system."
        )
        assert classify(quote, passage) == "match"

    def test_edited_word_is_a_differ(self):
        quote = "automatic recording of events (logs) over the lifetime of the system."
        passage = (
            "High-risk AI systems shall technically allow for the manual recording of events "
            "over the lifetime of the system."
        )
        assert classify(quote, passage) == "differ"

    def test_case_change_is_a_differ(self):
        passage = "High-risk AI systems Shall technically allow"
        assert classify("shall technically allow", passage) == "differ"

    def test_quote_is_a_substring_not_the_whole_passage(self):
        passage = "many words before and after logging capabilities shall enable here"
        assert classify("logging capabilities shall enable", passage) == "match"


class TestExtractPassage:
    def test_finds_the_named_division(self):
        source = (FIXTURE_DIR / FIXTURE_BY_KEY["ai_act"]).read_text(encoding="utf-8")
        paragraph = extract_passage(source, selector="012.001")
        assert paragraph == (
            "1. High-risk AI systems shall technically allow for the automatic recording of "
            "events (logs) over the lifetime of the system."
        )

    def test_returns_none_for_a_missing_selector(self):
        source = (FIXTURE_DIR / FIXTURE_BY_KEY["ai_act"]).read_text(encoding="utf-8")
        assert extract_passage(source, selector="999.999") is None

    def test_ecoa_whole_document_is_the_passage(self):
        source = (FIXTURE_DIR / FIXTURE_BY_KEY["ecoa"]).read_text(encoding="utf-8")
        passage = extract_passage(source, selector=None)
        assert passage is not None
        assert "A creditor shall notify an applicant of action taken within: (i) 30 days" in passage


class TestFetchSource:
    def test_ecfr_fetch_resolves_the_latest_official_issue_date(self, monkeypatch):
        urls: list[str] = []
        responses = iter(
            [
                BytesIO(b'{"meta":{"latest_issue_date":"2026-07-27"}}'),
                BytesIO((FIXTURE_DIR / FIXTURE_BY_KEY["ecoa"]).read_bytes()),
            ]
        )

        def fake_urlopen(request, timeout):
            urls.append(request.full_url)
            return next(responses)

        monkeypatch.setattr(drift.urllib.request, "urlopen", fake_urlopen)
        source = next(source for source in SOURCES if source.key == "ecoa")

        passage = drift.fetch_source(source)

        assert urls == [
            drift.ECFR_VERSIONS_URL,
            "https://www.ecfr.gov/api/versioner/v1/full/2026-07-27/"
            "title-12.xml?part=1002&section=1002.9",
        ]
        assert "A creditor shall notify an applicant of action taken within:" in passage


class TestCheckStatuteDrift:
    def test_all_statutory_quotes_match_the_recorded_sources(self):
        report = check_statute_drift(fixture_fetcher)
        assert report.counts == {
            "match": STATUTORY_REQUIREMENT_COUNT,
            "differ": 0,
            "could-not-verify": 0,
        }
        assert not report.has_drift

    def test_a_modified_quote_is_a_differ_naming_both_strings(self, tmp_path):
        pack = _minimal_pack(
            tmp_path,
            clause="Article 12(1)",
            verbatim=(
                "High-risk AI systems shall technically allow for the MANUAL recording of events "
                "(logs) over the lifetime of the system."
            ),
        )
        report = check_statute_drift(fixture_fetcher, packs=[pack])
        assert report.counts["differ"] == 1
        finding = report.results[0]
        assert finding.status == "differ"
        assert finding.requirement_id == "test_req_1"
        assert finding.article_clause == "Article 12(1)"
        assert finding.source_url.startswith("http")
        assert "MANUAL recording" in finding.quote
        assert "automatic recording" in finding.passage

    def test_unreachable_source_is_could_not_verify_not_a_pass(self, tmp_path):
        def broken_fetcher(source: drift.SourceDocument) -> str:
            raise DriftFetchError(f"boom for {source.key}")

        pack = _minimal_pack(tmp_path, clause="Article 12(1)", verbatim="whatever")
        report = check_statute_drift(broken_fetcher, packs=[pack])
        assert report.counts == {"match": 0, "differ": 0, "could-not-verify": 1}
        assert report.has_drift
        assert report.results[0].note == "boom for ai_act"

    def test_a_restructured_source_is_could_not_verify(self, tmp_path):
        def empty_fetcher(source: drift.SourceDocument) -> str:
            return '<html><body><div id="999.999">nothing here</div></body></html>'

        pack = _minimal_pack(tmp_path, clause="Article 12(1)", verbatim="whatever")
        report = check_statute_drift(empty_fetcher, packs=[pack])
        assert report.counts == {"match": 0, "differ": 0, "could-not-verify": 1}
        assert "selector '012.001' not found" in report.results[0].note

    def test_an_unregistered_clause_is_refused(self, tmp_path):
        pack = _minimal_pack(tmp_path, clause="Article 99(9)", verbatim="whatever")
        with pytest.raises(ValueError, match="Article 99\\(9\\)"):
            check_statute_drift(fixture_fetcher, packs=[pack])

    def test_a_document_is_fetched_once_for_several_provisions(self):
        calls: list[str] = []

        def counting_fetcher(source: drift.SourceDocument) -> str:
            calls.append(source.key)
            return fixture_fetcher(source)

        report = check_statute_drift(counting_fetcher)
        assert not report.has_drift
        assert calls == ["ai_act", "gdpr_consolidated", "gdpr_original", "ecoa"]


class TestRegistry:
    def test_every_source_url_is_recorded_in_legal_sources(self):
        legal = (Path(__file__).resolve().parents[1] / "docs" / "legal-sources.md").read_text(
            encoding="utf-8"
        )
        for source in SOURCES:
            assert f"`{source.url}`" in legal, (
                f"source {source.key!r} URL is not recorded in docs/legal-sources.md: {source.url}"
            )

    def test_every_provision_resolves_to_a_registered_source(self):
        for clause, (source_key, _selector) in drift.PROVISIONS.items():
            assert source_key in {s.key for s in SOURCES}
            assert isinstance(clause, str) and clause

    def test_statutory_packs_exclude_table7(self):
        assert "table7" not in STATUTORY_PACKS


class TestWorkflow:
    def test_drift_issue_creation_is_serialized_and_uses_the_exact_title(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "statute-drift.yml"
        ).read_text(encoding="utf-8")
        assert "concurrency:\n  group: statute-drift\n  cancel-in-progress: false" in workflow
        assert 'if issue["title"] == title' in workflow


class TestReport:
    def test_render_and_json_round_trip(self, tmp_path):
        now = datetime(2026, 8, 1, 3, 0, tzinfo=timezone.utc)
        results = (
            DriftResult("gdpr", "r1", "Article 22(1)", "http://x/", "match", "q", ""),
            DriftResult("gdpr", "r2", "Article 22(3)", "http://x/", "differ", "old", "new"),
            DriftResult(
                "gdpr", "r3", "Recital 71", "http://x/", "could-not-verify", "q", "", "network"
            ),
        )
        report = DriftReport(results, now)
        text = report.render_text()
        assert "differ: 1  could-not-verify: 1" in text
        data = report.to_dict()
        assert data["has_drift"] is True
        assert len(data["findings"]) == 2
        out = tmp_path / "drift.json"
        out.write_text(json.dumps(data), encoding="utf-8")
        assert json.loads(out.read_text(encoding="utf-8")) == data

    def test_main_exit_codes_and_report_file(self, monkeypatch, tmp_path):
        match_report = DriftReport(
            (DriftResult("gdpr", "r1", "Article 22(1)", "http://x/", "match", "q", ""),),
            datetime(2026, 8, 1, 3, 0),
        )
        monkeypatch.setattr(drift, "check_statute_drift", lambda fetcher: match_report)
        assert drift.main([]) == 0

        drift_report = DriftReport(
            (DriftResult("gdpr", "r1", "Article 22(1)", "http://x/", "differ", "q", "p"),),
            datetime(2026, 8, 1, 3, 0),
        )
        monkeypatch.setattr(drift, "check_statute_drift", lambda fetcher: drift_report)
        out = tmp_path / "drift-report.json"
        assert drift.main(["--report", str(out)]) == 1
        assert json.loads(out.read_text(encoding="utf-8"))["has_drift"] is True

    def test_main_reports_invalid_utf8_as_could_not_verify(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            drift.urllib.request,
            "urlopen",
            lambda request, timeout: BytesIO(b"\xff"),
        )
        out = tmp_path / "drift-report.json"

        assert drift.main(["--report", str(out)]) == 1

        report = json.loads(out.read_text(encoding="utf-8"))
        assert report["counts"] == {
            "match": 0,
            "differ": 0,
            "could-not-verify": STATUTORY_REQUIREMENT_COUNT,
        }
        assert any("could not decode" in finding["note"] for finding in report["findings"])
