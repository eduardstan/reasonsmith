"""Builds `docs/nesyarena-conformance-report.md`, a conformance run against a real system.

What this module is for:
  Every report shipped before this one ran against a system written to illustrate a point. This
  one runs against `nesyarena`'s provenance semantics — the reference implementations of
  deployed NeSy aggregation strategies that this package already depends on for its oracle — on
  programs `nesyarena.generators` emits, checked against the shipped GDPR, EU AI Act and
  ECOA / Regulation B packs unchanged.

  Run: `python docs/build_nesyarena_report.py`

  The findings, including the unflattering ones, are written up in
  `docs/findings-nesyarena.md`. This script only produces the evidence.

What a reader must not break:
  - The report names `BUILD_COMMAND` as its provenance and deliberately carries no commit hash,
    the same convention `docs/build_example.py` uses for `docs/index.html`. A hash embedded in
    the artifact cannot name the commit containing that artifact: writing the hash changes the
    file, which changes the commit, so the self-reference never closes. Naming the preceding
    builder-bearing commit instead does not close it either — it asserts something no reader can
    check from a shallow CI clone, which is exactly how a commit that could not reproduce the
    report survived review once already.
    What replaces it is stronger because it is checked rather than asserted:
    `test_nesyarena_report_matches_the_builder` re-runs this module and compares byte-for-byte,
    so the committed report is provably the output of the committed builder. Anything that moves
    that output — a wording change in `report.render_text`, a different nesyarena version, a
    moved threshold — must be followed by regenerating the report.
  - `NesyArenaSUT` declares only signals the system genuinely emits, and every declared signal's
    value is computed from that system's own inference on that instance — never a placeholder
    and never a constant standing in for a measurement. `UNDECLARED_SIGNALS` records, for the
    reader, the pack signals deliberately not declared and why.
    Why this matters: the whole value of running against a real system is lost the moment a
    field is filled in to make a duty checkable. A duty this system cannot discharge must come
    back unattainable.
  - `REASON_RULE` is the definition of what counts as a per-decision reason, fixed before the
    run and applied identically to all five systems: the facts the system's *own* differentiation
    gives non-zero influence. A system whose gradient is identically zero has named nothing, and
    an empty reason field is the honest record of that.
    Why this matters: emitting an all-zero attribution as a reason is exactly the overclaim
    reasonsmith exists to refuse. Changing this rule per system would be tuning the run.
  - `system_scope` stays `None`. `nesyarena`'s provenances are reference implementations in a
    measurement harness, not an AI system placed on the market in an Annex III use, so no
    regulatory class is declared for them and the EU AI Act duties come back not applicable.
    Why this matters: declaring a class that does not fit would be a worse error than reporting
    less, and the not-applicable results are themselves a finding about what the tool can say
    about an unclassified system.
  - `system_domains` stays `None`, for exactly the same reason and with the same standing. These
    provenances decide graph reachability and Sudoku validity; they issue no credit, hire nobody
    and treat no patient, so there is no decision domain to declare and the ECOA duties come back
    not applicable.
    Why this matters: this is the run that produced finding 3 of `docs/findings-nesyarena.md` —
    an adverse-action notice duty reported `satisfied` against a graph-reachability benchmark.
    Naming a domain here to make those rows evaluate again would put that false positive back by
    hand. The not-applicable rows *are* the fix working.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from nesyarena.generators import chain_family, cyclic_family, overlap_family  # noqa: E402
from nesyarena.suts import registry  # noqa: E402

from reasonsmith.report import check_conformance  # noqa: E402
from reasonsmith.spec import load_pack  # noqa: E402
from reasonsmith.sut import BaseSUT  # noqa: E402

#: The provenance the report prints, and the command that reproduces it byte-for-byte.
BUILD_COMMAND = "python docs/build_nesyarena_report.py"

#: Pinned by `pyproject.toml`; restated here because it is the version of the system under test.
NESYARENA_VERSION = "0.1.0"

REPORT_PATH = ROOT / "docs" / "nesyarena-conformance-report.md"

#: The decision rule applied to every system on every instance. Fixed before the run; the
#: whole point of the exercise is void if it is moved afterwards to change a verdict.
APPROVE_THRESHOLD = 0.5

#: What counts as a per-decision reason, fixed before the run and identical for all systems.
REASON_RULE = (
    "the input facts the system's own gradient gives non-zero influence over this decision, "
    "with their weights"
)

#: Pack signals this adapter deliberately does not declare, and why. Printed in the report so a
#: reader can see that each unattainable verdict below is a genuine limit of the system rather
#: than an omission in the adapter. Together with `DECLARED_SIGNALS` this must account for every
#: signal the three packs read — including one that gates no duty, the ungated branch signal of
#: the either/or in 12 CFR 1002.9(a)(2).
UNDECLARED_SIGNALS = (
    (
        "provenance_active_exceptions",
        "the programs are definite Horn clauses over independent probabilistic facts; there is "
        "no defeater or exception mechanism for an inference to record as active",
    ),
    (
        "artifact_logs_notification_latency_days",
        "the system computes a query value; it neither issues nor times a notification",
    ),
    (
        "artifact_logs_counteroffer_not_accepted",
        "no counteroffer exists in this decision domain",
    ),
    (
        "artifact_logs_right_to_reasons_disclosure",
        "the system issues no adverse-action notice, so no decision of its own carries a "
        "disclosure of a right to request reasons. It is one branch of the either/or of 12 CFR "
        "1002.9(a)(2) and no `requires` gates it, so its absence makes no duty unattainable: "
        "that content duty is judged on the other branch, the reason explanation",
    ),
    (
        "artifact_logs_deleted_reason_count",
        "unlike every other signal here, this one is not something the system emits into a "
        "record: reasonsmith measures it itself from an inference artefact the system exposes "
        "through the optional `artifact()` method. None of the five provenances exposes one, so "
        "there is nothing to measure and no longer trace could ever supply it",
    ),
    (
        "artifact_logs_solely_automated",
        "whether a human reviews the output afterwards is a property of the pipeline the "
        "system is embedded in, which the system cannot observe",
    ),
    (
        "artifact_logs_significant_effect",
        "the effect of a decision on a person is a fact about the deployment, not about the "
        "inference",
    ),
    (
        "artifact_logs_human_intervention_route",
        "an intervention route is an organisational arrangement, not an inference output",
    ),
    (
        "provenance_basis_contract",
        "the lawful basis for processing is a controller's legal position, not a value any "
        "provenance semiring computes",
    ),
    (
        "provenance_basis_union_or_member_state_law",
        "as above",
    ),
    (
        "provenance_basis_explicit_consent",
        "as above",
    ),
)

#: Every signal the adapter declares. Each one has a value computed from the system's own run.
DECLARED_SIGNALS = (
    "artifact_logs_decision_record",
    "artifact_logs_decision_margin",
    "artifact_logs_event_log",
    "artifact_logs_reason_explanation",
    "provenance_model_version",
    "provenance_constraint_set",
    "scope_statements_local_vs_global",
    "scope_statements_explanation_scope",
    "scope_statements_approximation_vs_guarantee",
    "scope_statements_declared_deviation",
)

PACKS = ("gdpr", "eu_ai_act", "ecoa")


def battery():
    """The instance set, from `nesyarena.generators`, over a grid fixed before the run.

    Every instance is generated, not hand-written, and the enumeration depth is the one the
    generator itself records in `params["depth"]`. Nothing here is selected after seeing a
    result: the grid is a full cross product and the two graph families are taken as they come.
    """
    instances = []
    for p_count in (1, 2, 4):
        for length in (2, 3):
            for shared in (0, 1):
                instances.append(
                    (
                        f"G1-P{p_count}-L{length}-c{shared}",
                        overlap_family(P=p_count, L=length, c=shared, p=0.7),
                    )
                )
    for length in (2, 3, 4):
        instances.append((f"G2-chain-L{length}", chain_family(L=length, p=0.9)))
    instances.append(("G2-cyclic", cyclic_family()))
    return instances


def _fmt(value: float) -> str:
    return f"{value:.6f}"


class NesyArenaSUT(BaseSUT):
    """A `nesyarena` provenance, run over generated ground programs, as a system under test.

    One decision per instance: the provenance aggregates the bounded proof enumeration of the
    program and the value is thresholded at `APPROVE_THRESHOLD`. Every field of every record is
    read off that computation.
    """

    def __init__(self, provenance, instances):
        super().__init__(set(DECLARED_SIGNALS))
        self.provenance = provenance
        self.instances = instances
        self.name = provenance.name

    def rows(self):
        """The raw measurement behind the trace: one row per instance."""
        out = []
        for label, inst in self.instances:
            proofs = inst.proofs
            value = self.provenance.value(proofs, inst.probs)
            oracle = self.provenance.oracle(proofs, inst.probs)
            grad = self.provenance.grad(proofs, inst.probs)
            attribution = {f: w for f, w in grad.items() if w != 0.0}
            out.append(
                {
                    "label": label,
                    "instance": inst,
                    "proofs": proofs,
                    "value": value,
                    "oracle": oracle,
                    "error": value - oracle,
                    "attribution": attribution,
                }
            )
        return out

    def decisions(self):
        records = []
        for seq, row in enumerate(self.rows()):
            inst = row["instance"]
            decision = "approve" if row["value"] >= APPROVE_THRESHOLD else "deny"
            reason = [
                f"{fact!r}={_fmt(weight)}"
                for fact, weight in sorted(
                    row["attribution"].items(), key=lambda kv: (-abs(kv[1]), repr(kv[0]))
                )
            ]
            claim = self.provenance.claimed
            deviation = abs(row["error"])
            guarantee = (
                f"guarantee: value equals the {claim} oracle on this input (measured "
                f"deviation {_fmt(deviation)})"
                if deviation == 0.0
                else (
                    f"approximation: value deviates from the {claim} oracle it claims by "
                    f"{row['error']:+.6f} on this input"
                )
            )
            records.append(
                {
                    "artifact_logs_decision_record": (
                        f"instance={row['label']} query={inst.query!r} "
                        f"value={_fmt(row['value'])} threshold={APPROVE_THRESHOLD} "
                        f"decision={decision}"
                    ),
                    "artifact_logs_decision_margin": abs(row["value"] - APPROVE_THRESHOLD),
                    "artifact_logs_event_log": (
                        f"seq={seq} instance={row['label']} family={inst.params['family']} "
                        f"depth={inst.params['depth']} proofs={len(row['proofs'])} "
                        f"facts={len(inst.probs)}"
                    ),
                    "artifact_logs_reason_explanation": reason,
                    "provenance_model_version": (
                        f"nesyarena {NESYARENA_VERSION} provenance {self.provenance.name}"
                    ),
                    "provenance_constraint_set": [repr(r) for r in inst.program.rules],
                    "scope_statements_local_vs_global": (
                        "local: the attribution is the derivative at this input only and "
                        "describes no other input"
                    ),
                    "scope_statements_explanation_scope": (
                        f"reason names {REASON_RULE}; it covers the "
                        f"{len(row['proofs'])} bounded proof(s) enumerated to depth "
                        f"{inst.params['depth']} and no proof beyond that depth"
                    ),
                    "scope_statements_approximation_vs_guarantee": guarantee,
                    "scope_statements_declared_deviation": deviation,
                }
            )
        return records


def _inference_table(systems) -> list[str]:
    lines = [
        "| instance | family | depth | proofs | system | value | claimed-semantics oracle "
        "| signed error | facts with non-zero attribution | decision |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for sut in systems:
        for row in sut.rows():
            inst = row["instance"]
            decision = "approve" if row["value"] >= APPROVE_THRESHOLD else "deny"
            lines.append(
                f"| {row['label']} | {inst.params['family']} | {inst.params['depth']} "
                f"| {len(row['proofs'])} | {sut.name} | {_fmt(row['value'])} "
                f"| {_fmt(row['oracle'])} | {row['error']:+.6f} "
                f"| {len(row['attribution'])} | {decision} |"
            )
    return lines


def render() -> str:
    instances = battery()
    systems = [NesyArenaSUT(prov, instances) for prov in registry()]

    lines = [
        "# Conformance report: nesyarena provenance semantics",
        "",
        f"**Generated by:** `{BUILD_COMMAND}`  ",
        "**Provenance:** re-running that command in any checkout of this repository rewrites "
        "this file identically; `test_nesyarena_report_matches_the_builder` fails if it does "
        "not  ",
        f"**System under test:** nesyarena {NESYARENA_VERSION} "
        f"(`nesyarena.suts.registry()`, {len(systems)} provenances)  ",
        f"**Packs:** {', '.join(PACKS)} — shipped, unchanged  ",
        "**Declared regulatory class:** none",
        "",
        "This file is generated. Do not edit it by hand: regenerate it with the command above.",
        "The written account of what it found, including the unflattering parts, is in",
        "[findings-nesyarena.md](findings-nesyarena.md).",
        "",
        "## The systems",
        "",
        "`nesyarena.suts.registry()` is nesyarena's own standard lineup, taken whole rather than",
        "chosen: an exact oracle, an over-counting proof sum, two truncated proof selections and",
        "a min-max bottleneck. All five claim distribution semantics.",
        "",
    ]
    for sut in systems:
        lines.append(f"- `{sut.name}` — claims *{sut.provenance.claimed}*")
    lines.extend(
        [
            "",
            "## The decision rule and the record",
            "",
            "One decision per instance: the provenance aggregates the bounded proof",
            "enumeration of the ground program, and the value is thresholded at",
            f"`{APPROVE_THRESHOLD}`. The threshold was fixed before the run and not moved.",
            "",
            f"A per-decision reason is {REASON_RULE}. This rule was fixed before the run and is",
            "applied identically to all five systems.",
            "",
            "### Signals declared",
            "",
            "Each carries a value computed from that system's own inference on that instance:",
            "",
        ]
    )
    for signal in DECLARED_SIGNALS:
        lines.append(f"- `{signal}`")
    lines.extend(
        [
            "",
            "### Signals deliberately not declared",
            "",
            "The system genuinely cannot emit these, so a duty whose `requires` gates one is",
            "reported unattainable rather than filled in:",
            "",
        ]
    )
    for signal, why in UNDECLARED_SIGNALS:
        lines.append(f"- `{signal}` — {why}")

    lines.extend(
        [
            "",
            "## The instance battery",
            "",
            f"{len(instances)} instances from `nesyarena.generators`: the full cross product",
            "`P in (1, 2, 4) x L in (2, 3) x c in (0, 1)` of the overlap family at `p = 0.7`,",
            "the chain family at `L in (2, 3, 4)`, `p = 0.9`, and the cyclic recursion instance.",
            "Enumeration depth is the one each generator records. No instance was selected after",
            "seeing a result.",
            "",
            "## Measured inference",
            "",
        ]
    )
    lines.extend(_inference_table(systems))

    lines.extend(["", "## Conformance findings", ""])
    counterexamples: list[str] = []
    for sut in systems:
        labels = [label for label, _ in sut.instances]
        for pack_name in PACKS:
            pack = load_pack(pack_name)
            report = check_conformance(
                sut,
                pack,
                system_name=f"nesyarena:{sut.name}",
                system_scope=None,
                system_domains=None,
            )
            lines.extend(
                [
                    f"### `{sut.name}` against `{pack_name}`",
                    "",
                    "```text",
                    report.render_text(),
                    "```",
                    "",
                ]
            )
            for result in report.results:
                indices = result.details.get("violation_step_indices")
                if not indices:
                    continue
                absent = result.details.get("signals_absent_from_trace", ())
                # A record duty names the fields the decisions do not carry; a temporal duty
                # names the property they breach, because every field it reads is present and
                # it is the value that fails.
                breach = (
                    f"carry no {', '.join(absent)}"
                    if absent
                    else f"breach `{pack.get_requirement(result.requirement_id).spec}`"
                )
                counterexamples.append(
                    f"- `{sut.name}` / `{pack_name}` / `{result.requirement_id}`: "
                    f"{len(indices)} of {len(labels)} decisions {breach} — instances "
                    f"{', '.join(labels[i] for i in indices)} (record index "
                    f"{', '.join(str(i) for i in indices)})"
                )

    lines.extend(
        [
            "## Counterexamples",
            "",
            "The decisions behind every `violated` verdict above, named so a reader can",
            "reproduce them from the measured-inference table.",
            "",
        ]
    )
    lines.extend(counterexamples or ["No requirement was violated in this run."])
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    REPORT_PATH.write_text(render(), encoding="utf-8")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
