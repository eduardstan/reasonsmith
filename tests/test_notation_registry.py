"""Registry checks for the mathematical notation spine.

The extraction below is intentionally a heuristic, in the same spirit as ``VENUE_MARKERS`` in
``test_docs_formal.py``: it checks symbol resolution and registry hygiene, not LaTeX validity or
house style. It is not a LaTeX parser.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
THEORY_DIR = REPO_ROOT / "docs" / "theory"
NOTATION = THEORY_DIR / "00-notation.md"

# A table row's first cell is its declaration. The exact cell is the registry key: this lets the
# duplicate check reject a second declaration without pretending that LaTeX has one canonical AST.
_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|")
_MATH = re.compile(r"\$\$(.*?)\$\$|\$(?!\$)(.*?)(?<!\\)\$(?!\$)", re.DOTALL)
_CONTROL = re.compile(r"\\[a-zA-Z]+")
_SINGLE_LETTER = re.compile(r"(?<![A-Za-z])[A-Za-z](?![A-Za-z])")
_CODE_SPAN = re.compile(r"`[^`]*`")

# These commands only lay out or annotate a formula; they are not mathematical notation.
_LAYOUT_CONTROLS = {
    "\\begin", "\\end", "\\left", "\\right", "\\text", "\\quad", "\\qquad",
    "\\hspace", "\\mkern", "\\thinspace", "\\thickspace", "\\medspace", "\\mathrel",
    "\\cr", "\\lbrace", "\\rbrace",
}
# Environment names are arguments to layout commands, not notation declarations.
_LAYOUT_ENVIRONMENTS = {"aligned", "cases"}


def _table_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in NOTATION.read_text(encoding="utf-8").splitlines():
        match = _TABLE_ROW.match(line)
        if match and match.group(1).strip() != "LaTeX form":
            rows.append((match.group(1).strip(), line))
    return rows


def _math_spans(text: str) -> list[str]:
    """Extract GitHub math spans, ignoring code spans; this is deliberately not a LaTeX parser."""
    text = _CODE_SPAN.sub("", text)
    return [match.group(1) or match.group(2) for match in _MATH.finditer(text)]


def _tokens(text: str) -> set[str]:
    controls = set(_CONTROL.findall(text)) - _LAYOUT_CONTROLS
    without_controls = _CONTROL.sub("", text)
    for environment in _LAYOUT_ENVIRONMENTS:
        without_controls = without_controls.replace(environment, "")
    return controls | set(_SINGLE_LETTER.findall(without_controls))


def _declared_tokens() -> set[str]:
    return _tokens(" ".join(cell for cell, _ in _table_rows()))


def _used_tokens() -> set[str]:
    spans: list[str] = []
    for path in sorted(THEORY_DIR.glob("*.md")):
        if path == NOTATION:
            continue
        spans.extend(_math_spans(path.read_text(encoding="utf-8")))
    return _tokens(" ".join(spans))


def test_the_notation_table_has_entries_and_they_are_unique():
    """The notation table is non-empty and does not declare one form twice."""
    rows = _table_rows()
    assert rows, "docs/theory/00-notation.md defines no notation entries"
    forms = [form for form, _ in rows]
    duplicates = sorted({form for form in forms if forms.count(form) > 1})
    assert not duplicates, "the notation table declares a symbol twice: " + ", ".join(duplicates)


def test_every_symbol_used_resolves_to_a_notation_entry():
    """Every control sequence and bare single-letter token in theory math is registered."""
    missing = sorted(_used_tokens() - _declared_tokens())
    assert not missing, "theory math uses unregistered symbol(s): " + ", ".join(missing)


def test_every_notation_entry_is_used():
    """Every declared control sequence or bare letter occurs in the theory math corpus."""
    unused = sorted(_declared_tokens() - _used_tokens())
    assert not unused, "notation entry token(s) are unused: " + ", ".join(unused)


def test_math_spans_are_commonmark_escape_safe():
    """CommonMark strips backslashes before ASCII punctuation before math rendering."""
    ascii_punctuation = r'!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    unsafe: list[tuple[Path, str]] = []
    paths = sorted(THEORY_DIR.glob("*.md")) + [REPO_ROOT / "docs" / "semantics.md"]
    for path in paths:
        for span in _math_spans(path.read_text(encoding="utf-8")):
            if any(span[index] == "\\" and span[index + 1] in ascii_punctuation
                   for index in range(len(span) - 1)):
                unsafe.append((path, span))
    assert not unsafe, "math span contains a CommonMark-unsafe backslash escape: " + repr(unsafe)
