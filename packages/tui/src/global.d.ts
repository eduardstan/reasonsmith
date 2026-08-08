/**
 * Make Solid's `JSX.IntrinsicElements` pick up the OpenTUI intrinsic types (`box`, `text`, etc.).
 *
 * Solid ships an empty `JSX.IntrinsicElements` interface and lets downstream libraries extend it.
 * OpenTUI exports its extensions through `@opentui/solid/jsx-runtime`, and that runtime is what
 * every component below depends on at runtime; the type-level wiring is what this file fixes.
 *
 * Without this file, `tsc` resolves `JSX.IntrinsicElements` to Solid's empty interface, the
 * `box` and `text` intrinsics are unknown, and the components fail to compile even though they
 * run cleanly under `bun`. With it, OpenTUI's box/text/scrollbox/etc. props become the types of
 * the matching JSX elements.
 */
import "@opentui/solid/jsx-runtime"

export {}