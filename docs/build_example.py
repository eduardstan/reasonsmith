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
    into the tree it describes must say.
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


def render() -> str:
    return example_report().render_html(
        commit_hash="",
        command=BUILD_COMMAND,
        extra_section_html=render_key_finding_html(),
    )


def main() -> None:
    INDEX_HTML.write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    main()
