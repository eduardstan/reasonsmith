# Comparing statutory revisions

`reasonsmith.statute_replay` answers which *answers* changed when a sourced pack revision is
replayed. It runs the existing `check_conformance` machinery once for each revision and carries the
two ordinary reports unchanged; it adds only a per-duty comparison.

## Revision snapshots

A revision is a reviewable JSON manifest with `schema_version = 1`, a pack TOML path and SHA-256,
and source entries. Each source entry names the existing `drift.PROVISIONS` source key, the source
kind, a byte snapshot, its URL, retrieval timestamp, SHA-256 and a `synthetic` flag. Loading a
manifest verifies the pack and source hashes before loading the pack. Source quote matching reuses
the existing whitespace-only drift comparison. A stale quote is retained as `differ`, not silently
rewritten.

Use `StatuteRevision.from_manifest()` and `compare_revisions(before, after, sut)` from Python, or
run the module with two manifests and `--system-module module:attribute`. The JSON comparison
includes both ordinary conformance reports, source provenance, pack hashes, result transitions,
and an attribution field. `statutory-change` is used only when the relevant source passage changed
and the pack change is quote-only. A semantic pack edit alongside a source change is
`statutory-and-pack-change`; an isolated pack edit is `pack-change`; an answer difference with no
source or pack change is `system-change` when a second system is supplied, or `evidence-change` when the same system is run again. Added and removed duties are
`not-attributable`. A wording-only source revision therefore reports unchanged duty outcomes.

The committed fixtures in `tests/fixtures/statute_replay/` are deliberately labelled **SYNTHETIC
ONLY** and use `example.invalid`; they are not a historical statutory pair. They make the replay
and attribution tests deterministic. A future real demonstration must replace or supplement them
with independently sourced snapshots and their retrieval provenance. A notebook could now call
`compare_revisions` and render the resulting before/after reports, but no notebook is part of this
capability.
