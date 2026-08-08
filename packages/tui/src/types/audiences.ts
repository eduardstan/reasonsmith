/**
 * The five audience projections `reasonsmith check --audience <reader>` selects from, and the
 * rendering flags each one carries.
 *
 * The vocabulary is the Python's own (`docs/semantics.md` §7), re-declared here so the TUI can
 * label and gate its own views by the same names. `auditor` *is* the full report by identity — the
 * default `--audience` matches the auditor projection, and the no-audience run emits the auditor's
 * report verbatim.
 *
 * Acceptance criterion 1 of PR 129 keeps these declarations in this file: `rg -l
 * "packs|Strength|verdict" packages/` returns nothing outside `packages/tui/src/types/`. The TUI's
 * six routes are rendering decisions over `PROJECTIONS`, not the projections themselves.
 *
 * What a reader must not break:
 *
 *   - **Every projection but one *suppresses*.** `plainAccount` is the only field that **emits**,
 *     and it is on for `affected-individual` alone. Built out of suppression flags alone, the lay
 *     view would become a subset of an expert view — its word set a strict subset of the
 *     developer's — and the reader least able to fill a gap in would be handed the most gaps. It
 *     must never become a subset of an expert view again.
 *   - **Three rows no projection may drop: the verdict, the limits, and the undeclared-domain
 *     notice.** No audience may disagree with another about a verdict.
 *   - **`projectionFor` refuses an unknown audience rather than widening to the full report.**
 *     A typo in `--audience` should fail loudly, not silently show everything.
 */

export const AUDIENCES = [
  "developer",
  "deployer",
  "auditor",
  "regulator",
  "affected-individual",
] as const

export type Audience = (typeof AUDIENCES)[number]

export interface AudienceProjection {
  /** The evidence strength (the rung on the lattice). */
  readonly strength: boolean
  /** Declared scope, domains, headline and counts. */
  readonly headline: boolean
  /** The binding/interpretive tag and the duty's scope and domain limits. */
  readonly classification: boolean
  /** Required signal names and the signals absent from the trace. */
  readonly signalNames: boolean
  /** The capability signals a system does not declare. */
  readonly missingCapabilities: boolean
  /** The engine's own account of the evidence (the `evidence_summary` and per-engine panels). */
  readonly evidence: boolean
  /** The search budget a probed claim carries. */
  readonly probeBudget: boolean
  /** Counterexample inputs and the witness records of a violation. */
  readonly witnesses: boolean
  /**
   * The plain-language account of what the system recorded — the one field that emits. Everything
   * it prints is quoted: the decision and the reason out of the JSON record, and a reason left
   * unstated out of the certificate engine's own measurement. It paraphrases no statute and
   * explains no decision.
   */
  readonly plainAccount: boolean
}

/** The full report: every row. `auditor` is this by identity, and so is the no-flag default. */
const FULL: AudienceProjection = {
  strength: true,
  headline: true,
  classification: true,
  signalNames: true,
  missingCapabilities: true,
  evidence: true,
  probeBudget: true,
  witnesses: true,
  plainAccount: false,
}

export const PROJECTIONS: Record<Audience, AudienceProjection> = {
  developer: { ...FULL, classification: false },
  deployer: { ...FULL, signalNames: false, witnesses: false },
  auditor: FULL,
  regulator: { ...FULL, signalNames: false, missingCapabilities: false, witnesses: false },
  "affected-individual": {
    strength: false,
    headline: false,
    classification: false,
    signalNames: false,
    missingCapabilities: false,
    evidence: false,
    probeBudget: false,
    witnesses: false,
    plainAccount: true,
  },
}

/** An unknown audience is refused rather than widened to the full report. */
export function projectionFor(audience: string): AudienceProjection {
  if (!(AUDIENCES as readonly string[]).includes(audience)) {
    throw new Error(
      `Unknown audience ${JSON.stringify(audience)}; valid: ${AUDIENCES.join(", ")}`,
    )
  }
  return PROJECTIONS[audience as Audience]
}

/**
 * The status-bar counters, in the order they appear: from the strongest rung reached down to the
 * weakest verdict, with `not evaluated` and `on an assessment` reported together because they are
 * both *no verdict was reached* — the report keeps them apart so neither can be read as the other.
 */
export const CATEGORY_LABELS: ReadonlyArray<readonly [string, string]> = [
  ["proved", "proved"],
  ["probed", "probed"],
  ["recounted", "recounted"],
  ["observed", "observed"],
  ["violated", "violated"],
  ["inconclusive", "inconclusive"],
  ["not_evaluated", "not evaluated"],
  ["on_an_assessment", "on an assessment"],
  ["unattainable", "unattainable"],
  ["not_applicable", "not applicable"],
] as const
