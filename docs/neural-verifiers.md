# Neural verifier integrations

## Marabou (slice 3)

Reasonsmith’s Marabou bridge is an optional, out-of-process oracle. Installing `reasonsmith`
does **not** install Marabou, `maraboupy`, or a solver binary. Install the pinned open-source CPU
release separately and put its `marabou` executable on `PATH` (or pass an absolute executable path
to `reasonsmith.neural_verifiers.MarabouVerifier`):

```console
pip install maraboupy==2.0.0
# If your distribution builds the CLI from source, use the Marabou 2.0.0 release/commit
# documented by that distribution and verify: marabou --version
```

The adapter accepts the compiled ONNX/VNN-LIB query from
`reasonsmith.neural_queries` and invokes the executable with an argument vector in a private
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

Complete mode is deliberately refused until the slice-4 soundness gate. Timeout, process crash,
malformed status or assignment, version drift from Marabou 2.0.0, and unsupported ONNX operators
return a non-verdict `VerifierRun`. Every run carries the tool and version, VNN-LIB version, command
configuration, resource limits, return code, and SHA-256 hashes of the product model, VNN-LIB query,
and process output.

The real integration fixture is skipped unless `marabou --version` reports exactly `2.0.0`; CI uses
mocked subprocesses for the failure taxonomy, so the base test suite never requires Marabou.
