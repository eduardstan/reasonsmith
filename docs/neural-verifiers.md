# Neural verifier integrations

## Marabou (slice 3)

Reasonsmith’s Marabou bridge is an optional, out-of-process oracle. Installing `reasonsmith`
does **not** install Marabou, `maraboupy`, or a solver binary. Install the pinned open-source CPU
release separately and put its `marabou` executable on `PATH` (or pass an absolute executable path
to `reasonsmith.neural_verifiers.MarabouVerifier`):

```console
# Marabou is installed separately; it is not a reasonsmith dependency.
python -m pip install \
  'git+https://github.com/NeuralNetworkVerification/Marabou.git@d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d'
marabou --version  # must report 2.0.0
```

The current artifact profile is embedded ONNX (`OnnxArtifact`); reasonsmith generates the
VNN-LIB 1.0 query from it. A VNN-LIB-only artifact family is not supported by this slice. The adapter
accepts the compiled ONNX/VNN-LIB query from `reasonsmith.neural_queries` and invokes the executable
with an argument vector in a private
temporary directory. VNN-LIB **1.0** is pinned. Set `ResourceLimits(cpu_seconds=...,
memory_bytes=...)` for OS-enforced CPU/address-space limits; the `timeout` argument supplies a wall-clock
limit. No shell interpolation is used.

```python
from reasonsmith.neural_verifiers import MarabouVerifier, ResourceLimits

verifier = MarabouVerifier(
    resource_limits=ResourceLimits(cpu_seconds=30, memory_bytes=2_000_000_000),
)
# verify(query, timeout=30, mode="bounded-search")
```

This slice exposes **bounded-search only**, at the `probed` ceiling. A `sat` result is only a
candidate counterexample: the core must run `verify_query`/`check_witness` replay before reporting a
violation. An `unsat` response in bounded mode is retained as provenance (`unsat_semantics` is
`provenance-only; bounded search is not complete`) and is never a universal verdict.

Complete mode is deliberately refused: the slice-4 soundness gate could not establish a clean
run on the pinned open-source path. The committed corpus and installation evidence are in
[`docs/neural-soundness-corpus.md`](neural-soundness-corpus.md). Until that gate passes, Marabou
stays at `probed`; timeout, process crash, malformed status or assignment, version drift from
Marabou 2.0.0, and unsupported ONNX operators return a non-verdict `VerifierRun`. Every run carries
the tool and version, VNN-LIB version, command configuration, resource limits, return code, and
SHA-256 hashes of the product model, VNN-LIB query, and process output. In particular, a bounded
`UNSAT` is provenance-only and is never a universal verdict. The VNN-COMP 2024 soundness incident is
an admission risk, not a footnote; alpha-beta-CROWN is the planned first `proved` integration.

The real integration fixture is skipped unless `marabou --version` reports exactly `2.0.0`; CI uses
mocked subprocesses for the failure taxonomy, so the base test suite never requires Marabou.

## Packaged ONNX SUT example

`reasonsmith.examples.onnx_credit_scorer` ships a deterministic two-input classifier together with
its validated `OnnxArtifact`, declared finite input space, replay hook, and two reproduced decision
records. It compiles the shipped ECOA counterfactual duty into the same product-ONNX/VNN-LIB query
the external verifier boundary accepts:

```console
python -m reasonsmith.examples.onnx_credit_scorer
```

Install `reasonsmith[neural]` to construct the artifact. The example invokes Marabou when available;
a missing executable, unsupported operator, timeout, or malformed response is printed as an oracle
status, never substituted with an `observed` conformance result. A SAT assignment is replayed through
both the packaged ONNX bytes and the SUT before `witness_replayed` can be true. Bounded UNSAT remains
provenance-only under the boundary described above.

## alpha-beta-CROWN (slice 6)

The second adapter is `reasonsmith.neural_verifiers.AlphaBetaCrownVerifier`, an optional
out-of-process bridge. It pins the upstream repository at commit
`e5c7e17bf0488843acb77b7519f59876717a49f4` (package metadata `abcrown==0.7.0`; the upstream
repository publishes no release tags) and VNN-LIB 1.0. It writes the embedded ONNX and generated
query to a private directory and invokes `complete_verifier/abcrown.py` without a shell.
alpha-beta-CROWN, PyTorch, CUDA, Gurobi, and CPLEX are not reasonsmith dependencies. Proprietary
solver modes are explicitly disabled.

Native statuses are retained in `VerifierRun.provenance["native_status"]` and are not collapsed:
`unsafe-pgd` and `unsafe-bab` are SAT candidates requiring `verify_query`/`check_witness` replay;
`safe-incomplete` is an incomplete bound and never a proof; `safe`/`complete-safe` are proof
candidates only when an explicitly admitted complete configuration is used; timeout and unknown
remain non-verdict statuses. The current pinned installation did not pass the runner preflight, so
the adapter's honest ceiling is `probed` and complete mode is refused.

The differential helpers in `neural_verifiers.differential` compare two raw or replayed runs. They
never vote: a semantic disagreement, or an agreement where either run is not verdict-eligible,
sets `stronger_allowed=False` and carries a diagnostic requiring the witness or
query/configuration to be reproduced.

## Optional-install evidence

The pinned alpha-beta-CROWN source was cloned at the commit above and installation was attempted
from this runner's Python 3.12.9 environment. Pip refused the package metadata before dependency
resolution because the project requires Python `~=3.11.0`; no verifier executable was produced and
no complete corpus run was possible. The full attempt and hashes are recorded in
[`docs/neural-soundness-corpus.md`](neural-soundness-corpus.md). CI therefore mocks subprocesses for
all alpha-beta-CROWN status/configuration tests, just as it does for Marabou.
