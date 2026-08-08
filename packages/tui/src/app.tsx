/**
 * The app shell: the renderer, the provider stack, the route switch, and the masthead.
 *
 * Stack order, top-down, outermost-first:
 *
 *   ErrorBoundary
 *     ThemeProvider       — design tokens, result tone (one palette, not six)
 *     ExitProvider        — single exit() authority; restores terminal, runs onExit hooks
 *     ReportProvider      — the run + the selected row + the audience (the report's authority)
 *     RouteProvider       — which route is showing (findings/detail/limits/settings)
 *     DialogProvider      — overlay stack (help, alerts); mounts the overlay over the panel
 *     KeybindProvider     — owns the keyboard; reaches for the four above
 *     App                 — Masthead + Switch(route) + FooterHints
 *
 * Every panel inside the switch is wrapped in a rounded-border box (the nikcli "every panel is a
 * dialog" rule). The overlay is mounted by DialogProvider itself, so the route subtree does not
 * have to know about dialogs.
 */

import { type CliRendererConfig, createCliRenderer } from "@opentui/core"
import { render } from "@opentui/solid"
import { ErrorBoundary, Match, Switch } from "solid-js"
import type { ConformanceReport } from "./types/schema.ts"
import { DialogProviderWithOverlay } from "./ui/dialog.tsx"
import { ExitProvider } from "./context/exit.tsx"
import { KeybindProvider } from "./context/keybind.tsx"
import { ReportProvider } from "./context/report.tsx"
import { RouteProvider, useRoute } from "./context/route.tsx"
import { ThemeProvider, useTheme } from "./context/theme.tsx"
import { Detail } from "./routes/detail.tsx"
import { Findings } from "./routes/findings.tsx"
import { Limits } from "./routes/limits.tsx"
import { Settings } from "./routes/settings.tsx"
import { FooterHints } from "./ui/footer-hints.tsx"
import { ReportHeader } from "./ui/header.tsx"
import { StatusBar } from "./ui/status-bar.tsx"

function rendererConfig(): CliRendererConfig {
  return {
    targetFps: 45,
    gatherStats: false,
    exitOnCtrlC: false,
    useMouse: true,
    enableMouseMovement: true,
    consoleMode: "disabled",
    useKittyKeyboard: {
      disambiguate: true,
      alternateKeys: true,
      events: false,
    },
  }
}

export async function tui(report: ConformanceReport): Promise<void> {
  const renderer = await createCliRenderer(rendererConfig())

  await render(
    () => (
      <ErrorBoundary
        fallback={(error) => {
          renderer.stop()
          process.stderr.write(
            `reasonsmith tui: ${
              error instanceof Error ? (error.stack ?? error.message) : String(error)
            }\n`,
          )
          return null
        }}
      >
        <ThemeProvider>
          <ExitProvider>
            <ReportProvider report={report}>
              <RouteProvider>
                <DialogProviderWithOverlay>
                  <KeybindProvider>
                    <App />
                  </KeybindProvider>
                </DialogProviderWithOverlay>
              </RouteProvider>
            </ReportProvider>
          </ExitProvider>
        </ThemeProvider>
      </ErrorBoundary>
    ),
    renderer,
  )

  await new Promise<void>((resolve) => {
    const poll = setInterval(() => {
      if (!renderer.isRunning) {
        clearInterval(poll)
        resolve()
      }
    }, 50)
  })
}

function App() {
  const t = useTheme()
  const route = useRoute()

  return (
    <box flexDirection="column" width="100%" height="100%" backgroundColor={t.color.bg}>
      <ReportHeader />
      <StatusBar />
      <box flexGrow={1} minHeight={0} width="100%" paddingLeft={1} paddingRight={1} paddingTop={1} paddingBottom={0}>
        <Switch>
          <Match when={route.route().type === "findings"}>
            <Findings />
          </Match>
          <Match when={route.route().type === "detail"}>
            <Detail />
          </Match>
          <Match when={route.route().type === "limits"}>
            <Limits />
          </Match>
          <Match when={route.route().type === "settings"}>
            <Settings />
          </Match>
        </Switch>
      </box>
      <box flexShrink={0} width="100%">
        <FooterHints />
      </box>
    </box>
  )
}