# From scaffold to installed plug-in

One copy/paste walkthrough, from `reasonsmith init` to a pack or engine that `validate-pack` and
`verify-engine` find by name. Every command block on this page is executed in CI and every printed
transcript is compared byte-for-byte against the real output
(`tests/test_docs_authoring_scaffolds.py`), so what you read here is what runs.

What this page is not: the field-by-field contract. That is
[`authoring-packs.md`](authoring-packs.md) for what a pack's fields mean and
[`authoring-engines.md`](authoring-engines.md) for the engine result contract. This page is the
path; those two are the rules of the road.

The walkthrough assumes `reasonsmith` itself is already installed — `pip install reasonsmith`, or
the contributor virtualenv from `CONTRIBUTING.md` — and that you work in an empty directory you can
throw away. Commands are spelled `python -m ...` so they work against whichever `python` is on the
PATH, on Windows and Unix alike.

## 1. Create the pack scaffold

```sh
python -m reasonsmith.cli init pack demo-pack
```

```text
Created pack scaffold in demo-pack
```

The name must start with a letter and may then mix letters, digits, `-` and `_`; `-` becomes `_`
in the Python module. `init` refuses to overwrite an existing directory rather than merging into
it, and cleans up after itself if a write fails halfway.

Four files land in `demo-pack/`:

- `pyproject.toml` — a minimal setuptools project whose one important stanza is the entry point:
  `[project.entry-points."reasonsmith.packs"]` mapping `demo-pack = "demo_pack:pack_path"`. That
  line is the whole discovery mechanism: once the project is installed, `reasonsmith` finds the
  pack by the entry-point name.
- `src/demo_pack/__init__.py` — defines `pack_path()`, returning the `pack.toml` beside it.
- `src/demo_pack/pack.toml` — one placeholder requirement.
- `README.md` — the short version of this page.

## 2. Replace the TODOs — they are yours to clear, not the loader's

Every placeholder field in the generated `pack.toml` carries a `TODO:` marker. Be clear about the
semantics before editing: **nothing refuses a TODO**. `validate-pack` accepts the placeholder pack
as-is, because the loader's strictness is about the schema — the exact field set, a spec the
fragment supports, signals the requirement declares in `requires` — not about whether your text is
real. The TODOs are a checklist for you and for whoever reviews the pack, and the generated header
comment says so: replace every placeholder with a source-backed requirement before shipping. A pack
full of cleared-schema placeholders is still a pack of placeholders.

For this walkthrough the edit is a toy internal-policy duty — deliberately not a statute quote, so
nothing here is legal advice and no legal-source record is needed. Replace
`src/demo_pack/pack.toml` with:

```toml
[pack]
id = "demo_pack"
title = "Acme model-governance notices"
description = "One internal-policy duty formalised as a record check. A toy example for the walkthrough, not legal advice."

[source]
document = "Acme internal model-governance policy"
publication = "Acme policy register, 2026 edition"
url = "https://example.invalid/acme-model-governance"

[[requirement]]
id = "demo_pack_notice_states_model_version"
source_document = "Acme internal model-governance policy"
article_clause = "clause 4.2"
verbatim_text = "Every adverse-decision notice states the model version that produced the decision."
stakeholder = "applicant"
formalism = "record"
spec = "present(notice_states_model_version)"
rationale = "The notice either carries the model version or it does not; the check records presence and says nothing about whether the stated version is correct."
requires = ["notice_states_model_version"]
binding = true
scope = ""
domains = []
deontic_type = "obligation"
defeasibility = "strict"
```

For a real pack, `verbatim_text` is the exact source text and every field has a meaning the loader
enforces or the reviewers will ask about — [`authoring-packs.md`](authoring-packs.md) is the
contract, including the formula-gap discipline of writing down what the formalisation leaves out.

## 3. Validate by path, before any install

```sh
python -m reasonsmith.cli validate-pack demo-pack/src/demo_pack/pack.toml
```

```text
pack: demo_pack
title: Acme model-governance notices
description: One internal-policy duty formalised as a record check. A toy example for the walkthrough, not legal advice.
source.document: Acme internal model-governance policy
source.publication: Acme policy register, 2026 edition
source.url: https://example.invalid/acme-model-governance
requirements: 1
  demo_pack_notice_states_model_version | Acme internal model-governance policy clause 4.2 | record | binding: true | scope: unset | domains: none
```

Exit code 0 means the loader accepts the pack. This path form works anywhere, installed or not —
it is the fast edit-validate loop.

## 4. Install editable, so the entry point exists

```sh
python -m pip install -e demo-pack
```

pip prints its usual progress and a `Successfully installed demo-pack-0.1.0` line; the exact text
is pip's, not reasonsmith's, so this page does not pin it. `-e` is the editable install: the entry
point is registered but the files stay in your working directory, so the edit-validate loop keeps
working against the same `pack.toml`.

## 5. Validate by entry-point name

```sh
python -m reasonsmith.cli validate-pack demo-pack
```

```text
pack: demo_pack
title: Acme model-governance notices
description: One internal-policy duty formalised as a record check. A toy example for the walkthrough, not legal advice.
source.document: Acme internal model-governance policy
source.publication: Acme policy register, 2026 edition
source.url: https://example.invalid/acme-model-governance
requirements: 1
  demo_pack_notice_states_model_version | Acme internal model-governance policy clause 4.2 | record | binding: true | scope: unset | domains: none
```

Same output as the path form, but reached differently: `validate-pack` looked `demo-pack` up among
the built-in packs, did not find it, and resolved it through the installed
`reasonsmith.packs` entry point. Two discovery rules worth knowing before you ship:

- An entry point that names a **built-in** pack is refused with a warning — a plug-in cannot
  silently shadow a shipped pack.
- An entry point whose module fails to import is skipped with a warning naming the failure,
  never silently swallowed.

## 6. Create the engine scaffold

```sh
python -m reasonsmith.cli init engine demo-engine
```

```text
Created engine scaffold in demo-engine
```

The engine scaffold's `pyproject.toml` carries the matching stanza,
`[project.entry-points."reasonsmith.engines"]` mapping `demo-engine = "demo_engine:engine"`. The
generated `engine.py` is a **declining stub**: `max_strength = observed`, and `evaluate()` returns
`not evaluated` for every requirement it is offered. There are no TODO markers here because the
stub *is* the placeholder — an engine that declines everything is an honest non-answer, and that is
exactly the semantics to preserve until you implement one deliberately. The refusal semantics that
matter for engines:

- **Declining is a pass.** The conformance kit below accepts a declined triple, because an engine
  that cannot answer honestly must say so rather than guess.
- **`max_strength` is a ceiling the core enforces.** Raising it above `observed` is a claim about
  what your engine can establish, and the report layer refuses results reported above the declared
  ceiling. The scaffold's README says the same thing: raise it only when the engine can support
  the claim.

## 7. Install the engine editable

```sh
python -m pip install -e demo-engine
```

Same mechanics as the pack: the `reasonsmith.engines` entry point is registered, the files stay
yours.

## 8. Verify the engine against the conformance kit

```sh
python -m reasonsmith.cli verify-engine demo-engine
```

```text
engine: demo-engine
declared max_strength: observed

[PASS] triple 1: ecoa_reg_b_1002_9_a_1_timing_of_notice — expected satisfied/proved, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 2: ecoa_reg_b_1002_9_b_2_specific_reasons — expected satisfied/proved, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 3: ecoa_reg_b_1002_9_b_2_specific_reasons — expected satisfied/probed, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 4: ecoa_reg_b_1002_9_b_2_specific_reasons — expected satisfied/observed, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 5: ecoa_reg_b_1002_9_b_2_principal_reasons_complete — expected violated/probed, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 6: ecoa_reg_b_1002_9_c_2_incompleteness_notice_runs_out — expected unattainable/declined, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 7: ecoa_reg_b_1002_4_a_no_disparate_treatment — expected unattainable/declined, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined
[PASS] triple 8: ecoa_reg_b_1002_9_a_1_timing_of_notice — expected violated/proved, got not_evaluated/None; witness: trusted-ceiling
      verdict match: no; strength within declared ceiling: yes
      declined

summary: 8/8 triples passed

What passing proves:
1. On these eight inputs, the engine's verdict and strength agree with the built-in ladder, or it declined.
2. It never reported above its declared max_strength — already enforced at report.py:698-722, but the kit exercises it deliberately rather than incidentally.
3. Where it answered on a witness-bearing direction (§1), the witness it emitted was re-checked by the core and confirmed.
4. Every result named its plug-in (plugins.py:31-34).

What passing cannot prove:
- **Eight triples are eight points.** Agreement on a gold set is not soundness, and no size of gold set becomes soundness. The SV-COMP witness-validation experience is that validators and verifiers disagree, that a confirmation is a *second opinion* rather than a proof, and that unconfirmed results are common and often the validator's fault rather than the verifier's (Beyer & Strejček, *Case Study on Verification-Witness Validators: Where We Are and Where We Go*, SAS 2022, LNCS 13790, 160–174). The kit inherits every one of those caveats.
<!-- Docs annotation, not tool output: the witness-validator source above is registered as `[@beyer-2022]`. -->
- **The kit cannot see the direction the gold set does not go.** An engine that answers these eight correctly and answers a ninth duty wrongly passes.
- **A confirmed violation witness certifies the witness, not the search.** The engine may have missed ten other violations. Nothing in reasonsmith ever claimed otherwise — that is what `probed` means and why `PROBE_BUDGET_FIELDS` is compulsory — but a *passing* conformance kit is exactly the kind of artefact a reader over-reads, so `verify-engine`'s own output must carry the limit the way `MUTATION_LIMIT` and `TREATMENT_LIMIT` ride on their results.
- **The kit says nothing about safety.** A plug-in is imported and executed (`plugins.py:87` `ep.load()`); the trusted-code warning in the README's *Install and run* governs it, and passing the kit does not soften that.

The kit reports agreement on 8 named triples and confirms the witnesses those runs produced; it is not an audit of the engine and does not bound what the engine does on any duty not listed above.
```

The declining stub passes 8/8, and every row says `declined`: the kit's point is agreement with
the built-in ladder *or* an honest non-answer, never a forced verdict. `verify-engine` exits 2 —
not 0 — when a triple fails, and 1 on a usage error such as a name no installed entry point
carries. The *What passing proves / cannot prove* tail prints on every run; read it before citing
a pass, because agreement on eight gold triples is not soundness and the kit says so itself.

`verify-engine` also accepts `module:attribute` directly — `demo_engine:engine` — as a local
testing escape hatch for code that is not installed. The entry-point name is the form that proves
discovery works, which is why this page installs first.

## 9. The trusted-code warning, stated plainly

Everything this page installs runs **in the `reasonsmith` process, with your privileges**. An
entry point is imported and executed at discovery time; a pack's `pack_path` is code; an engine's
`evaluate` is code. The README's *Install and run* warning for `--system-module` applies verbatim
to plug-ins: install and run only code you trust. Neither `validate-pack` nor `verify-engine`
sandboxes anything, and passing the conformance kit does not soften that — the kit's own output
says so in its last bullet.

## Where next

- [`authoring-packs.md`](authoring-packs.md) — the pack schema, field by field, and the
  formula-gap discipline.
- [`authoring-engines.md`](authoring-engines.md) — the engine result contract, witness
  provenance, and what `max_strength` claims.
- [`adopting.md`](adopting.md) — running a check against your own system once the pack or engine
  is installed.
