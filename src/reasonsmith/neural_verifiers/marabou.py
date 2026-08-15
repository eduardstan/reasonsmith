"""Out-of-process Marabou bridge for the slice-3 neural verifier contract.

This module is intentionally not an engine in :mod:`reasonsmith.engines`: it returns the
policy-free ``VerifierRun`` oracle result from ``neural_queries``.  In particular, a bounded
search cannot claim a universal property.  Callers must run ``check_witness`` on SAT before
using a counterexample, and an UNSAT result from bounded mode is provenance only.

Marabou is optional.  Importing this module does not import ``maraboupy`` or any other verifier
package; the only runtime dependency is the pinned executable named by the caller.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reasonsmith.neural_queries import CompiledNeuralQuery, QueryShape, VerifierRun

# The soundness gate did not admit complete mode on the pinned open-source CPU path. Keep the
# constant in one place so a future complete-mode integration has an explicit review point.
MARABOU_VERSION = "2.0.0"
VNNLIB_VERSION = "1.0"
BOUNDED_SEARCH_MODE = "bounded-search"
COMPLETE_MODE = "complete-verification"

# This is a conservative profile, not a promise that every Marabou build supports every listed
# operation.  A caller can narrow it further with ``supported_operators``.  Unsupported graph
# operators are refused before a child process is started.
DEFAULT_SUPPORTED_OPERATORS = frozenset(
    {
        "Abs",
        "Add",
        "Clip",
        "Concat",
        "Constant",
        "Div",
        "Flatten",
        "Gather",
        "Gemm",
        "Identity",
        "LeakyRelu",
        "MatMul",
        "Max",
        "Min",
        "Mul",
        "Neg",
        "Relu",
        "Reshape",
        "Shape",
        "Sigmoid",
        "Squeeze",
        "Sub",
        "Tanh",
        "Unsqueeze",
    }
)

_VERSION_RE = re.compile(r"(?<![0-9])([0-9]+(?:\.[0-9]+)+)(?![0-9])")
_NUMBER_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_ASSIGNMENT_RE = re.compile(
    rf"^\s*(?:input\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*({_NUMBER_RE}|nan|inf|-inf)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Limits applied to the verifier child where the host OS supports them."""

    cpu_seconds: int | None = None
    memory_bytes: int | None = None
    gpu: str | None = None

    def __post_init__(self) -> None:
        if self.cpu_seconds is not None and (
            isinstance(self.cpu_seconds, bool)
            or not isinstance(self.cpu_seconds, int)
            or self.cpu_seconds < 1
        ):
            raise ValueError("cpu_seconds must be a positive integer or None")
        if self.memory_bytes is not None and (
            isinstance(self.memory_bytes, bool)
            or not isinstance(self.memory_bytes, int)
            or self.memory_bytes < 1
        ):
            raise ValueError("memory_bytes must be a positive integer or None")
        if self.gpu is not None and (not isinstance(self.gpu, str) or not self.gpu):
            raise ValueError("gpu must be a non-empty string or None")

    def as_dict(self, timeout: float | None) -> dict[str, Any]:
        return {
            "cpu_seconds": self.cpu_seconds,
            "memory_bytes": self.memory_bytes,
            "gpu": self.gpu,
            "wall_seconds": timeout,
            "enforcement": {
                "cpu": "RLIMIT_CPU"
                if self.cpu_seconds is not None and os.name == "posix"
                else "none",
                "memory": "RLIMIT_AS"
                if self.memory_bytes is not None and os.name == "posix"
                else "none",
                "wall": "Popen.communicate(timeout=...)" if timeout is not None else "none",
                "gpu": "declaration-only" if self.gpu is not None else "none",
            },
        }


def _limit_child(limits: ResourceLimits) -> None:
    """Install POSIX resource limits in the child; harmlessly unavailable elsewhere."""
    if os.name != "posix":
        return
    import resource

    if limits.cpu_seconds is not None:
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    if limits.memory_bytes is not None and hasattr(resource, "RLIMIT_AS"):
        resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _version_from_output(output: str) -> str | None:
    match = _VERSION_RE.search(output)
    return match.group(1) if match else None


def _status_from_output(output: str) -> str | None:
    # Check UNSAT before SAT because the latter is a substring of the former.
    for status in ("unsat", "sat", "unknown", "timeout"):
        if re.search(rf"(?im)^\s*(?:result\s*[:=]\s*)?{status}\s*$", output):
            return status
    # Some builds prefix their one-word result with a short diagnostic.  Keep this fallback
    # line-oriented so an incidental word in a stack trace cannot become a verdict.
    for line in output.splitlines():
        token = line.strip().lower().rstrip(".")
        if token in ("unsat", "sat", "unknown", "timeout"):
            return token
    return None


def _assignment_from_output(
    output: str, declared: set[str]
) -> tuple[dict[str, float] | None, str | None]:
    assignment: dict[str, float] = {}
    for match in _ASSIGNMENT_RE.finditer(output):
        name, raw = match.groups()
        if name not in declared:
            continue
        try:
            value = float(raw)
        except ValueError:
            return None, f"malformed numeric assignment for {name!r}"
        if not math.isfinite(value):
            return None, f"non-finite assignment for {name!r}"
        old = assignment.get(name)
        if old is not None and old != value:
            return None, f"conflicting assignments for {name!r}"
        assignment[name] = value
    if not assignment:
        return None, "SAT output did not contain a declared assignment"
    return assignment, None


def _declared_variables(vnnlib: str) -> set[str]:
    return set(re.findall(r"\(declare-fun\s+([A-Za-z_][A-Za-z0-9_.-]*)\s+\(\)\s+Real\)", vnnlib))


def _kill_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - Windows CI does not exercise this branch.
            process.kill()
    except (OSError, AttributeError):
        process.kill()


class MarabouVerifier:
    """Pinned, bounded-search Marabou adapter implementing ``NeuralVerifier``.

    The adapter accepts an executable (or argv prefix) instead of importing ``maraboupy``.  This
    keeps the base install free of Marabou and makes the subprocess boundary straightforward to
    mock.  ``complete-verification`` remains refused after the slice-4 gate failed; even a textual
    ``UNSAT`` from bounded mode is tagged provenance-only and must not be promoted by a caller.
    """

    name = "marabou"
    version = MARABOU_VERSION
    max_strength = "probed"
    marabou_version = MARABOU_VERSION
    vnnlib_version = VNNLIB_VERSION
    supported_artifact_schema_versions = (1,)
    supported_onnx_ir_versions = tuple(range(7, 14))
    supported_onnx_opsets = tuple(range(7, 22))
    supported_onnx_domains = ("", "ai.onnx")
    supported_dtypes = ("float32", "float64", "int32", "int64")
    supported_vnnlib_versions = (VNNLIB_VERSION,)
    supported_query_shapes = tuple(item.value for item in QueryShape)
    modes = frozenset((BOUNDED_SEARCH_MODE,))

    def __init__(
        self,
        executable: str | Sequence[str] = "marabou",
        *,
        expected_version: str = MARABOU_VERSION,
        version_args: Sequence[str] = ("--version",),
        extra_args: Sequence[str] = (),
        resource_limits: ResourceLimits | None = None,
        supported_operators: Sequence[str] = DEFAULT_SUPPORTED_OPERATORS,
        check_version: bool = True,
    ) -> None:
        if isinstance(executable, str):
            executable = (executable,)
        self.executable = tuple(executable)
        if not self.executable or any(
            not isinstance(item, str) or not item for item in self.executable
        ):
            raise ValueError("Marabou executable must be a non-empty argv or path")
        if not expected_version:
            raise ValueError("expected_version must be non-empty")
        self.expected_version = expected_version
        self.version_args = tuple(version_args)
        self.extra_args = tuple(extra_args)
        self.resource_limits = resource_limits or ResourceLimits()
        self.supported_operators = frozenset(supported_operators)
        self.check_version = check_version

    def _base_provenance(
        self, query: CompiledNeuralQuery, mode: str, timeout: float | None
    ) -> dict[str, Any]:
        return {
            "tool": self.name,
            "version": self.expected_version,
            "expected_version": self.expected_version,
            "vnnlib_version": self.vnnlib_version,
            "mode": mode,
            "configuration": {
                "executable": self.executable,
                "version_args": self.version_args,
                "extra_args": self.extra_args,
                "supported_operators": tuple(sorted(self.supported_operators)),
            },
            "resource_limits": self.resource_limits.as_dict(timeout),
            "hashes": {
                "model_sha256": query.model_sha256,
                "product_model_sha256": _sha256(query.product_model),
                "query_sha256": query.query_sha256,
                "vnnlib_sha256": _sha256(query.vnnlib),
            },
            "requires_replay": True,
            "verdict_eligible": False,
        }

    def _run_command(
        self, command: Sequence[str], cwd: Path, timeout: float | None
    ) -> tuple[str, str, int | None, str | None]:
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                start_new_session=(os.name == "posix"),
                preexec_fn=(lambda: _limit_child(self.resource_limits))
                if os.name == "posix"
                else None,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_process(process)
                stdout, stderr = process.communicate()
                return stdout, stderr, None, "timeout"
            return stdout, stderr, process.returncode, None
        except FileNotFoundError as exc:
            return "", str(exc), None, "crash"
        except OSError as exc:
            return "", str(exc), None, "crash"
        finally:
            # Duration is recorded by the caller from its own stable timestamps; this local
            # assignment intentionally keeps the process helper free of mutable run state.
            _ = started

    def _run_result(
        self,
        status: str,
        query: CompiledNeuralQuery,
        provenance: dict[str, Any],
        *,
        assignment: Mapping[str, Any] | None = None,
        diagnostic: str | None = None,
        version: str | None = None,
    ) -> VerifierRun:
        return VerifierRun(
            status,
            assignment=assignment,
            verifier=self.name,
            version=version or self.expected_version,
            diagnostic=diagnostic,
            provenance=provenance,
        )

    def verify(
        self,
        query: CompiledNeuralQuery,
        *,
        timeout: float | None = None,
        mode: str = BOUNDED_SEARCH_MODE,
    ) -> VerifierRun:
        provenance = self._base_provenance(query, mode, timeout)
        if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
            provenance["failure"] = "invalid_timeout"
            return self._run_result(
                "error", query, provenance, diagnostic="timeout must be finite and positive"
            )
        if mode != BOUNDED_SEARCH_MODE:
            provenance["failure"] = "complete_mode_not_admitted"
            return self._run_result(
                "unsupported",
                query,
                provenance,
                diagnostic=(
                    "complete mode is not admitted until the pinned slice-4 soundness gate passes"
                ),
            )
        try:
            query.validate()
        except Exception as exc:
            provenance["failure"] = "unsupported_query"
            return self._run_result("unsupported", query, provenance, diagnostic=str(exc))
        artifact = query.artifact
        if artifact.schema_version not in self.supported_artifact_schema_versions:
            provenance["failure"] = "unsupported_artifact_schema"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported artifact schema version"
            )
        if artifact.vnnlib_version not in self.supported_vnnlib_versions:
            provenance["failure"] = "unsupported_vnnlib_version"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported VNN-LIB version"
            )
        if query.shape.value not in self.supported_query_shapes:
            provenance["failure"] = "unsupported_query_shape"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported neural query shape"
            )
        if artifact.onnx_ir_version not in self.supported_onnx_ir_versions:
            provenance["failure"] = "unsupported_onnx_ir"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported ONNX IR version"
            )
        if any(
            binding.dtype not in self.supported_dtypes
            for binding in (*artifact.inputs, *artifact.outputs)
        ):
            provenance["failure"] = "unsupported_dtype"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported ONNX tensor dtype"
            )
        if any(
            domain not in self.supported_onnx_domains or version not in self.supported_onnx_opsets
            for domain, version in artifact.opset_imports
        ):
            provenance["failure"] = "unsupported_onnx_opset"
            return self._run_result(
                "unsupported", query, provenance, diagnostic="unsupported ONNX opset"
            )

        try:
            import onnx

            graph = onnx.load_model_from_string(query.product_model).graph
            operators = {node.op_type for node in graph.node}
        except Exception as exc:
            provenance["failure"] = "unsupported_query"
            return self._run_result(
                "unsupported", query, provenance, diagnostic=f"cannot inspect ONNX graph: {exc}"
            )
        unsupported = sorted(operators - self.supported_operators)
        if unsupported:
            provenance["failure"] = "unsupported_operator"
            provenance["unsupported_operators"] = tuple(unsupported)
            return self._run_result(
                "unsupported",
                query,
                provenance,
                diagnostic=f"unsupported ONNX operator(s): {', '.join(unsupported)}",
            )

        started = time.monotonic()
        deadline = None if timeout is None else started + timeout

        def remaining_timeout() -> float | None:
            if deadline is None:
                return None
            return max(0.0, deadline - time.monotonic())

        def budget_expired() -> bool:
            return deadline is not None and time.monotonic() >= deadline

        with tempfile.TemporaryDirectory(prefix="reasonsmith-marabou-") as raw_dir:
            workdir = Path(raw_dir)
            model_path = workdir / "query.onnx"
            vnnlib_path = workdir / "query.vnnlib"
            model_path.write_bytes(query.product_model)
            vnnlib_path.write_text(query.vnnlib, encoding="utf-8")
            provenance["hashes"]["model_file_sha256"] = _sha256(model_path.read_bytes())
            provenance["hashes"]["query_file_sha256"] = _sha256(vnnlib_path.read_bytes())

            observed_version = self.expected_version
            if self.check_version:
                remaining = remaining_timeout()
                if remaining is not None and remaining <= 0:
                    provenance["failure"] = "timeout"
                    provenance["duration_seconds"] = round(time.monotonic() - started, 6)
                    return self._run_result(
                        "timeout", query, provenance,
                        diagnostic="Marabou exceeded the wall-clock limit",
                    )
                version_out, version_err, version_code, version_failure = self._run_command(
                    (*self.executable, *self.version_args), workdir, remaining
                )
                version_text = version_out + "\n" + version_err
                observed_version = _version_from_output(version_text)
                provenance["version_probe"] = {
                    "command": (*self.executable, *self.version_args),
                    "returncode": version_code,
                    "stdout_sha256": _sha256(version_out),
                    "stderr_sha256": _sha256(version_err),
                }
                if budget_expired() and version_failure != "crash":
                    version_failure = "timeout"
                if version_failure is not None:
                    provenance["failure"] = version_failure
                    return self._run_result(
                        "timeout" if version_failure == "timeout" else "error",
                        query,
                        provenance,
                        diagnostic=version_err or version_failure,
                    )
                if version_code != 0 or observed_version is None:
                    provenance["failure"] = "version_drift"
                    return self._run_result(
                        "unsupported",
                        query,
                        provenance,
                        diagnostic="Marabou version probe was not a pinned release",
                    )
                provenance["observed_version"] = observed_version
                if observed_version != self.expected_version:
                    provenance["failure"] = "version_drift"
                    return self._run_result(
                        "unsupported",
                        query,
                        provenance,
                        diagnostic=(
                            f"expected Marabou {self.expected_version}, found {observed_version}"
                        ),
                        version=observed_version,
                    )

            command = (
                *self.executable,
                *self.extra_args,
                str(model_path),
                "--vnnlib",
                str(vnnlib_path),
            )
            provenance["configuration"]["command_shape"] = (
                command[0 : len(self.executable)]
                + self.extra_args
                + ("<model.onnx>", "--vnnlib", "<query.vnnlib>")
            )
            remaining = remaining_timeout()
            if remaining is not None and remaining <= 0:
                provenance["failure"] = "timeout"
                provenance["duration_seconds"] = round(time.monotonic() - started, 6)
                return self._run_result(
                    "timeout", query, provenance,
                    diagnostic="Marabou exceeded the wall-clock limit",
                    version=observed_version,
                )
            stdout, stderr, returncode, failure = self._run_command(command, workdir, remaining)
            provenance["duration_seconds"] = round(time.monotonic() - started, 6)
            if budget_expired() and failure != "crash":
                failure = "timeout"
            provenance["returncode"] = returncode
            provenance["hashes"]["stdout_sha256"] = _sha256(stdout)
            provenance["hashes"]["stderr_sha256"] = _sha256(stderr)
            provenance["stdout_bytes"] = len(stdout.encode())
            provenance["stderr_bytes"] = len(stderr.encode())
            combined = stdout + "\n" + stderr
            if failure == "timeout":
                provenance["failure"] = "timeout"
                return self._run_result(
                    "timeout",
                    query,
                    provenance,
                    diagnostic="Marabou exceeded the wall-clock limit",
                    version=observed_version,
                )
            if failure == "crash" or returncode not in (0, None):
                provenance["failure"] = "crash"
                return self._run_result(
                    "error",
                    query,
                    provenance,
                    diagnostic=stderr.strip() or "Marabou process failed",
                    version=observed_version,
                )
            status = _status_from_output(combined)
            if status is None:
                provenance["failure"] = "malformed_output"
                return self._run_result(
                    "error",
                    query,
                    provenance,
                    diagnostic="Marabou output contained no recognized status",
                    version=observed_version,
                )
            if status == "sat":
                assignment, assignment_error = _assignment_from_output(
                    combined, _declared_variables(query.vnnlib)
                )
                if assignment_error is not None or assignment is None:
                    provenance["failure"] = "malformed_assignment"
                    return self._run_result(
                        "error",
                        query,
                        provenance,
                        diagnostic=assignment_error,
                        version=observed_version,
                    )
                provenance["assignment_variables"] = tuple(sorted(assignment))
                provenance["requires_replay"] = True
                return self._run_result(
                    "sat", query, provenance, assignment=assignment, version=observed_version
                )
            if status == "unsat":
                # Bounded search has no independently checkable proof.  Preserve the raw status as
                # provenance for diagnostics, while making the non-verdict boundary explicit.
                provenance["unsat_semantics"] = "provenance-only; bounded search is not complete"
                provenance["verdict_eligible"] = False
            return self._run_result(status, query, provenance, version=observed_version)


MarabouAdapter = MarabouVerifier


__all__ = [
    "MARABOU_VERSION",
    "VNNLIB_VERSION",
    "BOUNDED_SEARCH_MODE",
    "COMPLETE_MODE",
    "DEFAULT_SUPPORTED_OPERATORS",
    "ResourceLimits",
    "MarabouVerifier",
    "MarabouAdapter",
]
