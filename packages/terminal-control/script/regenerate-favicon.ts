#!/usr/bin/env bun
/**
 * Regenerate the PWA web-app-manifest PNG icons from favicon-v3.svg.
 *
 * Output:
 *   - packages/ui/src/assets/favicon/web-app-manifest-192x192.png
 *   - packages/ui/src/assets/favicon/web-app-manifest-512x512.png
 *
 * Run from the monorepo root via:
 *   bun --cwd packages/terminal-control run script/regenerate-favicon.ts
 *
 * (terminal-control has @resvg/resvg-js as an optional dep with the
 * platform-specific native binary properly resolved.)
 */
import { readFile, writeFile } from "node:fs/promises"
import { Resvg } from "@resvg/resvg-js"

const FAVICON_DIR = new URL("../../ui/src/assets/favicon/", import.meta.url).pathname
const SVG_PATH = `${FAVICON_DIR}favicon-v3.svg`
const TARGETS = [
  { file: `${FAVICON_DIR}web-app-manifest-192x192.png`, size: 192 },
  { file: `${FAVICON_DIR}web-app-manifest-512x512.png`, size: 512 },
] as const

const svg = await readFile(SVG_PATH, "utf8")

for (const { file, size } of TARGETS) {
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: size },
    background: "#131010",
    shapeRendering: 2, // geometricPrecision
    imageRendering: 0, // optimizeQuality
  })

  const rendered = resvg.render()
  const png = rendered.asPng()

  if (rendered.width !== size || rendered.height !== size) {
    throw new Error(
      `Unexpected render size for ${file}: got ${rendered.width}x${rendered.height}, expected ${size}x${size}`,
    )
  }

  await writeFile(file, png)
  console.log(`✓ ${file}  (${rendered.width}x${rendered.height}, ${png.length} bytes)`)
}
