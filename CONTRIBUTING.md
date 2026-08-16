# Contributing to reasonsmith

Thank you for your interest in contributing to `reasonsmith`. See [`GOVERNANCE.md`](GOVERNANCE.md) for contributor governance and compensation commitments.

The terminal interface and recording harness were contributed by **nikomatt69**.

## Development Environment Setup

Follow the single pinned installation path:

```sh
git clone https://github.com/eduardstan/reasonsmith.git
cd reasonsmith
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

*Note:* `nesyarena` is pinned to `nesyarena==0.1.0` on PyPI in `pyproject.toml`. Do not point it at a local sibling checkout or branch when submitting PRs, as measurements must remain reconstructible.

## Running Tests and Linters

Before submitting a pull request, run the verification commands relevant to your change:

```sh
ruff check .
pytest
python -m reasonsmith.demo
reasonsmith init pack example_pack
reasonsmith init engine example_engine
reasonsmith validate-pack ecoa --analyse
reasonsmith verify-engine my_engine:engine
```

The scaffold commands write their named directories; remove those directories after inspection.
Replace `my_engine:engine` with the module and attribute for the engine you are verifying. All
commands must pass cleanly with zero errors or warnings. Continuous integration
(`.github/workflows/ci.yml`) runs the lint and test suite for every pull request and for pushes to
`main`; a push to a pull-request branch is covered by the pull-request run rather than a duplicate
push run.

## Roadmap & What to Work On

**The roadmap lives in [`ROADMAP.md`](ROADMAP.md)**, not here: each numbered objective records its
status, measurable outcome, dependencies and remaining limits, plus what is deliberately not
planned. Read it before proposing work. What follows is the status summary and the smaller items
that are not objectives in their own right.

### Project Status

| Category | Status | Details |
|---|---|---|
| **What is built** | Current release (v0.10.2) | The package has witness-checked engine boundaries, neural systems as first-class subjects with an honest bounded ceiling, measurement-only statistical evidence, the Seoul Frontier AI Safety Commitments pack, and the EU AI Act Article 86 duty contributed externally. Event-time bounded response is now supported, including the Cyber Resilience Act Article 14(2)(a) 24-hour duty landed in PR [#247](https://github.com/eduardstan/reasonsmith/pull/247). The package modules live under [`src/reasonsmith/`](src/reasonsmith/), and [`docs/README.md`](docs/README.md) indexes the documents that explain them. |
| **Deliberately NOT done** | Out of Scope | Web/GUI dashboards — the `--html` report is one static offline file, not a served application — reimplementing `nesyarena` IR or oracle engines, generating automated legal opinions, or making un-hedged legal compliance guarantees. |

### Concrete Open Work for Contributors

The demonstrations **Issue 6** asked for — rows 1, 2, 5 and 6 — have landed, so every Table 7 row now has one. What is still open:

- **The open objectives in [`ROADMAP.md`](ROADMAP.md)**, which is where the substantial work is.
- **The live issue board, [issues 237–244](https://github.com/eduardstan/reasonsmith/issues)**, including the temporal-rule-set work now tracked by [#237](https://github.com/eduardstan/reasonsmith/issues/237).
- **Anything labelled [`good first issue`](https://github.com/eduardstan/reasonsmith/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)** or [`help wanted`](https://github.com/eduardstan/reasonsmith/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22).

For new regulation packs, use the [pack proposal form](.github/ISSUE_TEMPLATE/pack_proposal.yml). For engines and verifiers, use the [engine proposal form](.github/ISSUE_TEMPLATE/engine_proposal.yml); for a system or model, use the [system/model proposal form](.github/ISSUE_TEMPLATE/sut_model_proposal.yml). Extending an engine or bringing a well-described system, rather than adding another demo, is now the concrete, high-impact contribution.

## Standing Rules for Changes

1. **Table 7 and Legal Quotes Are Verbatim:**
   `src/reasonsmith/table7.toml` and statutory text quotes in `src/reasonsmith/packs/*.toml` reproduce published papers and official statutory texts (`docs/legal-sources.md`). They are guarded by automated tests: `test_pack_matches_table7_transcription` holds the Table 7 pack to `table7.toml`, and `test_pack_quotes_found_verbatim_in_legal_sources_report` holds every statutory quote to `docs/legal-sources.md`. Do not tidy, modernize, or alter quotes of law or Table 7 wording.

2. **No Satisfied Verdicts on Absent Evidence:**
   Nothing in `reasonsmith` may report `satisfied` or `COMPLETE` on missing or incomplete evidence. Default values or fallbacks must never be substituted for missing fields.

3. **Preserve the Non-Pass Distinctions:**
   Do not combine unattainable, not-evaluated, and not-applicable results or treat any of them as a
   pass. Their authoritative contracts and invariants live in `verdict.py` and `report.py`; the
   user-facing explanation lives in [`docs/theory/08-evidence.md`](docs/theory/08-evidence.md) §8.1, with the shorter
   statements in the README's *Limits* section and
   [`docs/what-this-does-not-do.md`](docs/what-this-does-not-do.md) §3.

4. **What Makes a Good Change:**
   - Minimal, focused diffs addressing a specific requirement or issue.
   - Accompanying unit tests in `tests/`.
   - Complete adherence to existing module docstring shapes and safety boundaries.

## Versioning and Releases

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Below 1.0 the
shape is `0.y.z`: a **breaking** change bumps `y`, everything else bumps `z`, and there is no
major bump available below 1.0. **1.0.0 is a promise of a stable public interface, and this
project is not ready to make it.** The absence of a 1.0.0 is a decision, not an oversight.

Every `CHANGELOG.md` entry links the pull request that introduced it.

The version lives in **four** places and they are bumped together, in one change:

1. `version` in `pyproject.toml`
2. the topmost released heading in `CHANGELOG.md` — close `[Unreleased]` into the new version
   and open a fresh `[Unreleased]`
3. `__version__` in `src/reasonsmith/__init__.py`
4. `version` in `CITATION.cff`

Then publish a GitHub Release whose tag is `v<version>`. `.github/workflows/publish.yml`
does the PyPI upload by trusted publishing; there is no token anywhere.

`tests/test_release_discipline.py` holds all four to one another, and `publish.yml` refuses to
build a release whose tag is not `v` plus that version.

## Reporting Issues

**A suspected vulnerability is not a bug report.** Do not open a discussion, an issue, or a pull request for one. Report it privately, to the email address in [SECURITY.md](SECURITY.md), which owns the reporting process, the scope, and the response times for security reports.

For a bug, question, proposal, or help request:
1. **Questions go to [GitHub Discussions](https://github.com/eduardstan/reasonsmith/discussions)**; issues use the available forms for bugs, packs, engines, and systems/models. Good-first-issue and help-wanted work is also listed on the issue board.
2. Check the existing discussions or issues before starting a new one.
3. Pick the matching template from `.github/ISSUE_TEMPLATE/` — GitHub offers it automatically, and each form applies its own label (see [Labels](#labels)). The **Bug report**, **Pack proposal**, **Engine proposal**, and **System or model proposal** forms each describe the evidence needed to make the work actionable.

## Response times

We aim to acknowledge a contribution within one week and to give it an initial review within two weeks. A release or other urgent work can make the review take longer; a friendly ping after either window is welcome, never rude.

## Attribution convention

Commit messages, pull-request bodies, and pull-request comments should not include an AI co-author trailer or an AI-attribution footer. Disclosing AI use is fine; the ideas and invention belong to the author, and a tool gets no authorship credit, just as a compiler or proof assistant does not. Human co-author trailers remain welcome. This is a contributor-facing convention, not an automated check: no build, test, lint rule, or CI job enforces it.

## Submitting Pull Requests

1. Create a focused topic branch (`git checkout -b my-feature-branch`).
2. Implement your change with tests.
3. Verify that `ruff check .`, `pytest`, and `python -m reasonsmith.demo` pass.
4. Open a Pull Request targeting `main`, referencing any open issue it addresses (e.g., `Fixes #123`). The concise template in `.github/PULL_REQUEST_TEMPLATE.md` is shown automatically.
5. **No AI co-author trailers:** Do not include automated co-author trailers in commit messages.

### Labels

Every issue and pull request carries at least one label. A label is how a reader filters a list they did not write; an unlabelled item is findable only by whoever remembers it.

Issues opened through a form are labelled automatically — **Bug report** carries `bug`, **Pack proposal** carries `pack`, **Engine proposal** carries `wanted: engine`, and **System or model proposal** carries `wanted: model/SUT`. An issue opened through the API or `gh issue create` bypasses the form and arrives with none, so add one or say which it should have.

A pull request has no form and no automatic label, and **applying a label needs triage permission, which an outside contributor does not have**. So the convention is: name the intended label under *Intended label* in the pull-request description, and a maintainer applies it. Dependabot labels its own.

Beyond GitHub's defaults, the labels in use are `pack`, for a regulation pack, and `dependencies`, `javascript` and `github_actions`, which Dependabot creates as it needs them.

### Pull-Request Titles and the Squash Merge

reasonsmith normally **squash-merges** pull requests. On that path, GitHub collapses the branch's commits and writes the pull-request **title** onto `main` as the commit subject, appending `(#NN)` — the PR number. The individual branch commits do not appear in the history.

PRs [#31](https://github.com/eduardstan/reasonsmith/pull/31) and [#32](https://github.com/eduardstan/reasonsmith/pull/32) are one deliberate exception sequence: the first reverted a squash that had erased an outside contributor's authorship, and the second re-landed the contributor's commits with a merge commit so that authorship survived. If keeping your individual commits in the history matters to you, ask for that in the pull-request description.

That is where the convention is strict, and only there:

- **The title becomes the history on the normal squash path**, so it must follow the conventional-commits form below. Reviewers read titles as the permanent record; expect a non-conforming title to be asked to change. There is no automated check that fails your build over a message — the convention is guidance, applied in review.
- **Branch commits are normally collapsed on merge**, so keep them tidy and reasonably atomic while you work, but you will not be sent back to rewrite them.

### Pull-Request Title Form

Pull-request titles follow **Conventional Commits**: `<type>: <summary>` or
`<type>(<scope>): <summary>`.

- `type` is the change's kind. Types already present on `main` are `feat`, `fix`, `docs`, `build`, and `revert`; use one when it fits. Other Conventional Commit types are welcome, and on the normal squash path the pull-request title is likewise what lands in history.
- `scope` is optional and names the part of the codebase the change touches (`engines`, `cli`, `packs`, `report`, `drift`, `reasonsmith`, …). When in doubt, omit it.
- `summary` is short, imperative, lowercase, and has no trailing period: *add*, *fix*, *document* — not *added* or *Adding*.

One real example of each type, exactly as each reads in `main`'s history today. GitHub
appended the `(#NN)` suffix to each squash-merged subject; the merge-commit exception did not:

| Type | Example | PR |
|---|---|---|
| `feat` — a new capability | `feat(engines): add active probing for opaque decision systems (#37)` | [#37](https://github.com/eduardstan/reasonsmith/pull/37) |
| `fix` — a bug corrected | `fix: depend on nesyarena==0.1.0 from PyPI instead of a git commit pin (#26)` | [#26](https://github.com/eduardstan/reasonsmith/pull/26) |
| `docs` — documentation only | `docs: define verifiable verdict semantics (#38)` | [#38](https://github.com/eduardstan/reasonsmith/pull/38) |
| `build` — packaging, dependencies, CI | `build(reasonsmith): pin nesyarena by commit and run the same install path in CI (#2)` | [#2](https://github.com/eduardstan/reasonsmith/pull/2) |
| `revert` — undoes an earlier change | `revert: undo the squash merge of #30 so the contributor commits can land with their authorship` | [#31](https://github.com/eduardstan/reasonsmith/pull/31) |

Put issue references (`Fixes #123`) in the pull-request **description**, not the title — the description closes the issue on merge, and the title would otherwise carry the reference into the commit subject.

### What a Good Pull Request Contains

A good pull request makes its behavioural change reviewable:

- **One change per pull request**, with the intent stated in one sentence up front.
- **Tests that would fail if the change were reverted.** If the change genuinely needs no test, say why.
- **For anything touching quoted statute:** name the official source recorded in `docs/legal-sources.md` and say why the quote is character-for-character correct. The verbatim-quote tests and the monthly `statute-drift` workflow hold statutory text to that retrieval record.
- **For anything touching Table 7 wording:** say how you checked it against the paper transcription in `src/reasonsmith/table7.toml`. The paper is the authority, and the transcription must remain character-for-character faithful to it.
- **The template's four prompts** — what changed, why, how it was verified, and authoritative text — are exactly these points. Fill them in and the pull request is done.
