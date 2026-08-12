/**
 * The spinner is a clock, not a glyph.
 *
 * The parent owns the glyph, the spinner owns the clock. This is the reason the
 * spinner is reusable across a wide range of cell widths and themes — a widget
 * that owned both would couple the clock to a single layout. The component
 * renders nothing; `onFrame(index)` is the only output, and the parent decides
 * what to print in whatever text node it owns.
 *
 * Visibility handling: the ticker pauses while `document.hidden` is true so a
 * backgrounded tab does not eat cycles advancing an invisible glyph. Guarded
 * for non-DOM environments (bun, SSR, headless).
 */

import { createSignal, onCleanup, onMount } from "solid-js"

const DEFAULT_FRAMES = ["\u280B", "\u2819", "\u2839", "\u2838", "\u283C", "\u2834", "\u2826", "\u2827", "\u2807", "\u280F"]

export function Spinner(props: {
  frames?: readonly string[]
  interval?: number
  onFrame: (index: number) => void
}) {
  const frames = () => props.frames ?? DEFAULT_FRAMES
  const interval = () => props.interval ?? 80
  const [index, setIndex] = createSignal(0)

  let hidden = false
  let timer: ReturnType<typeof setInterval> | null = null

  const tick = () => {
    const next = (index() + 1) % frames().length
    setIndex(next)
    props.onFrame(next)
  }

  const start = () => {
    if (timer !== null) return
    if (hidden) return
    timer = setInterval(tick, interval())
  }

  const stop = () => {
    if (timer === null) return
    clearInterval(timer)
    timer = null
  }

  onMount(() => {
    if (typeof document !== "undefined") {
      const onVisibility = () => {
        hidden = document.hidden
        if (hidden) {
          stop()
        } else {
          start()
        }
      }
      document.addEventListener("visibilitychange", onVisibility)
      hidden = document.hidden
      onCleanup(() => document.removeEventListener("visibilitychange", onVisibility))
    }
    start()
  })

  onCleanup(stop)

  return null
}