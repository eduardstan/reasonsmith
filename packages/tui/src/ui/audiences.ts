/**
 * The audience labels, in the order the footer and help dialog show them.
 *
 * Kept in one place so the footer, the help dialog, and the audience-cycling logic all read the
 * same strings. The audience *vocabulary* lives in `types/audiences.ts` (`AUDIENCES` /
 * `PROJECTIONS`); these are the labels this UI puts on them.
 */

import type { Audience } from "../types/audiences.ts"

export type { Audience }

export const AUDIENCE_LABELS: Record<Audience, string> = {
  developer: "developer",
  deployer: "deployer",
  auditor: "auditor",
  regulator: "regulator",
  "affected-individual": "affected individual",
}

/**
 * One-line gloss for each audience. The full projection is in `PROJECTIONS`; this is the caption
 * the help dialog shows beside the name so a reader who picks an audience knows what they will and
 * will not see. The wording is the audience's own purpose, in one sentence.
 */
export const AUDIENCE_HELP: Record<Audience, string> = {
  developer: "every verdict, every rung; drops classification",
  deployer: "every verdict; drops witness records and signal names",
  auditor: "the full report — every row, every flag",
  regulator: "strength + basis + probe budget; drops signal names, missing capabilities, witnesses",
  "affected-individual": "the plain account of what the system recorded",
}
