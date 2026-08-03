"""A symbolic underwriting rule set, checked over every input its constraints admit.

What this module is for:
  One of three self-contained systems checked against the *same* binding duty — ECOA /
  Regulation B 12 CFR 1002.9(b)(2), "the statement of reasons ... must be specific and indicate
  the principal reason(s) for the adverse action". See `docs/three-systems.md` for the three
  side by side.

  This is the readable case. The underwriting policy *is* the system: a short ordered rule set
  over declared variables, with the admissible input space stated as constraints. Because the
  system can hand that over, the duty stops being a question about the decisions it happened to
  log.

  Run: `python -m reasonsmith.examples.symbolic_rules`

What a reader must not break:
  - `RULES` is the system's actual decision procedure, not a paraphrase of one. `RulesAdapter`
    executes these same statements in `decide()` and exposes them from `logic()`, sharing
    `reasonsmith.rulelang` with the solver, so a proof and a replay cannot come to be about
    different programs. Writing a tidier summary here and calling it the logic would produce a
    proof about the summary.
  - Every branch assigns `artifact_logs_reason_explanation` a non-blank string **naming a factor**.
    Both halves matter, because the duty checks both: that a statement was made at all, and that it
    is not one of the two the clause itself calls insufficient — resting on the creditor's internal
    standards or policies, or on a failure to achieve a qualifying score. The solver checks that
    over every input `CONSTRAINTS` admits, not over `TEST_INPUTS`, which only supply a decision
    trace for the weaker rungs to fall back on. Adding a branch that leaves the reason unset, sets
    it blank, or writes one of those forbidden statements turns the verdict to `violated` with a
    counterexample, which is the tool working, not failing. The reason codes below are the
    standardised ECOA ones precisely because they name factors.
  - `CONSTRAINTS` bound the input space the proof quantifies over, so they are part of what the
    verdict claims. Widening them weakens nothing; narrowing them to dodge a counterexample would
    make the proof true of a system nobody deployed.
  - The rules that carry this system past the *state* duties and into the two `temporal` ones —
    the notification block and the margin block — are ordinary rules and are held to the same bar.
    Two of them state a policy commitment rather than measure anything, and a reader must be able
    to see which:
      * `notification_queue_days` is a free input the system's own operations bound
        (`CONSTRAINTS`: at most a seven-day batch window), and the notice lands a day after the
        batch runs. The proof of 12 CFR 1002.9(a)(1) is exactly as good as that bound: widen it to
        `<= 45` and the duty comes back `violated` with a counterexample, which is the tool
        working. No engine checks that the deployed batch honours the seven days.
      * `artifact_logs_decision_margin` is the distance the deciding factor stands from *its own*
        threshold, in that factor's own units, because each branch is decided by one factor. An
        approval has no adverse factor, so it states the credit score's distance from the score
        threshold; that choice is this example's, not a fact about margins.
      * `scope_statements_declared_deviation` is `0.0` because an exact rule set approximates
        nothing. It is a self-declaration and no engine verifies it — see `docs/semantics.md` §3,
        *the first shipped duty that reads a declared approximation error*.
"""

from __future__ import annotations

from dataclasses import replace

from reasonsmith.adapters.rules import RulesAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

#: The duty all three systems in `reasonsmith.examples` are checked against. Binding, limited to no
#: regulatory class, and limited to the consumer-credit decision domain — which all three of these
#: systems are in, and which each of them declares below through `system_domains`. A system that
#: declared nothing would be reported not applicable on this duty rather than judged on its trace.
REQUIREMENT_ID = "ecoa_reg_b_1002_9_b_2_specific_reasons"

#: What kind of decision this system makes. Not inferred by reasonsmith from anything: an
#: undeclared system is never reported satisfied on a domain-limited duty, so the declaration is
#: what puts this system within the duty's reach at all.
DECLARED_DOMAINS = ("consumer-credit",)

#: The underwriting policy, in execution order. Reason codes are the standardised ECOA ones.
RULES = [
    "over_leveraged = debt_to_income > 0.43",
    "thin_file = credit_history_months < 24",
    "delinquent = delinquencies_24m > 0",
    "low_score = credit_score < 640",
    "adverse_action = over_leveraged or thin_file or delinquent or low_score",
    (
        "if over_leveraged:\n"
        '    artifact_logs_reason_explanation = '
        '"C02 excessive obligations in relation to income"\n'
        "elif delinquent:\n"
        '    artifact_logs_reason_explanation = '
        '"C04 delinquent past or present credit obligations"\n'
        "elif low_score:\n"
        '    artifact_logs_reason_explanation = '
        '"C01 income insufficient for amount requested"\n'
        "elif thin_file:\n"
        '    artifact_logs_reason_explanation = "C03 length of credit history"\n'
        "else:\n"
        '    artifact_logs_reason_explanation = "C00 no adverse factor"\n'
    ),
    (
        "if adverse_action:\n"
        '    artifact_logs_decision_record = "adverse action taken on this application"\n'
        "else:\n"
        '    artifact_logs_decision_record = "credit granted on this application"\n'
    ),
    # The notice goes out one day after the nightly batch that queues it, and the batch window is
    # bounded in CONSTRAINTS. No counteroffer is ever made by this policy, so 1002.9(a)(1)(iv) —
    # the only branch the 90-day deadline reaches — never applies to it.
    "artifact_logs_notification_latency_days = notification_queue_days + 1",
    "artifact_logs_counteroffer_not_accepted = 0.0",
    # The margin of this decision from the threshold that decided it, in that factor's own units.
    (
        "if over_leveraged:\n"
        "    artifact_logs_decision_margin = debt_to_income - 0.43\n"
        "elif delinquent:\n"
        "    artifact_logs_decision_margin = delinquencies_24m\n"
        "elif low_score:\n"
        "    artifact_logs_decision_margin = 640 - credit_score\n"
        "elif thin_file:\n"
        "    artifact_logs_decision_margin = 24 - credit_history_months\n"
        "else:\n"
        "    artifact_logs_decision_margin = credit_score - 640\n"
    ),
    "scope_statements_declared_deviation = 0.0",
    'provenance_model_version = "underwriting-rules-2026.05.0"',
    'scope_statements_local_vs_global = "global: the rule set below decided this application"',
    (
        "scope_statements_approximation_vs_guarantee = "
        '"guarantee: these rules are the decision procedure, not an approximation of one"'
    ),
]

#: Declared types for every variable the rules read or write. The solver reasons over these, and
#: together with the *direction* declaration they say which names this system is answerable about.
#: `RulesAdapter` derives that direction from `RULES` — the assignment targets are what this system
#: computes — so the five names below that no rule assigns are the inputs the application supplies:
#: `credit_score`, `debt_to_income`, `delinquencies_24m`, `credit_history_months` and
#: `notification_queue_days`. A name in neither list is one this system has no notion of, and a
#: property reading one is refused a proof rather than answered from a constant the solver invented
#: (`docs/semantics.md` §3.5).
VARIABLES = {
    "credit_score": "int",
    "debt_to_income": "real",
    "delinquencies_24m": "int",
    "credit_history_months": "int",
    "notification_queue_days": "int",
    "over_leveraged": "bool",
    "thin_file": "bool",
    "delinquent": "bool",
    "low_score": "bool",
    "adverse_action": "bool",
    "artifact_logs_reason_explanation": "str",
    "artifact_logs_decision_record": "str",
    "artifact_logs_notification_latency_days": "int",
    "artifact_logs_counteroffer_not_accepted": "real",
    "artifact_logs_decision_margin": "real",
    "scope_statements_declared_deviation": "real",
    "provenance_model_version": "str",
    "scope_statements_local_vs_global": "str",
    "scope_statements_approximation_vs_guarantee": "str",
}

#: The inputs the system admits. The proof quantifies over exactly these, and no further.
CONSTRAINTS = [
    "credit_score >= 300",
    "credit_score <= 850",
    "debt_to_income >= 0.0",
    "debt_to_income <= 1.0",
    "delinquencies_24m >= 0",
    "credit_history_months >= 0",
    "notification_queue_days >= 0",
    "notification_queue_days <= 7",
]

#: A handful of applications, so the weaker rungs have a trace to read if the proof rung ever
#: establishes nothing. They are not what the proof is about.
TEST_INPUTS = [
    {
        "credit_score": 715,
        "debt_to_income": 0.21,
        "delinquencies_24m": 0,
        "credit_history_months": 96,
        "notification_queue_days": 1,
    },
    {
        "credit_score": 602,
        "debt_to_income": 0.48,
        "delinquencies_24m": 2,
        "credit_history_months": 19,
        "notification_queue_days": 6,
    },
]


def system_under_test() -> RulesAdapter:
    """The system as reasonsmith sees it: exposed logic, and a capability set declared with it."""
    sut = RulesAdapter(
        rules=RULES,
        variables=VARIABLES,
        constraints=CONSTRAINTS,
        declared_capabilities={
            "decision",
            "adverse_action",
            "artifact_logs_reason_explanation",
            "artifact_logs_decision_record",
            "artifact_logs_notification_latency_days",
            "artifact_logs_counteroffer_not_accepted",
            "artifact_logs_decision_margin",
            "scope_statements_declared_deviation",
            "provenance_model_version",
            "scope_statements_local_vs_global",
            "scope_statements_approximation_vs_guarantee",
        },
        test_inputs=TEST_INPUTS,
    )
    sut.system_domains = DECLARED_DOMAINS
    return sut


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
        system_name="underwriting-rules (symbolic, logic exposed)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
