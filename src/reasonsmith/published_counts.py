"""Machine-readable facts for the Reasonsmith site build.

The values in this module are deliberately computed from the shipped packs and the
strength enum.  ``render`` is the only operation that writes an artefact; the artefact
therefore carries both the source verification date and its own generation timestamp.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from reasonsmith.spec import list_packs, load_pack
from reasonsmith.verdict import Strength

_ROOT = Path(__file__).resolve().parents[2]
_SOURCE = _ROOT / "docs" / "legal-sources.md"
_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")


def _source_dates() -> list[str]:
    return ["-".join(m.groups()) for m in _DATE_RE.finditer(_SOURCE.read_text(encoding="utf-8"))]


def published_counts() -> dict[str, object]:
    """Return facts consumed by the site, with provenance for every date."""
    packs = [load_pack(name) for name in list_packs()]
    statutory = [p for p in packs if "paper" not in p.source_metadata]
    dates = _source_dates()
    # A quote is a requirement in a statutory pack; Table 7 rows quote the paper instead.
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "reasonsmith tree (verdict.py, spec.py, packs/, docs/legal-sources.md)",
        "rungs": [strength.value for strength in Strength],
        "pack_count": len(packs),
        "requirement_count": sum(len(p.requirements) for p in packs),
        "quote_count": sum(len(p.requirements) for p in statutory),
        "regulation_count": len({p.source_metadata.get("document") for p in statutory}),
        "quotes_last_verified": max(dates),
        "quotes_last_verified_source": "docs/legal-sources.md (retrieval/re-verification dates)",
    }


def write_published_counts(path: str | Path) -> None:
    Path(path).write_text(json.dumps(published_counts(), indent=2) + "\n", encoding="utf-8")
