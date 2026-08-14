import { describe } from "bun:test"

/**
 * `describe` for a block that needs a real pseudo-terminal.
 *
 * `bun-pty` cannot open one on Windows: `new Terminal` throws `PTY spawn failed` from its own
 * constructor, before any code in this package runs. A suite that cannot pass on a platform is
 * worse than one that says which blocks it did not run — so the PTY-backed blocks are skipped
 * there, and the screen parser, the renderers and the recorder, which need no terminal, still run
 * everywhere.
 *
 * CI runs `packages/**` on `ubuntu-latest` only, so nothing here is skipped in CI today. The
 * platform this matters on is a contributor's.
 */
export const describePty = process.platform === "win32" ? describe.skip : describe

/**
 * `describe` for a block that shells out to a POSIX command through the native
 * `@kitlangton/terminal-control` binary.
 *
 * Two reasons it cannot run on Windows, and either alone is enough: the package resolves no
 * binary for the platform (`resolveTerminalControlBinary` throws in its own constructor), and the
 * commands under test are `/bin/sh` invocations. Same rule as {@link describePty} — say which
 * blocks did not run rather than ship a suite that cannot pass.
 */
export const describeNativeBinary = describePty
