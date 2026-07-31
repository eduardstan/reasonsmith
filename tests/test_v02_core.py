"""Tests for reasonsmith v0.2 core foundations (Stage 1)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from reasonsmith.report import (
    ConformanceReport,
    RequirementResult,
    analyze_unattainable,
    check_conformance,
    evaluate_requirement,
)
from reasonsmith.spec import PACKS_DIR, Pack, Requirement, list_packs, load_pack
from reasonsmith.sut import REASON_SIGNALS, BaseSUT, FullCapabilitySUT, NoReasonsSUT
from reasonsmith.verdict import (
    Strength,
    Verdict,
    combine_verdicts,
    max_strength,
    min_strength,
)

TABLE7_SOURCE = Path(__file__).resolve().parents[1] / "src" / "reasonsmith" / "table7.toml"


def _requirement(**overrides) -> Requirement:
    """A minimal valid requirement, for tests that vary one field at a time."""
    fields = {
        "id": "r1",
        "source_document": "Doc",
        "article_clause": "Art. 1",
        "verbatim_text": "quoted text",
        "stakeholder": "deployer",
        "formalism": "record",
        "spec": "a spec",
        "requires": ("signal_a",),
    }
    fields.update(overrides)
    return Requirement(**fields)


def _write_pack(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "custom.toml"
    path.write_text('[pack]\nid = "custom"\n\n' + body, encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# verdict.py — the lattice
# --------------------------------------------------------------------------------------


def test_strength_lattice_ordering():
    """Strength lattice forms a strict total order: unattainable < observed < probed < proved."""
    assert Strength.UNATTAINABLE < Strength.OBSERVED
    assert Strength.OBSERVED < Strength.PROBED
    assert Strength.PROBED < Strength.PROVED

    # Transitive checks
    assert Strength.UNATTAINABLE < Strength.PROVED
    assert Strength.OBSERVED < Strength.PROVED

    # Reflexivity and the derived operators total_ordering fills in
    assert Strength.OBSERVED <= Strength.OBSERVED
    assert Strength.PROVED > Strength.OBSERVED
    assert not Strength.OBSERVED < Strength.OBSERVED

    ladder = [Strength.UNATTAINABLE, Strength.OBSERVED, Strength.PROBED, Strength.PROVED]
    assert sorted(reversed(ladder)) == ladder

    assert min_strength(ladder) == Strength.UNATTAINABLE
    assert max_strength(ladder) == Strength.PROVED
    assert min_strength(["proved"]) == Strength.PROVED

    # Parsing
    assert Strength.parse("unattainable") == Strength.UNATTAINABLE
    assert Strength.parse("PROVED") == Strength.PROVED
    assert Strength.parse(Strength.PROBED) == Strength.PROBED
    with pytest.raises(ValueError, match="Unknown strength"):
        Strength.parse("invalid_strength")


def test_strength_comparison_rejects_foreign_types():
    """A strength never silently orders against something that is not a strength."""
    with pytest.raises(TypeError):
        _ = Strength.OBSERVED < "proved"


def test_min_max_strength_reject_empty():
    """There is no weakest or strongest evidence in an empty collection; refuse to invent one."""
    with pytest.raises(ValueError, match="empty collection"):
        min_strength([])
    with pytest.raises(ValueError, match="empty collection"):
        max_strength([])


def test_verdict_combination():
    """Verdict combination follows worst-case propagation: VIOLATED > INCONCLUSIVE > SATISFIED."""
    assert combine_verdicts([Verdict.SATISFIED, Verdict.SATISFIED]) == Verdict.SATISFIED
    assert combine_verdicts([Verdict.SATISFIED, Verdict.INCONCLUSIVE]) == Verdict.INCONCLUSIVE
    assert combine_verdicts([Verdict.SATISFIED, Verdict.VIOLATED]) == Verdict.VIOLATED
    assert combine_verdicts([Verdict.INCONCLUSIVE, Verdict.VIOLATED]) == Verdict.VIOLATED
    assert combine_verdicts(["satisfied", Verdict.VIOLATED]) == Verdict.VIOLATED

    # String representation and parsing
    assert str(Verdict.SATISFIED) == "satisfied"
    assert Verdict.parse("violated") == Verdict.VIOLATED
    with pytest.raises(ValueError, match="Unknown verdict"):
        Verdict.parse("invalid_verdict")


def test_combining_no_verdicts_is_not_satisfied():
    """Having checked nothing is not evidence that a requirement holds.

    An empty conjunction is vacuously true in logic, but a conformance run that evaluated no
    sub-property must not come back compliant — that is the one defect that would make every
    other verdict in this tool worthless.
    """
    assert combine_verdicts([]) == Verdict.INCONCLUSIVE


# --------------------------------------------------------------------------------------
# spec.py — the pack loader
# --------------------------------------------------------------------------------------


def test_load_table7_pack():
    """Table 7 pack loads correctly from TOML with verbatim traceability."""
    packs = list_packs()
    assert "table7" in packs

    pack = load_pack("table7")
    assert pack.id == "table7"
    assert len(pack.requirements) == 6

    req_gdpr = pack.get_requirement("gdpr_art22_meaningful_information")
    assert req_gdpr.source_document == "GDPR"
    assert req_gdpr.article_clause == "Art. 22 (and Rec. 71)"
    assert req_gdpr.verbatim_text == (
        "Automated decisions: “meaningful information about the logic involved”"
    )
    assert req_gdpr.formalism == "record"
    assert "per_decision_reason_string" in req_gdpr.requires

    req_ecoa = pack.get_requirement("ecoa_reg_b_adverse_action")
    assert req_ecoa.source_document == "ECOA / Reg B"
    assert "stored_reasons_per_decision" in req_ecoa.requires

    with pytest.raises(KeyError, match="not found in pack"):
        pack.get_requirement("no_such_requirement")

    assert load_pack(PACKS_DIR / "table7.toml").to_dict() == pack.to_dict()
    with pytest.raises(FileNotFoundError):
        load_pack("no_such_pack")


def test_pack_matches_table7_transcription():
    """The shipped pack is derived from the transcription, and stays derived.

    `src/reasonsmith/table7.toml` is the authority — a verbatim transcription of the printed
    table. The pack restates those rows as requirements, so any drift between the two is a
    traceability failure: a lawyer checking the pack against the print would find text the
    paper does not contain. This test is what makes the pack's header claim true.
    """
    duties = tomllib.loads(TABLE7_SOURCE.read_text(encoding="utf-8"))["duty"]
    by_id = {d["id"]: d for d in duties}
    pack = load_pack("table7")

    assert [r.id for r in pack.requirements] == [d["id"] for d in duties], (
        "pack requirements must be the six Table 7 rows, in printed order"
    )

    for req in pack.requirements:
        duty = by_id[req.id]
        assert req.verbatim_text == duty["requirement"], (
            f"{req.id}: verbatim_text must quote the Requirement column exactly"
        )
        # The paper gives one Legal source string; the pack splits it so code can address the
        # document separately. The two halves must RECONSTRUCT the printed string, separated
        # only by punctuation: a substring test would accept "ECOA" for "ECOA / Reg B", or
        # "Art. 22" for "Art. 22 (and Rec. 71)", silently citing less than the paper prints.
        legal_source = duty["legal_source"]
        assert legal_source.startswith(req.source_document), (
            f"{req.id}: source_document {req.source_document!r} does not open the printed "
            f"legal source {legal_source!r}"
        )
        rest = legal_source[len(req.source_document) :]
        start = rest.find(req.article_clause)
        assert start != -1, (
            f"{req.id}: article_clause {req.article_clause!r} is not in the printed "
            f"legal source {legal_source!r}"
        )
        separators = set(" ();")
        before, after = rest[:start], rest[start + len(req.article_clause) :]
        assert set(before) <= separators and set(after) <= separators, (
            f"{req.id}: source_document {req.source_document!r} and article_clause "
            f"{req.article_clause!r} do not reconstruct the printed legal source "
            f"{legal_source!r}; text {before + after!r} would be dropped"
        )
        assert list(req.requires) == [f["key"] for f in duty["evidence_field"]], (
            f"{req.id}: required signals must be the row's evidence fields, in printed order"
        )


def test_pack_source_metadata_matches_transcription():
    """The pack's [source] block cites the same publication as the transcription."""
    source = tomllib.loads(TABLE7_SOURCE.read_text(encoding="utf-8"))["source"]
    meta = load_pack("table7").source_metadata
    for key in ("table", "caption", "paper", "authors", "venue", "publication_date", "page"):
        assert meta[key] == source[key], f"pack cites a different {key} than the transcription"


@pytest.mark.parametrize(
    "field_name",
    ["id", "source_document", "article_clause", "verbatim_text", "stakeholder", "formalism",
     "spec", "requires"],
)
def test_loader_rejects_missing_field(tmp_path, field_name):
    """A requirement missing any field is a malformed pack, not a partial one."""
    fields = {
        "id": '"r1"',
        "source_document": '"Doc"',
        "article_clause": '"Art. 1"',
        "verbatim_text": '"quoted"',
        "stakeholder": '"deployer"',
        "formalism": '"record"',
        "spec": '"a spec"',
        "requires": '["signal_a"]',
    }
    del fields[field_name]
    body = "[[requirement]]\n" + "".join(f"{k} = {v}\n" for k, v in fields.items())
    with pytest.raises(ValueError, match=f"missing required field.*{field_name}"):
        load_pack(_write_pack(tmp_path, body))


def test_loader_rejects_requires_as_bare_string(tmp_path):
    """`requires = "reasons"` must fail, not become six single-character signals.

    A bare string is iterable, so tupling it silently yields ('r', 'e', 'a', 's', ...). Every
    one of those would then be reported as a missing signal, turning a typo into a confident
    architectural finding about signals nobody ever named.
    """
    body = (
        '[[requirement]]\nid = "r1"\nsource_document = "Doc"\narticle_clause = "Art. 1"\n'
        'verbatim_text = "quoted"\nstakeholder = "deployer"\nformalism = "record"\n'
        'spec = "a spec"\nrequires = "per_decision_reason_string"\n'
    )
    with pytest.raises(ValueError, match="must be an array of signal names"):
        load_pack(_write_pack(tmp_path, body))


def test_loader_rejects_blank_and_duplicate_fields(tmp_path):
    """Blank traceability fields, blank signals and duplicate ids are all rejected."""
    base = (
        '[[requirement]]\nid = "r1"\nsource_document = "Doc"\narticle_clause = "Art. 1"\n'
        'verbatim_text = {verbatim}\nstakeholder = "deployer"\nformalism = "record"\n'
        'spec = "a spec"\nrequires = {requires}\n'
    )
    with pytest.raises(ValueError, match="verbatim_text.*non-empty"):
        load_pack(_write_pack(tmp_path, base.format(verbatim='"   "', requires='["a"]')))
    with pytest.raises(ValueError, match="non-empty\n?.*signal name|signal name"):
        load_pack(_write_pack(tmp_path, base.format(verbatim='"q"', requires='["a", ""]')))
    with pytest.raises(ValueError, match="duplicate signal names"):
        load_pack(_write_pack(tmp_path, base.format(verbatim='"q"', requires='["a", "a"]')))

    one = base.format(verbatim='"q"', requires='["a"]')
    with pytest.raises(ValueError, match="duplicate requirement id"):
        load_pack(_write_pack(tmp_path, one + "\n" + one))


def test_loader_rejects_empty_pack_and_bad_formalism(tmp_path):
    """A pack with no requirements, or an unknown formalism, is malformed."""
    with pytest.raises(ValueError, match="declares no .*requirement.* blocks"):
        load_pack(_write_pack(tmp_path, ""))

    body = (
        '[[requirement]]\nid = "r1"\nsource_document = "Doc"\narticle_clause = "Art. 1"\n'
        'verbatim_text = "q"\nstakeholder = "deployer"\nformalism = "vibes"\n'
        'spec = "a spec"\nrequires = ["a"]\n'
    )
    with pytest.raises(ValueError, match="Invalid formalism"):
        load_pack(_write_pack(tmp_path, body))


def test_loader_error_names_the_offending_block(tmp_path):
    """A malformed pack says which file and which block, not just which key."""
    good = (
        '[[requirement]]\nid = "r1"\nsource_document = "Doc"\narticle_clause = "Art. 1"\n'
        'verbatim_text = "q"\nstakeholder = "deployer"\nformalism = "record"\n'
        'spec = "a spec"\nrequires = ["a"]\n'
    )
    bad = good.replace('id = "r1"', 'id = "r2"').replace('spec = "a spec"\n', "")
    with pytest.raises(ValueError, match=r"custom\.toml \[\[requirement\]\] #2 \('r2'\)"):
        load_pack(_write_pack(tmp_path, good + "\n" + bad))


def test_loader_rejects_an_unknown_field(tmp_path):
    """A key the loader never reads would vanish, leaving a pack that looks complete."""
    good = (
        '[[requirement]]\nid = "r1"\nsource_document = "Doc"\narticle_clause = "Art. 1"\n'
        'verbatim_text = "q"\nstakeholder = "deployer"\nformalism = "record"\n'
        'spec = "a spec"\nrequires = ["a"]\n'
    )
    with pytest.raises(ValueError, match=r"custom\.toml.*unknown field\(s\): stakeholders"):
        load_pack(_write_pack(tmp_path, good + 'stakeholders = "deployer"\n'))
    with pytest.raises(ValueError, match=r"unknown field\(s\): strength"):
        load_pack(_write_pack(tmp_path, good + 'strength = "proved"\n'))


def test_requirement_needs_at_least_one_signal():
    """A requirement with no required signals could never be unattainable, so it is malformed."""
    with pytest.raises(ValueError, match="at least one required signal"):
        _requirement(requires=())


# --------------------------------------------------------------------------------------
# sut.py + the unattainable analysis
# --------------------------------------------------------------------------------------


def test_base_sut_rejects_a_bare_capability_string():
    """set("reasons") would declare six one-character capabilities; refuse the string."""
    with pytest.raises(TypeError, match="not a single string"):
        BaseSUT("per_decision_reason_string")
    assert BaseSUT({"a", "b"}).capabilities() == {"a", "b"}
    assert BaseSUT(["a"]).capabilities() == {"a"}
    assert BaseSUT({"a": None, "b": None}.keys()).capabilities() == {"a", "b"}


def test_base_sut_rejects_a_capability_map():
    """Iterating a map yields its keys, so a signal switched off would read as declared."""
    with pytest.raises(TypeError, match="not a capability map"):
        BaseSUT({"per_decision_reason_string": False, "model_version": True})


def test_reference_systems_declare_the_packs_signals():
    """The reference systems are derived from the pack, so they cannot drift from it."""
    pack_signals = {s for req in load_pack("table7").requirements for s in req.requires}
    full = FullCapabilitySUT().capabilities()
    assert pack_signals <= full
    assert REASON_SIGNALS <= pack_signals

    no_reasons = NoReasonsSUT().capabilities()
    assert no_reasons == full - REASON_SIGNALS
    assert full - no_reasons == set(REASON_SIGNALS)


def test_unattainable_analysis_no_execution():
    """Definition of Done: a system declaring no reason-giving capability is reported
    unattainable for the reason-giving requirements, with the missing signals named, WITHOUT
    the system being executed at all.
    """
    no_reasons_sut = NoReasonsSUT()
    pack = load_pack("table7")

    reason_reqs = [
        pack.get_requirement("gdpr_art22_meaningful_information"),
        pack.get_requirement("ecoa_reg_b_adverse_action"),
    ]

    for req in reason_reqs:
        expected = sorted(REASON_SIGNALS & set(req.requires))
        assert expected, "each reason-giving requirement names a reason signal"

        is_unattainable, missing = analyze_unattainable(req, no_reasons_sut)
        assert is_unattainable is True
        assert list(missing) == expected

        result = evaluate_requirement(req, no_reasons_sut)
        assert result.strength == Strength.UNATTAINABLE
        assert result.verdict == Verdict.INCONCLUSIVE
        assert list(result.signals_missing) == expected
        # The finding must name the signal, not merely count it.
        for signal in expected:
            assert signal in result.evidence_summary

    # Crucial assertion: decisions() was NEVER executed.
    assert no_reasons_sut.was_executed is False


def test_unattainable_requirement_never_reaches_the_trace():
    """Second, independent proof of the same guarantee: a trace that cannot be read at all.

    NoReasonsSUT proves it by a flag it sets when read; this proves it by making the read
    itself impossible, so the guarantee does not rest on one system remembering to record it.
    """

    class ExplodingTraceSUT(BaseSUT):
        def decisions(self):
            raise AssertionError("the trace must not be read for an unattainable requirement")

    req = _requirement(requires=("signal_a", "signal_b"))
    sut = ExplodingTraceSUT({"signal_a"})

    result = evaluate_requirement(req, sut)
    assert result.strength == Strength.UNATTAINABLE
    assert result.signals_missing == ("signal_b",)

    report = check_conformance(sut, Pack("p", "P", "", (req,)))
    assert report.headline == "1 requirements · 1 unattainable"


def test_check_conformance_never_executes_a_system_it_cannot_check():
    """A whole-pack run over an all-unattainable pack reads no decisions at all."""
    pack = load_pack("table7")
    no_reasons_sut = NoReasonsSUT()
    reason_pack = Pack(
        id="reason_subset",
        title="Reason Requirements",
        description="Subset of reason-requiring duties",
        requirements=(
            pack.get_requirement("gdpr_art22_meaningful_information"),
            pack.get_requirement("ecoa_reg_b_adverse_action"),
        ),
    )

    report = check_conformance(no_reasons_sut, reason_pack, system_name="BlackBoxNeuralModel")
    assert no_reasons_sut.was_executed is False
    assert report.headline == "2 requirements · 2 unattainable"
    assert report.counts["unattainable"] == 2
    assert report.counts["observed"] == 0

    text = report.render_text()
    assert "MISSING SIGNALS: per_decision_reason_string" in text
    assert "UNATTAINABLE" in text


def test_unattainable_analysis_reports_every_missing_signal():
    """The finding names all shortfalls, so a fix list is complete rather than one-at-a-time."""
    req = _requirement(requires=("a", "b", "c"))
    is_unattainable, missing = analyze_unattainable(req, BaseSUT({"b"}))
    assert is_unattainable is True
    assert missing == ("a", "c")

    is_unattainable, missing = analyze_unattainable(req, BaseSUT({"a", "b", "c", "extra"}))
    assert is_unattainable is False
    assert missing == ()


def test_unattainable_analysis_rejects_a_bad_capabilities_return():
    """A SUT returning a string would have every character read as a declared signal."""

    class StringCapabilities:
        def capabilities(self):
            return "abc"

        def decisions(self):
            return []

    with pytest.raises(TypeError, match="must return a collection"):
        analyze_unattainable(_requirement(requires=("a",)), StringCapabilities())

    class DictKeyCapabilities:
        def capabilities(self):
            return {"a": None, "b": None}.keys()

        def decisions(self):
            return []

    # dict_keys is a collection of names, so it is accepted: the guard rejects a bare
    # string, not every type that is not a set.
    assert analyze_unattainable(_requirement(requires=("a",)), DictKeyCapabilities()) == (
        False,
        (),
    )


def test_unattainable_analysis_rejects_a_capability_map():
    """A map is iterable over its keys, so a signal declared unavailable would read as declared.

    `{"per_decision_reason_string": False}` says the system cannot give reasons. Reading its
    keys would report the requirement checkable and judge it against the trace instead of
    reporting it unattainable — the overclaim direction this analysis exists to close.
    """

    class MappingCapabilities:
        def capabilities(self):
            return {"per_decision_reason_string": False, "model_version": True}

        def decisions(self):
            return []

    req = _requirement(requires=("per_decision_reason_string",))
    with pytest.raises(TypeError, match="not a capability map"):
        analyze_unattainable(req, MappingCapabilities())


def test_no_reasons_system_against_the_whole_table7_pack():
    """The headline this stage exists to produce, from the most obvious call in the API.

    A system that keeps a trace but gives no reasons is checkable on four Table 7 rows and
    unattainable on the two that need a reason — reported in one line, without either half
    being quietly dropped or the run failing.
    """
    sut = NoReasonsSUT()
    report = check_conformance(sut, load_pack("table7"), system_name="BlackBoxNeuralModel")

    assert report.headline == "6 requirements · 4 observed · 2 unattainable"
    assert sut.was_executed is True

    unattainable = [r.requirement_id for r in report.results if r.strength == Strength.UNATTAINABLE]
    assert unattainable == ["gdpr_art22_meaningful_information", "ecoa_reg_b_adverse_action"]
    for res in report.results:
        if res.strength == Strength.UNATTAINABLE:
            assert set(res.signals_missing) <= REASON_SIGNALS
        else:
            assert res.verdict == Verdict.SATISFIED
            assert res.strength == Strength.OBSERVED


def test_the_whole_pack_is_checked_with_one_execution():
    """Reading the trace once per requirement would re-run a system six times over."""
    full_sut = FullCapabilitySUT()
    check_conformance(full_sut, load_pack("table7"))
    assert full_sut.execution_count == 1


# --------------------------------------------------------------------------------------
# report.py — no verdict stronger than its evidence
# --------------------------------------------------------------------------------------


def test_full_conformance_report():
    """FullCapabilitySUT achieves observed strength across all Table 7 requirements."""
    full_sut = FullCapabilitySUT()
    pack = load_pack("table7")

    report = check_conformance(full_sut, pack, system_name="FullReferenceModel")
    assert report.system_name == "FullReferenceModel"
    assert report.pack_id == "table7"
    assert len(report.results) == 6

    for res in report.results:
        assert res.strength == Strength.OBSERVED
        assert res.verdict == Verdict.SATISFIED
        assert res.signals_missing == ()

    assert report.headline == "6 requirements · 6 observed"

    # Serialization tests (house pattern)
    r_dict = report.to_dict()
    assert r_dict["headline"] == "6 requirements · 6 observed"
    assert r_dict["counts"]["observed"] == 6
    assert "limits" in r_dict

    r_json = report.to_json(indent=2)
    parsed = json.loads(r_json)
    assert parsed["system_name"] == "FullReferenceModel"
    assert parsed["counts"]["total"] == 6
    assert parsed["results"][0]["strength"] == "observed"


def test_observed_verdict_states_what_it_does_not_cover():
    """A satisfied-on-the-trace result says it is about the trace, not about all decisions."""
    report = check_conformance(FullCapabilitySUT(), load_pack("table7"))
    summary = report.results[0].evidence_summary
    assert "trace supplied" in summary
    assert "not in it" in summary
    assert "not a compliance guarantee" in report.limits
    assert "not evaluated" in report.limits


def test_a_declared_signal_absent_from_the_trace_is_a_violation():
    """Declaring a capability is not emitting it; the trace decides, and names the gap."""

    class SilentSUT(BaseSUT):
        def decisions(self):
            return [{"signal_a": "x", "signal_b": "y"}, {"signal_a": "x"}]

    req = _requirement(requires=("signal_a", "signal_b"))
    result = evaluate_requirement(req, SilentSUT({"signal_a", "signal_b"}))
    assert result.verdict == Verdict.VIOLATED
    assert result.strength == Strength.OBSERVED
    # Not a capability shortfall: the system declares it can emit signal_b.
    assert result.signals_missing == ()
    assert result.details["signals_absent_from_trace"] == ["signal_b"]
    assert "signal_b" in result.evidence_summary


@pytest.mark.parametrize("useless", [None, "", "   ", [], {}, ()])
def test_a_present_but_empty_signal_does_not_count_as_evidence(useless):
    """A key whose value is empty is not a reason given.

    `str([])` is "[]", so a truthiness check on the stringified value would pass an empty
    reason list as a reason — the exact case where a system looks compliant because it emitted
    the field name and nothing else.
    """

    class EmptySignalSUT(BaseSUT):
        def decisions(self):
            return [{"signal_a": useless}]

    req = _requirement(requires=("signal_a",))
    result = evaluate_requirement(req, EmptySignalSUT({"signal_a"}))
    assert result.verdict == Verdict.VIOLATED
    assert result.details["signals_absent_from_trace"] == ["signal_a"]


@pytest.mark.parametrize("real", [0, False, "x", ["r1"], {"k": "v"}])
def test_a_falsy_but_real_signal_value_counts(real):
    """Zero and False are values a system emitted, not absences."""

    class FalsySUT(BaseSUT):
        def decisions(self):
            return [{"signal_a": real}]

    result = evaluate_requirement(_requirement(requires=("signal_a",)), FalsySUT({"signal_a"}))
    assert result.verdict == Verdict.SATISFIED


def test_an_empty_trace_is_not_evidence():
    """No decisions observed means nothing was evaluated — not that the requirement holds."""
    result = evaluate_requirement(_requirement(), BaseSUT({"signal_a"}))
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert result.evaluated is False
    assert "empty" in result.evidence_summary

    report = ConformanceReport(pack_id="p", system_name="s", results=(result,))
    assert report.headline == "1 requirements · 1 not evaluated"
    assert report.counts["observed"] == 0
    assert report.to_dict()["results"][0]["strength"] is None
    assert "[NOT EVALUATED]" in report.render_text()


@pytest.mark.parametrize("formalism", ["temporal", "logical"])
def test_a_formalism_without_an_engine_is_not_evaluated(formalism):
    """Declaring the signals a temporal or logical property needs does not establish it.

    There is no monitor and no solver in this build. Checking such a requirement by looking
    for the signal names in the trace would report `satisfied` for a property nothing tested —
    the failure mode that would make every verdict in this tool unfalsifiable.
    """

    class TraceSUT(BaseSUT):
        def decisions(self):
            raise AssertionError("must not read the trace for a formalism no engine covers")

    req = _requirement(formalism=formalism, requires=("signal_a",))
    result = evaluate_requirement(req, TraceSUT({"signal_a"}))
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.strength is None
    assert formalism in result.evidence_summary

    report = check_conformance(TraceSUT({"signal_a"}), Pack("p", "P", "", (req,)))
    assert report.headline == "1 requirements · 1 not evaluated"


def test_result_cannot_claim_more_than_its_evidence():
    """The invariants that stop a nonsense result being constructed at all."""
    ok = {
        "requirement_id": "r1",
        "source_clause": "Doc Art. 1",
        "signals_required": ("a", "b"),
    }

    # An unattainable requirement is never satisfied: the system cannot discharge it as built.
    with pytest.raises(ValueError, match="cannot be reported satisfied"):
        RequirementResult(
            verdict=Verdict.SATISFIED,
            strength=Strength.UNATTAINABLE,
            signals_missing=("a",),
            **ok,
        )

    # Missing signals are exactly the unattainable finding — not decoration on a stronger one.
    with pytest.raises(ValueError, match="populated exactly when"):
        RequirementResult(
            verdict=Verdict.SATISFIED, strength=Strength.PROVED, signals_missing=("a",), **ok
        )
    with pytest.raises(ValueError, match="populated exactly when"):
        RequirementResult(
            verdict=Verdict.INCONCLUSIVE, strength=Strength.UNATTAINABLE, signals_missing=(), **ok
        )

    # A result with no evidence at all cannot carry a verdict.
    with pytest.raises(ValueError, match="no evidence strength"):
        RequirementResult(verdict=Verdict.VIOLATED, strength=None, **ok)

    # A shortfall must be in the signals the requirement actually asked for.
    with pytest.raises(ValueError, match="does not require"):
        RequirementResult(
            verdict=Verdict.INCONCLUSIVE,
            strength=Strength.UNATTAINABLE,
            signals_missing=("z",),
            **ok,
        )


def test_a_string_verdict_or_strength_is_parsed_not_trusted():
    """The invariants compare against enum members, so a raw string must not slip past them.

    `strength="unattainable"` is not `Strength.UNATTAINABLE`, so every guard above would have
    read False and constructed a result rendering as `[UNATTAINABLE] r1 (...): satisfied` —
    the exact overclaim this class exists to make unconstructible.
    """
    ok = {
        "requirement_id": "r1",
        "source_clause": "Doc Art. 1",
        "signals_required": ("a",),
    }

    with pytest.raises(ValueError, match="cannot be reported satisfied"):
        RequirementResult(verdict=Verdict.SATISFIED, strength="unattainable", **ok)

    res = RequirementResult(verdict="satisfied", strength="observed", **ok)
    assert res.verdict == Verdict.SATISFIED
    assert res.strength == Strength.OBSERVED
    assert res.to_dict()["strength"] == "observed"
    assert res == RequirementResult(verdict=Verdict.SATISFIED, strength=Strength.OBSERVED, **ok)

    # `None` stays legal: it marks "no engine here evaluated this", not a rung on the lattice.
    assert RequirementResult(verdict="inconclusive", strength=None, **ok).evaluated is False

    with pytest.raises(ValueError, match="Unknown strength"):
        RequirementResult(verdict=Verdict.INCONCLUSIVE, strength="vibes", **ok)
    with pytest.raises(ValueError, match="Unknown verdict"):
        RequirementResult(verdict="probably", strength=Strength.OBSERVED, **ok)


def test_result_rejects_a_bare_signal_string():
    """signals_required="reasons" would become seven one-character signals; refuse it."""
    with pytest.raises(TypeError, match="signals_required must be a sequence"):
        RequirementResult(
            requirement_id="r1",
            source_clause="Doc Art. 1",
            verdict=Verdict.INCONCLUSIVE,
            strength=None,
            signals_required="reasons",
        )
    with pytest.raises(TypeError, match="signals_missing must be a sequence"):
        RequirementResult(
            requirement_id="r1",
            source_clause="Doc Art. 1",
            verdict=Verdict.INCONCLUSIVE,
            strength=Strength.UNATTAINABLE,
            signals_required=("a",),
            signals_missing="a",
        )
    # A list of names is fine and arrives as a tuple.
    res = RequirementResult(
        requirement_id="r1",
        source_clause="Doc Art. 1",
        verdict=Verdict.INCONCLUSIVE,
        strength=None,
        signals_required=["a", "b"],
    )
    assert res.signals_required == ("a", "b")


def test_a_trace_of_the_wrong_shape_names_the_system():
    """One record instead of a list of records iterates its keys; say which system did it."""

    class OneRecordSUT(BaseSUT):
        def decisions(self):
            return {"signal_a": "value"}

    sut = OneRecordSUT({"signal_a"})
    with pytest.raises(TypeError, match=r"OneRecordSUT\.decisions\(\).*got str"):
        evaluate_requirement(_requirement(), sut)
    with pytest.raises(TypeError, match="each a mapping of signal name to value"):
        check_conformance(sut, Pack("p", "P", "", (_requirement(),)))


def test_headline_and_counts_never_disagree():
    """The headline is rendered from the counts, so a reader and a machine see one story.

    Uses a system that gives no reasons but does keep a trace — the realistic black box, where
    part of the pack is unattainable and the rest is checkable, so both halves of the headline
    have to be right at once.
    """

    report = check_conformance(NoReasonsSUT(), load_pack("table7"), system_name="BlackBox")
    counts = report.counts

    assert counts["total"] == 6
    assert counts["unattainable"] == 2
    assert counts["observed"] == 4
    assert counts["total"] == sum(
        counts[k]
        for k in ("proved", "probed", "observed", "violated", "inconclusive",
                  "not_evaluated", "unattainable")
    )
    assert report.headline == "6 requirements · 4 observed · 2 unattainable"
    assert json.loads(report.to_json())["counts"] == counts
