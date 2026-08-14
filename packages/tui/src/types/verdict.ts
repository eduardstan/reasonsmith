/**
 * The verdict, the strength lattice, and the evidence basis.
 *
 * These names are *declared here because the Python is the authority and the JSON is the contract.*
 * `docs/semantics.md` is the source, and `src/reasonsmith/verdict.py` is what every reported value
 * comes from. The TypeScript copy exists so the TUI can render what the JSON carries and refuse what
 * the JSON never says — anything outside these vocabularies is not a verdict.
 *
 * Acceptance criterion 1 of PR 129 keeps these declarations here: `rg -l "packs|Strength|verdict"
 * packages/` returns nothing outside `packages/tui/src/types/`. No duty, rung or verdict is defined
 * anywhere else.
 */

/** The four values a JSON `verdict` field can carry. */
export type Verdict = "satisfied" | "violated" | "inconclusive" | "not_applicable"

/** The operational outcome carried additively beside the compatibility verdict and strength. */
export type OperationalOutcome =
  | "satisfied"
  | "violated"
  | "not_applicable"
  | "not_evaluated"
  | "unattainable"

/** The five values a JSON `strength` field can carry, plus `null` for `not evaluated`. */
export type Strength = "unattainable" | "observed" | "recounted" | "probed" | "proved"

export type StrengthOrNull = Strength | null

/** The four evidence bases `docs/semantics.md` §10 names — a *kind*, never a rank. */
export type EvidenceBasis = "behavioural" | "relational" | "artifact" | "assessment"

export function isOperationalOutcome(value: string): value is OperationalOutcome {
  return (
    value === "satisfied" ||
    value === "violated" ||
    value === "not_applicable" ||
    value === "not_evaluated" ||
    value === "unattainable"
  )
}

export const VERDICTS: readonly Verdict[] = [
  "satisfied",
  "violated",
  "inconclusive",
  "not_applicable",
] as const

export const STRENGTHS: readonly Strength[] = [
  "unattainable",
  "observed",
  "recounted",
  "probed",
  "proved",
] as const

export const BASISES: readonly EvidenceBasis[] = [
  "behavioural",
  "relational",
  "artifact",
  "assessment",
] as const

/**
 * The semantics an inference artefact may claim, from `spec.CLAIMED_SEMANTICS`.
 *
 * Closed on the Python side deliberately, so that a consumer may *compare* two declarations without
 * treating an author's prose as a new semantics it has to interpret. The TUI's job with a closed
 * vocabulary is the same as with the other four: refuse a value outside it where it is read, rather
 * than printing an unknown string beside a measured one as though the pair meant something.
 */
export type ClaimedSemantics = "distribution semantics" | "weighted sum" | "free-text rationale"

export const CLAIMED_SEMANTICS: readonly ClaimedSemantics[] = [
  "distribution semantics",
  "weighted sum",
  "free-text rationale",
] as const

export function isClaimedSemantics(value: unknown): value is ClaimedSemantics {
  return typeof value === "string" && (CLAIMED_SEMANTICS as readonly string[]).includes(value)
}

/** A `strength` is a value of `Strength | null`; `null` means *not evaluated*. */
export function isStrength(value: unknown): value is Strength {
  return typeof value === "string" && (STRENGTHS as readonly string[]).includes(value)
}

export function isVerdict(value: unknown): value is Verdict {
  return typeof value === "string" && (VERDICTS as readonly string[]).includes(value)
}

export function isBasis(value: unknown): value is EvidenceBasis {
  return typeof value === "string" && (BASISES as readonly string[]).includes(value)
}

/**
 * Whether a verdict was *reached* at all. `inconclusive` is a verdict; `not_applicable` is not.
 * This is the predicate the lay projection's *no verdict here* block turns on, and a counter that
 * conflates the two would tell a reader a clean run where there was none.
 */
export function evaluated(verdict: Verdict): boolean {
  return verdict !== "not_applicable"
}
