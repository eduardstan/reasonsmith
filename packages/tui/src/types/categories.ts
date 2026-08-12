/**
 * Which category of the status bar a result falls in — the one predicate, used by the counter row
 * and by the list it filters.
 *
 * The categories and their membership tests are `_category_counts` in `src/reasonsmith/report.py`.
 * Nothing is counted here: the numbers on screen are the Python's `counts`, read straight off the
 * record. What this file settles is the *inverse* question the counters raise the moment they are
 * clickable — given a category, which rows are the ones that number counted — and it has to answer
 * it exactly as the Python answered the forward one, or a reader is shown a list that contradicts
 * the number they clicked.
 *
 * What a reader must not break:
 *
 *   - **The unprefixed counts are binding-only, so the filter is too.** `counts.violated` counts the
 *     `binding_total` binding requirements and nothing else; a recital informs how a duty is read
 *     but creates no obligation of its own, and the Python keeps the two halves under separate keys
 *     precisely so neither number can be read as the other. A filter that answered `3 violated` with
 *     five rows would undo that split at the last step, in the one place a reader is most likely to
 *     believe the two agree — they clicked the number to see them.
 *   - **There is one copy of this predicate.** It lived twice, in `routes/findings.tsx` and in
 *     `ui/status-bar.tsx`, and the two had already drifted: the unknown-key fallback returned `true`
 *     in one and `false` in the other, so an unrecognised category showed every row in the list and
 *     selected none of them in the bar.
 *   - **An unknown key matches nothing.** `false` is the safe fallback of the two: a category this
 *     build has no test for shows an empty list, which reads as *nothing here*, where `true` would
 *     show every row and read as *all of these*.
 */

import type { RequirementResult } from "./schema.ts"

/**
 * True when `result` is one of the requirements `counts[key]` counted.
 *
 * Mirrors `_category_counts`, including its two subtleties: the four rung categories count
 * *satisfied* results at that rung and nothing else, so a duty violated at `probed` is `violated`
 * and never `probed`; and `not_evaluated` and `on_an_assessment` split the same `strength === null`
 * population by evidence basis, because a solver that fell short and a predicate no rung was ever
 * going to rank are not one finding.
 */
export function matchesCategory(result: RequirementResult, key: string): boolean {
  // Every unprefixed count in the record covers the binding requirements alone.
  if (!result.binding) return false
  switch (key) {
    case "proved":
    case "probed":
    case "recounted":
    case "observed":
      return result.verdict === "satisfied" && result.strength === key
    case "violated":
      return result.verdict === "violated"
    case "inconclusive":
      return (
        result.verdict === "inconclusive" &&
        result.strength !== null &&
        result.strength !== "unattainable"
      )
    case "not_evaluated":
      return (
        result.strength === null &&
        result.verdict !== "not_applicable" &&
        result.basis !== "assessment"
      )
    case "on_an_assessment":
      return (
        result.strength === null &&
        result.verdict !== "not_applicable" &&
        result.basis === "assessment"
      )
    case "unattainable":
      return result.strength === "unattainable"
    case "not_applicable":
      return result.verdict === "not_applicable"
    default:
      return false
  }
}
