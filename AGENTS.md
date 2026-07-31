# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## The authority

`src/reasonsmith/table7.toml` is a verbatim transcription of Table 7 of *Symbols and Neurons: A
Review of Symbolic XAI in Deep Learning* (Stan, Sciavicco & Napoletano, JAIR 2026, p. 36:22), whose
first author owns this repository. The conformance checks come from Table 19 of the same paper. The
paper is the authority: where a design and the table disagree, the table wins, or the disagreement
is reported as a finding. Do not improve, extend or modernise the wording — the transcription's
value is that a lawyer can check it against the print.

## Dependency

nesyarena supplies the ground-program IR, bounded proof enumeration, the exact WMC oracle and the
adapter protocol. Depend on it; do not reimplement any of those. It is not on PyPI, so
`pyproject.toml` pins it to an immutable commit of the public repo — `pip install -e ".[dev]"` in a
venv is the single install path, and `.github/workflows/ci.yml` uses that same one. Never point it
at a sibling checkout or a branch: the measured numbers must stay reconstructible. `torch` is
deliberately not a declared dependency of *this* package (see README, "Dependencies & PyPI") but
has been installed and measured in a separate environment — see [RESULTS.md](RESULTS.md) for the
exact commands and counts, and do not re-litigate that caveat from stale memory of "torch was never
installed here". `tests/conftest.py` puts `src` on the path so this package itself needs no
install, but nesyarena does. `pip install`ing nesyarena only gets the built package, not its
`tests/`/`experiments/` directories — to run nesyarena's *own* suite (as opposed to depending on
it), clone `github.com/eduardstan/nesyarena` separately and check out the pinned commit.

## Two rules that shaped the code

- No emitted record, certificate or measurement may present itself as complete when it is not, and
  every one carries its own limits. See the module docstrings in `evidence.py` and `certificate.py`
  for why each check exists before changing one.
- No check asserts branding, wording or presentation.

In v0.2 the first rule becomes structural. A verdict carries the strength of the evidence behind it
(`verdict.py`), and `RequirementResult.__post_init__` refuses to construct a result that claims more
than it has — including `strength=None` for "no engine here evaluated this", which is deliberately
not a strength on the lattice. Two consequences worth knowing before editing `report.py`: combining
zero verdicts is `inconclusive`, never vacuously `satisfied`, and `SUPPORTED_FORMALISMS` is the list
of formalisms an engine actually exists for — widen it when the engine lands, not before.

`src/reasonsmith/packs/*.toml` are derived, not authored. The EU AI Act, GDPR and ECOA packs quote
`docs/legal-sources.md`, which is the retrieval record for the official statutory text and the one
place a quote is checked against the law. The Table 7 pack restates the rows of
`src/reasonsmith/table7.toml`, and `test_pack_matches_table7_transcription` holds it to the print:
quoted text character-for-character, both halves of the legal source, and the paper's own
evidence-field keys as the signal names. Do not rename a signal to something tidier — that test is
the only thing keeping the pack attached to the paper.

`docs/example-output.md` is derived too. `tests/test_docs_example_output.py` re-runs every command
block in it and compares stdout byte-for-byte, and cross-checks the header's line count and
`md5sum` against RESULTS.md. So anything that changes what the demo or the CLI prints — a wording
tweak included — means regenerating the transcripts and updating both files' headers together.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
