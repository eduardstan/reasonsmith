# Global notation

This table is the notation register for every chapter under `docs/theory/`. Mathematical text uses
GitHub LaTeX; implementation identifiers remain code spans.

| LaTeX form | ASCII spelling | sort/type | meaning | chapter of introduction | code object where one exists |
|---|---|---|---|---|---|
| $\mathbf{A} = (A, \sqcap, \sqcup, \otimes, \to, \neg, 0, 1)$ | `Algebra` | algebra | An algebra and its carrier and operations. | 03 Semantics | `manyvalued.Algebra` |
| $A$ | `A` | carrier | Carrier of an algebra. | 03 Semantics | `manyvalued.Algebra` |
| $\sqcap$ | `meet` | binary operation | Meet operation. | 03 Semantics | `manyvalued.Algebra.conjunction` |
| $\sqcup$ | `join` | binary operation | Join operation; existential quantification uses this operation. | 03 Semantics | `manyvalued.Algebra.disjunction` |
| $\otimes$ | `t_norm` | binary operation | The algebra's conjunction (t-norm). | 03 Semantics | `manyvalued.Algebra.conjunction` |
| $\to$ | `residuum` | binary operation | Residuated implication. | 03 Semantics | `manyvalued.Algebra.residuum` |
| $\neg$ | `negation` | unary operation | Algebra negation. | 03 Semantics | `manyvalued.Algebra.negation` |
| $0$ | `0` | element of $A$ | Bottom element. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $1$ | `1` | element of $A$ | Top element. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $\mathsf{f}$ | `F` | Kleene value | False in the Kleene chain. | 03 Semantics | `rulelang.kleene_value` |
| $\mathsf{u}$ | `U` | Kleene value | Unknown in the Kleene chain. | 03 Semantics | `rulelang.UNKNOWN` |
| $\mathsf{t}$ | `T` | Kleene value | True in the Kleene chain. | 03 Semantics | `rulelang.kleene_value` |
| $F$ | `F` | set of facts | Facts exposed by an inference artefact. | 01 Models | `artifacts.InferenceArtifact` |
| $T$ | `T` | set of traces | Trace set used by the denotation. | 01 Models | `rulelang.eval_temporal_trace` |
| $L$ | `L` | declaration | System declaration. | 01 Models | `sut.SystemUnderTest.logic` |
| $\mathbb{L}(\beta)$ | `L(beta)` | deletion lattice | Lattice of deletions of the fact set for interpretation $\beta$. | 07 Explanation | `explanations.contrastive_sets` |
| $D(L)$ | `D(L)` | input space | Declaration model and its input space. | 01 Models | `engines.proved.encode_logic_domain` |
| $\mathrm{Dom}$ | `Dom` | set | Declared decision-domain set. | 01 Models | `report._inapplicability` |
| $S \subseteq F$ | `S subset F` | subset | A deletion subset and the AXp/sufficient set. | 07 Explanation | `artifacts.InferenceArtifact.without` |
| $u_i \subseteq F$ | `u_i subset F` | subset | One reason's facts. | 07 Explanation | `explanations.contrastive_sets` |
| $\mathcal{R} = \{u_1, \dots, u_n\}$ | `reasons` | family of subsets | Family of reasons. | 07 Explanation | `artifacts.InferenceArtifact.reasons` |
| $r_i$ | `r_i` | record | The $i$th decision record. | 01 Models | `rulelang.eval_expression` |
| $\sigma = r_0 \dots r_{n-1}$ | `sigma` | finite trace | A finite sequence of records. | 01 Models | `rulelang.eval_temporal_trace` |
| $v, v' \in \mathrm{Var}$ | `v, v_prime in Var` | signal | Signal names supplied by a system. | 02 Syntax | `spec.Requirement.variables` |
| $\mathrm{Var}$ | `Var` | set | Set of signal names. | 01 Models | `spec.Requirement.variables` |
| $\mathcal{C}$ | `C` | CXp | Contrastive explanation set. | 07 Explanation | `explanations.contrastive_sets` |
| $\mathrm{Cap}$ | `Cap` | set | Capability names a system exposes. | 01 Models | `sut.SystemUnderTest.capabilities` |
| $C.n$ | `C.n` | label | Global numbered label. | 08 Evidence | `report.ConformanceReport` |
| $p$ | `p` | protected variable | Protected variable in a counterfactual property. | 04 Decision problems | `rulelang.counterfactually_invariant` |
| $w$ | `w` | phrase metavariable | Literal phrase used by `contains`. | 02 Syntax | `rulelang.contains_literal` |
| $q$ | `q` | query | Query supplied to an inference artefact. | 04 Decision problems | `artifacts.InferenceArtifact.exact_value` |
| $g$ | `g` | grading-key metavariable | Key naming an open-textured grading predicate. | 03 Semantics | `manyvalued.Grading` |
| $x, y, z$ | `x, y, z` | element of $A$ | Algebra elements. | 03 Semantics | `manyvalued.Algebra` |
| $c$ | `c` | class | Regulatory class. | 01 Models | `spec.Requirement.scope` |
| $k$ | `k` | constant | Comparison constant. | 02 Syntax | `rulelang.parse_property` |
| $P$ | `P` | set of pairs | Replay pair set. | 04 Decision problems | `engines.counterfactual` |
| $R$ | `R` | set of pairs | Replay set, preserving the relation $R \subseteq P$. | 04 Decision problems | `engines.counterfactual.cross_rung_signal` |
| $\Pi$ | `Pi` | program | Program, only where a mathematical name is unavoidable. | 01 Models | `program` |
| $\varphi$ | `phi` | formula metavariable | Formula metavariable. | 02 Syntax | `rulelang.parse_property` |
| $\psi$ | `psi` | formula metavariable | Formula metavariable. | 02 Syntax | `rulelang.parse_property` |
| $\beta$ | `beta` | interpretation | Interpretation of an artefact. | 07 Explanation | `artifacts.admits_interpretation` |
| $i$ | `i` | index | Record or reason index. | 01 Models | `rulelang.eval_temporal_trace` |
| $n$ | `n` | natural number | Finite cardinality or final trace index. | 01 Models | `rulelang.eval_temporal_trace` |
| $\mathsf{Spec}$ | `Spec` | set of formulas | Well-formed formulas of the grammar. | 02 Syntax | `rulelang.parse_property` |
| $\bowtie$ | `bowtie` | comparison operator | One of the six code comparison operators: `==`, `!=`, `<`, `<=`, `>`, `>=`. | 02 Syntax | `rulelang.parse_property` |
| $\oplus$ | `or` | binary operation | Explicit `Algebra.disjunction` component, the t-conorm dual to $\otimes$ under standard negation $1-x$; it is not derived through the algebra's own $\neg$. | 03 Semantics | `manyvalued.Algebra.disjunction` |

