"""Conformance report skeleton and unattainable analysis for reasonsmith v0.2.

What this module is for:
  Constructs `ConformanceReport` instances carrying per-requirement verdicts, strengths, source
  clauses, required/missing signals, and headline summaries. Evaluates `check_conformance` and
  static `analyze_unattainable`.

What a reader must not break:
  - No result claims a strength it did not earn (`strength` is `None` when un-evaluated).
    Why this matters: A requirement never evaluated (e.g. unsupported formalism or empty trace)
    is recorded as un-evaluated, never quietly counted as satisfied or given an unearned strength.
  - `_engine_ladder` decides which engines may discharge a requirement from two things: the
    fragment its property belongs to, and what the system under test exposes. `evaluate_requirement`
    then takes the strongest evidence any of them produced, falling to the next rung when an engine
    established nothing.
    Why this matters: `formalism` used to name the property *and* pick the engine, so 17 of 18
    shipped duties could never exceed `observed` however much a system exposed — a fact about a
    word in a TOML file, reported as a fact about the system. Which rung a duty reaches must be a
    fact about the system. What a verdict *means* is untouched by this: see `docs/semantics.md`
    §3.5, including the case where exposed logic and trace disagree.
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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from reasonsmith.rulelang import STATE_FRAGMENTS, is_present
from reasonsmith.spec import Pack, Requirement, normalize_domains, normalize_scope
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
    "applicable was excluded on one of two independent gates. Either no regulatory class was "
    "declared for the system at all, or the class that was declared is not the one the "
    "requirement is limited to; or no decision domain was declared for the system at all, or "
    "none of the domains that were declared is one the requirement is about. This tool infers "
    "neither the class nor the domain, so an undeclared system is neither placed in scope nor "
    "cleared of the duty: read the declared scope and domain lines before reading a "
    "not-applicable result. The decision-domain vocabulary is written by the pack author and by "
    "no regulation, and a duty declaring no domain reaches every system it is run against."
)

#: Formalisms this build can actually evaluate.
SUPPORTED_FORMALISMS = ("record", "temporal", "logical")

#: Where a probed result carries the search that produced it, and the fields that search must
#: name. A probed verdict is a statement about a bounded search — how many inputs were replayed,
#: how they were generated and from which seed — so a result that does not carry them cannot be
#: constructed at all (see `RequirementResult.__post_init__`), rather than being rendered without
#: them and read as if the property had been established for every input.
PROBE_BUDGET_KEY = "probe_budget"
PROBE_BUDGET_FIELDS = ("trials", "strategy", "seed", "input_space")
_UNREAD = object()


def _budget_line(budget: Mapping[str, Any]) -> str:
    """One line naming what a probed search covered, shared by every rendering of it."""
    space = budget.get("input_space")
    if isinstance(space, Mapping):
        fields = ", ".join(f"{name} ({count} values)" for name, count in sorted(space.items()))
    else:
        fields = str(space)
    unestablished = budget.get("property_kinds_unestablished", ())
    kind_limit = (
        f" Property field kind(s) not established by trace: {', '.join(unestablished)}."
        if unestablished
        else ""
    )
    return (
        f"{budget['trials']} input(s) replayed, seed {budget['seed']}, "
        f"input space: {fields or 'no field varied'}. Strategy: {budget['strategy']}{kind_limit}"
    )


#: Re-exported so the engines and the JSONL adapter keep importing presence from one place. The
#: definition lives in `rulelang` because `present(signal)` is an atom of the property language
#: and the interpreter has to answer it; having two definitions of "present" is how the record
#: engine and a `present()` atom would come to disagree about the same record.
_is_present = is_present


@dataclass(frozen=True)
class RequirementResult:
    """The conformance result for a single requirement.

    `strength` is `None` when the requirement was not evaluated at all or is not applicable;
    see the module docstring. `signals_missing` names required signals missing from the
    adapter's capability set and is therefore populated only on an unattainable result. Signals
    in that set but absent from a particular trace are a different finding and land in
    `details`.

    `binding` records whether the duty is a legally binding obligation (true) or an
    interpretive recital/guidance item (false), `scope` records any regulatory class the
    duty is limited to (e.g. 'high-risk'), and `domains` records the kinds of decision it is
    about (e.g. 'consumer-credit'), empty meaning it is not domain-limited. All three are
    carried through from the requirement so a reader of a single result never has to go back to
    the pack to know what kind of duty it is.
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
    domains: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Every invariant below compares against the enum members, so a raw string would
        # match none of them and walk past all of them. Normalise first: the guards are the
        # only thing standing between a caller and a result that claims more than it has.
        object.__setattr__(self, "verdict", Verdict.parse(self.verdict))
        if self.strength is not None:
            object.__setattr__(self, "strength", Strength.parse(self.strength))
        object.__setattr__(self, "binding", bool(self.binding))
        object.__setattr__(self, "scope", str(self.scope))
        object.__setattr__(self, "domains", normalize_domains(self.domains))
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

        # Probed is not proved, and the only thing that keeps the two apart on the page is the
        # budget: the number of inputs replayed, how they were generated and the seed that
        # generated them. Refusing the result here rather than at render time is what makes it
        # impossible to publish a probed verdict in any format without what was searched.
        self._validate_probe_budget()

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

    def _validate_probe_budget(self) -> None:
        if self.strength != Strength.PROBED:
            return
        budget = self.details.get(PROBE_BUDGET_KEY)
        if not isinstance(budget, Mapping):
            raise ValueError(
                f"{self.requirement_id}: a probed result must carry its search budget in "
                f"details[{PROBE_BUDGET_KEY!r}]; no counterexample found is a claim about a "
                f"bounded search, and a reader who cannot see the bound cannot read it"
            )
        missing_fields = [field for field in PROBE_BUDGET_FIELDS if field not in budget]
        if missing_fields:
            raise ValueError(
                f"{self.requirement_id}: the probe budget must name "
                f"{', '.join(PROBE_BUDGET_FIELDS)}; missing {', '.join(missing_fields)}"
            )

    @property
    def evaluated(self) -> bool:
        """False when no evidence of any strength was gathered for this requirement."""
        return self.strength is not None

    def to_dict(self) -> dict:
        self._validate_probe_budget()
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
            "domains": list(self.domains),
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
    system_domains: tuple[str, ...] = ()
    limits: str = LIMITS

    def __post_init__(self) -> None:
        object.__setattr__(self, "system_domains", normalize_domains(self.system_domains))

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
        for result in self.results:
            result._validate_probe_budget()
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
            f"declared domains: {', '.join(self.system_domains) or 'undeclared'}",
            f"pack: {self.pack_id}",
            f"headline: {self.headline}",
            "",
            "REQUIREMENT FINDINGS:",
        ]
        for r in self.results:
            r._validate_probe_budget()
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
            if r.domains:
                lines.append(f"    domain limit: {', '.join(r.domains)}")
            if r.signals_missing:
                lines.append(f"    MISSING SIGNALS: {', '.join(r.signals_missing)}")
            absent = r.details.get("signals_absent_from_trace")
            if absent:
                lines.append(f"    ABSENT FROM TRACE: {', '.join(absent)}")
            if r.evidence_summary:
                lines.append(f"    summary: {r.evidence_summary}")
            budget = r.details.get(PROBE_BUDGET_KEY)
            if budget:
                lines.append(f"    probe budget: {_budget_line(budget)}")
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
        sys_domains = html.escape(", ".join(self.system_domains) or "undeclared")
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
            r._validate_probe_budget()
            req_id = html.escape(r.requirement_id)
            source = html.escape(r.source_clause)
            summary = html.escape(r.evidence_summary)
            sc_esc = html.escape(r.scope)
            scope_tag = f'<span class="badge badge-scope">Scope: {sc_esc}</span>' if r.scope else ""
            dom_esc = html.escape(", ".join(r.domains))
            domain_tag = (
                f'<span class="badge badge-scope">Domain: {dom_esc}</span>' if r.domains else ""
            )
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

            probe_budget = r.details.get(PROBE_BUDGET_KEY)
            if probe_budget:
                details_html += (
                    '<div class="callout-box callout-probe">'
                    "<strong>PROBED — What Was Searched:</strong><br>"
                    f"{html.escape(_budget_line(probe_budget))}"
                    '<div class="callout-note">A bounded search, not a proof: the property is '
                    "unchecked outside the inputs named here.</div>"
                    "</div>"
                )

            counterexample = r.details.get("counterexample")
            if counterexample and r.verdict == Verdict.VIOLATED:
                ce_str = ", ".join(
                    f"{html.escape(str(k))}: {html.escape(str(v))}"
                    for k, v in counterexample.items()
                )
                # A counterexample the solver derived and one a replay found are both concrete
                # inputs, and neither may be worded as the other: `probed` did not prove anything.
                kind = "Replayed" if r.strength == Strength.PROBED else "Formal"
                details_html += (
                    '<div class="callout-box callout-violated">'
                    f"<strong>VIOLATED — {kind} Counterexample Input:</strong><br>"
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
              {domain_tag}
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
      /* ponytail: serif di sistema, non Newsreader come la landing — il report resta
         self-contained (un woff2 inline costerebbe ~130KB per ogni report CLI).
         Upgrade path: subset Newsreader + data-URI se l'identita' lo richiede. */
      --font-serif: Georgia, "Times New Roman", serif;

      /* Dossier palette: tinted neutrals in oklch, one accent (deletion red), color by role */
      --paper: oklch(96.6% 0.005 95);
      --surface: oklch(99.2% 0.003 95);
      --ink: oklch(24% 0.012 260);
      --ink-muted: oklch(45% 0.012 260);
      --ink-faint: oklch(56% 0.01 260);
      --line: oklch(88% 0.007 260);
      --line-strong: oklch(72% 0.01 260);
      --neutral-soft: oklch(95.5% 0.005 260);

      --accent: oklch(50% 0.19 25);
      --accent-deep: oklch(38% 0.14 25);
      --accent-soft: oklch(94.5% 0.025 25);
      --accent-line: oklch(80% 0.07 25);

      --ok: oklch(44% 0.11 155);
      --ok-soft: oklch(94.5% 0.03 155);
      --ok-line: oklch(82% 0.06 155);

      --warn: oklch(45% 0.1 75);
      --warn-soft: oklch(95.5% 0.03 90);
      --warn-line: oklch(84% 0.06 90);

      /* Fluid type, ratio 1.25 */
      --step--1: clamp(0.80rem, 0.77rem + 0.15vw, 0.90rem);
      --step-0: clamp(1.00rem, 0.95rem + 0.25vw, 1.13rem);
      --step-1: clamp(1.25rem, 1.15rem + 0.5vw, 1.55rem);
      --step-2: clamp(1.55rem, 1.35rem + 1vw, 2.10rem);
      --display: clamp(2.2rem, 1.5rem + 3.4vw, 3.6rem);

      --space-2xs: 0.5rem;
      --space-xs: 0.75rem;
      --space-s: 1rem;
      --space-m: 1.5rem;
      --space-l: 2.5rem;

      --dur-fast: 0.18s;
      --dur-base: 0.4s;
      --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
      --ease-snap: cubic-bezier(0.16, 1, 0.3, 1);

      --radius: 6px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      background-color: var(--paper);
      color: var(--ink);
      line-height: 1.6;
      font-size: var(--step-0);
      padding: var(--space-l) var(--space-s);
    }}

    .skip-link {{
      position: absolute;
      left: -9999px;
      top: 0;
      z-index: 10;
      background: var(--ink);
      color: var(--surface);
      font-family: var(--font-mono);
      font-size: var(--step--1);
      padding: var(--space-2xs) var(--space-s);
    }}
    .skip-link:focus {{ left: var(--space-s); top: var(--space-s); }}

    :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}

    .container {{
      max-width: 1080px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--line-strong);
      overflow: hidden;
    }}

    .report-header {{
      background: var(--ink);
      color: var(--surface);
      padding: var(--space-l);
      border-bottom: 4px solid var(--accent);
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: var(--space-s);
    }}
    .header-corner {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: oklch(72% 0.012 260);
      white-space: nowrap;
    }}
    .header-corner a {{ color: oklch(80% 0.06 25); text-decoration: none; }}
    .header-corner a:hover {{ text-decoration: underline; }}
    .dossier-foot {{
      margin: 0 var(--space-l) var(--space-m);
      padding-top: var(--space-s);
      border-top: 1px solid var(--line);
      font-family: var(--font-mono);
      font-size: 0.72rem;
      letter-spacing: 0.12em;
      color: var(--ink-faint);
      display: flex;
      justify-content: space-between;
      gap: var(--space-s);
      flex-wrap: wrap;
    }}
    .dossier-foot a {{ color: var(--accent-deep); text-decoration: none; }}
    .dossier-foot a:hover {{ text-decoration: underline; }}
    .brand-title {{
      display: flex;
      align-items: center;
      gap: var(--space-2xs);
      font-family: var(--font-mono);
      font-size: var(--step--1);
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: oklch(80% 0.06 25);
      margin-bottom: var(--space-2xs);
    }}
    .brand-title svg {{ width: 1.15rem; height: 1.15rem; }}
    .brand-title .mark-live {{ fill: var(--ok); }}
    .brand-title .mark-strike {{ fill: var(--accent); }}
    .main-title {{
      font-family: var(--font-serif);
      font-size: var(--display);
      font-weight: 600;
      line-height: 1.0;
      letter-spacing: -0.025em;
      text-wrap: balance;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--space-m);
      margin-top: var(--space-l);
      padding-top: var(--space-m);
      border-top: 1px solid oklch(42% 0.012 260);
    }}
    .meta-item {{ display: flex; flex-direction: column; gap: 0.15rem; }}
    .meta-label {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: oklch(72% 0.012 260);
    }}
    .meta-value {{
      font-size: var(--step-0);
      font-weight: 600;
      color: var(--surface);
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }}

    .headline-banner {{
      background: var(--accent-soft);
      border: 1px solid var(--accent-line);
      border-left: 4px solid var(--accent);
      padding: var(--space-m) var(--space-l);
      margin: var(--space-l);
      border-radius: var(--radius);
    }}
    .headline-title {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--accent-deep);
      margin-bottom: var(--space-2xs);
    }}
    .headline-text {{
      font-family: var(--font-serif);
      font-size: var(--step-2);
      font-weight: 600;
      line-height: 1.15;
      letter-spacing: -0.015em;
      color: var(--accent-deep);
      max-width: 65ch;
      text-wrap: pretty;
    }}
    .provenance-bar {{
      font-size: 0.8rem;
      color: var(--ink-muted);
      margin-top: var(--space-xs);
      padding-top: var(--space-xs);
      border-top: 1px dashed var(--accent-line);
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }}

    .dashboard-section {{
      padding: 0 var(--space-l) var(--space-l) var(--space-l);
    }}
    .split-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--space-m);
    }}
    @media (max-width: 768px) {{
      .split-grid {{ grid-template-columns: 1fr; }}
    }}
    .split-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: var(--space-m);
      background: var(--surface);
    }}
    .split-card-header {{
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: var(--space-xs);
      padding-bottom: var(--space-2xs);
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      color: var(--ink-muted);
      font-variant-numeric: tabular-nums;
    }}
    .pill-group {{
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2xs);
    }}
    .stat-pill {{
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-variant-numeric: tabular-nums;
    }}
    .text-muted {{ color: var(--ink-faint); font-size: var(--step--1); }}

    .section-title {{
      font-family: var(--font-serif);
      font-size: var(--step-2);
      font-weight: 600;
      letter-spacing: -0.015em;
      padding: var(--space-m) var(--space-l) var(--space-xs);
      border-top: 1px solid var(--line);
      color: var(--ink);
      text-wrap: balance;
    }}
    .req-list {{
      padding: var(--space-xs) var(--space-l) var(--space-l);
      display: flex;
      flex-direction: column;
      gap: var(--space-m);
    }}

    .req-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface);
      overflow: hidden;
    }}
    .req-card.verdict-violated {{
      border: 1px solid var(--accent-line);
      border-left: 4px solid var(--accent);
      background: var(--surface);
    }}
    .req-card.verdict-unattainable {{
      border: 1px dashed var(--warn-line);
      border-left: 4px dashed var(--warn);
      background: var(--surface);
    }}
    .req-card.verdict-satisfied {{
      border-left: 4px solid var(--ok);
      background: var(--surface);
    }}

    .req-card-header {{
      padding: var(--space-s) var(--space-m);
      background: var(--neutral-soft);
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: var(--space-s);
      flex-wrap: wrap;
    }}
    .req-title-group {{ flex: 1; min-width: 16rem; }}
    .req-id {{
      font-size: var(--step-0);
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--ink);
      letter-spacing: -0.01em;
    }}
    .req-clause {{
      font-size: var(--step--1);
      color: var(--ink-muted);
      margin-left: var(--space-2xs);
    }}
    .badge-group {{
      display: flex;
      align-items: center;
      gap: var(--space-2xs);
      flex-wrap: wrap;
    }}

    .badge {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      white-space: nowrap;
    }}
    .badge-binding {{ background: var(--ink); color: var(--surface); }}
    .badge-interpretive {{
      background: var(--surface); color: var(--ink-muted); border: 1px solid var(--line-strong);
    }}
    .badge-scope {{
      background: var(--neutral-soft); color: var(--ink-muted); border: 1px solid var(--line);
    }}

    .verdict-satisfied {{
      background: var(--ok-soft);
      color: var(--ok);
      border: 1px solid var(--ok-line);
    }}
    .verdict-violated {{
      background: var(--accent-soft);
      color: var(--accent-deep);
      border: 1px solid var(--accent-line);
    }}
    .verdict-unattainable {{
      background: var(--warn-soft);
      color: var(--warn);
      border: 1px dashed var(--warn-line);
    }}
    .verdict-inconclusive {{
      background: var(--neutral-soft);
      color: var(--ink-muted);
      border: 1px solid var(--line);
    }}
    .verdict-not-applicable {{
      background: var(--surface);
      color: var(--ink-faint);
      border: 1px solid var(--line);
    }}

    .lattice-container {{
      padding: var(--space-xs) var(--space-m);
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      gap: var(--space-s);
      flex-wrap: wrap;
    }}
    .lattice-label {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--ink-faint);
      white-space: nowrap;
    }}
    .lattice-track {{
      display: flex;
      align-items: center;
      gap: 0.3rem;
      flex-wrap: wrap;
    }}
    .lattice-step {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      color: var(--ink-faint);
      background: var(--surface);
      border: 1px solid var(--line);
      font-variant-numeric: tabular-nums;
    }}
    .lattice-step.active-proved {{
      background: var(--ink); color: var(--surface); border-color: var(--ink); font-weight: 700;
    }}
    .lattice-step.active-probed {{
      background: var(--ok); color: var(--surface); border-color: var(--ok); font-weight: 700;
    }}
    .lattice-step.active-observed {{
      background: var(--ok); color: var(--surface); border-color: var(--ok); font-weight: 700;
    }}
    .lattice-step.active-unattainable {{
      background: var(--warn); color: var(--surface); border-color: var(--warn);
      font-weight: 700; border-style: dashed;
    }}
    .lattice-step.passed {{
      background: var(--neutral-soft); color: var(--ink-muted); border-color: var(--line-strong);
    }}
    .lattice-arrow {{ color: var(--line-strong); font-size: 0.72rem; }}

    .req-card-body {{ padding: var(--space-m); }}
    .signal-list {{ margin-bottom: var(--space-xs); font-size: var(--step--1); }}
    .signal-tag {{
      font-family: var(--font-mono);
      background: var(--neutral-soft);
      color: var(--ink-muted);
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      border: 1px solid var(--line);
      font-size: 0.78rem;
      display: inline-block;
      margin: 0.1rem;
    }}
    .signal-tag.missing {{
      background: var(--warn-soft); color: var(--warn); border-color: var(--warn-line);
      font-weight: 600;
    }}
    .signal-tag.absent {{
      background: var(--accent-soft); color: var(--accent-deep); border-color: var(--accent-line);
      font-weight: 600;
    }}

    .evidence-summary {{
      font-size: var(--step--1);
      color: var(--ink-muted);
      margin-top: var(--space-2xs);
      line-height: 1.6;
      max-width: 75ch;
      text-wrap: pretty;
    }}
    .callout-box {{
      margin-top: var(--space-s);
      padding: var(--space-s);
      border-radius: var(--radius);
      font-size: var(--step--1);
    }}
    .callout-unattainable {{
      background: var(--warn-soft); border: 1px dashed var(--warn-line); color: var(--warn);
    }}
    .callout-violated {{
      background: var(--accent-soft); border: 1px solid var(--accent-line);
      color: var(--accent-deep);
    }}
    .callout-probe {{
      background: var(--neutral-soft); border: 1px solid var(--line-strong); color: var(--ink);
    }}
    .callout-note {{ font-size: 0.78rem; margin-top: var(--space-2xs); font-style: italic; }}

    .witness-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: var(--space-xs);
      font-size: 0.78rem;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }}
    .witness-table th, .witness-table td {{
      border: 1px solid var(--accent-line);
      padding: 0.4rem 0.6rem;
      text-align: left;
      vertical-align: top;
    }}
    .witness-table th {{
      background: var(--surface);
      color: var(--accent-deep);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
    }}
    .witness-table tr:nth-child(even) {{ background: var(--surface); }}

    .limits-card {{
      margin: var(--space-l);
      margin-top: 0;
      padding: var(--space-m);
      background: var(--neutral-soft);
      border: 1px solid var(--line);
      border-radius: var(--radius);
    }}
    .limits-header {{
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--ink-muted);
      margin-bottom: var(--space-2xs);
    }}
    .limits-text {{
      font-size: var(--step--1);
      color: var(--ink-muted);
      line-height: 1.7;
      max-width: 85ch;
      text-wrap: pretty;
    }}

    .reveal {{ opacity: 0; transform: translateY(16px); }}
    .reveal.in {{
      opacity: 1;
      transform: none;
      transition: opacity var(--dur-base) var(--ease-out),
        transform var(--dur-base) var(--ease-out);
    }}
    @media (prefers-reduced-motion: reduce) {{
      .reveal {{ opacity: 1; transform: none; }}
    }}

    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .container {{ border: none; max-width: 100%; }}
      .reveal {{ opacity: 1 !important; transform: none !important; }}
      .report-header {{
        background: oklch(24% 0.012 260) !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      .req-card {{ break-inside: avoid; border: 1px solid oklch(30% 0.012 260) !important; }}
      .req-card.verdict-violated {{ border-left: 4px solid oklch(50% 0.19 25) !important; }}
      .req-card.verdict-unattainable {{ border-left: 4px dashed oklch(45% 0.1 75) !important; }}
      .witness-table th, .witness-table td {{ border-color: oklch(50% 0.07 25) !important; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#findings">Skip to requirement findings</a>
  <div class="container" id="top">
    <header class="report-header">
      <div class="header-top">
        <div>
          <div class="brand-title">
            <svg viewBox="0 0 64 64" aria-hidden="true">
              <g stroke="currentColor" stroke-opacity="0.35" stroke-width="1.5">
                <line x1="10" y1="47" x2="32" y2="17"/><line x1="21" y1="47" x2="32" y2="17"/>
                <line x1="32" y1="47" x2="32" y2="17"/><line x1="43" y1="47" x2="32" y2="17"/>
                <line x1="54" y1="47" x2="32" y2="17"/>
              </g>
              <circle cx="32" cy="15" r="6.5" fill="currentColor"/>
              <circle cx="10" cy="47" r="5" class="mark-live"/>
              <circle cx="21" cy="47" r="5" fill="currentColor"/>
              <circle cx="32" cy="47" r="5" fill="currentColor"/>
              <circle cx="43" cy="47" r="5" fill="currentColor"/>
              <circle cx="54" cy="47" r="5" fill="currentColor"/>
              <rect x="15" y="44.8" width="45" height="4.4" rx="1.2" class="mark-strike"
                transform="rotate(-3 37.5 47)"/>
            </svg>
            reasonsmith audit engine
          </div>
          <h1 class="main-title">Conformance Report</h1>
        </div>
        <span class="header-corner">
          <a href="index.html">&larr; landing</a> &middot; audit dossier
        </span>
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
          <span class="meta-label">Declared Domains</span>
          <span class="meta-value">{sys_domains}</span>
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

    <h2 class="section-title" id="findings">Requirement Findings</h2>
    <main class="req-list">
{req_section_html}
    </main>

    <section class="limits-card">
      <h3 class="limits-header">Limits of this report</h3>
      <p class="limits-text">{limits_esc}</p>
    </section>
    <footer class="dossier-foot">
      <span>reasonsmith &middot; audit-grade explanations</span>
      <span><a href="index.html">landing</a> &middot; <a href="#top">top</a></span>
    </footer>
  </div>
  <script>
    (function () {{
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var deleted = document.querySelectorAll(".reason-deleted");
      if (reduce || !("IntersectionObserver" in window)) {{
        deleted.forEach(function (li) {{ li.classList.add("struck"); }});
        return;
      }}
      var blocks = document.querySelectorAll(
        ".split-card, .req-card, .limits-card"
      );
      blocks.forEach(function (el) {{ el.classList.add("reveal"); }});
      var io = new IntersectionObserver(function (entries) {{
        entries.forEach(function (en) {{
          if (!en.isIntersecting) return;
          en.target.classList.add("in");
          io.unobserve(en.target);
        }});
      }}, {{ rootMargin: "0px 0px -10% 0px" }});
      blocks.forEach(function (el, i) {{
        el.style.transitionDelay = (i % 4) * 60 + "ms";
        io.observe(el);
      }});
      var audit = deleted.length ? deleted[0].parentNode : null;
      if (audit) {{
        var rio = new IntersectionObserver(function (entries) {{
          entries.forEach(function (en) {{
            if (!en.isIntersecting) return;
            deleted.forEach(function (li, i) {{
              setTimeout(function () {{ li.classList.add("struck"); }}, 350 + i * 200);
            }});
            rio.unobserve(en.target);
          }});
        }}, {{ threshold: 0.35 }});
        rio.observe(audit);
      }}
    }})();
  </script>
</body>
</html>
"""


    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "system_scope": self.system_scope,
            "system_domains": list(self.system_domains),
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


class _EvaluationResources:
    def __init__(self, sut: SystemUnderTest):
        self.sut = sut
        self._records: object = _UNREAD
        self._trace_error: Exception | None = None
        self._logic_data: Any = _UNREAD
        self._logic_error: Exception | None = None

    def trace(self) -> list[dict[str, Any]]:
        if self._records is _UNREAD:
            try:
                self._records = _read_trace(self.sut)
            except Exception as exc:
                self._trace_error = exc
                self._records = None
        if self._trace_error is not None:
            raise self._trace_error
        return cast(list[dict[str, Any]], self._records)

    def logic(self) -> Any:
        if self._logic_data is _UNREAD:
            logic_func = getattr(self.sut, "logic", None)
            try:
                self._logic_data = logic_func() if callable(logic_func) else None
            except Exception as exc:
                self._logic_error = exc
                self._logic_data = None
        if self._logic_error is not None:
            raise self._logic_error
        return self._logic_data


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


def _declared_scope(sut: SystemUnderTest, system_scope: str | None) -> str | None:
    """The regulatory class this run is judging against — the argument, or the system's own."""
    if system_scope is None:
        return getattr(sut, "system_scope", getattr(sut, "declared_scope", None))
    return system_scope


def _declared_domains(sut: SystemUnderTest, system_domains: Any) -> tuple[str, ...]:
    """The decision domains this run is judging against — the argument, or the system's own.

    No second attribute name is honoured here, unlike `declared_scope` beside it: a domain
    declaration is new in this version, so there is no older spelling of it in the wild to keep
    working, and inventing one would be a second place a system could speak from.
    """
    if system_domains is None:
        system_domains = getattr(sut, "system_domains", None)
    return normalize_domains(system_domains, "declared system decision domain")


def _not_applicable(req: Requirement, summary: str) -> RequirementResult:
    """The not-applicable result: no strength, no missing signals, nothing about the system."""
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.NOT_APPLICABLE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=summary,
        binding=req.binding,
        scope=req.scope,
        domains=req.domains,
    )


def _inapplicability(
    req: Requirement, sys_scope_norm: str, sys_domains: tuple[str, ...], system_scope: Any
) -> str | None:
    """Why this duty does not reach this system, or None when it does.

    Two independent gates, on two axes that are not the same question. `scope` is a regulatory
    class from one statute's own fixed vocabulary; `domains` is the kind of decision the duty is
    about, from a vocabulary this repository wrote (`spec.DECISION_DOMAINS`). A duty is evaluated
    only when it passes both.

    Each gate is a conjunction against a declaration this tool never infers, and each fails in
    the same two ways — the system declared nothing, or declared something else — because those
    two are one instruction to the reader: *say what this system is, and run it again*. The
    message names which of the two it was, so nobody reads "not applicable" as "cleared".

    An unset gate on the requirement is a deliberate wildcard, not an accident: `scope = ""` is a
    duty no regulatory class limits, and `domains = []` is a duty about no particular kind of
    decision — the GDPR's Article 22 is both. Neither can be reached by omission, because the
    loader refuses a requirement that does not carry both fields.
    """
    if req.scope and normalize_scope(req.scope) != sys_scope_norm:
        desc = f"declared as {system_scope!r}" if sys_scope_norm else "undeclared"
        return (
            f"Not applicable: requirement scope is {req.scope!r}, but system regulatory "
            f"class is {desc}. reasonsmith never infers a system's regulatory class."
        )
    if req.domains and not (set(req.domains) & set(sys_domains)):
        desc = f"declared as {', '.join(sys_domains)}" if sys_domains else "undeclared"
        return (
            f"Not applicable: this duty is about {', '.join(req.domains)} decisions, but the "
            f"system's decision domain is {desc}. reasonsmith never infers a system's decision "
            "domain, and the domain vocabulary is the pack author's rather than the "
            "regulation's — see docs/authoring-packs.md."
        )
    return None


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
    system_scope: str | None = None,
    system_domains: Iterable[str] | None = None,
    *,
    _resources: _EvaluationResources | None = None,
) -> RequirementResult:
    """Evaluate a single requirement against a SUT.

    Applicability is answered first, on the two gates `_inapplicability` describes: a requirement
    limited to a regulatory class the system is not declared to be in, or about a kind of
    decision the system is not declared to make, does not reach this system, and the result is
    NOT_APPLICABLE with no strength, because nothing about the system was checked. Neither the
    class nor the domain is ever inferred — an undeclared system is not silently treated as in
    scope, and the result says which of the two it was. A declared class outside
    `REGULATORY_CLASSES`, or a domain outside `DECISION_DOMAINS`, is refused rather than
    answered, here as well as in `check_conformance`, so a caller reaching this function
    directly gets the same guarantee.

    If the adapter's capability set does not cover the required signals, returns UNATTAINABLE
    without executing the SUT. Otherwise `records` is used as the decision trace; when it is
    None the trace is fetched from the SUT, so callers holding a trace already can avoid
    re-running the system once per requirement.
    """
    result = _evaluate_requirement(
        req, sut, records, system_scope, system_domains, _resources=_resources
    )
    # The duty's own domain limit is stamped once, here, rather than threaded through four
    # engines: an engine has nothing to say about which systems a duty reaches, and a rung that
    # forgot to carry it would render a domain-limited duty as one that reaches everything.
    return replace(result, domains=req.domains)


def _evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None,
    system_scope: str | None,
    system_domains: Iterable[str] | None,
    *,
    _resources: _EvaluationResources | None,
) -> RequirementResult:
    resources = _resources or _EvaluationResources(sut)

    system_scope = _declared_scope(sut, system_scope)
    sys_scope_norm = normalize_scope(system_scope, "declared system scope")
    sys_domains = _declared_domains(sut, system_domains)

    inapplicable = _inapplicability(req, sys_scope_norm, sys_domains, system_scope)
    if inapplicable:
        return _not_applicable(req, inapplicable)

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

    candidates = _engine_ladder(req, sut, records, resources)
    if not candidates:
        raise NotImplementedError(
            f"{req.formalism!r} is listed in SUPPORTED_FORMALISMS but no engine here evaluates "
            "it. Widen SUPPORTED_FORMALISMS when the engine lands, not before."
        )

    # Take the strongest evidence there is a basis for, not the first engine tried. An engine
    # that came back with `strength=None` established nothing, so it discharged nothing, and the
    # next rung down is the strongest evidence this run actually has. The order comes from the
    # lattice rather than from the order `_engine_ladder` appended, so a rung added there cannot
    # be tried out of turn.
    #
    # When nothing established anything, the strongest engine's not-evaluated result is reported,
    # so the reader is told how the best available engine fell short. The one exception is a proof
    # rung that never had any logic to reason over: that says nothing about this evaluation, so a
    # lower rung's account of the evidence the system did supply displaces it.
    fallback: RequirementResult | None = None
    for _strength, run in sorted(candidates, key=lambda rung: rung[0], reverse=True):
        result = run()
        if result.strength is not None:
            return result
        if fallback is None or fallback.details.get("result") == _NO_LOGIC_TO_REASON_OVER:
            fallback = result
    return cast(RequirementResult, fallback)


#: Tags a proof-rung result produced without any logic to reason over — `logic()` absent, returning
#: None, or raising. Such a result is not an account of this evaluation, only of an interface that
#: was never there, so `evaluate_requirement` lets a lower rung's not-evaluated result displace it.
_NO_LOGIC_TO_REASON_OVER = "no_logic_to_reason_over"


def _run_proof_rung(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None,
    resources: _EvaluationResources,
) -> RequirementResult:
    """The proof rung, with a broken `logic()` reported rather than raised.

    `logic()` is an optional interface, and one that raises has established nothing — which is
    what `strength=None` means. Letting the exception out would take the whole evaluation down
    with it, so a duty whose trace the record engine could have read would lose a verdict it had
    the evidence for. A malformed *trace* is deliberately not treated this way: that is the
    system's own decision log coming back the wrong shape, and it still raises and names the
    system.
    """
    from reasonsmith.engines.proved import ProvedEngine

    try:
        logic_data = resources.logic()
    except Exception as exc:
        return RequirementResult(
            requirement_id=req.id,
            source_clause=f"{req.source_document} {req.article_clause}",
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required=tuple(req.requires),
            evidence_summary=(
                f"Not evaluated: reading the system's decision logic failed — "
                f"{type(sut).__name__}.logic() raised {type(exc).__name__}: {exc}. "
                "Nothing was proved about this requirement."
            ),
            details={"result": _NO_LOGIC_TO_REASON_OVER},
            binding=req.binding,
            scope=req.scope,
        )
    result = ProvedEngine.evaluate(req, sut, records, logic_data=logic_data)
    if logic_data is None:
        return replace(result, details={**result.details, "result": _NO_LOGIC_TO_REASON_OVER})
    return result


def _engine_ladder(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None,
    resources: _EvaluationResources,
) -> list[tuple[Strength, Any]]:
    """Every engine that could discharge this requirement, strongest first.

    Two things decide the list, and `formalism` is only one of them. The fragment says what kind
    of property this is — a state property of one decision record, or a temporal one reaching
    across records — and the system's exposed surface says what can be reasoned over. A presence
    property checked against a trace is `observed`; the *same* property discharged against exposed
    `logic()` is `proved`. Which rung a duty reaches is therefore a fact about the system, not
    about which word a pack author typed.

    Building the ladder never *executes* the system: both optional rungs are selected from the
    callable surface alone, `logic` exactly as `decide` already was. Calling `logic()` here to
    decide whether the proof rung belongs would let a system whose `logic()` raises abort a duty
    the record engine could have answered from its trace.

    Temporal properties reach only the observed engine. The solver and the replay search both
    reason about one decision at a time and have nothing to say about a formula quantified over
    the trace; there is no temporal engine above `observed` in this build, and inventing a rung
    for one would be the overclaim this package exists to refuse.
    """
    ladder: list[tuple[Strength, Any]] = []

    if req.formalism in STATE_FRAGMENTS:
        if callable(getattr(sut, "logic", None)):
            ladder.append((Strength.PROVED, lambda: _run_proof_rung(req, sut, records, resources)))
        if callable(getattr(sut, "decide", None)):
            from reasonsmith.engines.probed import ProbedEngine
            ladder.append(
                (
                    Strength.PROBED,
                    lambda: ProbedEngine.evaluate(
                        req,
                        sut,
                        records,
                        trace_provider=resources.trace if records is None else None,
                    ),
                )
            )

    if req.formalism == "record":
        from reasonsmith.engines.record import RecordEngine
        ladder.append(
            (
                Strength.OBSERVED,
                lambda: RecordEngine.evaluate(
                    req, sut, records if records is not None else resources.trace()
                ),
            )
        )
    elif req.formalism == "temporal":
        from reasonsmith.engines.observed import ObservedEngine
        ladder.append(
            (
                Strength.OBSERVED,
                lambda: ObservedEngine.evaluate(
                    req, sut, records if records is not None else resources.trace()
                ),
            )
        )
    elif not ladder:
        # A logical duty against a system exposing neither `logic()` nor `decide()`. The proved
        # engine is the one that can say which interface was missing, so it is reached to report
        # no evidence rather than left out to produce none.
        from reasonsmith.engines.proved import ProvedEngine
        ladder.append((Strength.PROVED, lambda: ProvedEngine.evaluate(req, sut, records)))

    return ladder


def check_conformance(
    sut: SystemUnderTest,
    pack: Pack,
    system_name: str = "SUT",
    system_scope: str | None = None,
    system_domains: Iterable[str] | None = None,
) -> ConformanceReport:
    """Check conformance of a SUT against all requirements in a Pack.

    Applicability and unattainability are resolved for a requirement before anything is run for
    it, and the decision trace is read at most once — and not at all when nothing in the pack is
    applicable, attainable and checkable here. Both are properties of `evaluate_requirement` and
    of the shared, lazily read `_EvaluationResources`, so "the unattainable analysis does not run
    the system" does not depend on the order the requirements happen to appear in.

    A declared class outside `REGULATORY_CLASSES`, or a decision domain outside
    `DECISION_DOMAINS`, is refused before any of that, so a misspelling cannot pass for a system
    that is simply out of scope. A class or domain the vocabulary knows but this pack does not
    target is not an error: the system is genuinely outside those duties' reach, and they are
    reported not applicable as a declared mismatch.
    """
    system_scope = _declared_scope(sut, system_scope)
    normalize_scope(system_scope, "declared system scope")
    sys_domains = _declared_domains(sut, system_domains)
    resources = _EvaluationResources(sut)
    results = [
        evaluate_requirement(
            req,
            sut,
            system_scope=system_scope,
            system_domains=sys_domains,
            _resources=resources,
        )
        for req in pack.requirements
    ]
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        system_scope=system_scope,
        system_domains=sys_domains,
        results=tuple(results),
    )
