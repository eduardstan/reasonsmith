"""The `--json` record carries what the report holds — the three additive keys.

What this module is for:
  `tests/test_json_schema_version.py` pins the *shape* of the `--json` envelope to
  `JSON_SCHEMA_VERSION`. This module holds the *content* of the keys that the envelope grew
  without a version bump, all additive: `basis`, `verbatim_text` and
  `details.certificate`. A schema-version pin proves a key exists; it does not prove the key
  carries what the report object holds, and it does not prove absence is meaningful.

What a reader must not break:
  - `verbatim_text` is a quotation from the law, carried through **unchanged**. The pack's copy is
    the authority and this is a passthrough; a test that reflows, truncates or normalises it would
    be a test of a rendering this record does not do.
  - `details.certificate` is present only where a certificate actually exists. A result with no
    certificate has **no** `certificate` key at all, never an empty object — absence is the
    meaningful state, and an empty record would read "certified nothing" where the truth is
    "nothing was certified".
  - `status` is the `ReasonVerdict.status` verbatim — `live`, `deleted`, `unseparable`,
    `inconclusive`, `undetermined` — never a boolean and never two collapsed states. `deleted` is
    a finding and `unseparable` is a guess about the same reason; a record that cannot tell them
    apart will show the second as the first.
"""

from __future__ import annotations

import json

from nesyarena.ir import Atom, GroundProgram, Rule

from reasonsmith import demo
from reasonsmith.certificate import certify
from reasonsmith.engines.certificate import CERTIFICATE_KEY, _certificate_record
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

#: The reason-adequacy duty the certificate engine settles; only its result carries certificates.
ADEQUACY = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"


def _run() -> dict:
    """One real run — the demonstration system against the ECOA pack — as the CLI emits it."""
    return check_conformance(demo.deployed_credit_system(), load_pack("ecoa")).to_dict()


# ------------------------------------------------------ added, additive, through the report ----

def test_every_result_carries_basis_and_verbatim_text_from_the_report_object():
    """Add 1 and Add 2: both keys present on every result, equal to what each result holds.

    Neither key is recomputed at serialisation time and neither is invented where the report has
    none: the JSON is the result object's own fields carried through.
    """
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    payload = report.to_dict()
    for r in report.results:
        record = next(x for x in payload["results"] if x["requirement_id"] == r.requirement_id)
        assert record["basis"] == r.basis.value
        assert record["verbatim_text"] == r.verbatim_text


def test_verbatim_text_is_byte_identical_to_the_packs_string():
    """The quotation is a passthrough: byte-identical to the pack's copy, never reflowed."""
    payload = _run()
    pack = load_pack("ecoa")
    by_id = {r["requirement_id"]: r for r in payload["results"]}
    for req in pack.requirements:
        got = by_id[req.id]["verbatim_text"]
        assert isinstance(got, str)
        # Not equal-normalised: byte-identical, so a stricter (or Unicode-folded) consumer sees
        # exactly the words Section 12 CFR 1002.9 actually speaks.
        assert got.encode("utf-8") == req.verbatim_text.encode("utf-8")


def test_a_result_with_no_certificate_has_no_certificate_key():
    """Absence is meaningful: no certificate duty, no `details.certificate`, never an empty list."""
    payload = _run()
    for result in payload["results"]:
        if result["requirement_id"] == ADEQUACY:
            continue
        assert CERTIFICATE_KEY not in result["details"]


# ----------------------------------------------------------- the deletion certificates ----


def test_a_failed_certificate_is_a_reported_finding_beside_the_verdict():
    payload = _run()
    result = next(r for r in payload["results"] if r["requirement_id"] == ADEQUACY)
    assert result["verdict"] == "violated"
    assert result["findings"] == [
        {"type": "certificate", "verdict": "FAIL", "decision_index": 1}
    ]


def test_a_certificate_result_carries_the_full_reason_record():
    """Add 3: the verdict names the reasons, and the details name the reasons' verdicts.

    The headline finding of the project — one stated reason, five found by exact inference, four
    deleted — must be rebuildable from the record alone: for the violated decision the certificate
    carries four `deleted` and one `live`, each with its own score and drops.
    """
    payload = _run()
    result = next(r for r in payload["results"] if r["requirement_id"] == ADEQUACY)
    records = result["details"][CERTIFICATE_KEY]

    assert len(records) == 2  # two decisions certified, matching the summary's count
    # The demonstrated case: decision #1 is the one with the four deleted reasons.
    breached = next(rec for rec in records if rec["decision_index"] == 1)
    statuses = [reason["status"] for reason in breached["reasons"]]
    assert statuses.count("deleted") == 4 and statuses.count("live") == 1
    for reason in breached["reasons"]:
        assert set(reason) >= {"label", "status", "score", "exact_drop", "engine_drop", "detail"}


def test_the_certificate_record_matches_the_certificates_the_report_holds():
    """The machine record is the report's own measurement, carried unchanged, and JSON-safe."""
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    result = next(r for r in report.results if r.requirement_id == ADEQUACY)
    assert result.details[CERTIFICATE_KEY] == result.to_dict()["details"][CERTIFICATE_KEY]


def test_an_unseparable_reason_keeps_its_status_through_the_record_and_json():
    """The unseparable state is a third thing, and the JSON must keep it that way.

    The engine answers a constant, so deleting any fact leaves its answer where it was and the
    joint search resolves nothing; `{a, b}` shares every fact with a sibling, so it is the
    unseparable reason. That state must reach a JSON consumer verbatim — not a boolean, not
    folded into two states, and never promoted to `deleted`.
    """

    class _ConstantEngine:
        supports_grad = False
        name = "reference:constant-engine"
        claimed_semantics = "distribution semantics"

        def infer(self, program, base, queries):
            return {q: 0.5 for q in queries}

    q, a, b, c, d = Atom("q"), Atom("a"), Atom("b"), Atom("c"), Atom("d")
    program = GroundProgram((Rule(q, (a, b)), Rule(q, (a, c)), Rule(q, (b, d))))
    cert = certify(
        program,
        {a: 0.6, b: 0.5, c: 0.4, d: 0.3},
        q,
        _ConstantEngine(),
        1,
        monotone=True,
    )
    statuses = {frozenset(v.reason): v.status for v in cert.verdicts}
    assert statuses[frozenset({a, b})] == "unseparable"  # the fixture still says so

    record = _certificate_record(0, cert)
    reasons = json.loads(json.dumps(record))["reasons"]
    by_label = {r["label"]: r for r in reasons}
    # Every status is a JSON string, and the unseparable one is spelled verbatim — a later change
    # that collapses it into a truth value cannot pass this test while keeping the name.
    for r in reasons:
        assert isinstance(r["status"], str)
    assert any(r["status"] == "unseparable" for r in reasons), by_label
