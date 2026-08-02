"""Builds `docs/audiences.html`, the committed page showing one run rendered for five readers.

What this module is for:
  `docs/report.html` shows what a conformance report looks like. It shows it once, for one
  reader. This page shows the same report reaching *five* readers as five documents, because
  the audience projection is the one capability of this tool a reader cannot see working from
  a single rendering: a claim that a regulator is shown less than an auditor is worth nothing
  beside the two documents.

  Run: `python docs/build_audiences.py`

What a reader must not break:
  - **Every document on the page comes out of `render_html`.** The five frames carry complete,
    self-contained renderings — the same bytes `reasonsmith check --audience <name>` would hand
    a reader — embedded verbatim through `srcdoc`. Nothing here re-renders, summarises or
    abbreviates a report: a page arguing that projections differ, whose evidence had been
    retyped, would be arguing from an artefact of the typing.
  - **No new palette, font or stylesheet.** The page *is* a `render_html` page, which is the
    only reason the design tokens are in scope at all: they live inside that function's
    stylesheet and are not exported. The gallery therefore reuses the classes already defined
    there — `limits-card`, `limits-header`, `limits-text`, `split-grid`, `split-card`,
    `split-card-header`, `signal-tag`, `text-muted` — and adds two inline rules and no more:
    one collapsing the grid to a single column, and one sizing the frames, written in the
    existing `--line`, `--radius`, `--paper` and `--space-xs` tokens.

    The frames are stacked full width rather than tiled. Tiled two to a row they are 412px
    wide, which drops each embedded document into its own mobile layout, and five identical
    dark headers stacked in five narrow columns is not a comparison. Full width they render as
    the documents they are, and the comparison a reader actually needs — what this reader is
    not shown that the next one is — is answered by the legend above each frame, which is read
    off the projection rather than off the pixels.
  - **What each reader loses is derived, never asserted.** `_suppressed` reads the
    `AudienceProjection` dataclass itself, so a projection that gains, loses or renames a field
    changes this page rather than making it wrong.
  - **The short document is not a failure.** The affected individual's rendering is the
    shortest on the page and one of its sections reports that nothing in this run measured
    whether the stated reasons were all the reasons. The page says so, and
    `test_the_page_states_the_short_document_is_correct` holds that sentence to the rendering
    it describes, so it cannot survive the finding it is about disappearing.
  - `test_docs_audiences_html_matches_the_builder` runs this module rather than composing the
    page a second time. Do not give the test its own copy of this composition. `commit_hash=""`
    and `PROVENANCE_NOTE` carry the same claim, for the same reason, as `docs/build_example.py`.
"""

from __future__ import annotations

import html
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reasonsmith.examples.symbolic_rules import system_under_test  # noqa: E402
from reasonsmith.render import AUDIENCES, AudienceProjection  # noqa: E402
from reasonsmith.report import ConformanceReport, check_conformance  # noqa: E402
from reasonsmith.spec import load_pack  # noqa: E402

#: The provenance the page reports, and the command that reproduces it byte-for-byte.
BUILD_COMMAND = "python docs/build_audiences.py"

PROVENANCE_NOTE = (
    "Re-running that command in any checkout of this repository rewrites this page identically; "
    "test_docs_audiences_html_matches_the_builder fails if it does not. No commit hash is named "
    "because a page committed into the repository it describes cannot name the commit that "
    "carries it: that commit does not exist while the page is being rendered."
)

AUDIENCES_HTML = ROOT / "docs" / "audiences.html"

#: How tall each embedded document is drawn. One number, so no frame is given more room than
#: another and a document's length on the page is its own length and not a layout decision.
FRAME_HEIGHT = "44rem"


def gallery_report() -> ConformanceReport:
    """The run behind the page: the shipped rule-based underwriting system against `ecoa`.

    Chosen because it is the run where the five readers have the most to differ about, and it
    is not the run `docs/report.html` already publishes:

      - all three evidence rungs stand in one report — two duties `proved` by Z3, one
        `observed` over the trace, one `unattainable` as built — so the strength lattice the
        affected individual is not shown is carrying something to be not shown;
      - one duty is unattainable for a named missing capability, which the regulator's
        rendering drops and the developer's keeps, and that block is the single most visible
        difference between two expert readings on the page;
      - the system exposes both logic and a decision trace, so the plain-language account the
        affected individual is shown quotes two decisions the system actually recorded rather
        than reporting that this run read none.

    Scope and domain are declared, because an undeclared system is reported `not_applicable`
    on a domain-limited duty and a page of four not-applicable rows demonstrates nothing about
    audiences. `system_under_test()` already declares `consumer-credit`; the class declaration
    is this caller's, exactly as it is in `docs/build_example.py`.
    """
    return check_conformance(
        system_under_test(),
        load_pack("ecoa"),
        system_name="underwriting-rules (symbolic, logic exposed)",
        system_scope="high-risk",
    )


def _suppressed(view: AudienceProjection) -> list[str]:
    """The parts of the report this projection does not draw, read off the projection itself.

    `plain_account` is excluded because it is the one field that emits rather than suppresses:
    listing it as withheld from four readers would describe the page backwards.
    """
    return [
        f.name
        for f in fields(view)
        if f.name != "plain_account" and not getattr(view, f.name)
    ]


def _card(name: str, document: str) -> str:
    """One reader's frame: the audience, what it is not shown, and the document itself."""
    view = AUDIENCES[name]
    withheld = _suppressed(view)
    if withheld:
        tags = "".join(
            f'<span class="signal-tag">{html.escape(field)}</span>' for field in withheld
        )
        legend = f'<p class="text-muted">Not drawn for this reader: {tags}</p>'
    else:
        legend = (
            '<p class="text-muted">Not drawn for this reader: nothing. '
            "This is the full report.</p>"
        )
    if view.plain_account:
        legend += (
            '<p class="text-muted">Drawn only for this reader: '
            '<span class="signal-tag">plain_account</span></p>'
        )
    return (
        '        <div class="split-card">\n'
        '          <div class="split-card-header">\n'
        f"            <span>{html.escape(name)}</span>\n"
        f"            <span>{len(document):,} characters</span>\n"
        "          </div>\n"
        f"          {legend}\n"
        f'          <iframe title="The {html.escape(name)} rendering of this run" '
        'loading="lazy" style="width: 100%; height: '
        f"{FRAME_HEIGHT}; margin-top: var(--space-xs); border: 1px solid var(--line); "
        'border-radius: var(--radius); background: var(--paper);" '
        f'srcdoc="{html.escape(document, quote=True)}"></iframe>\n'
        "        </div>\n"
    )


def gallery_html(report: ConformanceReport) -> str:
    """The five documents, longest first, so the page's own gradient is the finding."""
    documents = {
        name: report.render_html(commit_hash="", command=BUILD_COMMAND, audience=name)
        for name in AUDIENCES
    }
    order = sorted(documents, key=lambda name: -len(documents[name]))
    cards = "".join(_card(name, documents[name]) for name in order)
    return f"""
    <section class="limits-card">
      <h3 class="limits-header">One run, five readers</h3>
      <p class="limits-text">Each frame below holds a complete conformance report — the whole
      document <code>reasonsmith check --audience &lt;name&gt;</code> writes, embedded as it was
      written. All five are the same run against the same pack, evaluated once. An audience
      projection decides <em>what is shown</em> and never what is claimed: no verdict differs
      between these documents, no audience loses the report's limits, and no audience sees a
      verdict another audience does not (<code>docs/semantics.md</code> §7). What differs is
      which parts of the one report are drawn, listed above each frame as the field names of
      the projection that produced it. The page you are reading is that same run once more, at
      full width, with nothing withheld.</p>
      <p class="limits-text">The affected individual's document is the shortest here, and one of
      its sections reports that nothing in this run measured whether the reasons the system
      stated were all the reasons it acted on. Both are correct output. A document that is short
      because its reader is not owed solver input, and that says plainly what was not measured
      rather than leaving silence to be read as a clean result, is the result this tool is for —
      not a rendering that failed to fill.</p>
      <div class="split-grid" style="grid-template-columns: 1fr;">
{cards}      </div>
    </section>
"""


def render() -> str:
    report = gallery_report()
    return report.render_html(
        commit_hash="",
        command=BUILD_COMMAND,
        extra_section_html=gallery_html(report),
        provenance_note=PROVENANCE_NOTE,
    )


def main() -> None:
    AUDIENCES_HTML.write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    main()
