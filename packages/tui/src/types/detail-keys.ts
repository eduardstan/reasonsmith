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
 *   - **Nothing here is stubbed for a field the Python has not got yet.** Both fields this file
 *     once listed as open work have landed: `verbatim_text` is a top-level key of every result and
 *     is typed in `./schema.ts`, and the per-decision certificate identities are `CERTIFICATE_KEY`
 *     below. A list of things the Python does not carry goes stale the moment it does carry them,
 *     and a stub left behind it renders as an absence a reader reads as a finding.
 */

/** The reason-deletion certificate summary, one entry per certified decision, in `details["certificates"]`. */
export const CERTIFICATES_KEY = "certificates"

/**
 * The full machine record the summary condenses, in `details["certificate"]` — one entry per
 * certified decision, carrying the semantics the artefact *claimed*, the semantics it was measured
 * *against*, and the gap between the two.
 *
 * Present only where the certificate engine settled the duty. Absence means no certificate exists,
 * never an empty measurement, and the two must not render alike.
 */
export const CERTIFICATE_KEY = "certificate"

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
