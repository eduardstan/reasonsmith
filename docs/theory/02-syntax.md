# 2 — Syntax

**Definition 2.1 (signature).** The property language has formulas $\varphi$ and $\psi$, signal
names $v$ and $v'$ in $\mathrm{Var}$, phrase literals $w$, comparison constants $k$, and the
call names and operators listed by the grammar below. A requirement's `spec` is an element of
$\mathsf{Spec}$ when it passes the grammar, the kind discipline, and all side conditions.

The text is read in four stages: `preprocess_spec` rewrites arrows textually before parsing;
`parse_expression` uses CPython's expression parser; `validate_property` performs the whitelist
walk; and `classify_fragment` assigns the narrowest fragment. The grammar is a description checked
against those code objects, not a second parser.

**Definition 2.2 (grammar).** Terminals are quoted. The arrow level is textual and precedes the
operator level, which is CPython's expression grammar narrowed by the whitelist.

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

The grammar deliberately does not encode the kind discipline or side conditions. They are semantic
well-formedness conditions checked by the same whitelist walk.

**Definition 2.3 (kind discipline).** `expression_kind` assigns `boolean`, `number`, `string`,
`none`, or `unknown`. A bare name has kind `unknown` and is admissible wherever a value's kind is
not yet known. Boolean positions are operands of `not`, `and`, `or`, temporal operators, and the
implication and equivalence calls. Numeric positions are operands of unary signs, arithmetic, `abs`,
`min`, and `max`. Comparison operands are untyped. A whole `spec` must be Boolean or unknown.

**Definition 2.4 (side conditions).** The following conditions are part of well-formed syntax:

- the first argument of `present`, `contains`, `counterfactually_invariant`, `undetermined`, and
  `degree` is a signal name;
- a `contains` phrase is nonempty and ASCII;
- `counterfactually_invariant` has two distinct names and is the whole `spec`;
- `undetermined` and `degree` cannot occur together;
- `degree` cannot occur under a comparison, arithmetic, or temporal operator;
- `True` and `False` cannot be bare Boolean atoms, and temporal Boolean comparisons are refused;
- one signal cannot have both bare-Boolean and measured-magnitude roles;
- chained equivalence is refused, while implication chains are right-associative.

**Definition 2.5 (named refusals).** Each refusal below is a syntactic side condition. Every listed
identifier is part of the language contract and is preserved verbatim.

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

**Definition 2.6 (fragment assignment).** Fragment assignment is the following function on
formulas. The order is narrowest-first and is the definition, not an optimisation.

```
fragment(spec) =
     "counterfactual"  if the whole spec is the relational atom
else "undetermined"    if undetermined() occurs anywhere
else "graded"          if degree() occurs anywhere
else "temporal"        if a temporal operator occurs anywhere
else "record"          if the spec is a conjunction of present() atoms and nothing else
else "logical"
```

The first three cases dominate later cases because each names a claim no trace-reading engine may
answer. A formula containing `undetermined()` is therefore not a record formula with an ignored
conjunct.
