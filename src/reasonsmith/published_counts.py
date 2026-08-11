"""Machine-readable facts for the Reasonsmith site build.

The values in this module are deliberately computed from the shipped packs and the
strength enum.  ``render`` is the only operation that writes an artefact; the artefact
therefore carries both the source verification date and its own generation timestamp.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from reasonsmith.drift import STATUTORY_PACKS
from reasonsmith.spec import list_packs, load_pack
from reasonsmith.verdict import Strength

_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION = _ROOT / "docs" / "legal-verification.json"


def _verification() -> dict[str, object] | None:
    """Read the output of a statute-drift verification run, when one exists."""
    if not _VERIFICATION.exists():
        return None
    return json.loads(_VERIFICATION.read_text(encoding="utf-8"))


def published_counts() -> dict[str, object]:
    """Return facts consumed by the site, with provenance for every date."""
    packs = [load_pack(name) for name in list_packs()]
    statutory = [load_pack(name) for name in STATUTORY_PACKS]
    verification = _verification()
    quote_count = sum(len(p.requirements) for p in statutory)
    if verification is not None and (
        verification["match"] != quote_count or verification["differ"] != 0
    ):
        raise ValueError("legal verification manifest does not cover all statutory quotes")
    # A quote is a requirement in a statutory pack; Table 7 rows quote the paper instead.
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "reasonsmith tree (verdict.py, spec.py, packs/, docs/legal-sources.md)",
        "rungs": [strength.value for strength in Strength],
        "pack_count": len(packs),
        "requirement_count": sum(len(p.requirements) for p in packs),
        "quote_count": sum(len(p.requirements) for p in statutory),
        "statutory_source_document_count": len(
            {p.source_metadata.get("document") for p in statutory}
        ),
        "quotes_last_verified": verification["verified_at"] if verification else None,
        "quotes_last_verified_source": (
            "statute-drift verification run (docs/legal-verification.json)"
            if verification else "no statute-drift verification run recorded"
        ),
        "quotes_verification": (
            {"status": "verified", "match": verification["match"], "differ": verification["differ"]}
            if verification else {"status": "not_run"}
        ),
    }


def write_published_counts(path: str | Path) -> None:
    Path(path).write_text(json.dumps(published_counts(), indent=2) + "\n", encoding="utf-8")
