import json
from datetime import datetime
from pathlib import Path

import pytest

import reasonsmith.published_counts as counts
from reasonsmith.published_counts import published_counts
from reasonsmith.spec import list_packs


def test_published_counts_artifact_matches_tree():
    path = Path("docs/published-counts.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected = published_counts()
    assert artifact["generated_at"]
    generated = datetime.fromisoformat(artifact["generated_at"])
    assert generated.tzinfo is not None
    assert generated.utcoffset().total_seconds() == 0
    # Generation time is intentionally not compared: it records when this artefact was made.
    assert {k: v for k, v in artifact.items() if k != "generated_at"} == {
        k: v for k, v in expected.items() if k != "generated_at"
    }


def test_published_counts_command_is_machine_readable(capsys):
    from reasonsmith.cli import main

    assert main(["published-counts"]) == 0
    assert json.loads(capsys.readouterr().out)["pack_count"] == len(list_packs())


def test_published_counts_verification_manifest_and_writer(monkeypatch, tmp_path):
    manifest = tmp_path / "legal-verification.json"
    monkeypatch.setattr(counts, "_VERIFICATION", manifest)
    baseline = published_counts()
    manifest.write_text(
        json.dumps({"match": baseline["quote_count"], "differ": 0, "verified_at": "today"}),
        encoding="utf-8",
    )
    verified = published_counts()
    assert verified["quotes_last_verified"] == "today"
    assert verified["quotes_verification"]["status"] == "verified"
    manifest.write_text(json.dumps({"match": 0, "differ": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="does not cover"):
        published_counts()
    manifest.write_text(
        json.dumps({"match": baseline["quote_count"], "differ": 0, "verified_at": "today"}),
        encoding="utf-8",
    )
    output = tmp_path / "published.json"
    counts.write_published_counts(output)
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == 1
