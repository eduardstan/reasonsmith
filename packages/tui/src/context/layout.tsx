/**
 * The terminal's dimensions, and what this UI does with them.
 *
 * A terminal is not a canvas with a scrollbar — it is a fixed grid that the reader resizes, and
 * anything wider than it is not clipped politely, it wraps into the next row and shears the layout
 * below. So every width in this package is derived here from one measurement, and no component
 * carries a number it guessed.
 *
 * The design rule the breakpoints encode, in one sentence: **decoration goes first, labels go
 * second, and a claim never goes at all.** A narrow terminal loses the ASCII masthead, then the
 * ladder caption, then the words beside the counters — and keeps every verdict, every count and
 * every notice at any width this program will run in. That ordering is not a preference. A rendering
 * that dropped a violated count to fit its own brand mark would be making a presentation decision
 * about a compliance finding, which is the one thing no surface in this repository may do.
 *
 * What a reader must not break:
 *
 *   - **One measurement, read reactively.** `renderer.width`/`height` are read on mount and on every
 *     `resize` event. Components read `measure`, `pad` and `gap`; they do not read the renderer.
 *   - **`measure` is a *text* width, not the panel width.** It already has the app gutter, the panel
 *     border and the panel padding subtracted, so a component may hand it straight to `wrap()`. It is
 *     also capped: prose set across 200 columns is unreadable, and a compliance notice is prose.
 *   - **A cap is measured, never guessed.** Two thresholds started life here as constants — how
 *     many footer hints fit, and how wide a terminal must be for the ladder caption — and both were
 *     wrong the same way: the width of a row's contents is not a function of the terminal's, it
 *     grows with the pack. Where contents can grow, the component measures them against `cols()`
 *     itself. The booleans below are only for elements whose own width is fixed and known.
 *   - **Vertical rhythm collapses before content does.** On a short terminal `gap` goes to 0 and the
 *     headline row is dropped, which buys rows without withholding a finding; the notice is never
 *     dropped, at any height.
 */

import { createContext, createSignal, onCleanup, onMount, useContext, type JSX } from "solid-js"
import { useRenderer } from "@opentui/solid"

/**
 * Terminal widths, in columns. The names are t-shirt sizes because the thresholds are not natural
 * kinds — 88 is where this program's masthead stops fitting beside its own tab row, and 112 is the
 * width the recording harness uses.
 */
export type Breakpoint = "xs" | "sm" | "md" | "lg"

/** The widest a wrapped paragraph is allowed to get, however wide the terminal is. */
const MAX_MEASURE = 92

/** The narrowest paragraph this UI will set rather than give up on. */
const MIN_MEASURE = 24

/**
 * Cells of chrome between the terminal edge and a paragraph inside a route panel: the app's own
 * left/right gutter, the panel border, and the panel's padding. Subtracted once, here, so a panel
 * that wraps to `measure` cannot overflow by the width of its own frame.
 */
const PANEL_CHROME = 8

export interface Layout {
  /** Terminal width in columns. */
  readonly cols: () => number
  /** Terminal height in rows. */
  readonly rows: () => number
  readonly breakpoint: () => Breakpoint
  /** Width to wrap prose to, inside a route panel. Already net of the frame. */
  readonly measure: () => number
  /** Width for a modal panel, never wider than the terminal it floats over. */
  readonly dialogWidth: () => number
  /** Horizontal padding inside a panel: 1 cell, or 0 when every column counts. */
  readonly pad: () => number
  /** Vertical space between blocks: 1 row, or 0 on a short terminal. */
  readonly gap: () => number
  /** The ASCII masthead fits beside the tab row. */
  readonly showMasthead: () => boolean
  /** The counters can afford their words, not just their numbers. */
  readonly showCounterLabels: () => boolean
  /** The report headline row fits without costing a row of findings. */
  readonly showHeadline: () => boolean
}

const LayoutContext = createContext<Layout>()

export function useLayout(): Layout {
  const layout = useContext(LayoutContext)
  if (!layout) throw new Error("useLayout must be used inside a LayoutProvider")
  return layout
}

// eslint-disable-next-line @typescript-eslint/prefer-readonly-parameter-types -- Solid JSX children are immutable at the component boundary.
export function LayoutProvider(props: Readonly<{ children: JSX.Element }>): JSX.Element {
  const renderer = useRenderer()
  const [cols, setCols] = createSignal(renderer.width || 80)
  const [rows, setRows] = createSignal(renderer.height || 24)

  onMount(() => {
    // The event's payload shape is not depended on: the renderer is the authority on its own size,
    // so the handler re-reads it rather than trusting arguments it was handed.
    const onResize = () => {
      setCols(renderer.width || 80)
      setRows(renderer.height || 24)
    }
    onResize()
    renderer.on("resize", onResize)
    onCleanup(() => {
      renderer.off("resize", onResize)
    })
  })

  const breakpoint = (): Breakpoint => {
    const width = cols()
    if (width < 64) return "xs"
    if (width < 88) return "sm"
    if (width < 112) return "md"
    return "lg"
  }

  const clamp = (value: number, low: number, high: number) =>
    Math.min(Math.max(value, low), high)

  const layout: Layout = {
    cols,
    rows,
    breakpoint,
    measure: () => clamp(cols() - PANEL_CHROME, MIN_MEASURE, MAX_MEASURE),
    // A dialog that is wider than the terminal is a dialog with no border on one side.
    dialogWidth: () => clamp(cols() - 8, 32, 78),
    pad: () => (breakpoint() === "xs" ? 0 : 1),
    gap: () => (rows() < 24 ? 0 : 1),
    showMasthead: () => cols() >= 88,
    showCounterLabels: () => cols() >= 72,
    showHeadline: () => rows() >= 22,
  }

  return <LayoutContext.Provider value={layout}>{props.children}</LayoutContext.Provider>
}
