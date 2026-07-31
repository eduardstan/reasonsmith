"""Conformance report skeleton and unattainable analysis for reasonsmith v0.2.

What this module is for:
  Constructs `ConformanceReport` instances carrying per-requirement verdicts, strengths, source
  clauses, required/missing signals, and headline summaries. Evaluates `check_conformance` and
  static `analyze_unattainable`.

What a reader must not break:
  - No result claims a strength it did not earn (`strength` is `None` when un-evaluated).
    Why this matters: A requirement never evaluated (e.g. unsupported formalism or empty trace)
    is recorded as un-evaluated, never quietly counted as satisfied or given an unearned strength.
  - Combining zero verdicts is `inconclusive`, never vacuously `satisfied`.
    Why this matters: Having checked nothing is not evidence that a requirement holds.
  - The unattainable analysis must NEVER execute the system (`sut.decisions()` is never called).
    Why this matters: Static capability checking acts as a pre-execution safety gate using set
    differences over declared signal names before running decision traces.
  - Every emitted report carries explicit limits on its scope and guarantees.
    Why this matters: Reports assess technical trace evidence against specifications, not legal
    counsel.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reasonsmith.spec import Pack, Requirement, normalize_scope
from reasonsmith.sut import SystemUnderTest, _validate_capability_collection
from reasonsmith.verdict import Strength, Verdict

LIMITS = (
    "This report is not a compliance guarantee and is not legal advice. It assesses system "
    "capability information and trace evidence against formal specifications. Whether these "
    "findings discharge legal duties remains a determination this tool does not make and cannot "
    "make. A requirement reported without a strength was not evaluated or is not applicable, "
    "and no verdict on it should be read from this report. "
    "Recital and guidance items inform how statutory duties are interpreted but create no "
    "obligation of their own; interpretive requirements are evaluated and reported separately, "
    "and are never folded into the binding headline counts. A requirement reported not "
    "applicable was excluded either because no regulatory class was declared for the system at "
    "all, or because the class that was declared is not the one the requirement is limited to. "
    "This tool never infers that class, so an undeclared system is neither placed in scope nor "
    "cleared of the duty: read the declared scope line before reading a not-applicable result."
)

#: Formalisms this build can actually evaluate.
SUPPORTED_FORMALISMS = ("record", "temporal", "logical")


def _is_present(value: Any) -> bool:
    """True when a trace value carries something, not merely a key.

    A missing key, None, a blank string and an empty list/dict/set all mean the system
    emitted nothing for that signal. Only the first of those is caught by a key check,
    and only the first two by a truthiness check on `str(value)` — `str([])` is `"[]"`,
    which is why an empty reason list would otherwise pass as a reason given.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


@dataclass(frozen=True)
class RequirementResult:
    """The conformance result for a single requirement.

    `strength` is `None` when the requirement was not evaluated at all or is not applicable;
    see the module docstring. `signals_missing` names required signals missing from the
    adapter's capability set and is therefore populated only on an unattainable result. Signals
    in that set but absent from a particular trace are a different finding and land in
    `details`.

    `binding` records whether the duty is a legally binding obligation (true) or an
    interpretive recital/guidance item (false), and `scope` records any regulatory class the
    duty is limited to (e.g. 'high-risk'). Both are carried through from the requirement so a
    reader of a single result never has to go back to the pack to know what kind of duty it is.
    """

    requirement_id: str
    source_clause: str
    verdict: Verdict
    strength: Strength | None
    signals_required: tuple[str, ...]
    signals_missing: tuple[str, ...] = ()
    evidence_summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    binding: bool = True
    scope: str = ""

    def __post_init__(self) -> None:
        # Every invariant below compares against the enum members, so a raw string would
        # match none of them and walk past all of them. Normalise first: the guards are the
        # only thing standing between a caller and a result that claims more than it has.
        object.__setattr__(self, "verdict", Verdict.parse(self.verdict))
        if self.strength is not None:
            object.__setattr__(self, "strength", Strength.parse(self.strength))
        object.__setattr__(self, "binding", bool(self.binding))
        object.__setattr__(self, "scope", str(self.scope))
        for name in ("signals_required", "signals_missing"):
            object.__setattr__(self, name, self._signal_names(name))

        # Not applicable is a statement about the duty's reach, not about the system: nothing
        # was checked, so nothing may be claimed. A strength or a missing-signal list here
        # would be a finding smuggled in under a verdict that says none was made.
        if self.verdict == Verdict.NOT_APPLICABLE:
            if self.strength is not None:
                raise ValueError(
                    f"{self.requirement_id}: a not_applicable requirement cannot carry "
                    f"evidence strength {self.strength}"
                )
            if bool(self.signals_missing):
                raise ValueError(
                    f"{self.requirement_id}: a not_applicable requirement cannot have "
                    f"missing signals"
                )

        unattainable = self.strength == Strength.UNATTAINABLE
        if unattainable and self.verdict != Verdict.INCONCLUSIVE:
            raise ValueError(
                f"{self.requirement_id}: an unattainable requirement cannot be reported "
                f"{self.verdict}; the system cannot discharge it as built"
            )
        if bool(self.signals_missing) != unattainable:
            raise ValueError(
                f"{self.requirement_id}: signals_missing is populated exactly when the result "
                f"is unattainable (strength={self.strength}, missing={self.signals_missing})"
            )
        if self.strength is None and self.verdict not in (
            Verdict.INCONCLUSIVE,
            Verdict.NOT_APPLICABLE,
        ):
            raise ValueError(
                f"{self.requirement_id}: a result with no evidence strength cannot be reported "
                f"{self.verdict}"
            )
        unknown = set(self.signals_missing) - set(self.signals_required)
        if unknown:
            raise ValueError(
                f"{self.requirement_id}: signals_missing names signals the requirement does not "
                f"require: {sorted(unknown)}"
            )

    def _signal_names(self, name: str) -> tuple[str, ...]:
        """Coerce a signal field to a tuple of names, refusing shapes that would be misread.

        A bare string is iterable, so signals_required="reasons" would become seven
        single-character signals; a mapping is iterable over its keys, for the same reason
        the capability sites reject one.
        """
        value = getattr(self, name)
        if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
            raise TypeError(
                f"{self.requirement_id}: {name} must be a sequence of signal names, got "
                f"{type(value).__name__}; pass ({value!r},) to name one signal"
            )
        names = tuple(value)
        bad = [s for s in names if not isinstance(s, str) or not s.strip()]
        if bad:
            raise TypeError(
                f"{self.requirement_id}: every entry of {name} must be a non-empty signal "
                f"name, got {bad!r}"
            )
        return names

    @property
    def evaluated(self) -> bool:
        """False when no evidence of any strength was gathered for this requirement."""
        return self.strength is not None

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "source_clause": self.source_clause,
            "verdict": self.verdict.value,
            "strength": self.strength.value if self.strength else None,
            "signals_required": list(self.signals_required),
            "signals_missing": list(self.signals_missing),
            "evidence_summary": self.evidence_summary,
            "details": dict(self.details),
            "binding": self.binding,
            "scope": self.scope,
        }


#: The report categories, in the order they are rendered. Every result falls in exactly one of
#: them, which is what lets the counts reconcile against a total instead of merely summing to
#: something plausible.
_CATEGORY_LABELS = (
    ("proved", "proved"),
    ("probed", "probed"),
    ("observed", "observed"),
    ("violated", "violated"),
    ("inconclusive", "inconclusive"),
    ("not_evaluated", "not evaluated"),
    ("unattainable", "unattainable"),
    ("not_applicable", "not applicable"),
)


#: How each category of `_CATEGORY_LABELS` is drawn in the HTML report: (style class, icon).
#: Keyed by the same keys, so a category added there and forgotten here raises rather than
#: silently rendering no pill.
_CATEGORY_PILL_STYLE = {
    "proved": ("satisfied", "🏆"),
    "probed": ("satisfied", "🔍"),
    "observed": ("satisfied", "👁"),
    "violated": ("violated", "✖"),
    "inconclusive": ("inconclusive", "?"),
    "not_evaluated": ("inconclusive", "−"),
    "unattainable": ("unattainable", "⊘"),
    "not_applicable": ("not-applicable", "⊝"),
}

#: Icon per lattice rung. The rungs and their order come from `Strength` itself, so the drawn
#: lattice cannot disagree with the lattice the verdicts are computed on.
_STRENGTH_ICONS = {
    Strength.UNATTAINABLE: "⊘",
    Strength.OBSERVED: "👁",
    Strength.PROBED: "🔍",
    Strength.PROVED: "🏆",
}

#: Most witness rows the HTML report prints for one violated requirement. A record duty that no
#: record in the trace discharges makes every record offending, so the segment is trace-sized;
#: an unbounded table would inline an entire production decision log into the page. The count of
#: what was elided is always printed with the table, never elided silently.
_WITNESS_ROW_LIMIT = 20


def _source_checkout() -> tuple[str, str]:
    """Identify the git checkout this package was imported from.

    Returns `(commit, state)`, where state is `"clean"`, `"modified"` or `"unknown"`. The
    commit is non-empty only for a clean checkout: naming a commit in a report claims the
    reader can check that commit out and reproduce the run, and neither a tree with
    uncommitted changes nor a checkout git cannot describe can honour that claim.

    The checkout inspected is the one holding this module, not the caller's working
    directory: what a report can attest to is the code that produced it. Git answers about
    whatever repository encloses a directory, which is not the same question — this package
    installed into a `.venv/` of an unrelated project sits inside that project's checkout,
    and an ignored path is absent from `status --porcelain`, so the host tree would read as
    clean and hand back a commit containing none of this code. So the first thing asked is
    whether that repository tracks this very file; if it does not, it cannot describe this
    build at all, in either direction.
    """
    source = Path(__file__).resolve()
    repo = str(source.parent)

    def git(*argv: str) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                ["git", "-C", repo, *argv],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    tracked = git("ls-files", "--error-unmatch", "--", str(source))
    if tracked is None or tracked.returncode != 0:
        return "", "unknown"

    status = git("status", "--porcelain")
    if status is None or status.returncode != 0:
        return "", "unknown"
    if status.stdout.strip():
        return "", "modified"
    head = git("rev-parse", "HEAD")
    if head is None or head.returncode != 0 or not head.stdout.strip():
        return "", "unknown"
    return head.stdout.strip(), "clean"


def _category_counts(
    results: list[RequirementResult], prefix: str = ""
) -> dict[str, int]:
    """Count one set of results into the categories of `_CATEGORY_LABELS`.

    Binding and interpretive results are counted the same way and reported under different
    keys, so the two halves cannot drift into meaning different things.
    """

    def satisfied_at(strength: Strength) -> int:
        return sum(
            1 for r in results if r.verdict == Verdict.SATISFIED and r.strength == strength
        )

    counts = {
        "proved": satisfied_at(Strength.PROVED),
        "probed": satisfied_at(Strength.PROBED),
        "observed": satisfied_at(Strength.OBSERVED),
        "violated": sum(1 for r in results if r.verdict == Verdict.VIOLATED),
        "inconclusive": sum(
            1
            for r in results
            if r.verdict == Verdict.INCONCLUSIVE
            and r.evaluated
            and r.strength != Strength.UNATTAINABLE
        ),
        "not_evaluated": sum(
            1 for r in results if not r.evaluated and r.verdict != Verdict.NOT_APPLICABLE
        ),
        "unattainable": sum(1 for r in results if r.strength == Strength.UNATTAINABLE),
        "not_applicable": sum(1 for r in results if r.verdict == Verdict.NOT_APPLICABLE),
    }
    return {f"{prefix}{key}": value for key, value in counts.items()}


@dataclass(frozen=True)
class ConformanceReport:
    """Report summarizing conformance of a System Under Test against a Pack."""

    pack_id: str
    system_name: str
    results: tuple[RequirementResult, ...]
    system_scope: str | None = None
    limits: str = LIMITS

    @property
    def counts(self) -> dict[str, int]:
        """Per-category counts, split so no single number can mean two things.

        `total` is every requirement reported, binding and interpretive alike — a JSON
        consumer reading it is never told a shorter pack was run than was. The unprefixed
        category counts cover the `binding_total` binding requirements only: a recital or a
        guidance item informs how a statutory duty is read but creates no obligation of its
        own, so counting one as compliance evidence would overstate what was established.
        Interpretive results are reported under the `interpretive_` keys, never dropped.

        Each half is an exact partition of its own total, so `binding_total` and
        `interpretive_total` each reconcile against the eight categories below and sum to
        `total`. `proved`/`probed`/`observed` count *satisfied* requirements at that strength,
        so a requirement is never counted as evidence for a property it does not have.
        """
        binding_res = [r for r in self.results if r.binding]
        interp_res = [r for r in self.results if not r.binding]
        return {
            "total": len(self.results),
            "binding_total": len(binding_res),
            **_category_counts(binding_res),
            "interpretive_total": len(interp_res),
            **_category_counts(interp_res, "interpretive_"),
        }

    @property
    def headline(self) -> str:
        """Headline count line, naming each half in words rather than leaving it inferred.

        E.g. '6 requirements · 4 binding: 2 observed, 2 unattainable · 2 interpretive:
        2 observed'. A reader who sees only the leading number still learns from the following
        clauses how many of those requirements are duties and how many merely interpret one.
        """
        counts = self.counts
        parts = [f"{counts['total']} requirements"]
        for total_key, prefix, noun in (
            ("binding_total", "", "binding"),
            ("interpretive_total", "interpretive_", "interpretive"),
        ):
            if not counts[total_key]:
                continue
            categories = [
                f"{counts[prefix + key]} {label}"
                for key, label in _CATEGORY_LABELS
                if counts[prefix + key]
            ]
            detail = f": {', '.join(categories)}" if categories else ""
            parts.append(f"{counts[total_key]} {noun}{detail}")
        return " · ".join(parts)

    def render_text(self) -> str:
        """Readable text rendering of the report."""
        lines = [
            "CONFORMANCE REPORT",
            f"system: {self.system_name}",
            f"declared scope: {self.system_scope or 'undeclared'}",
            f"pack: {self.pack_id}",
            f"headline: {self.headline}",
            "",
            "REQUIREMENT FINDINGS:",
        ]
        for r in self.results:
            if r.verdict == Verdict.NOT_APPLICABLE:
                tier = "NOT APPLICABLE"
            else:
                tier = r.strength.value.upper() if r.strength else "NOT EVALUATED"
            interp_tag = " [INTERPRETIVE]" if not r.binding else ""
            lines.append(
                f"  [{tier}]{interp_tag} {r.requirement_id} ({r.source_clause}): {r.verdict.value}"
            )
            lines.append(f"    requires: {', '.join(r.signals_required)}")
            if r.scope:
                lines.append(f"    scope limit: {r.scope}")
            if r.signals_missing:
                lines.append(f"    MISSING SIGNALS: {', '.join(r.signals_missing)}")
            absent = r.details.get("signals_absent_from_trace")
            if absent:
                lines.append(f"    ABSENT FROM TRACE: {', '.join(absent)}")
            if r.evidence_summary:
                lines.append(f"    summary: {r.evidence_summary}")
        lines.extend(["", "LIMITS OF THIS REPORT", f"  {self.limits}"])
        return "\n".join(lines)

    def render_html(
        self,
        commit_hash: str | None = None,
        command: str | None = None,
        extra_section_html: str | None = None,
    ) -> str:
        """Self-contained HTML conformance report rendering.

        Zero external dependencies, network-free, printable on A4. Presents the
        evidence strength lattice, counts split by binding vs interpretive,
        and visually distinguishes unattainable architectural gaps from violated trace failures.

        The provenance bar states what can be established and nothing more. `commit_hash`
        left `None` means "work it out": the commit is named only when the checkout this
        package was imported from is clean (see `_source_checkout`), and a modified or
        unidentifiable checkout is reported as such rather than given a hash it would not
        reproduce. Passing an empty `commit_hash` asserts no commit identifies this report,
        which is what a report committed into the tree it describes must say. `command` is
        never guessed: an unsupplied command is left out, because a command line the report
        invented is not provenance.

        `extra_section_html` is inserted verbatim below the headline and is empty unless a
        caller supplies it. Nothing derived from anything but this report's own results may be
        rendered by default: a narrative about another system's decision, sitting inside a
        document handed to an auditor, is exactly the false completeness this package refuses.
        The caller that passes it owns the claim it makes and escapes its own content.
        """
        import html

        if commit_hash is None:
            commit_hash, tree_state = _source_checkout()
        else:
            tree_state = "clean" if commit_hash else "unknown"

        counts = self.counts
        sys_name = html.escape(self.system_name)
        pack_name = html.escape(self.pack_id)
        sys_scope = html.escape(self.system_scope or "undeclared")
        headline_esc = html.escape(self.headline)
        limits_esc = html.escape(self.limits)
        c_short_esc = html.escape(commit_hash[:7]) if commit_hash else ""

        if c_short_esc:
            origin = f"from commit <code>{c_short_esc}</code>"
        elif tree_state == "modified":
            origin = "from a modified working tree, which no commit identifies"
        else:
            origin = "without an identified source commit"
        cmd_part = f" Command: <code>{html.escape(command)}</code>" if command else ""
        provenance_html = (
            '<div class="provenance-bar">'
            f'<strong>Report Provenance:</strong> Generated {origin}.{cmd_part}'
            '</div>'
        )

        def render_pill_group(prefix: str) -> str:
            pills = []
            for key, label in _CATEGORY_LABELS:
                style_key, icon = _CATEGORY_PILL_STYLE[key]
                val = counts.get(f"{prefix}{key}", 0)
                if val > 0:
                    pills.append(
                        f'<span class="stat-pill verdict-{style_key}">'
                        f'<span aria-hidden="true">{icon}</span> {val} {html.escape(label)}</span>'
                    )
            return "".join(pills) if pills else '<span class="text-muted">None</span>'

        binding_pills = render_pill_group("")
        interp_pills = render_pill_group("interpretive_")
        extra_section = extra_section_html or ""

        req_html_blocks = []
        for r in self.results:
            req_id = html.escape(r.requirement_id)
            source = html.escape(r.source_clause)
            summary = html.escape(r.evidence_summary)
            sc_esc = html.escape(r.scope)
            scope_tag = f'<span class="badge badge-scope">Scope: {sc_esc}</span>' if r.scope else ""
            binding_tag = (
                '<span class="badge badge-binding">Binding</span>'
                if r.binding
                else '<span class="badge badge-interpretive">Interpretive</span>'
            )

            # Verdict badge & card styling
            is_unattainable = r.strength == Strength.UNATTAINABLE
            if is_unattainable:
                v_class = "verdict-unattainable"
                v_badge = (
                    '<span class="badge verdict-unattainable">'
                    '<span aria-hidden="true">⊘</span> UNATTAINABLE</span>'
                )
            elif r.verdict == Verdict.SATISFIED:
                v_class = "verdict-satisfied"
                v_badge = (
                    '<span class="badge verdict-satisfied">'
                    '<span aria-hidden="true">✓</span> SATISFIED</span>'
                )
            elif r.verdict == Verdict.VIOLATED:
                v_class = "verdict-violated"
                v_badge = (
                    '<span class="badge verdict-violated">'
                    '<span aria-hidden="true">✖</span> VIOLATED</span>'
                )
            elif r.verdict == Verdict.NOT_APPLICABLE:
                v_class = "verdict-not-applicable"
                v_badge = (
                    '<span class="badge verdict-not-applicable">'
                    '<span aria-hidden="true">⊝</span> NOT APPLICABLE</span>'
                )
            else:
                v_class = "verdict-inconclusive"
                v_badge = (
                    '<span class="badge verdict-inconclusive">'
                    '<span aria-hidden="true">?</span> INCONCLUSIVE</span>'
                )

            # Strength Lattice render
            cur_rank = r.strength.rank if r.strength is not None else None
            lattice_spans = []
            for step in sorted(Strength, key=lambda s: s.rank):
                if r.strength is step:
                    active_cls = f"active-{step.value}"
                elif (
                    cur_rank is not None
                    and cur_rank > step.rank
                    and step is not Strength.UNATTAINABLE
                ):
                    active_cls = "passed"
                else:
                    active_cls = ""

                lattice_spans.append(
                    f'<span class="lattice-step {active_cls}">'
                    f'<span aria-hidden="true">{_STRENGTH_ICONS[step]}</span> {step.value}</span>'
                )

            lattice_html = (
                '<div class="lattice-track">'
                + '<span class="lattice-arrow">&rarr;</span>'.join(lattice_spans)
                + "</div>"
            )

            # Signal tags
            req_signals = "".join(
                f'<span class="signal-tag">{html.escape(s)}</span>' for s in r.signals_required
            )

            details_html = ""
            if r.signals_missing:
                missing_tags = "".join(
                    f'<span class="signal-tag missing">{html.escape(s)}</span>'
                    for s in r.signals_missing
                )
                details_html += (
                    '<div class="callout-box callout-unattainable">'
                    "<strong>UNATTAINABLE AS BUILT — Missing Capability Signals:</strong><br>"
                    f"{missing_tags}"
                    '<div class="callout-note">The system declares no capability to emit these '
                    "signals. No testing trace can satisfy this requirement.</div>"
                    "</div>"
                )

            absent_signals = r.details.get("signals_absent_from_trace")
            if absent_signals:
                absent_tags = "".join(
                    f'<span class="signal-tag absent">{html.escape(s)}</span>'
                    for s in absent_signals
                )
                details_html += (
                    '<div class="callout-box callout-violated">'
                    "<strong>VIOLATED IN TRACE — Required Signals Absent from Decision Log:"
                    f"</strong><br>{absent_tags}"
                    "</div>"
                )

            # Counterexample / witness rendering for ObservedEngine violations
            offending_segment = r.details.get("offending_trace_segment")
            violation_indices = r.details.get("violation_step_indices")
            if offending_segment and violation_indices:
                witnesses = list(zip(violation_indices, offending_segment, strict=False))
                shown = witnesses[:_WITNESS_ROW_LIMIT]
                rows = []
                for idx, record in shown:
                    rec_str = ", ".join(
                        f"{html.escape(str(k))}: {html.escape(str(v))}" for k, v in record.items()
                    )
                    rows.append(f"<tr><td>Step {idx}</td><td><code>{rec_str}</code></td></tr>")
                witness_table = (
                    '<table class="witness-table">'
                    "<thead><tr><th>Trace Step</th><th>Decision Record Witness</th>"
                    f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
                )
                if len(shown) < len(witnesses):
                    counted = (
                        f"showing the first {len(shown)} of {len(witnesses)} offending records"
                    )
                    truncation_note = (
                        f'<div class="callout-note">Witness truncated for display: {counted}. '
                        "The report is a witness that the requirement is violated, not the "
                        "complete list of decisions that violate it; read the full segment from "
                        "<code>offending_trace_segment</code> in the JSON output.</div>"
                    )
                else:
                    plural = "" if len(witnesses) == 1 else "s"
                    counted = f"all {len(witnesses)} offending record{plural}"
                    truncation_note = ""
                details_html += (
                    '<div class="callout-box callout-violated">'
                    "<strong>VIOLATED IN TRACE — Execution Counterexample Witness "
                    f"({counted}):</strong>"
                    f"{witness_table}{truncation_note}"
                    "</div>"
                )

            counterexample = r.details.get("counterexample")
            if counterexample and r.verdict == Verdict.VIOLATED:
                ce_str = ", ".join(
                    f"{html.escape(str(k))}: {html.escape(str(v))}"
                    for k, v in counterexample.items()
                )
                details_html += (
                    '<div class="callout-box callout-violated">'
                    "<strong>VIOLATED — Formal Counterexample Input:</strong><br>"
                    f"<code>{ce_str}</code>"
                    "</div>"
                )

            req_html_blocks.append(f"""
        <article class="req-card {v_class}">
          <header class="req-card-header">
            <div class="req-title-group">
              <span class="req-id">{req_id}</span>
              <span class="req-clause">({source})</span>
            </div>
            <div class="badge-group">
              {binding_tag}
              {scope_tag}
              {v_badge}
            </div>
          </header>
          <div class="lattice-container">
            <span class="lattice-label">Strength Lattice:</span>
            {lattice_html}
          </div>
          <div class="req-card-body">
            <div class="signal-list">
              <strong>Requires Signals:</strong> {req_signals}
            </div>
            <div class="evidence-summary">{summary}</div>
            {details_html}
          </div>
        </article>""")

        req_section_html = "\n".join(req_html_blocks)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reasonsmith Conformance Report - {sys_name}</title>
  <style>
    :root {{
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --color-slate-50: #f8fafc;
      --color-slate-100: #f1f5f9;
      --color-slate-200: #e2e8f0;
      --color-slate-300: #cbd5e1;
      --color-slate-600: #475569;
      --color-slate-700: #334155;
      --color-slate-800: #1e293b;
      --color-slate-900: #0f172a;

      --color-satisfied-bg: #ecfdf5;
      --color-satisfied-border: #a7f3d0;
      --color-satisfied-text: #065f46;

      --color-violated-bg: #fef2f2;
      --color-violated-border: #fca5a5;
      --color-violated-text: #991b1b;
      --color-violated-accent: #dc2626;

      --color-unattainable-bg: #fffbeb;
      --color-unattainable-border: #fde68a;
      --color-unattainable-text: #92400e;
      --color-unattainable-accent: #d97706;

      --color-inconclusive-bg: #f1f5f9;
      --color-inconclusive-border: #cbd5e1;
      --color-inconclusive-text: #334155;

      --color-not-applicable-bg: #f8fafc;
      --color-not-applicable-border: #e2e8f0;
      --color-not-applicable-text: #64748b;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      background-color: var(--color-slate-50);
      color: var(--color-slate-900);
      line-height: 1.5;
      padding: 2rem 1rem;
    }}

    .container {{
      max-width: 1000px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid var(--color-slate-200);
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
      overflow: hidden;
    }}

    .report-header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #ffffff;
      padding: 2rem;
      border-bottom: 3px solid #3b82f6;
    }}
    .brand-title {{
      font-size: 0.85rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #60a5fa;
      margin-bottom: 0.25rem;
    }}
    .main-title {{
      font-size: 1.75rem;
      font-weight: 800;
      line-height: 1.2;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.15);
    }}
    .meta-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
    }}
    .meta-value {{
      font-size: 0.95rem;
      font-weight: 600;
      color: #f8fafc;
      font-family: var(--font-mono);
    }}

    .headline-banner {{
      background: #eff6ff;
      border-left: 4px solid #2563eb;
      padding: 1rem 1.5rem;
      margin: 1.5rem;
      border-radius: 6px;
    }}
    .headline-title {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #1e40af;
      margin-bottom: 0.25rem;
    }}
    .headline-text {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #1e3a8a;
    }}
    .provenance-bar {{
      font-size: 0.8rem;
      color: #1e40af;
      margin-top: 0.5rem;
      padding-top: 0.5rem;
      border-top: 1px solid #bfdbfe;
      font-family: var(--font-mono);
    }}

    .dashboard-section {{
      padding: 0 1.5rem 1.5rem 1.5rem;
    }}
    .split-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }}
    @media (max-width: 768px) {{
      .split-grid {{ grid-template-columns: 1fr; }}
    }}
    .split-card {{
      border: 1px solid var(--color-slate-200);
      border-radius: 8px;
      padding: 1.25rem;
      background: #fafafa;
    }}
    .split-card-header {{
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--color-slate-200);
      display: flex;
      justify-content: space-between;
      color: var(--color-slate-700);
    }}
    .pill-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .stat-pill {{
      font-size: 0.8rem;
      font-weight: 600;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }}

    .section-title {{
      font-size: 1.25rem;
      font-weight: 700;
      padding: 1rem 1.5rem 0.5rem 1.5rem;
      border-top: 1px solid var(--color-slate-200);
      color: var(--color-slate-800);
    }}
    .req-list {{
      padding: 1rem 1.5rem 1.5rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}

    .req-card {{
      border: 1px solid var(--color-slate-200);
      border-radius: 8px;
      background: #ffffff;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .req-card.verdict-violated {{
      border: 2px solid var(--color-violated-accent);
      background: #fffafa;
    }}
    .req-card.verdict-unattainable {{
      border: 2px dashed var(--color-unattainable-accent);
      background: #fffdf5;
    }}
    .req-card.verdict-satisfied {{
      border-left: 4px solid #059669;
    }}

    .req-card-header {{
      padding: 1rem 1.25rem;
      background: #f8fafc;
      border-bottom: 1px solid var(--color-slate-200);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .req-title-group {{ flex: 1; }}
    .req-id {{
      font-size: 1rem;
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--color-slate-900);
    }}
    .req-clause {{
      font-size: 0.85rem;
      color: var(--color-slate-600);
      margin-left: 0.5rem;
    }}
    .badge-group {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}

    .badge {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }}
    .badge-binding {{ background: #e0e7ff; color: #3730a3; }}
    .badge-interpretive {{ background: #f3e8ff; color: #6b21a8; }}
    .badge-scope {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}

    .verdict-satisfied {{
      background: var(--color-satisfied-bg);
      color: var(--color-satisfied-text);
      border: 1px solid var(--color-satisfied-border);
    }}
    .verdict-violated {{
      background: var(--color-violated-bg);
      color: var(--color-violated-text);
      border: 1px solid var(--color-violated-border);
    }}
    .verdict-unattainable {{
      background: var(--color-unattainable-bg);
      color: var(--color-unattainable-text);
      border: 1px dashed var(--color-unattainable-border);
    }}
    .verdict-inconclusive {{
      background: var(--color-inconclusive-bg);
      color: var(--color-inconclusive-text);
      border: 1px solid var(--color-inconclusive-border);
    }}
    .verdict-not-applicable {{
      background: var(--color-not-applicable-bg);
      color: var(--color-not-applicable-text);
      border: 1px solid var(--color-not-applicable-border);
    }}

    .lattice-container {{
      padding: 0.6rem 1.25rem;
      background: #f1f5f9;
      border-bottom: 1px solid var(--color-slate-200);
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .lattice-label {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-slate-600);
      white-space: nowrap;
    }}
    .lattice-track {{
      display: flex;
      align-items: center;
      gap: 0.3rem;
      flex-wrap: wrap;
    }}
    .lattice-step {{
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      color: #94a3b8;
      background: #ffffff;
      border: 1px solid #e2e8f0;
    }}
    .lattice-step.active-proved {{
      background: #059669; color: #ffffff; border-color: #047857; font-weight: 700;
    }}
    .lattice-step.active-probed {{
      background: #2563eb; color: #ffffff; border-color: #1d4ed8; font-weight: 700;
    }}
    .lattice-step.active-observed {{
      background: #3b82f6; color: #ffffff; border-color: #2563eb; font-weight: 700;
    }}
    .lattice-step.active-unattainable {{
      background: #d97706; color: #ffffff; border-color: #b45309;
      font-weight: 700; border-style: dashed;
    }}
    .lattice-step.passed {{ background: #e2e8f0; color: #334155; }}
    .lattice-arrow {{ color: #cbd5e1; font-size: 0.75rem; }}

    .req-card-body {{ padding: 1.25rem; }}
    .signal-list {{ margin-bottom: 0.75rem; font-size: 0.85rem; }}
    .signal-tag {{
      font-family: var(--font-mono);
      background: #f1f5f9;
      color: #334155;
      padding: 0.15rem 0.4rem;
      border-radius: 3px;
      border: 1px solid #e2e8f0;
      font-size: 0.8rem;
      display: inline-block;
      margin: 0.1rem;
    }}
    .signal-tag.missing {{
      background: #fef3c7; color: #92400e; border-color: #fde68a; font-weight: 600;
    }}
    .signal-tag.absent {{
      background: #fee2e2; color: #991b1b; border-color: #fca5a5; font-weight: 600;
    }}

    .evidence-summary {{
      font-size: 0.9rem; color: var(--color-slate-700); margin-top: 0.5rem; line-height: 1.5;
    }}
    .callout-box {{ margin-top: 1rem; padding: 1rem; border-radius: 6px; font-size: 0.85rem; }}
    .callout-unattainable {{ background: #fffbeb; border: 1px dashed #fde68a; color: #78350f; }}
    .callout-violated {{ background: #fef2f2; border: 1px solid #fca5a5; color: #7f1d1d; }}
    .callout-note {{ font-size: 0.75rem; margin-top: 0.5rem; color: #92400e; font-style: italic; }}

    .witness-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.75rem;
      font-size: 0.8rem;
      font-family: var(--font-mono);
    }}
    .witness-table th, .witness-table td {{
      border: 1px solid var(--color-slate-300);
      padding: 0.4rem 0.6rem;
      text-align: left;
    }}
    .witness-table th {{ background: #f1f5f9; color: #334155; font-weight: 700; }}
    .witness-table tr:nth-child(even) {{ background: #f8fafc; }}

    .limits-card {{
      margin: 1.5rem;
      padding: 1.25rem;
      background: #f8fafc;
      border: 1px solid var(--color-slate-300);
      border-radius: 8px;
    }}
    .limits-header {{
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-slate-700);
      margin-bottom: 0.5rem;
    }}
    .limits-text {{ font-size: 0.8rem; color: var(--color-slate-600); line-height: 1.6; }}

    @media print {{
      body {{ background: #ffffff; padding: 0; color: #000000; }}
      .container {{ border: none; box-shadow: none; max-width: 100%; }}
      .report-header {{
        background: #1e293b !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      .req-card {{ break-inside: avoid; border: 1px solid #000000 !important; }}
      .req-card.verdict-violated {{ border: 2px solid #dc2626 !important; }}
      .req-card.verdict-unattainable {{ border: 2px dashed #d97706 !important; }}
      .witness-table th, .witness-table td {{ border-color: #000000 !important; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="report-header">
      <div class="header-top">
        <div>
          <div class="brand-title">reasonsmith audit engine</div>
          <h1 class="main-title">Conformance Report</h1>
        </div>
      </div>
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">System under test</span>
          <span class="meta-value">{sys_name}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Declared Scope</span>
          <span class="meta-value">{sys_scope}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Regulation Pack</span>
          <span class="meta-value">{pack_name}</span>
        </div>
      </div>
    </header>

    <div class="headline-banner">
      <div class="headline-title">Executive Headline Summary</div>
      <div class="headline-text">{headline_esc}</div>
      {provenance_html}
    </div>

    {extra_section}

    <section class="dashboard-section">
      <div class="split-grid">
        <div class="split-card">
          <div class="split-card-header">
            <span>Binding Duties</span>
            <span>{counts['binding_total']} total</span>
          </div>
          <div class="pill-group">
            {binding_pills}
          </div>
        </div>
        <div class="split-card">
          <div class="split-card-header">
            <span>Interpretive Items</span>
            <span>{counts['interpretive_total']} total</span>
          </div>
          <div class="pill-group">
            {interp_pills}
          </div>
        </div>
      </div>
    </section>

    <h2 class="section-title">Requirement Findings</h2>
    <main class="req-list">
{req_section_html}
    </main>

    <section class="limits-card">
      <h3 class="limits-header">Limits of this report</h3>
      <p class="limits-text">{limits_esc}</p>
    </section>
  </div>
</body>
</html>
"""


    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "system_scope": self.system_scope,
            "pack_id": self.pack_id,
            "headline": self.headline,
            "counts": self.counts,
            "results": [r.to_dict() for r in self.results],
            "limits": self.limits,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON representation following house pattern."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def analyze_unattainable(req: Requirement, sut: SystemUnderTest) -> tuple[bool, tuple[str, ...]]:
    """Perform the unattainable analysis for a requirement against a SUT.

    COMPUTED WITHOUT EXECUTING THE SYSTEM (`sut.decisions()` is never called here): the answer
    is the set difference between the signals the requirement needs and the capability set the
    SUT adapter supplies. Most adapters require an explicit system declaration. A trace-derived
    adapter is weaker: its result is limited to that supplied trace rather than stated as a
    property of the system as built.

    Returns:
        (is_unattainable, missing_signals) — missing_signals is sorted and never empty when
        is_unattainable is True.
    """
    declared = sut.capabilities()
    _validate_capability_collection(declared, f"{type(sut).__name__}.capabilities() must return")
    missing = tuple(sorted(set(req.requires) - set(declared)))
    return bool(missing), missing


def _read_trace(sut: SystemUnderTest) -> list[dict[str, Any]]:
    """Read a SUT's decision trace, refusing a shape that would be read record by record.

    A system returning one record instead of a list of records yields its key strings, which
    would otherwise blow up deep inside the signal check with no mention of the system that
    caused it. Shared by both places a trace is read, so neither can drift from the other.
    """
    records = list(sut.decisions())
    for rec in records:
        if not isinstance(rec, Mapping):
            raise TypeError(
                f"{type(sut).__name__}.decisions() must return an iterable of decision records, "
                f"each a mapping of signal name to value; got {type(rec).__name__}"
            )
    return records


def _unattainable_result(
    req: Requirement, missing: tuple[str, ...], sut: SystemUnderTest | None = None
) -> RequirementResult:
    """The unattainable result, worded for how the capability set was established.

    A system that declares its capabilities is speaking about itself as built. An adapter
    that infers them from a supplied trace is not: a longer trace could carry the signal, so
    the result says what it was read from rather than putting a claim in the system's mouth.
    """
    if getattr(sut, "capability_basis", "declared") == "trace":
        summary = (
            "Unattainable on the evidence supplied: no record in the supplied decision trace "
            f"carries a value for {', '.join(missing)}, and the system declared no "
            "capabilities, so nothing here can discharge this requirement. Read from that "
            "trace alone; a longer trace could show the system emitting these signals."
        )
    else:
        summary = (
            "Unattainable as built: the system declares no capability to emit "
            f"{', '.join(missing)}, so no amount of testing can discharge this requirement. "
            "Determined from declared capabilities alone; the system was not executed."
        )
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=Strength.UNATTAINABLE,
        signals_required=tuple(req.requires),
        signals_missing=missing,
        evidence_summary=summary,
        binding=req.binding,
        scope=req.scope,
    )


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
    system_scope: str | None = None,
) -> RequirementResult:
    """Evaluate a single requirement against a SUT.

    A requirement limited to a regulatory class is answered first: if the system's declared
    class is not that class, the duty does not reach this system and the result is
    NOT_APPLICABLE with no strength, because nothing about the system was checked. The class
    is never inferred — an undeclared system is not silently treated as in scope, and the
    result says which of the two it was. A declared class outside `REGULATORY_CLASSES` is
    refused rather than answered, here as well as in `check_conformance`, so a caller reaching
    this function directly gets the same guarantee.

    If the adapter's capability set does not cover the required signals, returns UNATTAINABLE
    without executing the SUT. Otherwise `records` is used as the decision trace; when it is
    None the trace is fetched from the SUT, so callers holding a trace already can avoid
    re-running the system once per requirement.
    """
    if system_scope is None:
        system_scope = getattr(sut, "system_scope", getattr(sut, "declared_scope", None))

    sys_scope_norm = normalize_scope(system_scope, "declared system scope")

    req_scope_norm = normalize_scope(req.scope)

    if req_scope_norm:
        if not sys_scope_norm or sys_scope_norm != req_scope_norm:
            clause = f"{req.source_document} {req.article_clause}"
            desc = f"declared as {system_scope!r}" if sys_scope_norm else "undeclared"
            return RequirementResult(
                requirement_id=req.id,
                source_clause=clause,
                verdict=Verdict.NOT_APPLICABLE,
                strength=None,
                signals_required=tuple(req.requires),
                evidence_summary=(
                    f"Not applicable: requirement scope is {req.scope!r}, but system regulatory "
                    f"class is {desc}. reasonsmith never infers a system's regulatory class."
                ),
                binding=req.binding,
                scope=req.scope,
            )

    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return _unattainable_result(req, missing, sut)

    clause = f"{req.source_document} {req.article_clause}"

    if req.formalism not in SUPPORTED_FORMALISMS:
        # Declaring the signals is not evidence that the property holds, and this build has no
        # engine for this formalism to establish one. Say so.
        return RequirementResult(
            requirement_id=req.id,
            source_clause=clause,
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Not evaluated: no engine in this build checks a {req.formalism!r} requirement. "
                "The system declares the signals this requirement needs, so it is attainable, "
                "but nothing here establishes that the property holds."
            ),
            binding=req.binding,
            scope=req.scope,
        )

    if req.formalism in ("record", "temporal") and records is None:
        records = _read_trace(sut)

    if req.formalism == "record":
        from reasonsmith.engines.record import RecordEngine
        return RecordEngine.evaluate(req, sut, records or [])
    elif req.formalism == "temporal":
        from reasonsmith.engines.observed import ObservedEngine
        return ObservedEngine.evaluate(req, sut, records or [])
    elif req.formalism == "logical":
        from reasonsmith.engines.proved import ProvedEngine
        return ProvedEngine.evaluate(req, sut, records)

    raise NotImplementedError(
        f"{req.formalism!r} is listed in SUPPORTED_FORMALISMS but no engine here evaluates it. "
        "Widen SUPPORTED_FORMALISMS when the engine lands, not before."
    )


def check_conformance(
    sut: SystemUnderTest,
    pack: Pack,
    system_name: str = "SUT",
    system_scope: str | None = None,
) -> ConformanceReport:
    """Check conformance of a SUT against all requirements in a Pack.

    Applicability and unattainability are resolved for every requirement first, and the
    decision trace is read at most once — and not at all when nothing in the pack is
    applicable, attainable and checkable here. That keeps "the unattainable analysis does not
    run the system" a property of the code rather than of the order the requirements happen to
    appear in.

    A declared class outside `REGULATORY_CLASSES` is refused before any of that, so a
    misspelling cannot pass for a system that is simply out of scope. A class the vocabulary
    knows but this pack does not target is not an error: the system is genuinely out of scope
    for those duties, and they are reported not applicable as a declared mismatch.
    """
    if system_scope is None:
        system_scope = getattr(sut, "system_scope", getattr(sut, "declared_scope", None))
    sys_norm = normalize_scope(system_scope, "declared system scope")
    eval_plan = []
    for req in pack.requirements:
        req_norm = normalize_scope(req.scope)
        applicable = not req_norm or (bool(sys_norm) and sys_norm == req_norm)
        if not applicable:
            eval_plan.append((req, False, False, ()))
        else:
            eval_plan.append((req, True, *analyze_unattainable(req, sut)))

    needs_trace = any(
        applicable and not is_unattainable and req.formalism in ("record", "temporal")
        for req, applicable, is_unattainable, _ in eval_plan
    )

    # When nothing needs the trace this stays empty and is never read: the only requirements
    # left are out of scope, unattainable, or of a formalism no engine here checks.
    records = _read_trace(sut) if needs_trace else []

    # `records` is a list by now, so evaluate_requirement never re-reads the trace; it
    # re-derives the applicability and unattainable results itself, which is why there is no
    # branch here.
    results = [
        evaluate_requirement(req, sut, records, system_scope=system_scope)
        for req in pack.requirements
    ]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        system_scope=system_scope,
        results=tuple(results),
    )
