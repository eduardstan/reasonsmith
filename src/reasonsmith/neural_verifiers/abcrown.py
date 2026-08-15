"""Out-of-process alpha-beta-CROWN adapter for neural verification.

The adapter is deliberately an oracle boundary: it returns :class:`VerifierRun`, never a
``RequirementResult``.  alpha-beta-CROWN has several result labels with different epistemic
meaning.  They are retained in provenance while the canonical status remains compatible with
``neural_queries.verify_query`` (unsafe labels are ``sat`` and safe labels are ``unsat``).

The pinned source used by this integration is the upstream ``abcrown`` 0.7.0 package at commit
``e5c7e17bf0488843acb77b7519f59876717a49f4``.  The package is optional and is never imported by
reasonsmith itself.
"""

from __future__ import annotations

import hashlib
import json
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

ABCROWN_VERSION = "0.7.0"
ABCROWN_COMMIT = "e5c7e17bf0488843acb77b7519f59876717a49f4"
VNNLIB_VERSION = "1.0"
BOUNDED_SEARCH_MODE = "bounded-search"
COMPLETE_MODE = "complete-verification"

# These are native labels documented/emitted by alpha-beta-CROWN.  Do not collapse them into a
# single "unsafe" or "safe" label: the native label is evidence about how the answer was obtained.
ABCROWN_NATIVE_STATUSES = frozenset(
    {
        "unsafe-pgd",
        "unsafe-bab",
        "unsafe",
        "falsified",
        "safe-incomplete",
        "complete-safe",
        "safe",
        "verified",
        "timeout",
        "unknown",
    }
)

# Canonical statuses are intentionally the existing VerifierRun vocabulary.  The third value says
# whether the native result is eligible to support a proved claim; the adapter still requires the
# explicit complete-mode admission gate before setting it.
ABCROWN_STATUS_MAP: dict[str, tuple[str, bool, str]] = {
    "unsafe-pgd": ("sat", False, "attack-witness"),
    "unsafe-bab": ("sat", False, "branch-and-bound-witness"),
    "unsafe": ("sat", False, "unsafe-witness"),
    "falsified": ("sat", False, "falsified-witness"),
    "safe-incomplete": ("unsat", False, "incomplete-bound"),
    "complete-safe": ("unsat", True, "complete-proof-candidate"),
    "safe": ("unsat", True, "complete-proof-candidate"),
    "verified": ("unsat", True, "complete-proof-candidate"),
    "timeout": ("timeout", False, "timeout"),
    "unknown": ("unknown", False, "unknown"),
}

# A conservative profile.  Unsupported operators are rejected before starting a child process.
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
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_ASSIGNMENT_RE = re.compile(
    rf"^\s*(?:input\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:=|:)\s*"
    rf"(?:tensor\(\s*)?({_NUMBER}|nan|inf|-inf)",
    re.I | re.M,
)
_RESULT_RE = re.compile(r"^\s*(?:result|status)\s*[:=]\s*([A-Za-z][A-Za-z0-9_-]*)\s*$", re.I | re.M)


def _sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _version_from_output(output: str) -> str | None:
    match = _VERSION_RE.search(output)
    return match.group(1) if match else None


def parse_abcrown_status(output: str) -> str | None:
    """Parse one native alpha-beta-CROWN result label from process output."""
    for match in _RESULT_RE.finditer(output):
        token = match.group(1).lower()
        if token in ABCROWN_NATIVE_STATUSES:
            return token
        if token in {"safe-complete", "complete"}:
            return "complete-safe"
    for line in output.splitlines():
        token = line.strip().lower().rstrip(".")
        if token in ABCROWN_NATIVE_STATUSES:
            return token
        if token in {"safe-complete", "complete"}:
            return "complete-safe"
    return None


def map_abcrown_status(native_status: str) -> tuple[str, bool, str]:
    """Return ``(VerifierRun status, candidate eligibility, semantic class)``.

    Native labels remain available through ``VerifierRun.provenance['native_status']``.  This
    explicit mapping prevents a safe-incomplete answer from being mistaken for complete-safe.
    """
    token = str(native_status).strip().lower()
    try:
        return ABCROWN_STATUS_MAP[token]
    except KeyError as exc:
        raise ValueError(f"unsupported alpha-beta-CROWN status {native_status!r}") from exc


def _declared_variables(vnnlib: str) -> set[str]:
    return set(re.findall(r"\(declare-fun\s+([A-Za-z_][A-Za-z0-9_.-]*)\s+\(\)\s+Real\)", vnnlib))


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
        if name in assignment and assignment[name] != value:
            return None, f"conflicting assignments for {name!r}"
        assignment[name] = value
    if not assignment:
        return None, "unsafe output did not contain a declared assignment"
    return assignment, None


def _kill_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover
            process.kill()
    except (OSError, AttributeError):
        process.kill()


@dataclass(frozen=True, slots=True)
class ABCROWNResourceLimits:
    cpu_seconds: int | None = None
    memory_bytes: int | None = None
    gpu: str | None = None

    def __post_init__(self) -> None:
        if self.cpu_seconds is not None and (
            isinstance(self.cpu_seconds, bool) or self.cpu_seconds < 1
        ):
            raise ValueError("cpu_seconds must be a positive integer or None")
        if self.memory_bytes is not None and (
            isinstance(self.memory_bytes, bool) or self.memory_bytes < 1
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


def _limit_child(limits: ABCROWNResourceLimits) -> None:
    if os.name != "posix":
        return
    import resource

    if limits.cpu_seconds is not None:
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    if limits.memory_bytes is not None and hasattr(resource, "RLIMIT_AS"):
        resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))


class ABCROWNVerifier:
    """Pinned alpha-beta-CROWN subprocess adapter.

    The current pinned install could not be admitted on the runner, so the default ceiling is
    ``probed``.  ``admit_complete=True`` is an explicit review gate and must only be used after the
    committed soundness corpus has passed for this exact commit/configuration.
    """

    name = "alpha-beta-crown"
    version = ABCROWN_VERSION
    commit = ABCROWN_COMMIT
    max_strength = "probed"
    modes = frozenset((BOUNDED_SEARCH_MODE,))
    supported_artifact_schema_versions = (1,)
    supported_vnnlib_versions = (VNNLIB_VERSION,)
    supported_query_shapes = tuple(item.value for item in QueryShape)
    supported_dtypes = ("float32", "float64", "int32", "int64")
    supported_onnx_domains = ("", "ai.onnx")

    def __init__(
        self,
        executable: str | Sequence[str] = "python",
        *,
        script: str = "complete_verifier/abcrown.py",
        expected_version: str = ABCROWN_VERSION,
        version_args: Sequence[str] = (
            "-c",
            "import importlib.metadata; print(importlib.metadata.version('abcrown'))",
        ),
        extra_args: Sequence[str] = (),
        configuration: Mapping[str, Any] | None = None,
        resource_limits: ABCROWNResourceLimits | None = None,
        supported_operators: Sequence[str] = DEFAULT_SUPPORTED_OPERATORS,
        check_version: bool = True,
        admit_complete: bool = False,
        working_directory: str | Path | None = None,
    ) -> None:
        self.executable = (executable,) if isinstance(executable, str) else tuple(executable)
        if not self.executable or any(not isinstance(x, str) or not x for x in self.executable):
            raise ValueError("alpha-beta-CROWN executable must be a non-empty argv or path")
        if not script:
            raise ValueError("alpha-beta-CROWN script must be non-empty")
        self.script = str(Path(script).expanduser().resolve())
        self.working_directory = (
            Path(working_directory or Path(self.script).parent.parent).expanduser().resolve()
        )
        self.expected_version = expected_version
        self.version_args = tuple(version_args)
        self.extra_args = tuple(extra_args)
        self.configuration = dict(configuration or {})
        self._reject_proprietary_configuration()
        self.resource_limits = resource_limits or ABCROWNResourceLimits()
        self.supported_operators = frozenset(supported_operators)
        self.check_version = check_version
        self.admit_complete = bool(admit_complete)
        if self.admit_complete:
            self.modes = frozenset((BOUNDED_SEARCH_MODE, COMPLETE_MODE))

    def _reject_proprietary_configuration(self) -> None:
        serialized = repr(self.configuration).lower() + " " + " ".join(self.extra_args).lower()
        for name in ("gurobi", "cplex"):
            if name in serialized and (
                "true" in serialized or "enable" in serialized or "use" in serialized
            ):
                raise ValueError(f"proprietary solver mode {name} is disabled")

    def _base_provenance(
        self, query: CompiledNeuralQuery, mode: str, timeout: float | None
    ) -> dict[str, Any]:
        return {
            "tool": self.name,
            "version": self.expected_version,
            "commit": self.commit,
            "expected_version": self.expected_version,
            "vnnlib_version": VNNLIB_VERSION,
            "mode": mode,
            "configuration": {
                "executable": self.executable,
                "script": self.script,
                "working_directory": str(self.working_directory),
                "version_args": self.version_args,
                "extra_args": self.extra_args,
                "settings": self.configuration,
                "proprietary_solvers": {"gurobi": False, "cplex": False},
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

    @staticmethod
    def _result(
        status: str, query: CompiledNeuralQuery, provenance: dict[str, Any], **kwargs: Any
    ) -> VerifierRun:
        kwargs.setdefault("version", provenance["version"])
        return VerifierRun(status, verifier="alpha-beta-crown", provenance=provenance, **kwargs)

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
            return self._result(
                "error", query, provenance, diagnostic="timeout must be finite and positive"
            )
        if mode not in self.modes:
            provenance["failure"] = "complete_mode_not_admitted"
            return self._result(
                "unsupported",
                query,
                provenance,
                diagnostic=(
                    "complete mode is not admitted until the alpha-beta-CROWN soundness gate passes"
                ),
            )
        try:
            query.validate()
            if query.artifact.schema_version not in self.supported_artifact_schema_versions:
                raise ValueError("unsupported artifact schema version")
            if query.artifact.vnnlib_version not in self.supported_vnnlib_versions:
                raise ValueError("unsupported VNN-LIB version")
            if query.shape.value not in self.supported_query_shapes:
                raise ValueError("unsupported neural query shape")
            import onnx

            graph = onnx.load_model_from_string(query.product_model).graph
            unsupported = sorted({node.op_type for node in graph.node} - self.supported_operators)
            if unsupported:
                provenance["failure"] = "unsupported_operator"
                provenance["unsupported_operators"] = tuple(unsupported)
                return self._result(
                    "unsupported",
                    query,
                    provenance,
                    diagnostic=f"unsupported ONNX operator(s): {', '.join(unsupported)}",
                )
        except Exception as exc:
            provenance["failure"] = "unsupported_query"
            return self._result("unsupported", query, provenance, diagnostic=str(exc))

        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="reasonsmith-abcrown-") as raw_dir:
            workdir = Path(raw_dir)
            model_path, vnnlib_path = workdir / "query.onnx", workdir / "query.vnnlib"
            config_path = workdir / "abcrown-config.yaml"
            model_path.write_bytes(query.product_model)
            vnnlib_path.write_text(query.vnnlib, encoding="utf-8")
            config = {
                "general": {
                    "device": "cpu",
                    "complete_verifier": "bab" if mode == COMPLETE_MODE else "auto",
                    "enable_incomplete_verification": mode != COMPLETE_MODE,
                },
                "attack": {"pgd_order": "skip"},
                **self.configuration,
            }
            if mode == COMPLETE_MODE:
                config["general"]["complete_verifier"] = "bab"
                config["general"]["enable_incomplete_verification"] = False
            config_path.write_text(json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
            provenance["hashes"]["config_sha256"] = _sha256(config_path.read_bytes())
            provenance["configuration"]["effective_config"] = config
            provenance["hashes"]["model_file_sha256"] = _sha256(model_path.read_bytes())
            provenance["hashes"]["query_file_sha256"] = _sha256(vnnlib_path.read_bytes())
            observed_version = self.expected_version
            if self.check_version:
                version_out, version_err, version_code, failure = self._run_command(
                    (*self.executable, *self.version_args), self.working_directory, timeout
                )
                observed_version = _version_from_output(version_out + "\n" + version_err)
                provenance["version_probe"] = {
                    "command": (*self.executable, *self.version_args),
                    "returncode": version_code,
                    "stdout_sha256": _sha256(version_out),
                    "stderr_sha256": _sha256(version_err),
                }
                if failure is not None:
                    provenance["failure"] = failure
                    return self._result(
                        "timeout" if failure == "timeout" else "error",
                        query,
                        provenance,
                        diagnostic=version_err or failure,
                    )
                if (
                    version_code != 0
                    or observed_version is None
                    or observed_version != self.expected_version
                ):
                    provenance["failure"] = "version_drift"
                    return self._result(
                        "unsupported",
                        query,
                        provenance,
                        diagnostic=(
                            f"expected alpha-beta-CROWN {self.expected_version}, "
                            f"found {observed_version}"
                        ),
                        version=observed_version or self.expected_version,
                    )
                provenance["observed_version"] = observed_version

            command = (
                *self.executable,
                self.script,
                *self.extra_args,
                "--config",
                str(config_path),
                *(("--no_incomplete",) if mode == COMPLETE_MODE else ()),
                "--onnx_path",
                str(model_path),
                "--vnnlib_path",
                str(vnnlib_path),
                "--device",
                "cpu",
            )
            provenance["configuration"]["command_shape"] = (
                *self.executable,
                "<abcrown.py>",
                *self.extra_args,
                "--config",
                "<abcrown-config.yaml>",
                *(("--no_incomplete",) if mode == COMPLETE_MODE else ()),
                "--onnx_path",
                "<model.onnx>",
                "--vnnlib_path",
                "<query.vnnlib>",
                "--device",
                "cpu",
            )
            stdout, stderr, returncode, failure = self._run_command(
                command, self.working_directory, timeout
            )
            provenance["duration_seconds"] = round(time.monotonic() - started, 6)
            provenance["returncode"] = returncode
            provenance["hashes"]["stdout_sha256"] = _sha256(stdout)
            provenance["hashes"]["stderr_sha256"] = _sha256(stderr)
            combined = stdout + "\n" + stderr
            if failure == "timeout":
                provenance["failure"] = "timeout"
                return self._result(
                    "timeout",
                    query,
                    provenance,
                    diagnostic="alpha-beta-CROWN exceeded the wall-clock limit",
                    version=observed_version,
                )
            if failure == "crash" or returncode not in (0, None):
                provenance["failure"] = "crash"
                return self._result(
                    "error",
                    query,
                    provenance,
                    diagnostic=stderr.strip() or "alpha-beta-CROWN process failed",
                    version=observed_version,
                )
            native = parse_abcrown_status(combined)
            if native is None:
                provenance["failure"] = "malformed_output"
                return self._result(
                    "error",
                    query,
                    provenance,
                    diagnostic="alpha-beta-CROWN output contained no recognized result",
                    version=observed_version,
                )
            canonical, candidate_eligible, semantic = map_abcrown_status(native)
            provenance.update(
                {
                    "native_status": native,
                    "semantic_status": semantic,
                    "candidate_verdict_eligible": candidate_eligible,
                }
            )
            if native in ("unsafe-pgd", "unsafe-bab", "unsafe", "falsified"):
                assignment, assignment_error = _assignment_from_output(
                    combined, _declared_variables(query.vnnlib)
                )
                if assignment_error is not None or assignment is None:
                    provenance["failure"] = "malformed_assignment"
                    return self._result(
                        "error",
                        query,
                        provenance,
                        diagnostic=assignment_error,
                        version=observed_version,
                    )
                provenance["assignment_variables"] = tuple(sorted(assignment))
                return self._result(
                    "sat", query, provenance, assignment=assignment, version=observed_version
                )
            if native in ("safe-incomplete", "safe", "verified", "complete-safe"):
                provenance["unsat_semantics"] = (
                    "incomplete bound; not a universal proof"
                    if native == "safe-incomplete"
                    else "external complete proof candidate"
                )
            provenance["verdict_eligible"] = (
                native in ("complete-safe", "safe", "verified")
                and mode == COMPLETE_MODE
                and self.admit_complete
            )
            return self._result(canonical, query, provenance, version=observed_version)


AlphaBetaCrownVerifier = ABCROWNVerifier
AlphaBetaCROWNVerifier = ABCROWNVerifier
ABCrownVerifier = ABCROWNVerifier
AlphaBetaCrownAdapter = ABCROWNVerifier
ABCrownAdapter = ABCROWNVerifier
ABCROWNAdapter = ABCROWNVerifier
ResourceLimits = ABCROWNResourceLimits
ALPHA_BETA_CROWN_VERSION = ABCROWN_VERSION
ALPHA_BETA_CROWN_COMMIT = ABCROWN_COMMIT

__all__ = [
    "ABCROWN_VERSION",
    "ABCROWN_COMMIT",
    "VNNLIB_VERSION",
    "BOUNDED_SEARCH_MODE",
    "COMPLETE_MODE",
    "ABCROWN_NATIVE_STATUSES",
    "ABCROWN_STATUS_MAP",
    "ABCROWNResourceLimits",
    "ResourceLimits",
    "ALPHA_BETA_CROWN_VERSION",
    "ALPHA_BETA_CROWN_COMMIT",
    "parse_abcrown_status",
    "map_abcrown_status",
    "ABCROWNVerifier",
    "ABCrownVerifier",
    "AlphaBetaCrownVerifier",
    "AlphaBetaCROWNVerifier",
    "AlphaBetaCrownAdapter",
    "ABCrownAdapter",
    "ABCROWNAdapter",
]
