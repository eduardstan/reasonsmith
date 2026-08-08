/**
 * The report context: the run this TUI is showing, and who it is being shown to.
 *
 * The conformance run happens **once**, before the renderer mounts (`index.tsx`), and this context
 * holds the result. Nothing here recomputes anything: switching audience re-*projects* the same
 * `ConformanceReport`, which is the rule `docs/semantics.md` §7 states for the five audiences —
 * *the projection changes what is shown and never what is claimed*. A verdict one audience is shown
 * is the verdict every audience is shown.
 *
 * What a reader must not break:
 *
 *   - **`AUDIENCES` and `PROJECTIONS` are declared in `types/audiences.ts` and are never
 *     re-declared here.** A second copy of that table in the TUI would be a second place for the
 *     lay projection's rules to drift out of step with the text renderer's, and the flags are
 *     load-bearing: `strength: false` on `affected-individual` is what withholds both the rung and
 *     the evidence basis from the reader who is least able to interpret either.
 *   - **The selected index is clamped, never wrapped past the ends by accident.** `selectNext` at
 *     the last row stays on the last row rather than silently returning to the top, so a reader
 *     scanning downward can tell they have reached the end of the findings.
 */

import { createMemo, createSignal } from "solid-js"
import {
  AUDIENCES,
  PROJECTIONS,
  type Audience,
  type AudienceProjection,
} from "../types/audiences.ts"
import type { ConformanceReport, RequirementResult } from "../types/schema.ts"
import { createSimpleContext } from "./helper.tsx"

export const { use: useReport, provider: ReportProvider } = createSimpleContext({
  name: "Report",
  init: (props: { report: ConformanceReport }) => {
    const report = props.report
    const [audience, setAudience] = createSignal<Audience>("auditor")
    const [selected, setSelected] = createSignal(0)
    const [categoryFilter, setCategoryFilter] = createSignal<string | null>(null)

    const results = (): readonly RequirementResult[] => report.results
    const view = createMemo<AudienceProjection>(() => PROJECTIONS[audience()])

    function clamp(index: number): number {
      const last = results().length - 1
      if (last < 0) return 0
      return Math.min(Math.max(index, 0), last)
    }

    return {
      report,
      results,
      audience,
      /** The projection flags for the current audience. Read from types; never re-derived here. */
      view,
      selected,
      current: (): RequirementResult | null => results()[selected()] ?? null,
      select: (index: number) => setSelected(clamp(index)),
      next: () => setSelected((i) => clamp(i + 1)),
      previous: () => setSelected((i) => clamp(i - 1)),
      first: () => setSelected(0),
      last: () => setSelected(clamp(results().length - 1)),
      setAudience,
      cycleAudience: () =>
        setAudience((a) => AUDIENCES[(AUDIENCES.indexOf(a) + 1) % AUDIENCES.length]),
      categoryFilter,
      setCategoryFilter,
      clearCategoryFilter: () => setCategoryFilter(null),
      audiences: AUDIENCES,
    }
  },
})
