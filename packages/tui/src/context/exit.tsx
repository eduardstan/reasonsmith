/**
 * ExitProvider — the single place this TUI hands control back to the host process.
 *
 * Mirrors nikcli's `src/cli/cmd/tui/context/exit.tsx`. The shape of `init` and the public
 * surface (`exit`, `restart`, `setSummary`) are deliberately identical so a future
 * re-sync against the reference is a one-step diff.
 *
 * Exit-code contract:
 *   - `exit(reason)` exits 1 if `reason` is truthy, 0 otherwise.
 *   - Any error thrown by `onBeforeExit` or `onExit`, or by the renderer teardown,
 *     flips the exit code to 1 and is written to stderr.
 *   - A code of `2` is the conformance tool's signal for a *violated* requirement and
 *     intentionally belongs with the run, not with the UI. This module never sets it.
 *     The TUI can only exit 0 (clean) or 1 (something went wrong leaving the TUI).
 *
 * Terminal restoration:
 *   - On exit we clear the terminal title, destroy the renderer, and restore whatever
 *     raw-mode state the TUI took. The nikcli reference calls `restoreTerminalState`
 *     from a `win32` helper; this project has no equivalent module, so the call is a
 *     documented no-op. Adding a real implementation here would require a platform
 *     check (`process.platform`) and the same `process.exit` ordering as below.
 *
 * Re-entry:
 *   - An `exiting` flag short-circuits a second call to either `exit` or `restart`.
 *     The renderer destroy path is not safe to run twice and `process.exit` does
 *     not return, so a stray second call would otherwise leak teardown errors.
 */
import { useRenderer } from "@opentui/solid"
import { createSimpleContext } from "./helper"

function formatError(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}

export const { use: useExit, provider: ExitProvider } = createSimpleContext({
  name: "Exit",
  init: (input: Readonly<{
    onExit?: () => Promise<void>
    onBeforeExit?: () => Promise<void>
    onRestart?: () => Promise<void>
  }>) => {
    const renderer = useRenderer()
    let exiting = false
    let summary: (() => string | undefined) | undefined

    const writeSummary = () => {
      const text = summary?.()
      if (!text) return
      process.stdout.write(text + "\n")
    }

    const exit = async (reason?: unknown) => {
      if (exiting) return
      exiting = true

      let exitCode = reason ? 1 : 0
      const errors: unknown[] = reason ? [reason] : []

      try {
        await input.onBeforeExit?.()
      } catch (error) {
        errors.push(error)
        exitCode = 1
      }

      try {
        renderer.setTerminalTitle("")
        renderer.destroy()
        if (!reason) writeSummary()
        // win32/restoreTerminalState() would go here; this project has no win32 helper.
      } catch (error) {
        errors.push(error)
        exitCode = 1
      }

      try {
        await input.onExit?.()
      } catch (error) {
        errors.push(error)
        exitCode = 1
      }

      for (const error of errors) {
        process.stderr.write(formatError(error) + "\n")
      }

      process.exit(exitCode)
    }

    const restart = async () => {
      if (exiting) return
      exiting = true

      try {
        await input.onBeforeExit?.()
      } catch {
        // best effort
      }

      try {
        renderer.setTerminalTitle("")
        renderer.destroy()
        // win32/restoreTerminalState() would go here; this project has no win32 helper.
      } catch {
        // best effort
      }

      try {
        await input.onExit?.()
      } catch {
        // best effort
      }

      await input.onRestart?.()
    }

    return {
      exit,
      restart,
      setSummary(fn: () => string | undefined) {
        summary = fn
      },
    }
  },
})