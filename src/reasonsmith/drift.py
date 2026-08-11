"""Statute drift check: re-verify pack quotes against the live official sources.

What this module is for:
  Re-fetches the official statutory documents recorded in `docs/legal-sources.md` and checks every
  `verbatim_text` in the EU AI Act, GDPR and ECOA packs against them character-for-character. The
  check classifies each requirement as `match`, `differ` or `could-not-verify` and never edits a
  pack: a quote that no longer matches the print is reported, not silently fixed.

  The pipeline per requirement is: fetch the recorded source document once per document, extract
  the passage its `article_clause` names, normalize both the quote and the passage, and test the
  quote as a substring of the passage. A drift finding names the pack, the requirement, the clause,
  the source URL and both strings. An unreachable source, or a document that no longer carries the
  registered passage, is `could-not-verify`, never a pass.

What a reader must not break:
  - Only whitespace collapsing is allowed when comparing: `" ".join(text.split())`. The official
    documents wrap lines, indent lettered items and insert NBSPs that only line-preview on a page,
    so runs of whitespace (including U+00A0) collapse to a single space. Everything else --
    spelling, punctuation, Unicode normalization, case -- is compared verbatim, so a real edit to
    the law is reported as `differ`.
    Why this matters: the check exists to catch a statute that moved, and the one thing a printer
    legitimately changes is line wrapping. Collapsing more than whitespace would launder a rewrite.
  - `STATUTORY_PACKS` is exactly the packs whose quotes are checked against the print. `table7` is
    excluded on purpose: its `verbatim_text` is quoted from the review paper, not from an official
    statutory source, so there is no official document to re-fetch for it.
  - `PROVISIONS` maps each `article_clause` to a recorded source document and a passage selector. A
    requirement whose clause has no registry entry is refused, never skipped: an unregistered quote
    cannot be verified and must not look as though it was.
  - A source document is fetched once per run and reused for every provision that points at it, so
    a check of N provisions makes at most as many network calls as there are documents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Literal

from reasonsmith.spec import load_pack

#: The packs whose quotes are verified against official statutory sources. `table7` is deliberately
#: absent: its quotes come from the review paper itself, and no official document re-fetches them.
STATUTORY_PACKS = ("eu_ai_act", "gpai", "gdpr", "ecoa")

#: Elements that carry no text and no end tag even in well-formed XHTML/XML, so the passage
#: extractor must not count them when tracking element nesting depth.
VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

#: Default network guardrails for the live fetch.
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_BYTES = 20 * 1024 * 1024
ECFR_VERSIONS_URL = "https://www.ecfr.gov/api/versioner/v1/versions/title-12.json"


@dataclass(frozen=True)
class SourceDocument:
    """A recorded official statutory source.

    `url` is copied verbatim from `docs/legal-sources.md`; `test_drift.py` holds the registry to
    that file so the two cannot drift apart. `kind` names the format the endpoint serves and tells
    the live fetch whether it must resolve the current version before retrieval.
    """

    key: str
    url: str
    kind: Literal["cellar-xhtml", "ecfr-xml"]


SOURCES = (
    SourceDocument(
        "ai_act",
        "http://publications.europa.eu/resource/cellar/dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.03/DOC_1",
        "cellar-xhtml",
    ),
    SourceDocument(
        "gdpr_consolidated",
        "http://publications.europa.eu/resource/cellar/5f2552c2-cc45-11e6-ad7c-01aa75ed71a1.0022.03/DOC_1",
        "cellar-xhtml",
    ),
    SourceDocument(
        "gdpr_original",
        "http://publications.europa.eu/resource/cellar/3e485e15-11bd-11e6-ba9a-01aa75ed71a1.0006.03/DOC_1",
        "cellar-xhtml",
    ),
    SourceDocument(
        "ecoa",
        "https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?part=1002&section=1002.9",
        "ecfr-xml",
    ),
    SourceDocument(
        "ecoa_general_rules",
        "https://www.ecfr.gov/api/versioner/v1/full/2023-08-29/title-12.xml?part=1002&section=1002.4",
        "ecfr-xml",
    ),
)
SOURCES_BY_KEY = {source.key: source for source in SOURCES}

#: Provision registry: requirement `article_clause` -> (source key, passage selector).
#: For Cellar XHTML the selector is the `id` of the paragraph, article or recital `<div>`; the eCFR
#: response *is* the section it was asked for, so its selector is None (the whole document is
#: the passage). Section 1002.4 is a second eCFR document rather than a selector into the
#: first: the versioner endpoint returns one section per request.
PROVISIONS = {
    "Article 12(1)": ("ai_act", "012.001"),
    "Article 12(2)": ("ai_act", "012.002"),
    "Article 13(1)": ("ai_act", "013.001"),
    "Article 13(2)": ("ai_act", "013.002"),
    # Article 53(1) and 55(1) carry their lettered points inside the paragraph division, so all
    # four points of each share the paragraph's selector and each quote is a substring of it.
    "Article 53(1)(a)": ("ai_act", "053.001"),
    "Article 53(1)(b)": ("ai_act", "053.001"),
    "Article 53(1)(c)": ("ai_act", "053.001"),
    "Article 53(1)(d)": ("ai_act", "053.001"),
    "Article 55(1)(a)": ("ai_act", "055.001"),
    "Article 55(1)(b)": ("ai_act", "055.001"),
    "Article 55(1)(c)": ("ai_act", "055.001"),
    "Article 55(1)(d)": ("ai_act", "055.001"),
    "Article 22(1)": ("gdpr_consolidated", "art_22"),
    "Article 22(3)": ("gdpr_consolidated", "art_22"),
    "Recital 71": ("gdpr_original", "rct_71"),
    "12 CFR 1002.9(a)(1)": ("ecoa", None),
    "12 CFR 1002.9(a)(2)": ("ecoa", None),
    "12 CFR 1002.9(b)(2)": ("ecoa", None),
    "12 CFR 1002.9(c)(2)": ("ecoa", None),
    "12 CFR 1002.4(a)": ("ecoa_general_rules", None),
}


def normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace to a single space; change nothing else."""
    return " ".join(text.split())


def classify(quote: str, passage: str) -> Literal["match", "differ"]:
    """Classify a quote against an extracted source passage.

    Only whitespace runs collapse; everything else is compared verbatim. The quote is tested as a
    substring of the passage because a quote is a portion of the provision, not the whole of it.
    """
    if normalize_whitespace(quote) in normalize_whitespace(passage):
        return "match"
    return "differ"


def quote_corpus_sha256(entries: Iterable[tuple[str, str, str]]) -> str:
    """Fingerprint pack, requirement and exact quote text in a stable order."""
    corpus = sorted(entries)
    encoded = json.dumps(
        corpus, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _PassageExtractor(HTMLParser):
    """Collect the text of one element, joining text nodes at element boundaries.

    A single space is inserted before a text node that follows an element start tag, so words split
    across block-level markup (paragraphs, table cells) stay separate. A space is *not* inserted
    after an end tag, so an inline element closed mid-phrase (``</I>--(1)``) keeps its phrase
    contiguous. Inline elements that open in the middle of a word, which the official sources do not
    use, would gain a space they should not.
    """

    def __init__(self, target_id: str | None) -> None:
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.collecting = target_id is None
        self.depth = 0
        self._at_element_start = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.collecting:
            if tag not in VOID_ELEMENTS:
                self.depth += 1
            self._at_element_start = True
            return
        if tag != "div":
            return
        for name, value in attrs:
            if name == "id" and value == self.target_id:
                self.collecting = True
                self.depth = 1
                self._at_element_start = False
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # A self-closing element contributes no text and no nesting.
        pass

    def handle_endtag(self, tag: str) -> None:
        if not self.collecting:
            return
        if tag not in VOID_ELEMENTS:
            self.depth -= 1
        if self.depth <= 0:
            self.collecting = False
        self._at_element_start = False

    def handle_data(self, data: str) -> None:
        if not self.collecting:
            return
        if self._at_element_start and self.chunks and not self.chunks[-1].endswith(" "):
            self.chunks.append(" ")
        self.chunks.append(data)
        self._at_element_start = False

    def text(self) -> str:
        return "".join(self.chunks)


def extract_passage(source_text: str, *, selector: str | None) -> str | None:
    """Extract the passage a provision names, whitespace-normalized.

    For Cellar XHTML, `selector` is the `id` of the division holding the provision's text; for the
    eCFR response it is None and the whole document is the passage. Returns None when the selector
    is missing from the document -- the source has moved structurally, which is `could-not-verify`,
    not a mismatch.
    """
    parser = _PassageExtractor(selector)
    parser.feed(source_text)
    text = parser.text()
    if not text:
        return None
    return normalize_whitespace(text)


class DriftFetchError(RuntimeError):
    """The official source could not be safely resolved, retrieved, or decoded."""


def _fetch_url(url: str, *, timeout: float, max_bytes: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "reasonsmith-statute-drift/0.2 (+https://github.com/eduardstan/reasonsmith)"
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
    except Exception as exc:  # noqa: BLE001 - every urllib failure mode is an unreachable source
        raise DriftFetchError(f"could not fetch {url}: {exc}") from exc
    if len(data) > max_bytes:
        raise DriftFetchError(f"{url} exceeded the {max_bytes}-byte size guard")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DriftFetchError(f"could not decode {url} as UTF-8: {exc}") from exc


def _current_ecfr_url(source: SourceDocument, *, timeout: float, max_bytes: int) -> str:
    metadata_text = _fetch_url(ECFR_VERSIONS_URL, timeout=timeout, max_bytes=max_bytes)
    try:
        issue_date = json.loads(metadata_text)["meta"]["latest_issue_date"]
        canonical_date = datetime.strptime(issue_date, "%Y-%m-%d").date().isoformat()
        if issue_date != canonical_date:
            raise ValueError(f"non-canonical issue date {issue_date!r}")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise DriftFetchError(
            f"could not resolve the current eCFR version from {ECFR_VERSIONS_URL}: {exc}"
        ) from exc
    prefix, marker, dated_path = source.url.partition("/full/")
    _recorded_date, separator, suffix = dated_path.partition("/")
    if not marker or not separator:
        raise DriftFetchError(f"recorded eCFR URL has no versioned full path: {source.url}")
    return f"{prefix}/full/{issue_date}/{suffix}"


def fetch_source(
    source: SourceDocument, *, timeout: float = DEFAULT_TIMEOUT, max_bytes: int = DEFAULT_MAX_BYTES
) -> str:
    """Fetch the live version of a recorded source document as text.

    The eCFR versioner requires a published issue date, so its current date is resolved from
    official title metadata at run time. Raises `DriftFetchError` on any resolution or retrieval
    failure.
    """
    url = source.url
    if source.kind == "ecfr-xml":
        url = _current_ecfr_url(source, timeout=timeout, max_bytes=max_bytes)
    return _fetch_url(url, timeout=timeout, max_bytes=max_bytes)


@dataclass(frozen=True)
class DriftResult:
    """One requirement's verdict against its source.

    For a `match` the quote still stands in the official text. For a `differ` both strings travel
    with the result -- the pack quote and the extracted passage -- so the finding can be checked by
    hand. For `could-not-verify` `note` carries why no comparison was possible at all.
    """

    pack_id: str
    requirement_id: str
    article_clause: str
    source_url: str
    status: Literal["match", "differ", "could-not-verify"]
    quote: str
    passage: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "pack_id": self.pack_id,
            "requirement_id": self.requirement_id,
            "article_clause": self.article_clause,
            "source_url": self.source_url,
            "status": self.status,
            "quote": self.quote,
            "passage": self.passage,
            "note": self.note,
        }


@dataclass(frozen=True)
class DriftReport:
    """The full result of one drift check run."""

    results: tuple[DriftResult, ...]
    checked_at: datetime

    @property
    def counts(self) -> dict[str, int]:
        counts = {"match": 0, "differ": 0, "could-not-verify": 0}
        for result in self.results:
            counts[result.status] += 1
        return counts

    @property
    def has_drift(self) -> bool:
        return self.counts["differ"] > 0 or self.counts["could-not-verify"] > 0

    def render_text(self) -> str:
        lines = [f"Statute drift check - {self.checked_at:%Y-%m-%d %H:%M UTC}", ""]
        for result in self.results:
            where = f"{result.pack_id}/{result.requirement_id} ({result.article_clause})"
            if result.status == "match":
                lines.append(f"  match            {where}")
            elif result.status == "differ":
                lines.append(f"  DIFFER           {where}")
                lines.append(f"      source:   {result.source_url}")
                lines.append(f"      pack quote:  {result.quote}")
                lines.append(f"      source text: {result.passage}")
            else:
                lines.append(f"  could-not-verify {where}")
                lines.append(f"      source: {result.source_url}")
                lines.append(f"      {result.note}")
        counts = self.counts
        lines += [
            "",
            f"match: {counts['match']}  differ: {counts['differ']}  could-not-verify: "
            f"{counts['could-not-verify']}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "checked_at": self.checked_at.isoformat(),
            "counts": self.counts,
            "has_drift": self.has_drift,
            "findings": [r.to_dict() for r in self.results if r.status != "match"],
            "report": self.render_text(),
        }


Fetcher = Callable[[SourceDocument], str]


def check_statute_drift(
    fetcher: Fetcher,
    *,
    packs: Iterable[str | Path] = STATUTORY_PACKS,
    now: datetime | None = None,
) -> DriftReport:
    """Re-verify every statutory pack quote against a fetcher-supplied source.

    `fetcher` maps a `SourceDocument` to its text and raises `DriftFetchError` when the source is
    unreachable; the live fetch is the default, and tests substitute recorded fixtures.
    """
    results: list[DriftResult] = []
    cache: dict[str, str] = {}
    failed: set[str] = set()
    for pack_name in packs:
        pack = load_pack(pack_name)
        for requirement in pack.requirements:
            try:
                source_key, selector = PROVISIONS[requirement.article_clause]
            except KeyError:
                raise ValueError(
                    f"Requirement {requirement.id!r} in pack {pack.id!r} has clause "
                    f"{requirement.article_clause!r}, which has no registered official source. "
                    "Refusing to check rather than pretending an unregistered quote was verified."
                ) from None
            source = SOURCES_BY_KEY[source_key]
            if source_key in failed:
                results.append(
                    DriftResult(
                        pack_id=pack.id,
                        requirement_id=requirement.id,
                        article_clause=requirement.article_clause,
                        source_url=source.url,
                        status="could-not-verify",
                        quote=requirement.verbatim_text,
                        passage="",
                        note=f"source could not be fetched; see the first finding for {source.url}",
                    )
                )
                continue
            if source_key not in cache:
                try:
                    cache[source_key] = fetcher(source)
                except DriftFetchError as exc:
                    failed.add(source_key)
                    results.append(
                        DriftResult(
                            pack_id=pack.id,
                            requirement_id=requirement.id,
                            article_clause=requirement.article_clause,
                            source_url=source.url,
                            status="could-not-verify",
                            quote=requirement.verbatim_text,
                            passage="",
                            note=str(exc),
                        )
                    )
                    continue
            passage = extract_passage(cache[source_key], selector=selector)
            if passage is None:
                results.append(
                    DriftResult(
                        pack_id=pack.id,
                        requirement_id=requirement.id,
                        article_clause=requirement.article_clause,
                        source_url=source.url,
                        status="could-not-verify",
                        quote=requirement.verbatim_text,
                        passage="",
                        note=f"selector {selector!r} not found in {source.url}",
                    )
                )
                continue
            status = classify(requirement.verbatim_text, passage)
            results.append(
                DriftResult(
                    pack_id=pack.id,
                    requirement_id=requirement.id,
                    article_clause=requirement.article_clause,
                    source_url=source.url,
                    status=status,
                    quote=requirement.verbatim_text,
                    passage=passage if status == "differ" else "",
                )
            )
    return DriftReport(
        results=tuple(results),
        checked_at=now if now is not None else datetime.now(timezone.utc),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the drift check against the live sources and exit non-zero on any drift.

    Writes the machine-readable JSON report to `--report PATH` (the workflow's issue step reads it)
    and prints the human-readable report to stdout.
    """
    parser = argparse.ArgumentParser(
        prog="python -m reasonsmith.drift",
        description="Re-fetch the official legal sources and check every statutory pack quote.",
    )
    parser.add_argument(
        "--report", metavar="PATH", help="write the JSON drift report to PATH (default: none)"
    )
    parser.add_argument(
        "--verification-manifest", metavar="PATH",
        help="write a successful-run quote verification manifest to PATH",
    )
    args = parser.parse_args(argv)
    report = check_statute_drift(fetch_source)
    print(report.render_text())
    if args.report:
        Path(args.report).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    if args.verification_manifest and not report.has_drift:
        matches = sum(result.status == "match" for result in report.results)
        differs = sum(result.status == "differ" for result in report.results)
        corpus_sha256 = quote_corpus_sha256(
            (result.pack_id, result.requirement_id, result.quote)
            for result in report.results
        )
        Path(args.verification_manifest).write_text(
            json.dumps({
                "schema_version": 2,
                "verified_at": report.checked_at.date().isoformat(),
                "match": matches,
                "differ": differs,
                "quote_corpus_sha256": corpus_sha256,
                "method": "python -m reasonsmith.drift",
            }, indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if report.has_drift else 0


if __name__ == "__main__":
    sys.exit(main())
