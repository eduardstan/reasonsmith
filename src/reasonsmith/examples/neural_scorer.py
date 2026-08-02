"""A neural credit scorer, audited from the only thing it exposes: its decision log.

What this module is for:
  One of three self-contained systems checked against the *same* binding duty — ECOA /
  Regulation B 12 CFR 1002.9(b)(2), "the statement of reasons ... must be specific and indicate
  the principal reason(s) for the adverse action". See `docs/three-systems.md` for the three
  side by side.

  This is the black box. A risk network is served behind an inference API; the audit runs on a
  separate host, against the decision log the serving stack exported. Nothing else crosses the
  boundary.

  Run: `python -m reasonsmith.examples.neural_scorer`

What a reader must not break:
  - This system exposes `decisions()` and nothing else, and that is the point, not an omission
    to be fixed. There is no `decide()` because the served model is not reachable from the audit
    host, and no `logic()` because a weight matrix is not a rule set: there is no formula in it
    for a solver to reason over. `report._engine_ladder` reads exactly that surface, so the
    strongest evidence available here is `observed` — read off the trace supplied, claiming
    nothing about the decisions not in it.
    Why this matters: `tests/test_docs_three_systems.py` asserts that ceiling. A future edit that
    hands this adapter a replay hook would raise the rung, and the demonstration would stop being
    the honest one it is sold as.
  - `declared_capabilities` is passed, so the capability basis stays `"declared"` — the vendor's
    data sheet states which signals the serving stack emits. Dropping it would make `JSONLAdapter`
    derive the set from this one sample trace, and an unattainable finding would then be worded as
    a claim about the system rather than about the log.
"""

from __future__ import annotations

from dataclasses import replace

from reasonsmith.adapters.jsonl import JSONLAdapter
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

#: The signals the vendor's data sheet says the serving stack writes for every scored application.
#: Declared, not inferred from the log below.
DECLARED_CAPABILITIES = {
    "applicant_id",
    "decision",
    "artifact_logs_reason_explanation",
    "provenance_model_version",
    "scope_statements_local_vs_global",
}

#: Decision log exported from the inference service, one JSON object per scored application. The
#: network that produced it is not in this file and cannot be called from here; this is what an
#: auditor of a hosted model actually holds.
EXPORTED_LOG = "\n".join(
    [
        '{"applicant_id": "APP-1042", "decision": "adverse_action",'
        ' "artifact_logs_reason_explanation": "C01 income insufficient for amount requested",'
        ' "provenance_model_version": "risk-net-2026.06.2",'
        ' "scope_statements_local_vs_global": "local: attribution for this applicant only"}',
        '{"applicant_id": "APP-1043", "decision": "approved",'
        ' "artifact_logs_reason_explanation": "C00 no adverse factor",'
        ' "provenance_model_version": "risk-net-2026.06.2",'
        ' "scope_statements_local_vs_global": "local: attribution for this applicant only"}',
        '{"applicant_id": "APP-1044", "decision": "adverse_action",'
        ' "artifact_logs_reason_explanation": "C03 length of credit history",'
        ' "provenance_model_version": "risk-net-2026.06.2",'
        ' "scope_statements_local_vs_global": "local: attribution for this applicant only"}',
    ]
)


def system_under_test() -> JSONLAdapter:
    """The system as reasonsmith sees it: an exported log and a declared capability set."""
    sut = JSONLAdapter(EXPORTED_LOG, declared_capabilities=DECLARED_CAPABILITIES)
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
        system_name="risk-net (neural, served behind an inference API)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
