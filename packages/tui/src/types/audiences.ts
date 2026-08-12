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
 *   - **This table is a *checked* copy, not a trusted one.** The record's `audience` block carries
 *     the flags the Python resolved, and `checkAudienceBlock` refuses a run whose projection
 *     disagrees with the one here. The copy has to exist — audience cycling is local and the
 *     subprocess ran once — so the guarantee that can be had is that drift stops the run instead of
 *     showing a reader a projection no Python would emit.
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
 * The Python's own name for each flag above, in `report._audience_block`'s spelling.
 *
 * The table above has to exist — a reader cycles audience with `a` and the run happened once, so
 * there is no second subprocess call to ask the Python what the next projection suppresses. What
 * the record *can* do is settle whether this copy still agrees, for the one audience the run was
 * asked for, and `checkAudienceBlock` makes that a refusal rather than a hope. That is the whole
 * job of this map: it is not a rename, it is the join between two spellings of one table.
 */
const PYTHON_FLAG_NAMES: Record<keyof AudienceProjection, string> = {
  headline: "overview",
  strength: "strength",
  classification: "legal_metadata",
  signalNames: "signals",
  missingCapabilities: "missing_signals",
  evidence: "evidence_summary",
  probeBudget: "probe_budget",
  witnesses: "witnesses",
  plainAccount: "plain_account",
}

/**
 * The `audience` block of the machine record: the projection the run was *asked* for, declared
 * rather than applied. `name` is null when no `--audience` was given, which the Python resolves to
 * the full report — the auditor's projection by identity.
 */
export interface AudienceBlock {
  readonly name: Audience | null
  readonly projection: AudienceProjection
}

/**
 * Parse the record's `audience` block and refuse a projection that disagrees with the table above.
 *
 * A disagreement is not repaired and not preferred one way: it is thrown, naming the flag and both
 * values. The alternative — taking the JSON's flags and rendering with them — would look more
 * deferential and be worse, because the other four projections in this file would go on disagreeing
 * silently while the one the run named quietly agreed. A drifted table is a defect to fix in this
 * file against `src/reasonsmith/render.py`, not a value to paper over at runtime.
 */
export function checkAudienceBlock(value: unknown): AudienceBlock {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("`audience` must be an object")
  }
  const block = value as Record<string, unknown>
  const rawName = block["name"]
  if (rawName !== null && (typeof rawName !== "string" || !(AUDIENCES as readonly string[]).includes(rawName))) {
    throw new Error(
      `audience.name is not a recognised audience (or null): ${JSON.stringify(rawName)}; ` +
        `valid: ${AUDIENCES.join(", ")}`,
    )
  }
  // A null name is the full report, which `auditor` is by identity — so even a run given no
  // `--audience` checks one row of the table rather than none.
  const name = (rawName as Audience | null) ?? null
  const projection = PROJECTIONS[name ?? "auditor"]
  for (const [flag, pythonName] of Object.entries(PYTHON_FLAG_NAMES) as [
    keyof AudienceProjection,
    string,
  ][]) {
    const reported = block[pythonName]
    if (typeof reported !== "boolean") {
      throw new Error(
        `audience.${pythonName} must be a boolean; got ${JSON.stringify(reported)}`,
      )
    }
    if (reported !== projection[flag]) {
      throw new Error(
        `the audience projection in this build disagrees with the one the Python reported for ` +
          `${JSON.stringify(name)}: \`${flag}\` is ${projection[flag]} here and ` +
          `\`${pythonName}\` is ${reported} there. The Python owns the projection ` +
          "(`src/reasonsmith/render.py`); fix `PROJECTIONS` in this file to match it.",
      )
    }
  }
  return { name, projection }
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
