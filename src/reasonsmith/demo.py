"""The two demonstrations: ECOA / Reg B credit, and GDPR Art. 22 clinical.

What this module is for:
  Executes end-to-end demonstrations comparing Table 7 evidence records against reason-deletion
  certificates, Table 19 stratified per-group conformance metrics, and window stability checks.

  Run: `python -m reasonsmith.demo`

What a reader must not break:
  - Synthetic programs are frozen and deterministic without randomness; demo output must remain
    reproducible byte-for-byte.
    Why this matters: Guarantees every measured figure and transcript line in the paper and repo
    can be verified and diffed byte-for-byte.
  - Credit comes first on purpose: ECOA requires specific principal reasons, making proof
    truncation a legal compliance issue.
    Why this matters: Under credit law, a dropped reason is a reason legally owed to an applicant
    and withheld, making it the sharpest test of certificate value.
"""

from __future__ import annotations

from dataclasses import dataclass

from nesyarena.adapters.base import ReferenceAdapter
from nesyarena.ir import Atom, GroundProgram, Rule
from nesyarena.oracle import wmc
from nesyarena.suts import ExactWMC, TopK, proof_score

from . import conformance
from .certificate import certify
from .evidence import emit, traceability_report

# ------------------------------------------------------------------- domains ----
# (reason code, the reason as it would be stated to the person, EDB evidence facts)

CREDIT_REASONS = [
    ("C01", "Income insufficient for amount of credit requested",
     ("dti_above_policy", "income_verified")),
    ("C02", "Length of time credit has been established is too short",
     ("history_under_24_months", "file_thin")),
    ("C03", "Delinquent past or present credit obligations",
     ("delinquency_on_file", "bureau_record_matched")),
    ("C04", "Too many recent inquiries on credit bureau report",
     ("inquiries_over_policy", "bureau_record_matched")),
    ("C05", "Insufficient number of credit references provided",
     ("references_under_policy", "application_complete")),
]

CLINICAL_REASONS = [
    ("H01", "Comorbidity burden above the fast-track ceiling",
     ("comorbidity_index_high", "history_coded")),
    ("H02", "Renal function below the protocol floor",
     ("egfr_below_floor", "labs_within_window")),
    ("H03", "Interacting medication on the active list",
     ("interacting_drug_active", "medication_list_current")),
    ("H04", "Vital-sign instability in the observation window",
     ("vitals_unstable", "monitoring_continuous")),
    ("H05", "Imaging finding outside the automated-review scope",
     ("imaging_finding_out_of_scope", "imaging_reported")),
]

CREDIT_QUERY = "adverse_action"
CLINICAL_QUERY = "withhold_fast_track"


@dataclass(frozen=True)
class Case:
    case_id: str
    group: str
    query: Atom
    program: GroundProgram
    base: dict
    labels: dict


def build_case(case_id: str, group: str, query_pred: str, reasons, level: float) -> Case:
    """One decision: a ground program whose every proof is one reason, and a base interpretation.

    Fact probabilities decrease with the reason's position and with the fact's position inside it,
    so reason scores are distinct and the score order is C01 > C02 > ... — which is what makes a
    top-k engine's discard set predictable enough to attribute.
    """
    query = Atom(query_pred, (case_id,))
    rules, base, labels = [], {}, {}
    for j, (code, text, facts) in enumerate(reasons):
        atoms = tuple(Atom(f, (case_id,)) for f in facts)
        rules.append(Rule(query, atoms))
        for i, a in enumerate(atoms):
            base.setdefault(a, round(level - 0.04 * j - 0.01 * i, 4))
        labels[frozenset(atoms)] = f"{code} — {text}"
    return Case(case_id, group, query, GroundProgram(tuple(rules)), base, labels)


def score_factors(cert) -> str | None:
    """The Table 7 score factors, read off the certificate's measured proof scores.

    None when exact inference found no reason to score: the record then reports the field missing,
    which is the whole point — a plausible-looking figure nobody measured is the one thing this
    package must never put in a compliance document.
    """
    if not cert.verdicts:
        return None
    return "; ".join(f"{v.label.partition(' — ')[0]} {v.score:.4f}"
                     for v in sorted(cert.verdicts, key=lambda v: (-v.score, v.label)))


def certify_case(case: Case, adapter):
    return certify(case.program, case.base, case.query, adapter, exact_depth=1,
                   labels=case.labels)


# ------------------------------------------------------- deliberately broken ----

class SilentDropAdapter:
    """A perturbed engine: it claims exact distribution semantics, and quietly drops the
    lowest-scoring reason before answering. This is what an undocumented pruning heuristic looks
    like from outside — the value is close enough to exact to pass an eyeball check."""

    supports_grad = False

    def __init__(self, max_depth: int = 8):
        self.max_depth = max_depth
        self.name = "perturbed:silent-drop-lowest-reason"
        self.claimed_semantics = "distribution semantics"

    def infer(self, program, base, queries):
        out = {}
        for q in queries:
            proofs = program.proof_supports(q, self.max_depth)
            kept = sorted(proofs, key=lambda pr: (-proof_score(pr, base),
                                                  sorted(repr(a) for a in pr)))[:-1]
            out[q] = wmc(kept, base) if kept else 0.0
        return out


class MiscalibratedAdapter:
    """A perturbed engine of the other kind: it uses every reason, and scales its answer by a
    'calibration' factor it does not declare. No reason is deleted, so the deletion probe alone
    would clear it; the value check against the exact oracle is what catches it."""

    supports_grad = False

    def __init__(self, factor: float = 0.97, max_depth: int = 8):
        self.factor = factor
        self.max_depth = max_depth
        self.name = f"perturbed:undeclared-calibration(x{factor})"
        self.claimed_semantics = "distribution semantics"

    def infer(self, program, base, queries):
        return {q: self.factor * wmc(program.proof_supports(q, self.max_depth), base)
                for q in queries}


# ------------------------------------------------------------------- cohorts ----

def cohort(prefix: str, group: str, query_pred: str, reasons, level: float, n: int = 4):
    return [build_case(f"{prefix}-{group[:3].upper()}{i}", group, query_pred,
                       reasons, round(level - 0.02 * i, 4))
            for i in range(n)]


def design_a(prefix: str, query_pred: str, reasons):
    """Confidence varies, reason structure held fixed: both groups have the same three reasons,
    the atypical group's evidence carries lower model confidence."""
    return {"typical": cohort(prefix, "typical", query_pred, reasons[:3], 0.90),
            "atypical": cohort(prefix, "atypical", query_pred, reasons[:3], 0.55)}


def design_b(prefix: str, query_pred: str, reasons):
    """Reason multiplicity varies, confidence held fixed: the atypical group trips five reasons
    where the typical group trips two, at the same confidence level."""
    return {"typical": cohort(prefix, "typical", query_pred, reasons[:2], 0.80),
            "atypical": cohort(prefix, "atypical", query_pred, reasons[:5], 0.80)}


# -------------------------------------------------------------------- report ----

RULE = "=" * 100


def _head(title: str) -> str:
    return f"\n{RULE}\n{title}\n{RULE}"


def credit_demo() -> str:
    """ECOA / Reg B end to end, on one adverse action."""
    out = [_head("1. CREDIT — ECOA / Reg B (12 CFR 1002.9), Table 7 row 4")]
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)

    topk = ReferenceAdapter(TopK(1))
    exact = ReferenceAdapter(ExactWMC())
    cert_topk = certify_case(case, topk)
    cert_exact = certify_case(case, exact)

    out += ["", "The deployed engine keeps the single best proof.", "", cert_topk.render()]
    out += ["", "Exact inference on the same program and the same base interpretation recovers "
                "every one of them:", "", cert_exact.render()]

    reasons_line = "\n".join(f"  {v.label}" for v in
                             sorted(cert_topk.live, key=lambda v: v.label))
    record = emit(
        "ecoa_reg_b_adverse_action", case.case_id,
        {
            "stored_reasons_per_decision": reasons_line,
            "model_version": "credit-scoring-2026.03.1 / rules cs-rules-2026.03",
            "score_factors": score_factors(cert_topk),
            "audit_ids": "AAN-2026-0731-1042 / trace-9f3c1b",
            "retention_for_regulatory_lookback": "25 months from notice date, per lender policy",
        },
        attachments={"reason-deletion certificate": cert_topk.render()},
    )
    out += ["", "The adverse action notice pipeline emits its Table 7 record:", "", record.render()]
    out += ["",
            "Read those two together. The record is COMPLETE — every field Table 7 lists for row 4 "
            "was produced.",
            "The certificate says the stored reasons are not all the reasons. Table 7 completeness "
            "is a check on the",
            "form of the record, not on the truth of what it contains; under 12 CFR 1002.9 the "
            "notice must state the",
            f"specific principal reasons, and {len(cert_topk.deleted)} of "
            f"{len(cert_topk.verdicts)} are absent from this one."]

    partial = emit(
        "ecoa_reg_b_adverse_action", case.case_id,
        {
            "stored_reasons_per_decision": reasons_line,
            "model_version": "credit-scoring-2026.03.1 / rules cs-rules-2026.03",
            "score_factors": score_factors(cert_topk),
            "retention_for_regulatory_lookback": "25 months from notice date, per lender policy",
        },
    )
    out += ["", "Withholding one required field — the audit IDs — is refused loudly rather than "
                "papered over:", "", partial.render()]
    return "\n".join(out)


def clinical_demo() -> str:
    """GDPR Art. 22 end to end, on one automated clinical decision."""
    out = [_head("2. CLINICAL — GDPR Art. 22 and Rec. 71, Table 7 row 3")]
    case = build_case("PT-0731", "typical", CLINICAL_QUERY, CLINICAL_REASONS, 0.86)

    cert_topk = certify_case(case, ReferenceAdapter(TopK(1)))
    cert_exact = certify_case(case, ReferenceAdapter(ExactWMC()))
    out += ["", cert_topk.render()]
    out += ["", "Exact inference recovers the reasons the top-k setting discarded:", "",
            cert_exact.render()]

    record = emit(
        "gdpr_art22_meaningful_information", case.case_id,
        {
            "per_decision_reason_string": "\n".join(
                f"{v.label}" for v in sorted(cert_exact.live, key=lambda v: v.label)),
            "feature_to_named_concept_mapping": "\n".join(
                f"{f} -> {code}: {text}" for code, text, facts in CLINICAL_REASONS[:5]
                for f in facts),
            "dpia_cross_reference": "DPIA-2026-014 s.4.2 (automated triage, Art. 22 assessment)",
        },
        attachments={"reason-deletion certificate": cert_exact.render()},
    )
    out += ["", "With exact inference behind it the Art. 22 record can state the whole logic:", "",
            record.render()]

    partial = emit(
        "gdpr_art22_meaningful_information", case.case_id,
        {
            "per_decision_reason_string": "\n".join(
                f"{v.label}" for v in sorted(cert_exact.live, key=lambda v: v.label)),
            "dpia_cross_reference": "DPIA-2026-014 s.4.2 (automated triage, Art. 22 assessment)",
        },
    )
    out += ["", "Withhold the feature-to-concept mapping and the record says so:", "",
            partial.render()]
    return "\n".join(out)


def corruption_demo() -> str:
    out = [_head("3. PERTURBED ENGINES — does the certificate catch a broken one?")]
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    for adapter in (SilentDropAdapter(), MiscalibratedAdapter()):
        cert = certify_case(case, adapter)
        out += ["", cert.render()]
    out += ["",
            "An instrument that passed a corrupted engine would be worthless, so both "
            "perturbations must fail, and by",
            "different routes: the silent drop is caught by the deletion probe, which names the "
            "reason that stopped",
            "mattering; the undeclared calibration keeps every reason live and is caught only by "
            "the value check against",
            "the exact oracle. Neither check subsumes the other, which is why the certificate "
            "requires both."]
    return "\n".join(out)


def stratified_demo() -> str:
    out = [_head("4. STRATIFIED PER-GROUP CHECKS (Table 19: minority over-smoothing)")]
    out += ["",
            "Registered hypothesis, stated before the measurement: low-probability reasons are "
            "dropped first, so",
            "atypical cases lose reasons faster. Two cohort designs separate the two things that "
            "could drive that."]
    topk = ReferenceAdapter(TopK(1))
    results = {}
    for name, groups in (("A: confidence varies, reason structure fixed",
                          design_a("APP", CREDIT_QUERY, CREDIT_REASONS)),
                         ("B: reason multiplicity varies, confidence fixed",
                          design_b("APP", CREDIT_QUERY, CREDIT_REASONS))):
        strat = conformance.stratified(
            {g: [certify_case(c, topk) for c in cases] for g, cases in groups.items()})
        results[name] = strat
        out += ["", f"design {name}", "", conformance.render(strat, size_cap=3)]

    a = results["A: confidence varies, reason structure fixed"]
    b = results["B: reason multiplicity varies, confidence fixed"]

    def line(strat, metric):
        g = strat["gaps"][metric]
        vals = {name: s[metric] for name, s in strat["per_group"].items()}
        detail = ", ".join(f"{n} {v:.4f}" for n, v in vals.items())
        if abs(g["gap"]) < 1e-12:
            return f"    {metric:<16} no gap ({detail})"
        return f"    {metric:<16} gap {g['gap']:.4f}, worse for {g['worst']} ({detail})"

    out += ["", "OUTCOME OF THE REGISTERED HYPOTHESIS", ""]
    out += ["  Design A — confidence varies, reason structure fixed:"]
    out += [line(a, m) for m in ("coverage", "retained_share", "fidelity")]
    out += ["", "  Design B — reason multiplicity varies, confidence fixed:"]
    out += [line(b, m) for m in ("coverage", "retained_share", "fidelity")]
    out += [
        "",
        "  In its confidence form the hypothesis is NOT supported. Lowering confidence alone does "
        "not cost a case any",
        "  reasons: top-k keeps a fixed number of proofs, and scaling every score down leaves "
        "their order unchanged, so",
        "  coverage is identical across the two groups of design A. The atypical group is still "
        "worse off, but on the",
        "  value metrics rather than the reason count — it keeps a smaller share of the answer it "
        "would have had under",
        "  exact inference.",
        "",
        "  In its multiplicity form it is supported: a case that trips five reasons and is told "
        "one keeps a fifth of its",
        "  reasons, a case that trips two keeps half. Coverage moves in design B and not in design "
        "A, which locates the",
        "  mechanism in how many reasons a case trips, not in how confident the model is about "
        "them.",
        "",
        "  Both readings were registered in advance and both are reported. The negative half is "
        "the more useful one: a",
        "  per-group coverage check will not detect confidence-driven harm at all, so a deployment "
        "watching coverage alone",
        "  would have seen design A as clean. Retained share is what caught it.",
        "",
        "  The limit that matters most: these are frozen synthetic cohorts, built to separate two "
        "mechanisms. Whether real",
        "  atypical cases trip more reasons than typical ones is an empirical question about data "
        "this does not have.",
    ]
    return "\n".join(out)


def stability_demo() -> str:
    """Table 19 'stability across time/windows', on one decision re-scored as a signal drifts."""
    out = [_head("5. STABILITY ACROSS WINDOWS (Table 19)")]
    out += ["",
            "One decision, four monitoring windows, one drifting signal: the bureau's delinquency "
            "evidence strengthens",
            "window by window. Nothing about the program changes, and the applicant's other "
            "evidence does not change."]
    topk = ReferenceAdapter(TopK(1))
    certs = []
    for w in range(4):
        case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
        base = {a: (round(min(0.99, p + 0.06 * w), 4)
                    if a.pred in ("delinquency_on_file", "bureau_record_matched") else p)
                for a, p in case.base.items()}
        cert = certify(case.program, base, case.query, topk, exact_depth=1, labels=case.labels)
        certs.append(cert)
        out.append(f"  window {w}: reason given = "
                   f"{', '.join(v.label for v in cert.live) or '(none)'}")
    out += ["",
            f"  stability across the four windows: {conformance.stability(certs):.4f} "
            f"(1.0 would mean the same reasons every window)",
            "",
            "  The applicant's file did not change, and the reason they are given did. Under a "
            "top-1 setting the reason",
            "  stated is whichever proof currently scores highest, so drift in one signal silently "
            "replaces the stated",
            "  reason with another. Exact inference has nothing to reorder — it gives all of them "
            "in every window."]
    return "\n".join(out)


def main() -> str:
    parts = [
        _head("0. TRACEABILITY — every schema entry against the Table 7 text it came from"),
        "",
        traceability_report(),
        credit_demo(),
        clinical_demo(),
        corruption_demo(),
        stratified_demo(),
        stability_demo(),
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    print(main())
