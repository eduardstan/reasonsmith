"""A scikit-learn credit classifier wrapped for reasonsmith auditing.

What this module is for:
  This is a worked example of bringing a mainstream machine-learning model through the
  reasonsmith audit boundary. The model is a real scikit-learn LogisticRegression instance,
  but reasonsmith only sees the model's predictions through CallableAdapter.

  The model is deterministic and self-contained: its coefficients are fixed directly, so
  importing this module performs no training, network access, or dataset download.

What a reader must not break:
  - The model is replayable through ``predict()``, so the strongest evidence available is
    ``probed``. It does not expose ``logic()``, so the example must not claim formal proof
    over the model's learned parameters.
  - The capability declarations describe only fields actually emitted by the model wrapper.
  - The fixture inputs are frozen and intentionally small so the example remains reproducible.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

REQUIREMENT_ID = "ecoa_reg_b_1002_9_b_2_specific_reasons"

DECLARED_DOMAINS = ("consumer-credit",)

MODEL_VERSION = "sklearn-logistic-regression-1.0"

# Frozen inputs used by the active probe. No dataset is downloaded or generated at runtime.
TEST_INPUTS: list[dict[str, Any]] = [
    {
        "applicant_id": "APP-3101",
        "income": 90000.0,
        "debt_to_income": 0.18,
        "credit_score": 760.0,
    },
    {
        "applicant_id": "APP-3102",
        "income": 42000.0,
        "debt_to_income": 0.52,
        "credit_score": 590.0,
    },
]


def _build_model() -> LogisticRegression:
    """Build the frozen scikit-learn model without fitting or external data."""
    model = LogisticRegression()
    model.classes_ = np.array([0, 1])
    model.coef_ = np.array([[0.00002, 3.0, -0.015]])
    model.intercept_ = np.array([-1.0])
    model.n_features_in_ = 3
    return model


class SklearnCreditModel:
    """Wrap a frozen scikit-learn classifier and return audit-ready decision records."""

    def __init__(self) -> None:
        self.model = _build_model()

    def predict(self, case: dict[str, Any]) -> dict[str, Any]:
        features = [[
            float(case["income"]),
            float(case["debt_to_income"]),
            float(case["credit_score"]),
        ]]

        prediction = int(self.model.predict(features)[0])

        contributions = self.model.coef_[0] * np.asarray(features[0])

        if prediction == 1:
            reason_index = int(np.argmax(contributions))
        else:
            reason_index = int(np.argmin(contributions))

        reason_by_feature = {
            0: "C01 income insufficient for amount requested",
            1: "C02 excessive obligations in relation to income",
            2: "C04 insufficient credit history",
        }

        reason = reason_by_feature[reason_index]

        return {
            **case,
            "decision": "adverse_action" if prediction == 1 else "approved",
            "artifact_logs_reason_explanation": reason,
            "provenance_model_version": MODEL_VERSION,
            "scope_statements_local_vs_global": (
                "local: prediction for this applicant only"
            ),
        }


def system_under_test() -> CallableAdapter:
    """Return the scikit-learn model through reasonsmith's callable adapter."""
    sut = CallableAdapter(
        SklearnCreditModel(),
        declared_capabilities={
            "applicant_id",
            "decision",
            "provenance_model_version",
            "scope_statements_local_vs_global",
            "artifact_logs_reason_explanation",
        },
        test_inputs=TEST_INPUTS,
    )
    sut.system_domains = DECLARED_DOMAINS
    return sut


def main() -> None:
    pack = load_pack("ecoa")
    one_duty = replace(
        pack,
        id=f"{pack.id}:{REQUIREMENT_ID}",
        requirements=(pack.get_requirement(REQUIREMENT_ID),),
    )

    report = check_conformance(
        system_under_test(),
        one_duty,
        system_name="scikit-learn logistic regression credit model",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
