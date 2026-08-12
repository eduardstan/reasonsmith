/**
 * The theme context — enterprise palettes with invariant verdict semantics.
 *
 * nikcli loads sixty JSON palettes; this TUI carries three enterprise chrome palettes while
 * keeping verdict colours fixed. Colours live in a Solid store so palette switches re-render
 * every panel without touching individual components.
 */

import { createEffect, createSignal } from "solid-js"
import { createStore } from "solid-js/store"
import { createSimpleContext } from "./helper.tsx"
import { A, resultTone, strengthWord } from "../theme.ts"
import {
  type PaletteId,
  VERDICT,
  getPalette,
  nextPalette,
  PALETTE_IDS,
  type Palette,
} from "../theme/palettes.ts"

function chromeFor(id: PaletteId) {
  return { ...getPalette(id).chrome, ...VERDICT }
}

export const { use: useTheme, provider: ThemeProvider } = createSimpleContext({
  name: "Theme",
  init: () => {
    const [paletteId, setPaletteId] = createSignal<PaletteId>("enterprise-dark")
    const [color, setColor] = createStore(chromeFor("enterprise-dark"))

    createEffect(() => {
      setColor(chromeFor(paletteId()))
    })

    const palettes = (): readonly Palette[] => PALETTE_IDS.map((id) => getPalette(id))

    return {
      paletteId,
      palettes,
      setPalette: setPaletteId,
      cyclePalette: () => setPaletteId((id) => nextPalette(id)),
      color,
      attr: A,
      resultTone,
      strengthWord,
    }
  },
})
