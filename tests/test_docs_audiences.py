"""Tests holding `docs/audiences.html` to its builder and to the stylesheet it borrows.

What this module is for:
  `docs/audiences.html` is generated, not hand-maintained, and it makes one argument: the same
  conformance run reaches five readers as five different documents. Two things can quietly make
  that argument false. The evidence can stop being the renderer's output — a frame filled by
  hand shows whatever was typed into it — and the page can stop belonging to the product, by
  growing a palette, a font stack or a stylesheet of its own beside the one `render_html`
  already ships. One test here pins the first and one pins the second.

What a reader must not break:
  - The builder is loaded and run, never re-implemented. `docs/` is not an import package, so it
    is loaded by path exactly as `tests/test_html_report.py` loads `docs/build_example.py`.
  - `test_the_page_adds_no_palette_font_or_stylesheet` reads the design tokens back out of the
    rendered page rather than holding a list of its own. A token renamed in `render.py` fails
    this test at the use site instead of leaving the page referring to a variable that no longer
    exists.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from reasonsmith.render import AUDIENCES

ROOT = Path(__file__).resolve().parents[1]
DOCS_AUDIENCES = ROOT / "docs" / "audiences.html"


def _load_build_audiences():
    spec = importlib.util.spec_from_file_location(
        "build_audiences", ROOT / "docs" / "build_audiences.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_audiences = _load_build_audiences()


def test_docs_audiences_html_matches_the_builder():
    """The committed page is generated: it must match its build script byte for byte.

    Regenerate it with `python docs/build_audiences.py`, the command the page itself names.
    """
    assert DOCS_AUDIENCES.read_text(encoding="utf-8") == build_audiences.render()


def test_the_page_names_a_provenance_command_that_reproduces_it():
    """A command the page cannot be reproduced from is decoration, not provenance."""
    page = DOCS_AUDIENCES.read_text(encoding="utf-8")

    assert f"Command: <code>{build_audiences.BUILD_COMMAND}</code>" in page
    assert "test_docs_audiences_html_matches_the_builder" in build_audiences.PROVENANCE_NOTE
    assert build_audiences.PROVENANCE_NOTE in page


def test_every_audience_is_embedded_as_a_whole_document():
    """Five readers, five complete renderings, none of them retyped.

    A frame holding a fragment, a summary or an excerpt would let the page argue from an
    artefact of the excerpting. Each `srcdoc` must therefore be a document in its own right,
    and the set of them must be exactly the audiences the renderer defines — not four of five,
    and not a sixth this page invented.
    """
    page = DOCS_AUDIENCES.read_text(encoding="utf-8")
    frames = re.findall(r'srcdoc="([^"]*)"', page)

    assert len(frames) == len(AUDIENCES)
    for frame in frames:
        assert frame.startswith("&lt;!DOCTYPE html&gt;")
        assert "&lt;/html&gt;" in frame
        assert "LIMITS OF THIS REPORT" in frame or "Limits of this report" in frame

    for name in AUDIENCES:
        assert f"<span>{name}</span>" in page


def test_the_page_states_the_short_document_is_correct():
    """The page's sentence about the shortest document is held to that document.

    `--audience affected-individual` produces the shortest rendering on this page, and on this
    run one of its sections reports that nothing measured whether the stated reasons were all
    the reasons. The page says both are correct output rather than a rendering that failed to
    fill. That sentence is a claim about an artefact, so it fails here if the artefact stops
    carrying what it describes — a page reassuring a reader about a finding that is no longer
    on it is worse than no reassurance.
    """
    report = build_audiences.gallery_report()
    lay = report.render_html(commit_hash="", audience="affected-individual")
    expert = report.render_html(commit_hash="", audience="auditor")

    assert len(lay) < len(expert)
    assert "Nothing in this report measured that." in lay

    page = DOCS_AUDIENCES.read_text(encoding="utf-8")
    assert "not a rendering that failed to fill" in page


def test_the_page_adds_no_palette_font_or_stylesheet():
    """The gallery borrows the renderer's tokens and classes and introduces none of its own.

    The site's visual identity belongs with the renderer. This page is a `render_html` page for
    exactly that reason — it is the only way the tokens are in scope at all — so the section it
    inserts may reference them and may not restate them. A colour literal, a font stack or a
    second `<style>` block here is a competing design system in the one document whose job is
    to look like every other report this tool writes.
    """
    page = DOCS_AUDIENCES.read_text(encoding="utf-8")
    gallery = build_audiences.gallery_html(build_audiences.gallery_report())
    chrome = re.sub(r'srcdoc="[^"]*"', "", gallery)

    assert "<style" not in chrome
    for literal in ("oklch(", "rgb(", "#0", "#f", "#F", "font-family"):
        assert literal not in chrome

    tokens = set(re.findall(r"var\((--[a-z0-9-]+)\)", chrome))
    assert tokens, "the gallery styles nothing through the renderer's tokens"
    for token in tokens:
        assert f"{token}:" in page, f"{token} is not a token this renderer defines"

    classes = {
        name
        for attr in re.findall(r'class="([^"]*)"', chrome)
        for name in attr.split()
    }
    for name in classes:
        assert f".{name}" in page, f"class {name} is not defined by the renderer's stylesheet"
