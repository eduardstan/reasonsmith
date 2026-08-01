"""Verification engines for reasonsmith v0.2.

What this module is for:
  Exports verification engines (`RecordEngine`, `ObservedEngine`, `ProbedEngine`, `ProvedEngine`),
  one per rung of the strength lattice above `unattainable`. Which engine a `logical` requirement
  reaches is decided in `report.evaluate_requirement`, by what the system exposes: `logic()` gets
  the proved engine, `decide()` alone gets the probed engine.

What a reader must not break:
  - `SUPPORTED_FORMALISMS` in `report.py` maps to engines exported here; widen
    `SUPPORTED_FORMALISMS` only when new engines land.
    Why this matters: Widening supported formalisms prematurely causes missing engines to be
    reported as evaluated rather than not evaluated.
"""

from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.engines.probed import ProbedEngine
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.engines.record import RecordEngine

__all__ = [
    "RecordEngine",
    "ObservedEngine",
    "ProbedEngine",
    "ProvedEngine",
]
