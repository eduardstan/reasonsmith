"""The one shipped example that comes back **violated**: a system that deleted four reasons.

What this module is for:
  Its three siblings — `neural_scorer`, `probabilistic_scorer`, `symbolic_rules` — all come back
  `satisfied`, so a reader who ran every shipped example never saw the tool report a breach, and a
  breach is the memorable result. This one runs the demonstration's own adverse-action pipeline
  against ECOA / Regulation B 12 CFR 1002.9(b)(2)'s *content* duty: are the reasons stated all the
  reasons the decision's own inference used? On decision `APP-1042` exact inference finds five and
  the deletion probe shows the engine's answer depends on one, so the run reports `violated` at
  strength `probed` and names the four that went unstated.

  Run: `python -m reasonsmith.examples.truncating_credit_system`

What a reader must not break:
  - The system is `reasonsmith.demo`'s `TruncatingCreditSystem`, imported and not reimplemented.
    A second copy of it here would be a second thing to keep in step with the demonstration, the
    committed dossier and the README transcript, all of which are that same system's output.
  - The duty is the *content* half of the clause, not the *form* half its siblings check. The two
    are different requirements of the same clause and this system satisfies the first while
    breaching the second; checking the form duty here would print a `satisfied` and lose the point.
  - `main` prints and returns; the exit code is left alone. `reasonsmith check` is where a
    violation exits 2, and this module is the `python -m` demonstration beside it, not a gate.
"""

from __future__ import annotations

from dataclasses import replace

from reasonsmith.demo import deployed_credit_system
from reasonsmith.report import check_conformance
from reasonsmith.spec import load_pack

#: The duty this system breaches: the reasons a notice states against the reasons the decision's
#: own inference used. Its sibling `ecoa_reg_b_1002_9_b_2_specific_reasons` reads the same clause's
#: form and is satisfied on this same run, which is the finding rather than an inconsistency.
REQUIREMENT_ID = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"

#: What kind of decision this system makes, declared on the adapter itself
#: (`reasonsmith.demo.TruncatingCreditSystem.system_domains`). An undeclared system is reported not
#: applicable on a domain-limited duty rather than judged.
system_under_test = deployed_credit_system


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
        system_name="TruncatingCreditSystem (top-k truncation at k=1, inference artefact exposed)",
    )
    print(report.render_text())


if __name__ == "__main__":
    main()
