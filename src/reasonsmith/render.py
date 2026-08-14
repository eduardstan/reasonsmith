"""Rendering of a `ConformanceReport` into plain text and self-contained HTML.

What this module is for:
  The two renderings of a conformance report, moved out of `report.py` so the report type,
  the result type and the evaluation machinery are not half of a thousand-line method:
  `render_text` is the readable console rendering, and `render_html` is the self-contained,
  offline, A4-printable HTML page. The `ConformanceReport` methods of the same names delegate
  here, so the public API is unchanged.

What a reader must not break:
  - These are pure renders of the report they are handed: they compute nothing about the
    system and print nothing the report does not carry. `render_html`'s provenance bar is the
    one deliberate exception, and it states only the caller's own `commit_hash`/`command`
    arguments or what the checkout this module was imported from can attest (`_source_checkout`)
    — never a guess.
  - Every rendering is a witness, not a summary that may round: probe budgets, elided witness
    rows and skipped duties are printed with the numbers they had, and a requirement without a
    strength renders as not evaluated, never as satisfied. A rendering that must not be read as
    complete carries its own limit in the same breath.
  - An audience projection (`AudienceProjection`, `AUDIENCES`) decides *what is shown*, never
    what is claimed. Three properties of it are load-bearing and are asserted in
    `tests/test_audience_view.py`: no audience sees a verdict another audience does not see, no
    audience loses `report.limits`, and the affected-individual projection carries no system
    internals. `audience=None` is the full report and is byte-identical to the rendering that
    existed before projections did — every generated document in `docs/` is pinned to it.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reasonsmith.report import (
    _CATEGORY_LABELS,
    CERTIFICATES_KEY,
    OPEN_TEXTURE_KEY,
    PROBE_BUDGET_KEY,
    TRUTH_DEGREE_KEY,
    ConformanceReport,
    certificate_findings,
)
from reasonsmith.verdict import EvidenceBasis, Strength, Verdict

# This warning belongs beside every HTML conformance headline so an affected person sees the
# boundary before interpreting a verdict. It is deliberately not rendered in text output: the
# affected-person front door is the HTML report and the audience gallery.
AFFECTED_PERSON_CARD_TEXT = (
    "This checks a formal test chosen by people; it does not decide whether that test is the "
    "correct legal interpretation or whether the decision-maker complied. A sample report is "
    "not evidence about your decision. Ask for the exact per-decision report and every item "
    "marked not evaluated, unattainable, or not applicable."
)


@dataclass(frozen=True)
class AudienceProjection:
    """Which parts of a report one audience is shown.

    Every field selects a part of the report that already exists; nothing here computes anything
    about the system, and no field can change a verdict. A projection narrows a rendering and
    never widens it beyond what the full report carries.

    Eight of the nine fields suppress: they default to shown and turning one off drops a part of
    the page. `plain_account` is the one that emits, and it defaults to *off* so `_FULL` — and
    with it every generated document under `docs/` — is untouched by its existence. It exists
    because suppression alone produced an artefact defined only by what had been taken out of it:
    a reader shown four requirement identifiers, four statute citations, four verdict words and
    the limits, and not one sentence of what the system said about them. What it turns on is
    `_lay_sections`, which restates parts of this same report — the decision accounts the run
    read, the certificate engine's measurement, and the duties nothing settled — in the words the
    system and the engines used. It derives no fact and paraphrases no statute.
    """

    #: The declared scope and domain lines, the headline and the per-category counts.
    overview: bool = True
    #: The evidence strength: the text tier prefix and the HTML strength lattice. With this off
    #: the verdict badge is drawn from the verdict alone, so an unattainable result still reads
    #: as the `inconclusive` it is rather than gaining a strength word the reader is not shown.
    #: The evidence *basis* rides on this same flag rather than gaining one of its own: it is the
    #: other coordinate of the same claim, it is only ever shown to explain which rungs a duty
    #: cannot reach, and an audience not shown the rungs cannot be shown a sentence about them.
    strength: bool = True
    #: Binding-vs-interpretive, the regulatory class limit and the decision domain limit.
    legal_metadata: bool = True
    #: Signal names as diagnostics: what the duty requires, and what the trace did not carry.
    signals: bool = True
    #: The missing-capability finding that makes a duty unattainable as built.
    missing_signals: bool = True
    #: The engine's own sentence about what it established.
    evidence_summary: bool = True
    #: What a bounded replay search covered.
    probe_budget: bool = True
    #: Concrete decision records and solver inputs that witness a violation.
    witnesses: bool = True
    #: The one field that *emits*: the plain-language account of `_lay_sections`, restating what
    #: this report already carries for a reader who is not an engineer, a regulator or a lawyer.
    plain_account: bool = False


#: The full report: every part of it, and the rendering `audience=None` produces.
_FULL = AudienceProjection()


#: The five audiences, and what each is shown. This table is **authored**, not derived — the same
#: kind of choice a pack author makes when they pick a threshold — and the reasoning for each row
#: is written down in `docs/semantics.md` §7 rather than left to be inferred from the flags.
#:
#: `auditor` is `_FULL` itself, by identity: the report that existed before this table did is the
#: auditor's report, which is why the no-flag default did not have to change to gain one.
AUDIENCES: dict[str, AudienceProjection] = {
    "affected-individual": AudienceProjection(
        overview=False,
        strength=False,
        legal_metadata=False,
        signals=False,
        missing_signals=False,
        evidence_summary=False,
        probe_budget=False,
        witnesses=False,
        plain_account=True,
    ),
    "auditor": _FULL,
    "deployer": AudienceProjection(signals=False, witnesses=False),
    "developer": AudienceProjection(legal_metadata=False),
    "regulator": AudienceProjection(signals=False, missing_signals=False, witnesses=False),
}


def _projection(audience: str | None) -> AudienceProjection:
    """Resolve an audience name, refusing one outside the table rather than falling back.

    An unknown name silently rendering the full report is how an affected individual would be
    handed a page of solver output because of a typo.
    """
    if audience is None:
        return _FULL
    try:
        return AUDIENCES[audience]
    except KeyError:
        raise ValueError(
            f"unknown audience {audience!r}; known audiences are {', '.join(sorted(AUDIENCES))}"
        ) from None


def _duties(count: int) -> str:
    return "duty" if count == 1 else "duties"


def _lay_sections(report: ConformanceReport) -> list[tuple[str, list[str]]]:
    """The plain-language account, as `(heading, lines)` pairs, for `plain_account` renderings.

    Every line restates something this report already carries, and the two renderings share this
    one derivation so the page and the console cannot come to say different things.

    Three rules hold every line here, and each of them is the same rule seen from a different
    side. **The system's own words only**: a decision and a reason are quoted out of the trace,
    never rewritten, and a deleted reason is named with the label the certificate gave it. **No
    heading without a line under it**: a section with nothing to say is either dropped or says
    plainly that it has nothing, because a confident heading over an empty box is exactly the
    defect this account exists to remove. **Absence of a finding is never completeness**: a run
    where the certificate engine never measured whether the stated reasons were all the reasons
    says so in its own section, rather than leaving a reader to read silence as a clean result.
    """
    sections: list[tuple[str, list[str]]] = []

    account_lines: list[str] = []
    for account in report.decisions:
        if account.decision:
            account_lines.append(f'the decision it recorded: "{account.decision}"')
        if account.reason:
            account_lines.append(f'the reason it stated: "{account.reason}"')
        elif account.decision:
            account_lines.append("it stated no reason for that decision.")
    if not report.decisions:
        heading = "WHAT THE SYSTEM RECORDED"
        account_lines = [
            "Nothing. This run read no decision record stating a decision or a reason, so this "
            "report carries none of the system's own words about one."
        ]
    elif len(report.decisions) == 1:
        heading = "WHAT THE SYSTEM RECORDED ABOUT THIS DECISION"
    else:
        heading = f"WHAT THE SYSTEM RECORDED ABOUT THE {len(report.decisions)} DECISIONS IT LOGGED"
    sections.append((heading, account_lines))

    certificates = [
        certificate
        for result in report.results
        for certificate in (result.details.get(CERTIFICATES_KEY) or ())
    ]
    not_stated = [
        str(name)
        for certificate in certificates
        for name in (certificate.get("missing_reasons") or ())
    ]
    if not certificates:
        complete_lines = [
            "Nothing in this report measured that. No finding here says the reasons above are "
            "all the reasons, and nothing here should be read as saying they are."
        ]
    elif not not_stated:
        complete_lines = [
            f"{len(certificates)} decision(s) were re-run against the system's own inference. "
            "Every reason it found there is one the answer depended on, so none was shown to "
            "have been left unstated."
        ]
    else:
        complete_lines = [
            f"{len(not_stated)} further reason(s) the system's own answer depended on were not "
            "stated. Measured by re-running its inference, not inferred from its log:"
        ]
        complete_lines += [f'"{name}"' for name in not_stated]
    sections.append(("WHETHER THOSE WERE ALL THE REASONS", complete_lines))

    unattainable = [r for r in report.results if r.strength == Strength.UNATTAINABLE]
    unsettled = [
        r
        for r in report.results
        if r.strength is None and r.verdict != Verdict.NOT_APPLICABLE
    ]
    inapplicable = [r for r in report.results if r.verdict == Verdict.NOT_APPLICABLE]
    unchecked_lines = []
    if unattainable:
        unchecked_lines.append(
            f"{len(unattainable)} {_duties(len(unattainable))}: the system supplied nothing any "
            "check here could read, so it was not checked either way."
        )
    if unsettled:
        unchecked_lines.append(
            f"{len(unsettled)} {_duties(len(unsettled))}: no check in this report could settle "
            "it, so it was left open rather than answered."
        )
    if inapplicable:
        unchecked_lines.append(
            f"{len(inapplicable)} {_duties(len(inapplicable))}: not one this run applies to this "
            "system, so nothing here says it was met."
        )
    if unchecked_lines:
        sections.append(("WHAT THIS REPORT COULD NOT CHECK", unchecked_lines))

    return sections


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
    # What raised is named beside what was replayed, never left to be recovered from `--json`.
    # `trials` counts every input the search put through decide(); the ones that raised produced
    # no decision to read the property over, so a line stating only `trials` overstates what was
    # measured — and, where a summary elsewhere subtracts them, leaves two counts of one search
    # for the reader to reconcile.
    errored = budget.get("inputs_errored") or 0
    unmeasured = (
        f", {errored} of which raised rather than producing a decision, "
        f"leaving {budget['trials'] - errored} measured"
        if errored
        else ""
    )
    return (
        f"{budget['trials']} input(s) replayed{unmeasured}, seed {budget['seed']}, "
        f"input space: {fields or 'no field varied'}. Strategy: {budget['strategy']}{kind_limit}"
    )


def degree_sentence(reading: Mapping[str, Any]) -> str:
    """The one rendering of a truth degree there is, in text and in HTML alike.

    **This is the presentation rule of `docs/semantics.md` §9 in code.** A degree is never rendered
    as a percentage, never as a score, never as a verdict, and never alone: the numeral, the algebra
    it was combined over, and the authority, scale and method that fixed it are one sentence that
    cannot be split, because there is one function that writes it and no rendering formats the
    number by another route. A reader handed `0.7` reads *seventy percent compliant*; a reader
    handed this sentence reads what was assessed, by whom, and against what.

    `report.RequirementResult._validate_truth_degree` is the other half: a result cannot carry the
    numeral without the fields this sentence needs, so the sentence can never be short of them.
    """
    source = reading["source"]
    atoms = ", ".join(
        f"{name} at {value}" for name, value in sorted(dict(reading["atoms"]).items())
    )
    return (
        f"holds to degree {reading['degree']} over the {reading['algebra']} algebra "
        f"({atoms}). This is a measurement and not a verdict, and no share of one: the clause "
        f"states no threshold on it and this tool invents none. Degrees assessed by "
        f"{source['authority']}, on the scale {source['scale']}, by {source['method']}."
    )


#: What each evidence basis other than the behavioural one says about the rungs it cannot reach.
#: The behavioural basis is deliberately absent: it reaches every rung, so naming it on every
#: result would be a word every reader learns to skip, and the sentence a reader needs is the one
#: that explains a *ceiling*. `basis_sentence` is the only reader of this table.
_BASIS_SENTENCES = {
    EvidenceBasis.RELATIONAL: (
        "relational — this duty is a property of a pair of executions, and a decision record holds "
        "one. No length of decision log observes it, so the rungs it can reach are probed and "
        "proved; a system exposing only a log cannot discharge it, and that is a fact about the "
        "kind of property and not about how much the system exposed"
    ),
    EvidenceBasis.ARTIFACT: (
        "artifact — this duty is measured against the inference artefact behind a decision rather "
        "than against what the system decided. No trace holds that artefact and the enumeration is "
        "exact only on the one artefact it ran over, so the rungs above unattainable are recounted "
        "and probed, and neither observed nor proved is reachable however much the system exposes. "
        "Which of the two a verdict reaches is a fact about the artefact and not about the search: "
        "probed measures a reason set enumerated from a model encoding, recounted measures one the "
        "system recounted about its own inference"
    ),
    EvidenceBasis.ASSESSMENT: (
        "assessment — this duty rests on how an open-textured predicate applies, which a named "
        "authority settles and no engine here does. No rung of the strength lattice ranks it, "
        "because the lattice ranks ways of interrogating a system and no system was interrogated"
    ),
}


def basis_sentence(basis: EvidenceBasis) -> str | None:
    """The one wording of an evidence basis there is, in text and in HTML alike, or None.

    `degree_sentence` is the precedent and the standard: one function, so no surface can word the
    second coordinate of an evidence claim by another route and no two renderings can drift about
    what it means. The rule this sentence exists to keep is `docs/semantics.md` §10's — **a basis is
    a kind and never a rank** — and it keeps it by saying, in every place a basis is shown, which
    rungs this duty cannot reach and that the reason is the duty's rather than the system's. A bare
    word beside a rung word would be read as a fifth rung.

    Returns None for the behavioural basis, which is every duty whose evidence is about the system's
    own executions: it reaches every rung, there is no ceiling to explain, and a sentence on every
    result would be the noise that makes the other three unreadable.
    """
    return _BASIS_SENTENCES.get(EvidenceBasis.parse(basis))


def witness_sentence(result: Any) -> str | None:
    """The one wording of plug-in witness provenance on the text surface."""
    if result.strength is None or "engine_plugin" not in result.details:
        return None
    if result.witness_provenance == "witness-checked":
        return (
            "Witness provenance: witness-checked — this package re-derived the result from "
            "the engine plug-in's supplied witness."
        )
    return (
        "Witness provenance: trusted-ceiling — this package did not re-check a witness; "
        "the plug-in's declared ceiling is the only bound on this result."
    )


#: How each category of `_CATEGORY_LABELS` is drawn in the HTML report: (style class, icon).
#: Keyed by the same keys, so a category added there and forgotten here raises rather than
#: silently rendering no pill.
_CATEGORY_PILL_STYLE = {
    "proved": ("satisfied", "🏆"),
    "probed": ("satisfied", "🔍"),
    "recounted": ("satisfied", "🗣"),
    "observed": ("satisfied", "👁"),
    "violated": ("violated", "✖"),
    "inconclusive": ("inconclusive", "?"),
    "not_evaluated": ("inconclusive", "−"),
    # Drawn as an inconclusive pill and with no rung icon of its own, deliberately: this category
    # is a *kind* of evidence and not a rank, and an icon from the lattice row above would put it
    # in the ladder. See `basis_sentence`.
    "on_an_assessment": ("inconclusive", "≈"),
    "unattainable": ("unattainable", "⊘"),
    "not_applicable": ("not-applicable", "⊝"),
}


#: Icon per lattice rung. The rungs and their order come from `Strength` itself, so the drawn
#: lattice cannot disagree with the lattice the verdicts are computed on.
_STRENGTH_ICONS = {
    Strength.UNATTAINABLE: "⊘",
    Strength.OBSERVED: "👁",
    Strength.RECOUNTED: "🗣",
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


def render_text(report: ConformanceReport, audience: str | None = None) -> str:
        """Readable text rendering of the report, projected for `audience`.

        `audience` left `None` renders the full report, byte for byte as it always did; a name
        from `AUDIENCES` narrows what is shown and nothing else. Whatever the projection, the
        verdict of every requirement and the report's limits are printed.
        """
        view = _projection(audience)
        lines = [
            "CONFORMANCE REPORT",
            f"system: {report.system_name}",
        ]
        if view.overview:
            lines += [
                f"declared scope: {report.system_scope or 'undeclared'}",
                f"declared domains: {', '.join(report.system_domains) or 'undeclared'}",
            ]
        lines.append(f"pack: {report.pack_id}")
        if view.overview:
            lines.append(f"headline: {report.headline}")
        notice = report.undeclared_domain_notice
        if notice:
            lines.append(f"DUTIES NOT CHECKED: {notice}")
        if view.plain_account:
            for heading, body in _lay_sections(report):
                lines += ["", heading, *(f"    {line}" for line in body)]
        lines += [
            "",
            "REQUIREMENT FINDINGS:",
        ]
        for r in report.results:
            r._validate_probe_budget()
            if r.verdict == Verdict.NOT_APPLICABLE:
                tier = "NOT APPLICABLE"
            else:
                tier = r.strength.value.upper() if r.strength else "NOT EVALUATED"
            tier_tag = f"[{tier}]" if view.strength else ""
            interp_tag = " [INTERPRETIVE]" if view.legal_metadata and not r.binding else ""
            head = f"{tier_tag}{interp_tag} ".lstrip()
            lines.append(
                f"  {head}{r.requirement_id} ({r.source_clause}): {r.verdict.value}"
            )
            # Printed only where the basis is not the behavioural one, and directly under the
            # verdict line, because what it explains is the tier tag on that line: a `[PROBED]`
            # ceiling this system cannot raise reads as one it failed to.
            basis = basis_sentence(r.basis) if view.strength else None
            if basis:
                lines.append(f"    evidence basis: {basis}.")
            if view.signals:
                lines.append(f"    requires: {', '.join(r.signals_required)}")
            if view.legal_metadata and r.scope:
                lines.append(f"    scope limit: {r.scope}")
            if view.legal_metadata and r.domains:
                lines.append(f"    domain limit: {', '.join(r.domains)}")
            if view.missing_signals and r.signals_missing:
                lines.append(f"    MISSING SIGNALS: {', '.join(r.signals_missing)}")
            absent = r.details.get("signals_absent_from_trace")
            if view.signals and absent:
                lines.append(f"    ABSENT FROM TRACE: {', '.join(absent)}")
            if view.evidence_summary and r.evidence_summary:
                lines.append(f"    summary: {r.evidence_summary}")
            if view.evidence_summary and r.scope_boundary:
                lines.append(f"    {r.scope_boundary}")
            if view.evidence_summary:
                witness_note = witness_sentence(r)
                if witness_note:
                    lines.append(f"    {witness_note}")
            if (
                view.evidence_summary
                and r.verdict == Verdict.SATISFIED
                and r.formalized_subset_only
            ):
                lines.append(f"    {r.formalized_subset_note}")
            if view.evidence_summary:
                for finding in certificate_findings(r):
                    lines.append(
                        f"    certificate finding: {finding['verdict']} "
                        f"(decision {finding['decision_index']})"
                    )
            # A violated finding names the decision record it came from, the way the JSON
            # (`details.offending_trace_segment`) and HTML (witness table) renderings already
            # do: the record's own `decision_id` when it carries one, and the step index
            # otherwise, so a record without an identifier is still named rather than printed as
            # an empty label. Same identifier, same fallback — this is not a third convention.
            offending = r.details.get("offending_trace_segment")
            indices = r.details.get("violation_step_indices")
            if (
                view.witnesses
                and r.verdict == Verdict.VIOLATED
                and offending
                and indices
            ):
                named = []
                for step, record in zip(indices, offending, strict=False):
                    identifier = record.get("decision_id") if isinstance(record, dict) else None
                    if identifier is not None and str(identifier).strip():
                        named.append(f"decision {identifier} (step {step})")
                    else:
                        named.append(f"step {step}")
                plural = "" if len(named) == 1 else "s"
                lines.append(f"    offending record{plural}: {', '.join(named)}")
            # Both open-texture lines ride on `evidence_summary`, the flag that decides
            # whether this audience is shown an engine's account of what it established. They are
            # deliberately not a projection field of their own: the one audience that suppresses
            # that account is the affected individual, who is shown these duties by
            # `_lay_sections` as duties nothing settled, and a lay reader handed a number on a
            # lattice would read it as a score whatever sentence surrounded it.
            open_texture = r.details.get(OPEN_TEXTURE_KEY)
            if view.evidence_summary and open_texture:
                for atom in open_texture:
                    lines.append(
                        f"    open-textured predicate: whether {atom['signal']} is "
                        f"{atom['predicate']!r} is settled by {atom['authority']}, not here"
                    )
            reading = r.details.get(TRUTH_DEGREE_KEY)
            if view.evidence_summary and reading:
                lines.append(f"    truth degree: {degree_sentence(reading)}")
            budget = r.details.get(PROBE_BUDGET_KEY)
            if view.probe_budget and budget:
                lines.append(f"    probe budget: {_budget_line(budget)}")
        lines.extend(["", "LIMITS OF THIS REPORT", f"  {report.limits}"])
        return "\n".join(lines)


def render_html(
    report: ConformanceReport,
    commit_hash: str | None = None,
    command: str | None = None,
    extra_section_html: str | None = None,
    audience: str | None = None,
    provenance_note: str | None = None,
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

        `provenance_note` is one sentence appended to the provenance bar, escaped, and is empty
        unless a caller supplies it. It exists for the caller that can establish something about
        this report's origin that this module cannot: a page committed into the repository it
        describes can never name the commit that carries it — that commit does not exist when the
        page is rendered — but it can name the check that holds it to its command. The claim
        belongs to the caller for the same reason `extra_section_html` does. Nothing is guessed
        here and nothing is defaulted: a report whose caller says nothing says nothing.

        `audience` selects an `AudienceProjection` exactly as it does for `render_text`: it
        narrows which parts of this report are drawn and changes no verdict. `None` is the full
        page, unchanged, which is what every generated document under `docs/` is pinned to.
        """
        import html

        view = _projection(audience)

        if commit_hash is None:
            commit_hash, tree_state = _source_checkout()
        else:
            tree_state = "clean" if commit_hash else "unknown"

        counts = report.counts
        sys_name = html.escape(report.system_name)
        pack_name = html.escape(report.pack_id)
        sys_scope = html.escape(report.system_scope or "undeclared")
        sys_domains = html.escape(", ".join(report.system_domains) or "undeclared")
        headline_esc = html.escape(report.headline)
        limits_esc = html.escape(report.limits)
        c_short_esc = html.escape(commit_hash[:7]) if commit_hash else ""

        if c_short_esc:
            origin = f"from commit <code>{c_short_esc}</code>"
        elif tree_state == "modified":
            origin = "from a modified working tree, which no commit identifies"
        else:
            origin = "without an identified source commit"
        cmd_part = f" Command: <code>{html.escape(command)}</code>." if command else ""
        note_part = f" {html.escape(provenance_note)}" if provenance_note else ""
        provenance_html = (
            '<div class="provenance-bar">'
            f'<strong>Report Provenance:</strong> Generated {origin}.{cmd_part}{note_part}'
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

        notice = report.undeclared_domain_notice
        notice_html = (
            '<div class="headline-banner notice-banner">'
            '<div class="headline-title">Duties Not Checked</div>'
            f'<div class="notice-text">{html.escape(notice)}</div>'
            "</div>"
            if notice
            else ""
        )

        # Page-level optional blocks. Each carries the indentation the template spelled
        # inline, so the full view stays byte-for-byte the page that existed before.
        declared_meta_html = (
            '        <div class="meta-item">\n'
            '          <span class="meta-label">Declared Scope</span>\n'
            f'          <span class="meta-value">{sys_scope}</span>\n'
            "        </div>\n"
            '        <div class="meta-item">\n'
            '          <span class="meta-label">Declared Domains</span>\n'
            f'          <span class="meta-value">{sys_domains}</span>\n'
            "        </div>\n"
            if view.overview
            else ""
        )
        headline_block = (
            '    <div class="headline-banner">\n'
            '      <div class="headline-title">Executive Headline Summary</div>\n'
            f'      <div class="headline-text">{headline_esc}</div>\n'
            f"      {provenance_html}\n"
            "    </div>\n"
            if view.overview
            else ""
        )
        affected_person_card = (
            '    <aside class="affected-person-card" '
            'aria-label="For a person affected by a decision">\n'
            '      <div class="affected-person-card-title">'
            'For a person affected by a decision</div>\n'
            f'      <p>{html.escape(AFFECTED_PERSON_CARD_TEXT)}</p>\n'
            '    </aside>\n'
        )
        dashboard_block = (
            '    <section class="dashboard-section">\n'
            '      <div class="split-grid">\n'
            '        <div class="split-card">\n'
            '          <div class="split-card-header">\n'
            "            <span>Binding Duties</span>\n"
            f"            <span>{counts['binding_total']} total</span>\n"
            "          </div>\n"
            '          <div class="pill-group">\n'
            f"            {binding_pills}\n"
            "          </div>\n"
            "        </div>\n"
            '        <div class="split-card">\n'
            '          <div class="split-card-header">\n'
            "            <span>Interpretive Items</span>\n"
            f"            <span>{counts['interpretive_total']} total</span>\n"
            "          </div>\n"
            '          <div class="pill-group">\n'
            f"            {interp_pills}\n"
            "          </div>\n"
            "        </div>\n"
            "      </div>\n"
            "    </section>\n"
            if view.overview
            else ""
        )

        req_html_blocks = []
        for r in report.results:
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
            if not view.legal_metadata:
                binding_tag = scope_tag = domain_tag = ""

            # Verdict badge & card styling. An audience not shown the strength is not shown the
            # strength-derived badge either: `unattainable` is a rung, not a verdict, and a
            # reader who is told the rung is not being shown must still be told the verdict.
            is_unattainable = view.strength and r.strength == Strength.UNATTAINABLE
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

            # Strength Lattice render. The track shows the rungs *this duty's basis admits* and no
            # others: drawing all four for a duty that can only reach two showed a reader two steps
            # the system was one exposure away from, when nothing it could expose would reach them.
            # For the behavioural basis — every `record`, `logical` and `temporal` duty — the row is
            # all four rungs and the track is the one that has always been drawn.
            cur_rank = r.strength.rank if r.strength is not None else None
            lattice_spans = []
            for step in r.basis.rungs:
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
            # The sentence that keeps a shortened track from reading as an unfinished one, and the
            # basis word from reading as a rung. `basis_sentence` is the only place either is
            # worded, so this line and the text report's cannot drift.
            basis_note = basis_sentence(r.basis)
            if basis_note:
                lattice_html += (
                    f'<div class="lattice-basis">Evidence basis: '
                    f"{html.escape(basis_note)}.</div>"
                )
            # Each optional block carries the indentation the template used to spell inline, so
            # the full view is byte-for-byte the page that existed before projections did.
            lattice_block = (
                '          <div class="lattice-container">\n'
                '            <span class="lattice-label">Strength Lattice:</span>\n'
                f"            {lattice_html}\n"
                "          </div>"
                if view.strength
                else ""
            )

            # Signal tags
            req_signals = "".join(
                f'<span class="signal-tag">{html.escape(s)}</span>' for s in r.signals_required
            )
            signal_block = (
                '            <div class="signal-list">\n'
                f"              <strong>Requires Signals:</strong> {req_signals}\n"
                "            </div>"
                if view.signals
                else ""
            )
            summary_block = (
                f'            <div class="evidence-summary">{summary}</div>'
                if view.evidence_summary
                else ""
            )
            scope_boundary = r.scope_boundary
            scope_block = (
                f'            <div class="scope-boundary">{html.escape(scope_boundary)}</div>'
                if view.evidence_summary and scope_boundary
                else ""
            )
            subset_note = r.formalized_subset_note
            subset_block = (
                f'            <div class="subset-marker">{html.escape(subset_note)}</div>'
                if view.evidence_summary and subset_note
                else ""
            )

            details_html = ""
            witness_note = witness_sentence(r) if view.evidence_summary else None
            if witness_note:
                details_html += (
                    '<div class="witness-pill">'
                    f"{html.escape(witness_note)}"
                    "</div>"
                )
            if view.evidence_summary:
                for finding in certificate_findings(r):
                    details_html += (
                        '<div class="callout-box callout-violated">'
                        f"<strong>CERTIFICATE FINDING — "
                        f"{html.escape(finding['verdict'])}:</strong> "
                        f"decision {html.escape(str(finding['decision_index']))}"
                        "</div>"
                    )
            if view.missing_signals and r.signals_missing:
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
            if view.signals and absent_signals:
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
            if view.witnesses and offending_segment and violation_indices:
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

            open_texture = r.details.get(OPEN_TEXTURE_KEY)
            if view.evidence_summary and open_texture:
                atom_items = "".join(
                    "<li>whether <code>{}</code> is {} — settled by {}, not here</li>".format(
                        html.escape(str(atom["signal"])),
                        html.escape(repr(atom["predicate"])),
                        html.escape(str(atom["authority"])),
                    )
                    for atom in open_texture
                )
                details_html += (
                    '<div class="callout-box callout-unattainable">'
                    "<strong>NOT EVALUATED — Open-Textured Predicate:</strong>"
                    f"<ul>{atom_items}</ul>"
                    '<div class="callout-note">Nothing here says this duty is met and nothing '
                    "here says it is breached. The predicate has no sharp boundary and this tool "
                    "does not settle one in place of the named authority.</div>"
                    "</div>"
                )

            reading = r.details.get(TRUTH_DEGREE_KEY)
            if view.evidence_summary and reading:
                details_html += (
                    '<div class="callout-box callout-probe">'
                    "<strong>NOT EVALUATED — Truth Degree Measured:</strong><br>"
                    f"{html.escape(degree_sentence(reading))}"
                    '<div class="callout-note">A degree is a distinct evidence basis, not a '
                    "rescaled verdict: it is not a percentage of compliance and it carries no rung "
                    "of the evidence lattice.</div>"
                    "</div>"
                )

            probe_budget = r.details.get(PROBE_BUDGET_KEY)
            if view.probe_budget and probe_budget:
                # Named for the rung the result actually carries: the same search over a reason set
                # the system recounted is not a probed verdict, and a heading saying so would put
                # it on the rung above (`docs/semantics.md` §10, the presentation rule).
                searched = (
                    "RECOUNTED" if r.strength is Strength.RECOUNTED else "PROBED"
                )
                details_html += (
                    '<div class="callout-box callout-probe">'
                    f"<strong>{searched} — What Was Searched:</strong><br>"
                    f"{html.escape(_budget_line(probe_budget))}"
                    '<div class="callout-note">A bounded search, not a proof: the property is '
                    "unchecked outside the inputs named here.</div>"
                    "</div>"
                )

            counterexample = r.details.get("counterexample")
            if view.witnesses and counterexample and r.verdict == Verdict.VIOLATED:
                ce_str = ", ".join(
                    f"{html.escape(str(k))}: {html.escape(str(v))}"
                    for k, v in counterexample.items()
                )
                # A counterexample the solver derived and one a replay found are both concrete
                # inputs, and neither may be worded as the other: `probed` did not prove anything.
                kind = (
                    "Replayed"
                    if r.strength in (Strength.PROBED, Strength.RECOUNTED)
                    else "Formal"
                )
                details_html += (
                    '<div class="callout-box callout-violated">'
                    f"<strong>VIOLATED — {kind} Counterexample Input:</strong><br>"
                    f"<code>{ce_str}</code>"
                    "</div>"
                )

            # A projection that suppresses every part of a card's body leaves the body itself
            # behind: a confident verdict chip over an empty box, which reads as a finding with
            # nothing behind it rather than as a part deliberately not shown. The box is emitted
            # only when something goes in it. Every audience that shows an evidence summary
            # always fills it, so this changes no page that carries one — including the byte-
            # pinned `docs/report.html`.
            body_inner = (
                f"{signal_block}\n{summary_block}\n{scope_block}\n{subset_block}\n"
                f"            {details_html}"
            )
            body_block = (
                '          <div class="req-card-body">\n'
                f"{body_inner}\n"
                "          </div>\n"
                if body_inner.strip()
                else ""
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
{lattice_block}
{body_block}        </article>""")

        req_section_html = "\n".join(req_html_blocks)

        # The plain-language account, drawn with the classes the page already defines so this
        # carries no stylesheet of its own: the account is the neutral callout, the two sections
        # about what was not established are the dashed one every other gap on this page uses.
        account_html = ""
        if view.plain_account:
            blocks = []
            for index, (heading, body) in enumerate(_lay_sections(report)):
                tone = "callout-probe" if index == 0 else "callout-unattainable"
                items = "".join(
                    f"<p>{html.escape(line)}</p>" for line in body
                )
                blocks.append(
                    f'    <h2 class="section-title">{html.escape(heading.capitalize())}</h2>\n'
                    f'    <div class="callout-box {tone}">{items}</div>\n'
                )
            account_html = "".join(blocks)

        # The limits are a real disclaimer and no audience may lose them, so they are never cut.
        # For a lay reader they are also, unchanged, longer than everything else on the page put
        # together — a page whose largest element is a legal caveat is one that has told this
        # reader nothing. `<details>` keeps every word one click away and gives the account above
        # the page; it is a native element, so this needs no CSS and cannot fight the stylesheet.
        limits_block = (
            '      <details>\n'
            f'        <summary class="limits-header">Limits of this report</summary>\n'
            f'        <p class="limits-text">{limits_esc}</p>\n'
            "      </details>"
            if view.plain_account
            else (
                '      <h3 class="limits-header">Limits of this report</h3>\n'
                f'      <p class="limits-text">{limits_esc}</p>'
            )
        )

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
      /* ponytail: a system serif, not Newsreader as on the landing page — the report
         stays self-contained (one inlined woff2 would cost ~130KB for every CLI report).
         Upgrade path: subset Newsreader + data URI if the identity demands it. */
      --font-serif: Georgia, "Times New Roman", serif;

      /* Dossier palette: tinted neutrals in oklch, one accent (deletion red), color by role.
         Every colour is a token here so the dark block below is a second set of values,
         not a second stylesheet. Two rules keep both schemes legible:
         solid chips pair var(--ink)/var(--ok)/var(--warn) with var(--paper), which inverts
         with the scheme; and the report header keeps its own --band/--band-ink pair,
         because it is a dark band in both schemes rather than an inversion of the page. */
      --paper: oklch(96.6% 0.005 95);
      --surface: oklch(99.2% 0.003 95);
      --ink: oklch(24% 0.012 260);
      --ink-muted: oklch(45% 0.012 260);
      --ink-faint: oklch(56% 0.01 260);
      --line: oklch(88% 0.007 260);
      --line-strong: oklch(72% 0.01 260);
      --neutral-soft: oklch(95.5% 0.005 260);
      --band: oklch(24% 0.012 260);
      --band-ink: oklch(99.2% 0.003 95);
      --band-faint: oklch(72% 0.012 260);
      --band-line: oklch(42% 0.012 260);
      --band-accent: oklch(80% 0.06 25);

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

    /* Dark scheme. Scoped to `screen` on purpose: the @media print block below assumes the
       light tokens, so a dark OS setting must not follow the page onto paper. */
    @media screen and (prefers-color-scheme: dark) {{
      :root {{
        --paper: oklch(18% 0.008 260);
        --surface: oklch(22.5% 0.009 260);
        --ink: oklch(93% 0.006 95);
        --ink-muted: oklch(76% 0.008 260);
        --ink-faint: oklch(64% 0.008 260);
        --line: oklch(32% 0.01 260);
        --line-strong: oklch(45% 0.012 260);
        --neutral-soft: oklch(27% 0.009 260);
        --band: oklch(13.5% 0.01 260);
        --band-ink: oklch(95% 0.004 95);
        --band-faint: oklch(70% 0.012 260);
        --band-line: oklch(34% 0.012 260);
        --band-accent: oklch(78% 0.08 25);

        /* Violated red and satisfied green must stay far apart on a dark ground:
           the foreground pair is 72% L red against 78% L green, and each sits on its
           own tinted soft ground rather than on the shared page background. */
        --accent: oklch(66% 0.19 25);
        --accent-deep: oklch(78% 0.13 25);
        --accent-soft: oklch(27% 0.055 25);
        --accent-line: oklch(45% 0.11 25);

        --ok: oklch(78% 0.14 155);
        --ok-soft: oklch(26% 0.045 155);
        --ok-line: oklch(44% 0.08 155);

        --warn: oklch(80% 0.12 80);
        --warn-soft: oklch(27% 0.04 85);
        --warn-line: oklch(46% 0.07 85);
      }}
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
      color: var(--paper);
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
      background: var(--band);
      color: var(--band-ink);
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
      color: var(--band-faint);
      white-space: nowrap;
    }}
    .header-corner a {{ color: var(--band-accent); text-decoration: none; }}
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
      color: var(--band-accent);
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
      border-top: 1px solid var(--band-line);
    }}
    .meta-item {{ display: flex; flex-direction: column; gap: 0.15rem; }}
    .meta-label {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--band-faint);
    }}
    .meta-value {{
      font-size: var(--step-0);
      font-weight: 600;
      color: var(--band-ink);
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
    .notice-banner {{
      background: var(--warn-soft);
      border-color: var(--warn-line);
      border-left-color: var(--warn);
    }}
    .notice-banner .headline-title {{ color: var(--warn); }}
    .notice-text {{
      font-family: var(--font-serif);
      font-size: var(--step-0);
      font-weight: 600;
      line-height: 1.45;
      color: var(--warn);
      max-width: 70ch;
      text-wrap: pretty;
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
    .affected-person-card {{
      margin: var(--space-l);
      padding: var(--space-m) var(--space-l);
      background: var(--warn-soft);
      border: 1px solid var(--warn-line);
      border-left: 4px solid var(--warn);
      border-radius: var(--radius);
    }}
    .affected-person-card-title {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--warn);
      margin-bottom: var(--space-2xs);
    }}
    .affected-person-card p {{
      margin: 0;
      max-width: 75ch;
      font-size: var(--step-0);
      line-height: 1.45;
      color: var(--ink);
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
    /* `flex: 1 1 20rem` and not `flex: 1; min-width: 16rem`. With a zero basis and a floor
       narrower than a requirement identifier, this item was handed less width than its own
       content between roughly 768px and 1000px — wide enough for the desktop row, too narrow
       for a long identifier beside three badges — and the identifier overflowed *under* the
       badges instead of the badges wrapping. The basis is the width below which the row is
       not worth keeping, so the badge group drops to its own line before anything collides.
       `overflow-wrap` on the identifier is the backstop: an identifier is one unbreakable
       token, so at a real phone width no reflow can help and it must be allowed to break. */
    .req-title-group {{ flex: 1 1 26rem; min-width: 0; }}
    .req-id {{
      font-size: var(--step-0);
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--ink);
      letter-spacing: -0.01em;
      overflow-wrap: anywhere;
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
    .badge-binding {{ background: var(--ink); color: var(--paper); }}
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
      background: var(--ink); color: var(--paper); border-color: var(--ink); font-weight: 700;
    }}
    .lattice-step.active-probed {{
      background: var(--ok); color: var(--paper); border-color: var(--ok); font-weight: 700;
    }}
    .lattice-step.active-observed {{
      background: var(--ok); color: var(--paper); border-color: var(--ok); font-weight: 700;
    }}
    .lattice-step.active-unattainable {{
      background: var(--warn); color: var(--paper); border-color: var(--warn);
      font-weight: 700; border-style: dashed;
    }}
    .lattice-step.passed {{
      background: var(--neutral-soft); color: var(--ink-muted); border-color: var(--line-strong);
    }}
    .lattice-arrow {{ color: var(--line-strong); font-size: 0.72rem; }}
    /* The basis sentence takes its own line under the track — `flex-basis: 100%` inside the
       wrapping `.lattice-container` — so it reads as an account of the track and never as one
       more step on it. Existing tokens only, so both schemes and the print block inherit it. */
    .lattice-basis {{
      flex-basis: 100%;
      font-size: 0.78rem;
      font-style: italic;
      color: var(--ink-faint);
    }}

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
    .scope-boundary {{
      margin-top: var(--space-xs);
      padding: var(--space-xs);
      border-left: 3px solid var(--warn);
      background: var(--warn-soft);
      color: var(--ink);
      font-size: var(--step--1);
      max-width: 75ch;
    }}
    .witness-pill {{
      display: inline-block;
      margin-top: var(--space-xs);
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      background: var(--ink);
      color: var(--paper);
      font-family: var(--font-mono);
      font-size: 0.78rem;
    }}
    .subset-marker {{
      margin-top: var(--space-xs);
      color: var(--ink-muted);
      font-size: var(--step--1);
      font-style: italic;
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
          <a href="https://reasonsmith.dev/">&larr; landing</a> &middot; audit dossier
        </span>
      </div>
      <div class="meta-grid">
        <div class="meta-item">
          <span class="meta-label">System under test</span>
          <span class="meta-value">{sys_name}</span>
        </div>
{declared_meta_html}        <div class="meta-item">
          <span class="meta-label">Regulation Pack</span>
          <span class="meta-value">{pack_name}</span>
        </div>
      </div>
    </header>

{headline_block}
{affected_person_card}
    {notice_html}

    {extra_section}

{dashboard_block}
{account_html}    <h2 class="section-title" id="findings">Requirement Findings</h2>
    <main class="req-list">
{req_section_html}
    </main>

    <section class="limits-card">
{limits_block}
    </section>
    <footer class="dossier-foot">
      <span>reasonsmith &middot; audit-grade explanations</span>
      <span><a href="https://reasonsmith.dev/">landing</a> &middot; <a href="#top">top</a></span>
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
