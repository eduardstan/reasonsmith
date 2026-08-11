# The property language, defined

`docs/semantics.md` says what a *verdict* means. This document says what a *formula* means: the
grammar a requirement's `spec` is written in, the denotation every engine is an implementation of,
and which test fails if either claim becomes false. It is the companion to §2 of that document,
which describes the language informally and points here for the definition.

**Why it exists.** `validate-pack --analyse` asks whether a set of requirements is jointly
satisfiable, whether one duty entails another, and whether a subformula can be replaced without
changing a verdict (`docs/semantics.md` §8). Satisfiability, entailment and vacuity are relations
*between formulas of a language*, and are meaningful only once the language is defined. Until this
document the tool reasoned formally about something that existed only as a whitelist in
`rulelang.py` and four separate translations out of it.

**What it is not.** It is not a paper and it introduces no new construct, engine, rung or basis.
Every clause below describes something the tree already does, and every one names a test that fails
if it stops doing it. A denotational clause with no executable consequence is either wrong or not
worth stating; where one is stated anyway, the reason is given in the clause.

Where this document and the code disagree, the code is right and this document has a defect — with
one exception, §4, which records three places where the code disagrees *with itself* and says which
side this document takes.

[`formal.md`](formal.md) §2 states this document's §2 in the notation the rest of the repository's
mathematics is written in, and carries the **bibliography** every citation here resolves to. The
grammar, the refusals and the four divergences of §4 live here and nowhere else.

---

## 1. The grammar

### 1.1 Where the text is read

A `spec` is a string in a pack's TOML. It reaches a verdict through exactly four steps, all in
`rulelang.py`:

1. `preprocess_spec` — a **textual** rewrite of the arrow operators into call form. It runs *before*
   the parse, so what it emits decides what every later step can tell apart.
2. `parse_expression` — `ast.parse(..., mode="eval")`. CPython's parser, unmodified.
3. `validate_property` — the whitelist walk. Everything the language does not admit raises
   `UnsupportedConstructError` here; nothing is skipped.
4. `classify_fragment` — the narrowest fragment the formula belongs to, which `spec.load_pack`
   demands match the declared `formalism` exactly.

Nothing in this path calls `eval`, `exec` or `compile`, and nothing may
(`test_pack_text_is_never_executed_as_python`). Pack files are third-party data; a `__builtins__`
dict is not a sandbox, so the whitelist is the interpreter itself. **This document does not
replace the parser and nothing in it licenses replacing the parser.** The grammar below is a
*description*, checked against CPython's parser plus the whitelist by
`tests/test_language_definition.py`, and a description that drifts is a failing test rather than a
second front end.

### 1.2 The grammar

Terminals are quoted. Two levels: the arrow level is textual and applies before the parse; the
operator level is CPython's own expression grammar, narrowed by the whitelist walk.

```ebnf
spec              = arrow_expr ;

(* ---- arrow level: preprocess_spec, textual, before the parse ---- *)

eq_token          = "<=>" | "<->" ;
imp_token         = "=>" | "->" | " implies " ;   (* one space either side of the word *)

arrow_expr        = eq_expr ;
eq_expr           = imp_expr , eq_token , imp_expr   (* at most one at parenthesis depth 0 *)
                  | imp_expr ;
imp_expr          = or_expr , imp_token , imp_expr   (* right-associative *)
                  | or_expr ;

(* ---- operator level: CPython's expression grammar, parsed in eval mode ---- *)

or_expr           = and_expr , { "or" , and_expr } ;
and_expr          = not_expr , { "and" , not_expr } ;
not_expr          = "not" , not_expr | comparison ;
comparison        = arith , { cmp_op , arith } ;     (* chained comparisons admitted *)
cmp_op            = "==" | "!=" | "<" | "<=" | ">" | ">=" ;
arith             = term , { ( "+" | "-" ) , term } ;
term              = factor , { ( "*" | "/" | "%" ) , factor } ;
factor            = ( "-" | "+" ) , factor | primary ;
primary           = name | literal | call | "(" , arrow_expr , ")" ;

name              = ? a Python identifier, as CPython's tokenizer defines one ? ;
literal           = number | string | "True" | "False" | "None" ;
number            = ? any Python integer or floating-point literal ? ;
string            = ? any Python string literal ? ;

(* ---- calls ---- *)

call              = record_atom | relational_atom | open_texture_atom
                  | temporal_call | connective_call | arithmetic_call ;

record_atom       = "present" , "(" , name , ")"
                  | "contains" , "(" , name , "," , string , ")" ;
relational_atom   = "counterfactually_invariant" , "(" , name , "," , name , ")" ;
open_texture_atom = "undetermined" , "(" , name , "," , string , "," , string , ")"
                  | "degree" , "(" , name , "," , string , ")" ;

temporal_call     = unary_temporal , "(" , arrow_expr , ")"
                  | binary_temporal , "(" , arrow_expr , "," , arrow_expr , ")" ;
unary_temporal    = "always" | "eventually" | "once" | "historically"
                  | "next" | "prev" | "rise" | "fall" ;
binary_temporal   = "until" | "since" ;

connective_call   = ( "implies" | "Implies" | "Iff" ) , "(" , arrow_expr , "," , arrow_expr , ")" ;
arithmetic_call   = "abs" , "(" , arrow_expr , ")"
                  | ( "min" | "max" ) , "(" , arrow_expr , "," , arrow_expr , ")" ;
```

Two productions are deliberately not written into the grammar, because they are not grammatical
facts: the **kind discipline** of §1.4 decides which `arrow_expr` may stand in which argument
position, and the **side conditions** of §1.5 decide which argument shapes an atom admits. Both are
checked by the same whitelist walk and both raise the same error type, so a reader chasing a load
failure has one place to look; they are separated here because a context-free production cannot
state either.

`test_the_grammar_names_exactly_the_calls_the_language_defines` reads the block above out of this
file and compares its call-name terminals against `rulelang`'s own constants. A call added to the
language and not to this grammar fails the build, and so does a call named here that the language
does not have.

### 1.3 The lexical decisions

The inventory that preceded this document
(`firstmate/data/rs-language-inventory/report.md`) left five points marked `UNCERTAIN`. Each is
settled here. None is a change to the code: each states what the code already does and why that is
the intended reading rather than an accident.

**L1 — Numerals are Python's numerals, in full.** `0x10`, `0o17`, `0b101`, `1_000`, `1e9` and `.5`
are all admitted, because `ast.parse` produces an `ast.Constant` for each and the whitelist walk
asks only for the *type* of the value, never for how it was spelled. This is the intended reading
and not an oversight: the parser is CPython's, a numeral notation this language refused would have
to be refused by inspecting source text the parser has already discarded, and no such refusal would
make a pack more checkable. A `complex` literal (`1j`) is refused, as is every other constant type,
because `expression_kind` has no kind for it
(`test_the_numeral_syntax_is_pythons_and_the_other_constant_types_are_refused`).

**L2 — Identifiers are Python's identifiers, and CPython normalises them.** A signal name is
whatever CPython accepts as an identifier, which includes non-ASCII names (PEP 3131). The
consequence worth knowing is that the tokenizer applies NFKC normalisation, so a `spec` reading
`present(ﬁeld)` — with the `ﬁ` ligature — reads the signal `field`. The pack's `requires` list is
an ordinary TOML string and is *not* normalised, so such a pack fails at load with the
ungated-signal error rather than quietly reading a different field. That refusal is the whole of
the protection and it is why no further rule is needed
(`test_an_identifier_the_tokenizer_normalises_is_refused_by_the_requires_gate`).

**L3 — Arrow tokens.** `=>`, `->`, `<=>` and `<->` are matched anywhere at parenthesis depth 0
outside a string literal, with no whitespace requirement. The word form is the token `" implies "`,
one space on each side, so `(a)implies(b)` is not an arrow and fails as a Python syntax error; a
signal named `implies_this` is untouched because the token requires the trailing space. The
asymmetry is deliberate: `=>` and `->` cannot occur inside an identifier and the bare word can
(`test_the_word_arrow_needs_a_space_on_each_side_and_the_symbol_arrows_do_not`).

**L4 — `<=>` and `==` are now distinguishable, and this was the one that mattered.** The inventory
recorded that the rewriter emitted `==` for `<=>`, so after the parse an author's equivalence and
an author's equality were the same node and no later pass could tell them apart. That is resolved:
the rewriter emits `Iff(φ, ψ)`, a distinct node on the footing `Implies(φ, ψ)` already had. Over
𝔹 the two readings coincide, so no shipped verdict moved; over a residuated lattice they do not,
because `==` is a crisp comparison of two degrees — a threshold — while `Iff` is the biresiduum
(§2.7). `test_the_rewriter_never_collapses_equivalence_to_a_comparison` is the pin.

**L5 — Call syntax is positional only.** `f(x=1)` parses and is refused by the whitelist walk;
`f(*xs)` and `f(**kw)` parse and are refused as unsupported constructs. Nothing about a call
reaches an engine except its head name and its positional arguments
(`test_a_call_carrying_keywords_or_unpacking_is_refused`).

### 1.4 The kind discipline

`expression_kind` assigns every expression one of five kinds — `boolean`, `number`, `string`,
`none`, `unknown` — and refuses a kind in a position that does not admit it. A bare `name` has kind
`unknown` and satisfies any position, because nothing about a signal's type is known until a system
supplies a value.

| Position | Kind required |
|---|---|
| operand of `not`, of `and`/`or`, of a temporal operator, of `implies`/`Implies`/`Iff` | `boolean` |
| operand of `-`/`+` (unary), of `+ - * / %`, of `abs`/`min`/`max` | `number` |
| operand of a comparison | **none — the comparison is untyped** |
| the whole `spec` | `boolean` or `unknown` |

The comparison row is the one to notice. `present(a) == present(b)` is admitted, and so is
`contains(r, "x") == True`: the walk types a comparison's *result* and not its operands. That is a
deliberate width — a Boolean-to-Boolean comparison is a well-formed question, and the temporal
fragment separately refuses the one shape it cannot render (§1.5) — and it is paid for by a
heterogeneous comparison such as `text < count` being a run-time refusal rather than a load-time
one. Nothing is reported satisfied there: the engines catch it and report *not evaluated*.

### 1.5 The side conditions

A shape the grammar admits may still be refused, and every such refusal is a rule about what the
formula would *mean* rather than about how it is written.

- **Atoms whose first argument is a signal name.** `present`, `contains`,
  `counterfactually_invariant`, `undetermined` and `degree` each bind their first argument to one
  field of one decision record or to one named variable of a decision procedure, and there is no
  such field behind a computed value. Every literal argument after the first is fixed by the pack
  and is never a name: a phrase, a predicate word or an authority read out of the audited system's
  own log is a self-declaration with an extra step.
- **`contains` phrases.** Non-empty and ASCII. Empty is `present()` written the long way; non-ASCII
  is refused because the fold that makes the solver and the interpreter agree reaches exactly the
  twenty-six ASCII capitals (§3.2).
- **`counterfactually_invariant`.** Two distinct names, and the atom is the whole of a `spec` or no
  part of one. A conjunction or a negation over a 2-safety atom is a strictly larger claim than
  anything here discharges (§2.10).
- **The two open-texture atoms may not meet.** `undetermined()` says nothing here settles the
  predicate; `degree()` asks for the whole formula to be read over the pack's algebra. A formula
  asking both answers neither.
- **A `degree()` atom may not stand under a comparison, under arithmetic, or under a temporal
  operator.** The first two state a threshold and ask for a number on an undefined scale; the third
  would need a many-valued reading of a temporal operator, and §2.8 is why there is none.
- **A Boolean literal may not stand as a bare Boolean atom**, and the temporal fragment further
  refuses `==`/`!=` against a Boolean literal in either operand order, because rtamt cannot render
  the Boolean role without reading it as a magnitude.
- **A signal may not hold both the bare-Boolean role and the measured-magnitude role** in one
  property. `x >= 0.5` and `0.5 <= x` are the one comparison pattern read as a flag rather than as
  a magnitude; every other comparison makes both sides magnitudes.
- **Chained equivalence is refused as ambiguous** while an implication chain is admitted
  right-associatively, because `a -> b -> c` has a settled reading in every logic this package
  touches and `a <=> b <=> c` does not.

### 1.6 Fragment assignment

`classify_fragment` returns the **narrowest** fragment, asked in this order. The order is the
definition, not an optimisation: an earlier answer dominates a later one.

```
fragment(spec) =
     "counterfactual"  if the whole spec is the relational atom
else "undetermined"    if undetermined() occurs anywhere
else "graded"          if degree() occurs anywhere
else "temporal"        if a temporal operator occurs anywhere
else "record"          if the spec is a conjunction of present() atoms and nothing else
else "logical"
```

Each of the first three dominates for the same reason: the fragment decides which engines may
discharge a duty, and each of those three names a claim no trace-reading engine may answer. A spec
carrying an `undetermined()` atom is not a `record` duty with an asterisk — classifying it by its
presence conjuncts would answer the settleable part and report that answer as the duty's, which is
the presence-as-a-proxy substitution the construct exists to end
(`test_the_fragment_order_is_the_documented_order`).

### 1.7 The refusals, by name

Every refusal raises `UnsupportedConstructError`. The identifiers in the first column exist so that
this table and `tests/test_language_definition.py` can be checked against each other: the test refuses
one witness per row and fails if a row here has no witness or a witness here has no row.

| Id | Refused |
|---|---|
| `R-PROSE` | text CPython cannot parse as an expression, English included |
| `R-NOT-READ-WHOLE` | text CPython parsed without reading whole, a comment or a token of the input dropped |
| `R-NOT-TOKENISED-WHOLE` | text CPython parsed and its tokeniser would not read whole, so whether anything was dropped cannot be established |
| `R-UNTERMINATED-STRING` | an unterminated string literal, found by the rewriter |
| `R-UNBALANCED-PARENS` | unbalanced parentheses, found by the rewriter |
| `R-EMPTY-ARROW-OPERAND` | a missing operand on either side of an arrow |
| `R-CHAINED-EQUIVALENCE` | two equivalence tokens at parenthesis depth 0 |
| `R-CONSTANT-TYPE` | a constant of a type with no kind, such as a complex literal |
| `R-UNARY-OP` | a unary operator outside `not`, `-`, `+` |
| `R-BINARY-OP` | a binary operator outside `+ - * / %`, the bitwise operators included |
| `R-COMPARISON-OP` | a comparison outside `== != < <= > >=` |
| `R-CONSTRUCT` | any other expression form: conditional expressions, attributes, subscripts, unpacking |
| `R-KEYWORD-ARGUMENT` | a keyword argument to any call |
| `R-UNKNOWN-CALL` | a call to a name outside the language's call set |
| `R-ARITY` | a call of the right name and the wrong number of arguments |
| `R-KIND` | an expression in a position its kind does not admit |
| `R-NOT-BOOLEAN` | a whole `spec` whose kind is `number`, `string` or `none` |
| `R-PRESENT-ARGUMENT` | `present()` given anything but one signal name |
| `R-CONTAINS-SHAPE` | `contains()` given a computed haystack, a named phrase, or the wrong arity |
| `R-CONTAINS-EMPTY` | `contains()` given the empty phrase |
| `R-CONTAINS-NON-ASCII` | `contains()` given a non-ASCII phrase |
| `R-COUNTERFACTUAL-ARGUMENT` | `counterfactually_invariant()` given an expression, or one name twice |
| `R-COUNTERFACTUAL-COMPOSED` | the relational atom in any position but the whole `spec` |
| `R-OPEN-TEXTURE-LITERAL` | `undetermined()` or `degree()` given a computed or blank literal |
| `R-OPEN-TEXTURE-BOTH` | one `spec` using both open-texture atoms |
| `R-DEGREE-UNDER-COMPARISON` | a `degree()` atom under a comparison or arithmetic |
| `R-DEGREE-UNDER-TEMPORAL` | a `degree()` atom under a temporal operator |
| `R-BARE-BOOLEAN-CONSTANT` | `True` or `False` standing as a Boolean atom |
| `R-CONFLICTING-ROLES` | one signal in both the bare-Boolean and the measured-magnitude role |
| `R-TEMPORAL-BOOLEAN-COMPARISON` | `== `/`!=` against a Boolean literal inside the temporal fragment |

`test_every_documented_refusal_is_refused` and `test_every_refusal_the_grammar_test_knows_is_named_here`
are the two halves of that pin, and what they hold is stated exactly: **this table is the refusals
reachable from `classify_fragment`** — the rewriter, the parse, the whitelist walk, and
`validate_temporal_property` — which is the entry point every witness runs through. It is not every
refusal `rulelang` raises.

One refusal on that path has no row and cannot have one: the walk refuses a Boolean operator
outside `and` and `or`, and CPython's grammar produces no third — `&` and `|` are binary operators
and are refused as those. It is a defensive branch with no witness, and a table row with no witness
is what this pin exists to catch.

Three refusals are **outside this table's scope** rather than missing from it, and they are not
defensive branches: `classify_fragment` *accepts* each of these specifications and assigns it a
fragment, and the refusal fires later, when an engine evaluates the formula against a decision
record. They are `counterfactually_invariant()`, `undetermined()` and `degree()` reached by
`eval_expression`. The first is the whole of the guarantee that no rung ever reads the relational
atom off a trace (`docs/semantics.md` §3, *counterfactual*); the other two are the two open-texture
constructs, which reach no engine at all. What each of them means, and what it costs, is stated in
`docs/semantics.md` §3 and §9. No row is added for them here: a witness for one would have to run
through an engine rather than through `classify_fragment`, so a row would be a rule this pin cannot
check, which is the hollow pin this section exists to prevent.

### 1.8 The grammar is checked

`test_every_spec_the_grammar_generates_is_accepted` generates from the productions of §1.2, subject
to §1.4 and §1.5, and asserts `parse_property` accepts each one and `classify_fragment` places it in
the fragment the generator built it for. A grammar nothing generates from is a comment.

---

## 2. The denotation

### 2.1 The shape

```
⟦·⟧_{M,A} : Spec → (𝒫(Trace_M) ⇀ A)
```

A formula denotes a **partial** map from *sets of traces* to a value in an algebra `A`, relative to
a structure `M`.

Three parameters, each a decision recorded in
`firstmate/data/rs-language-semantics/decision.md` and taken in its uniform reading:

- **`M`, the structure**, is either a finite trace or an input space (§2.2). The rungs of the
  strength lattice are different instantiations of this one denotation and not two denotations
  joined by a bridge theorem.
- **`𝒫(Trace_M)`, sets of traces**, uniformly — Clarkson & Schneider's hyperproperties
  (*Hyperproperties*, CSF 2008 / JCS 2010 — `[@clarkson-2010]`). This is how the counterfactual atom is typed: it is a
  2-safety property and therefore not a property of any single execution. It is heavier than three
  quarters of the language needs, and §2.9 states the cost and the theorem that discharges it. The
  uniformity is the decision: a semantics that typed one fragment differently because it was
  inconvenient would be the first thing a reader objected to.
- **`A`, the algebra**, is a complete residuated lattice. `𝔹`, the two-element Boolean algebra, is
  a degenerate instance of that and not a separate system (§2.3).

`⇀` is a partial map. Partiality is not an oversight and is the point of half this package: a
formula that has no value on the evidence supplied is *not evaluated*, never satisfied and never
violated (§2.4).

### 2.2 The structures `M`

`M` supplies what a name means and which traces exist.

- **`O(σ)` — an observation structure.** A finite sequence σ of decision records, each a mapping
  from signal name to value; `Trace_{O(σ)} = {σ}`. This is `sut.decisions()`. Names are read out of
  a record; a name a record does not carry is not an error but the very question `present()` asks.
- **`D(L)` — a declaration structure.** An exposed decision procedure `L = (Var, sorts, rules,
  constraints)`; that is `sut.logic()`. `Trace_{D(L)}` is every finite sequence of records each of
  which is an execution of `rules` on an input satisfying `constraints`. Names are variables of the
  procedure, with a declared sort and a declared **direction**: computed by the rules, supplied to
  them, or neither.

A third thing is not a third structure. The `probed` rung replays a system on a finite set of
generated cases, which yields `T ⊆ Trace_{D(L)}` for the `L` the system implements but does not
expose. That containment *is* the strength lattice's content at that rung: the same denotation,
evaluated on a subset, which can refute a universal claim and cannot establish one
(`test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach`).

### 2.3 The algebras `A`

`A = (A, ⊓, ⊔, ⊗, →, ¬, 0, 1)`, a complete residuated lattice: `⊓` and `⊔` are the lattice meet and
join, `⊗` is a residuated monoid operation with unit `1`, `→` its residuum
(`x ⊗ z ≤ y  ⟺  z ≤ x → y`), and `¬x = x → 0`.

Two instantiations ship.

- **`𝔹`** — `{0, 1}`, where `⊓ = ⊗ = ∧`, `⊔ = ∨` and `→` is material implication. Every fragment
  but `graded` is read here.
- **`[0,1]` under a declared t-norm** — `manyvalued.ALGEBRAS`: Łukasiewicz, Gödel and product, the
  three fundamental continuous t-norms from which every continuous t-norm is an ordinal sum (Hájek,
  *Metamathematics of Fuzzy Logic*, 1998 — `[@hajek-1998]`). Each stores its residuum rather than deriving one, and
  `¬` and the biresiduum are derived from it, so a member is internally consistent by construction
  (`test_each_algebra_is_a_residuated_lattice_on_the_grid`). Which one is a **declared parameter of
  the pack** (`[grading] algebra`) and never a default: a conjunction of two halves is `0` under
  Łukasiewicz, `0.5` under Gödel and `0.25` under product, so a default nobody read would be a
  semantics this tool picked on a pack author's behalf.

**`⊗` and `⊓` are two different conjunctions and the code uses both.** `and` in a formula is the
*strong* conjunction `⊗` (`manyvalued.degree_of` calls `algebra.conjunction`), while
quantification over positions and over traces is the lattice infimum `⊓`
(`manyvalued.degree_over_trace` takes the minimum). Over `𝔹` they coincide, which is why nothing
two-valued has ever had to notice; over Łukasiewicz they emphatically do not
(`test_the_three_algebras_disagree_about_a_conjunction_of_two_halves`,
`test_the_degree_of_a_trace_is_the_infimum_of_its_records`). Stating it is worth the line because
the two are one keystroke apart in an implementation and the difference is invisible to every
existing test that runs over `𝔹`.

### 2.4 Partiality, and when it resolves

Write `↑` for *undefined*: the denotation assigns no value. Four things make a formula undefined at
a point, and each is a *not evaluated* result rather than a verdict:

1. a name the structure does not interpret (an unbound identifier at `D(L)`; a signal absent where
   a **magnitude** was asked for at `O(σ)`);
2. a value of the wrong sort for the operation asked of it — `contains()` on a number, a bare
   Boolean atom on a record carrying neither `True` nor `False`, a division by zero;
3. an atom no supplied evidence scores — a `degree()` atom the `Grading` does not cover;
4. `undetermined(...)`, which is `↑` **by construction, at every structure and every algebra**
   (§2.11).

Undefinedness does not simply propagate. The rule is **insensitivity**:

> `⟦φ⟧` is defined at a point when its value is the same for every value in `A` that its undefined
> subformulas could take, and `↑` otherwise.

That is what makes the interpreter's short-circuit correct rather than a shortcut: `0 ⊗ a = 0` for
every `a` in every algebra here, so `⟦φ ∧ ψ⟧ = 0` whenever `⟦φ⟧ = 0`, whatever ψ does. The Z3
encoding is strict instead — it must build both operands before it can assert either — so it
reports `↑` where the definition resolves. `test_the_encoder_and_the_interpreter_answer_the_same`
asserts the two agree about *refusal* on every spec it generates, which is the corpus where both
are total; the divergence above is reachable only where one operand is inexpressible to the encoder
and the other decides the formula, and that corpus does not generate one. It is an incompleteness of
one implementation and never an unsoundness: it refuses where the definition answers, which is the
direction this package always errs in.

### 2.5 Values

Boolean formulas are built over a value layer. `⟦e⟧^val_{M}(r)` maps an arithmetic expression to a
number at a record `r`, and it is partial in the sense above.

| Expression | Value |
|---|---|
| a numeral | itself |
| a name `x` | `r(x)` if the structure interprets it, else `↑` |
| `-e`, `+e` | negation, identity |
| `e₁ + e₂`, `e₁ - e₂`, `e₁ * e₂` | the ring operations |
| `e₁ / e₂` | **true division**, `↑` at `e₂ = 0` |
| `e₁ % e₂` | Python's **floor-based** remainder, which takes the sign of the divisor |
| `abs(e)`, `min(e₁,e₂)`, `max(e₁,e₂)` | as usual |

Two of those rows are choices rather than facts about arithmetic, and both are named because two
implementations had to be made to agree on them: division is true division on both sides
(`test_division_is_true_division_on_both_sides`) and `%` follows Python rather than Z3, whose `mod`
is non-negative (`test_modulo_follows_python_semantics_for_any_divisor`,
`test_the_encoder_and_the_interpreter_compute_the_same_number`).

**A stated gap.** The numbers are not the same numbers on both sides: Z3 reasons over exact
rationals and the interpreter runs float64. `engines/counterfactual.REAL_ARITHMETIC_LIMIT` carries
that on every verdict resting on it, and the differential corpus in
`tests/test_semantics_agreement.py` generates exact halves so that it rediscovers no divergence
already known and declared.

### 2.6 State formulas, at one record

`⟦φ⟧^rec_{M,A}(r) ∈ A` for a formula of the `record`, `logical` or `graded` fragment at a record
`r`. Four of the six rows below are **crisp** — their value is `0` or `1` even when `A` is not `𝔹`
— and that is a claim about the language and not about the algebra:

| Atom | `⟦·⟧^rec(r)` |
|---|---|
| `present(x)` | `1` if `rulelang.is_present(r(x))`, else `0` |
| `contains(x, "p")` | `1` if `rulelang.contains_literal(r(x), p)`, else `0`; `↑` if `r(x)` is present and is not a statement |
| `e₁ ⋈ e₂` | `1` if the comparison holds of `⟦e₁⟧^val(r)` and `⟦e₂⟧^val(r)`, else `0`; `↑` if either is `↑` |
| `x` (bare Boolean atom) | `1` if `r(x)` is `True`, `0` if `r(x)` is `False`, `↑` otherwise |
| `degree(x, "q")` | `G(q(x)) ∈ A`, the degree the supplied `Grading` assessed; `↑` if it assessed none |
| `undetermined(x, "q", "a")` | `↑`, always |

`contains()` is `0` and not `↑` where the record carries nothing, which is what lets an implication
guarded by `present()` decide a duty that bites only where a statement was made
(`test_a_record_carrying_no_statement_carries_no_phrase`). It is `↑` and not `0` where the record
carries something that is not a statement, because answering `0` would report a system satisfied on
a field nothing read (`test_a_present_value_that_is_not_a_statement_is_refused`).

`degree(x, "q")` does not read `r` at all. The `Grading` is one assessment for the whole run, so the
atom is a constant of the structure rather than a function of the record — which is what makes
"there is no per-record grading" a fact about the semantics rather than an omission in an interface
(`manyvalued.Grading`, `test_a_grading_must_state_who_fixed_the_scale`).

### 2.7 The connectives

Every connective has a reading in `A`, which is the requirement decision 2.3 imposed and the reason
the equivalence connective had to land before this document could be written.

| Formula | `⟦·⟧` |
|---|---|
| `not φ` | `¬⟦φ⟧` |
| `φ and ψ` | `⟦φ⟧ ⊗ ⟦ψ⟧` |
| `φ or ψ` | `⟦φ⟧ ⊕ ⟦ψ⟧`, the dual t-conorm |
| `Implies(φ, ψ)`, `φ -> ψ`, `φ => ψ`, `φ implies ψ` | `⟦φ⟧ → ⟦ψ⟧`, the residuum |
| `Iff(φ, ψ)`, `φ <=> ψ`, `φ <-> ψ` | `(⟦φ⟧ → ⟦ψ⟧) ⊗ (⟦ψ⟧ → ⟦φ⟧)`, the biresiduum |

Over `𝔹` every row is the classical connective, so nothing two-valued moves
(`test_the_interpreter_reads_equivalence_as_the_truth_table`,
`test_the_solver_reads_equivalence_as_the_truth_table`). Over Łukasiewicz the biresiduum works out
to `1 − |x − y|` (`test_lukasiewicz_equivalence_is_one_minus_the_distance`), and it is `1` exactly
when the two degrees agree (`test_the_biresiduum_is_one_exactly_when_the_degrees_agree`) — which is
the *graded* reading of equality and precisely not the crisp comparison `==` denotes.

`==` between two degrees is therefore a different formula from `<=>` between them, and remains
refused: it states a threshold, and a threshold written into a pack is the author's number
presented as the regulation's (`test_a_graded_comparison_the_author_wrote_is_still_refused`).

### 2.8 Temporal formulas denotation over finite traces

For a trace $\sigma$ of length $n = |\sigma| > 0$ and a position $i \in \{0, \dots, n-1\}$, $\llbracket \phi \rrbracket^{\text{pos}}(\sigma, i)$ defines the semantics of every temporal formula $\phi$ at position $i$. The trace verdict is evaluated at position 0: $\llbracket \phi \rrbracket^{\text{tr}}(\sigma) = \llbracket \phi \rrbracket^{\text{pos}}(\sigma, 0)$ (§2.9). The **future** clauses are the standard finite-trace semantics of LTL over finite traces — De Giacomo & Vardi, *Linear temporal logic and linear dynamic logic on finite traces* (IJCAI 2013 — `[@degiacomo-2013]`) — with **one exception**, stated here rather than left for a reader to find in clause 3: `next` is the **weak** next, true at the final position $n-1$. De Giacomo & Vardi's $X$ is the **strong** next and is *false* there, for want of a successor to satisfy it; the weak next is its dual, $N \phi \equiv \neg X \neg \phi$. Every other future clause is theirs as written. The **past** clauses are not the mirror images of the future ones, and this document does not claim they are: their conventions at position 0 are **rtamt's**. Both departures are adopted for the same reason, deliberately. rtamt is the monitor that computes the robustness reported beside every verdict `engines/observed.py` produces — the `observed` verdicts of `engines/record.py` run no monitor and carry none — and a denotation that diverged from it at a boundary would make the documented semantics and the executed semantics disagree, which is worse than adopting a convention this section can simply state. Each was read off the monitor, and the probes are recorded below.

They are **restated here rather than named**, and the reason is a change in the code that this
section is the contract for. `rulelang.eval_temporal_trace` evaluates these clauses directly, over
the Kleene chain of §2.12 rather than over `𝔹`, and `engines/observed.py` takes its verdict from
that evaluation. It does **not** take it from a robustness sign, and that is the whole point of the
clauses being written down: $\rho > 0$ implies satisfaction and $\rho < 0$ implies violation, but
$\rho = 0$ implies neither, and $\rho$ does not represent strictness at all — $\rho(x > c) = \rho(x
\ge c)$. A Boolean question answered by comparing a robustness number is therefore a defect, and a
definition that only *named* its clauses gave no statement against which to find one.

What is still owned elsewhere, and what may still never be implemented twice: rtamt owns the
real-valued monitoring at the `observed` rung and BLACK owns the decision procedure in the
analysis, and a second monitor, automaton construction or tableau is the thing to refuse if it is
ever proposed. The property language's contribution to *those two* remains a **syntax mapping** —
prefix calls, because it parses through Python's `ast`, rendered back into rtamt's infix by
`engines/observed.to_stl` and into BLACK's by `ltlf.to_ltlf`
(`test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it`). The clauses below are the
statement those renderings are checked *against*, which is what §4 does when it reports four shapes
on which the rtamt rendering and this definition part company.

State predicates without temporal operators are evaluated per-record via $\llbracket f \rrbracket^{\text{rec}}(\sigma_i)$ using `rulelang.eval_expression`. The connective and temporal operator denotations over finite traces are stated below, and every one of them is checked against what `rtamt` does on a discrete trace:

#### Connectives
- $\llbracket \text{not } \phi \rrbracket^{\text{pos}}(\sigma, i) = \neg \llbracket \phi \rrbracket^{\text{pos}}(\sigma, i)$
- $\llbracket \phi_1 \text{ and } \phi_2 \rrbracket^{\text{pos}}(\sigma, i) = \llbracket \phi_1 \rrbracket^{\text{pos}}(\sigma, i) \land \llbracket \phi_2 \rrbracket^{\text{pos}}(\sigma, i)$
- $\llbracket \phi_1 \text{ or } \phi_2 \rrbracket^{\text{pos}}(\sigma, i) = \llbracket \phi_1 \rrbracket^{\text{pos}}(\sigma, i) \lor \llbracket \phi_2 \rrbracket^{\text{pos}}(\sigma, i)$
- $\llbracket \text{Implies}(\phi_1, \phi_2) \rrbracket^{\text{pos}}(\sigma, i) = \neg \llbracket \phi_1 \rrbracket^{\text{pos}}(\sigma, i) \lor \llbracket \phi_2 \rrbracket^{\text{pos}}(\sigma, i)$
- $\llbracket \text{Iff}(\phi_1, \phi_2) \rrbracket^{\text{pos}}(\sigma, i) = (\llbracket \phi_1 \rrbracket^{\text{pos}}(\sigma, i) == \llbracket \phi_2 \rrbracket^{\text{pos}}(\sigma, i))$

#### Temporal Operators
1. `always(f)`: $\bigwedge_{j=i}^{n-1} \llbracket f \rrbracket^{\text{pos}}(\sigma, j)$
2. `eventually(f)`: $\bigvee_{j=i}^{n-1} \llbracket f \rrbracket^{\text{pos}}(\sigma, j)$
3. `next(f)`: $\llbracket f \rrbracket^{\text{pos}}(\sigma, i+1)$ if $i+1 < n$, else $1$ (weak `next`)
4. `prev(f)`: $\llbracket f \rrbracket^{\text{pos}}(\sigma, i-1)$ if $i > 0$, else $1$ (weak `prev`)
5. `historically(f)`: $\bigwedge_{j=0}^{i} \llbracket f \rrbracket^{\text{pos}}(\sigma, j)$
6. `once(f)`: $\bigvee_{j=0}^{i} \llbracket f \rrbracket^{\text{pos}}(\sigma, j)$
7. `rise(f)`: $\llbracket f \rrbracket^{\text{pos}}(\sigma, 0)$ if $i = 0$, else $\llbracket f \rrbracket^{\text{pos}}(\sigma, i) \land \neg \llbracket f \rrbracket^{\text{pos}}(\sigma, i-1)$
8. `fall(f)`: $\neg \llbracket f \rrbracket^{\text{pos}}(\sigma, 0)$ if $i = 0$, else $\neg \llbracket f \rrbracket^{\text{pos}}(\sigma, i) \land \llbracket f \rrbracket^{\text{pos}}(\sigma, i-1)$
9. `until(a, b)`: $\bigvee_{j=i}^{n-1} \left( \llbracket b \rrbracket^{\text{pos}}(\sigma, j) \land \bigwedge_{k=i}^{j-1} \llbracket a \rrbracket^{\text{pos}}(\sigma, k) \right)$
10. `since(a, b)`: $\bigvee_{j=0}^{i} \left( \llbracket b \rrbracket^{\text{pos}}(\sigma, j) \land \bigwedge_{k=j+1}^{i} \llbracket a \rrbracket^{\text{pos}}(\sigma, k) \right)$

#### Boundary Edge Cases & Empirical `rtamt` Evidence

The finite-trace boundary edge cases are determined by running `rtamt` over discrete traces:

- **`next` at position $n - 1$**: Weak `next` (evaluates to `True`).
  *Empirical probe*: `next(b >= 0.5)` on $b = [1.0, 0.0]$:
  ```python
  spec = rtamt.StlDiscreteTimeSpecification()
  spec.declare_var('b', 'float')
  spec.spec = 'next(b >= 0.5)'
  spec.parse()
  spec.evaluate({'time': [0, 1], 'b': [1.0, 0.0]})
  # Output: [[0, -0.5], [1, inf]]  --> robustness +inf at t=1 implies True
  ```
- **`prev` at position 0**: Weak `prev` (evaluates to `True`).
  *Empirical probe*: `prev(b >= 0.5)` on $b = [0.0, 1.0]$:
  ```python
  spec.spec = 'prev(b >= 0.5)'
  spec.evaluate({'time': [0, 1], 'b': [0.0, 1.0]})
  # Output: [[0, inf], [1, -0.5]]  --> robustness +inf at t=0 implies True
  ```
- **`until(a, b)`**: Search interval $[i, n-1]$ is inclusive. If $b$ never holds on $[i, n-1]$, returns `False`.
  *Empirical probe*: `until(a >= 0.5, b >= 0.5)` on $a = [1, 1], b = [0, 0]$:
  ```python
  spec.evaluate({'time': [0, 1], 'a': [1.0, 1.0], 'b': [0.0, 0.0]})
  # Output: [[0, -0.5], [1, -0.5]] --> robustness -0.5 implies False
  ```
- **`since`, `once`, `historically` at position 0**: Evaluated over prefix $[0, 0]$.
  *Empirical probe*: `since(a >= 0.5, b >= 0.5)` on $a = [0, 1], b = [1, 0]$:
  ```python
  spec.evaluate({'time': [0, 1], 'a': [0.0, 1.0], 'b': [1.0, 0.0]})
  # Output: [[0, 0.5], [1, 0.5]]   --> robustness +0.5 implies True
  ```
- **`rise` and `fall` at position 0**: Implicitly assumes initial boundary conditions $f(-1) = 0$ for `rise` and $f(-1) = 1$ for `fall`.
  *Empirical probe*: `rise(b >= 0.5)` on $b = [1.0, 0.0]$ evaluates to `True` at $t=0$ (`[[0, 0.5], [1, -0.5]]`), and `fall(b >= 0.5)` on $b = [0.0, 1.0]$ evaluates to `True` at $t=0$ (`[[0, 0.5], [1, -0.5]]`).
- **Strictness at threshold $\rho = 0$**: The Boolean verdict follows from strict comparison operator semantics: `>` and `<` evaluate to `False` on the threshold, while `>=` and `<=` evaluate to `True` (`test_strict_comparison_boundary_table`, `test_all_ten_temporal_operators_covered_and_distinguished`, `test_differential_property_shipped_packs_and_systems`, `test_differential_property_random_traces`, `test_missing_numeric_signal_returns_inconclusive`).

#### Which reading each past operator takes at position 0

Past LTL has **two** previous operators, and the distinction is the standard one: the *strong*
previous $\ominus$ is false at the initial position, there being no predecessor to satisfy it, and
the *weak* previous $\widetilde{\ominus}$ is true there for the same reason — Manna & Pnueli, *The
Temporal Logic of Reactive and Concurrent Systems: Specification* (Springer, 1992 —
`[@manna-1992]`), where the pair is introduced and $\widetilde{\ominus} \phi \equiv \neg \ominus
\neg \phi$. This language has one `prev`, and the three clauses that look one position back do not
all read it the same way:

- `prev(f)` is the **weak** previous: $1$ at position 0 (clause 4).
- `rise(f)` takes the **strong** reading: at position 0 it evaluates as if $f(-1) = 0$, so it
  reduces to $\llbracket f \rrbracket^{\text{pos}}(\sigma, 0)$ (clause 7).
- `fall(f)` takes the **strong** reading with the opposite boundary value: at position 0 it
  evaluates as if $f(-1) = 1$, so it reduces to $\neg \llbracket f \rrbracket^{\text{pos}}(\sigma,
  0)$ (clause 8).

**The consequence, which is the part a reader will otherwise get wrong.** `rise(f)` and
`f and not prev(f)` agree at every position but the first, and at position 0 they are **not
interchangeable**, because one clause is written against the strong previous and the other against
the weak one. Witness, on $\sigma = [\{\texttt{flag}: 1\}, \{\texttt{flag}: 0\}]$: `rise(flag)` is
$1$ at position 0, while `flag and not prev(flag)` is $0$ there, since `prev(flag)` is weak and
therefore $1$. Neither is wrong and neither is a defect — they are two operators, spelled apart —
and this paragraph exists so that a pack author does not write one meaning the other.
`historically`, `once` and `since` raise no such question: they quantify over the prefix $[0, i]$,
which at $i = 0$ is $[0, 0]$ and asks for no value at $-1$. The three conventions are pinned by
`test_all_ten_temporal_operators_covered_and_distinguished`, which asserts the witness above as
well as the boundary values: a trace beginning `b = False` cannot pin `rise` at position 0, because
the strong reading and the weak-previous one agree there, so the pin needs a trace beginning
`b = True` and carries one.

One clause `engines/temporal.py` implements for reduction to `proved`:
```
⟦always(φ)⟧^tr(σ)  =  ⨅_{i < |σ|} ⟦φ⟧^rec(σᵢ)          for φ free of temporal operators
```

This is exact over a finite trace, and it is the whole of why a temporal duty can reach the proof
rung at all: `always(f)` holds iff `f` holds at every position, and every position is a decision the
exposed logic admits (`test_only_always_reaches_the_temporal_proof_rung`,
`test_a_nested_temporal_operator_does_not_reduce`).

**There is no reading of a temporal operator in a general `A`.** A many-valued temporal semantics is
a temporal semantics, and this package implements none; so the graded fragment is a property of one
decision record, quantified over the trace by the infimum of its per-record degrees. The load-time
refusal of a `degree()` atom under a temporal operator is a **consequence of this gap and not a
policy** (`test_a_graded_atom_under_a_temporal_operator_is_refused_at_load`).

### 2.9 Traces, and sets of traces

For every fragment but `counterfactual`:

```
⟦φ⟧^tr(σ)      =  ⨅_{i < |σ|} ⟦φ⟧^rec(σᵢ)        for a state formula φ
⟦φ⟧^set(T)     =  ⨅_{σ ∈ T} ⟦φ⟧^tr(σ)
```

with `⨅` the lattice infimum — the meet, not the strong conjunction (§2.3). A temporal formula's
trace value is `⟦φ⟧^pos(σ, 0)`.

**The factoring theorem, which is the cost the uniform typing buys back.** For every fragment but
`counterfactual`, `⟦φ⟧^set` factors through the traces individually, so nothing about evaluating one
of those duties over a set of traces differs from evaluating it over each trace and taking the meet.
That is why three quarters of the language pays nothing for being typed over `𝒫(Trace_M)`: an
implementation reading one trace at a time is a correct implementation of the set-valued denotation,
and the reports this tool emits carry `⟦φ⟧^tr(σ)` for the single supplied σ. The uniformity was
still taken, and the reason is `counterfactually_invariant`, the one atom for which the factoring
fails and which would otherwise have needed a judgement of its own.

**The empty set, and the empty trace, are deliberately not the top of the lattice.** Mathematically
`⨅ ∅ = 1`. This package refuses that value everywhere it could arise: an empty trace is *not
evaluated* rather than satisfied (`test_an_empty_trace_is_not_evidence`), combining zero verdicts is
`inconclusive` rather than vacuously `satisfied`, and `manyvalued.degree_over_trace` raises rather
than returning `1.0`. So the denotation as this package reads it is narrowed at exactly one point:
`⟦φ⟧^set(∅) = ↑` and `⟦φ⟧^tr(ε) = ↑`. Having observed nothing is not evidence, and it is not
evidence graded any higher than it is evidence Boolean. This is the one place the code departs from
the mathematics on purpose, and it is worth stating for that reason even though it changes no
formula: a reader who derived `1` here would derive a verdict the tool refuses to print.

### 2.10 The relational atom

`counterfactually_invariant(o, p)` is the whole of the `counterfactual` fragment and the one place
`⟦·⟧^set` does not factor. Over a declaration structure `D(L)`:

```
⟦counterfactually_invariant(o, p)⟧^set_{D(L)}(T) = 1
  iff  for every pair of records r, r′ occurring in traces of T that arise from admissible inputs
       agreeing on every input variable except p,  r(o) = r′(o).
```

Over an observation structure `O(σ)` it is **`↑`, and no engine may compute it**. The reason is not
that a hyperproperty cannot be evaluated on a subset — this one is subset-closed, so a subset could
in principle refute it. The reason is that refuting it needs a pair differing in `p` *and in nothing
else*, and a log supplies no such pair except by coincidence and no way to certify that a pair is
one. The admissible values of `p` therefore come from the system's declared `constraints` and never
from the trace (`test_paired_replay_takes_no_protected_value_from_the_trace`). The refusal lives in
`rulelang.eval_expression`, which every trace-reading engine evaluates through, so that "no engine
answers a counterfactual off a decision log" is a fact about the code rather than a convention
(`test_no_engine_can_evaluate_the_atom_against_a_decision_record`,
`test_the_ladder_for_this_fragment_carries_no_trace_rung`).

Two further consequences of the definition, both enforced:

- **The atom does not compose.** A conjunction, negation or implication over it is a strictly larger
  claim — a property of a pair combined with a property of one, or with a second pair — and nothing
  here discharges one. Admitting the shape and reporting it not evaluated would put the atom into
  `logical`'s reach through classification (`test_the_atom_is_the_whole_spec_or_no_part_of_one`).
- **Unawareness is not invariance.** The definition quantifies over pairs of *admissible inputs*
  differing in `p`; if `L` has no notion of `p` there are no such pairs, the condition is vacuously
  `1`, and reporting that as `satisfied` would certify an unaware system as provably fair. The
  engine reports `unattainable` instead, and telling the two apart is the only reason `computes` is
  consulted at this rung (`test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`,
  `test_the_two_cases_reach_different_verdicts_on_the_same_rules`).

### 2.11 Where there is no reading in a general `A`, and why

Three, stated rather than invented:

1. **`undetermined(x, "q", "a")` has no value in any `A`.** Not `0`, not `1`, not a degree. The
   construct exists to say that a predicate the law states without a sharp boundary is settled by a
   named authority outside this tool, and any value at all would be this tool guessing. It is `↑`
   by construction, and the *authority* is what the result reports instead
   (`test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority`,
   `test_an_undetermined_atom_is_refused_by_the_two_valued_interpreter`).
2. **The temporal operators have no reading in a general `A`** (§2.8). Over `𝔹` they are LTLf, owned
   by two published implementations; over a residuated lattice they would be a many-valued temporal
   logic this package has not implemented and must not improvise.
3. **`⟦φ⟧(∅)` has no value** (§2.9), though `A` supplies one. The lattice's top is a value the
   evidence does not support.

A fourth is worth naming as *not* being an exception: a `degree()` atom under a comparison has no
reading here either, but the reason is a decision about packs rather than a gap in the algebra —
`≤` between two elements of `[0,1]` is perfectly well defined, and the refusal is that a pack
stating one would be stating a compliance threshold no statute states
(`test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`).

### 2.12 The third value, and whose three-valuedness it is

The reference interpreter and `eval_temporal_trace` do not evaluate into `𝔹` but into the **Kleene
strong three-valued logic** `[@kleene-1952]` on the chain `F < U < T` (`rulelang.UNKNOWN`, `kleene_not`,
`kleene_and`, `kleene_or`, `kleene_implies`, `kleene_iff`). The tables are Kleene's and no other's:

| `φ` | `¬φ` |   | `∧` | F | U | T |   | `∨` | F | U | T |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F | T |   | **F** | F | F | F |   | **F** | F | U | T |
| U | U |   | **U** | F | U | U |   | **U** | U | U | T |
| T | F |   | **T** | F | U | T |   | **T** | T | T | T |

`φ → ψ` is `¬φ ∨ ψ` and `φ ↔ ψ` is `(φ → ψ) ∧ (ψ → φ)`, both derived rather than tabulated, which
is why `U ↔ U = U`. `UNKNOWN.__bool__` **raises**: a third value that silently coerced to `False`
at an `if` would be a two-valued answer wearing a three-valued type. The tables above are checked
against the operators cell by cell (`test_the_kleene_tables_are_the_ones_the_language_doc_writes_out`,
`test_implication_and_equivalence_are_derived_and_not_tabulated`,
`test_the_unknown_value_refuses_to_coerce_to_a_boolean`).

Each operand is read as a **truth value** and never by identity against `True`/`False`
(`rulelang.kleene_value`), and `eval_temporal_trace` normalises every position of the trace the
same way. This is load-bearing rather than tidy: an atom of this language returns whatever the
decision record carried, so `0`, `1` or `""` in a Boolean position matched neither identity branch
and fell through to the operator's unit — a `T` off a falsy conjunct and an `F` off a truthy
disjunct, at the two rungs (`probed`, `certificate`) that guard no atom
(`test_a_falsy_operand_is_false_and_not_a_third_thing`,
`test_a_truthy_operand_is_true_and_not_a_third_thing`,
`test_the_interpreter_does_not_answer_a_conjunction_off_a_falsy_atom`,
`test_a_trace_of_records_evaluates_into_the_kleene_chain_and_not_into_raw_values`).

**Where `U` comes from here, and where it does not.** `U` is this tool's *ignorance about a record*
— a signal the decision record does not carry a value for, so the atom reading it has no truth
value at this position. That is the source Bruns & Godefroid `[@bruns-1999]` treat: a partial state
space, incompletely known. It is **not** the source Bauer, Leucker & Schallhart `[@bauer-2011]`
treat in LTL₃, which is a *truncated trace* — the prefix seen so far may be extended, and the
question is whether every extension agrees. The two are different questions with the same arity,
and this repository answers only the first. [`semantics.md`](semantics.md) §8 states the second as
**not available from this tool**, and that statement is about LTL₃ and stays true: nothing here
computes a verdict about the extensions of a trace. Conflating them — in prose or in a value — is
the mistake this paragraph exists to prevent.

**Kleene is sound for the question and it is not complete for it.** If this evaluation returns `T`
or `F`, that value holds under *every* assignment of the unknowns, so a verdict read off it is
never a guess. The converse fails: `φ ∨ ¬φ` evaluates to `U` when `φ` is `U`, although every
completion makes it true. So `U` means **this evaluation did not determine the formula**, and never
*no determination is possible*. Supervaluation `[@vanfraassen-1966]` — quantifying over the
classical completions — is complete for that question and is deliberately not implemented: it costs
a satisfiability check per formula, and the direction Kleene errs in is the direction this package
always errs in, reporting *not evaluated* where a sharper procedure would answer. A duty whose
verdict rests on that gap is therefore reported inconclusive, never satisfied
(`test_kleene_is_sound_and_not_complete_for_determinacy`).

---

## 3. Four implementations of one denotation

Each of the four is an implementation of §2 over a particular `A` and `M`, and each already has a
differential test that was written as a hygiene check between two components. Named as what they
are, those tests are the conformance evidence for this document: a differential test says *these two
agreed on the cases we tried*, and a semantics says *here is the definition and these implement it*.

| Implementation | `M` | `A` | Rung | Conformance evidence |
|---|---|---|---|---|
| `rulelang.eval_expression` | `O(σ)`, one record at a time | the Kleene chain `F < U < T` of §2.12 | reference | — it *is* the reference |
| `engines/proved._ast_to_z3` | `D(L)` | `𝔹` | `proved` | `test_the_encoder_and_the_interpreter_answer_the_same`, `test_the_encoder_and_the_interpreter_compute_the_same_number`, `test_the_solvers_fold_is_the_interpreters_fold`, `test_the_solvers_blank_string_is_pythons_blank_string` |
| `engines/observed.to_stl` + rtamt | `O(σ)` | `𝔹` (via robustness sign) — the **margin** the rung publishes, no longer its verdict (§2.8) | `observed` | `test_the_monitor_agrees_with_the_reference_reading`, and §4 |
| `ltlf.to_ltlf` + BLACK | a propositional abstraction of `O(σ)` | `𝔹` | none — it answers about *packs* | `test_the_ltlf_backend_agrees_with_the_monitor` |

`manyvalued.degree_of` is not a fifth implementation but the same reference interpreter at a
different `A`: every subtree carrying no `degree()` atom is handed to `eval_expression` and mapped
to `1.0`/`0.0`, so the crisp parts of a graded formula mean exactly what they mean everywhere else
(`test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else`).

### 3.1 The reference interpreter

`rulelang.eval_expression` at `A` = the Kleene chain of §2.12, `M = O(σ)`, one record at a time. It
is the reference because
it is the only implementation that is a direct transcription of §2.5–§2.7 with no encoding step
between, and because every other engine's cross-check is run against it — including the proof
rung's, which replays the interpreter on the witness the solver chose before any verdict is read off
the solver (`test_encoding_disagreeing_with_the_interpreter_is_not_a_proof`).

Being the reference is a job and not a privilege: where it and this document part company, §2 is the
one that has to move.

### 3.2 Z3, at the declaration structure

`engines/proved.py` encodes the same constructs into Z3 formulas over `D(L)`, which is what lets a
verdict quantify over *every* admissible input rather than over the ones a log happened to contain.
Three clauses need saying because their encoding is not the obvious one:

- **`present(x)`** is the solver's blankness language, and `contains(x, "p")` is a bracketed regular
  language conjoined with it. A substring search alone would find a phrase of blanks in a string of
  blanks, where §2.6 says the record carries nothing
  (`test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry`).
- **The ASCII fold** is rendered character by character as a regular language matching exactly one
  character, which is why `fold_ascii_case` must be one-to-one and why a non-ASCII phrase is refused
  at load rather than compared under a fold only one side can perform
  (`test_the_solvers_fold_is_the_interpreters_fold`).
- **`Iff`** is encoded as implication both ways rather than as `arg0 == arg1`. The two are the same
  Boolean formula, but the second would also accept two numeric operands and quietly become numeric
  equality — the crisp comparison `<=>` is no longer a spelling for.

Both atoms refuse a signal the rules only *read*: `⟦present(x)⟧` at `D(L)` asks what the procedure
writes, and a free input the solver may set to anything is no answer.

The two agreement obligations are asserted as agreement, not hoped for: same answer on a generated
corpus of specs and environments, and same *set* — a spec `parse_property` accepts must not make the
encoder raise anything but its own deliberate refusal, and where the encoder accepts, the
interpreter must not refuse (`test_the_encoder_and_the_interpreter_answer_the_same`). What that does
not establish is agreement on every input; §2 of `docs/semantics.md` states that gap in the same
words and the runtime cross-check is what stands in the way of it becoming a wrong `proved`.

### 3.3 rtamt, at the observation structure

`engines/observed.py` renders the property in rtamt's syntax and monitors it for the **robustness
margin** it publishes in `details['evaluation_scores']`. It does not read the sign of that signal as
the verdict — the verdict is `rulelang.eval_temporal_trace` over the clauses of §2.8 and the chain
of §2.12 (§2.8 for why, §4 for what the refusals still protect). What this section names as an
implementation of §2 is therefore the *rendering*, and
`test_the_monitor_agrees_with_the_reference_reading` is what holds it to the denotation.
Two clauses of §2.6 could not be handed to rtamt at all — it reasons
over real-valued signals and nothing else — so `present(x)` and `contains(x, "p")` are evaluated in
Python per record and reach the monitor as **synthetic flags**. That is what keeps their meaning the
one meaning of §2.6 instead of a second definition living inside an STL string.

The rendering is textual, on `req.spec` as the author wrote it. So `φ -> ψ` reaches rtamt as `->`,
which rtamt reads, while `Implies(φ, ψ)` reaches it as a call, which rtamt does not — the trace rung
does not reach every shape and says so rather than guessing
(`test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow`).

`test_the_monitor_agrees_with_the_reference_reading` is the conformance test this document adds: a
corpus of state formulas, evaluated by the reference interpreter and by the monitor, asserted equal.
It carries four **named exclusions**, and §4 is what they are — three of them now refused in the
rendering rather than answered, the fourth a boundary convention.

### 3.4 BLACK, at a propositional abstraction

`ltlf.py` hands a temporal formula to BLACK (a satisfiability checker for LTL and LTLf) over a subprocess boundary.
It is the only implementation that changes the structure rather than the algebra: every comparison of magnitudes becomes one
opaque propositional atom, so `x <= 30` bears no relation to `x <= 90`. That abstraction is sound
for the entailments it reports and incomplete for the ones it does not, which is why satisfiability
is reported only in the affirmative and `LTLF_ABSTRACTION_LIMIT` rides on every answer.

Two of its choices are §2 clauses rather than implementation details. Every question is asked over
a **non-empty** trace, which is §2.9's refusal of `⨅ ∅` restated in the object logic: an `always`
duty satisfiable only by the empty trace is reported unsatisfiable
(`test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable`). BLACK
interprets LTLf over non-empty finite traces natively, so that clause is inherited from the
procedure rather than conjoined as a guard formula — the clause is the same one either way, and it
is the clause and not the guard that this document states. And `Iff` is expanded both ways, the
same expansion Z3 uses, because the mapping has no `<->` of its own
(`test_the_trace_logic_has_a_spelling_for_equivalence`).

The decision record that fixed the shape of this document predates `ltlf.py`, so it names three
implementations and there are four. Nothing in the decision needs revisiting: `ltlf` is a fourth
implementation of the same denotation at a coarser structure, it occupies no rung, it returns no
`RequirementResult`, and `test_the_ltlf_backend_agrees_with_the_monitor` already holds it to the
same agreement obligation the other three carry.

---

## 4. Four shapes the monitor does not render soundly

Writing §2 down found three places where the `observed` implementation and the denotation part
company, beside one that was already known and documented. **Rows 1–3 are now refused in the
rendering**: `engines/observed._refuse_shapes_the_monitor_misreads` raises on each, so a duty using
one is reported *not evaluated* naming the construct rather than answered off a formula rtamt read
differently. All four remain latent besides — no shipped pack writes any of these shapes, and
`test_no_shipped_spec_uses_a_shape_the_monitor_misrenders` is what keeps that true — so no verdict
moved when the refusal landed.

Each row is pinned twice: `test_the_monitor_agrees_with_the_reference_reading` excludes it by name,
and `test_the_four_named_shapes_are_still_what_the_document_records` asserts a concrete witness on
which rtamt and the reference reading still disagree *behind* the refusal — or, for a refused row
the strict lexer now makes rtamt raise on, that it raises there rather than being read differently
— so the exclusion list can neither grow silently nor keep a refusal whose reason has gone.

**What the refusal protects, now that the verdict is not the monitor's.** §2.8 records the change
this rationale has to be restated against: `engines/observed.py` takes its verdict from
`rulelang.eval_temporal_trace`, over the clauses of §2.8 and the chain of §2.12, and not from a
robustness sign. A shape rtamt misreads therefore no longer decides the verdict. The refusal is
kept, and its reason is the **other** number the rung publishes. rtamt's robustness still populates
`details['evaluation_scores']`, which travels into the JSON record and into every rendering that
reads one, so a shape rtamt reads differently would carry a margin computed from a *different
formula than the one the duty states* — `1 < count_a < 10` scored as `(1 < count_a) < 10`, a `%`
scored with the token dropped, an `Iff` scored as `−|ρ(left) − ρ(right)|`. A correct verdict beside
a margin that does not belong to it is worse than no `observed` verdict at all: nothing on the
record says the margin is about another formula, and a reader has no way to tell. So the rung is
refused, the four rows stay, and neither pin moves.

**1. The remainder operator, `%`.** rtamt's lexer has no `%`. ANTLR **error-recovers by dropping the
token**, and on rtamt's default lexer `spec.parse()` did not raise, so the monitor answered about a
formula nobody wrote, with a token-recognition line on stderr as the only trace. `_monitor` now
installs rtamt's own raising error listener on the lexer and asserts the parse produced exactly one
statement, so a dropped token is a raise rather than a silent answer — `RTAMT_BEHAVIOUR` records
this row as *raises* for that reason, and the refusal below is kept in front of it rather than
resting on the listener. Witness: `count_a % count_b > 1` at
`count_a = -2, count_b = 2`. The reference reading is `-2 % 2 = 0`, so the formula is false; on the
default lexer the monitor scored robustness `+1.0` and would have reported **satisfied**. This is
the exact failure mode
`rulelang`'s own module docstring names — a silently dropped construct makes an engine answer about
logic the author did not write — arriving through a dependency's error recovery rather than through
this package's whitelist. It is the row that mattered most, because it was the only one the engine's
old protection (rtamt raising) could not see. **Refused.**

**2. Chained comparison.** §2.6 reads `a ⋈ b ⋈ c` as the conjunction of its pairs, and so do the
interpreter and Z3. rtamt parses it and **left-associates over robustness values**: it reads
`1 < x < 10` as `(1 < x) < 10`, comparing a robustness margin against `10`.
Witness: `1 < count_a < 10` at `count_a = -2`.
The reference reading is false; the monitor scores `+13.0` and would report **satisfied**.
**Refused.**

**3. Equivalence.** rtamt has an `iff` whose robustness is `−|ρ(left) − ρ(right)|`, which is negative
whenever the two sides' *margins* differ — including when both sides are false and the equivalence
is therefore true. Witness: `(count_a >= 1) <-> (count_b >= 1)` at `count_a = -2, count_b = 0`. Both
conjuncts are false, so §2.7 gives `1`; the monitor scores `−2.0` and would report **violated**. The
two spellings of the one connective also parted company at this rung: `<->` was monitored and got
this wrong answer, while `<=>` is not in rtamt's grammar at all and was reported *not evaluated*.
The refusal is asked of the parsed `Iff` node, which is where both arrive, so the two spellings now
reach the same refusal in the same words
(`test_both_spellings_of_equivalence_reach_the_same_refusal`). **Refused.**

**4. The exact tie** — already known, already documented, listed for completeness, and **not
refused**. rtamt scores a comparison that holds with no margin as robustness `0`, and `ρ` does not
represent strictness at all: `ρ(x > c) = ρ(x >= c)`, so the score cannot tell the two apart. This is
now a divergence of the **margin alone**. The verdict is not read off the score, so a strict
comparison satisfied nowhere by the reference reading is reported **violated** at the boundary —
`always(b > 0)` on a trace of `b = 0.0` is violated and `always(b >= 0)` satisfied
(`test_strict_comparison_boundary_table`). Every shipped duty uses `<=`, and at a tie `<=` *is*
satisfied, so no shipped verdict turns on this;
`test_a_declared_deviation_exactly_equal_to_the_margin_is_reported_satisfied` is that duty's case.

**Why the fix is a refusal and not a repair.** §2 is the reading, and three encodings — the
interpreter, the Z3 encoding and the finite-trace rendering — implement it. One backend disagreeing
is a defect in that backend, so the shape of the fix is the one this package already uses for `!=`,
`min(...)`, `max(...)` and `Implies(...)`: refuse the shape in the rendering. What this costs is a
trace rung, and it is stated rather than hidden — a duty writing one of these three has no
`observed` verdict at all.

The refusal list is three constructs long for a reason that belongs to a dependency and not to this
package: rtamt **raises** for nearly every construct this language admits and it does not
support — `!=`, `min`, `max`, `Implies(...)`, `<=>` — which is why `spec.parse()` raising sufficed
for as long as it did. That is measured rather than assumed:
`test_rtamt_still_behaves_the_way_the_refusals_assume` probes every admitted construct and asserts
which of *raises*, *agrees* and *misreads* rtamt does with it. Its purpose is a version bump
reopening the `%` hole under another construct, which would otherwise be as invisible as `%` was.

What is **not** done, and is a separate decision: verifying that what rtamt parsed is what was
rendered, rather than naming the shapes it misreads. That is the general form of this fix and would
not need a list.

The margin question is settled by the same soundness boundary: a shape rtamt misreads is
refused, not answered with a verdict and no margin. Suppressing `evaluation_scores` would still
leave a result claiming that the observed rung evaluated the duty while the only monitor margin
available came from another formula. The refusal therefore keeps both the verdict and its
misleading margin out of the record (`test_a_duty_using_a_misread_shape_is_not_evaluated_and_names_the_construct`).

---

## 5. Claim-to-test map

| Claim | Test |
|---|---|
| The grammar of §1.2 names exactly the calls the language defines | `test_the_grammar_names_exactly_the_calls_the_language_defines` |
| Every spec the grammar generates is accepted, and lands in the fragment it was generated for | `test_every_spec_the_grammar_generates_is_accepted` |
| Every refusal §1.7 names is refused, and every refusal the test knows is named | `test_every_documented_refusal_is_refused`, `test_every_refusal_the_grammar_test_knows_is_named_here` |
| The fragment order of §1.6 is the order the classifier uses | `test_the_fragment_order_is_the_documented_order` |
| Numerals are Python's and every other constant type is refused | `test_the_numeral_syntax_is_pythons_and_the_other_constant_types_are_refused` |
| An identifier CPython normalises is caught by the `requires` gate rather than read as another signal | `test_an_identifier_the_tokenizer_normalises_is_refused_by_the_requires_gate` |
| The word arrow needs a space each side and the symbol arrows do not | `test_the_word_arrow_needs_a_space_on_each_side_and_the_symbol_arrows_do_not` |
| A call carrying keywords or unpacking is refused | `test_a_call_carrying_keywords_or_unpacking_is_refused` |
| Equivalence survives the rewriter as a connective and never as a comparison | `test_the_rewriter_never_collapses_equivalence_to_a_comparison`, `test_an_author_written_equality_is_still_a_comparison` |
| Over `𝔹` both readings of `Iff` are the truth table | `test_the_interpreter_reads_equivalence_as_the_truth_table`, `test_the_solver_reads_equivalence_as_the_truth_table` |
| Over a residuated lattice `Iff` is the biresiduum, `1` exactly when the degrees agree | `test_a_graded_equivalence_is_the_algebra_s_biresiduum`, `test_lukasiewicz_equivalence_is_one_minus_the_distance`, `test_the_biresiduum_is_one_exactly_when_the_degrees_agree` |
| Each shipped algebra is a residuated lattice, and the three disagree | `test_each_algebra_is_a_residuated_lattice_on_the_grid`, `test_the_three_algebras_disagree_about_a_conjunction_of_two_halves` |
| Quantification over a trace is the infimum, and `and` is not that operation | `test_the_degree_of_a_trace_is_the_infimum_of_its_records` |
| Division is true division and `%` is Python's remainder, on both implementations | `test_division_is_true_division_on_both_sides`, `test_modulo_follows_python_semantics_for_any_divisor`, `test_the_encoder_and_the_interpreter_compute_the_same_number` |
| The Z3 encoding and the reference interpreter answer the same, and accept the same set | `test_the_encoder_and_the_interpreter_answer_the_same` |
| A proof disagreeing with the reference interpreter on its own witness is not a proof | `test_encoding_disagreeing_with_the_interpreter_is_not_a_proof` |
| `present()` and `contains()` mean the same thing to the solver as to the reference reading | `test_the_solvers_blank_string_is_pythons_blank_string`, `test_the_solvers_fold_is_the_interpreters_fold`, `test_the_solver_finds_no_phrase_in_a_string_the_record_does_not_carry` |
| The monitor agrees with the reference reading on every shape it renders | `test_the_monitor_agrees_with_the_reference_reading` |
| The four shapes it does not render soundly are still exactly those four, and still what §4 records | `test_the_four_named_shapes_are_still_what_the_document_records` |
| A duty writing one of the three refused shapes is not evaluated, naming the construct | `test_a_duty_using_a_misread_shape_is_not_evaluated_and_names_the_construct` |
| Both spellings of equivalence reach the same refusal | `test_both_spellings_of_equivalence_reach_the_same_refusal` |
| rtamt still raises for every other construct the language admits, so the refusal list is still three long | `test_rtamt_still_behaves_the_way_the_refusals_assume` |
| No shipped pack writes one of those shapes | `test_no_shipped_spec_uses_a_shape_the_monitor_misrenders` |
| The LTLf backend and the monitor agree about every shipped temporal duty | `test_the_ltlf_backend_agrees_with_the_monitor` |
| LTLf questions are asked over a non-empty trace, so `⨅ ∅` is never the answer | `test_an_always_duty_satisfiable_only_by_the_empty_trace_is_reported_unsatisfiable` |
| An empty trace has no value, at every rung and on the graded scale | `test_an_empty_trace_is_not_evidence`, `test_a_graded_duty_with_no_grading_or_no_trace_is_not_evaluated` |
| `undetermined()` has no value in any algebra and names its authority instead | `test_an_undetermined_atom_is_reported_undetermined_and_names_its_authority`, `test_an_undetermined_atom_is_refused_by_the_two_valued_interpreter`, `test_an_undetermined_duty_dominates_the_settleable_parts_of_its_formula` |
| A `degree()` atom the grading does not score has no value, and is not a degree of zero | `test_an_ungraded_atom_is_not_evaluated_and_never_a_degree_of_zero` |
| There is no many-valued reading of a temporal operator, so a graded atom under one is refused | `test_a_graded_atom_under_a_temporal_operator_is_refused_at_load` |
| A `degree()` atom under a comparison or arithmetic states a threshold and is refused | `test_a_graded_atom_under_arithmetic_or_a_comparison_is_refused`, `test_a_graded_comparison_the_author_wrote_is_still_refused` |
| The crisp parts of a graded formula mean what they mean everywhere else | `test_the_crisp_parts_of_a_graded_formula_mean_what_they_mean_everywhere_else` |
| The relational atom is the whole of a spec or no part of one | `test_the_atom_is_the_whole_spec_or_no_part_of_one`, `test_the_atom_classifies_into_its_own_fragment_and_not_into_logical` |
| No engine evaluates the relational atom against a decision record, and its fragment has no trace rung | `test_no_engine_can_evaluate_the_atom_against_a_decision_record`, `test_the_ladder_for_this_fragment_carries_no_trace_rung`, `test_a_log_only_system_is_never_answered_from_its_trace` |
| The protected values come from the declaration and never from the trace | `test_paired_replay_takes_no_protected_value_from_the_trace` |
| Unawareness is unattainable and not satisfied | `test_a_system_with_no_notion_of_the_protected_variable_is_unattainable`, `test_the_two_cases_reach_different_verdicts_on_the_same_rules` |
| A replayed subset can refute a universal claim and cannot establish one | `test_paired_replay_misses_what_the_trace_it_was_given_cannot_reach` |
| Only `always(f)` reduces to the state property, and nesting does not | `test_only_always_reaches_the_temporal_proof_rung`, `test_a_nested_temporal_operator_does_not_reduce` |
| The prefix temporal calls are rendered into the syntax the monitor actually reads | `test_the_rendered_form_is_rtamt_infix_and_rtamt_monitors_it` |
| The monitor reads the spec as written, so implication is spelled with an arrow | `test_the_monitor_reads_the_spec_as_written_so_implication_is_spelled_with_an_arrow` |
| Pack text is data and is never executed as Python | `test_pack_text_is_never_executed_as_python` |
| Every test this document names exists | `test_every_test_named_in_the_language_doc_exists` |
