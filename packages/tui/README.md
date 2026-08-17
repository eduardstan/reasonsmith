# @reasonsmith/tui — the terminal interface

The OpenTUI renderer for `reasonsmith check`. Every verdict it shows is reached by the Python
package and arrives over one subprocess call to `reasonsmith check ... --json`; this process
imports no engine, loads no pack, and reads no trace itself.

## Requirements

- **Bun 1.3.14** — the version the workspace pins in the root `package.json`'s `packageManager`
  field. Other Bun releases may work; this is the one CI runs.
- **Python `reasonsmith` installed** — either `pip install reasonsmith`, or the contributor
  checkout's virtualenv from `CONTRIBUTING.md` (`pip install -e ".[dev]"`). The TUI shells out
  to it; it does not bundle it.

## Install

From the repository root:

```sh
bun install
```

## Run

Against the shipped demonstration system — a credit system whose notice states one reason while
its own inference used five — with the `ecoa` pack:

```sh
bun run dev:tui -- --system reasonsmith.demo:deployed_credit_system --pack ecoa
```

`--system` accepts either a `decisions.jsonl` path or a `module:attribute` reference to a Python
system (passed through to `reasonsmith check --system-module` automatically, so point it only at
code you trust — the module is imported and executed).

## When Python lives in a virtualenv

The TUI runs `python3` by default. If `reasonsmith` is installed in a virtualenv, name that
interpreter explicitly:

```sh
bun run dev:tui -- --system reasonsmith.demo:deployed_credit_system --pack ecoa \
  --python .venv/bin/python
```

On Windows the interpreter is `.venv\Scripts\python.exe`.

## The rest of the argument grammar

```sh
bun run dev:tui -- --help
```

prints every flag (`--audience`, `--system-scope`, `--system-domain`, `--capabilities`, …). The
compiled binary prints the same text as `reasonsmith-tui --help`. What each flag means for the
verdicts is the Python side's documentation: `reasonsmith check --help`.
