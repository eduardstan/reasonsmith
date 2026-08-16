# Global notation

This table is the notation register for every chapter under `docs/theory/`. Mathematical text uses
GitHub LaTeX; implementation identifiers remain code spans.

| LaTeX form | ASCII spelling | sort/type | meaning | chapter of introduction | code object where one exists |
|---|---|---|---|---|---|
| $\mathbf{A} = (A, \sqcap, \sqcup, \otimes, \to, \neg, 0, 1)$ | `Algebra` | algebra | An algebra and its carrier and operations. | 03 Semantics | `manyvalued.Algebra` |
| $A$ | `A` | carrier | Carrier of an algebra. | 03 Semantics | `manyvalued.Algebra` |
| $\sqcap$ | `meet` | binary operation | Lattice meet; trace aggregation uses the lattice minimum. | 03 Semantics | `manyvalued.degree_over_trace` (`min`) |
| $\sqcup$ | `join` | binary operation | Lattice join; no standalone runtime operation is exposed. | 03 Semantics | — |
| $\otimes$ | `t_norm` | binary operation | The algebra's conjunction (t-norm). | 03 Semantics | `manyvalued.Algebra.conjunction` |
| $\to$ | `residuum` | binary operation | Residuated implication. | 03 Semantics | `manyvalued.Algebra.residuum` |
| $\neg$ | `negation` | unary operation | Algebra negation. | 03 Semantics | `manyvalued.Algebra.negation` |
| $0$ | `0` | element of $A$ | Bottom element. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $1$ | `1` | element of $A$ | Top element. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $\mathsf{f}$ | `kleene_false` | Kleene value | False in the Kleene chain. | 03 Semantics | `rulelang.kleene_value` |
| $\mathsf{u}$ | `kleene_unknown` | Kleene value | Unknown in the Kleene chain. | 03 Semantics | `rulelang.UNKNOWN` |
| $\mathsf{t}$ | `kleene_true` | Kleene value | True in the Kleene chain. | 03 Semantics | `rulelang.kleene_value` |
| $F$ | `facts` | set of facts | Facts exposed by an inference artefact. | 01 Models | `artifacts.InferenceArtifact` |
| $T$ | `traces` | set of traces | Trace set used by the denotation. | 01 Models | `rulelang.eval_temporal_trace` |
| $L$ | `L` | declaration | System declaration. | 01 Models | `sut.SystemUnderTest.logic` |
| $\mathbb{L}(\beta)$ | `L(beta)` | deletion lattice | Lattice of deletions of the fact set for interpretation $\beta$. | 07 Explanation | `explanations.contrastive_sets` |
| $D(L)$ | `D(L)` | input space | Declaration model and its input space. | 01 Models | `engines.proved.encode_logic_domain` |
| $\mathrm{Dom}$ | `Dom` | set | Declared decision-domain set. | 01 Models | `report._inapplicability` |
| $\setminus$ | `setminus` | binary operation | Set difference in explanation subsets. | 07 Explanation | `explanations.contrastive_sets` |
| $S \subseteq F$ | `S subset F` | subset | A deletion subset and the AXp/sufficient set. | 07 Explanation | `artifacts.InferenceArtifact.without` |
| $u_i \subseteq F$ | `u_i subset F` | subset | One reason's facts. | 07 Explanation | `explanations.contrastive_sets` |
| $\mathcal{R} = \lbrace u_1, \dots, u_n\rbrace$ | `reasons` | family of subsets | Family of reasons. | 07 Explanation | `artifacts.InferenceArtifact.reasons` |
| $r_i$ | `r_i` | record | The $i$th decision record. | 01 Models | `rulelang.eval_expression` |
| $\sigma = r_0 \dots r_{n-1}$ | `sigma` | finite trace | A finite sequence of records. | 01 Models | `rulelang.eval_temporal_trace` |
| $v, v' \in \mathrm{Var}$ | `v, v_prime in Var` | signal | Signal names supplied by a system. | 02 Syntax | `spec.Requirement.variables` |
| $\mathrm{Var}$ | `Var` | set | Set of signal names. | 01 Models | `spec.Requirement.variables` |
| $\mathcal{C}$ | `C` | CXp | Contrastive explanation set. | 07 Explanation | `explanations.contrastive_sets` |
| $\mathrm{Cap}$ | `Cap` | set | Capability names a system exposes. | 01 Models | `sut.SystemUnderTest.capabilities` |
| $C.n$ | `C.n` | label | Global numbered label. | 08 Evidence | `report.ConformanceReport` |
| $p$ | `p` | protected variable | Protected variable in a counterfactual property. | 04 Decision problems | `rulelang.counterfactually_invariant` |
| $E$ | `E` | value | Audited engine answer for one interpretation. | 07 Explanation | `artifacts.InferenceArtifact.computes` |
| $V$ | `V` | value | Exact inference value for one interpretation. | 07 Explanation | `artifacts.InferenceArtifact.exact_value` |
| $a$ | `a` | fact | One switchable fact in $F$. | 07 Explanation | `artifacts.InferenceArtifact.without` |
| $\Pr$ | `Pr` | probability | Probability under an independent fact interpretation. | 07 Explanation | `nesyarena` |
| $\bigcup$ | `bigcup` | operation | Union of reasons or explanation families. | 07 Explanation | `explanations.contrastive_sets` |
| $\mapsto$ | `mapsto` | assignment | Assignment of zero probability in a deletion. | 07 Explanation | `artifacts.InferenceArtifact.without` |
| $\rightsquigarrow$ | `refinement` | relation | Refinement from a clause record to a requirement tuple. | 06 Formalisation | `spec.Requirement` |
| $\sqsubseteq$ | `admissibility` | relation | Evidence-basis/strength admissibility relation. | 08 Evidence | `verdict.BASIS_RUNGS` |
| $\times$ | `product` | operation | Cartesian product in the admissibility relation. | 08 Evidence | `verdict.BASIS_RUNGS` |
| $w$ | `w` | phrase metavariable | Literal phrase used by `contains`. | 02 Syntax | `rulelang.contains_literal` |
| $q$ | `q` | query | Query supplied to an inference artefact. | 04 Decision problems | `artifacts.InferenceArtifact.exact_value` |
| $x, y, z$ | `x, y, z` | element of $A$ | Algebra elements. | 03 Semantics | `manyvalued.Algebra` |
| $c$ | `c` | class | Regulatory class. | 01 Models | `spec.Requirement.scope` |
| $k$ | `k` | constant | Comparison constant. | 02 Syntax | `rulelang.parse_property` |
| $t_a, t_b$ | `t_a, t_b` | instant | UTC instants of an event-time anchor and endpoint. | 03 Semantics | `reasonsmith.event_time` |
| $P$ | `declared_pairs` | set of pairs | Pair set admitted by the declaration. | 04 Decision problems | `engines.counterfactual` |
| $R$ | `replay_pairs` | set of pairs | Replay set, preserving the relation $R \subseteq P$. | 04 Decision problems | `engines.counterfactual.cross_rung_signal` |
| $\Pi$ | `Pi` | program | Program, only where a mathematical name is unavoidable. | 01 Models | `program` |
| $\varphi$ | `phi` | formula metavariable | Formula metavariable. | 02 Syntax | `rulelang.parse_property` |
| $\psi$ | `psi` | formula metavariable | Formula metavariable. | 02 Syntax | `rulelang.parse_property` |
| $\beta$ | `beta` | interpretation | Interpretation of an artefact. | 07 Explanation | `artifacts.admits_interpretation` |
| $\lambda$ | `lambda` | probability | Probability assigned to one fact by an interpretation. | 07 Explanation | `artifacts.InferenceArtifact.at` |
| $i$ | `i` | index | Record or reason index. | 01 Models | `rulelang.eval_temporal_trace` |
| $n$ | `n` | natural number | Finite cardinality or final trace index. | 01 Models | `rulelang.eval_temporal_trace` |
| $\mathsf{Spec}$ | `Spec` | set of formulas | Well-formed formulas of the grammar. | 02 Syntax | `rulelang.parse_property` |
| $\oplus$ | `or` | binary operation | Explicit `Algebra.disjunction` component, the t-conorm dual to $\otimes$ under standard negation $1-x$; it is not derived through the algebra's own $\neg$. | 03 Semantics | `manyvalued.Algebra.disjunction` |
| $\mathcal{M}$ | `M` | structure | Structure supplying interpretations and traces. | 03 Semantics | `rulelang.eval_expression` |
| $O(\sigma)$ | `O(sigma)` | observation structure | Structure induced by an observed finite log. | 01 Models | `sut.SystemUnderTest.decisions` |
| $\Sigma$ | `Sigma` | set | Set of signal names. | 01 Models | `spec.Requirement.variables` |
| $\mathrm{Val}$ | `Val` | set | Set of record values. | 01 Models | `sut.SystemUnderTest` |
| $\mathrm{Trace}_{\mathcal{M}}$ | `Trace_M` | set | Traces admitted by structure $\mathcal{M}$. | 03 Semantics | `rulelang.eval_temporal_trace` |
| $[\hspace{-0.17em}[\cdot]\hspace{-0.17em}]$ | `denotation` | map | Denotation of a formula. | 03 Semantics | `rulelang.eval_expression` |
| $\uparrow$ | `undefined` | value | Undefined value of the partial denotation. | 03 Semantics | `rulelang.UNKNOWN` |
| $\mathbb{B}$ | `Boolean` | algebra | Two-element Boolean algebra, a degenerate residuated lattice. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $j$ | `j` | index | Temporal position or quantifier index. | 03 Semantics | `rulelang.eval_temporal_trace` |
| $\bigwedge$ | `infimum` | aggregation | Finite meet over a family of values. | 03 Semantics | `manyvalued.degree_over_trace` |
| $\bigvee$ | `supremum` | aggregation | Finite join over a family of values. | 03 Semantics | — |
| $\mathcal{P}$ | `powerset` | operation | Powerset constructor in a trace domain. | 03 Semantics | `rulelang.eval_temporal_trace` |
| $[\hspace{-0.17em}[$ | `left_bracket` | delimiter | Left denotation bracket. | 03 Semantics | `rulelang.eval_expression` |
| $]\hspace{-0.17em}]$ | `right_bracket` | delimiter | Right denotation bracket. | 03 Semantics | `rulelang.eval_expression` |
| $\cdot$ | `dot` | placeholder | Formula placeholder in the denotation map. | 03 Semantics | `rulelang.eval_expression` |
| $\rightharpoonup$ | `partial_map` | map | Partial-map arrow. | 03 Semantics | `rulelang.eval_expression` |
| $\Longleftrightarrow$ | `iff` | relation | Logical equivalence in residuation. | 03 Semantics | `manyvalued.Algebra.residuum` |
| $\models$ | `models` | relation | Satisfaction of a formula by a trace or structure. | 04 Decision problems | `rulelang.eval_temporal_trace` |
| $\le$ | `le` | relation | Non-strict order on algebra elements and indices. | 03 Semantics | `manyvalued.Algebra` |
| $\emptyset$ | `emptyset` | set | Empty trace set. | 03 Semantics | `manyvalued.degree_over_trace` |
| $\varepsilon$ | `epsilon` | trace | Empty log. | 01 Models | `rulelang.eval_temporal_trace` |
| $\max$ | `max` | operation | Maximum operation in the Łukasiewicz t-norm. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $\min$ | `min` | operation | Minimum operation in shipped algebras. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $\wedge$ | `wedge` | binary operation | Boolean conjunction in $\mathbb{B}$. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $\vee$ | `vee` | binary operation | Boolean disjunction in $\mathbb{B}$. | 03 Semantics | `manyvalued.ALGEBRAS` |
| $o$ | `o` | outcome | Outcome name in a relational atom. | 03 Semantics | `rulelang.counterfactually_invariant` |
