"""Conformance report skeleton and unattainable analysis for reasonsmith v0.10.2.

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
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, replace
from typing import Any, cast

from reasonsmith.artifacts import RECOUNTED_REASONS
from reasonsmith.manyvalued import DEGREE_SOURCE_FIELDS
from reasonsmith.rulelang import (
    STATE_FRAGMENTS,
    UnsupportedConstructError,
    counterfactual_atom,
    is_present,
    parse_property,
    statistical_atom,
    undetermined_atoms,
)
from reasonsmith.spec import (
    FRONTIER_TRIGGER,
    Pack,
    Requirement,
    normalize_domains,
    normalize_frontier_ai_status,
    normalize_scope,
)
from reasonsmith.statistical import (
    PROXY_BLINDNESS_LIMIT,
    measure_selection_rates,
    validate_measurement_payload,
)
from reasonsmith.statistical import (
    STATISTICAL_MEASUREMENT_KEY as STATISTICAL_PAYLOAD_KEY,
)
from reasonsmith.sut import (
    EVENT_TIME,
    ORDINAL_TIME,
    TIME_DOMAIN_KEY,
    SystemUnderTest,
    _validate_capability_collection,
    read_time_domain,
)
from reasonsmith.verdict import EvidenceBasis, Strength, Verdict

LIMITS = (
    "This report is not a compliance guarantee and is not legal advice. It assesses system "
    "capability information and trace evidence against formal specifications. Whether these "
    "findings discharge legal duties remains a determination this tool does not make and cannot "
    "make. A requirement reported without a strength was not evaluated or is not applicable, "
    "and no verdict on it should be read from this report. "
    "Recital and guidance items inform how statutory duties are interpreted but create no "
    "obligation of their own; interpretive requirements are evaluated and reported separately, "
    "and are never folded into the binding headline counts. A requirement reported not "
    "applicable was excluded on one of the independent gates. Either no regulatory class was "
    "declared for the system at all, or the class that was declared is not the one the "
    "requirement is limited to; or no decision domain was declared for the system at all, or "
    "none of the domains that were declared is one the requirement is about; or the Seoul pack "
    "self-asserted frontier_ai_status is undeclared or not-frontier. This tool infers neither "
    "the class nor the domain, and it does not infer frontier status, so an undeclared system is "
    "neither placed in scope nor "
    "cleared of the duty: read the declared scope, domain, and frontier-status lines before "
    "reading "
    "a not-applicable result. The decision-domain vocabulary is written by the pack author and by "
    "no regulation, and a duty declaring no domain reaches every system it is run against. A wrong "
    "frontier declaration remains an audited-system overclaim."
)

#: Formalisms this build can actually evaluate. `undetermined` and `graded` are on this list and
#: neither reaches an engine: what this build does with one is refuse it in a way a reader can act
#: on, which is an evaluation of the duty and not the absence of one.
SUPPORTED_FORMALISMS = (
    "record",
    "temporal",
    "logical",
    "counterfactual",
    "statistical",
    "undetermined",
    "graded",
)

#: Where a result records that the duty rests on an open-textured predicate no engine here settles,
#: and who would settle it. Both halves are the finding: a `not evaluated` that does not name the
#: authority is the ordinary un-evaluated result this construct exists to stop being the answer.
OPEN_TEXTURE_KEY = "open_texture"

#: The fields that key carries, per atom. Named here for the reason `PROBE_BUDGET_FIELDS` is: a
#: rendering asks the result rather than parsing a sentence that is free to be reworded.
OPEN_TEXTURE_FIELDS = ("signal", "predicate", "authority")

#: Where a result carries a truth degree measured over a declared algebra against a declared
#: grading. Everything about this key is a refusal in the shape of a data structure, and
#: `RequirementResult._validate_truth_degree` is where each one bites:
#:
#: - the degree may not travel without `algebra` and without all of `DEGREE_SOURCE_FIELDS`, which is
#:   constraint B of this design — a degree with no account of who fixed the scale is a figure;
#: - a result carrying one may not carry a strength, because a truth degree is a **distinct evidence
#:   basis and not a rescaled verdict**: nothing here turns `0.7` into seventy percent of a verdict,
#:   and no rung of the lattice means "graded".
TRUTH_DEGREE_KEY = "truth_degree"

#: A statistical result is a measurement beside a not-evaluated outcome in the first wave.
STATISTICAL_MEASUREMENT_KEY = STATISTICAL_PAYLOAD_KEY

#: The fields that key carries. `atoms` is every graded atom's own degree, so a reader sees what the
#: algebra combined rather than only what it produced.
TRUTH_DEGREE_FIELDS = ("degree", "algebra", "atoms", "source")

#: Where a probed result carries the search that produced it, and the fields that search must
#: name. A probed verdict is a statement about a bounded search — how many inputs were replayed,
#: how they were generated and from which seed — so a result that does not carry them cannot be
#: constructed at all (see `RequirementResult.__post_init__`), rather than being rendered without
#: them and read as if the property had been established for every input.
PROBE_BUDGET_KEY = "probe_budget"
PROBE_BUDGET_FIELDS = ("trials", "strategy", "seed", "input_space")
_UNREAD = object()


def jsonable_finite(value: float) -> bool:
    """Whether a numeric search datum is finite and JSON-safe."""
    return math.isfinite(value)

#: Where a not-applicable result records that the *system* said nothing, rather than that it said
#: something else. The two are not the same finding: a declared domain that does not meet the
#: duty's is an answer, while an undeclared one is a missing input, and a run that skipped duties
#: for a missing input must not read like a run that checked them. Carried as a flag rather than
#: left to be recovered from the reason prose, so every rendering asks the result rather than
#: parsing a sentence that is free to be reworded.
UNDECLARED_DOMAIN_KEY = "skipped_for_undeclared_domain"

#: Where a Seoul-pack result records the self-asserted frontier applicability gate.
FRONTIER_GATE_KEY = "frontier_ai_status"

#: Where a result produced by an installed engine plug-in records which plug-in produced it and
#: what ceiling that plug-in declared. Both halves are load-bearing. The name is provenance: a
#: reader of a verdict must be able to see that a third-party engine answered, and this package
#: refuses an invisible provenance everywhere else. The ceiling is the claim the plug-in made
#: about itself, and `__post_init__` refuses a result carrying a strength above it — an engine
#: declaring `probed` and returning `proved` has its result refused rather than trusted. See
#: `reasonsmith.plugins` and `docs/authoring-engines.md`.
ENGINE_PLUGIN_KEY = "engine_plugin"

#: Where a plug-in result records the witness provenance established by this package. The
#: payload is retained for an independently re-checkable witness; a refuted payload is kept under
#: ``unverified_payload`` instead and never rendered as a finding.
WITNESS_KEY = "witness"
WITNESS_FIELDS = ("kind", "provenance", "checker", "payload")
WITNESS_KINDS = (
    "trace_position",
    "presence_absence",
    "input_valuation",
    "execution_pair",
    "position_certificate",
    "trace_prefix",
    "event_pair",
)
WITNESS_PROVENANCES = ("witness-checked", "trusted-ceiling")

#: Where the certificate engine records one entry per decision it certified. Named here rather
#: than spelled twice because a rendering reads it: a reader who is shown "the reasons stated were
#: not all the reasons" is being shown this measurement and nothing else.
CERTIFICATES_KEY = "certificates"

#: Where the certificate engine records the full machine record of each certificate it produced —
#: one entry per certified decision, each carrying the per-reason verdicts the summary under
#: `CERTIFICATES_KEY` collapses to counts and names. Absent on a result the certificate engine
#: did not settle, so `in` rather than a value read means "a certificate exists here". The two
#: keys are a deliberate pair: `CERTIFICATES_KEY` is the summary a rendering already reads, and
#: this is the full record that summary was condensed from.
CERTIFICATE_KEY = "certificate"

#: Where the semantics-agreement certificate records the margin used for each decision. The
#: distinction is part of the evidence: an exposed threshold yields a reasonsmith measurement,
#: while silence retains the decision record's declared margin rather than guessing one.
DECISION_MARGINS_KEY = "decision_margins"

#: Where a result measured against an inference artefact records whether the reason set it was
#: measured against was *enumerated* from a model encoding or *recounted* by the system. False caps
#: the result at `Strength.RECOUNTED`, and `__post_init__` refuses one that claims higher — the
#: structural form of the rule `docs/semantics.md` §3 used to state in prose and gate a second
#: artefact family on. See `artifacts.RECOUNTED_REASONS`.
EXACT_REASON_SET_KEY = "reason_set_is_exact"

#: The version of the `--json` envelope's *shape*, carried as `schema_version` on every
#: `ConformanceReport.to_dict()`. It is a single integer and it is not the package version:
#: a consumer reads it to know which keys to expect, and pinning it to `__version__` would make
#: every release look like a shape change. The convention, stated in docs/semantics.md §7, is that
#: it increments when an existing key is **removed, renamed, or changes type or meaning** —
#: anything a parser written against the previous number could get wrong — and does **not**
#: increment when a key is added, because a consumer reading known keys is unaffected.
#: `tests/test_json_schema_version.py` pins the key set at each level to this number, so a
#: change to the shape fails the suite until this number moves with it.
#:
#: Version 2 adds `time_domain` and is a bump under that rule rather than in spite of it: adding
#: the key is not what moved the number, the *meaning* of every temporal verdict in the envelope
#: did. Under version 1 a bound in a temporal `spec` counted records, and that a reader had to
#: know from `docs/semantics.md` §2 rather than from the document in front of them. Version 2
#: states the clock the run was answered on, so a parser can tell a verdict counted in decisions
#: from one counted on any later domain instead of assuming the first.
#:
#: Version 2 has since grown `basis`, `verbatim_text` and `details.certificate` without a bump,
#: deliberately: each is a key added beside keys a parser already reads, and the convention above
#: says addition is not a shape change. The decision was made in `tests/test_json_schema_version.py`
#: rather than skipped.
JSON_SCHEMA_VERSION = 2

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


def certificate_findings(result: "RequirementResult") -> list[dict[str, Any]]:
    """Expose failed certificate measurements as findings without changing the duty verdict."""
    return [
        {
            "type": "certificate",
            "verdict": "FAIL",
            "decision_index": certificate.get("decision_index"),
        }
        for certificate in (result.details.get(CERTIFICATES_KEY) or ())
        if certificate.get("certificate_verdict") == "FAIL"
    ]


_FORMALIZED_SUBSET_MARKERS = (
    "nothing here decides",
    "nothing here says",
    "nothing here measures",
    "nothing here captures",
    "cannot see",
    "does not see",
    "does not measure",
    "does not capture",
    "does not determine",
    "not formalised",
    "not formalized",
    "unformalised",
    "unformalized",
    "presence cannot",
    "never read",
    "never measures",
    "outside every engine",
    "not a determination",
    "omission is deliberate",
    "does not test",
    "cannot test",
    "does not fix",
    "not that ",
    "no engine here",
    "not a proxy",
)


def rationale_names_formalized_subset(rationale: str) -> bool:
    """Whether the authored explanation explicitly names a boundary of its formula.

    This is a presentation annotation only. It deliberately recognises conservative, explicit
    limitation language rather than treating every ``not`` in legal prose as a scope claim. The
    rationale is the pack author's explanation surfaced by ``explain``; no verdict is inferred
    from this flag.
    """
    text = rationale.casefold()
    return any(marker in text for marker in _FORMALIZED_SUBSET_MARKERS)


def _probe_scope_line(budget: Mapping[str, Any]) -> str:
    """Compactly carry the search budget into a positive-result boundary sentence."""
    trials = budget.get("trials", "unknown")
    seed = budget.get("seed", "unknown")
    strategy = budget.get("strategy", "unknown")
    space = budget.get("input_space")
    if isinstance(space, Mapping):
        space_text = ", ".join(f"{name} ({count} values)" for name, count in sorted(space.items()))
    else:
        space_text = str(space) if space is not None else "no field varied"
    return (
        f"{trials} input(s) replayed, seed {seed}, input space: {space_text}; strategy: {strategy}"
    )


def positive_scope_boundary(result: "RequirementResult") -> str | None:
    """Return the run-specific boundary a satisfied result must carry on every surface."""
    if result.verdict is not Verdict.SATISFIED or result.strength is None:
        return None
    rung = result.strength.value
    if result.strength is Strength.OBSERVED:
        count = result.details.get("records_observed")
        supplied = (
            f"the supplied {count} decision records"
            if count is not None
            else "the supplied records"
        )
        evidence = f"{supplied} at the observed evidence rung"
        ending = (
            "this run did not establish that the trace is complete, representative, or unfiltered, "
            "and it did not determine legal adequacy or compliance outside those records"
        )
    elif result.strength in (Strength.RECOUNTED, Strength.PROBED):
        budget = result.details.get(PROBE_BUDGET_KEY)
        search = (
            _probe_scope_line(budget)
            if isinstance(budget, Mapping)
            else "a bounded search whose budget is not recorded"
        )
        evidence = f"the bounded search ({search}) at the {rung} evidence rung"
        ending = (
            "this run did not establish that the searched inputs are complete, representative, or "
            "unfiltered, and it did not determine legal adequacy or compliance outside that search"
        )
    elif result.strength is Strength.PROVED:
        assumptions = result.details.get("assumptions") or result.details.get("assumption_set")
        if isinstance(assumptions, (list, tuple, set)):
            assumption_text = ", ".join(str(item) for item in assumptions)
        elif assumptions:
            assumption_text = str(assumptions)
        elif result.details.get("solver") == "z3":
            assumption_text = "the system's declared logic and constraints"
        else:
            assumption_text = "the assumptions carried by this result"
        evidence = f"all inputs admitted by {assumption_text} at the proved evidence rung"
        ending = (
            "this run did not establish that those assumptions match production or the world, and "
            "it did not determine legal adequacy or compliance outside those assumptions"
        )
    else:
        # A future positive rung must not silently lose the boundary. Keep the wording tied to the
        # result's own named rung rather than presenting a generic compliance disclaimer.
        evidence = f"the evidence carried by this result at the {rung} evidence rung"
        ending = "this run did not determine legal adequacy or compliance outside that evidence"
    plugin = result.details.get(ENGINE_PLUGIN_KEY)
    if (
        isinstance(plugin, Mapping)
        and plugin.get("name")
        and result.witness_provenance == "trusted-ceiling"
    ):
        ending += (
            f"; this verdict rests on the declared ceiling of the engine plug-in "
            f"{plugin['name']!r}, which this package did not re-check"
        )
    return (
        "Scope of this positive result: this formal property was satisfied only on "
        f"{evidence}; {ending}."
    )


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

    `verbatim_text` is the statutory quotation the duty restates, carried through from the
    requirement unchanged and never reflowed, truncated or whitespace-normalised: the pack's
    copy is the authority and this is a passthrough, so a detail pane that names a clause can
    show its words. It is stamped beside `domains` and `basis` by `evaluate_requirement`, so a
    directly constructed result may carry the default until a run stamps it.

    `basis` is the fourth such fact and the second coordinate of the evidence claim: what kind of
    thing this duty's evidence is *about*, as against `strength`, which says how far the claim was
    pushed. It is derived from the requirement by `evidence_basis` and stamped once by
    `evaluate_requirement`, never authored in a pack and never declared by a system; the default
    here is the behavioural basis because that is what a direct construction is — evidence about
    the system's own executions — and the stamp is what makes a non-behavioural duty carry the
    truth. A result may not carry a strength its basis does not admit
    (`verdict.BASIS_RUNGS`): a counterfactual duty cannot be reported `observed` and a certificate
    duty cannot be reported `proved`, and those are refusals rather than conventions.
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
    basis: EvidenceBasis = EvidenceBasis.BEHAVIOURAL
    verbatim_text: str = ""
    formalized_subset_only: bool = False

    @property
    def outcome(self) -> str:
        """Return the operational outcome a machine consumer should act on.

        ``verdict`` remains the compatibility field for the formal result model, while this
        field carries the reader-facing outcome vocabulary from ``docs/semantics.md``.  The
        derivation is deliberately structural rather than another outcome registry: applicability
        and the missing-capability rung take precedence, then the two terminal verdicts leave the
        remaining strength-less result as *not evaluated*.
        """
        if self.verdict is Verdict.NOT_APPLICABLE:
            return "not_applicable"
        if self.strength is Strength.UNATTAINABLE:
            return "unattainable"
        if self.verdict is Verdict.SATISFIED:
            return "satisfied"
        if self.verdict is Verdict.VIOLATED:
            return "violated"
        return "not_evaluated"

    @property
    def scope_boundary(self) -> str | None:
        """The positive-result boundary derived from this result's own evidence."""
        return positive_scope_boundary(self)

    @property
    def witness_provenance(self) -> str:
        """Return the provenance a reader may attach to this result's evidence."""
        record = self.details.get(WITNESS_KEY)
        if isinstance(record, Mapping) and record.get("provenance") == "witness-checked":
            return "witness-checked"
        return "trusted-ceiling"

    @property
    def formalized_subset_note(self) -> str | None:
        """A short pointer to the authored rationale's explicit limitation, when present."""
        if self.verdict is Verdict.SATISFIED and self.formalized_subset_only:
            return f"Formalized subset only — see explain {self.requirement_id} rationale."
        return None

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
        object.__setattr__(self, "basis", EvidenceBasis.parse(self.basis))
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
        self._validate_witness()

        # And an artefact whose reason set the system recounted cannot report above `recounted`,
        # for the same reason again: the probe is the same probe, and what it was run against is
        # not the same evidence.
        self._validate_reason_set()

        # A vacuous-trigger result carries the trigger that never fired and the domain that was
        # searched. Refused here for the reason the probe budget is: those two are the whole of
        # the finding, and a result that cannot name them is not one a rendering can report.
        self._validate_vacuous_trigger()

        # An open-textured result names its authority, and a graded one names the algebra and the
        # source that fixed the scale. Refused here rather than at render time for the reason the
        # probe budget is: it is what makes it impossible to publish either in any format without
        # what a reader needs to read it.
        self._validate_open_texture()
        self._validate_truth_degree()
        self._validate_statistical_measurement()

        # The two coordinates have to agree. A rung this duty's basis does not admit is a claim
        # that some engine reached it, and for each of the four non-behavioural bases there is no
        # such engine and no such evidence — see `verdict.EvidenceBasis`.
        self._validate_basis()

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

    def _validate_reason_set(self) -> None:
        """Refuse a verdict claiming more than a recounted reason set can carry.

        The rule `docs/semantics.md` §3 stated in prose for as long as the ground program was the
        only family: a certificate over a reason set the system recounted claims strictly less than
        one over a model encoding, and must not report at the same strength. The key is absent on
        every result that is not measured against an inference artefact, so this refuses nothing
        else.
        """
        exact = self.details.get(EXACT_REASON_SET_KEY)
        if exact is None or exact:
            return
        if self.strength is not None and self.strength > Strength.RECOUNTED:
            raise ValueError(
                f"{self.requirement_id}: a result measured against a reason set the system "
                f"recounted cannot be reported {self.strength}; {Strength.RECOUNTED} is the "
                f"ceiling for it — {RECOUNTED_REASONS}"
            )

    def _validate_probe_budget(self) -> None:
        # `recounted` is a bounded search exactly as `probed` is — the same deletion probe over a
        # different reason set — so it owes a reader the same budget.
        if self.strength not in (Strength.PROBED, Strength.RECOUNTED):
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
        trials = budget["trials"]
        if isinstance(trials, bool) or not isinstance(trials, int) or trials <= 0:
            raise ValueError(
                f"{self.requirement_id}: a probed result must report a positive integer number "
                f"of trials, got {trials!r}"
            )
        strategy = budget["strategy"]
        if not isinstance(strategy, str) or not strategy.strip():
            raise ValueError(
                f"{self.requirement_id}: a probed result must name a non-empty search strategy, "
                f"got {strategy!r}"
            )
        seed = budget["seed"]
        if isinstance(seed, bool) or not isinstance(seed, (int, float, str)):
            raise ValueError(
                f"{self.requirement_id}: a probed result must carry a serialisable search seed, "
                f"got {seed!r}"
            )
        if isinstance(seed, float) and not jsonable_finite(seed):
            raise ValueError(
                f"{self.requirement_id}: a probed result must carry a finite search seed, "
                f"got {seed!r}"
            )
        if isinstance(seed, str) and not seed.strip():
            raise ValueError(
                f"{self.requirement_id}: a probed result must carry a non-empty search seed, "
                f"got {seed!r}"
            )
        input_space = budget["input_space"]
        if not (
            isinstance(input_space, Mapping)
            or (isinstance(input_space, str) and bool(input_space.strip()))
        ):
            raise ValueError(
                f"{self.requirement_id}: a probed result must describe its input space with a "
                f"mapping or non-empty string, got {input_space!r}"
            )

    def _validate_vacuous_trigger(self) -> None:
        """Refuse a vacuous-trigger result that does not name both halves of the finding."""
        vacuous = self.details.get(VACUOUS_TRIGGER_KEY)
        if vacuous is None:
            return
        missing = (
            list(VACUOUS_TRIGGER_FIELDS)
            if not isinstance(vacuous, Mapping)
            else [
                field for field in VACUOUS_TRIGGER_FIELDS if not str(vacuous.get(field, "")).strip()
            ]
        )
        if missing:
            raise ValueError(
                f"{self.requirement_id}: details[{VACUOUS_TRIGGER_KEY!r}] must name "
                f"{', '.join(VACUOUS_TRIGGER_FIELDS)}; missing {', '.join(missing)}. An "
                "implication holds wherever its trigger is false, so a reader who is not told "
                "which trigger stayed false and over what has been handed a verdict about the "
                "formula and told it is a verdict about the system"
            )
        if self.strength is not None:
            raise ValueError(
                f"{self.requirement_id}: a duty whose trigger fired nowhere cannot carry "
                f"evidence strength {self.strength}; nothing was learned about the system"
            )

    def _validate_open_texture(self) -> None:
        """Refuse an open-texture result that does not name every atom's authority."""
        atoms = self.details.get(OPEN_TEXTURE_KEY)
        if atoms is None:
            return
        if not isinstance(atoms, (list, tuple)) or not atoms:
            raise ValueError(
                f"{self.requirement_id}: details[{OPEN_TEXTURE_KEY!r}] must be a non-empty list of "
                f"the open-textured atoms this duty rests on; got {atoms!r}"
            )
        for atom in atoms:
            missing = (
                list(OPEN_TEXTURE_FIELDS)
                if not isinstance(atom, Mapping)
                else [f for f in OPEN_TEXTURE_FIELDS if not str(atom.get(f, "")).strip()]
            )
            if missing:
                raise ValueError(
                    f"{self.requirement_id}: every entry of details[{OPEN_TEXTURE_KEY!r}] must "
                    f"name {', '.join(OPEN_TEXTURE_FIELDS)}; {atom!r} is missing "
                    f"{', '.join(missing)}. A predicate this tool does not settle, reported "
                    "without saying who does, is the un-evaluated result this construct exists to "
                    "stop being the answer"
                )
        if self.strength is not None:
            raise ValueError(
                f"{self.requirement_id}: a duty resting on a predicate no engine settles cannot "
                f"carry evidence strength {self.strength}; nothing here applied the predicate"
            )

    def _validate_truth_degree(self) -> None:
        """Refuse a truth degree without its algebra, its source, or with a strength beside it.

        Three refusals, and each is one of this design's constraints made structural rather than
        conventional. **No bare degree**: `algebra` and every field of `source` must be there, so no
        rendering can print the numeral without what fixed it, because no result can exist that does
        not carry them. **No rescaled verdict**: a result carrying a degree carries no strength, so
        `0.7` can never be read off a rung as seventy percent of a proof. **A degree is a degree**:
        the value lies in [0, 1] and nothing here rescales it to a percentage.
        """
        reading = self.details.get(TRUTH_DEGREE_KEY)
        if reading is None:
            return
        if not isinstance(reading, Mapping):
            raise ValueError(
                f"{self.requirement_id}: details[{TRUTH_DEGREE_KEY!r}] must be a mapping naming "
                f"{', '.join(TRUTH_DEGREE_FIELDS)}; got {reading!r}"
            )
        missing = [f for f in TRUTH_DEGREE_FIELDS if reading.get(f) is None]
        if missing:
            raise ValueError(
                f"{self.requirement_id}: a truth degree must name "
                f"{', '.join(TRUTH_DEGREE_FIELDS)}; missing {', '.join(missing)}"
            )
        source = reading["source"]
        source_missing = (
            list(DEGREE_SOURCE_FIELDS)
            if not isinstance(source, Mapping)
            else [f for f in DEGREE_SOURCE_FIELDS if not str(source.get(f, "")).strip()]
        )
        if source_missing:
            raise ValueError(
                f"{self.requirement_id}: a truth degree travels with the source that fixed its "
                f"scale — {', '.join(DEGREE_SOURCE_FIELDS)}; missing "
                f"{', '.join(source_missing)}. A degree a reader cannot trace to whoever assessed "
                "it is a figure, and a degree the audited system asserted about itself is a "
                "self-declaration wearing a lattice's clothes"
            )
        degree = reading["degree"]
        if isinstance(degree, bool) or not isinstance(degree, (int, float)):
            raise ValueError(
                f"{self.requirement_id}: a truth degree must be a number in [0, 1], got {degree!r}"
            )
        if not 0.0 <= float(degree) <= 1.0:
            raise ValueError(
                f"{self.requirement_id}: a truth degree must lie in [0, 1], got {degree!r}"
            )
        if self.strength is not None:
            raise ValueError(
                f"{self.requirement_id}: a result carrying a truth degree cannot also carry "
                f"evidence strength {self.strength}. A degree is a distinct evidence basis and "
                "never a rescaled verdict — no rung of the lattice means 'graded', and a reader "
                "handed both would read the number as a fraction of the rung"
            )

    def _validate_statistical_measurement(self) -> None:
        """Enforce the first-wave statistical measurement contract.

        A payload is not a fourth spelling of an observed verdict: it is a population-shaped
        measurement beside ``not_evaluated``.  Keeping this refusal at the result boundary makes
        every renderer and JSON consumer inherit the same limits.
        """
        payload = self.details.get(STATISTICAL_MEASUREMENT_KEY)
        if self.verdict is Verdict.NOT_APPLICABLE:
            return
        if payload is None:
            if self.basis is EvidenceBasis.STATISTICAL and self.strength is None:
                raise ValueError(
                    f"{self.requirement_id}: a statistical result must carry "
                    f"details[{STATISTICAL_MEASUREMENT_KEY!r}]"
                )
            return
        if self.basis is not EvidenceBasis.STATISTICAL:
            raise ValueError(
                f"{self.requirement_id}: statistical measurement details require the statistical "
                "evidence basis"
            )
        if self.strength is not None:
            raise ValueError(
                f"{self.requirement_id}: a statistical measurement is not a strength rung; "
                "first-wave results carry strength=None"
            )
        if self.verdict is not Verdict.INCONCLUSIVE:
            raise ValueError(
                f"{self.requirement_id}: a first-wave statistical measurement cannot be reported "
                f"{self.verdict}; it is not evaluated"
            )
        validate_measurement_payload(payload)
        if payload.get("proxy_blindness_limit") != PROXY_BLINDNESS_LIMIT:
            raise ValueError(
                f"{self.requirement_id}: statistical measurements must carry the proxy-blindness "
                "limit"
            )

    def _validate_basis(self) -> None:
        """Refuse a result whose strength is a rung its evidence basis does not admit.

        Three sentences that were prose in three separate module docstrings become one refusal
        here. A `relational` duty is a property of a pair of executions, so no trace observes one;
        an `artifact` duty is measured against the inference behind a decision, so no exposure of
        the system proves one; an `assessment` duty rests on a predicate an authority applies, so
        no rung of the lattice ranks one at all. Each of the three is a fact about the *kind* of
        claim, which is why it is checked against the basis and not inside the engine that would
        otherwise have to remember it.
        """
        if self.strength is None or self.basis.admits(self.strength):
            return
        admitted = ", ".join(s.value for s in self.basis.rungs)
        raise ValueError(
            f"{self.requirement_id}: a result on the {self.basis} basis cannot be reported "
            f"{self.strength}; that basis admits {admitted} and no other rung. The strength "
            "lattice ranks how far a claim was pushed and the basis says what the claim was "
            "about, so a rung outside the basis is a claim that evidence of a kind nothing here "
            "produces was produced — see docs/semantics.md §10."
        )

    def _validate_witness(self) -> None:
        """Keep witness provenance a closed, machine-readable result contract."""
        witness = self.details.get(WITNESS_KEY)
        if witness is None:
            return
        if not isinstance(witness, Mapping):
            raise ValueError(
                f"{self.requirement_id}: details[{WITNESS_KEY!r}] must be a mapping; "
                f"got {witness!r}"
            )
        kind = witness.get("kind")
        if kind not in WITNESS_KINDS:
            raise ValueError(
                f"{self.requirement_id}: details[{WITNESS_KEY!r}]['kind'] must be one of "
                f"{WITNESS_KINDS}; got {kind!r}"
            )
        provenance = witness.get("provenance")
        if provenance == "refuted":
            missing = [field for field in ("failure", "unverified_payload") if field not in witness]
            if missing:
                raise ValueError(
                    f"{self.requirement_id}: a refuted witness must record {', '.join(missing)}"
                )
            if self.strength is not None or self.verdict is not Verdict.INCONCLUSIVE:
                raise ValueError(
                    f"{self.requirement_id}: a refuted witness cannot carry a verdict or "
                    "evidence strength"
                )
            return
        if provenance not in WITNESS_PROVENANCES:
            raise ValueError(
                f"{self.requirement_id}: details[{WITNESS_KEY!r}]['provenance'] must be one of "
                f"{WITNESS_PROVENANCES}; got {provenance!r}"
            )
        missing = [field for field in ("payload",) if field not in witness]
        if provenance == "witness-checked" and (
            "checker" not in witness or not str(witness.get("checker", "")).strip()
        ):
            missing.append("checker")
        if missing:
            raise ValueError(f"{self.requirement_id}: a witness must name {', '.join(missing)}")

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
            "verbatim_text": self.verbatim_text,
            "verdict": self.verdict.value,
            "strength": self.strength.value if self.strength else None,
            # Additive operational outcome: unlike the compatibility verdict/rung pair, this
            # names not_applicable, not_evaluated and unattainable distinctly for JSON readers.
            "outcome": self.outcome,
            "signals_required": list(self.signals_required),
            "signals_missing": list(self.signals_missing),
            "evidence_summary": self.evidence_summary,
            "details": dict(self.details),
            "findings": certificate_findings(self),
            "binding": self.binding,
            "scope": self.scope,
            "domains": list(self.domains),
            "basis": self.basis.value,
            # Additive machine fields: a consumer can keep reading every existing key while
            # gaining the same point-of-belief boundary shown by text and HTML.
            "scope_boundary": self.scope_boundary,
            "witness_provenance": self.witness_provenance,
            "formalized_subset_only": self.formalized_subset_only,
            "formalized_subset_note": self.formalized_subset_note,
        }


#: Where a result records that the duty's trigger fired nowhere in the evidence the engine had.
#: It carries the antecedent that never fired and the domain that was searched, because those two
#: are the whole of the finding: an implication is true of every system alike where its antecedent
#: is false, so a reader who is not told which trigger stayed false and over what has been handed a
#: verdict about the formula and told it is a verdict about the system.
VACUOUS_TRIGGER_KEY = "vacuous_trigger"

#: The two fields that key carries, named here so a rendering asks the result rather than parsing
#: a sentence that is free to be reworded — the same reason `PROBE_BUDGET_FIELDS` is named.
VACUOUS_TRIGGER_FIELDS = ("antecedent", "domain")


def not_evaluated_for_unreachable_trigger(
    req: Requirement,
    antecedent: str,
    domain: str,
    details: dict[str, Any] | None = None,
) -> RequirementResult:
    """The one result an engine returns when a duty's trigger fired nowhere it could look.

    Written once, against the result model, for the reason `rulelang.implication_antecedent` is
    written once against the property language: the vacuity is a fact about the formula, the same
    subtree in every engine, and four rungs answering it in four sentences would be four places for
    the rule to drift. `antecedent` is the trigger as the property states it, and `domain` is the
    engine's own account of what it searched and how much of it there was — "every input the
    declared constraints admit", "2 decision(s) of the trace", "59 replayed input(s)" — because the
    contract is that both travel with the verdict.

    The verdict is `inconclusive` at `strength=None`, which is this package's "not evaluated": the
    duty reaches the system, the engine ran, and what it learned about the system is nothing. It is
    deliberately not `satisfied`, which would be literally true of the formula and false of the
    claim a reader takes from it, and deliberately not `not_applicable`, which is a statement about
    a duty's reach that no engine is in a position to make. See `docs/semantics.md` §4.
    """
    merged: dict[str, Any] = dict(details or {})
    merged[VACUOUS_TRIGGER_KEY] = {"antecedent": antecedent, "domain": domain}
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Not evaluated: {req.spec!r} is an implication, and nothing in {domain} made its "
            f"antecedent {antecedent!r} true. An implication holds wherever its trigger is false, "
            "so this evidence would report every system alike satisfied and says nothing about "
            "this one. A duty whose trigger never fired is reported as no evidence rather than as "
            "a clean verdict."
        ),
        details=merged,
        binding=req.binding,
        scope=req.scope,
    )


def not_evaluated_for_open_texture(req: Requirement) -> RequirementResult:
    """The result for a duty resting on a predicate the law states without a sharp boundary.

    Written against the result model beside `not_evaluated_for_unreachable_trigger`, and reusing the
    same `inconclusive` at `strength=None` rather than inventing a mechanism beside it. Three
    quarters of this already happened by accident: a duty whose predicate nobody had modelled fell
    down whichever un-evaluated path its shape happened to take, and the report said the engine fell
    short rather than that the *law* had not been narrowed. What the construct adds is that the pack
    says which predicate is open-textured and **who settles it**, and the result carries both.

    It is deliberately not `unattainable`: the gap is not in the system, and telling an adopter to
    change a system because a statute uses the word *meaningful* is the wrong instruction. It is
    deliberately not `not_applicable`: the duty reaches this system, and only its application to
    these facts is unsettled. And it is deliberately never `satisfied` or `violated`, at any
    strength, because nothing here applied the predicate at all.
    """
    atoms = [
        {"signal": signal, "predicate": predicate, "authority": authority}
        for signal, predicate, authority in undetermined_atoms(parse_property(req.spec))
    ]
    named = "; ".join(
        f"whether {atom['signal']} is {atom['predicate']!r} — settled by {atom['authority']}"
        for atom in atoms
    )
    plural = "" if len(atoms) == 1 else "s"
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Not evaluated: this duty turns on {len(atoms)} predicate{plural} the law states "
            f"without a sharp boundary, and no engine here settles {'it' if not plural else 'them'}"
            f" — {named}. The system can emit the signal{plural} the predicate{plural} "
            f"{'is' if not plural else 'are'} about, so this is not a gap in the system; it is a "
            "question this tool refuses to answer in place of the named authority. Nothing here "
            "says the duty is met, and nothing here says it is breached."
        ),
        details={OPEN_TEXTURE_KEY: atoms},
        binding=req.binding,
        scope=req.scope,
    )


def _graded_result(
    req: Requirement, degree: float, atoms: dict[str, float], grading: Any
) -> RequirementResult:
    """The result carrying a truth degree, and no verdict derived from it.

    The verdict is `inconclusive` at `strength=None` — this package's *not evaluated* — and that is
    the design and not a stub. Turning a degree into `satisfied` needs a cut-off, no statute states
    one for *sufficiently detailed*, and a cut-off written into a shipped pack would be the pack
    author's number presented as the regulation's: the objection `docs/authoring-packs.md` already
    makes about an invented bound, arriving on a lattice instead of in a `spec`. So the machinery
    measures, the measurement travels with its algebra and its source, and what discharges the duty
    is a legal reading this tool does not make.
    """
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=(
            f"Not evaluated as satisfied or violated, and measured instead: this duty turns on a "
            f"predicate with no sharp boundary, and it holds to degree {degree} over the "
            f"{req.algebra} algebra, on degrees assessed by {grading.authority}. That number is a "
            "measurement and not a verdict: no threshold on it is stated by the clause, and this "
            "tool does not invent one. Read it with the scale and method that fixed it."
        ),
        details={
            TRUTH_DEGREE_KEY: {
                "degree": degree,
                "algebra": req.algebra,
                "atoms": dict(atoms),
                "source": grading.source(),
            }
        },
        binding=req.binding,
        scope=req.scope,
    )


def _not_evaluated(req: Requirement, summary: str, details: dict[str, Any] | None = None):
    """The plain not-evaluated result: the duty reaches the system and nothing was established."""
    return RequirementResult(
        requirement_id=req.id,
        source_clause=f"{req.source_document} {req.article_clause}",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=summary,
        details=dict(details or {}),
        binding=req.binding,
        scope=req.scope,
    )


def evaluate_graded_requirement(
    req: Requirement,
    records: list[dict[str, Any]],
    grading: Any | None,
) -> RequirementResult:
    """Measure a graded duty's truth degree, or say exactly why it was not measured.

    Four ways this returns without a degree, and none of them is a low one. No grading supplied; a
    grading that scores no degree for an atom the property reads; an empty trace, whose infimum
    would be the top of the lattice; and a formula putting a graded atom somewhere the reading has
    no meaning for it. Each is *not evaluated* naming what was missing — a predicate nobody assessed
    is not a predicate assessed as wholly false, and answering `0.0` for any of them would let this
    machinery report a breach it measured nothing for.
    """
    from reasonsmith.manyvalued import (
        algebra_named,
        atom_key,
        degree_over_trace,
    )
    from reasonsmith.rulelang import degree_atoms

    if grading is None:
        return _not_evaluated(
            req,
            "Not evaluated: this duty is graded, and no grading was supplied to this run. A truth "
            "degree comes from an assessment made outside this tool and is never read off the "
            "system or its log, so without one there is nothing to measure. Pass a "
            "reasonsmith.manyvalued.Grading to check_conformance — see docs/semantics.md §9.",
        )
    if not records:
        return _not_evaluated(
            req,
            "Not evaluated: this duty is graded over the decisions of the trace, and the trace is "
            "empty. The degree over a trace is the infimum of its per-decision degrees, and the "
            "infimum of nothing is the top of the lattice — having observed nothing is not "
            "evidence graded 1.0.",
        )

    node = parse_property(req.spec)
    try:
        algebra = algebra_named(req.algebra)
        degree = degree_over_trace(node, records, algebra, grading)
    except (UnsupportedConstructError, ValueError) as exc:
        return _not_evaluated(req, f"Not evaluated: {exc}.")

    atoms = {
        atom_key(signal, predicate): grading.degree(signal, predicate)
        for signal, predicate in degree_atoms(node)
    }
    return _graded_result(req, degree, atoms, grading)


#: The report categories, in the order they are rendered. Every result falls in exactly one of
#: them, which is what lets the counts reconcile against a total instead of merely summing to
#: something plausible.
_CATEGORY_LABELS = (
    ("proved", "proved"),
    ("probed", "probed"),
    ("recounted", "recounted"),
    ("observed", "observed"),
    ("violated", "violated"),
    ("inconclusive", "inconclusive"),
    ("not_evaluated", "not evaluated"),
    ("on_an_assessment", "on an assessment"),
    ("on_a_statistical_measurement", "on a statistical measurement"),
    ("unattainable", "unattainable"),
    ("not_applicable", "not applicable"),
)


def _category_counts(results: list[RequirementResult], prefix: str = "") -> dict[str, int]:
    """Count one set of results into the categories of `_CATEGORY_LABELS`.

    Binding and interpretive results are counted the same way and reported under different
    keys, so the two halves cannot drift into meaning different things.
    """

    def satisfied_at(strength: Strength) -> int:
        return sum(1 for r in results if r.verdict == Verdict.SATISFIED and r.strength == strength)

    counts = {
        "proved": satisfied_at(Strength.PROVED),
        "probed": satisfied_at(Strength.PROBED),
        "recounted": satisfied_at(Strength.RECOUNTED),
        "observed": satisfied_at(Strength.OBSERVED),
        "violated": sum(1 for r in results if r.verdict == Verdict.VIOLATED),
        "inconclusive": sum(
            1
            for r in results
            if r.verdict == Verdict.INCONCLUSIVE
            and r.evaluated
            and r.strength != Strength.UNATTAINABLE
        ),
        # `not_evaluated` is a gap in the audit — an empty trace, a solver timeout, an unmodelled
        # construct — and it tells a reader to fix the evidence or the specification. A duty on the
        # `assessment` basis reaching the same `strength=None` is not that: nothing fell short,
        # because no rung of this lattice was ever going to rank a predicate an authority applies.
        # Counting the two together made a measured truth degree and a solver timeout render as one
        # number in the headline, which is the cost `docs/semantics.md` §9 named and §10 removes.
        "not_evaluated": sum(
            1
            for r in results
            if not r.evaluated
            and r.verdict != Verdict.NOT_APPLICABLE
            and r.basis != EvidenceBasis.ASSESSMENT
        ),
        "on_an_assessment": sum(
            1
            for r in results
            if not r.evaluated
            and r.verdict != Verdict.NOT_APPLICABLE
            and r.basis == EvidenceBasis.ASSESSMENT
        ),
        "unattainable": sum(1 for r in results if r.strength == Strength.UNATTAINABLE),
        "not_applicable": sum(1 for r in results if r.verdict == Verdict.NOT_APPLICABLE),
    }
    statistical = sum(
        1
        for r in results
        if not r.evaluated
        and r.verdict != Verdict.NOT_APPLICABLE
        and r.basis == EvidenceBasis.STATISTICAL
        and STATISTICAL_MEASUREMENT_KEY in r.details
    )
    # Keep existing report envelopes byte-compatible when no statistical duty was run; the
    # category is materialized as soon as the new measurement basis appears.
    if statistical:
        counts["on_a_statistical_measurement"] = statistical
        counts["not_evaluated"] -= statistical
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

    `time_domain` is the clock the trace this run read *states* (`sut.read_time_domain`), and it
    is in `to_dict` because it qualifies every temporal verdict there. `"ordinal"` is a log that
    says nothing about time, which is every log until one carries `sut.TIME_DOMAIN_KEY`, and it is
    also what an unread trace reports — a run that needed no trace read no clock either. `"event"`
    says the log records when things happened, and it is the clock a bounded-response duty is
    counted on (`rulelang.BOUNDED_RESPONSE_CALL`, `docs/theory/03-semantics.md` Definition 3.9a).
    It does not say every verdict in the report was: a duty written without that operator is still
    counted on the record index whatever clock the trace states.
    """

    pack_id: str
    system_name: str
    results: tuple[RequirementResult, ...]
    system_scope: str | None = None
    system_domains: tuple[str, ...] = ()
    limits: str = LIMITS
    time_domain: str = ORDINAL_TIME
    decisions: tuple[DecisionAccount, ...] = ()
    # CLI strict mode is a presentation/exit-policy choice, not a new verdict. It is kept out
    # of the JSON envelope so default and strict consumers retain the same additive schema.
    strict_unresolved: bool = False

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
        `interpretive_total` each reconcile against the nine categories below and sum to
        `total`. `proved`/`probed`/`observed` count *satisfied* requirements at that strength,
        so a requirement is never counted as evidence for a property it does not have.
        `on_an_assessment` is the one category that is not a rung and not a verdict: it counts
        duties on the `assessment` evidence basis, which the strength lattice does not rank at all
        (`verdict.EvidenceBasis`, `docs/semantics.md` §10).
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
                if counts.get(prefix + key, 0)
            ]
            detail = f": {', '.join(categories)}" if categories else ""
            parts.append(f"{counts[total_key]} {noun}{detail}")
        positives = [r for r in self.results if r.verdict is Verdict.SATISFIED]
        if positives and all(r.strength is Strength.OBSERVED for r in positives):
            parts.append("all positives observed-only")
        if self.strict_unresolved:
            unresolved = Counter(
                r.outcome for r in self.results if r.outcome not in ("satisfied", "violated")
            )
            if unresolved:
                details = ", ".join(
                    f"{count} {outcome.replace('_', ' ')}" for outcome, count in unresolved.items()
                )
                parts.append(f"strict unresolved: {details}")
        return " · ".join(parts)

    @property
    def skipped_for_undeclared_domain(self) -> tuple[str, ...]:
        """The duties reported not applicable *solely* because this system declared no domain.

        A declared domain that does not meet a duty's is not counted here: that duty was answered,
        not skipped for want of an input.
        """
        return tuple(r.requirement_id for r in self.results if r.details.get(UNDECLARED_DOMAIN_KEY))

    @property
    def undeclared_domain_notice(self) -> str | None:
        """The one sentence every rendering owes a reader when duties went unchecked, or None.

        A run that skipped duties for a missing declaration exits exactly as a run that checked
        them does in the default mode — only a violation exits non-zero, and that is deliberate
        (`docs/semantics.md` §4). The CLI's opt-in `--strict-unresolved` policy can make the
        unresolved outcomes non-zero, but the report itself still carries what the default exit
        code cannot, in the place a reader
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

    def to_dict(self, audience: str | None = None) -> dict:
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
            "time_domain": self.time_domain,
            # The notice is a machine-record fact, not a display-only annotation.  Keep it in
            # every audience projection (null when no duty was skipped) so consumers never have
            # to infer missing input from the result prose or from the requested audience.
            "undeclared_domain_notice": self.undeclared_domain_notice,
            "audience": _audience_block(audience),
        }

    def to_json(self, indent: int | None = None, audience: str | None = None) -> str:
        """JSON representation following house pattern.

        `audience` travels onto the record as a declaration of the projection it was asked for,
        never as a filter: the complete machine record is emitted regardless, and the envelope's
        `audience` block names the projection (or `null` when none was asked for) beside every
        field it would have filtered. A consumer can therefore tell the record it was given from
        the projection the caller requested, and nothing is hidden from a machine consumer by a
        display flag.
        """
        return json.dumps(
            self.to_dict(audience=audience),
            indent=indent,
            default=str,
            allow_nan=False,
        )


def _audience_block(audience: str | None) -> dict[str, Any]:
    """The `audience` block of the machine record: the projection asked for, declared not applied.

    `--json` is the complete machine record and no projection filters it, but a record must be
    able to say *which* projection it was asked for — otherwise a consumer cannot tell `absent
    because the audience is not shown it` from `absent because the run never established it`. The
    block carries the name (`null` when no audience was given, matching the text renderer's
    `audience=None` full report) and every flag of the resolved `AudienceProjection`.

    The flags are derived, one field per `AudienceProjection` dataclass field, by iterating
    `dataclasses.fields` — never by hand-listing the names. A hand-written list is a second copy
    of the authored `AUDIENCES` table, and it would drift the first time a flag is added; this
    derivation makes the block a projection of the projection, with no second copy to keep in
    step. The unknown-audience refusal is the renderer's own `_projection` refusal, so the JSON
    path and the text path reject the same name with the same words.
    """
    from reasonsmith.render import AudienceProjection, _projection

    projection = _projection(audience)
    return {
        "name": audience,
        **{f.name: getattr(projection, f.name) for f in fields(AudienceProjection)},
    }


def evidence_basis(req: Requirement) -> EvidenceBasis:
    """What kind of thing this duty's evidence is about, derived from the duty alone.

    A function of the *requirement* and of nothing else — not of the system, not of which engine
    happened to answer, and never of a field a pack author writes. That is what makes the basis a
    fact a reader can rely on before a run: it says which rungs are reachable for this duty at all,
    so a ceiling reads as the duty's rather than as something the system failed to expose.

    The three tests below are the three branches of `_engine_ladder`, in `_engine_ladder`'s own
    order, and they are the whole of the derivation:

    - a duty gating on any of `engines.certificate.MEASURED_SIGNALS` is measured against the
      inference artefact behind a decision — the `artifact` basis, one rung;
    - a `counterfactual` duty is a property of a pair of executions — the `relational` basis, no
      trace rung;
    - an `undetermined` or `graded` duty rests on a predicate an authority applies rather than on
      anything measured from the system — the `assessment` basis, no rung at all.

    Everything else is a property of the system's own executions, one at a time, and reaches every
    rung the system's exposed surface allows. `test_the_basis_admits_exactly_the_rungs_the_ladder_
    can_reach` is what keeps this function and that one from drifting apart.
    """
    from reasonsmith.engines.certificate import MEASURED_SIGNALS

    if getattr(req, "formalism", None) == "statistical":
        return EvidenceBasis.STATISTICAL
    if any(signal in req.requires for signal in MEASURED_SIGNALS):
        return EvidenceBasis.ARTIFACT
    if req.formalism == "counterfactual":
        return EvidenceBasis.RELATIONAL
    if req.formalism in ("undetermined", "graded"):
        return EvidenceBasis.ASSESSMENT
    return EvidenceBasis.BEHAVIOURAL


def analyze_unattainable(req: Requirement, sut: SystemUnderTest) -> tuple[bool, tuple[str, ...]]:
    """Perform the unattainable analysis for a requirement against a SUT.

    COMPUTED WITHOUT EXECUTING THE SYSTEM (`sut.decisions()` is never called here): the answer
    is the set difference between the signals the requirement needs and the capability set the
    SUT adapter supplies. Most adapters require an explicit system declaration. A trace-derived
    adapter is weaker: its result is limited to that supplied trace rather than stated as a
    property of the system as built.

    One name is exempt from the subtraction, and only one: the *protected* argument of a
    `counterfactually_invariant(outcome, protected)` duty. `capabilities()` is what a system can
    emit into a decision record, and that is the opposite direction from what this duty needs —
    what the decision procedure *accepts*. Both of its engines read the protected variable's values
    from the system's declared `constraints` and never from a record, so gating on the capability
    would report a creditor whose procedure accepts a prohibited basis and whose log deliberately
    carries it for nobody `unattainable`, and tell that adopter to start logging a prohibited basis
    per decision. The name stays in the requirement's `requires` because it is the one the
    counterfactual engine names as missing when the system's declared logic has no notion of it —
    an unattainable result may not name a signal the requirement never required.

    Returns:
        (is_unattainable, missing_signals) — missing_signals is sorted and never empty when
        is_unattainable is True.
    """
    declared = sut.capabilities()
    _validate_capability_collection(declared, f"{type(sut).__name__}.capabilities() must return")
    missing = tuple(sorted(set(req.requires) - set(declared) - _input_only_signals(req)))
    return bool(missing), missing


def _input_only_signals(req: Requirement) -> set[str]:
    """The names a duty reads as declared inputs rather than as fields of a decision record."""
    if req.formalism != "counterfactual":
        return set()
    try:
        atom = counterfactual_atom(parse_property(req.spec))
    except UnsupportedConstructError:
        return set()
    return {atom[1]} if atom is not None else set()


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
    req: Requirement,
    sys_scope_norm: str,
    sys_domains: tuple[str, ...],
    system_scope: Any,
    frontier_trigger: str = "",
    frontier_ai_status: str | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """Why this duty does not reach this system, and what that is, or None when it does.

    The second element is the details a result carries away from here. A duty skipped because
    the system declared *no* decision domain is flagged with `UNDECLARED_DOMAIN_KEY`: that is a
    missing input rather than an answer, and every rendering says so. A duty skipped because the
    system declared a domain that is simply not this duty's carries nothing — that one is a real
    answer, and warning about it would train a reader to ignore the warning that matters.

    Three independent applicability axes can matter, on questions that are not the same. `scope`
    is a regulatory class from one statute's own fixed vocabulary; `domains` is the kind of decision
    a duty is about, from a vocabulary this repository wrote (`spec.DECISION_DOMAINS`); and the
    optional pack-level `frontier_trigger` requires a self-asserted frontier status. A duty is
    evaluated only when it passes every gate its pack declares.

    Each gate is a conjunction against a declaration this tool never infers, and each fails in
    the same two ways — the system declared nothing, or declared something else — because those
    two are one instruction to the reader: *say what this system is, and run it again*. The
    message names which of the two it was, so nobody reads "not applicable" as "cleared".

    An unset gate on the requirement is a deliberate wildcard, not an accident: `scope = ""` is a
    duty no regulatory class limits, and `domains = []` is a duty about no particular kind of
    decision — the GDPR's Article 22 is both. Neither can be reached by omission, because the
    loader refuses a requirement that does not carry both fields.
    """
    if frontier_trigger == FRONTIER_TRIGGER and frontier_ai_status != "frontier":
        if frontier_ai_status is None:
            declaration = "undeclared"
        else:
            declaration = repr(frontier_ai_status)
        return (
            "Not applicable: this pack applies only when the system self-declares "
            "frontier_ai_status='frontier'; the system's frontier AI status is "
            f"{declaration}, so no requirement was evaluated. reasonsmith does not independently "
            "verify this self-declaration; a wrong frontier declaration is the audited system's "
            "overclaim.",
            {FRONTIER_GATE_KEY: frontier_ai_status or "undeclared"},
        )
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


def _effective_frontier_trigger(req: Requirement, frontier_trigger: str | None) -> str:
    """Keep a pack-level frontier gate attached when a requirement is evaluated alone."""
    requirement_trigger = getattr(req, "frontier_trigger", "")
    supplied = frontier_trigger or ""
    if supplied not in ("", FRONTIER_TRIGGER):
        raise ValueError(
            f"unsupported frontier trigger {supplied!r}; the only supported gate is "
            f"{FRONTIER_TRIGGER!r}"
        )
    if requirement_trigger and supplied not in ("", requirement_trigger):
        raise ValueError(
            f"Requirement {req.id!r} carries frontier gate {requirement_trigger!r}, but the "
            f"evaluation supplied conflicting gate {supplied!r}"
        )
    return requirement_trigger or supplied


def evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None = None,
    system_scope: str | None = None,
    system_domains: Iterable[str] | None = None,
    grading: Any | None = None,
    frontier_trigger: str | None = None,
    frontier_ai_status: str | None = None,
    statistical_plan: Mapping[str, Any] | None = None,
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
    frontier_trigger = _effective_frontier_trigger(req, frontier_trigger)
    result = _evaluate_requirement(
        req,
        sut,
        records,
        system_scope,
        system_domains,
        grading,
        frontier_trigger,
        frontier_ai_status,
        statistical_plan,
        _resources=_resources,
    )
    # The duty's own domain limit is stamped once, here, rather than threaded through four
    # engines: an engine has nothing to say about which systems a duty reaches, and a rung that
    # forgot to carry it would render a domain-limited duty as one that reaches everything.
    #
    # The evidence basis is stamped in the same place and for the same reason. It is a fact about
    # the duty rather than about the run — which is why it is derived here from `req` alone and not
    # asked of whichever engine answered — and `replace` re-runs `__post_init__`, so a result
    # carrying a rung its basis does not admit is refused at the stamp rather than rendered.
    return replace(
        result,
        domains=req.domains,
        basis=evidence_basis(req),
        # The statutory quotation, stamped beside the other two facts about the duty rather
        # than threaded through four engines: it is the pack's copy, unchanged, and an engine
        # has nothing to say about the words of the clause it was checked against.
        verbatim_text=req.verbatim_text,
        formalized_subset_only=rationale_names_formalized_subset(req.rationale),
    )


def _evaluate_requirement(
    req: Requirement,
    sut: SystemUnderTest,
    records: list[dict[str, Any]] | None,
    system_scope: str | None,
    system_domains: Iterable[str] | None,
    grading: Any | None,
    frontier_trigger: str,
    frontier_ai_status: str | None,
    statistical_plan: Mapping[str, Any] | None,
    *,
    _resources: _EvaluationResources | None,
) -> RequirementResult:
    resources = _resources or _EvaluationResources(sut)
    frontier_trigger = _effective_frontier_trigger(req, frontier_trigger)

    system_scope = _declared_scope(sut, system_scope)
    sys_scope_norm = normalize_scope(system_scope, "declared system scope")
    sys_domains = _declared_domains(sut, system_domains)
    frontier_ai_status = normalize_frontier_ai_status(
        frontier_ai_status
        if frontier_ai_status is not None
        else getattr(sut, "frontier_ai_status", None),
        "declared frontier AI status",
    )

    inapplicable = _inapplicability(
        req,
        sys_scope_norm,
        sys_domains,
        system_scope,
        frontier_trigger,
        frontier_ai_status,
    )
    if inapplicable:
        return _not_applicable(req, *inapplicable)

    is_unattainable, missing = analyze_unattainable(req, sut)
    if is_unattainable:
        return _unattainable_result(req, missing, sut)

    clause = f"{req.source_document} {req.article_clause}"

    if req.formalism == "statistical":
        return _evaluate_statistical_requirement(
            req, records if records is not None else resources.trace(), statistical_plan
        )

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

    # The two open-texture fragments return here, before the ladder, and they return *after* the
    # capability gate above rather than before it. That order is the whole of the guarantee that a
    # graded semantics does not make every duty answerable: a system that can show nothing is
    # `unattainable`, exactly as it was, and never a low degree. No engine reaches either fragment,
    # so `_engine_ladder` would have nothing to append — and a rung that reported one would be a
    # rung claiming to have settled a predicate this tool refuses to settle.
    if req.formalism == "undetermined":
        return not_evaluated_for_open_texture(req)
    if req.formalism == "graded":
        return evaluate_graded_requirement(
            req, records if records is not None else resources.trace(), grading
        )

    candidates = _engine_ladder(req, sut, records, resources, capability_missing=missing)
    if not candidates:
        raise NotImplementedError(
            f"{req.formalism!r} is listed in SUPPORTED_FORMALISMS but no engine here evaluates "
            "it. Every listed formalism is either answered by an engine or refused without one "
            "(`undetermined` and `graded`); this one is neither, so the ladder has a gap and this "
            "is a build error rather than a widening decision."
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


def _statistical_refusal_payload(plan: Any, reason: str) -> dict[str, Any]:
    """Build a closed refusal payload without trusting any malformed plan field."""
    raw_groups: Any = None
    if isinstance(plan, Mapping):
        try:
            raw_groups = plan.get("groups")
        except Exception:
            raw_groups = None
    groups: list[str] = ["undeclared"]
    if isinstance(raw_groups, (list, tuple)) and raw_groups:
        candidate = list(raw_groups)
        if (
            all(isinstance(group, str) and group.strip() for group in candidate)
            and len(set(candidate)) == len(candidate)
        ):
            groups = candidate
    return {
        "groups": groups,
        "sampling_assumption": {
            "status": "absent",
            "description": "no valid sampling plan could be read",
        },
        "n": 0,
        "counts": {},
        "metric": {"formula": "min_g(p_hat_g) / max_h(p_hat_h)", "status": "refused"},
        "confidence": {
            "level": None,
            "interval_method": None,
            "tail_allocation": None,
            "intervals": None,
            "ratio_interval": None,
        },
        "threshold": None,
        "authority_provenance": None,
        "decision_rule": None,
        "status": "refused",
        "refusal": reason,
        "proxy_blindness_limit": PROXY_BLINDNESS_LIMIT,
    }


def _evaluate_statistical_requirement(
    req: Requirement, records: list[dict[str, Any]], plan: Mapping[str, Any] | None
) -> RequirementResult:
    """Run the population measurement once, outside the ordinary trace engine ladder."""
    clause = f"{req.source_document} {req.article_clause}"
    try:
        atom = statistical_atom(parse_property(req.spec))
        if atom is None:
            raise ValueError("statistical requirement must be one selection_rate_ratio() atom")
        outcome_field, group_field = atom
        if not isinstance(plan, Mapping):
            raise TypeError("statistical plan must be a mapping")
        config = dict(plan)
        groups = config.pop("groups", None)
        if not groups:
            raise ValueError("statistical plan must declare the fixed duty group set")
        payload = measure_selection_rates(
            records,
            groups=tuple(groups),
            group_field=group_field,
            outcome_field=outcome_field,
            sampling_assumption=config.pop("sampling_assumption", None),
            confidence_level=float(config.pop("confidence_level", 0.95)),
            authority_provenance=config.pop("authority_provenance", None),
            threshold=config.pop("threshold", None),
            unit_field=config.pop("unit_field", None),
        )
        summary = (
            "Statistical measurement only: the sample estimate and uncertainty interval are "
            "reported under the declared plan; this first wave makes no conformance verdict."
        )
    except Exception as exc:  # malformed plans are a refused measurement, never an audit abort
        payload = _statistical_refusal_payload(plan, f"{type(exc).__name__}: {exc}")
        validate_measurement_payload(payload)
        summary = f"Statistical measurement not evaluated: {exc}."
    return RequirementResult(
        requirement_id=req.id,
        source_clause=clause,
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=tuple(req.requires),
        evidence_summary=summary,
        details={STATISTICAL_MEASUREMENT_KEY: payload},
        binding=req.binding,
        scope=req.scope,
        basis=EvidenceBasis.STATISTICAL,
    )


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
    capability_missing: tuple[str, ...] | None = None,
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
    must not be able to answer a counterfactual duty off a log either. This is also the one
    fragment whose *lower* rung is run after the higher one has already answered: the two do not
    range over the same object, so their disagreement is evidence in its own right and
    `engines.counterfactual.cross_rung_signal` records what it eliminates. It changes no verdict
    and no strength, and it runs only when the proof rung reached one, so nothing here pays for it
    twice.

    Three duties are deliberately given a ladder of **one** rung: a duty gating on any of
    `engines.certificate.MEASURED_SIGNALS` asks something about the inference behind a decision —
    whether the reasons it stated are all the reasons it had, or whether its answer is the
    semantics it claims — and that is measured against the inference artefact or not at all. Every
    other rung here would answer a weaker question off the system's own log — that the reason field
    is non-blank, or that the number the system wrote in it is small — and reporting either in
    place of the measurement is the substitution the certificate engine exists to remove. A
    system exposing no artefact is therefore reported *unattainable* by that engine rather than
    falling through to a presence check. That single rung stays single: the plug-in
    rungs below are appended after it has already returned, so no installed package can answer that
    duty off the system's log either.

    Engines an installed package supplies (entry-point group `reasonsmith.engines`) join the ladder
    at the ceiling each declares, which is exactly what makes "a new engine is reached the moment it
    exists" mean *installed* rather than *in this tree*. What a plug-in may claim, and what happens
    when one misbehaves, is `reasonsmith.plugins` and `docs/authoring-engines.md`.
    """
    from reasonsmith.engines.certificate import MEASURED_SIGNALS

    if any(signal in req.requires for signal in MEASURED_SIGNALS):
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
            cross_rung_signal,
        )

        def replay() -> RequirementResult:
            return PairedReplayEngine.evaluate(
                req,
                sut,
                records,
                trace_provider=resources.trace if records is None else None,
            )

        def proof() -> RequirementResult:
            proved = _run_proof_rung(req, sut, records, resources, engine=CounterfactualProofEngine)
            if proved.verdict not in (Verdict.SATISFIED, Verdict.VIOLATED):
                return proved
            return cross_rung_signal(req, proved, replay(), resources.logic())

        counterfactual: list[tuple[Strength, Any]] = []
        if callable(getattr(sut, "logic", None)):
            counterfactual.append((Strength.PROVED, proof))
        counterfactual.append((Strength.PROBED, replay))
        # Counterfactual evidence is relational and must be produced by one of the audited
        # pair-producing paths above. Generic installed engines consume a trace and therefore
        # cannot answer a property about executions the trace does not contain. Keep this early
        # branch closed to the generic plug-in group; a future neural verifier gets a dedicated,
        # typed insertion here rather than answering through ``reasonsmith.engines``.
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
            req,
            sut,
            lambda: records if records is not None else resources.trace(),
            capability_missing=capability_missing,
        )
    )

    return ladder


def check_conformance(
    sut: SystemUnderTest,
    pack: Pack,
    system_name: str = "SUT",
    system_scope: str | None = None,
    system_domains: Iterable[str] | None = None,
    grading: Any | None = None,
    frontier_ai_status: str | None = None,
    statistical_plan: Mapping[str, Any] | None = None,
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
            grading=grading,
            frontier_trigger=pack.frontier_trigger,
            frontier_ai_status=frontier_ai_status,
            statistical_plan=statistical_plan,
            _resources=resources,
        )
        for req in pack.requirements
    ]
    trace = resources.records_read()
    try:
        stated_time_domain = read_time_domain(trace).kind
    except (TypeError, ValueError):
        # A malformed event clock is an evidence refusal for the metric duty, not a reason to hide
        # the rest of an otherwise useful report. Preserve the fact that the trace attempted to
        # state event time without claiming that its instants were valid.
        stated_time_domain = (
            EVENT_TIME if any(TIME_DOMAIN_KEY in record for record in trace) else ORDINAL_TIME
        )
    return ConformanceReport(
        pack_id=pack.id,
        system_name=system_name,
        system_scope=system_scope,
        system_domains=sys_domains,
        results=tuple(results),
        time_domain=stated_time_domain,
        decisions=decision_accounts(trace),
    )
