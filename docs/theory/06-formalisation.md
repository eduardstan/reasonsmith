# 6 — Formalisation

This chapter defines the relation by which a statutory clause is refined into the property that a
pack records. It does not replace the operational record: [`refinement.md`](../refinement.md)
remains the one row for each shipped requirement, and its fourth column is the record of the
reading that the formula deliberately leaves out.

**Definition 6.1 (clause record).** A clause record is the triple
`(source_document, article_clause, verbatim_text)`. The first two members identify the provision;
the third is the quotation against which the reading can be checked. A clause record is not a
formula and does not by itself determine one.

**Definition 6.2 (requirement tuple).** A requirement tuple is the value of
`spec.Requirement`:

```
(id, source_document, article_clause, verbatim_text, stakeholder,
 formalism, spec, rationale, requires, binding, scope, domains,
 deontic_type, defeasibility, algebra)
```

The tuple separates the clause and its quotation from `spec`, the property formula. `formalism`
classifies the fragment, `requires` is the capability gate, and `rationale` is the English account
of the duty. `binding`, `scope`, `domains`, `deontic_type`, `defeasibility`, and (where applicable)
`algebra` are classifications or parameters; no engine is thereby added to the property.

**Definition 6.3 (refinement relation).** For a clause record `c` and a requirement tuple `q`, write

$$
c \rightsquigarrow q
$$

when all of the following hold:

1. `q.source_document`, `q.article_clause`, and `q.verbatim_text` identify `c`;
2. `q.spec` is a formula in the property language and `q.formalism` is its classified fragment;
3. `q.rationale` states the duty the author read in `c`;
4. `q.requires`, `q.scope`, and `q.domains` state the evidence and applicability gates that the
   formula needs; and
5. the fourth-column entry for `q` in [`refinement.md`](../refinement.md) states what the formula
   does not capture.

The relation is a record of a judgement, not a computation that discovers the legally correct
formula. A clause may therefore have more than one defensible refinement; this repository records
one and exposes its assumptions.

**Definition 6.4 (refinement side conditions).** A refinement is admissible only when its author
has discharged these side conditions:

- the quotation is copied from the retrieval record and the clause is identified precisely;
- every signal named by a formula is justified by the clause or by the evidence field it is meant
  to measure;
- an implication antecedent is used when the clause itself supplies a trigger, rather than being
  hidden in a gate or silently applied to every decision;
- an either/or clause is represented as a disjunction and does not gate a branch as if it were
  unconditional;
- an open-textured predicate is either left in the fourth column or named explicitly by
  `undetermined`/`degree`, never silently replaced by presence; and
- the author names the boundary between the formula and the legal duty, including organisational
  facts, representativeness of a trace, and any trigger or scope not represented by the evidence.

These are obligations on the author of the pack. The loader checks structural parts of them, while
legal interpretation and the adequacy of the reading remain recorded assumptions. The operational
census and its counts are generated from the packs by `tests/test_docs_refinement.py`; this chapter
does not duplicate or move that census.

**Remark 6.1 (assumption discharge).** The fourth column is where each assumption is made cited and
falsifiable: it names the omitted aspect and points to the semantic limit or source that supports
that statement. `docs/semantics.md` is authoritative for what an engine can establish; this chapter
is authoritative only for the shape of the refinement relation. A verdict about `q.spec` is never a
verdict that the statutory duty has been discharged.

**Remark 6.2 (internal and external axes).** Internal correctness asks whether the tuple is
well-formed, classified consistently, and evaluated according to the property language. External
adequacy asks whether the formula is an adequate reading of the clause. They are independent axes:
internal correctness never stands in for external adequacy, and external adequacy cannot repair an
ill-formed tuple.

**Remark 6.3 (no verification claim).** The map is not verified and cannot be. The adequacy of the
map is not a theorem of this system and is never asserted. The falsifiable assumptions in
`refinement.md` are the honest boundary of what this repository records.

**Remark 6.4 (open texture).** Presence records that a field is non-empty; it does not settle
*meaningful*, *sufficiently detailed*, *adequate*, or the other open-textured predicates named by
the refinement record. `contains` is narrower: it checks only a negative constraint stated by the
clause itself. `undetermined` and `degree` state that an open texture remains unsettled; neither
creates a verdict or makes the legal reading a theorem.

The map therefore has a deliberately one-way use: a statutory quotation and its recorded reading
produce a checkable requirement tuple, and the conformance machinery evaluates that tuple against
the evidence surface a system exposes. Nothing in this relation licenses a claim beyond the
assumptions written in the operational record.
