"""Holds `docs/findings-nesyarena.md` to the figures its sources produce.

What this module is for:
  `docs/findings-nesyarena.md` is hand-written prose, but it quotes counts that live in
  generated artefacts — `docs/nesyarena-conformance-report.md`, `DECLARED_SIGNALS` /
  `UNDECLARED_SIGNALS` in `docs/build_nesyarena_report.py`, and the per-formalism requirement
  census of the shipped packs. Nothing held the prose to those sources, so every pack change
  sent the figures stale silently: three separate fix rounds during one earlier task, and two
  stale figures that predated even those. This test re-derives every figure the prose quotes
  from the sources the prose names and fails when the prose disagrees, naming the figure and
  what to regenerate.

  Route chosen: pin with a test, not derive at build time. The findings document is an
  authorial account, not a transcript: its figures sit inside narrative and historical claims
  that a builder cannot compose without moving the writing into code, and a builder that could
  would be a second renderer of the same report. The repository's own pattern for hand-written
  documents is a claim-pinning test (`test_docs_semantics.py`), while generated transcripts get
  byte-for-byte pins (`test_nesyarena_conformance.py` already pins the report itself).

What a reader must not break:
  - Derive every figure from the same sources the prose names: the builder module (loaded by
    path, exactly as `test_nesyarena_conformance.py` does), the packs it loads, and the run it
    drives. A figure copied into this test from the document would pin the document to itself
    and pass while both drifted together.
  - The failure messages name the figure and what to regenerate: run
    `python docs/build_nesyarena_report.py` when the number lives in the report, re-derive from
    the pack when the census moved, and update the prose in the same commit.
  - Historical claims about earlier runs (11 requirements at the first run, 8 signals then, the
    pre-domain-gate ECOA column of 8 satisfied / 2 violated / 5 unattainable, the pre-gate
    verdicts column of finding 1) are not derivable from the current sources and are
    deliberately not pinned here; they were verified against the committed reports of those runs
    in the PR that introduced this test, and the document itself says which column is which run.
"""

from __future__ import annotations

import importlib.util
import re
from collections import Counter
from pathlib import Path

import nesyarena

from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "docs" / "findings-nesyarena.md"

DEVIATION_DUTY = "gdpr_recital71_error_risk_minimised"
MEANINGFUL_EXPLANATION = "gdpr_recital71_meaningful_explanation"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_nesyarena_report", ROOT / "docs" / "build_nesyarena_report.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


def _document() -> str:
    assert FINDINGS.is_file(), f"{FINDINGS} does not exist"
    return FINDINGS.read_text(encoding="utf-8")


def _prose() -> str:
    """The document with line wrapping collapsed, for prose figure pins.

    The document wraps at roughly column 100, so a figure split across two lines would
    otherwise fail a pin that the prose states correctly. Collapsing whitespace pins the
    figure, not the author's line breaks.
    """
    return re.sub(r"\s+", " ", _document())


def _requirements() -> dict[str, object]:
    """Every requirement of the three packs the builder loads, keyed by id."""
    reqs = {}
    for pack_name in builder.PACKS:
        for requirement in load_pack(pack_name).requirements:
            reqs[requirement.id] = requirement
    return reqs


def _battery() -> tuple[list, list, dict[str, dict[str, object]]]:
    """The battery the builder drives, and every result it produces, per system per duty.

    This is the derivation ground for every figure below. Nothing here is read from any
    document; `check_conformance` is the same call the builder's `render()` makes, with the
    same `system_scope=None` and `system_domains=None`.
    """
    instances = builder.battery()
    systems = [builder.NesyArenaSUT(prov, instances) for prov in nesyarena.suts.registry()]
    per_system: dict[str, dict[str, object]] = {}
    for sut in systems:
        per_system[sut.name] = {}
        for pack_name in builder.PACKS:
            report = check_conformance(
                sut,
                load_pack(pack_name),
                system_name=f"nesyarena:{sut.name}",
                system_scope=None,
                system_domains=None,
            )
            for result in report.results:
                per_system[sut.name][result.requirement_id] = result
    return systems, instances, per_system


SYSTEMS, INSTANCES, PER_SYSTEM = _battery()
RESULTS = [res for by_sys in PER_SYSTEM.values() for res in by_sys.values()]
REQS = _requirements()

_NUM_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
}


def _word(n: int) -> str:
    return _NUM_WORDS[n]


def _per_requirement_outcomes() -> dict[str, Counter]:
    """Verdict name -> count across the five systems, per requirement."""
    out: dict[str, Counter] = {}
    for by_sys in PER_SYSTEM.values():
        for rid, result in by_sys.items():
            out.setdefault(rid, Counter())[result.verdict.name] += 1
    return out


def _inference_stats(sut):
    """(max abs deviation, deviating count, differing-from-exact count, margin-exceeding count)."""
    rows = sut.rows()
    max_dev = max(abs(r["error"]) for r in rows)
    deviating = sum(1 for r in rows if r["error"] != 0.0)
    exact = SYSTEMS[0]
    differing = sum(
        1
        for r1, r2 in zip(rows, exact.rows(), strict=True)
        if (r1["value"] >= builder.APPROVE_THRESHOLD) != (r2["value"] >= builder.APPROVE_THRESHOLD)
    )
    exceeding = sum(
        1 for r in rows if abs(r["error"]) > abs(r["value"] - builder.APPROVE_THRESHOLD)
    )
    return max_dev, deviating, differing, exceeding


def _breach_indices(sut) -> tuple[list[int], list[int]]:
    """Indices where the declared deviation exceeds the margin, and where the decision flips."""
    rows = sut.rows()
    exact = SYSTEMS[0]
    exceed = [
        i for i, r in enumerate(rows)
        if abs(r["error"]) > abs(r["value"] - builder.APPROVE_THRESHOLD)
    ]
    flip = [
        i for i, (r1, r2) in enumerate(zip(rows, exact.rows(), strict=True))
        if (r1["value"] >= builder.APPROVE_THRESHOLD) != (r2["value"] >= builder.APPROVE_THRESHOLD)
    ]
    return exceed, flip


def _table_rows(block: str) -> dict[str, int]:
    """A markdown table's label -> count rows, as the document prints them."""
    rows = {}
    for line in block.splitlines():
        match = re.fullmatch(r"\| (.+) \| (\d+) \|", line)
        if match:
            rows[match.group(1)] = int(match.group(2))
    return rows


def _headline_table(document: str) -> dict[str, int]:
    match = re.search(r"## The headline\n(.*?)\n## ", document, re.S)
    assert match, "docs/findings-nesyarena.md has no '## The headline' section to pin"
    return _table_rows(match.group(1))


def _finding_table(document: str, header: str) -> dict[str, list[str]]:
    """A finding's table keyed by system name, cells stripped of markup."""
    match = re.search(re.escape(header) + r"[^\n]*\n\|\s*---.*?\n(.*?)\n\n", document, re.S)
    assert match, f"docs/findings-nesyarena.md has no table headed {header!r}"
    out = {}
    for line in match.group(1).splitlines():
        cells = [c.strip().strip("`").replace("**", "") for c in line.split("|")]
        out[cells[1]] = cells[2:]
    return out


def _unattainable_paragraph(document: str) -> str:
    """The paragraph that names the duties which came back `unattainable`."""
    for para in re.split(r"\n\s*\n", document):
        if "came back `unattainable` for all five systems" in para:
            return para
    raise AssertionError(
        "docs/findings-nesyarena.md no longer says anything 'came back `unattainable` for all "
        "five systems' — the account of the unattainable column is gone"
    )


def _unattainable_sentence(document: str) -> str:
    """The sentence naming the duties that came back `unattainable`."""
    match = re.search(r"came back `unattainable` for all five systems[^.]*\.", document)
    assert match, (
        "docs/findings-nesyarena.md no longer says anything 'came back `unattainable` for all "
        "five systems' — the account of the unattainable column is gone"
    )
    return match.group(0)


def _ecoa_with_domain() -> dict[str, Counter]:
    """The ECOA outcomes of a run that declared `consumer-credit`, derived by running it."""
    out: dict[str, Counter] = {}
    for sut in SYSTEMS:
        report = check_conformance(
            sut,
            load_pack("ecoa"),
            system_name=f"nesyarena:{sut.name}",
            system_scope=None,
            system_domains=["consumer-credit"],
        )
        for result in report.results:
            out.setdefault(result.requirement_id, Counter())[result.verdict.name] += 1
    return out


def _unattainable_ids() -> set[str]:
    return {
        rid for rid, outcomes in _per_requirement_outcomes().items()
        if outcomes["INCONCLUSIVE"]
    }


def _ecoa_ids() -> set[str]:
    return {rid for rid in REQS if rid.startswith("ecoa_")}


def _eu_ids() -> set[str]:
    return {rid for rid in REQS if rid.startswith("eu_ai_act_")}


def _results_for(ids: set[str]) -> list:
    return [res for by_sys in PER_SYSTEM.values() for rid, res in by_sys.items() if rid in ids]


# ---------------------------------------------------------------------------
# The headline
# ---------------------------------------------------------------------------


def test_headline_scale():
    """'65 results — 5 systems × 13 requirements' is the product of the real battery."""
    document = _document()
    assert len(REQS) == 13, f"the three packs now hold {len(REQS)} requirements, not 13"
    scale = f"{len(SYSTEMS)} systems × {len(REQS)} requirements"
    assert scale in document, (
        "docs/findings-nesyarena.md's headline scale is stale: the run is "
        f"{scale} across the three packs, not what the document says. "
        "Update the prose (regenerate docs/nesyarena-conformance-report.md first if the "
        "pack census moved)."
    )
    assert f"{len(SYSTEMS) * len(REQS)} results" in document, (
        "docs/findings-nesyarena.md's headline total is stale: the run produces "
        f"{len(SYSTEMS) * len(REQS)} results ({len(SYSTEMS)} systems × {len(REQS)} "
        "requirements), not what the document says."
    )
    assert len(RESULTS) == len(SYSTEMS) * len(REQS), "the run's own result count disagrees"
    assert f"{len(INSTANCES)} ground programs" in document, (
        "docs/findings-nesyarena.md's instance count is stale: the battery holds "
        f"{len(INSTANCES)} ground programs."
    )


def test_headline_outcome_table():
    """The outcome table equals what this run actually produced, row for row."""
    outcomes = _per_requirement_outcomes()
    satisfied = sum(c["SATISFIED"] for c in outcomes.values())
    violated = sum(c["VIOLATED"] for c in outcomes.values())
    unattainable = sum(c["INCONCLUSIVE"] for c in outcomes.values())
    na_class = sum(
        1
        for by_sys in PER_SYSTEM.values()
        for rid, result in by_sys.items()
        if result.verdict is Verdict.NOT_APPLICABLE and REQS[rid].scope
    )
    na_domain = sum(
        1
        for by_sys in PER_SYSTEM.values()
        for rid, result in by_sys.items()
        if result.verdict is Verdict.NOT_APPLICABLE and REQS[rid].domains
    )
    at_strength = Counter(
        result.strength.value for result in RESULTS if result.strength is not None
    )
    expected = {
        "satisfied, at strength `observed`": satisfied,
        "violated, at strength `observed`": violated,
        "inconclusive, `unattainable`": unattainable,
        "not applicable (no class declared)": na_class,
        "not applicable (no decision domain declared)": na_domain,
        "satisfied at `probed`": at_strength.get("probed", 0),
        "satisfied at `proved`": at_strength.get("proved", 0),
    }
    assert _headline_table(_document()) == expected, (
        "docs/findings-nesyarena.md's headline outcome table disagrees with the run: the run "
        f"produces {expected}. Update the table (regenerate "
        "docs/nesyarena-conformance-report.md with `python docs/build_nesyarena_report.py` "
        "first if the verdicts moved)."
    )


# ---------------------------------------------------------------------------
# The violation
# ---------------------------------------------------------------------------


def test_the_no_reason_violation_counterexamples():
    """add-mult's four no-reason decisions are the run's own, instances and indices included."""
    prose = _prose()
    am = next(sut for sut in SYSTEMS if "add-mult" in sut.name)
    rows = am.rows()
    empty = [i for i, r in enumerate(rows) if not r["attribution"]]
    assert len(empty) == 4, f"add-mult(clamped) now has {len(empty)} no-reason decisions, not 4"
    labels = [rows[i]["label"] for i in empty]
    assert labels == ["G1-P4-L2-c0", "G1-P4-L2-c1", "G1-P4-L3-c0", "G1-P4-L3-c1"]
    assert f"4 of its {len(INSTANCES)} decisions carry no reason" in prose, (
        "docs/findings-nesyarena.md's missing-reason figure is stale: the run reports 4 of "
        f"{len(INSTANCES)} decisions carrying no reason for add-mult(clamped), not what the "
        "document says."
    )
    for label in labels:
        assert f"`{label}`" in prose, (
            f"docs/findings-nesyarena.md no longer names counterexample instance `{label}`"
        )
    assert f"record indices 8–{11}" in prose, (
        "docs/findings-nesyarena.md's record indices for the counterexamples are stale: the "
        "run names indices 8–11, not what the document says."
    )
    # the report, which this test's sibling already pins byte-for-byte, says the same thing
    assert "4 of 16 decisions carry no artifact_logs_reason_explanation" in builder.render()


def test_add_mult_deviation_figures():
    """add-mult deviates on 8 of 16 instances by up to +0.347356 and never flips a decision."""
    prose = _prose()
    am = next(sut for sut in SYSTEMS if "add-mult" in sut.name)
    max_dev, deviating, differing, _ = _inference_stats(am)
    assert max_dev > 0.0 and differing == 0
    assert f"{deviating} of {len(INSTANCES)} instances, by as much as `+{max_dev:.6f}`" in prose, (
        "docs/findings-nesyarena.md's add-mult deviation figure is stale: the run measures "
        f"deviation on {deviating} of {len(INSTANCES)} instances by up to +{max_dev:.6f}."
    )
    assert f"same approve/deny as `exact-wmc` on all {len(INSTANCES)}" in prose, (
        "docs/findings-nesyarena.md's claim that add-mult lands on the same decisions as "
        "exact-wmc is stale: it differs on "
        f"{differing} of {len(INSTANCES)} instances."
    )
    # the two ECOA violations it used to carry are now not applicable on the domain gate
    assert "those two are now not applicable" in prose
    for rid in (
        "ecoa_reg_b_1002_9_a_2_written_statement",
        "ecoa_reg_b_1002_9_b_2_specific_reasons",
    ):
        outcomes = _per_requirement_outcomes()[rid]
        assert outcomes == Counter({"NOT_APPLICABLE": 5}), (
            f"{rid} is no longer uniformly not applicable, but the document says it is"
        )


# ---------------------------------------------------------------------------
# Finding 1
# ---------------------------------------------------------------------------


def test_finding_1_measured_inference_table():
    """Finding 1's deviation and decision-difference figures are the run's, not the memory's."""
    table = _finding_table(_document(), "| system | max abs. deviation")
    assert set(table) == {sut.name for sut in SYSTEMS}, (
        "docs/findings-nesyarena.md's finding-1 table names systems the run does not, or "
        "omits systems it does"
    )
    for sut in SYSTEMS:
        max_dev, deviating, differing, _ = _inference_stats(sut)
        assert table[sut.name][0] == f"{max_dev:.6f}", (
            "docs/findings-nesyarena.md's max deviation for "
            f"{sut.name} is stale: the run measures {max_dev:.6f}."
        )
        assert table[sut.name][1] == f"{deviating}/{len(INSTANCES)}", (
            "docs/findings-nesyarena.md's deviating-instance count for "
            f"{sut.name} is stale: the run reports {deviating}/{len(INSTANCES)}."
        )
        assert table[sut.name][2] == f"{differing}/{len(INSTANCES)}", (
            "docs/findings-nesyarena.md's decision-difference count for "
            f"{sut.name} is stale: the run reports {differing}/{len(INSTANCES)}."
        )


def test_finding_1_half_the_battery():
    """'Half the battery' is the top-1 count and it really is half."""
    prose = _prose()
    top1 = next(sut for sut in SYSTEMS if "top-1" in sut.name)
    _, _, differing, _ = _inference_stats(top1)
    assert differing == len(INSTANCES) // 2, (
        f"top-1-proofs now differs on {differing} of {len(INSTANCES)} instances, not half"
    )
    assert "**half the battery**" in prose


def test_finding_1_min_max_prose():
    """min-max deviates on every instance, flips four decisions, and its breaches contain them."""
    prose = _prose()
    mm = next(sut for sut in SYSTEMS if "min-max" in sut.name)
    max_dev, deviating, differing, _ = _inference_stats(mm)
    assert deviating == len(INSTANCES) and differing == 4
    exceed, flip = _breach_indices(mm)
    assert set(flip) <= set(exceed), (
        "min-max-prob's decision flips are no longer a subset of its margin breaches"
    )
    assert f"deviates on every single instance and flips {_word(differing)} decisions" in prose
    assert (
        f"breaches on {_word(len(exceed))} decisions where the {_word(len(flip))} it actually "
        "flips are a subset" in prose
    ), (
        "docs/findings-nesyarena.md's breach/subset sentence is stale: the run breaches on "
        f"{len(exceed)} decisions where the {len(flip)} flips are a subset."
    )


def test_finding_1_deviation_duty_table():
    """The deviation-duty table matches a real run of the duty, verdicts included."""
    table = _finding_table(_document(), "| system | max declared deviation")
    assert set(table) == {sut.name for sut in SYSTEMS}
    for sut in SYSTEMS:
        max_dev, _, _, exceeding = _inference_stats(sut)
        verdict = PER_SYSTEM[sut.name][DEVIATION_DUTY].verdict.name.lower()
        assert table[sut.name][0] == f"{max_dev:.6f}", (
            "docs/findings-nesyarena.md's max declared deviation for "
            f"{sut.name} is stale: the run measures {max_dev:.6f}."
        )
        assert table[sut.name][1] == f"{exceeding}/{len(INSTANCES)}", (
            "docs/findings-nesyarena.md's margin-exceeding count for "
            f"{sut.name} is stale: the run reports {exceeding}/{len(INSTANCES)}."
        )
        assert table[sut.name][2] == verdict, (
            "docs/findings-nesyarena.md's verdict for "
            f"{sut.name} on {DEVIATION_DUTY} is stale: the run reports {verdict}."
        )


# ---------------------------------------------------------------------------
# Finding 2
# ---------------------------------------------------------------------------


def test_finding_2_formalism_census():
    """The per-formalism census matches the packs, and so do the id lists."""
    prose = _prose()
    counts = Counter(req.formalism for req in REQS.values())
    assert dict(counts) == {"record": 7, "logical": 3, "temporal": 3}, (
        f"the packs now hold {dict(counts)} requirements by formalism; the document's census "
        "is stale — update docs/findings-nesyarena.md in the commit that moved the packs"
    )
    assert f"{_word(counts['logical'])} `logical` requirements" in prose
    assert f"{_word(counts['temporal'])} `temporal` requirements" in prose
    assert f"the {_word(counts['record'])} `record` duties" in prose
    for formalism in ("logical", "temporal"):
        match = re.search(
            rf"{_word(counts[formalism])} `{formalism}` requirements\s*\((.*?)\)",
            prose,
        )
        assert match, (
            f"docs/findings-nesyarena.md no longer lists the {formalism} requirements in "
            "parentheses after the census sentence"
        )
        listed = set(re.findall(r"`([a-z0-9_]+)`", match.group(1)))
        derived = {rid for rid, req in REQS.items() if req.formalism == formalism}
        assert listed == derived, (
            f"docs/findings-nesyarena.md's {formalism} requirement list is stale: the packs "
            f"hold {sorted(derived)}, the document lists {sorted(listed)}"
        )


def test_finding_2_unattainable_pair():
    """The sentence naming the unattainable pair names exactly the run's pair."""
    prose = _prose()
    derived = _unattainable_ids()
    assert derived == {
        "gdpr_art22_1_no_prohibited_decision_for_any_input",
        "gdpr_art22_1_automated_decision_prohibition",
    }, (
        f"the unattainable duties are no longer that pair but {sorted(derived)} — re-derive "
        "finding 2 against the run before updating the prose"
    )
    sentence = _unattainable_sentence(prose)
    sentence_ids = {token for token in re.findall(r"`([a-z0-9_]+)`", sentence) if token in REQS}
    assert sentence_ids == derived, (
        "docs/findings-nesyarena.md's account of which duties came back `unattainable` is "
        f"stale: it names {sorted(sentence_ids)}, the run reports {sorted(derived)}"
    )
    # the ECOA timing duty is not unattainable in this run, and the document says so
    timing = _per_requirement_outcomes()["ecoa_reg_b_1002_9_a_1_timing_of_notice"]
    assert timing == Counter({"NOT_APPLICABLE": 5})
    assert "is not `unattainable` in this run at all" in prose


def test_finding_2_why_unattainable():
    """The six-signal and missing-signal reasons are the packs' own gates."""
    prose = _prose()
    logical = REQS["gdpr_art22_1_no_prohibited_decision_for_any_input"]
    assert len(logical.requires) == 6, (
        f"gdpr_art22_1_no_prohibited_decision_for_any_input now requires "
        f"{len(logical.requires)} signals, not 6"
    )
    assert f"needs {_word(len(logical.requires))} signals" in prose, (
        "docs/findings-nesyarena.md's six-signal figure is stale: the logical duty requires "
        f"{len(logical.requires)} signals."
    )
    record = REQS["gdpr_art22_1_automated_decision_prohibition"]
    missing = set(record.requires) - set(builder.DECLARED_SIGNALS)
    para = _unattainable_paragraph(prose)
    for signal in sorted(missing):
        assert f"`{signal}`" in para, (
            f"docs/findings-nesyarena.md's account of why {record.id} is unattainable no "
            f"longer names the missing signal `{signal}`"
        )


def test_finding_2_top_rungs_never_ran():
    """The re-derived conclusion: Z3 and the replay search never ran, and the reasons hold."""
    prose = _prose()
    assert "the Z3 proved engine and the replay probed engine never ran" in prose
    at_top = [r for r in RESULTS if r.strength in (Strength.PROBED, Strength.PROVED)]
    assert not at_top, (
        f"the run now produces {len(at_top)} probed/proved results — finding 2's central "
        "claim is false and must be re-derived, not just re-pinned"
    )
    # no logical duty reaches an engine: each is unattainable or not applicable
    for rid, req in REQS.items():
        if req.formalism == "logical":
            outcomes = set(_per_requirement_outcomes()[rid])
            assert outcomes <= {"INCONCLUSIVE", "NOT_APPLICABLE"}, (
                f"{rid} is now checkable ({outcomes}) — the Z3 engine can run, and finding 2 "
                "must be re-derived"
            )
    # even a checkable state duty could not exceed observed: `BaseSUT.logic()` is a stub
    # that returns None (nothing to reason over) and `decide` is not part of the adapter
    for sut in SYSTEMS:
        assert sut.logic() is None, (
            f"{sut.name} now exposes real logic(); finding 2's ceiling claim is false"
        )
        assert not callable(getattr(sut, "decide", None)), (
            f"{sut.name} now exposes decide(); finding 2's ceiling claim is false"
        )
    assert (
        "no `decide()` to replay a perturbed input through and no `logic()` to reason over"
        in prose
    )
    assert "Zero results at `probed`, zero at `proved`" in prose


def test_finding_2_record_duty_split():
    """Of the seven record duties: four scope-gated, one unattainable, two observed."""
    record_ids = {rid for rid, req in REQS.items() if req.formalism == "record"}
    assert len(record_ids) == 7
    outcomes = _per_requirement_outcomes()
    na_scope = {rid for rid in record_ids if set(outcomes[rid]) == {"NOT_APPLICABLE"}}
    unattainable = {rid for rid in record_ids if outcomes[rid]["INCONCLUSIVE"]}
    observed = {
        rid for rid in record_ids if outcomes[rid]["SATISFIED"] or outcomes[rid]["VIOLATED"]
    }
    assert len(na_scope) == 4 and unattainable == {"gdpr_art22_1_automated_decision_prohibition"}
    assert observed == {
        "gdpr_art22_3_safeguards_human_intervention",
        MEANINGFUL_EXPLANATION,
    }
    prose = _prose()
    assert f"{_word(len(na_scope))} are the AI Act's" in prose
    assert f"one — `{sorted(unattainable)[0]}` — reaches no engine at all" in prose
    two = " and ".join(f"`{rid}`" for rid in sorted(observed))
    assert two in prose and "stay `observed`" in prose


# ---------------------------------------------------------------------------
# Finding 3
# ---------------------------------------------------------------------------


def test_finding_3_ecoa_domain_gate():
    """All twenty ECOA results are not applicable, and the document's split is the run's."""
    prose = _prose()
    ecoa_results = _results_for(_ecoa_ids())
    assert len(ecoa_results) == 20, (
        f"the ECOA pack now produces {len(ecoa_results)} results, not 20"
    )
    assert all(r.verdict is Verdict.NOT_APPLICABLE for r in ecoa_results), (
        "some ECOA result is no longer not applicable — finding 3's gate claim is stale"
    )
    assert "all twenty ECOA results are now `not_applicable`" in prose
    assert f"{len(_ecoa_ids()) * len(SYSTEMS)} results rather than 15" in prose


def test_finding_3_consumer_credit_counterfactual():
    """A consumer-credit run leaves two duties unattainable and two checkable, derived."""
    with_domain = _ecoa_with_domain()
    unattainable = {
        rid for rid, c in with_domain.items() if c["INCONCLUSIVE"]
    }
    checkable = {rid for rid, c in with_domain.items() if c["SATISFIED"] or c["VIOLATED"]}
    assert unattainable == {
        "ecoa_reg_b_1002_9_a_1_timing_of_notice",
        "ecoa_reg_b_1002_9_b_2_principal_reasons_complete",
    }, (
        "a consumer-credit run now leaves a different pair unattainable "
        f"({sorted(unattainable)}) — finding 3's counterfactual must be re-derived"
    )
    assert checkable == {
        "ecoa_reg_b_1002_9_a_2_written_statement",
        "ecoa_reg_b_1002_9_b_2_specific_reasons",
    }
    prose = _prose()
    assert f"{_word(len(unattainable))} of the four duties would stay unattainable" in prose
    assert "the written-statement and specific-reasons duties — would become checkable" in prose


# ---------------------------------------------------------------------------
# Findings 4 and 6
# ---------------------------------------------------------------------------


def test_finding_4_ai_act_not_applicable():
    """Every AI Act requirement for every system is not applicable, 20 results in all."""
    prose = _prose()
    eu_results = _results_for(_eu_ids())
    assert len(eu_results) == 20, (
        f"the EU AI Act pack now produces {len(eu_results)} results, not 20"
    )
    assert all(r.verdict is Verdict.NOT_APPLICABLE for r in eu_results)
    assert f"{len(eu_results)} of the 65 results" in prose
    assert "every AI Act requirement for every system — are `not_applicable`" in prose


def test_finding_6_alternative_reason_rule():
    """The alternative-rule counterfactual follows from the run's own violations."""
    violated = [
        (rid, res)
        for by_sys in PER_SYSTEM.values()
        for rid, res in by_sys.items()
        if res.verdict is Verdict.VIOLATED
    ]
    reason_rule_dependent = [t for t in violated if t[0] == MEANINGFUL_EXPLANATION]
    remaining = len(violated) - len(reason_rule_dependent)
    not_applicable = sum(1 for r in RESULTS if r.verdict is Verdict.NOT_APPLICABLE)
    non_violations = len(RESULTS) - not_applicable - remaining
    assert remaining == 2 and non_violations == 23, (
        "the alternative-reason-rule counterfactual is stale: the run now leaves "
        f"{remaining} violations and {non_violations} non-violations"
    )
    assert (
        f"**{_word(remaining)} remaining violations** and {non_violations} satisfied results"
        in _prose()
    ), (
        "docs/findings-nesyarena.md's alternative-rule figures are stale: re-deriving from "
        f"the run gives {_word(remaining)} remaining violations and {non_violations} "
        "satisfied results."
    )


# ---------------------------------------------------------------------------
# The signal census
# ---------------------------------------------------------------------------


def test_signal_census():
    """The declared/undeclared split accounts for every signal the packs read."""
    prose = _prose()
    declared = set(builder.DECLARED_SIGNALS)
    undeclared = {s for s, _ in builder.UNDECLARED_SIGNALS}
    assert declared.isdisjoint(undeclared), "a signal cannot be both declared and undeclared"
    pack_signals = {s for req in REQS.values() for s in req.requires}
    assert pack_signals <= declared | undeclared, (
        "the packs read signals the builder's census does not account for: "
        f"{sorted(pack_signals - (declared | undeclared))} — update DECLARED_SIGNALS or "
        "UNDECLARED_SIGNALS in docs/build_nesyarena_report.py"
    )
    # exactly one census signal gates no duty: the ungated branch of the 1002.9(a)(2) either/or
    ungated = (declared | undeclared) - pack_signals
    assert ungated == {"artifact_logs_right_to_reasons_disclosure"}, (
        f"the census no longer accounts for the same ungated signals: {sorted(ungated)}"
    )
    assert f"{_word(len(declared)).capitalize()} signals" in prose, (
        f"docs/findings-nesyarena.md's declared-signal count is stale: the builder declares "
        f"{len(declared)} signals."
    )
    assert f"{_word(len(undeclared)).capitalize()} further pack signals" in prose, (
        f"docs/findings-nesyarena.md's undeclared-signal count is stale: the builder lists "
        f"{len(undeclared)} undeclared signals."
    )


def test_six_article_22_signals():
    """The logical duty's six signals are exactly the six Article 22 signals left undeclared."""
    prose = _prose()
    logical = REQS["gdpr_art22_1_no_prohibited_decision_for_any_input"]
    undeclared = {s for s, _ in builder.UNDECLARED_SIGNALS}
    article22 = set(logical.requires) & undeclared
    assert article22 == set(logical.requires), (
        "gdpr_art22_1_no_prohibited_decision_for_any_input now requires a signal the system "
        "could declare — the account of why it is unattainable must be re-derived"
    )
    assert len(article22) == 6
    assert f"{_word(len(article22))} Article 22 signals" in prose
