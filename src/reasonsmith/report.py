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
    §3.5, including the case where exposed logic and trace disagree. One duty has a single-rung
    ladder, for the opposite reason: a weaker rung on a reason-adequacy duty would answer a
    *different* property off the system's own log — see `_engine_ladder`.
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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
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
SUPPORTED_FORMALISMS = ("record", "temporal", "logical", "counterfactual")

#: Where a probed result carries the search that produced it, and the fields that search must
#: name. A probed verdict is a statement about a bounded search — how many inputs were replayed,
#: how they were generated and from which seed — so a result that does not carry them cannot be
#: constructed at all (see `RequirementResult.__post_init__`), rather than being rendered without
#: them and read as if the property had been established for every input.
PROBE_BUDGET_KEY = "probe_budget"
PROBE_BUDGET_FIELDS = ("trials", "strategy", "seed", "input_space")
_UNREAD = object()

#: Where a not-applicable result records that the *system* said nothing, rather than that it said
#: something else. The two are not the same finding: a declared domain that does not meet the
#: duty's is an answer, while an undeclared one is a missing input, and a run that skipped duties
#: for a missing input must not read like a run that checked them. Carried as a flag rather than
#: left to be recovered from the reason prose, so every rendering asks the result rather than
#: parsing a sentence that is free to be reworded.
UNDECLARED_DOMAIN_KEY = "skipped_for_undeclared_domain"

#: Where a result produced by an installed engine plug-in records which plug-in produced it and
#: what ceiling that plug-in declared. Both halves are load-bearing. The name is provenance: a
#: reader of a verdict must be able to see that a third-party engine answered, and this package
#: refuses an invisible provenance everywhere else. The ceiling is the claim the plug-in made
#: about itself, and `__post_init__` refuses a result carrying a strength above it — an engine
#: declaring `probed` and returning `proved` has its result refused rather than trusted. See
#: `reasonsmith.plugins` and `docs/authoring-engines.md`.
ENGINE_PLUGIN_KEY = "engine_plugin"

#: Where the certificate engine records one entry per decision it certified. Named here rather
#: than spelled twice because a rendering reads it: a reader who is shown "the reasons stated were
#: not all the reasons" is being shown this measurement and nothing else.
CERTIFICATES_KEY = "certificates"

#: The version of the `--json` envelope's *shape*, carried as `schema_version` on every
#: `ConformanceReport.to_dict()`. It is a single integer and it is not the package version:
#: a consumer reads it to know which keys to expect, and pinning it to `__version__` would make
#: every release look like a shape change. The convention, stated in README, "The CLI", is that
#: it increments when an existing key is **removed, renamed, or changes type or meaning** —
#: anything a parser written against the previous number could get wrong — and does **not**
#: increment when a key is added, because a consumer reading known keys is unaffected.
#: `tests/test_json_schema_version.py` pins the key set at each level to this number, so a
#: change to the shape fails the suite until this number moves with it.
JSON_SCHEMA_VERSION = 1

#: The two signals a decision record is read for when a report is asked what the system itself
#: said about a decision: what it recorded as the decision, and what it stated as the reason.
#:
#: Naming two pack signals here is a real coupling and is deliberate. It is the same coupling
#: `engines/certificate.py` already carries for `artifact_logs_deleted_reason_count`, and it buys
#: the one thing a lay rendering cannot do without: the system's own words. Anything wider — a
#: rendering that guessed which of a record's fields is "the reason" — would be this package
#: inventing an explanation, which is the line `docs/semantics.md` §7 refuses to cross.
DECISION_RECORD_SIGNAL = "artifact_logs_decision_record"
REASON_SIGNAL = "artifact_logs_reason_explanation"


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

        # A plug-in cannot report above the ceiling it declared. Refused here rather than trusted
        # and rendered, for the same reason the probe budget is: an installed package this
        # repository never audited must not be able to make the tool claim more than it has.
        self._validate_plugin_claim()

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

    def _validate_plugin_claim(self) -> None:
        """Refuse a plug-in result claiming a strength above the ceiling the plug-in declared."""
        plugin = self.details.get(ENGINE_PLUGIN_KEY)
        if plugin is None:
            return
        if not isinstance(plugin, Mapping) or not plugin.get("name"):
            raise ValueError(
                f"{self.requirement_id}: details[{ENGINE_PLUGIN_KEY!r}] must be a mapping naming "
                f"the plug-in that produced this result; got {plugin!r}"
            )
        try:
            ceiling = Strength.parse(plugin["max_strength"])
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"{self.requirement_id}: the plug-in {plugin.get('name')!r} must declare the "
                f"maximum strength it may report in details[{ENGINE_PLUGIN_KEY!r}]"
                f"['max_strength']: {exc}"
            ) from exc
        if self.strength is not None and self.strength > ceiling:
            raise ValueError(
                f"{self.requirement_id}: the engine plug-in {plugin['name']!r} declared a maximum "
                f"strength of {ceiling} but reported {self.strength}; the result is refused. "
                "reasonsmith does not audit a plug-in, so the ceiling it declares is the only "
                "bound on what it may claim — see docs/authoring-engines.md."
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
class DecisionAccount:
    """What one decision record says the system decided, and the reason it stated for it.

    Both fields are the system's own words, copied out of the trace this run already read and
    never rewritten: `decision` is whatever the record carried under `DECISION_RECORD_SIGNAL`
    and `reason` whatever it carried under `REASON_SIGNAL`, with a mapping flattened the way
    every other rendering of a decision record in this package flattens one. Either may be the
    empty string, which is the record saying nothing there — a distinct thing from a record this
    run never read, and the renderings keep the two apart.

    Nothing here is a measurement and nothing here is an explanation. A reader shown these two
    strings has been shown the log, which is the only thing this package can honestly tell a
    person about *why*; whether they are all the reasons is a separate finding, and only
    `engines/certificate.py` produces it.
    """

    decision: str = ""
    reason: str = ""


def _account_text(value: Any) -> str:
    """One decision-record field as text, or `""` when the record carried nothing there."""
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    return str(value).strip()


def decision_accounts(records: Iterable[Mapping[str, Any]]) -> tuple[DecisionAccount, ...]:
    """The decisions a trace states, in trace order, skipping records that state neither.

    A record carrying neither a decision nor a reason yields no account at all rather than an
    empty one: a rendering that emitted a heading over a blank line would be reporting a decision
    it does not have, which is the defect this type exists to remove rather than relocate.
    """
    accounts = []
    for record in records:
        account = DecisionAccount(
            decision=_account_text(record.get(DECISION_RECORD_SIGNAL)),
            reason=_account_text(record.get(REASON_SIGNAL)),
        )
        if account.decision or account.reason:
            accounts.append(account)
    return tuple(accounts)


@dataclass(frozen=True)
class ConformanceReport:
    """Report summarizing conformance of a System Under Test against a Pack.

    `decisions` carries what the trace this run read said about each decision, in the system's
    own words (`DecisionAccount`). It is an input this run already read and not a finding, which
    is why it is not in `to_dict`: the JSON record is the findings record, and a conformance
    document is not the place a production decision log gets republished. A rendering that shows
    it — today only the affected-individual projection — is quoting the log, never summarising it.
    """

    pack_id: str
    system_name: str
    results: tuple[RequirementResult, ...]
    system_scope: str | None = None
    system_domains: tuple[str, ...] = ()
    limits: str = LIMITS
    decisions: tuple[DecisionAccount, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "system_domains", normalize_domains(self.system_domains))
        object.__setattr__(self, "decisions", tuple(self.decisions))

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

    @property
    def skipped_for_undeclared_domain(self) -> tuple[str, ...]:
        """The duties reported not applicable *solely* because this system declared no domain.

        A declared domain that does not meet a duty's is not counted here: that duty was answered,
        not skipped for want of an input.
        """
        return tuple(
            r.requirement_id for r in self.results if r.details.get(UNDECLARED_DOMAIN_KEY)
        )

    @property
    def undeclared_domain_notice(self) -> str | None:
        """The one sentence every rendering owes a reader when duties went unchecked, or None.

        A run that skipped duties for a missing declaration exits exactly as a run that checked
        them does — only a violation exits non-zero, and that is deliberate (`docs/semantics.md`
        §4). So the report itself has to carry what the exit code cannot, in the place a reader
        cannot miss and in every format, or a compliance gate goes green and stays green over
        duties nothing here looked at.
        """
        skipped = self.skipped_for_undeclared_domain
        if not skipped:
            return None
        duties = "duty was" if len(skipped) == 1 else "duties were"
        return (
            f"{len(skipped)} domain-limited {duties} reported not applicable without being "
            "checked, because this system declares no decision domain. Nothing in this report "
            "says those duties are met. Declare what kind of decision this system makes — "
            "--system-domain <domain>, repeatable, or a system_domains attribute on the "
            "adapter — and run it again; docs/authoring-packs.md names the vocabulary."
        )

    def render_text(self, audience: str | None = None) -> str:
        """Readable text rendering of the report, projected for `audience`.

        `audience` left `None` renders the full report; see `reasonsmith.render.AUDIENCES` for
        the five projections and `docs/semantics.md` §7 for why each shows what it shows.
        """
        from reasonsmith.render import render_text

        return render_text(self, audience=audience)

    def render_html(
        self,
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

        `provenance_note` is one caller-owned sentence appended to the provenance bar, for an
        origin claim this package cannot establish for itself — see `render.render_html`.

        `audience` selects an audience projection, exactly as it does for `render_text`.
        """
        from reasonsmith.render import render_html

        return render_html(
            self,
            commit_hash=commit_hash,
            command=command,
            extra_section_html=extra_section_html,
            audience=audience,
            provenance_note=provenance_note,
        )


    def to_dict(self) -> dict:
        return {
            "schema_version": JSON_SCHEMA_VERSION,
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

    def records_read(self) -> list[dict[str, Any]]:
        """The trace this run actually read, and never a read it did not need.

        Deliberately not `trace()`: the promise that a run which needed no trace never executed
        the system is the whole of `analyze_unattainable`'s guarantee, and a report asking after
        the fact what the decisions were must not be what breaks it. A trace nothing read, and a
        trace whose read raised, are both reported here as no decisions.
        """
        if self._records is _UNREAD or self._records is None:
            return []
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
    """The regulatory class this run is judging against — the argument, or the system's own.

    Refused here, beside `_declared_domains` and on the same terms, rather than at the first
    requirement that happens to be class-limited: a pack with no requirements, or none carrying
    a class, would otherwise end in a clean run on a misspelled one. The value returned is the
    declaration as it was given, because that is what a report prints back to its reader.
    """
    if system_scope is None:
        system_scope = getattr(sut, "system_scope", getattr(sut, "declared_scope", None))
    normalize_scope(system_scope, "declared system scope")
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


def _not_applicable(
    req: Requirement, summary: str, details: dict[str, Any] | None = None
) -> RequirementResult:
    """The not-applicable result: no strength, no missing signals, nothing about the system."""
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.NOT_APPLICABLE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=summary,
        details=dict(details or {}),
        binding=req.binding,
        scope=req.scope,
        domains=req.domains,
    )


def _inapplicability(
    req: Requirement, sys_scope_norm: str, sys_domains: tuple[str, ...], system_scope: Any
) -> tuple[str, dict[str, Any]] | None:
    """Why this duty does not reach this system, and what that is, or None when it does.

    The second element is the details a result carries away from here. A duty skipped because
    the system declared *no* decision domain is flagged with `UNDECLARED_DOMAIN_KEY`: that is a
    missing input rather than an answer, and every rendering says so. A duty skipped because the
    system declared a domain that is simply not this duty's carries nothing — that one is a real
    answer, and warning about it would train a reader to ignore the warning that matters.

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
            f"class is {desc}. reasonsmith never infers a system's regulatory class.",
            {},
        )
    if req.domains and not (set(req.domains) & set(sys_domains)):
        desc = f"declared as {', '.join(sys_domains)}" if sys_domains else "undeclared"
        return (
            f"Not applicable: this duty is about {', '.join(req.domains)} decisions, but the "
            f"system's decision domain is {desc}. reasonsmith never infers a system's decision "
            "domain, and the domain vocabulary is the pack author's rather than the "
            "regulation's — see docs/authoring-packs.md.",
            {} if sys_domains else {UNDECLARED_DOMAIN_KEY: True},
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
        return _not_applicable(req, *inapplicable)

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
    engine: Any = None,
) -> RequirementResult:
    """The proof rung, with a broken `logic()` reported rather than raised.

    `engine` names which solver-backed engine answers — `ProvedEngine` for a state property, and
    `engines.temporal.TemporalProofEngine` for an `always(f)` quantified over the trace. One
    function for both, because the handling of a `logic()` that raises is a property of the rung
    and not of the engine standing on it, and two copies of it would drift.

    `logic()` is an optional interface, and one that raises has established nothing — which is
    what `strength=None` means. Letting the exception out would take the whole evaluation down
    with it, so a duty whose trace the record engine could have read would lose a verdict it had
    the evidence for. A malformed *trace* is deliberately not treated this way: that is the
    system's own decision log coming back the wrong shape, and it still raises and names the
    system.
    """
    if engine is None:
        from reasonsmith.engines.proved import ProvedEngine

        engine = ProvedEngine

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
    result = engine.evaluate(req, sut, records, logic_data=logic_data)
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

    **Every state fragment admits a trace rung, `logical` included.** A `logical` property is a
    property of one decision record — that is what puts it in `STATE_FRAGMENTS` — so a trace of
    decision records is evidence about it, and a build that refused to read one reported *not
    evaluated* while the evidence sat in front of it. That was a defect, not a policy: the label
    on the fragment was deciding what could be checked, which is the thing fragment classification
    was introduced to stop. Which engine reads the trace still depends on the shape: a presence
    conjunction keeps the record engine and its per-signal, per-record diagnostics, and every other
    state formula is monitored per record by `ObservedEngine`, whose rtamt monitor scores a
    non-temporal formula pointwise and names the record positions that breached.

    **A temporal duty reaches the proof rung only in the one shape that reduces to a state
    property.** `always(f)`, over a finite trace, holds exactly when `f` holds at every position,
    and every position is a decision the exposed logic produces — so `engines.temporal`'s reduction
    hands the solver a property about one decision, which is the only kind it can answer. Every
    other temporal shape stops at `observed` as it always did, because a solver reasoning about one
    decision at a time still has nothing to say about it, and inventing a rung for one would be the
    overclaim this package exists to refuse. The rung is selected from the *shape of the spec* as
    well as from the exposed surface, which is why `state_property_under_always` is consulted here:
    appending a rung that will always report not-evaluated would make every non-`always` temporal
    duty pay for a solver call that cannot answer it.

    **The `counterfactual` fragment has no trace rung, and returns before every other rung is
    considered.** `counterfactually_invariant(outcome, protected)` is a property of a *pair* of
    executions: hold every input fixed, move one named variable, and the decision must not move. A
    trace holds what the system decided and a counterfactual asks what it would have decided, so no
    length of decision log establishes one — reading the atom off a record is refused by
    `rulelang.eval_expression` itself, which is why this is a fact about the code rather than a
    convention this function is trusted to keep. Two rungs remain, both of which *run* the system:
    the solver encoding the declared rules twice, and the paired replay running `decide()` on a
    recorded decision and on its twin. Neither is appended alongside a plug-in rung, for the reason
    the certificate duty below returns early: an installed package this repository never audited
    must not be able to answer a counterfactual duty off a log either.

    One duty is deliberately given a ladder of **one** rung: a duty gating on
    `engines.certificate.DELETED_REASON_COUNT` asks whether the reasons a decision states are all
    the reasons its inference had, and that is measured against the inference artefact or not at
    all. Every other rung here would answer a weaker question off the system's own log — that the
    reason field is non-blank, or that the number the system wrote in it is small — and reporting
    either in place of the measurement is the substitution the certificate engine exists to
    remove. A system exposing no artefact is therefore reported *unattainable* by that engine
    rather than falling through to a presence check. That single rung stays single: the plug-in
    rungs below are appended after it has already returned, so no installed package can answer that
    duty off the system's log either.

    Engines an installed package supplies (entry-point group `reasonsmith.engines`) join the ladder
    at the ceiling each declares, which is exactly what makes "a new engine is reached the moment it
    exists" mean *installed* rather than *in this tree*. What a plug-in may claim, and what happens
    when one misbehaves, is `reasonsmith.plugins` and `docs/authoring-engines.md`.
    """
    from reasonsmith.engines.certificate import DELETED_REASON_COUNT

    if DELETED_REASON_COUNT in req.requires:
        from reasonsmith.engines.certificate import CertificateEngine
        return [
            (
                Strength.PROBED,
                lambda: CertificateEngine.evaluate(
                    req, sut, records if records is not None else resources.trace()
                ),
            )
        ]

    if req.formalism == "counterfactual":
        from reasonsmith.engines.counterfactual import (
            CounterfactualProofEngine,
            PairedReplayEngine,
        )

        counterfactual: list[tuple[Strength, Any]] = []
        if callable(getattr(sut, "logic", None)):
            counterfactual.append(
                (
                    Strength.PROVED,
                    lambda: _run_proof_rung(
                        req, sut, records, resources, engine=CounterfactualProofEngine
                    ),
                )
            )
        counterfactual.append(
            (
                Strength.PROBED,
                lambda: PairedReplayEngine.evaluate(
                    req,
                    sut,
                    records,
                    trace_provider=resources.trace if records is None else None,
                ),
            )
        )
        return counterfactual

    ladder: list[tuple[Strength, Any]] = []

    if req.formalism == "temporal" and callable(getattr(sut, "logic", None)):
        from reasonsmith.engines.temporal import (
            TemporalProofEngine,
            state_property_under_always,
        )
        if state_property_under_always(req.spec) is not None:
            ladder.append(
                (
                    Strength.PROVED,
                    lambda: _run_proof_rung(
                        req, sut, records, resources, engine=TemporalProofEngine
                    ),
                )
            )

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

    # `record` is checked first and keeps the record engine. That is not an ordering detail: the
    # record engine walks a presence conjunction conjunct by conjunct and names *which* signal was
    # missing from *which* record, and the rtamt monitor below cannot, because robustness is one
    # number for the whole formula. Routing presence through the monitor to make the two branches
    # look alike would trade that diagnostic away for nothing.
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
    elif req.formalism in ("temporal", "logical"):
        from reasonsmith.engines.observed import ObservedEngine
        ladder.append(
            (
                Strength.OBSERVED,
                lambda: ObservedEngine.evaluate(
                    req, sut, records if records is not None else resources.trace()
                ),
            )
        )

    # Engines an installed package supplies, each at the ceiling it declared. Appended last, so at
    # an equal rung a built-in is tried first and a plug-in answers only what the built-in left
    # un-established. Nothing else about the ladder changes: with no plug-in installed this is the
    # empty list, and `_engine_ladder` returns exactly what it returned before.
    from reasonsmith.plugins import engine_rungs
    ladder.extend(
        engine_rungs(
            req, sut, lambda: records if records is not None else resources.trace()
        )
    )

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
        decisions=decision_accounts(resources.records_read()),
    )
