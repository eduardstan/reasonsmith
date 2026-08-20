"""Verification engines for reasonsmith v0.10.2.

What this module is for:
  Exports verification engines (`RecordEngine`, `ObservedEngine`, `ProbedEngine`, `ProvedEngine`,
  `CertificateEngine`, `TemporalProofEngine`), covering the rungs of the strength lattice above
  `unattainable` — two at `probed` and two at `proved`, which is not a contradiction: a rung is a
  claim about how far the evidence reaches, and two engines can reach the same distance over
  different properties. Which engine a requirement reaches is decided in
  `report.evaluate_requirement`, by what the system exposes: `logic()` gets a solver — the proved
  engine for a state property, the temporal proof engine for an `always(f)` over the trace —
  `decide()` alone gets the probed engine, and a duty about reason adequacy gets the certificate
  engine and nothing else (see `engines.certificate.DELETED_REASON_COUNT`).

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
from reasonsmith.engines.temporal import TemporalProofEngine

__all__ = [
    "CertificateEngine",
    "ObservedEngine",
    "ProbedEngine",
    "ProvedEngine",
    "RecordEngine",
    "TemporalProofEngine",
]
