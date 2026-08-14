"""Build the committed report JSON Schema from a real report payload.

Run from the repository root with ``python docs/build_report_schema.py``. The report and its
``to_dict`` methods remain the authority; this script only chooses a representative run and
writes the generated schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reasonsmith import demo  # noqa: E402
from reasonsmith.report import JSON_SCHEMA_VERSION, check_conformance  # noqa: E402
from reasonsmith.schema import schema_from_payloads  # noqa: E402
from reasonsmith.spec import load_pack  # noqa: E402

OUTPUT = ROOT / "docs" / "schema" / f"report-v{JSON_SCHEMA_VERSION}.schema.json"


def build_schema() -> dict:
    """Return the schema generated from actual report serialisations."""
    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    payloads = [report.to_dict(), report.to_dict(audience="developer")]
    return schema_from_payloads(payloads)


def write_schema(path: Path = OUTPUT) -> Path:
    """Write the versioned schema and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_schema(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_schema())
