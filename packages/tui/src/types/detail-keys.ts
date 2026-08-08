/**
 * The keys of `RequirementResult.details` the TUI reads, and the names they have on the TUI side.
 *
 * The Python places its own names in `src/reasonsmith/report.py`. The TUI does not own those names
 * and does not redefine the values it looks them up by — every constant here is *the Python's
 * key*. A renames on the Python side breaks the TUI here; that is the discipline the comment in
 * `PR 129` imposes (a renames that would silently keep the surface working is a renames that has
 * drifted).
 *
 * What a reader must not break:
 *
 *   - **The TUI does not compute these.** Every key here is the Python's own, copied from the
 *     JSON the subprocess emits. The TUI never derives a "vacuous trigger" finding or a "probe
 *     budget" from inputs — both come from the engine that emitted them.
 *   - **`THREE_FIELDS_NOT_IN_JSON_YET` is the open work.** `verbatim_text` and the per-decision
 *     deletion certificate identities are not yet in the Python JSON. The detail panel stubs them
 *     rather than computing them locally; the fields the comment in PR 129 named are owned by the
 *     Python side and arrive when the issues land there.
 */

/** The reason-deletion certificate block, in `details["certificates"]`. */
export const CERTIFICATES_KEY = "certificates"

/** The search budget a probed/recounted claim carries, in `details["probe_budget"]`. */
export const PROBE_BUDGET_KEY = "probe_budget"

/** A truth degree over a residuated lattice, in `details["truth_degree"]`. */
export const TRUTH_DEGREE_KEY = "truth_degree"

/** A vacuous trigger finding, in `details["vacuous_trigger"]`. */
export const VACUOUS_TRIGGER_KEY = "vacuous_trigger"

/** A record of a duty skipped for an undeclared domain, in `details["skipped_for_undeclared_domain"]`. */
export const UNDECLARED_DOMAIN_KEY = "skipped_for_undeclared_domain"

/** A list of signals absent from the trace (different from missing-capability signals). */
export const SIGNALS_ABSENT_FROM_TRACE_KEY = "signals_absent_from_trace"

/** The first witness record of a violation, in `details["offending_trace_segment"]`. */
export const OFFENDING_TRACE_SEGMENT_KEY = "offending_trace_segment"

/** Indices into the trace of violated records, in `details["violation_step_indices"]`. */
export const VIOLATION_STEP_INDICES_KEY = "violation_step_indices"

/** A counterexample input a proved/probed witness produced, in `details["counterexample"]`. */
export const COUNTEREXAMPLE_KEY = "counterexample"

/**
 * The three fields the TUI does not yet have. The Python side adds them in the order this list
 * names; until each one lands, the detail panel stubs the view rather than computing a value that
 * would be its own second source of truth.
 */
export const THREE_FIELDS_NOT_IN_JSON_YET = {
  /** `RequirementResult.verbatim_text` — the clause as the regulation writes it. */
  verbatimText: "verbatim_text",
  /**
   * The per-decision deletion certificate detail — *which* reasons were struck — surfaced at the
   * top of the result rather than only inside `details.certificates[].missing_reasons`.
   */
  deletionCertificate: "deletion_certificate_detail",
} as const
