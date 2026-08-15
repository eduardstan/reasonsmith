"""Optional neural verifier adapters.

Adapters in this package are oracle boundaries and never produce a RequirementResult.
"""

from reasonsmith.neural_verifiers.marabou import (
    MARABOU_VERSION,
    VNNLIB_VERSION,
    MarabouAdapter,
    MarabouVerifier,
    ResourceLimits,
)

__all__ = [
    "MARABOU_VERSION",
    "VNNLIB_VERSION",
    "MarabouAdapter",
    "MarabouVerifier",
    "ResourceLimits",
]
