# Authoring a requirement pack

A requirement pack is a TOML file the loader reads into `Requirement` and `Pack` structures
(`src/reasonsmith/spec.py`). Every requirement must be traceable to its statutory source: that is
the point of a pack, and it is why the loader refuses a pack that omits or adds a field rather
than guessing what a missing or unread field meant.

Validate your pack before shipping it — the CLI accepts the same names and files a `check` run
loads, because both go through the same loader:

```sh
python -m reasonsmith.cli validate-pack my_pack.toml
# after `pip install -e ".[dev]"` the same command is available as:
reasonsmith validate-pack my_pack.toml
```

`validate-pack` prints what the pack contains and exits 0. A pack the loader refuses makes it
exit 1, naming the file and the `[[requirement]]` at fault.

## Structure

```toml
[pack]
id = "my_pack"
title = "A human-readable title"
description = "What the pack covers, and any sharp edge in it."

[source]
document = "Official statute name"
publication = "Official collection"
url = "https://..."

[[requirement]]
id = "unique_requirement_id"
source_document = "Statute name"
article_clause = "Exact clause citation"
verbatim_text = """Exact text of the clause"""
stakeholder = "affected individual"
formalism = "record"          # one of: record, temporal, logical
spec = "The property the engine checks"
requires = ["signal_a", "signal_b"]
binding = true                # true = legal obligation, false = interpretive recital/guidance
scope = "high-risk"           # or "" for a duty that is not class-limited
```

A `[[requirement]]` block carries **exactly** these fields: `id`, `source_document`,
`article_clause`, `verbatim_text`, `stakeholder`, `formalism`, `spec`, `requires`, `binding`,
`scope`. Omitting one, or adding a field nothing reads, is a load-time error — an omitted field
would break source traceability, and an unread field would look like data the codebase acts on
when it does not.

## What each field is for

| Field | Meaning |
|---|---|
| `id` | A stable, unique identifier. Duplicate ids are rejected. |
| `source_document`, `article_clause` | The statute and clause the duty comes from. Together they are the citation a finding is reported against. |
| `verbatim_text` | The exact words of the clause, quoted for the report. |
| `stakeholder` | Whose interest the duty protects. |
| `formalism` | Which engine class checks it: `record` (completeness over a decision trace), `temporal` (rtamt monitors), `logical` (Z3 proof). A formalism no engine covers is reported not evaluated, never judged by a weaker check. |
| `spec` | The property the engine evaluates for this requirement. |
| `requires` | The signal names the system must be capable of emitting for the requirement to be checkable at all. A system missing one is reported unattainable on the missing signal, without being run. |
| `binding` | Whether this duty is a legally binding obligation (`true`) or an interpretive recital/guidance item (`false`). |
| `scope` | The regulatory class the duty is limited to, from the fixed vocabulary `prohibited`, `high-risk`, `limited-risk`, `minimal-risk`, `general-purpose`; `""` means the duty is not class-limited. |

Signal names conventionally start with the Section 6.3 taxonomy prefixes (`provenance_`,
`artifact_logs_`, `stability_signals_`, `scope_statements_`), but nothing enforces that: a name
outside the taxonomy is allowed and simply never supplied by an adapter that does not emit it.

## binding and scope have no default

Neither field has a default, here or in the loader. Defaulting a missing `binding` to `true`
would silently promote an unclassified item to a legal obligation, and defaulting it to `false`
would silently demote a statutory duty out of the compliance headline. Defaulting a missing
`scope` to `""` would leave an unclassified duty reachable for every system. A pack that has not
classified a requirement is a pack that must say so and be fixed, not one the code guesses for.

## Verbatim text must be traceable to the print

`verbatim_text` is quoted in reports and checked against the law, so it must be a character-faithful
quotation of the official statutory text — never a paraphrase. `docs/legal-sources.md` is the
retrieval record for the official text behind the shipped packs and the worked example: a new pack
that quotes a statute should record the same way, so a reviewer can verify the quotation against
the print. A requirement with a blank source document, clause or quotation is malformed rather
than merely incomplete, because it cannot be checked against the print at all.
