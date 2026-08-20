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

from reasonsmith.neural_verifiers.abcrown import (
    ABCROWN_COMMIT,
    ABCROWN_VERSION,
    ALPHA_BETA_CROWN_COMMIT,
    ALPHA_BETA_CROWN_VERSION,
    ABCROWNAdapter,
    ABCrownAdapter,
    ABCROWNResourceLimits,
    ABCROWNVerifier,
    ABCrownVerifier,
    AlphaBetaCrownAdapter,
    AlphaBetaCROWNVerifier,
    AlphaBetaCrownVerifier,
    map_abcrown_status,
    parse_abcrown_status,
)
from reasonsmith.neural_verifiers.differential import (
    DifferentialResult,
    compare_checks,
    compare_runs,
)

__all__ += [
    "ABCROWN_COMMIT",
    "ABCROWN_VERSION",
    "ALPHA_BETA_CROWN_COMMIT",
    "ALPHA_BETA_CROWN_VERSION",
    "ABCROWNAdapter",
    "ABCROWNResourceLimits",
    "ABCROWNVerifier",
    "ABCrownAdapter",
    "ABCrownVerifier",
    "AlphaBetaCROWNVerifier",
    "AlphaBetaCrownAdapter",
    "AlphaBetaCrownVerifier",
    "DifferentialResult",
    "compare_checks",
    "compare_runs",
    "map_abcrown_status",
    "parse_abcrown_status",
]
