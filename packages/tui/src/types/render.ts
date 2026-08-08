/**
 * The one place any rendering words an evidence basis.
 *
 * The wording is `render.basisSentence` from `packages/core/src/render.ts` and the Python's
 * `docs/semantics.md` §10 — a basis is a *kind*, never a rank, and its sentence carries the rungs
 * the basis admits so the ceiling reads as the duty's, not as an exposure the system withheld.
 *
 * What a reader must not break:
 *
 *   - **The basis sentence is rendered in exactly one place.** A second wording here would be the
 *     second-source-of-truth problem this module exists to prevent.
 *   - **The four sentences are kept verbatim from the Python.** A paraphrase would be this TUI
 *     saying what the basis means in its own voice — which is the move every rule in this
 *     repository is written to prevent.
 */

import type { EvidenceBasis } from "./verdict.ts"

/** The rungs each basis admits. Mirrors `BASIS_RUNGS` in `src/reasonsmith/verdict.py`. */
export const BASIS_RUNGS: Record<EvidenceBasis, readonly string[]> = {
  behavioural: ["unattainable", "observed", "probed", "proved"],
  relational: ["unattainable", "probed", "proved"],
  artifact: ["unattainable", "recounted", "probed"],
  assessment: ["unattainable"],
}

export function basisSentence(basis: EvidenceBasis): string {
  const rungs = BASIS_RUNGS[basis]
  switch (basis) {
    case "behavioural":
      return `evidence about the system's own executions, one at a time (rungs: ${rungs.join(", ")})`
    case "relational":
      return `evidence about a pair of executions — a 2-safety property, which no trace establishes (rungs: ${rungs.join(", ")})`
    case "artifact":
      return `evidence measured against the inference artefact behind a decision (rungs: ${rungs.join(", ")})`
    case "assessment":
      return "a predicate an authority applies rather than anything measured from the system (no rung on the lattice)"
  }
}

/**
 * The limits text every report carries, verbatim from `src/reasonsmith/report.py`. It is rendered
 * on the `limits` route and is also the prompt for the header's `i` key — a reader who wants to
 * know what this report cannot claim is shown the same words the JSON carries.
 */
export const LIMITS_DOCUMENTATION_URL = "https://reasonsmith.dev/limits"
