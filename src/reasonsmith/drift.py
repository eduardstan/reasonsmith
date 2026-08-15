"""Statute drift check: re-verify pack quotes against the live official sources.

What this module is for:
  Re-fetches the official statutory documents recorded in `docs/legal-sources.md` and checks every
  `verbatim_text` in the EU AI Act, GDPR, ECOA, and Seoul Frontier AI Safety Commitments packs
  against them character-for-character. The
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
  - GOV.UK HTML sources carry an edition sentinel. A changed update marker is a review finding and
    never silently repoints an immutable pack.
  - PDF sources use the optional, exactly pinned `pdfminer.six` extra. Extraction is text-layer
    only:
    encrypted, scanned/image-only, tool-version-drifted, or otherwise unparseable PDFs are
    `could-not-verify`. No OCR is attempted. The SHA-256 of fetched bytes travels beside each PDF
    result as corroboration; it never replaces quotation matching.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Literal, cast

from reasonsmith.spec import load_pack

#: The packs whose quotes are verified against official statutory sources. `table7` is deliberately
#: absent: its quotes come from the review paper itself, and no official document re-fetches them.
STATUTORY_PACKS = ("eu_ai_act", "gpai", "gdpr", "ecoa", "seoul_frontier_ai_safety_2024")

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
#: Exact extractor release accepted by the deterministic PDF route. Keep this in lockstep with the
#: optional `pdf` extra; a different installed release is a refusal, not an unmeasured pass.
PDFMINER_SIX_VERSION = "20250506"


@dataclass(frozen=True)
class SourceDocument:
    """A recorded official statutory source.

    `url` is copied verbatim from `docs/legal-sources.md`; `test_drift.py` holds the registry to
    that file so the two cannot drift apart. `kind` names the format the endpoint serves and tells
    the live fetch whether it must resolve the current version before retrieval.
    """

    key: str
    url: str
    kind: Literal["cellar-xhtml", "ecfr-xml", "pdf", "govuk-html"]
    versions_url: str | None = None
    edition_sentinel: str | None = None


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
    SourceDocument(
        "seoul_frontier_ai_safety_2024",
        "https://www.gov.uk/government/publications/frontier-ai-safety-commitments-ai-seoul-summit-2024/frontier-ai-safety-commitments-ai-seoul-summit-2024",
        "govuk-html",
        edition_sentinel="Updated 7 February 2025",
    ),
    SourceDocument(
        "uniform_guidelines",
        "https://www.ecfr.gov/api/versioner/v1/full/2017-01-03/title-29.xml?part=1607&section=1607.4",
        "ecfr-xml",
        versions_url="https://www.ecfr.gov/api/versioner/v1/versions/title-29.json?part=1607&section=1607.4",
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
    "Commitment I": ("seoul_frontier_ai_safety_2024", "I"),
    "Commitment II": ("seoul_frontier_ai_safety_2024", "II"),
    "Commitment III": ("seoul_frontier_ai_safety_2024", "III"),
    "Commitment IV": ("seoul_frontier_ai_safety_2024", "IV"),
    "Commitment V": ("seoul_frontier_ai_safety_2024", "V"),
    "Commitment VI": ("seoul_frontier_ai_safety_2024", "VI"),
    "Commitment VII": ("seoul_frontier_ai_safety_2024", "VII"),
    "Commitment VIII": ("seoul_frontier_ai_safety_2024", "VIII"),
    "29 CFR 1607.4(D)": ("uniform_guidelines", None),
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


class _GovUkCommitmentExtractor(HTMLParser):
    """Extract one numbered commitment paragraph from GOV.UK's govspeak HTML.

    GOV.UK's publication page is not a statute XML document: the operative passages are ordinary
    paragraphs under ``main .gem-c-govspeak`` and footnote links are presentation nodes. We keep
    only that subtree, discard linked ``sup`` footnotes, and leave punctuation and Unicode text
    untouched for the ordinary whitespace-only quote comparison.
    """

    def __init__(self, selector: str) -> None:
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.main_depth = 0
        self.govspeak_depth = 0
        self.p_depth = 0
        self.skip_sup_depth = 0
        self.after_sup = False
        self.chunks: list[str] = []
        self.found: str | None = None
        self._at_element_start = False

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: value or "" for name, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = self._attrs(attrs)
        if tag == "main":
            self.main_depth += 1
        target_container = (
            self.main_depth
            and tag in {"div", "section"}
            and "gem-c-govspeak" in attr.get("class", "").split()
        )
        if target_container:
            self.govspeak_depth = 1
        elif self.govspeak_depth and tag not in VOID_ELEMENTS:
            self.govspeak_depth += 1
        if self.govspeak_depth and tag == "p" and self.p_depth == 0:
            self.p_depth = 1
            self.chunks = []
            self._at_element_start = True
        elif self.p_depth and tag == "p":
            self.p_depth += 1
        elif self.p_depth and tag == "sup":
            self.skip_sup_depth = 1
        elif self.skip_sup_depth and tag not in VOID_ELEMENTS:
            self.skip_sup_depth += 1
        elif self.p_depth:
            self._at_element_start = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Footnote/self-closing nodes carry no operative text.
        return

    def handle_endtag(self, tag: str) -> None:
        if self.skip_sup_depth:
            if tag not in VOID_ELEMENTS:
                self.skip_sup_depth -= 1
            if self.skip_sup_depth == 0:
                self.after_sup = True
            return
        if self.p_depth and tag == "p":
            self.p_depth -= 1
            if self.p_depth == 0:
                text = normalize_whitespace("".join(self.chunks))
                if text.startswith(f"{self.selector}."):
                    self.found = text
        if self.govspeak_depth and tag not in VOID_ELEMENTS:
            self.govspeak_depth -= 1
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
        self._at_element_start = False

    def handle_data(self, data: str) -> None:
        if not self.p_depth or self.skip_sup_depth or self.found is not None:
            return
        if self.after_sup:
            if re.match(r"^\s+[,.;:!?]", data):
                data = data.lstrip()
            self.after_sup = False
        if self._at_element_start and self.chunks and not self.chunks[-1].endswith(" "):
            self.chunks.append(" ")
        self.chunks.append(data)
        self._at_element_start = False


class _GovUkEditionExtractor(HTMLParser):
    """Collect rendered GOV.UK edition markers from the inverse header."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.chunks: list[str] = []
        self.markers: list[str] = []
        self._capturing = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name: value or "" for name, value in attrs}
        if tag == "p" and "gem-c-inverse-header__subtext" in attr.get("class", "").split():
            self._capturing = True
            self.depth = 1
            self.chunks = []
        elif self._capturing and tag not in VOID_ELEMENTS:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self._capturing:
            return
        if tag not in VOID_ELEMENTS:
            self.depth -= 1
        if self.depth <= 0:
            self.markers.append(normalize_whitespace("".join(self.chunks)))
            self._capturing = False

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self.chunks.append(data)


def extract_govuk_edition(source_text: str) -> str:
    """Return the single rendered GOV.UK update marker, refusing an ambiguous page."""
    parser = _GovUkEditionExtractor()
    parser.feed(source_text)
    if len(parser.markers) != 1:
        raise DriftFetchError(
            "GOV.UK edition sentinel could not be verified: expected exactly one rendered "
            f"'gem-c-inverse-header__subtext' marker, found {len(parser.markers)}"
        )
    return parser.markers[0]


def _validate_source_edition(source: SourceDocument, payload: SourcePayload) -> None:
    if source.edition_sentinel is None:
        return
    if not isinstance(payload, str):
        raise DriftFetchError(f"edition sentinel for {source.key} requires decoded text")
    marker = extract_govuk_edition(payload)
    if marker != source.edition_sentinel:
        raise DriftFetchError(
            f"GOV.UK edition sentinel mismatch for {source.key}: expected "
            f"{source.edition_sentinel!r}, found {marker!r}; review the immutable pack edition"
        )


def extract_govuk_commitment(source_text: str, *, selector: str) -> str | None:
    """Extract a Roman-numbered commitment paragraph from the GOV.UK govspeak subtree."""
    parser = _GovUkCommitmentExtractor(selector)
    parser.feed(source_text)
    return parser.found


def extract_passage(
    source_text: SourcePayload, *, selector: str | None, kind: str | None = None
) -> str | None:
    """Extract the passage a provision names, whitespace-normalized.

    For Cellar XHTML, `selector` is the `id` of the division holding the provision's text; for the
    eCFR response it is None and the whole document is the passage. A PDF has no structural
    selector and supplies its whole deterministic text layer. Returns None when an XHTML selector
    is missing from the document -- a structural move is `could-not-verify`, not a mismatch.
    """
    if kind == "govuk-html":
        if selector is None:
            raise DriftFetchError("GOV.UK HTML provisions require a numbered paragraph selector")
        if isinstance(source_text, bytes):
            try:
                source_text = source_text.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise DriftFetchError(f"could not decode GOV.UK HTML as UTF-8: {exc}") from exc
        return extract_govuk_commitment(source_text, selector=selector)
    if isinstance(source_text, bytes):
        if selector is not None:
            raise DriftFetchError("PDF provision selectors are unsupported; the PDF is one passage")
        return extract_pdf_text(source_text)
    parser = _PassageExtractor(selector)
    parser.feed(source_text)
    text = parser.text()
    if not text:
        return None
    return normalize_whitespace(text)


class DriftFetchError(RuntimeError):
    """The official source could not be safely resolved, retrieved, or decoded."""


SourcePayload = str | bytes


def extract_pdf_text(data: bytes) -> str:
    """Extract and normalize a PDF text layer with the pinned pdfminer.six release.

    This deliberately does not fall back to OCR. Encryption, a missing text layer, an unavailable
    or different extractor release, and every parser failure are explicit refusals.
    """
    try:
        installed = importlib.metadata.version("pdfminer.six")
    except importlib.metadata.PackageNotFoundError as exc:
        raise DriftFetchError(
            "pdf extraction requires the optional pdf extra (pdfminer.six is not installed)"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - an unknown tool cannot be trusted
        raise DriftFetchError(f"could not determine the pdfminer.six version: {exc}") from exc
    if installed != PDFMINER_SIX_VERSION:
        raise DriftFetchError(
            "PDF extraction tool version drift: expected pdfminer.six "
            f"{PDFMINER_SIX_VERSION}, found {installed}"
        )
    try:
        from pdfminer.high_level import extract_text
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfparser import PDFParser

        stream = io.BytesIO(data)
        document = PDFDocument(PDFParser(stream))
        if document.encryption is not None:
            raise DriftFetchError(
                "encrypted PDFs are refused; no password or decryption is attempted"
            )
        if not document.is_extractable:
            raise DriftFetchError("PDF text extraction is not permitted by the document")
        stream.seek(0)
        extracted = extract_text(stream)
        text = normalize_whitespace(extracted)
    except DriftFetchError:
        raise
    except Exception as exc:  # noqa: BLE001 - every extraction failure is a loud refusal
        if exc.__class__.__name__ in {"PDFEncryptionError", "PDFPasswordIncorrect"}:
            raise DriftFetchError(
                "encrypted PDFs are refused; no password or decryption is attempted"
            ) from exc
        raise DriftFetchError(f"could not extract PDF text: {exc}") from exc
    if not text:
        raise DriftFetchError(
            "PDF has no extractable text layer; scanned/image-only sources are refused "
            "(OCR is not used)"
        )
    return text


def _fetch_url_bytes(url: str, *, timeout: float, max_bytes: int) -> bytes:
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
    return cast(bytes, data)


def _fetch_url(url: str, *, timeout: float, max_bytes: int) -> str:
    data = _fetch_url_bytes(url, timeout=timeout, max_bytes=max_bytes)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DriftFetchError(f"could not decode {url} as UTF-8: {exc}") from exc


def _current_ecfr_url(source: SourceDocument, *, timeout: float, max_bytes: int) -> str:
    metadata_url = source.versions_url or ECFR_VERSIONS_URL
    metadata_text = _fetch_url(metadata_url, timeout=timeout, max_bytes=max_bytes)
    try:
        issue_date = json.loads(metadata_text)["meta"]["latest_issue_date"]
        canonical_date = datetime.strptime(issue_date, "%Y-%m-%d").date().isoformat()
        if issue_date != canonical_date:
            raise ValueError(f"non-canonical issue date {issue_date!r}")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise DriftFetchError(
            f"could not resolve the current eCFR version from {metadata_url}: {exc}"
        ) from exc
    prefix, marker, dated_path = source.url.partition("/full/")
    _recorded_date, separator, suffix = dated_path.partition("/")
    if not marker or not separator:
        raise DriftFetchError(f"recorded eCFR URL has no versioned full path: {source.url}")
    return f"{prefix}/full/{issue_date}/{suffix}"


def fetch_source(
    source: SourceDocument, *, timeout: float = DEFAULT_TIMEOUT, max_bytes: int = DEFAULT_MAX_BYTES
) -> SourcePayload:
    """Fetch a recorded source as UTF-8 text, or raw bytes for the PDF route.

    The eCFR versioner requires a published issue date, so its current date is resolved from
    official title metadata at run time. Raises `DriftFetchError` on any resolution or retrieval
    failure.
    """
    url = source.url
    if source.kind == "ecfr-xml":
        url = _current_ecfr_url(source, timeout=timeout, max_bytes=max_bytes)
    if source.kind == "pdf":
        payload: SourcePayload = _fetch_url_bytes(url, timeout=timeout, max_bytes=max_bytes)
    else:
        # Both XHTML/XML and GOV.UK HTML are UTF-8 text. Edition validation is performed after
        # decoding, before a caller can mistake a changed immutable edition for quote drift.
        payload = _fetch_url(url, timeout=timeout, max_bytes=max_bytes)
    _validate_source_edition(source, payload)
    return payload


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
    source_sha256: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "requirement_id": self.requirement_id,
            "article_clause": self.article_clause,
            "source_url": self.source_url,
            "status": self.status,
            "quote": self.quote,
            "passage": self.passage,
            "note": self.note,
            **({"source_sha256": self.source_sha256} if self.source_sha256 else {}),
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

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_at": self.checked_at.isoformat(),
            "counts": self.counts,
            "has_drift": self.has_drift,
            "findings": [r.to_dict() for r in self.results if r.status != "match"],
            "report": self.render_text(),
        }


Fetcher = Callable[[SourceDocument], SourcePayload]


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
    cache: dict[str, SourcePayload] = {}
    source_hashes: dict[str, str] = {}
    failed: set[str] = set()
    failure_notes: dict[str, str] = {}
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
                        note=failure_notes.get(
                            source_key,
                            "source could not be verified; see the first finding for "
                            f"{source.url}",
                        ),
                        source_sha256=source_hashes.get(source_key, ""),
                    )
                )
                continue
            if source_key not in cache:
                try:
                    cache[source_key] = fetcher(source)
                    payload = cache[source_key]
                    _validate_source_edition(source, payload)
                    raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
                    source_hashes[source_key] = hashlib.sha256(raw).hexdigest()
                except DriftFetchError as exc:
                    failed.add(source_key)
                    failure_notes[source_key] = str(exc)
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
            try:
                passage = extract_passage(cache[source_key], selector=selector, kind=source.kind)
            except DriftFetchError as exc:
                failed.add(source_key)
                failure_notes[source_key] = str(exc)
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
                        source_sha256=source_hashes.get(source_key, ""),
                    )
                )
                continue
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
                        source_sha256=source_hashes.get(source_key, ""),
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
                    source_sha256=source_hashes.get(source_key, ""),
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
