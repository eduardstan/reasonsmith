"""A language model writing adverse-action notices, checked on what it can and cannot expose.

What this module is for:
  A fourth self-contained system beside the three in `docs/three-systems.md`, and it is here to
  make a different point. Those three are about *rungs*: one duty, three surfaces, three strengths.
  This one is about the **axis underneath** — which duties a system can be answered on at all. See
  `docs/language-model.md`.

  The system is a hosted language model prompted to write the adverse-action notice for a credit
  file. It is checked against the whole `ecoa` pack, and the run comes back three different ways in
  one report:

    - `observed` on the two duties about the notice's timing and contents, read off its log;
    - `probed` on 12 CFR 1002.9(b)(2)'s specific-reasons duty, because the model can be called
      again on inputs it has never seen — a bounded search, carrying its budget;
    - `unattainable` on 12 CFR 1002.9(b)(2)'s *principal reasons* duty, naming the one signal it
      lacks, because that duty is measured from an inference artefact and a language model has
      none to give.

  The last of those is the finding. reasonsmith refuses the duty it cannot answer instead of
  passing the system on the easier one that shares the clause.

  Run: `python -m reasonsmith.examples.language_model_notices`

Connecting a real model:
  `NoticeWriter` takes one argument: a `complete(prompt: str) -> str`. `stub_model` below stands in
  for it so this file runs offline and its transcript is reproducible. A reader swaps in their own
  at the call site and nothing else changes::

      client = SomeVendorClient(api_key=...)             # not imported here, on purpose
      def complete(prompt: str) -> str:
          return client.responses(model="...", input=prompt).text
      sut = system_under_test(complete)

  There is no vendor SDK, no network and no client wrapper in this package, and there should not
  be: reasonsmith audits whatever answers that one call.

What a reader must not break:
  - `logic()` is `None` and stays `None`. A prompt is not a rule set and a decoder is not a formula;
    handing the solver a paraphrase of either would prove a property of the paraphrase. `proved` is
    structurally out of reach here, and `tests/test_docs_language_model.py` asserts that on the
    mechanism rather than on the printed word.
  - `DECLARED_CAPABILITIES` deliberately omits `artifact_logs_deleted_reason_count`. That signal is
    measured by switching a decision's enumerated reasons off one at a time, which needs an
    inference artefact this system does not have. Declaring it to make the row evaluate would put
    back exactly the substitution the duty exists to refuse — a notice that names *a* reason
    standing in for one that names *the* reasons.
  - `stub_model` must stay deterministic. The committed transcript is compared byte for byte, and a
    generated document that changes between runs is worse than no document.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from reasonsmith.adapters.callable import CallableAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

#: What kind of decision this system makes. Not inferred by reasonsmith from anything: an
#: undeclared system is never reported satisfied on a domain-limited duty, so the declaration is
#: what puts this system within the reach of the ECOA pack at all.
DECLARED_DOMAINS = ("consumer-credit",)

MODEL_VERSION = "notice-writer-2026.07.1"

#: The signals this system genuinely emits, declared by its author.
#: `artifact_logs_deleted_reason_count` is absent because there is nothing here to measure it from.
DECLARED_CAPABILITIES = {
    "applicant_id",
    "decision",
    "artifact_logs_decision_record",
    "artifact_logs_reason_explanation",
    "artifact_logs_notification_latency_days",
    "artifact_logs_counteroffer_not_accepted",
    "provenance_model_version",
    "scope_statements_local_vs_global",
}

#: The prompt the system sends for every file. It is part of the system, not of this harness.
PROMPT = """You are writing the adverse-action notice for a consumer credit application.
Applicant file:
- credit_score: {credit_score}
- debt_to_income: {debt_to_income}
- delinquencies_24m: {delinquencies_24m}
- credit_history_months: {credit_history_months}

Answer with exactly two lines:
DECISION: <adverse action|approved>
PRINCIPAL REASON: <one standardised ECOA reason code and its wording>
"""

#: The reason the notice states, in the order the deployed prompt's few-shot examples establish.
_LADDER: list[tuple[str, Callable[[dict[str, float]], bool]]] = [
    ("C02 excessive obligations in relation to income", lambda f: f["debt_to_income"] > 0.43),
    ("C04 delinquent past or present credit obligations", lambda f: f["delinquencies_24m"] > 0),
    ("C01 income insufficient for amount requested", lambda f: f["credit_score"] < 640),
    ("C03 length of credit history", lambda f: f["credit_history_months"] < 24),
]

_FIELD_RE = re.compile(r"^- ([a-z_0-9]+): (.*)$", re.MULTILINE)


def stub_model(prompt: str) -> str:
    """A deterministic stand-in for the hosted model, so this file runs offline.

    It reads the file out of the prompt the way the real decoder attends to it, and writes the
    notice the deployed prompt's examples ask for. Nothing about the audit depends on which of the
    two is behind the call.
    """
    fields: dict[str, float] = {}
    for name, raw in _FIELD_RE.findall(prompt):
        try:
            fields[name] = float(raw)
        except ValueError:
            fields[name] = 0.0

    reason = "C00 no adverse factor"
    decision = "approved"
    for wording, fires in _LADDER:
        try:
            hit = fires(fields)
        except KeyError:
            continue
        if hit:
            reason, decision = wording, "adverse action"
            break
    return f"DECISION: {decision}\nPRINCIPAL REASON: {reason}\n"


class NoticeWriter:
    """Prompts a language model for a notice and records what came back."""

    def __init__(self, complete: Callable[[str], str]):
        self.complete = complete

    def decide(self, case: dict[str, Any]) -> dict[str, Any]:
        file = {
            key: case.get(key, 0)
            for key in ("credit_score", "debt_to_income", "delinquencies_24m",
                        "credit_history_months")
        }
        answer = self.complete(PROMPT.format(**file))
        stated = dict(re.findall(r"^([A-Z ]+): (.*)$", answer, re.MULTILINE))
        return {
            **case,
            "decision": (
                "adverse_action" if stated.get("DECISION") == "adverse action" else "approved"
            ),
            "artifact_logs_decision_record": answer.strip(),
            "artifact_logs_reason_explanation": stated.get("PRINCIPAL REASON", ""),
            "artifact_logs_notification_latency_days": 12,
            "artifact_logs_counteroffer_not_accepted": 0.0,
            "provenance_model_version": MODEL_VERSION,
            "scope_statements_local_vs_global": (
                "local: the notice this generation wrote for this applicant; "
                "no claim about the model's other outputs"
            ),
        }


#: Files already notified in production. The probe perturbs these and replays the results.
NOTIFIED_FILES: list[dict[str, Any]] = [
    {
        "applicant_id": "APP-3301",
        "credit_score": 715,
        "debt_to_income": 0.21,
        "delinquencies_24m": 0,
        "credit_history_months": 96,
    },
    {
        "applicant_id": "APP-3302",
        "credit_score": 602,
        "debt_to_income": 0.48,
        "delinquencies_24m": 2,
        "credit_history_months": 19,
    },
]


def system_under_test(complete: Callable[[str], str] = stub_model) -> CallableAdapter:
    """The system as reasonsmith sees it: a callable model and a declared capability set."""
    sut = CallableAdapter(
        NoticeWriter(complete),
        declared_capabilities=DECLARED_CAPABILITIES,
        test_inputs=NOTIFIED_FILES,
    )
    sut.system_domains = DECLARED_DOMAINS
    return sut


def main() -> None:
    report = check_conformance(
        system_under_test(),
        load_pack("ecoa"),
        system_name="notice-writer (language model, called through one text completion)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
