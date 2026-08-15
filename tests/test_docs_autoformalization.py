"""Pins the autoformalisation study and its authoring-path entry point."""

from __future__ import annotations

from pathlib import Path

from reasonsmith.autoformalize import challenge_requirements
from reasonsmith.spec import list_packs, load_pack

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "docs" / "autoformalization-study.md"


def test_the_study_publishes_the_complete_current_corpus_and_rates():
    document = STUDY.read_text(encoding="utf-8")
    requirements = {
        req.id: req for name in list_packs() for req in load_pack(name).requirements
    }
    assert len(requirements) == len(challenge_requirements()) == 37
    assert "37 challenge sets" in document
    for phrase in ("28 record-presence", "4 logical", "temporal, and", "1 counterfactual"):
        assert phrase in document
    assert "31/37 (83.78%) exact-match" in document
    assert "36/37 (97.30%)" in document
    assert "25 unavailable" in document
    assert "36/36" in document


def test_the_authoring_docs_link_the_worked_path_and_keep_the_safety_boundary():
    harness = (ROOT / "docs" / "autoformalization.md").read_text(encoding="utf-8")
    authoring = (ROOT / "docs" / "authoring-packs.md").read_text(encoding="utf-8")
    assert "The AI-assisted authoring path" in harness
    assert "source quote and hand-authored gold" in harness.lower()
    assert "round-trip gate" in harness
    assert "gold-challenge gate" in harness.lower()
    assert "Human sign-off: pending" in harness
    assert "autoformalization-study.md" in harness
    assert "autoformalization.md" in authoring
    assert "model proposes, the formal checker disposes" in authoring.lower()
