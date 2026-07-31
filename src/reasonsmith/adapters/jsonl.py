"""JSONL decision-log adapter for reasonsmith v0.2.

Point JSONLAdapter at a file or stream of decision records and it is a valid SystemUnderTest.
Works for a system written in any language that emits a JSONL log trace.

Capability derivation:
Capabilities are derived honestly from record content. A capability is what the system can
emit, so a field present and non-blank in at least ONE record is a declared signal — a field
missing from some of the later records is then a trace violation the engines report, not a
capability the system lacks. Fields present in only some records are also recorded in
`partially_present_fields` for diagnostic inspection.

Derived capabilities are read from one supplied trace, never declared by the system, so
`capability_basis` records which of the two a result rests on and the report says so.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from typing import Any, TextIO

from reasonsmith.report import _is_present
from reasonsmith.sut import BaseSUT


class JSONLAdapter(BaseSUT):
    """System Under Test adapter for JSONL decision trace files."""

    def __init__(
        self,
        source: str | Path | TextIO,
        declared_capabilities: set[str] | Iterable[str] | None = None,
    ):
        self.source = source
        self._records = self._parse_source(source)

        if declared_capabilities is not None:
            super().__init__(declared_capabilities)
            self._partially_present: dict[str, tuple[int, int]] = {}
            self.capability_basis = "declared"
        else:
            capabilities, partially_present = self._derive_capabilities(self._records)
            super().__init__(capabilities)
            self._partially_present = partially_present
            self.capability_basis = "trace"

    @property
    def partially_present_fields(self) -> dict[str, tuple[int, int]]:
        """Fields present in some but not all records."""
        return dict(self._partially_present)

    def _parse_source(self, source: str | Path | TextIO) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                # Allow inline JSONL string if it contains newlines or json syntax
                text = str(source).strip()
                if "\n" in text or (text.startswith("{") and text.endswith("}")):
                    fh: TextIO = StringIO(text)
                else:
                    raise FileNotFoundError(f"JSONL decision log file not found: {source}")
            else:
                fh = path.open("r", encoding="utf-8")
        else:
            fh = source

        try:
            for line_num, line in enumerate(fh, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    obj = json.loads(line_str)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Line {line_num} in JSONL log is not valid JSON: {exc}"
                    ) from exc
                if not isinstance(obj, dict):
                    raise TypeError(
                        f"Line {line_num} in JSONL log must be a JSON object (dict), "
                        f"got {type(obj).__name__}"
                    )
                records.append(obj)
        finally:
            if isinstance(source, (str, Path)) and 'fh' in locals() and hasattr(fh, 'close'):
                fh.close()

        return records

    @staticmethod
    def _derive_capabilities(
        records: list[dict[str, Any]],
    ) -> tuple[set[str], dict[str, tuple[int, int]]]:
        if not records:
            return set(), {}

        total = len(records)
        counts: dict[str, int] = {}

        for rec in records:
            for key, val in rec.items():
                if _is_present(val):
                    counts[key] = counts.get(key, 0) + 1

        partially_present = {
            k: (count, total) for k, count in counts.items() if 0 < count < total
        }
        return set(counts), partially_present

    def decisions(self) -> Iterable[dict[str, Any]]:
        return list(self._records)


#: Alias for JSONLAdapter
JsonlSUT = JSONLAdapter
