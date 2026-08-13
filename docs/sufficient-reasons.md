# Subset-minimal sufficient reasons — migration stub

The formal definitions formerly in this document now live in
[`theory/07-explanation.md`](theory/07-explanation.md), Definitions 7.1–7.19. That chapter is
the authoritative account of the deletion lattice, sufficiency, AXp/CXp duality, reason states,
certificates, value gap, claimed semantics, and bounded enumeration.

## Historical rationale

The original instrument switched one fact off at a time and reported a conclusion about reasons.
Two reasons can be jointly necessary and individually removable: each singleton probe then leaves
the engine's answer unchanged, producing a false `deleted` accusation. The chapter preserves this
defect and its repair as the reason the deletion lattice and joint CXp search are defined.

The operational semantics remain in [`semantics.md`](semantics.md) §3, and the refinement record
remains in [`refinement.md`](refinement.md). This file is retained until the later migration PR
deletes the stub.
