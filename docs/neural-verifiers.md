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
