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
SUPPORTED_FORMALISMS = ("record", "temporal", "logical")

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

    def render_text(self) -> str:
        """Readable text rendering of the report."""
        from reasonsmith.render import render_text

        return render_text(self)

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
        from reasonsmith.render import render_html

        return render_html(
            self, commit_hash=commit_hash, command=command, extra_section_html=extra_section_html
        )


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

    **Every state fragment admits a trace rung, `logical` included.** A `logical` property is a
    property of one decision record — that is what puts it in `STATE_FRAGMENTS` — so a trace of
    decision records is evidence about it, and a build that refused to read one reported *not
    evaluated* while the evidence sat in front of it. That was a defect, not a policy: the label
    on the fragment was deciding what could be checked, which is the thing fragment classification
    was introduced to stop. Which engine reads the trace still depends on the shape: a presence
    conjunction keeps the record engine and its per-signal, per-record diagnostics, and every other
    state formula is monitored per record by `ObservedEngine`, whose rtamt monitor scores a
    non-temporal formula pointwise and names the record positions that breached.

    Temporal properties reach only the observed engine, and that ceiling is unchanged. The solver
    and the replay search both reason about one decision at a time and have nothing to say about a
    formula quantified over the trace; there is no temporal engine above `observed` in this build,
    and inventing a rung for one would be the overclaim this package exists to refuse.

    One duty is deliberately given a ladder of **one** rung: a duty gating on
    `engines.certificate.DELETED_REASON_COUNT` asks whether the reasons a decision states are all
    the reasons its inference had, and that is measured against the inference artefact or not at
    all. Every other rung here would answer a weaker question off the system's own log — that the
    reason field is non-blank, or that the number the system wrote in it is small — and reporting
    either in place of the measurement is the substitution the certificate engine exists to
    remove. A system exposing no artefact is therefore reported *unattainable* by that engine
    rather than falling through to a presence check.
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
    )
