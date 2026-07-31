"""Verification engines for reasonsmith v0.2.

What this module is for:
  Exports verification engines (`RecordEngine`, `ObservedEngine`, `ProvedEngine`).

What a reader must not break:
  - `SUPPORTED_FORMALISMS` in `report.py` maps to engines exported here; widen
    `SUPPORTED_FORMALISMS` only when new engines land.
    Why this matters: Widening supported formalisms prematurely causes missing engines to be
    reported as evaluated rather than not evaluated.
"""

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.engines.record import RecordEngine

__all__ = [
    "RecordEngine",
    "ObservedEngine",
    "ProvedEngine",
]
