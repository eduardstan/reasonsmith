"""Tests for the decision-domain gate: what kind of decision a duty is about.

What this module is for:
  An adverse-action notification duty under 12 CFR 1002.9 used to reach a graph-reachability
  benchmark that issues no credit and notifies nobody, and report it `satisfied`
  (`docs/findings-nesyarena.md`, finding 3). `scope` could not catch it: that gate is a
  *regulatory class* from the EU AI Act's own vocabulary, and a subject matter is a different
  axis. `domains` is that second axis, and these tests hold it to the one guarantee it claims:
  **a system that has not declared its domain is never reported `satisfied` on a domain-limited
  duty.**

What a reader must not break:
  - The wildcard must stay deliberate. A duty with `domains = []` reaches every system, including
    one that declares nothing — the GDPR's Article 22 is genuinely not domain-limited. If that
    behaviour arrived by omission rather than by declaration, the gate would be worthless the
    moment a pack author forgot the field, so the loader refuses a requirement without it and
    `test_a_pack_that_has_not_classified_a_requirement_is_refused` is what holds that.
  - `not_applicable` and not `inconclusive` for an undeclared system. The two mean different
    things (`reasonsmith.verdict.Verdict`), and the choice is argued in `docs/semantics.md` §4:
    it matches what the class gate already does with an undeclared class, and the reason string
    says which of the two ways the duty failed to reach the system so nobody reads it as cleared.
  - Both entry points must agree. `check_conformance` plans applicability before running anything
    and `evaluate_requirement` answers it per requirement; a system that got a different answer
    from the two would make a whole-pack run disagree with a single check of the same duty.
"""

from __future__ import annotations

import html

import pytest

from reasonsmith.report import check_conformance, evaluate_requirement
from reasonsmith.spec import DECISION_DOMAINS, load_pack, normalize_domains
from reasonsmith.sut import BaseSUT
from reasonsmith.verdict import Strength, Verdict

#: A duty about consumer credit, and the signals a system needs to discharge it. Loaded from the
#: shipped pack rather than written here: a test that authored its own requirement would pass
#: while the pack said something else.
CREDIT_DUTY = "ecoa_reg_b_1002_9_b_2_specific_reasons"

#: A duty about no particular kind of decision. GDPR Article 22 governs solely-automated decisions
#: whatever they are about, which is why its `domains` is empty and must stay so.
ANY_DOMAIN_DUTY = "gdpr_art22_1_automated_decision_prohibition"


def _duty(pack_name: str, req_id: str):
    return load_pack(pack_name).get_requirement(req_id)


def _system(req, domains=None) -> BaseSUT:
    """A system that can emit everything this duty asks for, declaring `domains` or nothing.

    Capabilities are complete on purpose. An unattainable result would answer these tests for the
    wrong reason — the point is a system that *could* discharge the duty and still must not be
    reported as having done so.
    """
    sut = BaseSUT(set(req.requires))
    if domains is not None:
        sut.system_domains = domains
    return sut


def _records(req, count: int = 2) -> list[dict]:
    """`count` decision records carrying a value for every signal the duty reads."""
    return [{signal: f"{signal}-{i}" for signal in req.requires} for i in range(count)]


def test_an_undeclared_system_cannot_reach_satisfied_on_a_domain_limited_duty():
    """The defect, in the smallest form that reproduces it.

    Everything else is in place: the system declares every signal, the trace carries a value for
    each of them in every record, and the record engine would answer `satisfied`. The one thing
    missing is any statement of what kind of decision this system makes — and that alone must be
    enough to stop a consumer-credit duty being discharged against it.
    """
    req = _duty("ecoa", CREDIT_DUTY)
    assert req.domains == ("consumer-credit",)

    undeclared = _system(req)
    assert not hasattr(undeclared, "system_domains")

    result = evaluate_requirement(req, undeclared, _records(req))
    assert result.verdict == Verdict.NOT_APPLICABLE
    assert result.strength is None, "nothing was checked, so nothing may claim a strength"
    assert result.signals_missing == ()
    assert "undeclared" in result.evidence_summary
    assert "never infers a system's decision domain" in result.evidence_summary

    # The same system, having said what it decides, is judged on its evidence again.
    declared = _system(req, ("consumer-credit",))
    assert evaluate_requirement(req, declared, _records(req)).verdict == Verdict.SATISFIED


def test_a_system_in_another_domain_is_not_applicable_rather_than_judged():
    """A declared mismatch and an undeclared system are both out of reach, and are worded apart.

    Collapsing the two would lose the instruction: an undeclared system needs a declaration, a
    mismatched one needs no action at all.
    """
    req = _duty("ecoa", CREDIT_DUTY)
    result = evaluate_requirement(req, _system(req, ("healthcare",)), _records(req))
    assert result.verdict == Verdict.NOT_APPLICABLE
    assert "declared as healthcare" in result.evidence_summary


def test_a_duty_with_no_domain_still_reaches_a_system_that_declares_none():
    """The wildcard case, which must be deliberate rather than accidental.

    GDPR Article 22 is not domain-limited: it governs a solely-automated decision whatever the
    decision is about. A gate that quietly made *every* undeclared system unreachable would trade
    one false negative for a much larger one, so a duty carrying `domains = []` is answered on its
    evidence against a system that declares nothing — and the pack has to say so by writing the
    empty list, which `test_a_pack_that_has_not_classified_a_requirement_is_refused` enforces.
    """
    req = _duty("gdpr", ANY_DOMAIN_DUTY)
    assert req.domains == ()

    undeclared = _system(req)
    result = evaluate_requirement(req, undeclared, _records(req))
    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.OBSERVED

    # And it reaches a system that declared some *other* domain, too: an unset domain is not a
    # domain nothing matches, it is the absence of the limit.
    elsewhere = _system(req, ("criminal-justice",))
    assert evaluate_requirement(req, elsewhere, _records(req)).verdict == Verdict.SATISFIED


def test_matching_is_intersection_so_one_shared_domain_is_enough():
    """A system may decide in several domains, and a duty may govern several.

    Requiring the system's declaration to be a subset of the duty's would report a lender that
    also underwrites insurance out of reach of Regulation B, which is wrong in the direction that
    matters: it would clear a duty that does govern the system.
    """
    req = _duty("ecoa", CREDIT_DUTY)
    both = _system(req, ("insurance", "consumer-credit"))
    assert evaluate_requirement(req, both, _records(req)).verdict == Verdict.SATISFIED


def test_the_two_domain_gates_never_disagree():
    """`check_conformance` plans applicability; `evaluate_requirement` answers it. Same answer.

    The plan exists so the decision trace is read at most once and never at all for a pack nothing
    in which is applicable. A second, looser idea of applicability living in that plan would make
    a whole-pack run disagree with a single check of one of its duties.
    """
    pack = load_pack("ecoa")
    signals = {s for req in pack.requirements for s in req.requires}
    for domains in (None, (), ("consumer-credit",), ("healthcare",)):
        sut = BaseSUT(signals)
        if domains is not None:
            sut.system_domains = domains
        report = check_conformance(sut, pack, system_domains=domains)
        for req, result in zip(pack.requirements, report.results, strict=True):
            direct = evaluate_requirement(req, sut, system_domains=domains)
            assert result.verdict == direct.verdict, req.id


def test_an_undeclared_domain_never_runs_the_system():
    """Applicability is settled before anything is executed, exactly as the class gate is.

    Running a system to answer a duty that does not govern it is work whose result must be thrown
    away, and a report that quietly executed a system it then declared out of reach would be
    describing a run the reader cannot see.
    """
    pack = load_pack("ecoa")

    class CountingSUT(BaseSUT):
        def __init__(self):
            super().__init__({s for req in pack.requirements for s in req.requires})
            self.execution_count = 0

        def decisions(self):
            self.execution_count += 1
            return []

    sut = CountingSUT()
    report = check_conformance(sut, pack)
    assert all(r.verdict == Verdict.NOT_APPLICABLE for r in report.results)
    assert sut.execution_count == 0


def test_a_pack_that_has_not_classified_a_requirement_is_refused(tmp_path):
    """No default. A missing `domains` is a pack to fix, never a duty to guess at.

    Defaulting it to empty would make every unclassified requirement a wildcard reaching every
    system — which is the false positive this gate exists to stop, reintroduced as a default and
    invisible because it looks like a deliberate `[]`.
    """
    fields = {
        "id": '"r1"',
        "source_document": '"Doc"',
        "article_clause": '"Art. 1"',
        "verbatim_text": '"quoted"',
        "stakeholder": '"deployer"',
        "formalism": '"record"',
        "spec": '"present(signal_a)"',
        "rationale": '"Why this duty exists."',
        "requires": '["signal_a"]',
        "binding": "true",
        "scope": '""',
    }

    def write(extra: str) -> str:
        path = tmp_path / "custom.toml"
        body = "".join(f"{k} = {v}\n" for k, v in fields.items())
        path.write_text(
            '[pack]\nid = "custom"\n\n[[requirement]]\n' + body + extra, encoding="utf-8"
        )
        return str(path)

    with pytest.raises(ValueError, match=r"'r1'.*missing required field\(s\): domains"):
        load_pack(write(""))

    with pytest.raises(ValueError, match="'domains' must be an array of decision domains"):
        load_pack(write('domains = "consumer-credit"\n'))

    assert load_pack(write("domains = []\n")).requirements[0].domains == ()


@pytest.mark.parametrize(
    "typo", ["consumer credit", "consumer_credit", "credit", "Consumer-Credit ", ""]
)
def test_a_domain_outside_the_vocabulary_is_refused(tmp_path, typo):
    """A misspelling must not pass for a system that is simply about something else.

    Both sides of the comparison are checked against `DECISION_DOMAINS`, because a typo on either
    side fails silently and in opposite directions: in a pack it leaves a duty no system can ever
    match, and on a caller it turns every domain-limited duty not applicable in a run that still
    exits clean. Only case and surrounding whitespace are normalised — `Consumer-Credit ` is the
    same domain, `consumer_credit` is not, and guessing between the two is how a run answers a
    duty it was never told applies.
    """
    if typo.strip().lower() in DECISION_DOMAINS:
        assert normalize_domains([typo]) == (typo.strip().lower(),)
        return

    with pytest.raises(ValueError, match="not a known decision domain"):
        normalize_domains([typo])

    with pytest.raises(ValueError, match="not a known declared system decision domain"):
        check_conformance(BaseSUT(set()), load_pack("ecoa"), system_domains=[typo])


def test_a_domain_list_is_domain_names_and_nothing_else():
    """A bare string is iterable, and a mapping is iterable over its keys.

    `"housing"` would otherwise declare seven single-character domains, and a `{domain: bool}` map
    would declare the domains it marks False — the overclaim every other collection site in this
    package already refuses.
    """
    with pytest.raises(TypeError, match="not a single string"):
        normalize_domains("housing")
    with pytest.raises(TypeError, match="not a map"):
        normalize_domains({"housing": False})
    with pytest.raises(ValueError, match="duplicate decision domain"):
        normalize_domains(["housing", "housing"])
    assert normalize_domains(None) == ()
    assert normalize_domains([]) == ()


def test_every_shipped_pack_classifies_every_requirement():
    """The loader refuses an unclassified requirement, so this asserts what the packs chose.

    Load-time refusal only proves the field is present. That every domain a shipped pack names is
    in the vocabulary, and that the packs which use one say so in their description, is what keeps
    the classification readable by someone checking it rather than merely well-formed.
    """
    described = {"ecoa", "table7"}
    for name in ("ecoa", "eu_ai_act", "gpai", "gdpr", "table7"):
        pack = load_pack(name)
        uses_a_domain = False
        for req in pack.requirements:
            assert set(req.domains) <= set(DECISION_DOMAINS), req.id
            uses_a_domain |= bool(req.domains)
        assert uses_a_domain == (name in described), name
        if uses_a_domain:
            assert "DECISION_DOMAINS" in pack.description, (
                f"{name} limits a duty to a domain without saying in its description that the "
                "vocabulary is the pack author's rather than the regulation's"
            )


def test_a_run_that_skipped_duties_for_a_missing_declaration_says_so():
    """The exit code cannot carry this, so the report has to.

    A duty skipped for an undeclared domain is reported not applicable, and only a violation
    exits non-zero — so an existing gate over the ECOA pack goes green the moment this version
    lands and stays green over duties nothing looked at. Every rendering therefore names the
    count and what to pass to un-skip it. A *declared* mismatch is a real answer and must not
    raise the same alarm: a notice that fires when nothing is missing teaches a reader to skip it.
    """
    pack = load_pack("ecoa")
    signals = {s for req in pack.requirements for s in req.requires}

    undeclared = check_conformance(BaseSUT(signals), pack)
    assert len(undeclared.skipped_for_undeclared_domain) == len(pack.requirements)
    notice = undeclared.undeclared_domain_notice
    assert notice is not None
    assert f"{len(pack.requirements)} domain-limited duties were" in notice
    assert "--system-domain <domain>" in notice
    assert f"DUTIES NOT CHECKED: {notice}" in undeclared.render_text()
    assert html.escape(notice) in undeclared.render_html(commit_hash="")

    mismatched = check_conformance(BaseSUT(signals), pack, system_domains=["healthcare"])
    assert all(r.verdict == Verdict.NOT_APPLICABLE for r in mismatched.results)
    assert mismatched.skipped_for_undeclared_domain == ()
    assert mismatched.undeclared_domain_notice is None
    assert "DUTIES NOT CHECKED" not in mismatched.render_text()

    declared = check_conformance(BaseSUT(signals), pack, system_domains=["consumer-credit"])
    assert declared.skipped_for_undeclared_domain == ()
    assert declared.undeclared_domain_notice is None
