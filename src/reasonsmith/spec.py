"""Specification structures and pack loader for reasonsmith v0.2.

What this module is for:
  Defines `Requirement` and `Pack` data structures and the loader for TOML regulation packs
  (`packs/*.toml`).

What a reader must not break:
  - `REQUIREMENT_FIELDS` is exact. A pack that omits or adds fields to a `[[requirement]]` block
    must be rejected at load time.
    Why this matters: Omitting a field prevents statutory source traceability; adding unread fields
    makes data appear to carry meaning that nothing in the codebase acts on.
  - Verbatim text and statutory citations loaded from packs must strictly match source documents
    (`docs/legal-sources.md`).
    Why this matters: Ensures requirement packs stay legally faithful to official statutory texts.
  - `spec` is a formula in the one property language of `rulelang.py`, `rationale` is the English,
    and `formalism` names which fragment of that language the formula belongs to. The loader parses
    `spec`, classifies it, and refuses a declared fragment that is not the one it found.
    Why this matters: `formalism` used to be a label nothing checked, so prose could sit in `spec`
    under `formalism = "record"` and an STL formula could be labelled `record` and silently
    downgraded. The check is what makes the field mean something.
  - `domains` names the kinds of decision a duty is about, from `DECISION_DOMAINS`, and an empty
    list means the duty is not domain-limited. It is a required field with no default, exactly as
    `binding` and `scope` are.
    Why this matters: without it, an adverse-action notice duty reached a graph-reachability
    benchmark that issues no credit and notifies nobody, and reported it `satisfied`. Defaulting a
    missing `domains` to empty would put that false positive straight back, since empty is the
    wildcard. The vocabulary is the pack author's and not any regulation's, which is a claim the
    pack must carry rather than hide — see `DECISION_DOMAINS` and `docs/authoring-packs.md`.
  - `deontic_type` and `defeasibility` classify the *clause*, are required fields with no default,
    and no engine reads either. They exist so the recurring shape of the fourth column of
    `docs/refinement.md` can be counted rather than asserted.
    Why this matters: "the general rule is formalised, the exception is not" was said of the
    shipped packs often enough to look like one missing construct. It is measurable, and the
    measurement is in `docs/refinement.md`, *The defeasibility census*. Carrying the fields is the
    whole of what this repository does with them: nothing here reasons defeasibly, and a reader
    who takes `defeasible-modelled` for a defeasible engine has read a claim the pack does not
    make.
  - Every signal name a `spec` reads *unconditionally* must appear in `requires`. A name read only
    inside a disjunction whose every branch is settled by `present()` atoms, and which does not
    occur in all of those branches, is exempt, and deliberately so.
    Why this matters: `requires` is the capability gate that decides whether a duty is attainable
    at all, and it is a conjunction — a system missing any one of its names is reported
    unattainable without being run. An unconditional name that is not gated is a signal no
    unattainability analysis ever asks for, usually a typo. But a disjunct is an *alternative*:
    where a clause is an either/or, gating both branches would report a system that lawfully took
    one of them unattainable, which is a different way of getting the answer wrong. The price of
    the exemption is that a typo inside a disjunct is not caught here — it becomes a branch nothing
    can ever satisfy — so a pack author writing a disjunction owes the signal name a second look.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from reasonsmith.manyvalued import ALGEBRAS, algebra_named
from reasonsmith.rulelang import (
    UnsupportedConstructError,
    classify_fragment,
    parse_property,
    unconditional_signal_names,
)

VALID_FORMALISMS = (
    "record",
    "temporal",
    "logical",
    "counterfactual",
    "undetermined",
    "graded",
)
PACKS_DIR = Path(__file__).parent / "packs"

#: Exactly the fields a [[requirement]] block carries. A pack that omits one is
#: rejected at load time rather than producing a requirement that cannot be
#: traced back to its source, and one that adds a field the loader does not read
#: is rejected too rather than looking like it carries data nothing acts on.
#: `binding`, `scope` and `domains` are on this list on purpose, including for externally
#: authored packs: an unclassified requirement has no safe default (see Requirement), so the
#: loader refuses the pack by name rather than guessing which kind of duty it is.
REQUIREMENT_FIELDS = (
    "id",
    "source_document",
    "article_clause",
    "verbatim_text",
    "stakeholder",
    "formalism",
    "spec",
    "rationale",
    "requires",
    "binding",
    "scope",
    "domains",
    "deontic_type",
    "defeasibility",
)


#: What kind of normative sentence the clause is. This is a classification of the **clause**, not
#: of the property that stands for it, and the two can differ: GDPR Article 22(1) is a prohibition
#: whose shipped `record` property is a logging obligation, and that divergence is a finding
#: `docs/refinement.md` records rather than a mismatch this field papers over.
#:
#: `reparation` is the contrary-to-duty member: a duty whose antecedent is a violation or a harm,
#: which classical deontic logic cannot state without paradox and which the shipped result model —
#: a Boolean property of decision records — cannot express at all. It is listed here because
#: EU AI Act Article 55(1)(c) has that shape; what it does *not* buy is any machinery, and no
#: engine reads this field.
#:
#: There is deliberately no default. A duty nobody has classified is a duty whose refinement was
#: not examined, which is the same argument `binding`, `scope` and `domains` make.
DEONTIC_TYPES = (
    "obligation",
    "permission",
    "prohibition",
    "reparation",
)


#: Whether the clause states something that switches the duty off, and whether the property
#: carries it. Two different things are told apart here on purpose, because conflating them was
#: the thing that made the gap look bigger than it is:
#:
#: - a **defeater** is an exception that overrides an otherwise-applicable duty — 12 CFR
#:   1002.9(a)(1)(ii)'s *unless notice is provided in accordance with paragraph (c)*, GDPR
#:   Article 22(2)'s *paragraph 1 shall not apply if*. Modelling one needs a priority between
#:   rules, which this property language has no notion of.
#: - a **trigger** is the clause's condition of application — adverse action having been taken,
#:   the model having systemic risk. It is an antecedent, and `rulelang` already expresses one:
#:   `ecoa_reg_b_1002_9_b_2_specific_reasons` carries its own. What is missing there is a signal,
#:   not a construct.
#:
#: A duty carrying both is classified by its defeater, since that is the harder gap;
#: `docs/refinement.md`, *The defeasibility census*, names the rows where that hides a trigger.
#: A defeater counts only where the clause states it in the requirement's own `verbatim_text` or
#: in a source `docs/legal-sources.md` retrieved — the same discipline every other claim about
#: the law in this repository is held to. The census understates by whatever a wider retrieval
#: would find, and that limit is named in the document rather than hidden here.
DEFEASIBILITY_CLASSES = (
    "strict",
    "defeasible-modelled",
    "defeasible-unmodelled",
    "trigger-unmodelled",
)


#: The regulatory classes this tool knows how to name, as a fixed vocabulary rather than
#: whatever strings a pack or a caller happens to write. Both sides of the comparison are
#: checked against this list, so a misspelling is refused where it is written instead of
#: silently never matching: a pack typo would leave a duty unreachable for every system, and a
#: caller typo would turn every class-limited duty not applicable in a run that still exits
#: clean. An empty class is not a member — it means "not class-limited" on a requirement and
#: "undeclared" on a system, which are absences rather than classes.
REGULATORY_CLASSES = (
    "prohibited",
    "high-risk",
    "limited-risk",
    "minimal-risk",
    "general-purpose",
)


def normalize_scope(value: Any, what: str = "regulatory class") -> str:
    """Normalize a regulatory class for comparison and refuse one outside the vocabulary.

    Normalization is surrounding whitespace and letter case, and nothing else. `high-risk` and
    `high_risk` are different strings and stay different: guessing that two spellings mean the
    same class would let a run answer a duty it was never told applies. A value that is not a
    member of `REGULATORY_CLASSES` is refused here, naming what was given and what would have
    been accepted, rather than being carried forward as a class nothing can ever match.

    Returns "" for None and for the empty string, which mean "not class-limited" on a
    requirement and "undeclared" on a system. A value that is only whitespace is not the empty
    string and is refused with everything else outside the vocabulary: someone who wrote it
    meant to name a class, and treating it as the absence of one would leave a duty that no
    system can ever match — the same unreachable duty a misspelling would leave.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(
            f"a {what} must be a string or None, got {type(value).__name__}: {value!r}"
        )
    if not value:
        return ""
    normalized = value.strip().lower()
    if normalized not in REGULATORY_CLASSES:
        raise ValueError(
            f"{value!r} is not a known {what}. Accepted: "
            f"{', '.join(repr(c) for c in REGULATORY_CLASSES)}, or leave it unset for a "
            "requirement that is not class-limited or a system whose class is undeclared. "
            "Classes are compared after trimming surrounding whitespace and lowercasing, and "
            "are not otherwise guessed at."
        )
    return normalized


#: The decision domains this tool knows how to name — the *kind of decision* a duty is about,
#: which is a different axis from the regulatory class above and is gated separately.
#:
#: This vocabulary is **the pack author's, and not any regulation's**, and the difference from
#: `REGULATORY_CLASSES` is the whole reason it is written down here rather than derived. The five
#: regulatory classes are one statute's own vocabulary: the EU AI Act defines them, so a pack can
#: quote them. No statute defines a list of decision domains. Consumer credit, employment,
#: housing, insurance, healthcare and criminal justice are carved differently by every regime that
#: carves them at all — the GDPR is not domain-limited in the first place, and the AI Act works
#: from Annex III use-cases rather than subject matters. Any closed list is therefore wrong
#: somewhere, and this one is deliberately coarse: it exists to answer *has this system said what
#: kind of decision it makes*, not to classify a system correctly for a regulator.
#:
#: What that buys is one guarantee and no more: a system that has not declared its domain is never
#: reported `satisfied` on a domain-limited duty. `docs/authoring-packs.md` (*the decision-domain
#: vocabulary is the pack author's*) states the discipline a pack owes when it uses one of these
#: names, which is the same discipline it owes an invented threshold.
#:
#: An empty selection is not a member. On a requirement it means "not domain-limited"; on a system
#: it means "undeclared". Those are absences, not domains, and they are not the same absence.
DECISION_DOMAINS = (
    "consumer-credit",
    "criminal-justice",
    "education",
    "employment",
    "healthcare",
    "housing",
    "insurance",
    "public-services",
)

#: Semantics labels an inference artefact may claim.  This is deliberately closed: consumers
#: may compare these declarations without treating an author's prose as a new, interpretable
#: semantics.
CLAIMED_SEMANTICS = (
    "distribution semantics",
    "weighted sum",
    "free-text rationale",
)


def normalize_claimed_semantics(value: Any) -> str:
    """Normalize and refuse an inference artefact's claimed semantics declaration."""
    if not isinstance(value, str):
        raise TypeError(
            f"claimed semantics must be a string, got {type(value).__name__}: {value!r}"
        )
    normalized = value.strip().lower()
    if normalized not in CLAIMED_SEMANTICS:
        raise ValueError(
            f"{value!r} is not a known claimed semantics value. Accepted: "
            f"{', '.join(repr(s) for s in CLAIMED_SEMANTICS)}"
        )
    return normalized



def normalize_domain(value: Any, what: str = "decision domain") -> str:
    """Normalize one decision domain for comparison and refuse one outside the vocabulary.

    The same normalization `normalize_scope` performs, and for the same reasons: surrounding
    whitespace and letter case only, so `consumer-credit` and `consumer_credit` stay different
    strings. A value outside `DECISION_DOMAINS` is refused where it is written rather than carried
    forward as a domain nothing can ever match — in a pack that would leave a duty unreachable for
    every system, and on a caller's declaration it would turn every domain-limited duty not
    applicable in a run that still exits clean.

    Unlike `normalize_scope`, the empty string is refused here too. A requirement says "not
    domain-limited" with an empty *list*, and a system says "undeclared" by declaring no domains
    at all; an empty string inside a list is a name someone failed to finish typing.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"a {what} must be a string, got {type(value).__name__}: {value!r}"
        )
    normalized = value.strip().lower()
    if normalized not in DECISION_DOMAINS:
        raise ValueError(
            f"{value!r} is not a known {what}. Accepted: "
            f"{', '.join(repr(d) for d in DECISION_DOMAINS)}. Leave the list empty for a "
            "requirement that is not domain-limited or a system whose domains are undeclared. "
            "Domains are compared after trimming surrounding whitespace and lowercasing, and are "
            "not otherwise guessed at. This vocabulary is the pack author's, not any regulation's "
            "— see docs/authoring-packs.md."
        )
    return normalized


def normalize_domains(value: Any, what: str = "decision domain") -> tuple[str, ...]:
    """Normalize a collection of decision domains, sorted and deduplicated.

    Refuses a bare string for the reason every other signal-name site in this package does: a
    string is iterable, so `"housing"` would become seven single-character domains. Refuses a
    mapping for the reason `sut._validate_capability_collection` does — its False-valued entries
    would read as declared.

    Returns `()` for None and for an empty collection, which is "not domain-limited" on a
    requirement and "undeclared" on a system.
    """
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        raise TypeError(
            f"a {what} list must be a collection of domain names, not a single string; "
            f"pass [{value!r}] to name one domain"
        )
    if isinstance(value, Mapping):
        raise TypeError(
            f"a {what} list must be the declared domain names, not a map; got "
            f"{type(value).__name__}, whose False-valued entries would be read as declared"
        )
    if not isinstance(value, Iterable):
        raise TypeError(
            f"a {what} list must be a collection of domain names, got {type(value).__name__}"
        )
    names = [normalize_domain(item, what) for item in value]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValueError(
            f"duplicate {what}(s): {', '.join(duplicates)}. A domain list is a set of the kinds "
            "of decision a duty reaches, so naming one twice says nothing a single mention does "
            "not."
        )
    return tuple(sorted(names))


@dataclass(frozen=True)
class Requirement:
    """A single regulatory or governance requirement with signal dependencies.

    `spec` is the property, written in the one language of `rulelang.py`; `formalism` names which
    fragment of that language it belongs to; `rationale` is the English explanation of the duty,
    and no verdict is derived from its wording. `requires` names the signals a system must be
    capable of emitting for this requirement to be checkable at all. It is a conjunction, so a
    branch of an either/or clause does not belong in it: see `_check_spec` and the module
    docstring.
    `binding` indicates whether this duty is a legally binding obligation (true) or an
    interpretive recital/guidance item (false). `scope` records any regulatory class the duty
    is limited to; empty means the duty is not class-limited, and anything else must be a
    member of `REGULATORY_CLASSES`. `domains` records the kinds of decision the duty is about —
    a different axis, gated separately — and every entry must be a member of `DECISION_DOMAINS`.
    An empty list means the duty is not domain-limited and reaches every system it is run
    against, which is true of the GDPR's Article 22 and false of an adverse-action notice duty.

    The fragment and signal-name checks live in `load_pack`, not here: a test that hands an
    engine a deliberately unparseable property is checking what that engine does with one, and
    refusing to construct it would test nothing.

    None of the three fields has a default, here or in the loader: defaulting a missing `binding`
    to true would silently promote an unclassified item to a legal obligation, and defaulting it
    to false would silently demote a statutory duty out of the compliance headline. Defaulting
    `scope` or `domains` to empty would make an unclassified duty a wildcard reaching every
    system — which is precisely the false positive the domain gate exists to stop, reintroduced
    as a default. A pack that has not classified a requirement is a pack that must say so and be
    fixed, not one this code guesses for.
    """

    id: str
    source_document: str
    article_clause: str
    verbatim_text: str
    stakeholder: str
    formalism: Literal[
        "record", "temporal", "logical", "counterfactual", "undetermined", "graded"
    ]
    spec: str
    rationale: str
    requires: tuple[str, ...]
    binding: bool
    scope: str
    domains: tuple[str, ...]
    deontic_type: str
    defeasibility: str
    algebra: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.binding, bool):
            raise ValueError(f"Requirement {self.id!r}: field 'binding' must be a boolean")
        if not isinstance(self.scope, str):
            raise ValueError(f"Requirement {self.id!r}: field 'scope' must be a string")
        try:
            normalize_scope(self.scope)
        except ValueError as exc:
            raise ValueError(f"Requirement {self.id!r}: field 'scope': {exc}") from exc
        try:
            object.__setattr__(self, "domains", normalize_domains(self.domains))
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"Requirement {self.id!r}: field 'domains': {exc}") from exc
        for name, vocabulary in (
            ("deontic_type", DEONTIC_TYPES),
            ("defeasibility", DEFEASIBILITY_CLASSES),
        ):
            value = getattr(self, name)
            if value not in vocabulary:
                raise ValueError(
                    f"Requirement {self.id!r}: field {name!r} is {value!r}, which is not one of "
                    f"{', '.join(repr(v) for v in vocabulary)}. This classification has no "
                    "default: see docs/refinement.md, *The defeasibility census*, for what each "
                    "member claims and how to decide which one a clause is."
                )
        if self.formalism not in VALID_FORMALISMS:
            raise ValueError(
                f"Invalid formalism {self.formalism!r}; must be one of {VALID_FORMALISMS}"
            )
        self._check_algebra()
        # Traceability is the point of a pack: a requirement with a blank source
        # document, clause or quotation cannot be checked against the print, so it
        # is malformed rather than merely incomplete.
        text_fields = (
            "id", "source_document", "article_clause", "verbatim_text", "stakeholder", "spec",
            "rationale",
        )
        for name in text_fields:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Requirement {self.id!r}: field {name!r} must be a non-empty string, "
                    f"got {value!r}"
                )
        if not self.requires:
            raise ValueError(f"Requirement {self.id!r} must specify at least one required signal")
        for signal in self.requires:
            if not isinstance(signal, str) or not signal.strip():
                raise ValueError(
                    f"Requirement {self.id!r}: every entry of 'requires' must be a non-empty "
                    f"signal name, got {signal!r}"
                )
        if len(set(self.requires)) != len(self.requires):
            raise ValueError(f"Requirement {self.id!r}: 'requires' contains duplicate signal names")

    def _check_algebra(self) -> None:
        """A graded duty carries an algebra; every other duty carries none.

        Both halves are the same rule seen from two sides, and both are refusals.

        A graded duty **without** one cannot be read at all: which residuated lattice the
        connectives are read over decides what a conjunction of two `0.5`s means, so a missing
        declaration is not a default to fill in but a semantics nobody chose. The message names
        `[grading] algebra` because that is where a pack states it.

        A two-valued duty **with** one is refused for the reason the whole open-texture design
        exists: a duty with a sharp boundary must not acquire a degree because the machinery is now
        installed. The pack loader passes the pack's declared algebra to graded requirements only,
        so a pack that ships one graded duty beside twenty presence checks leaves those twenty
        exactly as two-valued as they were.
        """
        if not isinstance(self.algebra, str):
            raise ValueError(
                f"Requirement {self.id!r}: field 'algebra' must be a string, got "
                f"{type(self.algebra).__name__}"
            )
        object.__setattr__(self, "algebra", self.algebra.strip().lower())
        if self.formalism == "graded":
            if not self.algebra:
                raise ValueError(
                    f"Requirement {self.id!r} is a graded duty and declares no algebra. A truth "
                    "degree is read over a residuated lattice, and which one changes what a "
                    "conjunction of two 0.5s means, so it is a stated parameter of the pack and "
                    "never a default this tool picks. Declare it in the pack's [grading] table — "
                    f"`algebra = \"...\"`, one of {', '.join(sorted(ALGEBRAS))} — and see "
                    "docs/semantics.md §9."
                )
            try:
                algebra_named(self.algebra)
            except ValueError as exc:
                raise ValueError(f"Requirement {self.id!r}: field 'algebra': {exc}") from exc
        elif self.algebra:
            raise ValueError(
                f"Requirement {self.id!r} declares algebra {self.algebra!r} but its formalism is "
                f"{self.formalism!r}, which is two-valued. A duty with a sharp boundary does not "
                "acquire a truth degree because a pack declares an algebra; only a spec carrying a "
                "degree() atom is classified 'graded' — see docs/semantics.md §9."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_document": self.source_document,
            "article_clause": self.article_clause,
            "verbatim_text": self.verbatim_text,
            "stakeholder": self.stakeholder,
            "formalism": self.formalism,
            "spec": self.spec,
            "rationale": self.rationale,
            "requires": list(self.requires),
            "binding": self.binding,
            "scope": self.scope,
            "domains": list(self.domains),
            "deontic_type": self.deontic_type,
            "defeasibility": self.defeasibility,
            "algebra": self.algebra,
        }


@dataclass(frozen=True)
class Pack:
    """A collection of formal requirements with source metadata.

    `algebra` is the pack's declared reading of the connectives for its graded duties, from the
    `[grading]` table of the TOML file, and `""` when the pack ships none. It is a parameter of the
    pack rather than of a requirement because a pack that read two duties over two lattices would be
    a pack whose conjunction means two things, and because a reader of one verdict must be able to
    find the declaration in one place. See `Requirement._check_algebra` and `docs/semantics.md` §9.
    """

    id: str
    title: str
    description: str
    requirements: tuple[Requirement, ...]
    source_metadata: dict[str, Any] = field(default_factory=dict)
    algebra: str = ""

    def __post_init__(self) -> None:
        if not self.requirements:
            raise ValueError(f"Pack {self.id!r} contains no requirements")
        ids = [r.id for r in self.requirements]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            # get_requirement returns the first match, so a duplicate id would make one of the
            # two requirements silently unreachable and never reported on.
            raise ValueError(f"Pack {self.id!r} has duplicate requirement id(s): {duplicates}")

    def get_requirement(self, req_id: str) -> Requirement:
        for req in self.requirements:
            if req.id == req_id:
                return req
        raise KeyError(f"Requirement {req_id!r} not found in pack {self.id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requirements": [r.to_dict() for r in self.requirements],
            "source_metadata": dict(self.source_metadata),
            "algebra": self.algebra,
        }


def _check_spec(req: Requirement, where: str) -> None:
    """Refuse a spec that is not in the language, or not in the fragment the pack declared.

    Both halves are load-time errors rather than run-time surprises. A spec labelled with the
    wrong fragment used to be a silent downgrade: an STL formula written under
    `formalism = "record"` was never parsed by anything, and the duty was answered by a presence
    check nobody asked for. Naming the fragment the formula actually belongs to is the whole
    repair, so the message says which one it is.
    """
    try:
        node = parse_property(req.spec)
        found = classify_fragment(req.spec)
    except UnsupportedConstructError as exc:
        raise ValueError(f"{where}: field 'spec': {exc}") from exc

    if found != req.formalism:
        raise ValueError(
            f"{where}: declares formalism {req.formalism!r} but its spec is a {found!r} property. "
            f"Either declare {found!r}, or write a {req.formalism!r} property. The fragments are: "
            "'record' — a conjunction of present(signal) atoms; 'temporal' — anything using a "
            "temporal operator; 'counterfactual' — a lone counterfactually_invariant(outcome, "
            "protected) atom, which is a property of a pair of executions and may be the whole of "
            "a spec or no part of one; 'undetermined' — anything using undetermined(signal, "
            "predicate, authority), the open-textured predicate no engine here settles; 'graded' — "
            "anything using degree(signal, predicate), read over the pack's declared algebra; "
            "'logical' — any other property of a single decision record."
        )

    unrequired = sorted(set(unconditional_signal_names(node)) - set(req.requires))
    if unrequired:
        raise ValueError(
            f"{where}: field 'spec' reads signal(s) not named in 'requires': "
            f"{', '.join(unrequired)}. `requires` is the capability gate that decides whether "
            "this duty is attainable, so a signal the property cannot be settled without must be "
            "listed there. Only a signal standing for one branch of an either/or is exempt: the "
            "disjunction's every branch must be settled by present() atoms, and a name every "
            "branch reads is needed whichever one settles the formula, so it stays gated."
        )


def load_pack(name_or_path: str | Path) -> Pack:
    """Load a regulation pack from a built-in pack name, an installed package, or a TOML path.

    The three are one lookup and one loader, in that order: a built-in file under `PACKS_DIR`, then
    a pack an installed package provides through the `reasonsmith.packs` entry-point group, then
    the name read as a path. A built-in wins a name collision and the shadowing entry point is
    refused with a warning (`reasonsmith.plugins`), so installing a package can never change what
    `load_pack("gdpr")` means. Whatever the route, the file goes through the checks below
    unchanged: an externally provided pack is held to every rule an in-tree one is.
    """
    from reasonsmith.plugins import pack_names, pack_path

    path = Path(name_or_path)
    if not path.is_file() and not str(name_or_path).endswith(".toml"):
        candidate = PACKS_DIR / f"{name_or_path}.toml"
        if candidate.is_file():
            path = candidate
        else:
            provided = pack_path(str(name_or_path), tuple(list_packs()))
            if provided is not None:
                path = provided

    if not path.is_file():
        installed = pack_names(tuple(list_packs()))
        raise FileNotFoundError(
            f"Pack file not found: {name_or_path}. "
            f"Built-in packs: {', '.join(list_packs()) or 'none'}"
            + (f". Installed packs: {', '.join(installed)}" if installed else "")
        )

    with path.open("rb") as f:
        data = tomllib.load(f)

    pack_info = data.get("pack", {})
    pack_id = pack_info.get("id", path.stem)
    title = pack_info.get("title", pack_id)
    description = pack_info.get("description", "")

    source_meta = data.get("source", {})

    # The pack's declared reading of the connectives for its graded duties. Refused here when it
    # names an algebra this package has no reading for, rather than at the first graded requirement:
    # a pack whose only graded duty is later removed would otherwise carry a misspelling forever.
    grading_table = data.get("grading", {})
    if not isinstance(grading_table, Mapping):
        raise ValueError(
            f"{path}: [grading] must be a table declaring `algebra`, got "
            f"{type(grading_table).__name__}"
        )
    unknown_grading = sorted(set(grading_table) - {"algebra"})
    if unknown_grading:
        raise ValueError(
            f"{path}: [grading] carries unknown key(s): {', '.join(unknown_grading)}. The table "
            "declares exactly one thing, `algebra`; where a degree came from is the caller's "
            "`manyvalued.Grading` and never the pack's — see docs/semantics.md §9"
        )
    pack_algebra = grading_table.get("algebra", "")
    if pack_algebra:
        try:
            pack_algebra = algebra_named(pack_algebra).name
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path}: [grading] algebra: {exc}") from exc

    raw_reqs = data.get("requirement", [])
    if not raw_reqs:
        raise ValueError(f"Pack {path} declares no [[requirement]] blocks")

    reqs = []
    for index, rdata in enumerate(raw_reqs):
        where = f"{path} [[requirement]] #{index + 1} ({rdata.get('id', 'no id')!r})"
        missing = [f for f in REQUIREMENT_FIELDS if f not in rdata]
        if missing:
            raise ValueError(f"{where}: missing required field(s): {', '.join(missing)}")
        # A key the loader does not read is silently dropped, so a pack with `stakeholders`
        # or a speculative `strength` would load clean and look like it carries data it does
        # not. evidence.emit rejects off-row keys for the same reason.
        unknown = sorted(set(rdata) - set(REQUIREMENT_FIELDS))
        if unknown:
            raise ValueError(
                f"{where}: unknown field(s): {', '.join(unknown)}. A requirement block carries "
                f"exactly these fields: {', '.join(REQUIREMENT_FIELDS)}"
            )
        if not isinstance(rdata["binding"], bool):
            raise ValueError(
                f"{where}: 'binding' must be a boolean, got {type(rdata['binding']).__name__}"
            )
        if not isinstance(rdata["scope"], str):
            raise ValueError(
                f"{where}: 'scope' must be a string, got {type(rdata['scope']).__name__}"
            )
        # A bare string is iterable, so tuple("reasons") would silently become five
        # single-character signal names. Reject anything that is not a TOML array.
        if not isinstance(rdata["requires"], list):
            raise ValueError(
                f"{where}: 'requires' must be an array of signal names, got "
                f"{type(rdata['requires']).__name__}"
            )
        if not isinstance(rdata["domains"], list):
            raise ValueError(
                f"{where}: 'domains' must be an array of decision domains — write `domains = []` "
                f"for a duty that is not domain-limited — got "
                f"{type(rdata['domains']).__name__}"
            )
        try:
            req = Requirement(
                id=rdata["id"],
                source_document=rdata["source_document"],
                article_clause=rdata["article_clause"],
                verbatim_text=rdata["verbatim_text"],
                stakeholder=rdata["stakeholder"],
                formalism=rdata["formalism"],
                spec=rdata["spec"],
                rationale=rdata["rationale"],
                requires=tuple(rdata["requires"]),
                binding=rdata["binding"],
                scope=rdata["scope"],
                domains=tuple(rdata["domains"]),
                deontic_type=rdata["deontic_type"],
                defeasibility=rdata["defeasibility"],
                # Handed to a graded requirement and to no other, which is the whole of the
                # guarantee that a pack shipping one graded duty leaves its two-valued duties
                # two-valued: `Requirement._check_algebra` refuses a non-graded duty carrying one.
                algebra=pack_algebra if rdata["formalism"] == "graded" else "",
            )
        except (TypeError, ValueError) as exc:
            # Both become a load error: a caller of `load_pack` is told the pack is refused and
            # which block is at fault, not which of two exception types the field check chose.
            raise ValueError(f"{where}: {exc}") from exc
        _check_spec(req, where)
        reqs.append(req)

    return Pack(
        id=pack_id,
        title=title,
        description=description,
        requirements=tuple(reqs),
        source_metadata=source_meta,
        algebra=pack_algebra,
    )


def list_packs() -> list[str]:
    """List names of built-in requirement packs."""
    if not PACKS_DIR.exists():
        return []
    return sorted(p.stem for p in PACKS_DIR.glob("*.toml"))
