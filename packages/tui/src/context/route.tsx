/**
 * The route context: which of the screens is showing.
 *
 * Four routes, reduced from the original six. The conformance run happens once before the renderer
 * mounts (`index.tsx`), so a `packs` picker that listed built-ins and a `systems` picker that listed
 * demonstration systems were informational without being able to reload the run. The settings
 * panel already carries the active pack and the active system; the two pickers are removed so the
 * UI does not carry a control whose selection is a no-op.
 *
 *   - `findings` — every requirement result, one row each. The landing screen.
 *   - `detail`   — one result, opened from the list.
 *   - `limits`   — what this report does not claim.
 *   - `settings` — the panel that summarises the keybinds, the audience, the active pack and the
 *     system.
 *
 * What a reader must not break: **`limits` is a route and not a footnote.** `report.limits` states
 * that the report is not a compliance guarantee and that a requirement reported without a strength
 * was not evaluated. `docs/semantics.md` §7 makes it a rule that no audience projection may drop a
 * word of it, and a rendering that buried it below a scroll would be dropping it in practice while
 * passing any test that only asks whether the string is present. So it gets a key of its own, named
 * in the footer of every screen.
 */

import { createSignal } from "solid-js"
import { createSimpleContext } from "./helper.tsx"

export type Route =
  | { type: "findings" }
  | { type: "detail" }
  | { type: "limits" }
  | { type: "settings" }

export const { use: useRoute, provider: RouteProvider } = createSimpleContext({
  name: "Route",
  init: () => {
    const [route, setRoute] = createSignal<Route>({ type: "findings" })
    return {
      route,
      navigate: (next: Route) => setRoute(next),
      /** Back is always to the findings list — the only screen that is a starting point. */
      back: () => setRoute({ type: "findings" }),
    }
  },
})
