"""Builds `docs/report.html`, the committed example conformance report page.

What this module is for:
  The example page is generated, not hand-maintained, and this script is what generates it. It
  exists as a script rather than a CLI invocation because the page is deliberately not what the
  CLI writes: it carries the demonstration's key finding
  (`reasonsmith.demo.render_key_finding_html`) beside the report, and no report the CLI produces
  may carry that section, because it is a *second* conformance run — the `ecoa` pack against the
  demonstration's own pipeline, on case `APP-1042` — and says nothing about whatever system a
  report is run on. The section names its own system on the page for that reason.

  Run: `python docs/build_example.py`

What a reader must not break:
  - `BUILD_COMMAND` is what the page prints as its provenance, and it must stay the command that
    reproduces the page byte-for-byte. It lives here, beside the composition it names, because a
    page naming a command that writes a different page is a false provenance claim — the one
    thing `render_html`'s provenance bar exists to refuse.
  - `commit_hash=""` asserts that no commit identifies this page, which is what a page committed
    into the tree it describes must say. It is not a gap to be closed by working harder: the
    commit that carries this page does not exist while the page is being rendered, so a hash
    written here would be the hash of some *other* commit, and the byte-for-byte pin would fail
    the moment the page was committed. `PROVENANCE_NOTE` therefore states the guarantee that can
    be checked instead of the identifier that cannot — the same claim, and the same shape of
    claim, that `docs/nesyarena-conformance-report.md` carries for the same reason.
  - `test_docs_index_html_matches_the_renderer` runs this module rather than composing the page
    a second time, so the committed page, the provenance line it prints and the test agree by
    construction. Do not give the test its own copy of this composition.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reasonsmith.adapters.jsonl import JSONLAdapter  # noqa: E402
from reasonsmith.demo import render_key_finding_html  # noqa: E402
from reasonsmith.examples import SAMPLE_LOG  # noqa: E402
from reasonsmith.report import ConformanceReport, check_conformance  # noqa: E402
from reasonsmith.spec import load_pack  # noqa: E402

#: The provenance the page reports, and the command that reproduces it byte-for-byte.
BUILD_COMMAND = "python docs/build_example.py"

#: What this page can claim about its own origin in place of a commit hash, which it cannot have.
#: The claim is checkable by anyone holding a checkout, which is the property a hash was wanted
#: for, and `test_docs_index_html_matches_the_renderer` is what fails when it stops being true.
PROVENANCE_NOTE = (
    "Re-running that command in any checkout of this repository rewrites this page identically; "
    "test_docs_index_html_matches_the_renderer fails if it does not. No commit hash is named "
    "because a page committed into the repository it describes cannot name the commit that "
    "carries it: that commit does not exist while the page is being rendered."
)

INDEX_HTML = ROOT / "docs" / "report.html"


def example_report() -> ConformanceReport:
    """The Table 7 run behind the page: the committed trace, declared into the high-risk class.

    The domain declaration is `consumer-credit` and nothing else, which is what a credit-scoring
    pipeline decides. It is the whole reason the page's FDA GMLP row now reads *not applicable*:
    that duty is about medical-device software, and this system is not one. Declaring the domain
    of every duty in the pack would have kept the old page and made the declaration meaningless.
    """
    return check_conformance(
        JSONLAdapter(str(SAMPLE_LOG)),
        load_pack("table7"),
        system_name="CreditScoringPipeline",
        system_scope="high-risk",
        system_domains=("consumer-credit",),
    )


#: What the page says about itself, because a fixed exhibit cannot say it by being read.
#:
#: This run is one pack against one committed trace, and it stays that way — it is the artefact
#: behind the paper. Without this passage a reader has no way to tell a capability the engine
#: lacks from one this particular run does not exercise, and every capability named here is on
#: `main` and pointed at the document that shows it. Nothing may be named here that the
#: repository does not have: the claim sits on the most public page this project publishes.
#: It reuses the `limits-card` classes the renderer already defines and adds no rule of its own.
SAMPLE_NOTICE_HTML = (
    '\n'
    '    <section class="limits-card">\n'
    '      <h3 class="limits-header">Demonstration only</h3>\n'
    '      <p class="limits-text">This is a demonstration on frozen synthetic '
    'data &mdash; not evidence about any real '
    'decision.</p>\n'
    '    </section>\n'
)

SCOPE_NOTE_HTML = """
    <section class="limits-card">
      <h3 class="limits-header">What this dossier does not show</h3>
      <p class="limits-text">This is one fixed run — the <code>table7</code> pack against the
      committed sample log — and not the limit of what the engine does. Nothing here reads
      <em>proved</em>, because this system exposes only a decision log; the same duty reaches Z3
      when a system exposes its logic, and the three rungs stand side by side in
      <code>docs/three-systems.md</code>. The engine also renders this same report for one reader
      at a time (<code>--audience regulator</code>, <code>deployer</code>, <code>developer</code>,
      <code>affected-individual</code>, <code>auditor</code>), ships packs beyond this one for the
      GDPR, ECOA and the EU AI Act — including Articles 53 and 55, the duties of providers of
      general-purpose AI models — and accepts engines and packs installed as plug-ins rather than
      vendored (<code>docs/authoring-engines.md</code>).</p>
    </section>
"""


def render() -> str:
    return example_report().render_html(
        commit_hash="",
        command=BUILD_COMMAND,
        extra_section_html=SAMPLE_NOTICE_HTML + render_key_finding_html() + SCOPE_NOTE_HTML,
        provenance_note=PROVENANCE_NOTE,
    )


def main() -> None:
    INDEX_HTML.write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    main()
