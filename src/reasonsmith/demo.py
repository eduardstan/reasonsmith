"""The two demonstrations: ECOA / Reg B credit, and GDPR Art. 22 clinical.

What this module is for:
  Executes end-to-end demonstrations comparing Table 7 evidence records against reason-deletion
  certificates, Table 19 stratified per-group conformance metrics, and window stability checks.

  Run: `python -m reasonsmith.demo`

What a reader must not break:
  - The programs are frozen synthetic ones in nesyarena's style: realistic structure, no real
    personal data, no ethics approval needed, no randomness. Every probability is a fixed function
    of the case index.
    Why this matters: Guarantees every measured figure and transcript line in the paper and repo
    can be verified and diffed byte-for-byte. Those probabilities stand in for a neural component's
    confidence in each piece of evidence; whether real systems produce confidences shaped like
    these is a separate question this does not answer.
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


# --------------------------------------------------- the key finding, as a page ----

#: Styling for `render_key_finding_html`, carried by the section itself so a report that
#: does not ask for the section carries neither its markup nor its rules.
_KEY_FINDING_CSS = """
  .key-finding-section {
    margin: 1.5rem;
    border: 1px solid var(--color-slate-200);
    border-radius: 10px;
    background: #ffffff;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }
  .key-finding-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #ffffff;
    padding: 1.25rem 1.5rem;
    border-bottom: 2px solid #3b82f6;
  }
  .kf-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    background: #ef4444;
    color: #ffffff;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin-bottom: 0.35rem;
  }
  .kf-title {
    font-size: 1.25rem;
    font-weight: 800;
    line-height: 1.3;
  }
  .kf-subtitle {
    font-size: 0.9rem;
    color: #94a3b8;
    margin-top: 0.25rem;
  }
  .key-finding-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem;
    padding: 1.25rem;
    background: #f8fafc;
  }
  @media (max-width: 768px) {
    .key-finding-grid { grid-template-columns: 1fr; }
  }
  .kf-card {
    border-radius: 8px;
    border: 1px solid var(--color-slate-200);
    background: #ffffff;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .kf-card-record {
    border-top: 4px solid #059669;
  }
  .kf-card-cert {
    border-top: 4px solid #dc2626;
  }
  .kf-card-header {
    padding: 0.85rem 1rem;
    background: #f1f5f9;
    border-bottom: 1px solid var(--color-slate-200);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .kf-card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-slate-800);
  }
  .kf-card-body {
    padding: 1rem;
    font-size: 0.85rem;
    flex: 1;
  }
  .kf-meta-line {
    margin-bottom: 0.35rem;
    color: var(--color-slate-700);
  }
  .kf-subhead {
    font-weight: 700;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--color-slate-600);
    margin-top: 0.85rem;
    margin-bottom: 0.4rem;
    padding-top: 0.5rem;
    border-top: 1px dashed var(--color-slate-200);
  }
  .kf-field-list, .kf-reason-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .kf-field-list li {
    margin-bottom: 0.35rem;
    line-height: 1.4;
    font-size: 0.8rem;
  }
  .check-icon {
    color: #059669;
    font-weight: 800;
    margin-right: 0.25rem;
  }
  .kf-values-bar {
    display: flex;
    gap: 0.75rem;
    background: #f8fafc;
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
    border: 1px solid var(--color-slate-200);
    margin: 0.5rem 0;
    font-family: var(--font-mono);
    font-size: 0.8rem;
  }
  .kf-gap {
    color: #dc2626;
    font-weight: 700;
  }
  .kf-reason-list li {
    padding: 0.25rem 0.4rem;
    border-radius: 4px;
    margin-bottom: 0.3rem;
    font-size: 0.78rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .reason-live {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
  }
  .reason-deleted {
    background: #fef2f2;
    border: 1px solid #fca5a5;
    color: #991b1b;
  }
  .reason-tag {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 800;
    padding: 0.05rem 0.3rem;
    border-radius: 3px;
    text-transform: uppercase;
  }
  .tag-live {
    background: #059669;
    color: #ffffff;
  }
  .tag-deleted {
    background: #dc2626;
    color: #ffffff;
  }
  .reason-score {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--color-slate-600);
    margin-left: auto;
  }
"""


def render_key_finding_html() -> str:
    """Render the key finding: Evidence Record [COMPLETE] vs Reason-Deletion Certificate [FAIL].

    Computed live via evidence.emit and certificate.certify so every value on the page
    matches exact engine outputs.

    This is the demonstration's own case, `APP-1042`, and it lives here rather than in the
    renderer because it says nothing about whatever system a report is about. It belongs on the
    committed example page and nowhere else: a conformance report is read as being about its own
    system, so a report that carried this section by default would put another decision's
    evidence in front of the auditor reading it.
    """
    import html

    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    cert = certify_case(case, ReferenceAdapter(TopK(1)))
    reasons_line = "\n".join(
        f"  {v.label}" for v in sorted(cert.live, key=lambda v: v.label)
    )
    record = emit(
        "ecoa_reg_b_adverse_action",
        case.case_id,
        {
            "stored_reasons_per_decision": reasons_line.strip(),
            "model_version": "credit-scoring-2026.03.1 / rules cs-rules-2026.03",
            "score_factors": score_factors(cert),
            "audit_ids": "AAN-2026-0731-1042 / trace-9f3c1b",
            "retention_for_regulatory_lookback": "25 months from notice date, per lender policy",
        },
    )

    rec_d = record.to_dict()
    cert_d = cert.to_dict()

    rec_fields_html = []
    for k, v in rec_d["fields"].items():
        k_esc = html.escape(k)
        v_esc = html.escape(str(v))
        rec_fields_html.append(
            f'<li><span class="check-icon">✓</span> '
            f'<strong><code>{k_esc}</code></strong>: {v_esc}</li>'
        )

    cert_reasons_html = []
    for v_item in sorted(cert_d["verdicts"], key=lambda x: (-x["score"], x["label"])):
        lbl = html.escape(v_item["label"])
        sc = v_item["score"]
        st = v_item["status"]
        if st == "live":
            badge_item = '<span class="reason-tag tag-live">[used]</span>'
            cls_item = "reason-live"
        elif st == "deleted":
            badge_item = '<span class="reason-tag tag-deleted">[DELETED]</span>'
            cls_item = "reason-deleted"
        else:
            badge_item = f'<span class="reason-tag tag-other">[{st}]</span>'
            cls_item = "reason-other"

        cert_reasons_html.append(
            f'<li class="{cls_item}">{badge_item} <span>{lbl}</span> '
            f'<span class="reason-score">(score {sc:.4f})</span></li>'
        )

    rec_fields_str = "\n".join(rec_fields_html)
    cert_reasons_str = "\n".join(cert_reasons_html)

    sub_title = (
        "An evidence record can be marked <strong>COMPLETE</strong> while "
        "four of its five legally-owed reasons are missing due to proof truncation."
    )
    rec_status = rec_d["status"]
    rec_id_esc = html.escape(rec_d["decision_id"])
    rec_duty_esc = html.escape(rec_d["duty"])
    rec_source_esc = html.escape(rec_d["legal_source"])

    cert_verdict = cert_d["verdict"]
    cert_query_esc = html.escape(cert_d["query"])
    cert_adapter_esc = html.escape(cert_d["adapter_name"])
    cert_semantics_esc = html.escape(cert_d["claimed_semantics"])
    reasons_found = cert_d["reasons_found"]
    reasons_deleted = cert_d["reasons_deleted"]

    return f"""
    <section class="key-finding-section" aria-label="Key Empirical Finding">
      <style>
        {_KEY_FINDING_CSS}
      </style>
      <div class="key-finding-banner">
        <div class="kf-badge">Key Empirical Finding</div>
        <div class="kf-title">Form Completeness vs. Reason-Deletion Audit</div>
        <div class="kf-subtitle">
          Demonstrating Table 7 Row 1 (EU AI Act Art. 13) on Decision <code>{rec_id_esc}</code>:
          A system can be 100% compliant in form while dropping 80% of its decision reasons.
        </div>
      </div>
      <div class="key-finding-grid">
        <div class="kf-card kf-card-record">
          <div class="kf-card-header">
            <span class="kf-card-title">Evidence Record</span>
            <span class="badge verdict-satisfied">
              <span aria-hidden="true">✔</span> {rec_status}
            </span>
          </div>
          <div class="kf-card-body">
            <div class="kf-meta-line"><strong>Decision:</strong> <code>{rec_id_esc}</code></div>
            <div class="kf-meta-line"><strong>Duty:</strong> {rec_duty_esc}</div>
            <div class="kf-meta-line"><strong>Source:</strong> {rec_source_esc}</div>
            <div class="kf-subhead">Minimal Evidence Retained (5 of 5 Table 7 fields):</div>
            <ul class="kf-field-list">
              {rec_fields_str}
            </ul>
          </div>
        </div>
        <div class="kf-card kf-card-cert">
          <div class="kf-card-header">
            <span class="kf-card-title">Reason-Deletion Certificate</span>
            <span class="badge verdict-violated">
              <span aria-hidden="true">✖</span> {cert_verdict}
            </span>
          </div>
          <div class="kf-card-body">
            <div class="kf-meta-line"><strong>Query:</strong> <code>{cert_query_esc}</code></div>
            <div class="kf-meta-line">
              <strong>Engine:</strong> <code>{cert_adapter_esc}</code> ({cert_semantics_esc})
            </div>
            <div class="kf-values-bar">
              <span>Exact: <code>{cert_d['exact_value']:.4f}</code></span>
              <span>Engine: <code>{cert_d['engine_value']:.4f}</code></span>
              <span class="kf-gap">Gap: <code>{cert_d['value_gap']:+.4f}</code></span>
            </div>
            <div class="kf-subhead">
              Reason Audit ({reasons_found} found &middot;
              <strong style="color: #dc2626">{reasons_deleted} deleted</strong>):
            </div>
            <ul class="kf-reason-list">
              {cert_reasons_str}
            </ul>
          </div>
        </div>
      </div>
    </section>
"""


def art13_evidence_fields(case: Case, cert) -> dict:
    """The six row-1 fields for one deployer information package.

    Four are provenance the provider supplies and this package only carries. One,
    `fidelity_coverage_metrics`, is the field the package itself computes: the certificate's
    measured fidelity and coverage against exact inference, so the information the deployer gets
    is a measurement, not a claim. The sixth, `explanation_scope`, states what the artifact
    explains and what it does not.
    """
    linkage = "\n".join(
        f"{case.case_id} -> rule {code} on ({', '.join(facts)})"
        for code, _text, facts in CREDIT_REASONS)
    return {
        "model_and_data_version_ids": "model credit-scoring-2026.03.1; rules cs-rules-2026.03; "
                                      "training data snapshot bureau-panel-2025-Q4",
        "extraction_timestamp": "2026-07-31T00:00:00Z (frozen synthetic run: fixed at authoring "
                                "time, not wall-clock)",
        "dataset_snapshot_hash": "sha256:9f3c1b07ad4e (synthetic cohort APP-*, no personal data)",
        "fidelity_coverage_metrics": f"fidelity {conformance.fidelity(cert):.4f}; coverage "
                                     f"{conformance.coverage(cert):.4f} — measured against exact "
                                     f"inference on the same program, not claimed",
        "explanation_scope": "per-decision principal reasons over the adverse-action rule set "
                             f"({len(CREDIT_REASONS)} candidate rules); decision-local, not a "
                             "global account of the model",
        "linkage_from_decision_to_artifact": linkage,
    }


def art13_demo() -> str:
    """EU AI Act Art. 13 end to end: the deployer information package, Table 7 row 1."""
    out = [_head("6. EU AI ACT ART. 13 — TRANSPARENCY AND INFORMATION TO DEPLOYERS "
                 "(Table 7 row 1)")]
    out += ["",
            "Credit scoring is Annex III high-risk, so the provider owes the deployer an "
            "information package, and",
            "row 1 lists what it must retain. Five of the six fields are provenance the provider "
            "hands over; the sixth,",
            "fidelity/coverage, is the one this package computes — measured here on the deployed "
            "top-1 engine against",
            "exact inference on the same program."]
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    cert = certify_case(case, ReferenceAdapter(TopK(1)))
    fields = art13_evidence_fields(case, cert)
    record = emit("eu_ai_act_art13_transparency", case.case_id, fields,
                  attachments={"reason-deletion certificate": cert.render()})
    out += ["", record.render()]
    out += ["",
            "The record is COMPLETE, and its own numbers argue against the engine it documents. "
            f"Coverage {conformance.coverage(cert):.4f}",
            f"means the deployer is told, in the provider's own package, that the stated reasons "
            f"are {len(cert.live)} of",
            f"{len(cert.verdicts)}. That is Art. 13 working as intended: transparency is not the "
            "absence of gaps, it is",
            "the gaps being on the page. A package whose fidelity/coverage figures were asserted "
            "rather than measured",
            "would pass the same form check while saying nothing — which is why this field is "
            "computed from the",
            "certificate and never accepted as input.",
            "",
            "LIMITS: the provenance values above are fixed stand-ins for a synthetic cohort; a "
            "real package draws",
            "them from its model registry and dataset store. The measured field transfers "
            "unchanged."]
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
        art13_demo(),
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    print(main())
