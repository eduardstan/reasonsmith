"""Tests for sourced before/after statute replay (the fixture is explicitly synthetic)."""

import hashlib
import json
from pathlib import Path

import pytest

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.spec import load_pack
from reasonsmith.statute_replay import (
    SCHEMA_VERSION,
    SourceProvenance,
    SourceSnapshot,
    StatuteRevision,
    compare_revisions,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statute_replay"


def _revision(name: str) -> StatuteRevision:
    return StatuteRevision.from_manifest(FIXTURES / f"{name}.json")


def _sut(flag: bool = True, capabilities=None):
    declared = {"flag"} if capabilities is None else set(capabilities)
    return CallableAdapter(lambda _case: {"flag": flag}, declared, decisions=[{"flag": flag}])


def test_synthetic_fixture_flips_and_preserves_both_ordinary_results(tmp_path):
    before, after = _revision("before"), _revision("after")
    # The statutory wording changed, and the after pack's formal property records that changed
    # duty. This is still a comparison of ordinary conformance outcomes, not a new verdict.
    pack = (
        after.pack_path.read_text()
        .replace('spec = "present(flag)"', 'spec = "present(missing)"')
        .replace('requires = ["flag"]', 'requires = ["missing"]')
    )
    changed_pack = tmp_path / "after.toml"
    changed_pack.write_text(pack)
    source = after.source("ai_act")
    revision = StatuteRevision(
        "after-edited",
        load_pack(changed_pack),
        hashlib.sha256(changed_pack.read_bytes()).hexdigest(),
        (source,),
        changed_pack,
    )
    comparison = compare_revisions(before, revision, _sut())
    duty = comparison.duties[0]
    assert duty.status == "changed"
    assert duty.before["outcome"] == "satisfied"
    assert duty.after["outcome"] == "unattainable"
    assert duty.attribution == "statutory-and-pack-change"
    assert duty.before["verdict"] != "violated"  # a non-pass never becomes a pass


def test_wording_revision_does_not_flip_the_result():
    comparison = compare_revisions(_revision("before"), _revision("after"), _sut())
    duty = comparison.duties[0]
    assert duty.status == "unchanged"  # only provenance wording changed; the answer did not
    assert duty.before["outcome"] == duty.after["outcome"] == "satisfied"
    assert duty.attribution == "none"
    assert duty.source_status_before == duty.source_status_after == "match"


def test_pack_edit_is_not_called_a_statutory_change(tmp_path):
    before = _revision("before")
    source = before.source("ai_act")
    pack_text = (
        before.pack_path.read_text()
        .replace('spec = "present(flag)"', 'spec = "present(missing)"')
        .replace('requires = ["flag"]', 'requires = ["missing"]')
    )
    pack_path = tmp_path / "edited.toml"
    pack_path.write_text(pack_text)
    edited = StatuteRevision(
        "pack-edit",
        load_pack(pack_path),
        hashlib.sha256(pack_path.read_bytes()).hexdigest(),
        (source,),
        pack_path,
    )
    duty = compare_revisions(before, edited, _sut()).duties[0]
    assert duty.status == "changed"
    assert duty.attribution == "pack-change"
    assert not duty.source_changed


def test_system_or_evidence_change_is_not_called_statutory(tmp_path):
    before = _revision("before")
    # Same pack and source, but two supplied systems produce different traces.
    duty = compare_revisions(before, before, _sut(True), after_sut=_sut(False, [])).duties[0]
    assert duty.status == "changed"
    assert duty.attribution == "system-change"
    assert not duty.source_changed and not duty.pack_changed


def test_added_and_removed_duties_are_explicit(tmp_path):
    before = _revision("before")
    pack = before.pack_path.read_text().replace('id = "synthetic_duty"', 'id = "different_duty"')
    path = tmp_path / "different.toml"
    path.write_text(pack)
    other = StatuteRevision(
        "different",
        load_pack(path),
        hashlib.sha256(path.read_bytes()).hexdigest(),
        before.sources,
        path,
    )
    duties = compare_revisions(before, other, _sut()).duties
    assert {d.status for d in duties} == {"added", "removed"}
    assert all(d.attribution == "not-attributable" for d in duties)


def test_manifest_records_and_checks_hashes():
    revision = _revision("before")
    data = revision.to_dict()
    assert data["sources"][0]["synthetic"] is True
    assert len(data["pack_sha256"]) == 64
    assert revision.quote_status(revision.pack.requirements[0]) == "match"
    with pytest.raises(ValueError, match="hash mismatch"):
        SourceSnapshot(
            "ai_act",
            "cellar-xhtml",
            "tampered",
            SourceProvenance(
                "https://example.invalid", "2026-01-01T00:00:00+00:00", "0" * 64, True
            ),
        )


def test_manifest_schema_and_provenance_refusals(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": SCHEMA_VERSION + 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported statute revision schema"):
        StatuteRevision.from_manifest(path)
    with pytest.raises(ValueError, match="provenance"):
        SourceProvenance("", "now", "bad", False)


def test_snapshot_constructors_and_revision_refusals(tmp_path):
    before = _revision("before")
    source_file = tmp_path / "source.html"
    source_file.write_text('<div id="012.001">old statutory wording</div>\n')
    snapshot = SourceSnapshot.from_file(
        "ai_act",
        source_file,
        url="https://example.invalid",
        retrieved_at="2026-01-01T00:00:00+00:00",
        synthetic=True,
    )
    assert snapshot.to_manifest_entry("source.html")["key"] == "ai_act"
    with pytest.raises(ValueError, match="unknown statutory source"):
        SourceSnapshot(
            "unknown",
            "html",
            "x",
            SourceProvenance(
                "https://example.invalid",
                "2026-01-01T00:00:00+00:00",
                hashlib.sha256(b"x").hexdigest(),
            ),
        )
    with pytest.raises(ValueError, match="non-empty"):
        StatuteRevision("", before.pack, before.pack_sha256, before.sources)
    with pytest.raises(ValueError, match="duplicate"):
        StatuteRevision("dup", before.pack, before.pack_sha256, before.sources * 2)
    with pytest.raises(ValueError, match="missing source"):
        StatuteRevision("missing", before.pack, before.pack_sha256, ())
    with pytest.raises(ValueError, match="requires the pack"):
        StatuteRevision("hash", before.pack, "0", before.sources)
    with pytest.raises(KeyError):
        before.source("unknown")


def test_source_status_differ_and_unverifiable_passages(tmp_path):
    before = _revision("before")
    source_file = tmp_path / "changed.html"
    source_file.write_text('<div id="012.001">unrelated wording</div>\n')
    source = SourceSnapshot.from_file(
        "ai_act",
        source_file,
        url="https://example.invalid",
        retrieved_at="2026-01-01T00:00:00+00:00",
        synthetic=True,
    )
    changed = StatuteRevision("changed-source", before.pack, before.pack_sha256, (source,))
    assert changed.quote_status(changed.pack.requirements[0]) == "differ"
    assert changed.safe_passage(changed.pack.requirements[0]) == "unrelated wording"
    # A PDF payload with an XHTML selector is refused by the existing drift extractor.
    pdf_source = SourceSnapshot(
        "ai_act",
        "pdf",
        b"not a PDF",
        SourceProvenance(
            "https://example.invalid",
            "2026-01-01T00:00:00+00:00",
            hashlib.sha256(b"not a PDF").hexdigest(),
            True,
        ),
    )
    unverifiable = StatuteRevision("unverifiable", before.pack, before.pack_sha256, (pdf_source,))
    assert unverifiable.quote_status(unverifiable.pack.requirements[0]) == "could-not-verify"


def test_comparison_serialization_and_manifest_writer(tmp_path, capsys):
    before, after = _revision("before"), _revision("after")
    comparison = compare_revisions(before, after, _sut())
    assert comparison.changed == ()
    assert comparison.to_dict()["schema_version"] == SCHEMA_VERSION
    assert "attribution" in comparison.duties[0].to_dict()
    assert "source, pack" in comparison.render_text()
    pack = tmp_path / "before.toml"
    source = tmp_path / "before.html"
    pack.write_bytes(before.pack_path.read_bytes())
    source.write_bytes((FIXTURES / "before.html").read_bytes())
    manifest = tmp_path / "revision.json"
    from reasonsmith.statute_replay import write_manifest

    write_manifest(manifest, before, pack_path=pack, source_paths={"ai_act": source})
    loaded = StatuteRevision.from_manifest(manifest)
    assert loaded.revision == before.revision
    assert loaded.sources[0].provenance.sha256 == before.sources[0].provenance.sha256


def test_cli_replays_with_a_system_module(capsys):
    from reasonsmith.statute_replay import main

    assert (
        main(
            [
                str(FIXTURES / "before.json"),
                str(FIXTURES / "after.json"),
                "--system-module",
                "reasonsmith.examples.symbolic_rules:system_under_test",
                "--json",
            ]
        )
        == 0
    )
    assert '"duties"' in capsys.readouterr().out
