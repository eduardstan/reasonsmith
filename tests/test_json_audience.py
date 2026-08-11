"""The `--json` envelope declares the projection it was asked for, and never applies one.

What this module is for:
  `reasonsmith check --audience X --json` emits the complete machine record, `audience` not
  being a display flag that hides fields from a consumer. But a record that silently omitted what
  a projection hides would be exactly the false completeness the package refuses: a consumer could
  not tell *absent because the audience is not shown it* from *absent because the run never
  established it*. So the envelope *declares* the projection — a top-level `audience` block naming
  the requested audience and every flag of its resolved `AudienceProjection` — and carries every
  field regardless. The renderer applies the flags; the record just says which projection it was
  asked for.

What a reader must not break:
  - `results` (the verdicts, strengths, rungs, limits) is **byte-identical across every
    audience**: a machine consumer must get the same findings whichever display flag was passed,
    the property that makes carrying the audience declaration safe
    (`test_every_audience_leaves_results_byte_identical`).
  - The `audience` block is a projection of the `AUDIENCES` table, checked **field by field
    against the dataclass** rather than against literals — so the block cannot advertise flags
    the table does not own, and a table edit changes the block the test expects
    (`test_each_audience_block_matches_its_audiences_entry`).
  - `--audience` omitted means `name: null` and the full projection, exactly the relationship the
    text renderer already keeps with `audience=None` (`test_omitted_audience_is_null_full`).
  - An unknown audience is refused with the renderer's own `_projection` message, not a new JSON
    error path (`test_an_unknown_audience_is_refused_with_the_renderers_message`).
  - The block carries one key per `AudienceProjection` field plus `name`, so a flag added to the
    dataclass fails this test until it is carried in the JSON too
    (`test_the_json_block_carries_every_audience_projection_field`).
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from reasonsmith import demo
from reasonsmith.render import _FULL, AUDIENCES, AudienceProjection
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack


@pytest.fixture(scope="module")
def report():
    return check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))


def _block(report, audience: str | None) -> dict:
    """The `audience` block of the machine record for this audience."""
    return report.to_dict(audience=audience)["audience"]


def test_every_audience_leaves_results_byte_identical(report):
    """`results` is the same no matter which audience a consumer asks for.

    This is the property that makes declaring the projection safe: a machine consumer is never
    handed a narrower record because a display flag was passed, so nothing permanent can hide from
    a consumer behind `--audience`. The two halves of the brief's proof — the two JSON files
    differ, but `jq .results` of each is identical — are pinned here on the emitted results list.
    """
    expected = report.to_dict()["results"]
    for audience in AUDIENCES:
        assert report.to_dict(audience=audience)["results"] == expected


def test_every_audience_carries_the_domain_notice_unchanged(report):
    """The notice is a machine-record fact, so no audience projection suppresses it."""
    expected = report.to_dict()["undeclared_domain_notice"]
    for audience in [None, *AUDIENCES]:
        assert report.to_dict(audience=audience)["undeclared_domain_notice"] == expected


def test_each_audience_block_matches_its_audiences_entry(
    report,
):
    """Every one of the five audiences produces a block equal to its `AUDIENCES` entry.

    Checked field-by-field against the dataclass, never against literals: the expected flags are
    re-read from `AUDIENCES` rather than typed, so a flag changed in `AUDIENCES` changes the
    expected block in the same edit.
    """
    for name, projection in AUDIENCES.items():
        block = _block(report, name)
        assert block["name"] == name
        for field in fields(AudienceProjection):
            assert block[field.name] == getattr(projection, field.name)


def test_omitted_audience_gives_null_full(report):
    """No audience passed, `name` is `null` and the flags are `_FULL`'s.

    The text renderer emits the full report for `audience=None`; the envelope says the same thing
    in its own terms — a null name and the full projection, which is the auditor's table by
    identity.
    """
    block = _block(report, None)
    assert block["name"] is None
    for field in fields(AudienceProjection):
        assert block[field.name] == getattr(_FULL, field.name)
    # The auditor block differs only in the name it declares; the flags are the same object's.
    auditor_block = _block(report, "auditor")
    assert auditor_block["name"] == "auditor"
    for field in fields(AudienceProjection):
        assert auditor_block[field.name] == block[field.name]


def test_an_unknown_audience_is_refused_by_the_renderers_message(report):
    """A typo must fail the exact way it already failed the text renderer, through `_projection`.

    No second, JSON-only error path may be invented: `to_dict` resolves the audience through the
    renderer's own `_projection`, so a bad name raises the same ValueError the text renderer does.
    """
    with pytest.raises(ValueError, match="unknown audience"):
        report.to_dict(audience="affected individual")
    with pytest.raises(ValueError, match="unknown audience"):
        report.to_dict(audience="reglator")


def test_the_json_block_carries_every_audience_projection_field(report):
    """The block has exactly the names the dataclass defines, plus `name`.

    If `AudienceProjection` gains a field, `_audience_block` derives one for it by iteration, so
    the JSON carries it; this test fails if the derivation stops or a field is dropped, so the
    block cannot silently lose a flag. `dataclasses.fields` order is the dataclass's own
    declaration order.
    """
    block_keys = set(_block(report, "auditor"))
    expected = {"name"} | {f.name for f in fields(AudienceProjection)}
    assert block_keys == expected
