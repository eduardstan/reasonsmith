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
  - **A frame opens where the documents differ, and holds all of the one it shows.** See
    `FRAME_ANCHOR` and `FRAME_HEIGHT`. The frames used to open at the top and be tall, which
    put five copies of the same masthead, headline and dashboard on the screen and the first
    real difference below every frame's visible area: the page claimed a difference it did not
    show. The only mechanism here is a scroll position set on load — one anchor and one height
    for all five, nothing cropped, nothing restyled, nothing reordered, and with scripting off
    the frames open at the top exactly as they did.
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
#:
#: It is short on purpose. Paired with `FRAME_ANCHOR`, one 24rem window opens on the requirement
#: findings and holds the band where the projections show — the identifier, the badges, the
#: lattice, the signals — and stops before the evidence paragraph, which is the same wall of
#: prose in four of the five documents. Two frames then fit one screen at a normal window size,
#: so the comparison is made by looking rather than by remembering: a taller frame shows more of
#: one document and less of the next, and reading the difference becomes reading every word
#: twice.
FRAME_HEIGHT = "24rem"

#: The element every rendering carries and every rendering draws differently, and the one place
#: a frame may be opened at instead of the top.
#:
#: Opened at the top, four of the five frames are byte-identical for their whole first screen —
#: the masthead, the headline banner and the dashboard are chrome the projection does not touch,
#: so a page whose whole argument is that these documents differ opened on five copies of the
#: same picture. `id="findings"` is the anchor `render_html` already puts on the requirement
#: findings heading for its own skip link, it exists in all five renderings, and it is where the
#: projections start to show: the auditor's cards carry the lattice, the signals, the evidence
#: sentence and the witnesses; the regulator's carry no signals and no missing-capability
#: finding; the affected individual's carry the verdict alone, under two plain-language sections
#: no expert reading has.
#:
#: One anchor for all five, so this is a scroll position and not a crop: nothing is hidden, each
#: frame still holds the whole document, and scrolling up inside one reaches the masthead it
#: opened past. Without scripting the frames simply open at the top, which is where they were.
FRAME_ANCHOR = "findings"

#: Scroll the frame to `FRAME_ANCHOR` on load. `scrollTo` on the frame's own window rather than
#: `scrollIntoView`, which would also scroll the page holding the frame.
FRAME_ONLOAD = (
    "var w=this.contentWindow,e=w.document.getElementById('" + FRAME_ANCHOR + "');"
    "if(e)w.scrollTo(0,e.getBoundingClientRect().top+w.scrollY)"
)


def gallery_report() -> ConformanceReport:
    """The run behind the page: the shipped rule-based underwriting system against `ecoa`.

    Chosen because it is the run where the five readers have the most to differ about, and it
    is not the run `docs/report.html` already publishes:

      - verdicts and strengths are mixed in one report — two duties `proved` by Z3, one
        `observed` over the trace, two `unattainable` as built (no `probed` rung: nothing
        this system exposes leaves a duty to a bounded search) — so the strength lattice the
        affected individual is not shown is carrying something to be not shown;
      - two duties are unattainable for named missing capabilities, which the regulator's
        rendering drops and the developer's keeps, and those blocks are the single most visible
        difference between two expert readings on the page;
      - the system exposes both logic and a decision trace, so the plain-language account the
        affected individual is shown quotes two decisions the system actually recorded rather
        than reporting that this run read none.

    Scope and domain are declared, because an undeclared system is reported `not_applicable`
    on a domain-limited duty and a page of five not-applicable rows demonstrates nothing about
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
        f'onload="{html.escape(FRAME_ONLOAD, quote=True)}" '
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
      <p class="limits-text">Each frame is <em>scrolled</em> to the requirement findings, not
      cropped to them: the masthead, the headline and the dashboard above them are the same in
      every rendering because a projection does not touch them, and five copies of one picture
      demonstrate nothing. Every frame holds its whole document and scrolling up inside one
      reaches the part it opened past. The findings are where the projections show: what a card
      carries below its verdict — the strength lattice, the signals, the engine's sentence, the
      witnesses — is exactly what the fields listed above each frame decide.</p>
      <p class="limits-text">The affected individual's document is the shortest here, and one of
      its sections reports that nothing in this run measured whether the reasons the system
      stated were all the reasons it acted on. Both are correct output. A document that is short
      because its reader is not owed solver input, and that says plainly what was not measured
      rather than leaving silence to be read as a clean result, is the result this tool is for —
      not a rendering that failed to fill. Its two plain-language sections — the decisions the
      system recorded, and the reasons nothing here measured — sit immediately above the findings
      its frame opens on, and no other reader on this page is shown them.</p>
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
