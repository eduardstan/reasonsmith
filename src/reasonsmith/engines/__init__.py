"""Verification engines for reasonsmith v0.2.

What this module is for:
  Exports verification engines (`RecordEngine`, `ObservedEngine`, `ProbedEngine`, `ProvedEngine`,
  `CertificateEngine`), one per rung of the strength lattice above `unattainable` — two at
  `probed`, which is not a contradiction: a rung is a claim about how far the evidence reaches,
  and two searches can reach the same distance by different routes. Which engine a `logical`
  requirement reaches is decided in `report.evaluate_requirement`, by what the system exposes:
  `logic()` gets the proved engine, `decide()` alone gets the probed engine, and a duty about
  reason adequacy gets the certificate engine and nothing else (see
  `engines.certificate.DELETED_REASON_COUNT`).

What a reader must not break:
  - `SUPPORTED_FORMALISMS` in `report.py` maps to engines exported here; widen
    `SUPPORTED_FORMALISMS` only when new engines land.
    Why this matters: Widening supported formalisms prematurely causes missing engines to be
    reported as evaluated rather than not evaluated.
"""

from reasonsmith.engines.certificate import CertificateEngine
from reasonsmith.engines.observed import ObservedEngine
from reasonsmith.engines.probed import ProbedEngine
from reasonsmith.engines.proved import ProvedEngine
from reasonsmith.engines.record import RecordEngine

__all__ = [
    "RecordEngine",
    "ObservedEngine",
    "ProbedEngine",
    "ProvedEngine",
    "CertificateEngine",
]
