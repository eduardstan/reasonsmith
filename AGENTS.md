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
adapter protocol. Depend on it; do not reimplement any of those. `pyproject.toml` pins
`nesyarena==0.1.0` from PyPI — `pip install reasonsmith` is the user install, and
`pip install -e ".[dev]"` in a venv is the contributor install, the one CI
(`.github/workflows/ci.yml`) runs. Never point it at a sibling checkout, tag, or a
branch: the measured numbers must stay reconstructible. `torch` is
deliberately not a declared dependency of *this* package (see README, "Dependencies & PyPI") but
has been installed and measured in a separate environment — see [RESULTS.md](RESULTS.md) for the
exact commands and counts, and do not re-litigate that caveat from stale memory of "torch was never
installed here". `tests/conftest.py` puts `src` on the path so this package itself needs no
install, but nesyarena does. `pip install`ing nesyarena only gets the built package, not its
`tests/`/`experiments/` directories — to run nesyarena's *own* suite (as opposed to depending on
it), clone `github.com/eduardstan/nesyarena` separately and check out
`22b539bad6c3510fe457aa751141c5c4aa1483ea`, the commit 0.1.0 was built from (RESULTS.md, "PyPI
Release Note", records how that was verified; the repo publishes no tag).

## Two rules that shaped the code

- No emitted record, certificate or measurement may present itself as complete when it is not, and
  every one carries its own limits. See the module docstrings in `evidence.py` and `certificate.py`
  for why each check exists before changing one.
- No check asserts branding or presentation. Limits tests pin semantic boundary clauses, not full
  prose.

In v0.2 the first rule becomes structural. A verdict carries the strength of the evidence behind it
(`verdict.py`), and `RequirementResult.__post_init__` refuses to construct a result that claims more
than it has — including `strength=None` for "no engine here evaluated this", which is deliberately
not a strength on the lattice. Three consequences worth knowing before editing `report.py`: combining
zero verdicts is `inconclusive`, never vacuously `satisfied`; `SUPPORTED_FORMALISMS` is the list
of formalisms an engine actually exists for — widen it when the engine lands, not before; and a
`probed` result cannot be constructed without the search budget that produced it
(`PROBE_BUDGET_KEY` / `PROBE_BUDGET_FIELDS`), so the bound travels with the verdict into every
rendering instead of being a rendering convention. Which engine a `logical` requirement reaches is
decided by what the system exposes: `logic()` gets Z3, `decide()` alone gets the replay search in
`engines/probed.py`.

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
`docs/report.html` is generated as well, but not by the CLI: `docs/build_example.py` composes it — the
Table 7 run declared into the high-risk class, beside the demonstration's key finding, which no
report the CLI writes may carry — and `test_docs_index_html_matches_the_renderer` holds the
committed page byte-for-byte to that script. Touching the renderer means regenerating the page with
`python docs/build_example.py`, the command the page names as its own provenance. The website
(landing, vendored libraries, fonts, assets) lives in the separate private `reasonsmith-site`
repo and deploys to Vercel — see issue #35; this repo only generates the dossier that gets
published there as `report.html`.

`docs/nesyarena-conformance-report.md` is the third generated document, and the only run against a
real system rather than a demonstration fixture: `docs/build_nesyarena_report.py` drives the five
`nesyarena.suts.registry()` provenances over generated ground programs against the GDPR, EU AI Act
and ECOA packs, and `test_nesyarena_report_matches_the_builder` holds the committed file to it
byte-for-byte. Anything that moves `render_text`'s wording, the nesyarena version or the builder's
own constants means regenerating with `python docs/build_nesyarena_report.py`. Like
`docs/index.html`, it names its build command and deliberately carries no commit hash; reproducibility
is owned by the byte-for-byte builder test, so do not add a hash back. Its adapter declares only
signals a provenance genuinely emits, so nine pack signals are deliberately undeclared and no
regulatory class is declared; the resulting unattainable and not-applicable verdicts are the
finding, not a gap to close.
`docs/findings-nesyarena.md` is the written account and is hand-maintained — every number in it
comes from that report, so regenerating one means rereading the other.

`docs/semantics.md` states what each verdict means and what it does not, and every claim in it names
the test that fails if the claim becomes false. `tests/test_docs_semantics.py` checks that mapping,
so **renaming or deleting a test breaks the build if that test is named there** — update the
document in the same commit. It is also where a claim the code cannot support belongs: report the
gap in the document rather than describing a tool that does not exist.

## The web home and the install surface

The live home is `https://reasonsmith.dev` (landing) with the conformance dossier at
`https://reasonsmith.dev/report.html`; the old `eduardstan.github.io/reasonsmith` Pages URL is
superseded and nothing should reintroduce it. `reasonsmith` 0.2.0 is published on PyPI:
`pip install reasonsmith` is the user install the README's Quick Start leads with, and
`pip install -e ".[dev]"` in a venv is the contributor install the README keeps below it
for running the suite from a checkout. The forbidden string appears here deliberately:
this paragraph is the statement of the rule, and a rule that cannot name what it forbids
is not a rule — any repository-wide check for it must exclude this file.

## The front door

Before editing the CLI, read the maintenance contracts in `src/reasonsmith/cli.py`'s module
docstring. README, "The CLI", owns user-facing usage, and `docs/authoring-packs.md` owns the
pack-authoring rules.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
