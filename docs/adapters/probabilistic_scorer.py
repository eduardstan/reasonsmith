"""A probabilistic credit scorer that can be re-run on a perturbed input, but not reasoned about.

What this module is for:
  One of three self-contained systems checked against the *same* binding duty — ECOA /
  Regulation B 12 CFR 1002.9(b)(2), "the statement of reasons ... must be specific and indicate
  the principal reason(s) for the adverse action". See `docs/three-systems.md` for the three
  side by side.

  This is the middle case. A naive-Bayes style scorer accumulates log-odds contributions from a
  handful of factors, thresholds the posterior, and names as the principal reason whichever factor
  pushed hardest against the applicant. It lives in this process, so the auditor can hand it an
  input it has never seen and watch what it does.

  Run: `python docs/adapters/probabilistic_scorer.py`

What a reader must not break:
  - The model is reachable (`predict(case)`, the scikit-learn spelling `CallableAdapter` already
    dispatches to) but not readable. `logic()` stays unexposed because there is no rule set here:
    the posterior is arithmetic over calibrated weights, and handing the solver a hand-written
    paraphrase of it would prove a property of the paraphrase. So the ladder in
    `report._engine_ladder` finds `decide()` and stops there, and the strongest evidence is
    `probed` — a bounded search, carrying the budget that produced it into every rendering.
    Why this matters: `probed` is the rung that is easiest to read as `proved` and is not.
    The transcript prints the trial count, the seed, the strategy and the input space precisely
    so nobody has to take the verdict on trust.
  - `LOG_ODDS` and `THRESHOLD` are the model. `predict` must write a reason on every path it can
    take, including approval, or the probe finds a counterexample — which is the correct outcome,
    not a bug to work around.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

#: The duty all three systems in `docs/adapters/` are checked against. Binding, and limited to no
#: regulatory class, so it reaches every system without a declared scope.
REQUIREMENT_ID = "ecoa_reg_b_1002_9_b_2_specific_reasons"

MODEL_VERSION = "bayes-risk-2026.04.7"

#: Calibrated log-odds contribution per factor, and the ECOA reason code each one maps to. A
#: positive contribution is evidence against the applicant.
LOG_ODDS: dict[str, tuple[float, str]] = {
    "debt_to_income": (2.4, "C02 excessive obligations in relation to income"),
    "delinquencies_24m": (1.1, "C04 delinquent past or present credit obligations"),
    "credit_history_months": (-0.011, "C03 length of credit history"),
    "credit_score": (-0.009, "C01 income insufficient for amount requested"),
}

#: Posterior probability of default above which the application is declined.
THRESHOLD = 0.5

#: Applications already scored in production. The probe perturbs these and replays the results.
SCORED_APPLICATIONS: list[dict[str, Any]] = [
    {
        "applicant_id": "APP-2101",
        "credit_score": 715,
        "debt_to_income": 0.21,
        "delinquencies_24m": 0,
        "credit_history_months": 96,
    },
    {
        "applicant_id": "APP-2102",
        "credit_score": 602,
        "debt_to_income": 0.48,
        "delinquencies_24m": 2,
        "credit_history_months": 19,
    },
]


class BayesRiskScorer:
    """Accumulates log-odds per factor and reports the factor that dominated the outcome."""

    def __init__(self, intercept: float = -1.8):
        self.intercept = intercept

    def predict(self, case: dict[str, Any]) -> dict[str, Any]:
        contributions = {
            factor: weight * float(case.get(factor, 0) or 0)
            for factor, (weight, _reason) in LOG_ODDS.items()
        }
        log_odds = self.intercept + sum(contributions.values())
        posterior = 1.0 / (1.0 + 2.718281828459045 ** (-log_odds))
        declined = posterior >= THRESHOLD

        # The principal reason is the factor that pushed hardest in the direction of the outcome;
        # on approval, the factor that pushed hardest in the applicant's favour.
        pick = max if declined else min
        principal = pick(contributions, key=lambda factor: contributions[factor])

        return {
            **case,
            "decision": "adverse_action" if declined else "approved",
            "posterior_default": round(posterior, 6),
            "artifact_logs_reason_explanation": (
                LOG_ODDS[principal][1]
                if declined
                else f"C00 no adverse factor; strongest favourable factor {principal}"
            ),
            "provenance_model_version": MODEL_VERSION,
            "scope_statements_local_vs_global": (
                "local: log-odds attribution for this applicant only"
            ),
        }


def system_under_test() -> CallableAdapter:
    """The system as reasonsmith sees it: a replayable model and a declared capability set."""
    return CallableAdapter(
        BayesRiskScorer(),
        declared_capabilities={
            "applicant_id",
            "decision",
            "posterior_default",
            "artifact_logs_reason_explanation",
            "provenance_model_version",
            "scope_statements_local_vs_global",
        },
        test_inputs=SCORED_APPLICATIONS,
    )


def main() -> None:
    pack = load_pack("ecoa")
    # One duty, named in the report's own pack line, so no reader mistakes this run for the whole
    # ECOA pack. The requirement itself is the shipped one, unmodified.
    one_duty = replace(
        pack,
        id=f"{pack.id}:{REQUIREMENT_ID}",
        requirements=(pack.get_requirement(REQUIREMENT_ID),),
    )
    report = check_conformance(
        system_under_test(),
        one_duty,
        system_name="bayes-risk (probabilistic, replayable in-process)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
