# 3 — Semantics

This chapter gives the denotation of the language. The parent framework is the complete residuated
lattice implemented by `manyvalued.py`, in the point-based finite-word fragment of Conradie, Della
Monica, Muñoz-Velasco, Sciavicco & Stan, *Fuzzy Halpern and Shoham's interval temporal logics*
(*Fuzzy Sets and Systems*, 2023) `[@conradie-2023]`.

**Definition 3.1 (uniform denotation).** Relative to a structure $\mathcal{M}$ and an algebra
$\mathbf{A}$, the language denotes the partial map

$$
[\![\cdot]\!]_{\mathcal{M},\mathbf{A}} : \mathsf{Spec} \to
(\mathcal{P}(\mathrm{Trace}_M) \mathrel{\rightharpoonup} A).
$$

The structure supplies meanings for names and the traces over which a formula is evaluated. The
argument is uniformly a set of traces; the relational atom is therefore a 2-safety property rather
than a property of one execution `[@clarkson-2010]`.

**Definition 3.2 (algebra).** The algebra is
$\mathbf{A} = (A, \sqcap, \sqcup, \otimes, \to, \neg, 0, 1)$, a complete residuated
lattice. The operations $\sqcap$ and $\sqcup$ are lattice meet and join. The operation
$\otimes$ is a commutative monoid operation with unit $1$, and $\to$ is its residuum:

$$
x \otimes z \le y \quad\Longleftrightarrow\quad z \le x \to y,
\qquad \neg x = x \to 0.
$$

The Boolean algebra $\mathbb{B}$ is the degenerate instance with carrier $\{0,1\}$,
$\sqcap = \otimes = \wedge$, $\sqcup = \vee$, and material implication. The graded
fragment instead uses the carrier $[0,1]$ with the declared algebra.

**Definition 3.3 (the shipped algebras).** The three shipped algebras have the following operations.

| Name | $x \otimes y$ | $x \to y$ | $\neg x$ |
|---|---|---|---|
| `lukasiewicz` | $\max(0, x+y-1)$ | $\min(1,1-x+y)$ | $1-x$ |
| `godel` | $\min(x,y)$ | $1$ if $x ≤ y$, else $y$ | $1$ if $x=0$, else $0$ |
| `product` | $x \cdot y$ | $1$ if $x ≤ y$, else $y/x$ | $1$ if $x=0$, else $0$ |

`[grading] algebra` is a declared pack parameter, never a default. Negation and the biresiduum
are derived from the stored residuum.

**Definition 3.4 (partiality).** A formula may be undefined, written $\uparrow$, when a name is
not interpreted, a value has the wrong sort, supplied evidence scores no atom, or the atom
`undetermined` occurs. Undefinedness is not ordinary strict propagation. The insensitivity rule is:

$$
[\![\varphi]\!] \text{ is defined exactly when its value is the same for every
value in } A \text{ that undefined subformulas could take.}
$$

Thus a false strong conjunction is defined even when its other operand is undefined, because
$0 \otimes x = 0$ for every $x$ in the shipped algebras. The reference interpreter may resolve
such a case by short-circuiting; a strict encoding may instead return $\uparrow$.

**Definition 3.5 (state formulas).** At one record, a state formula has value
$[\![\varphi]\!]^{\mathrm{rec}}_{\mathcal{M},\mathbf{A}}(r) \in A$. The atom
rows are:

| Formula | Value |
|---|---|
| `present(x)` | $1$ when `x` is present, otherwise $0$ |
| `contains(x, "w")` | $1$ when the record's statement contains `w` under the ASCII fold, otherwise $0$; $\uparrow$ when a present value is not a statement |
| comparison | $1$ when its two partial numeric values satisfy the comparison, otherwise $0$; $\uparrow$ when either value is undefined |
| bare Boolean `x` | $1$ for `True`, $0$ for `False`, and $\uparrow$ otherwise |
| `degree(x, "g")` | the supplied grading value in $A$, or $\uparrow$ when the grading supplies none |
| `undetermined(x, "g", "a")` | $\uparrow$ for every structure and algebra |

The comparison and presence rows are crisp even when $A$ is not $\mathbb{B}$. `contains` is zero
when the record carries no value and undefined when it carries a non-statement. A grading value is
constant for the run and is not read from the record.

**Definition 3.6 (connectives).** For state or temporal values, the connectives are

| Formula | Denotation |
|---|---|
| `not` $\varphi$ | $\neg[\![\varphi]\!]$ |
| $\varphi$ `and` $\psi$ | $[\![\varphi]\!] \otimes [\![\psi]\!]$ |
| $\varphi$ `or` $\psi$ | $[\![\varphi]\!] \oplus [\![\psi]\!]$ |
| implication | $[\![\varphi]\!] \to [\![\psi]\!]$ |
| equivalence | $([\![\varphi]\!] \to [\![\psi]\!]) \otimes ([\![\psi]\!] \to [\![\varphi]\!])$ |

Here $\oplus$ is the explicit `Algebra.disjunction` component, dual to $\otimes$ under the
standard negation $1-x$. It is not derived through the algebra's own $\neg$. By contrast,
$\sqcup$ is lattice join and is used for existential quantification over positions and traces.
The strong conjunction $\otimes$ and lattice meet $\sqcap$ therefore remain distinct. Over
$\mathbb{B}$ the distinctions coincide extensionally.

**Definition 3.7 (trace and set aggregation).** For every fragment except `counterfactual`, a state
formula is evaluated by

$$
[\![\varphi]\!]^{\mathrm{tr}}(\sigma) =
\bigwedge_{i < n} [\![\varphi]\!]^{\mathrm{rec}}(r_i),
\qquad
[\![\varphi]\!]^{\mathrm{set}}(T) =
\bigwedge_{\sigma \in T} [\![\varphi]\!]^{\mathrm{tr}}(\sigma).
$$

The aggregation is lattice infimum, that is, $\sqcap$, not $\otimes$. A temporal formula is
instead evaluated at a position and its trace value is the position-zero value.

**Proposition 3.1 (factoring).** For every fragment except `counterfactual`, set evaluation factors
through individual traces: evaluate each trace and take the lattice meet. Thus the uniform
set-of-traces typing does not require a cross-trace operation for those fragments.

**Definition 3.8 (finite-trace temporal semantics).** Let $\sigma$ have length $n > 0$ and let
$i$ be a position. A state subformula is evaluated at each position by its record value. The
position clauses are:

$$
\begin{aligned}
[\![\text{always}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \bigwedge_{i \le j < n} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,j), \
[\![\text{eventually}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \bigvee_{i \le j < n} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,j), \
[\![\text{next}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \begin{cases}[\![\varphi]\!]^{\mathrm{pos}}(\sigma,i+1),&i+1<n,\\1,&i=n-1,\end{cases} \
[\![\text{prev}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \begin{cases}[\![\varphi]\!]^{\mathrm{pos}}(\sigma,i-1),&i>0,\\1,&i=0,\end{cases}.
\end{aligned}
$$

The remaining clauses are

$$
\begin{aligned}
[\![\text{historically}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \bigwedge_{0 \le j \le i} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,j), \
[\![\text{once}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \bigvee_{0 \le j \le i} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,j), \
[\![\text{rise}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \begin{cases}[\![\varphi]\!]^{\mathrm{pos}}(\sigma,0),&i=0,\\
    [\![\varphi]\!]^{\mathrm{pos}}(\sigma,i) \otimes \neg[\![\varphi]\!]^{\mathrm{pos}}(\sigma,i-1),&i>0,\end{cases} \
[\![\text{fall}(\varphi)]\!]^{\mathrm{pos}}(\sigma,i)
  &= \begin{cases}\neg[\![\varphi]\!]^{\mathrm{pos}}(\sigma,0),&i=0,\\
    \neg[\![\varphi]\!]^{\mathrm{pos}}(\sigma,i) \otimes [\![\varphi]\!]^{\mathrm{pos}}(\sigma,i-1),&i>0.\end{cases}
\end{aligned}
$$

For the binary operators:

$$
[\![\text{until}(\varphi,\psi)]\!]^{\mathrm{pos}}(\sigma,i)
 = \bigvee_{i \le j < n} ([\![\psi]\!]^{\mathrm{pos}}(\sigma,j) \otimes
   \bigwedge_{i \le k < j} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,k)),
$$

$$
[\![\text{since}(\varphi,\psi)]\!]^{\mathrm{pos}}(\sigma,i)
 = \bigvee_{0 \le j \le i} ([\![\psi]\!]^{\mathrm{pos}}(\sigma,j) \otimes
   \bigwedge_{j < k \le i} [\![\varphi]\!]^{\mathrm{pos}}(\sigma,k)).
$$

The trace value of a temporal formula is its position-zero value. The strong and weak boundary distinction is the standard distinction for previous operators `[@manna-1992]`. The runtime interpreter uses the
Kleene chain $\mathsf{f} < \mathsf{u} < \mathsf{t}$ for these clauses, rather than treating
unknown record values as ordinary falsity `[@kleene-1952]`.

**Remark 3.1 (boundary divergence).** Runtime `next` and `prev` are weak at their boundaries:
`next` is $1$ at the final position and `prev` is $1$ at position zero. The LTLf abstraction in
`ltlf.py` renders `next` as strong `X`, which is false at the final position. These are the two
faithful code-side semantics; the divergence is deliberately documented, not resolved here.

**Definition 3.9 (relational atom).** `counterfactually_invariant(o, p)` is the whole
`counterfactual` fragment. Over a declaration model, its value is $1$ exactly when every pair of
records arising from admissible inputs, agreeing on every input except $p$, has equal outcome at
$o$:

$$
r(o)=r'(o)
$$

for every such pair $r,r'$ in traces of $T$. This is a 2-safety property. On an observation model
$O(\sigma)$ the atom is $\uparrow$: a log supplies no certified pair differing only in $p$.
The admissible values of $p$ come from declaration constraints, never from a trace.

**Remark 3.2 (where factoring fails).** The relational atom does not factor through individual
traces, because its truth quantifies over pairs of executions and their agreement on all inputs
except $p$. It cannot be composed with a conjunction, negation, or implication in this language.
Unawareness of $p$ is not invariance: a declaration with no notion of $p$ is reported unattainable,
not satisfied.

**Definition 3.10 (empty-log narrowing).** The ordinary lattice equation would give the top value
when an infimum ranges over no elements. This package deliberately narrows that point:

$$
[\![\varphi]\!]^{\mathrm{set}}(\emptyset)=\uparrow,
\qquad
[\![\varphi]\!]^{\mathrm{tr}}(\varepsilon)=\uparrow.
$$

An empty log is not evaluated, and combining zero verdicts is `inconclusive`, not vacuously
`satisfied`. This deliberately declines the sharper supervaluation reading of unknowns `[@vanfraassen-1966]`.


**Remark 3.3 (rendering conformance anchors).** The finite-word denotation is checked against its
runtime rendering on the following four forms: `count_a % count_b > 1`, `1 < count_a < 10`,
`(count_a >= 1) <-> (count_b >= 1)`, and `count_a > 1`. The first three are refused by the
rendering where it diverges; the last is the exact-tie boundary. The corresponding executable
warrants are `test_the_four_named_shapes_are_still_what_the_document_records` and
`test_the_divergences_are_the_ones_the_document_reports`.


**Definition 3.11 (Kleene value layer).** The reference interpreter evaluates Boolean temporal values in
the strong Kleene chain $\mathsf{f} < \mathsf{u} < \mathsf{t}$ `[@kleene-1952]`. The unknown value is
ignorance about a record, not truncation of a trace; supervaluation over completions is not part of
this language `[@vanfraassen-1966]`.


## 3.12 Graded state and trace readings

A `degree(signal, predicate)` atom receives its value from the `manyvalued.Grading` supplied to
`check_conformance`, not from the audited system or its trace. The grading names the authority,
scale, and method that fixed the values. A missing score is $\uparrow$, not degree zero.

Above a graded atom, conjunction, disjunction, implication, and equivalence use the declared
residuated algebra. Equivalence is the derived biresiduum

$$
(\varphi \to \psi) \otimes (\psi \to \varphi).
$$

A graded atom under a comparison, arithmetic, or a temporal operator is refused at load: those
shapes would introduce a threshold or a temporal many-valued semantics that this package does not
claim. A formula with no graded atom remains two-valued, and the algebra parameter applies only to
graded requirements.

**Definition 3.12 (degree over a trace).** For a non-empty finite trace, the degree is the lattice
infimum of the per-record degrees:

$$
\mathrm{degree}(\sigma,\varphi) =
\bigwedge_{i < n} [\![\varphi]\!]^{\mathrm{rec}}(r_i).
$$

An empty trace has no degree. A degree is a measurement, not a verdict or a fraction of a proof;
the result carries no `Strength`, and no threshold turns it into `satisfied`.
