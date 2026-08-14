"""Builds the showcase artefacts: two SVGs the README embeds, and `docs/showcase.html`.

What this module is for:
  `docs/report.html` and `docs/audiences.html` are *outputs*. They render one conformance run to
  a reader who already knows what a conformance run is. Nothing introduced the tool visually, so
  the project's own result — a notice stating one reason where the decision's inference used five
  — arrived as a paragraph of prose forty lines above a wall of terminal output. This script
  builds the two artefacts that carry that result instead, and the page they live on.

  Run: `python docs/build_showcase.py`

  Three files, one run:
    - `docs/assets/showcase-figure.svg` — what the applicant was told, beside what the decision
      actually used, with the four reasons the answer did not depend on struck through.
    - `docs/assets/showcase-cast.svg` — two commands and the violation appearing, as an animated
      terminal.
    - `docs/showcase.html` — both of them above the conformance report they were derived from.

What a reader must not break:
  - **Every number is measured, never typed.** `showcase_run()` is `reasonsmith.demo`'s own
    `key_finding_report()` — the same run `docs/build_example.py` composes its key finding from —
    and `_reason_audit` reads the five reasons, the four deleted ones and the decision identifier
    off the certificate that run produced. A figure whose numbers were typed beside the run is a
    second place for them to rot, and this repository has spent enough on stopping exactly that.
  - **The cast is generated from real stdout.** `_terminal_lines` runs the CLI in-process, wraps
    its output at `COLUMNS` the way a terminal does, and keeps whole lines only: an excerpt elides
    lines and says how many, and never edits one. Every timing is synthesised from the row index,
    which is what makes the artefact regenerate byte-for-byte — a hand-recorded cast with real
    timings cannot, and would have rotted the moment the CLI's wording moved.
  - **The cast is a deliberate placeholder.** An outside contribution proposing an interactive
    conformance explorer is open as pull request 120
    (https://github.com/eduardstan/reasonsmith/pull/120), and a TUI is what should eventually
    stand here. This artefact is built to be swapped for one: nothing outside `_cast_svg` and
    `CAST_STEPS` knows how it was made, the README and `docs/showcase.html` reference it only as
    `SHOWCASE_CAST`, and replacing it means replacing one function and one constant.
  - **The SVGs carry their own colours, and that is not a second palette.** The design tokens
    live inside `render.render_html`'s stylesheet and are not exported, which is why
    `docs/audiences.html` is itself a report page. These two files are not: they are embedded in
    `README.md`, on GitHub, outside any stylesheet this repository controls, so they must state
    their own values or render as black text on nothing. They restate the renderer's palette and
    add nothing to it, in both schemes, and every class they define is prefixed — inline SVG
    `<style>` in an HTML document is document-scoped, so an unprefixed class here would restyle
    the report the page carries below.
  - `test_docs_showcase.py` runs this module rather than composing anything a second time, and
    holds all three files byte-for-byte. `commit_hash=""` and `PROVENANCE_NOTE` carry the same
    claim, for the same reason, as `docs/build_example.py`.
"""

from __future__ import annotations

import html
import io
import shlex
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reasonsmith.cli import main as cli_main  # noqa: E402
from reasonsmith.demo import key_finding_report  # noqa: E402
from reasonsmith.report import ConformanceReport  # noqa: E402

#: The provenance the page reports, and the command that reproduces all three files.
BUILD_COMMAND = "python docs/build_showcase.py"

PROVENANCE_NOTE = (
    "Re-running that command in any checkout of this repository rewrites this page and both "
    "figures identically; test_docs_showcase_matches_the_builder fails if it does not. No commit "
    "hash is named because a page committed into the repository it describes cannot name the "
    "commit that carries it: that commit does not exist while the page is being rendered."
)

SHOWCASE_FIGURE = ROOT / "docs" / "assets" / "showcase-figure.svg"
SHOWCASE_CAST = ROOT / "docs" / "assets" / "showcase-cast.svg"
SHOWCASE_HTML = ROOT / "docs" / "showcase.html"

SAMPLE_NOTICE_HTML = (
    '      <h3 class="limits-header">Demonstration only</h3>\n'
    '      <p class="limits-text">This is a demonstration on frozen synthetic '
    'data &mdash; not evidence about any real '
    'decision.</p>\n'
)

#: The clause both halves of the figure are about, and the two duties this repository ships it as.
FORM_DUTY = "ecoa_reg_b_1002_9_b_2_specific_reasons"
CONTENT_DUTY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"


def showcase_run() -> ConformanceReport:
    """The run behind every artefact here: the demonstration's own pipeline against `ecoa`.

    It is `reasonsmith.demo.key_finding_report()` and deliberately not a second run of its own.
    `docs/build_example.py` composes the committed dossier's key finding from that same function,
    so the figure, the cast, this page and the dossier cannot disagree about how many reasons the
    decision used or which of them went unstated.
    """
    return key_finding_report()


def _reason_audit(report: ConformanceReport) -> dict:
    """The measured facts the figure states, read off the certificate the run produced.

    Nothing here is a literal. `stated` is split out of the decision record the system logged —
    the notice's own words — and `deleted` is the certificate's own `missing_reasons`, which is
    the list the deletion probe established the engine's answer does not depend on.
    """
    results = {r.requirement_id: r for r in report.results}
    form = results[FORM_DUTY]
    content = results[CONTENT_DUTY]

    failing = [c for c in content.details["certificates"] if c["certificate_verdict"] == "FAIL"]
    if not failing:
        raise RuntimeError(
            "the showcase run reports no failing certificate, so there is no reason audit to "
            "draw: the figure's whole subject is a decision whose stated reasons were not all "
            "the reasons"
        )
    offending = content.details["offending_trace_segment"][0]

    return {
        "decision_id": str(offending["decision_id"]),
        "stated": [
            part.strip()
            for part in offending["artifact_logs_reason_explanation"].split(";")
            if part.strip()
        ],
        "deleted": [label for cert in failing for label in cert["missing_reasons"]],
        "found": sum(cert["reasons_found"] for cert in failing),
        "form": form,
        "content": content,
    }


# --------------------------------------------------------------------------------------------
# The figure
# --------------------------------------------------------------------------------------------

#: One monospace advance at `FIGURE_MONO_SIZE`, and the row geometry built on it. Every width in
#: the figure is derived from a character count rather than measured, because nothing here may
#: depend on a font being installed: the strike-through spans its whole row rather than its
#: label's rendered width, so a fallback font moves no line off the text it crosses.
FIGURE_MONO_SIZE = 12.0
FIGURE_CHAR = 7.22
FIGURE_ROW = 30.0
FIGURE_ROW_GAP = 8.0
FIGURE_PAD = 16.0

#: The renderer's palette, restated for a file that is read outside the renderer's stylesheet.
#: Light values first, then the `prefers-color-scheme: dark` overrides, exactly as `render_html`
#: orders its own two token blocks — and, exactly as there, the `screen` in the dark query is
#: load-bearing: a dark override reaching print media prints light text on white paper.
_SVG_TOKENS = """
    .{p} {{
      --paper: #f6f5f2; --surface: #fdfdfb; --ink: #23272e; --muted: #5b616b;
      --line: #dcdbd4; --ok: #1c6647; --ok-soft: #e6f2eb; --ok-line: #a9d2be;
      --accent: #ac2318; --accent-soft: #fbe9e7; --accent-line: #e6b0a9;
      --band: #23272e; --band-ink: #fdfdfb; --band-faint: #9aa1ab;
    }}
    @media screen and (prefers-color-scheme: dark) {{
      .{p} {{
        --paper: #1b1d22; --surface: #24272d; --ink: #e8e7e3; --muted: #a3a9b3;
        --line: #383c44; --ok: #6dbd93; --ok-soft: #1d3128; --ok-line: #2f5a45;
        --accent: #f0867c; --accent-soft: #38211f; --accent-line: #6a3730;
        --band: #14161a; --band-ink: #f2f1ed; --band-faint: #8d949e;
      }}
    }}
"""


#: Where a chip's label starts, measured from the chip's own left edge: the tag sits to its left
#: and a strike must begin after the tag rather than through it.
FIGURE_LABEL_X = 78.0

#: The three kinds of chip and the tag each carries. `gap` is the left panel's counterpart of a
#: struck reason on the right — the slot in the notice where a reason the decision used is not.
FIGURE_TAGS = {"live": "stated", "del": "deleted", "gap": "not stated"}


def _figure_row(x: float, y: float, width: float, label: str, kind: str) -> str:
    """One reason, as a chip, struck through where the answer did not depend on it.

    The strike is a line element rather than `text-decoration` and its end is derived from the
    label's character count rather than measured, for the same reason every other width here is:
    nothing may depend on a particular font being installed. It starts after the tag, because a
    line through the word `deleted` reads as the deletion being deleted.
    """
    end = min(x + FIGURE_LABEL_X + len(label) * FIGURE_CHAR + 6.0, x + width - 10.0)
    strike = (
        f'<line class="rs-fig-strike" x1="{x + FIGURE_LABEL_X - 8:.1f}" '
        f'y1="{y + FIGURE_ROW / 2:.1f}" x2="{end:.1f}" y2="{y + FIGURE_ROW / 2:.1f}"/>'
        if kind == "del"
        else ""
    )
    return (
        f'    <g class="rs-fig-chip rs-fig-{kind}">\n'
        f'      <rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{FIGURE_ROW:.1f}" '
        f'rx="5"/>\n'
        f'      <text class="rs-fig-tag" x="{x + 10:.1f}" y="{y + 19.5:.1f}">'
        f"{html.escape(FIGURE_TAGS[kind])}</text>\n"
        f'      <text class="rs-fig-label" x="{x + FIGURE_LABEL_X:.1f}" y="{y + 19.5:.1f}">'
        f"{html.escape(label)}</text>\n"
        f"      {strike}\n"
        f"    </g>\n"
    )


def figure_svg(audit: dict) -> str:
    """What the applicant was told, beside what the decision's own inference used.

    The asymmetry is the argument and it is drawn to scale: one chip on the left, five on the
    right, four of them struck. Everything on it comes out of `audit`.
    """
    widest = max(len(label) for label in audit["stated"] + audit["deleted"])
    body = 78.0 + widest * FIGURE_CHAR + 14.0
    panel = body + 2 * FIGURE_PAD
    margin = 26.0
    gap = 22.0
    width = 2 * panel + gap + 2 * margin

    right_rows = len(audit["stated"]) + len(audit["deleted"])
    panel_body = right_rows * FIGURE_ROW + (right_rows - 1) * FIGURE_ROW_GAP
    panel_top = 116.0
    panel_head = 26.0
    panel_height = panel_head + FIGURE_PAD + panel_body + FIGURE_PAD
    verdicts_top = panel_top + panel_height + 26.0
    height = verdicts_top + 62.0 + 22.0 + 40.0

    left_x, right_x = margin, margin + panel + gap
    rows_top = panel_top + panel_head + FIGURE_PAD

    # The two panels are row-for-row: what the notice said, against what the inference used. Each
    # reason the answer did not depend on leaves an empty slot on the left, drawn rather than left
    # as white space, because a half-empty box reads as a layout accident and a row of empty slots
    # reads as what it is.
    chips = ""
    y = rows_top
    for label in audit["stated"]:
        chips += _figure_row(left_x + FIGURE_PAD, y, body, label, "live")
        chips += _figure_row(right_x + FIGURE_PAD, y, body, label, "live")
        y += FIGURE_ROW + FIGURE_ROW_GAP
    for label in audit["deleted"]:
        chips += _figure_row(left_x + FIGURE_PAD, y, body, "", "gap")
        chips += _figure_row(right_x + FIGURE_PAD, y, body, label, "del")
        y += FIGURE_ROW + FIGURE_ROW_GAP

    form, content = audit["form"], audit["content"]
    verdict_width = (width - 2 * margin - gap) / 2
    verdicts = ""
    for index, (result, half) in enumerate(((form, "form"), (content, "content"))):
        verdict = str(result.verdict)
        kind = "ok" if verdict == "satisfied" else "bad"
        x = margin + index * (verdict_width + gap)
        verdicts += (
            f'    <g class="rs-fig-verdict rs-fig-v-{kind}">\n'
            f'      <rect x="{x:.1f}" y="{verdicts_top:.1f}" width="{verdict_width:.1f}" '
            f'height="62" rx="6"/>\n'
            f'      <text class="rs-fig-vhead" x="{x + 14:.1f}" y="{verdicts_top + 23:.1f}">'
            f"the notice&#8217;s {half} &#183; {html.escape(result.requirement_id)}</text>\n"
            f'      <text class="rs-fig-vverdict" x="{x + 14:.1f}" y="{verdicts_top + 46:.1f}">'
            f"{'&#10003;' if kind == 'ok' else '&#10007;'} {verdict.upper()}</text>\n"
            f'      <text class="rs-fig-vrung" x="{x + verdict_width - 14:.1f}" '
            f'y="{verdicts_top + 46:.1f}" text-anchor="end">'
            f"evidence: {html.escape(str(result.strength))}</text>\n"
            f"    </g>\n"
        )

    caption_y = verdicts_top + 62.0 + 26.0
    deleted = len(audit["deleted"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" \
width="{width:.0f}" height="{height:.0f}" role="img" class="rs-fig" \
aria-label="Decision {html.escape(audit["decision_id"])}: the notice stated \
{len(audit["stated"])} reason, the decision's own inference used {audit["found"]}, and the \
system's answer did not depend on {deleted} of them.">
  <style>
{_SVG_TOKENS.format(p="rs-fig")}
    .rs-fig text {{ font-family: ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif; }}
    .rs-fig-bg {{ fill: var(--paper); }}
    .rs-fig-title {{ fill: var(--ink); font-size: 19px; font-weight: 700; }}
    .rs-fig-sub {{ fill: var(--muted); font-size: 13px; }}
    .rs-fig-panel {{ fill: var(--surface); stroke: var(--line); }}
    .rs-fig-panel-head {{ fill: var(--band); }}
    .rs-fig-panel-title {{ fill: var(--band-ink); font-size: 11.5px; font-weight: 700;
      letter-spacing: 0.08em; }}
    .rs-fig-panel-count {{ fill: var(--band-faint); font-size: 11.5px; }}
    .rs-fig-label {{ fill: var(--ink); font-size: {FIGURE_MONO_SIZE}px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .rs-fig-tag {{ font-size: 9.5px; font-weight: 700; letter-spacing: 0.08em;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .rs-fig-live rect {{ fill: var(--ok-soft); stroke: var(--ok-line); }}
    .rs-fig-live .rs-fig-tag {{ fill: var(--ok); }}
    .rs-fig-del rect {{ fill: var(--accent-soft); stroke: var(--accent-line); }}
    .rs-fig-del .rs-fig-tag {{ fill: var(--accent); }}
    .rs-fig-del .rs-fig-label {{ fill: var(--muted); }}
    .rs-fig-gap rect {{ fill: none; stroke: var(--line); stroke-dasharray: 4 4; }}
    .rs-fig-gap .rs-fig-tag {{ fill: var(--muted); font-weight: 400; }}
    .rs-fig-strike {{ stroke: var(--accent); stroke-width: 1.8; }}
    .rs-fig-v-ok rect {{ fill: var(--ok-soft); stroke: var(--ok-line); }}
    .rs-fig-v-ok .rs-fig-vverdict {{ fill: var(--ok); }}
    .rs-fig-v-bad rect {{ fill: var(--accent-soft); stroke: var(--accent-line); }}
    .rs-fig-v-bad .rs-fig-vverdict {{ fill: var(--accent); }}
    .rs-fig-vhead {{ fill: var(--muted); font-size: 11px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .rs-fig-vverdict {{ font-size: 15px; font-weight: 700; letter-spacing: 0.04em; }}
    .rs-fig-vrung {{ fill: var(--muted); font-size: 11px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .rs-fig-caption {{ fill: var(--ink); font-size: 12.5px; }}
    .rs-fig-caption tspan.em {{ font-weight: 700; }}
  </style>
  <rect class="rs-fig-bg" x="0" y="0" width="{width:.0f}" height="{height:.0f}"/>
  <text class="rs-fig-title" x="{margin:.0f}" y="46">One declined credit application, \
decision {html.escape(audit["decision_id"])}</text>
  <text class="rs-fig-sub" x="{margin:.0f}" y="70">The reasons the adverse-action notice gave \
the applicant, beside the reasons the decision&#8217;s own inference used. reasonsmith re-ran \
that inference and switched each</text>
  <text class="rs-fig-sub" x="{margin:.0f}" y="88">reason off in turn: \
<tspan font-weight="700">{deleted}</tspan> of the {audit["found"]} are reasons the \
system&#8217;s answer did not depend on. Nothing here was read from the decision log \
&#8212; the log records nothing missing.</text>

  <rect class="rs-fig-panel" x="{left_x:.1f}" y="{panel_top:.1f}" width="{panel:.1f}" \
height="{panel_height:.1f}" rx="7"/>
  <path class="rs-fig-panel-head" d="M{left_x:.1f} {panel_top + 7:.1f}a7 7 0 0 1 7 -7h\
{panel - 14:.1f}a7 7 0 0 1 7 7v{panel_head - 7:.1f}h{-panel:.1f}z"/>
  <text class="rs-fig-panel-title" x="{left_x + FIGURE_PAD:.1f}" \
y="{panel_top + 17.5:.1f}">WHAT THE APPLICANT WAS TOLD</text>
  <text class="rs-fig-panel-count" x="{left_x + panel - FIGURE_PAD:.1f}" \
y="{panel_top + 17.5:.1f}" text-anchor="end">{len(audit["stated"])} of {audit["found"]} \
reasons</text>

  <rect class="rs-fig-panel" x="{right_x:.1f}" y="{panel_top:.1f}" width="{panel:.1f}" \
height="{panel_height:.1f}" rx="7"/>
  <path class="rs-fig-panel-head" d="M{right_x:.1f} {panel_top + 7:.1f}a7 7 0 0 1 7 -7h\
{panel - 14:.1f}a7 7 0 0 1 7 7v{panel_head - 7:.1f}h{-panel:.1f}z"/>
  <text class="rs-fig-panel-title" x="{right_x + FIGURE_PAD:.1f}" \
y="{panel_top + 17.5:.1f}">WHAT THE DECISION ACTUALLY USED</text>
  <text class="rs-fig-panel-count" x="{right_x + panel - FIGURE_PAD:.1f}" \
y="{panel_top + 17.5:.1f}" text-anchor="end">{audit["found"]} reasons, \
{deleted} struck</text>

{chips}{verdicts}  <text class="rs-fig-caption" x="{margin:.0f}" y="{caption_y:.1f}">\
<tspan class="em">Both duties are 12 CFR 1002.9(b)(2), on this same decision.</tspan> \
A checker that reads the notice&#8217;s form alone reports it compliant &#8212; and launders \
that gap into a document that reads as authoritative.</text>
</svg>
"""


# --------------------------------------------------------------------------------------------
# The cast
# --------------------------------------------------------------------------------------------

#: How wide the terminal in the cast is. Output is wrapped at this column exactly the way a
#: terminal wraps it — by character count, mid-word — because a `textwrap` rewrap would be an
#: edit of the CLI's own output and this artefact's whole claim is that it is not one.
COLUMNS = 156

#: The two commands the cast runs, and which of each run's lines it keeps.
#:
#: `keep` is matched against the run's own stdout: a `("prefix", text)` rule keeps every line
#: starting with `text`, a `("contains", text)` rule keeps every line holding it, and a
#: `("section", heading)` rule keeps the heading and every line under it up to the next blank.
#: Every rule must match at least one line or `_terminal_lines` raises — the defect
#: `docs/build_readme_transcripts.py` exists to make impossible, in the shape it takes here.
CAST_STEPS = (
    (
        "reasonsmith check --system-module reasonsmith.demo:deployed_credit_system "
        "--pack ecoa --system-name TruncatingCreditSystem",
        (
            ("prefix", "CONFORMANCE REPORT"),
            ("prefix", "system:"),
            ("prefix", "declared "),
            ("prefix", "pack:"),
            ("prefix", "headline:"),
            ("contains", f"{FORM_DUTY} ("),
            ("contains", f"{CONTENT_DUTY} ("),
            ("prefix", "    offending record:"),
        ),
    ),
    (
        "reasonsmith check --system-module reasonsmith.demo:deployed_credit_system "
        "--pack ecoa --system-name TruncatingCreditSystem --audience affected-individual",
        (("section", "WHETHER THOSE WERE ALL THE REASONS"),),
    ),
)

#: 0 is a clean run and 2 is a run reporting a violation. Anything else is a usage error and no
#: cast is drawn from it, on `docs/build_readme_transcripts.py`'s terms.
REPORTING_EXIT_CODES = (0, 2)

#: The cast's geometry and its one synthesised timing. Real timings cannot be byte-pinned, so
#: every row appears at `ROW_SECONDS` times its index and the whole thing loops after `HOLD`.
CAST_MONO_SIZE = 12.0
CAST_CHAR = 7.22
CAST_LINE = 18.0
CAST_PAD = 18.0
CAST_CHROME = 32.0
CAST_ROW_SECONDS = 0.16
CAST_HOLD_SECONDS = 4.0


def stdout_of(command: str) -> tuple[str, int]:
    """The CLI's own stdout for `command`, and its exit code, run in-process from the root."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_main(shlex.split(command)[1:])
    if exit_code not in REPORTING_EXIT_CODES:
        raise RuntimeError(
            f"{command!r} exited {exit_code}, which is a usage or input error rather than a "
            "report, so no cast was drawn from it"
        )
    return buffer.getvalue().rstrip("\n"), exit_code


def _select(lines: list[str], rules: tuple[tuple[str, str], ...]) -> list[int]:
    """The indices of the lines a rule keeps, in the order the run printed them."""
    kept: set[int] = set()
    for kind, text in rules:
        matched = False
        for index, line in enumerate(lines):
            if kind == "prefix" and line.startswith(text):
                kept.add(index)
                matched = True
            elif kind == "contains" and text in line:
                kept.add(index)
                matched = True
            elif kind == "section" and line.strip() == text:
                kept.add(index)
                matched = True
                for offset in range(index + 1, len(lines)):
                    if not lines[offset].strip():
                        break
                    kept.add(offset)
        if not matched:
            raise RuntimeError(
                f"the cast rule {(kind, text)!r} matches no line of the run it is written "
                "against, so the cast would silently show less than it claims"
            )
    return sorted(kept)


def _wrap(line: str) -> list[str]:
    """A terminal's wrap: whole characters at `COLUMNS`, never a rewrap at word boundaries."""
    if not line:
        return [""]
    return [line[start : start + COLUMNS] for start in range(0, len(line), COLUMNS)]


def _terminal_lines() -> list[tuple[str, str]]:
    """Every row of the cast as a `(kind, text)` pair, with elisions counted rather than hidden."""
    rows: list[tuple[str, str]] = []
    for command, rules in CAST_STEPS:
        if rows:
            rows.append(("blank", ""))
        for chunk in _wrap(f"$ {command}"):
            rows.append(("prompt", chunk))
        output, exit_code = stdout_of(command)
        lines = output.splitlines()
        kept = _select(lines, rules)
        previous = -1
        for index in kept:
            elided = index - previous - 1
            if elided > 0:
                rows.append(("elision", f"  ⋯ {elided} line(s) not shown"))
            for chunk in _wrap(lines[index]):
                rows.append(("out", chunk))
            previous = index
        trailing = len(lines) - previous - 1
        if trailing > 0:
            rows.append(("elision", f"  ⋯ {trailing} line(s) not shown"))
        # An annotation and not a command: `echo $?` was never run, so the cast does not draw a
        # prompt it did not execute. The number is the exit code `cli_main` actually returned.
        rows.append(("exit", f"  [exit status {exit_code}]"))
    return rows


def cast_svg(rows: list[tuple[str, str]]) -> str:
    """The rows above, revealed one at a time on a synthesised clock, looping forever.

    A one-shot reveal would have finished playing before most readers scrolled to it, so the
    whole sequence loops: `total` is the cycle, each row's keyframe block turns it on at its own
    fraction of that cycle, and `CAST_HOLD_SECONDS` is the pause on the finished screen.
    """
    width = COLUMNS * CAST_CHAR + 2 * CAST_PAD
    height = CAST_CHROME + CAST_PAD + len(rows) * CAST_LINE + CAST_PAD
    total = len(rows) * CAST_ROW_SECONDS + CAST_HOLD_SECONDS

    keyframes, texts = "", ""
    for index, (kind, text) in enumerate(rows):
        at = 100.0 * (index * CAST_ROW_SECONDS) / total
        keyframes += (
            f"    @keyframes rs-cast-k{index} {{ 0%, {at:.3f}% {{ opacity: 0 }} "
            f"{min(at + 0.4, 100.0):.3f}%, 100% {{ opacity: 1 }} }}\n"
        )
        y = CAST_CHROME + CAST_PAD + (index + 1) * CAST_LINE - 4.5
        texts += (
            f'  <text class="rs-cast-row rs-cast-{kind}" style="animation-name: rs-cast-k{index}" '
            f'x="{CAST_PAD:.1f}" y="{y:.1f}" xml:space="preserve">{html.escape(text)}</text>\n'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" \
width="{width:.0f}" height="{height:.0f}" role="img" class="rs-cast" \
aria-label="Two reasonsmith commands and the violation they report, as a terminal recording.">
  <style>
{_SVG_TOKENS.format(p="rs-cast")}
    .rs-cast-bg {{ fill: var(--band); }}
    .rs-cast-bar {{ fill: var(--band); stroke: var(--band-faint); stroke-opacity: 0.25; }}
    .rs-cast-title {{ fill: var(--band-faint); font-size: 11px; letter-spacing: 0.06em;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .rs-cast-row {{ font-size: {CAST_MONO_SIZE}px; fill: var(--band-ink); opacity: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      animation-duration: {total:.2f}s; animation-iteration-count: infinite;
      animation-timing-function: steps(1, end); }}
    .rs-cast-prompt {{ fill: #7fd6a8; }}
    .rs-cast-exit {{ fill: #f0867c; font-weight: 700; }}
    .rs-cast-elision {{ fill: var(--band-faint); font-style: italic; }}
    @media (prefers-reduced-motion: reduce) {{
      .rs-cast-row {{ animation: none; opacity: 1; }}
    }}
{keyframes}  </style>
  <rect class="rs-cast-bg" x="0" y="0" width="{width:.0f}" height="{height:.0f}" rx="8"/>
  <rect class="rs-cast-bar" x="0.5" y="0.5" width="{width - 1:.0f}" height="{CAST_CHROME:.0f}"/>
  <circle cx="20" cy="16" r="5" fill="#e06c60"/>
  <circle cx="38" cy="16" r="5" fill="#d9ae4e"/>
  <circle cx="56" cy="16" r="5" fill="#6fbf8a"/>
  <text class="rs-cast-title" x="{width / 2:.0f}" y="20" text-anchor="middle">\
reasonsmith &#183; excerpt of two real runs</text>
{texts}</svg>
"""


# --------------------------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------------------------


def showcase_html(audit: dict, figure: str, cast: str) -> str:
    """The showcase section: both artefacts, then the sentence that makes the figure bite.

    The two SVGs are inlined rather than linked so this page stays as self-contained as every
    other document this repository generates — it must open from a `file://` path with no network
    and no sibling asset. Their `<style>` blocks are document-scoped once inlined into HTML,
    which is why every class in them is prefixed.
    """
    deleted = len(audit["deleted"])
    commands = "\n".join(
        f"      <code class=\"rs-showcase-cmd\">$ {html.escape(command)}</code>"
        for command, _ in CAST_STEPS
    )
    return f"""
    <section class="limits-card">
{SAMPLE_NOTICE_HTML}      <h3 class="limits-header">What reasonsmith found</h3>
      <p class="limits-text">A credit system declined application
      <code>{html.escape(audit["decision_id"])}</code> and stated <strong>one</strong> reason. Its
      own inference used <strong>{audit["found"]}</strong>. reasonsmith re-ran that inference,
      switched each reason off in turn, and named the <strong>{deleted}</strong> the system&rsquo;s
      answer did not depend on and its notice never stated &mdash; without reading anything the
      decision log says is missing, because the log records nothing missing.</p>
{figure}
      <p class="limits-text">The two duties above are the two halves of one clause. 12 CFR
      1002.9(b)(2) asks that an adverse-action notice carry a statement of reasons and that the
      reasons it states be the reasons. This repository ships them as two requirements, and on
      this one decision the first is <strong>satisfied</strong> and the second is
      <strong>violated</strong>. That is the finding and not an inconsistency: a checker that
      reads the form alone reports this notice compliant, and launders the gap into a document
      that reads as authoritative.</p>
      <h3 class="limits-header">The two commands</h3>
      <p class="limits-text">Both run against a bare <code>pip install reasonsmith</code>, with no
      checkout and no data of your own. The recording below is an excerpt of their real stdout,
      generated by the same script that generated this page; lines it leaves out are counted where
      they were left out.</p>
      <div class="rs-showcase-cmds">
{commands}
      </div>
{cast}
      <p class="limits-text">The full report both commands print &mdash; every requirement, every
      evidence-strength line and the limits paragraph that travels with them &mdash; is in
      <code>docs/example-output.md</code>, pasted unedited. The report below on this page is that
      same run once more, rendered as a page.</p>
    </section>
    <style>
      .rs-showcase-cmds {{ display: flex; flex-direction: column; gap: var(--space-xs);
        margin: var(--space-sm) 0; }}
      .rs-showcase-cmd {{ display: block; overflow-x: auto; white-space: pre; padding: 0.5rem
        0.7rem; border: 1px solid var(--line); border-radius: var(--radius);
        background: var(--surface); }}
      .rs-fig, .rs-cast {{ display: block; width: 100%; height: auto;
        margin: var(--space-sm) 0; }}
    </style>
"""


def render() -> tuple[str, str, str]:
    """The three files, from one run: the figure, the cast, and the page carrying both."""
    report = showcase_run()
    audit = _reason_audit(report)
    figure = figure_svg(audit)
    cast = cast_svg(_terminal_lines())
    page = report.render_html(
        commit_hash="",
        command=BUILD_COMMAND,
        extra_section_html=showcase_html(audit, figure, cast),
        provenance_note=PROVENANCE_NOTE,
    )
    return figure, cast, page


def main() -> None:
    figure, cast, page = render()
    SHOWCASE_FIGURE.write_text(figure, encoding="utf-8")
    SHOWCASE_CAST.write_text(cast, encoding="utf-8")
    SHOWCASE_HTML.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
