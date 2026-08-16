"""A tiny credit classifier whose decisions are backed by its packaged ONNX artefact.

Unlike :mod:`reasonsmith.examples.neural_scorer`, this system exposes the model that produced its
records.  The ONNX bytes, coordinate maps, decoder, and finite input domain are therefore the
objects compiled into the external verifier query; no reason count or fairness result is declared
by the system itself.

Run with the neural extra installed::

    python -m reasonsmith.examples.onnx_credit_scorer

The command invokes the optional Marabou subprocess boundary.  A missing verifier, unsupported
operator, timeout, or bounded ``unsat`` remains an oracle outcome and is never printed as an
observed or proved conformance verdict.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from reasonsmith.neural import DeclaredInputSpace, OnnxArtifact
from reasonsmith.neural_queries import (
    NeuralVerifier,
    OracleCheck,
    VerifierRun,
    compile_counterfactual_query,
    verify_query,
)
from reasonsmith.spec import load_pack

REQUIREMENT_ID = "ecoa_reg_b_1002_4_a_no_disparate_treatment"
OUTCOME_SIGNAL = "artifact_logs_decision_record"
PROTECTED_SIGNAL = "applicant_prohibited_basis"
MODEL_ID = "tiny-credit-onnx-1"

# A two-input Gemm followed by Sigmoid: risk = sigmoid(score + protected_basis).  Keeping the
# serialized model literal makes the wheel, decision records, and compiled product-query hashes
# reproducible without generating a different protobuf at import time.
_MODEL_B64 = (
    "CA06uQEKJgoIZmVhdHVyZXMKB3dlaWdodHMKBGJpYXMSBWxvZ2l0IgRHZW1tChYKBWxvZ2l0"
    "EgRyaXNrIgdTaWdtb2lkEhZ0aW55LWNyZWRpdC1jbGFzc2lmaWVyKhkIAggBEAEiCAAAgD8A"
    "AIA/Qgd3ZWlnaHRzKhAIARABIgQAAAAAQgRiaWFzWhoKCGZlYXR1cmVzEg4KDAgBEggKAggB"
    "CgIIAmIWCgRyaXNrEg4KDAgBEggKAggBCgIIAUIECgAQDQ=="
)
MODEL_BYTES = base64.b64decode(_MODEL_B64)
MODEL_SHA256 = "1ccddebf24b161ae3bf0852e738c2802fd39b6aa82a723b9241d5919c2145212"
QUERY_SHA256 = "69c898875bcaab7a22767dd643dc94d1dd92b6041521f090b9951eb43979f55b"

INPUT_SPACE = DeclaredInputSpace(
    [
        {"signal": "score", "type": "real", "lower": -1.0, "upper": 1.0},
        {
            "signal": PROTECTED_SIGNAL,
            "type": "categorical",
            "lower": 0,
            "upper": 1,
            "values": [0, 1],
        },
    ],
    outcomes={OUTCOME_SIGNAL: "decision"},
)


def _artifact() -> OnnxArtifact:
    return OnnxArtifact(
        model=MODEL_BYTES,
        model_sha256=MODEL_SHA256,
        inputs=[
            {
                "name": "features",
                "signal_map": {"score": 0, PROTECTED_SIGNAL: 1},
            }
        ],
        outputs=[
            {
                "name": "risk",
                "signal_map": {OUTCOME_SIGNAL: 0},
                "decoder": {
                    OUTCOME_SIGNAL: {
                        "threshold": 0.6,
                        "low": "approved",
                        "high": "adverse_action",
                        "tie": "approved",
                    }
                },
            }
        ],
        input_space=INPUT_SPACE,
        deployed_model_id=MODEL_ID,
        preprocessing="included",
        postprocessing="included",
    )


@dataclass(frozen=True)
class TinyOnnxCreditSUT:
    """The SUT surface: trace, replay, input domain, and model-global ONNX artefact."""

    _artifact: OnnxArtifact | None

    system_domains = ("consumer-credit",)

    def capabilities(self) -> set[str]:
        return {"score", OUTCOME_SIGNAL}

    def logic(self) -> None:
        return None

    def input_space(self) -> DeclaredInputSpace:
        return INPUT_SPACE

    def artifact(self, decision: Mapping[str, Any] | None = None) -> OnnxArtifact | None:
        return self._artifact if decision is None else None

    def decide(self, case: Mapping[str, Any]) -> dict[str, Any]:
        if self._artifact is None:
            raise ValueError("the deployed ONNX artifact is unavailable")
        import numpy as np
        from onnx.reference import ReferenceEvaluator

        values = np.asarray(
            [[float(case["score"]), float(case[PROTECTED_SIGNAL])]], dtype=np.float32
        )
        evaluated = ReferenceEvaluator(self._artifact.model).run(None, {"features": values})
        risk = float(evaluated[0][0, 0])
        decision = "approved" if risk <= 0.6 else "adverse_action"
        return {**case, "risk": risk, OUTCOME_SIGNAL: decision, "decision": decision}

    def decisions(self) -> list[dict[str, Any]]:
        return [
            self.decide({"score": 0.0, PROTECTED_SIGNAL: protected})
            for protected in (0, 1)
        ]


def system_under_test() -> TinyOnnxCreditSUT:
    return TinyOnnxCreditSUT(_artifact())


def compile_pack_query(sut: TinyOnnxCreditSUT):
    """Compile the shipped ECOA counterfactual duty against the exposed model artefact."""
    requirement = load_pack("ecoa").get_requirement(REQUIREMENT_ID)
    if requirement.formalism != "counterfactual":
        raise ValueError(f"{REQUIREMENT_ID} is no longer a counterfactual duty")
    artifact = sut.artifact(None)
    if artifact is None:
        raise ValueError("the SUT exposes no model-global ONNX artifact")
    query = compile_counterfactual_query(
        artifact,
        protected_signal=PROTECTED_SIGNAL,
        outcome_signal=OUTCOME_SIGNAL,
    )
    return replace(query, metadata={**query.metadata, "requirement_id": requirement.id})


def verify_pack_duty(sut: TinyOnnxCreditSUT, verifier: NeuralVerifier) -> OracleCheck:
    """Run the external oracle and replay any SAT witness through both model and SUT."""
    try:
        query = compile_pack_query(sut)
    except Exception as exc:
        return OracleCheck(VerifierRun("error", diagnostic=f"artifact unavailable: {exc}"))
    return verify_query(query, verifier, sut_replay=sut.decide)


def main() -> None:
    from reasonsmith.neural_verifiers import MarabouVerifier

    sut = system_under_test()
    query = compile_pack_query(sut)
    check = verify_pack_duty(sut, MarabouVerifier())
    print(f"requirement: {REQUIREMENT_ID}")
    print(f"model_sha256: {sut.artifact(None).model_sha256}")  # type: ignore[union-attr]
    print(f"query_sha256: {query.query_sha256}")
    print(f"oracle_status: {check.run.status}")
    print(f"witness_replayed: {bool(check.witness and check.witness.valid)}")
    if check.run.diagnostic:
        print(f"diagnostic: {check.run.diagnostic}")


if __name__ == "__main__":
    main()
