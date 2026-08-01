"""The demonstrations: ECOA / Reg B credit, GDPR Art. 22 clinical, EU AI Act Art. 13,
EU AI Act Art. 12, FDA GMLP SaMD, and NIST AI RMF 1.0.

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

import hashlib
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
    certs = drift_windows("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88,
                          DRIFT_SIGNALS, 4, topk)
    for w, cert in enumerate(certs):
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
    margin: var(--space-l);
    margin-top: 0;
    border: 1px solid var(--line-strong);
    border-radius: var(--radius);
    background: var(--surface);
    overflow: hidden;
  }
  .key-finding-banner {
    background: var(--ink);
    color: var(--surface);
    padding: var(--space-m) var(--space-l);
    border-bottom: 4px solid var(--accent);
  }
  .kf-badge {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    background: var(--accent);
    color: var(--surface);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    margin-bottom: var(--space-2xs);
  }
  .kf-title {
    font-size: var(--step-2);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.02em;
    text-wrap: balance;
  }
  .kf-subtitle {
    font-size: var(--step--1);
    color: oklch(80% 0.01 260);
    margin-top: var(--space-2xs);
    max-width: 70ch;
    text-wrap: pretty;
  }
  .key-finding-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-m);
    padding: var(--space-m);
    background: var(--neutral-soft);
  }
  @media (max-width: 768px) {
    .key-finding-grid { grid-template-columns: 1fr; }
  }
  .kf-card {
    border-radius: var(--radius);
    border: 1px solid var(--line);
    background: var(--surface);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .kf-card-record {
    border-top: 4px solid var(--ok);
  }
  .kf-card-cert {
    border-top: 4px solid var(--accent);
  }
  .kf-card-header {
    padding: var(--space-xs) var(--space-s);
    background: var(--neutral-soft);
    border-bottom: 1px solid var(--line);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .kf-card-title {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-muted);
  }
  .kf-card-body {
    padding: var(--space-s);
    font-size: var(--step--1);
    flex: 1;
  }
  .kf-meta-line {
    margin-bottom: 0.35rem;
    color: var(--ink-muted);
  }
  .kf-subhead {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-faint);
    margin-top: var(--space-s);
    margin-bottom: var(--space-2xs);
    padding-top: var(--space-2xs);
    border-top: 1px dashed var(--line);
  }
  .kf-field-list, .kf-reason-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .kf-field-list li {
    margin-bottom: 0.35rem;
    line-height: 1.5;
    font-size: 0.8rem;
  }
  .check-icon {
    color: var(--ok);
    font-weight: 800;
    margin-right: 0.25rem;
  }
  .kf-values-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs);
    background: var(--surface);
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
    border: 1px solid var(--line);
    margin: var(--space-2xs) 0;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
  .kf-gap {
    color: var(--accent);
    font-weight: 700;
  }
  .kf-reason-list li {
    position: relative;
    padding: 0.3rem 0.45rem;
    border-radius: 4px;
    margin-bottom: 0.3rem;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .reason-live {
    background: var(--ok-soft);
    border: 1px solid var(--ok-line);
    color: var(--ok);
  }
  .reason-deleted {
    background: var(--accent-soft);
    border: 1px solid var(--accent-line);
    color: var(--accent-deep);
  }
  .reason-deleted::after {
    content: "";
    position: absolute;
    left: 0.3rem;
    right: 0.3rem;
    top: 50%;
    height: 2px;
    background: var(--accent);
    transform: scaleX(0);
    transform-origin: left center;
  }
  .reason-deleted.struck::after {
    transform: scaleX(1);
    transition: transform 0.45s var(--ease-snap);
  }
  @media (prefers-reduced-motion: reduce) {
    .reason-deleted::after { transform: scaleX(1); }
    .reason-deleted.struck::after { transition: none; }
  }
  @media print {
    .reason-deleted::after { transform: scaleX(1) !important; }
  }
  .reason-tag {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.08rem 0.35rem;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    white-space: nowrap;
  }
  .tag-live {
    background: var(--ok);
    color: var(--surface);
  }
  .tag-deleted {
    background: var(--accent);
    color: var(--surface);
  }
  .reason-score {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--ink-faint);
    margin-left: auto;
    font-variant-numeric: tabular-nums;
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
    <style>
{_KEY_FINDING_CSS}
    </style>
    <section class="key-finding-section">
      <div class="key-finding-banner">
        <div class="kf-badge">KEY FINDING</div>
        <h2 class="kf-title">Form Completeness Does Not Imply Reason Fidelity</h2>
        <div class="kf-subtitle">
          {sub_title}
        </div>
      </div>
      <div class="key-finding-grid">
        <div class="kf-card kf-card-record">
          <div class="kf-card-header">
            <span class="kf-card-title">Evidence Record</span>
            <span class="badge verdict-satisfied">
              <span aria-hidden="true">✓</span> {rec_status}
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
              <strong style="color: var(--accent)">{reasons_deleted} deleted</strong>):
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


# ------------------------------------ EU AI Act Art. 12: record-keeping ----

def _sha(text: str) -> str:
    """A short deterministic digest, for log fields that must be reproducible byte for byte."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def art12_event_log(case: Case, cert) -> str:
    """One automatic event-log entry, built from the certificate rather than beside it.

    Row 2 asks each entry to carry timestamp, input/output hashes, the chosen branch, and the
    active constraints. The certificate holds both halves of that: exact inference enumerates
    every constraint that fired, the engine's answer shows which branch was actually chosen. A
    log written from the final answer alone would record the branch and lose the active set —
    the four constraints that fired and never reached the output — which is exactly the
    difference post-market monitoring exists to see.
    """
    query = str(cert.query)
    inputs = "\n".join(f"{a} {p}" for a, p in sorted(case.base.items(), key=lambda kv: repr(kv[0])))
    chosen = ", ".join(v.label.partition(" — ")[0] for v in cert.live) or "(none)"
    active = ", ".join(v.label.partition(" — ")[0]
                       for v in sorted(cert.verdicts, key=lambda v: v.label))
    output = f"{query} = {cert.engine_value:.6f}; stated reasons: {chosen}"
    return "\n".join([
        f"2026-07-31T00:00:00Z event=decision id={case.case_id}",
        f"  input sha256:{_sha(inputs)} ({len(case.base)} evidence facts)",
        f"  output sha256:{_sha(output)} ({output})",
        f"  chosen branch/module: {chosen} (engine {cert.adapter_name})",
        f"  active constraints: {active} ({len(cert.verdicts)} fired)",
        "  violated constraints: not assessed — the certificate measures which constraints "
        "fired and which the engine used; violation status is not part of either",
        f"  active but not in output: {len(cert.deleted)} "
        f"(recorded here; absent from the decision's stated reasons)",
    ])


def art12_evidence_fields(case: Case, cert) -> dict:
    return {
        "automatic_event_logs": art12_event_log(case, cert),
        "retention_schedule": "10 years from placing on the market, WORM-stored, per QMS "
                              "procedure QS-LOG-07",
        "signer": "logging subsystem logd-01, Ed25519 key SHA256:2f8ad1c4 (automated integrity "
                  "signature over each entry; QMS countersignature at quarterly review QS-2026-Q3)",
    }


def art12_demo() -> str:
    """EU AI Act Art. 12 end to end: the automatic event log, Table 7 row 2."""
    out = [_head("7. EU AI ACT ART. 12 — RECORD-KEEPING / EVENT LOGGING (Table 7 row 2)")]
    out += ["",
            "Art. 12 makes the logging subsystem part of the compliance surface: each event "
            "record must name the",
            "chosen branch and the constraints that were active, not just the final answer. The "
            "certificate is the one",
            "place both halves already exist, so the log entry below is built from it — exact "
            "inference supplies the",
            "active set, the engine's answer supplies the choice."]
    case = build_case("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88)
    cert = certify_case(case, ReferenceAdapter(TopK(1)))
    record = emit("eu_ai_act_art12_record_keeping", case.case_id,
                  art12_evidence_fields(case, cert),
                  attachments={"reason-deletion certificate": cert.render()})
    out += ["", record.render()]
    out += ["",
            "Read the log line against the certificate: branch C01 chosen, five constraints "
            "active, four of them absent",
            "from the output. That gap is not an Art. 12 violation — the rule does not say the "
            "engine must use every",
            "constraint — but Art. 12 is what makes the gap retrievable after the fact. A log "
            "that recorded only the",
            "answer would pass the same form check ('automatic event logs: present') while making "
            "post-market",
            "monitoring blind to exactly the event it exists for. Form completeness over a log "
            "that cannot be",
            "interrogated is the row-2 version of the finding in section 1.",
            "",
            "LIMITS: timestamps are fixed and hashes are digests of frozen synthetic inputs, so "
            "the entry reproduces",
            "byte for byte; the signer is a stand-in for a real key-management story this package "
            "does not provide."]
    return "\n".join(out)


# ------------------------------------------ FDA GMLP: SaMD transparency ----

def fda_evidence_fields(case: Case, cert_deployed, cert_exact) -> dict:
    """The three row-5 fields for one design history file entry.

    GMLP asks for a traceable chain from requirement to test to artifact. Here the chain closes
    mechanically: the requirement (no protocol rule silently dropped) is machine-checkable, the
    test is the certificate, and the artifact is the certificate's own output — the first row
    whose verification log can be produced by the tool rather than about it. `change_control`
    records what the PCCP boundary means in measured terms: moving the engine off top-1 changes
    the stated reasons from one to all five, which is exactly the kind of change a PCCP must
    pre-specify.
    """
    links = "\n".join([
        "REQ-TRIAGE-07 \"every withheld fast-track states each protocol rule that fired\"",
        "  -> test VER-TRIAGE-07: reason-deletion certificate on the deployed engine, "
        "verdict must be PASS",
        f"  -> artifact: certificate for decision {case.case_id} "
        f"(engine {cert_deployed.adapter_name}, verdict {cert_deployed.verdict}) — attached",
    ])
    verification = "\n".join(
        f"engine {c.adapter_name}: verdict {c.verdict} "
        f"({len(c.deleted)} of {len(c.verdicts)} reasons deleted, "
        f"value gap {c.value_gap:+.6f})"
        for c in (cert_deployed, cert_exact))
    change = "; ".join([
        "PCCP-2026-02 names the proof-selection setting a controlled parameter",
        f"measured effect of moving off top-1: stated reasons {len(cert_deployed.live)} -> "
        f"{len(cert_exact.live)} of {len(cert_exact.verdicts)}, engine value "
        f"{cert_deployed.engine_value:.6f} -> {cert_exact.engine_value:.6f}",
        "outside the currently approved PCCP boundary: premarket submission required before "
        "deployment",
    ])
    return {
        "design_history_links": links,
        "verification_logs": verification,
        "change_control": change,
    }


def fda_demo() -> str:
    """FDA GMLP end to end: one SaMD triage decision in the design history file, Table 7 row 5."""
    out = [_head("8. FDA GMLP — TRANSPARENCY FOR SaMD (Table 7 row 5)")]
    out += ["",
            "The clinical triage model is software as a medical device, and GMLP wants the design "
            "history file to",
            "trace each requirement to its test and its artifact. The deployed engine keeps the "
            "single best proof;",
            "exact inference is the pre-specified alternative sitting behind the PCCP boundary. "
            "Both are certified."]
    case = build_case("PT-0731", "typical", CLINICAL_QUERY, CLINICAL_REASONS, 0.86)
    cert_deployed = certify_case(case, ReferenceAdapter(TopK(1)))
    cert_exact = certify_case(case, ReferenceAdapter(ExactWMC()))
    record = emit("fda_gmlp_samd", case.case_id,
                  fda_evidence_fields(case, cert_deployed, cert_exact),
                  attachments={"reason-deletion certificate (deployed engine)":
                               cert_deployed.render()})
    out += ["", record.render()]
    out += ["",
            "The chain is honest because the artifact fails the requirement it is filed under: "
            "VER-TRIAGE-07 demands",
            "PASS, the deployed engine's certificate says FAIL, and the record carries that "
            "verdict instead of",
            "re-running until something passes. A design history file that only ever contains "
            "passing artifacts is",
            "not traceability, it is curation. The change-control field is the second half of the "
            "same discipline:",
            "the PCCP boundary is stated as a measured delta — one stated reason versus five — "
            "not as a parameter",
            "name, so a reviewer can see what the boundary costs the patient before deciding "
            "whether to cross it.",
            "",
            "LIMITS: REQ/VER/PCCP identifiers are stand-ins for a real quality system; what "
            "transfers is that the",
            "verification log and the change delta are measured by the certificate, not asserted "
            "about it."]
    return "\n".join(out)


# ------------------------------------------- NIST AI RMF: continuous monitoring ----

# Declared before the run, like the registered hypothesis in section 4: a floor written after
# the numbers are in is not a control. Coverage 0.5 = the engine must depend on at least half the
# reasons exact inference finds; stability 0.8 = the stated reasons may not churn across windows.
NIST_THRESHOLDS = {"coverage": 0.5, "stability": 0.8}

DRIFT_SIGNALS = ("delinquency_on_file", "bureau_record_matched")


def drift_windows(case_id: str, group: str, query_pred: str, reasons, level: float,
                  drift_preds, n_windows: int, adapter) -> list:
    """The same decision re-scored once per window while one signal strengthens.

    The program and the rest of the file are identical across windows; only the facts named in
    `drift_preds` move, by a fixed step per window. One decision re-scored over time is the only
    input `conformance.stability` is defined on, which makes it the unit a continuous monitor can
    honestly log.
    """
    certs = []
    for w in range(n_windows):
        case = build_case(case_id, group, query_pred, reasons, level)
        base = {a: (round(min(0.99, p + 0.06 * w), 4) if a.pred in drift_preds else p)
                for a, p in case.base.items()}
        certs.append(certify(case.program, base, case.query, adapter,
                             exact_depth=1, labels=case.labels))
    return certs


def threshold_alerts(certs, thresholds: dict) -> list[dict]:
    """The declared thresholds against the measured metrics, one window at a time.

    An alert fires at the first window a measured metric sits below its floor, once per metric,
    and records the value actually measured — an alert that restated the number it fired on would
    be the dashboard version of a filled-in gap. A metric not measured in a window can neither
    alert nor clear. The two metrics here are the only ones a one-decision monitor has: coverage
    per window, and cumulative stability over the windows seen so far.
    """
    alerts, fired = [], set()
    for w, cert in enumerate(certs):
        metrics = {"coverage": conformance.coverage(cert),
                   "stability": conformance.stability(certs[:w + 1])}
        for metric, floor in thresholds.items():
            value = metrics[metric]
            if metric not in fired and value is not None and value < floor:
                fired.add(metric)
                alerts.append({"window": w, "metric": metric, "floor": floor, "value": value})
    return alerts


def nist_evidence_fields(certs, alerts, thresholds: dict) -> dict:
    """The three row-6 fields a synthetic monitoring run can produce honestly.

    The fourth, `reviews_and_sign_offs`, is not here and must not be: a review is a human act
    and a frozen run has no human in it. The caller emits the record without that key, and the
    record says so.
    """
    logs = []
    for w, cert in enumerate(certs):
        stated = ", ".join(v.label.partition(" — ")[0] for v in cert.live) or "(none)"
        logs.append(f"window {w}: stated reason {stated}; coverage "
                    f"{conformance.coverage(cert):.4f} (floor {thresholds['coverage']}); "
                    f"stability so far {conformance.stability(certs[:w + 1]):.4f} "
                    f"(floor {thresholds['stability']})")
    declared = "; ".join(f"{m} >= {f}" for m, f in thresholds.items())
    fired = "\n".join(
        f"window {a['window']}: {a['metric']} measured {a['value']:.4f}, below floor {a['floor']}"
        for a in alerts)
    tickets = "\n".join(
        f"INC-2026-0731-{i + 1:02d} (monitor-opened, window {a['window']}): {a['metric']} alert "
        f"on this decision; measured {a['value']:.4f} against floor {a['floor']}. "
        f"OPEN at emission time."
        for i, a in enumerate(alerts)) or "none opened: no threshold was breached"
    return {
        "continuous_monitoring_logs": "\n".join(logs),
        "metric_thresholds_and_alerts": f"declared before the run: {declared}\nalerts fired:"
                                        + (f"\n{fired}" if fired else " none"),
        "incident_tickets": tickets,
    }


def nist_demo() -> str:
    """NIST AI RMF 1.0 end to end: one decision under continuous monitoring, Table 7 row 6."""
    out = [_head("9. NIST AI RMF 1.0 — RISK EVIDENCE AND CONTINUOUS MONITORING (Table 7 row 6)")]
    out += ["",
            "Row 6 asks for risk evidence under continuous monitoring. The monitor is the "
            "machinery already shown:",
            "one adverse action re-scored over six windows while the bureau's delinquency signal "
            "strengthens, a",
            "certificate per window, and Table 19's coverage and stability as the monitored "
            "metrics. The thresholds are",
            "declared before the run:",
            ""]
    out += [f"  {m} floor {f}" for m, f in NIST_THRESHOLDS.items()]
    certs = drift_windows("APP-1042", "typical", CREDIT_QUERY, CREDIT_REASONS, 0.88,
                          DRIFT_SIGNALS, 6, ReferenceAdapter(TopK(1)))
    alerts = threshold_alerts(certs, NIST_THRESHOLDS)
    fields = nist_evidence_fields(certs, alerts, NIST_THRESHOLDS)
    out += ["", "the monitoring log, window by window:", ""]
    out += [f"  {line}" for line in fields["continuous_monitoring_logs"].splitlines()]
    record = emit("nist_ai_rmf_risk_evidence", "APP-1042", fields,
                  attachments={"rule drift report (certificate, final window)":
                               certs[-1].render()})
    out += ["", "The risk evidence register entry this run emits:", "", record.render()]
    out += ["",
            "Two alerts, two findings. The coverage alert fires at window 0: top-1 keeps one "
            "reason of five, so the",
            "deployment was under the floor from the first check — continuous monitoring's first "
            "value is often showing",
            "that a standing configuration was never within limits. The stability alert fires at "
            "window 2, when drift in",
            "the bureau signal replaces the reason stated to the applicant; the rule drift report "
            "attached to the record",
            "is that event's evidence.",
            "",
            "The record is INCOMPLETE, and the missing field is the point. Reviews and sign-offs "
            "are a human act; a",
            "frozen synthetic run has no reviewer, so the field is reported NOT PRODUCED rather "
            "than filled with a",
            "simulated signature. A monitor that could mint its own sign-offs would make the "
            "register worthless.",
            "",
            "LIMITS: the drift here is scripted — one signal on one frozen case — and the "
            "thresholds above are",
            "illustrative, not recommended values. Real monitoring faces unscripted drift on "
            "data this does not have."]
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
        art12_demo(),
        fda_demo(),
        nist_demo(),
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    print(main())
