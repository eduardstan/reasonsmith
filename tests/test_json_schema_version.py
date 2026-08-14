"""The `--json` envelope carries its own shape version, and the shape is pinned to it.

`JSON_SCHEMA_VERSION` is the promise a consumer of `reasonsmith check --json` parses against.
A promise nothing checks is a comment, so the two key sets below are written out literally: a
key removed, renamed or retyped fails these tests, and the only way to make them pass again is
to change the expected shape *and* the number in the same edit. That is the whole mechanism —
it catches a shape change made without moving the version, and it deliberately does not try to
catch a change in what a key *means* while its name and type stay put. No machinery exists for
that, and the convention on `JSON_SCHEMA_VERSION` states the obligation instead.

Adding a key is not a breaking change under that convention, so `_TOP_LEVEL_KEYS` is checked
for equality all the same: the point is that someone adding a key must come here, read the
convention, and decide. An assertion of "at least these keys" would let the decision be skipped.
"""

from __future__ import annotations

import json

import pytest

from reasonsmith import demo
from reasonsmith.report import JSON_SCHEMA_VERSION, ConformanceReport, check_conformance
from reasonsmith.spec import load_pack


@pytest.fixture(scope="module")
def sample_report() -> ConformanceReport:
    """One real run, so the pinned shape is the shape the CLI actually emits."""
    return check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))


#: Every key `ConformanceReport.to_dict()` emits, at version 2.
_TOP_LEVEL_KEYS = {
    "schema_version",
    "system_name",
    "system_scope",
    "system_domains",
    "pack_id",
    "headline",
    "counts",
    "results",
    "limits",
    "time_domain",
    # Added beside existing envelope keys, not renamed or retyped, so the convention says this
    # is not a version bump — the decision was made here rather than skipped.  The value is the
    # report's undeclared-domain notice, or null when every domain-limited duty was evaluated;
    # consumers therefore have a defined value in both cases.
    "undeclared_domain_notice",
    # Added, not renamed or retyped, so the convention says this is not a version bump — the
    # decision was made here rather than skipped. `audience` is the projection the record was
    # asked for, declared rather than applied: it carries the resolved `AudienceProjection`
    # flags beside the name (`null` when none was asked for), and no field is ever filtered
    # from the JSON for any audience. A consumer reading the keys it knows is unaffected.
    "audience",
}

#: Every key `RequirementResult.to_dict()` emits, at version 2. The results list is part of the
#: envelope's shape, so a change here is a change to the version's promise just as much as one
#: at the top level.
_RESULT_KEYS = {
    "requirement_id",
    "source_clause",
    # Added beside `source_clause`, not renamed or retyped, so the convention says this is not a
    # version bump — the decision was made here rather than skipped. `verbatim_text` is the
    # statutory quotation the duty restates, carried through from the pack unchanged; a consumer
    # reading the keys it knows is unaffected.
    "verbatim_text",
    "verdict",
    "strength",
    # Additive operational outcome. It distinguishes not_applicable, not_evaluated and
    # unattainable without changing the compatibility verdict/rung pair.
    "outcome",
    "signals_required",
    "signals_missing",
    "evidence_summary",
    "details",
    # Certificate FAIL measurements are additive findings beside the unchanged requirement
    # verdict. They do not alter the schema version under the additive-key convention.
    "findings",
    # Added, not renamed or retyped, so the convention says this is not a version bump — the
    # decision was made here rather than skipped. `basis` is the evidence basis of
    # `verdict.EvidenceBasis`: which kind of thing this duty's evidence is about, beside `strength`,
    # which says how far the claim was pushed. A consumer reading the keys it knows is unaffected.
    "basis",
    "binding",
    "scope",
    "domains",
    # Additive positive-result boundary and rationale marker. They are null/false or empty
    # outside the positive case, so a consumer can read the keys without a version bump.
    "scope_boundary",
    "witness_provenance",
    "formalized_subset_only",
    "formalized_subset_note",
}


def test_the_envelope_declares_its_schema_version(sample_report: ConformanceReport) -> None:
    assert sample_report.to_dict()["schema_version"] == JSON_SCHEMA_VERSION


def test_declared_domain_has_a_defined_null_notice(sample_report: ConformanceReport) -> None:
    """The added notice key is null when no domain-limited duty was skipped."""
    assert sample_report.undeclared_domain_notice is None
    assert sample_report.to_dict()["undeclared_domain_notice"] is None


def test_the_version_survives_serialisation(sample_report: ConformanceReport) -> None:
    """A consumer reads the JSON text, not the dict, so the field must be in the text."""
    assert json.loads(sample_report.to_json())["schema_version"] == JSON_SCHEMA_VERSION


def test_version_2_is_this_shape(sample_report: ConformanceReport) -> None:
    """The pin. Changing the shape means changing this test, which means reading the convention."""
    assert JSON_SCHEMA_VERSION == 2
    payload = sample_report.to_dict()
    assert set(payload) == _TOP_LEVEL_KEYS
    assert payload["results"], "the fixture must exercise at least one result"
    for result in payload["results"]:
        assert set(result) == _RESULT_KEYS
