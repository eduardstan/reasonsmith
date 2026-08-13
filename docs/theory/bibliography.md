# Bibliography

This is the repository bibliography registry. Every citation in the scanned corpus resolves to an entry below, and every entry is cited by a claim outside its own entry. The registry checks are defined in `tests/test_docs_formal.py`.


Every citation anywhere in this repository resolves to an entry here, and every entry here is cited
by at least one claim. That is enforced, not asked for; the mechanism is stated after the list.

**The key convention.** A citation is a backticked, pandoc-style key: an at-sign and a lowercase
ASCII key inside square brackets inside backticks — `[@hajek-1998]`, `[@waldchen-2021]`,
`[@flloat]`. The key is the first author's surname and the year for published work, and the
artefact's name for software that has no paper.

Three properties are why it is this and not something shorter. It is **greppable** and matches
nothing else: `grep -rn '\[@' docs src` finds every citation in the repository, and the at-sign is
what keeps the pattern off `[grading] algebra` and off `details[PROBE_BUDGET_KEY]`, both of which a
bare bracketed word would have collided with. It **sorts**, so two works by one author in one year
would disambiguate by suffix rather than by renaming. And it sits **beside** the prose naming the
authors rather than replacing it, so a reader is never sent to the end of a document to learn whose
work is being described — which is the property that made keying the existing citation sites an
addition rather than a rewrite.

### Specification and verification

- **`[@alpern-1985]`** B. Alpern, F. B. Schneider. *Defining Liveness.* Information Processing
  Letters 21(4):181–185, 1985. — the trace property, which the `behavioural` basis is named after
  (§4.2).
- **`[@terauchi-2005]`** T. Terauchi, A. Aiken. *Secure Information Flow as a Safety Problem.* SAS
  2005, LNCS 3672, 352–367. — 2-safety: the class `counterfactually_invariant` belongs to (Definition 3.8,
  §4.2).
- **`[@conradie-2023]`** W. Conradie, G. Della Monica, A. Muñoz-Velasco, G. Sciavicco, E. Stan. *Fuzzy Halpern and Shoham's interval temporal logics.* Fuzzy Sets and Systems, 2023. — the complete residuated-lattice parent framework for the point-based finite-word fragment (Chapter 3).
- **`[@clarkson-2010]`** M. R. Clarkson, F. B. Schneider. *Hyperproperties.* Journal of Computer
  Security 18(6):1157–1210, 2010. (Earlier at CSF 2008.) — why the denotation is typed over sets of
  traces (§2.1).
- **`[@barthe-2004]`** G. Barthe, P. R. D'Argenio, T. Rezk. *Secure Information Flow by
  Self-Composition.* CSFW 2004, 100–114. — the proof method the counterfactual engine uses (§6.6).
- **`[@degiacomo-2013]`** G. De Giacomo, M. Y. Vardi. *Linear Temporal Logic and Linear Dynamic Logic
  on Finite Traces.* IJCAI 2013, 854–860. — the finite-trace semantics whose clauses
  [`03-semantics.md`](03-semantics.md) Definition 3.8 states and `rulelang.eval_temporal_trace` evaluates (Definition 3.8).
- **`[@manna-1992]`** Z. Manna, A. Pnueli. *The Temporal Logic of Reactive and Concurrent Systems:
  Specification.* Springer, 1992. — the strong and weak previous operators of past LTL, whose
  distinction is what separates this language's `prev` from its `rise` and `fall` at position 0
  ([`03-semantics.md`](03-semantics.md) Definition 3.8).
- **`[@bauer-2011]`** A. Bauer, M. Leucker, C. Schallhart. *Runtime Verification for LTL and TLTL.*
  ACM Transactions on Software Engineering and Methodology 20(4):14, 2011. — the three-valued
  finite-trace distinction this package reports unavailable rather than synthesising (§6.10). Its
  third value is a *truncated trace* and is deliberately not the third value of
  [`03-semantics.md`](03-semantics.md) Definition 3.11, which is `[@bruns-1999]`'s.
- **`[@bruns-1999]`** G. Bruns, P. Godefroid. *Model Checking Partial State Spaces with 3-Valued
  Temporal Logics.* CAV 1999, LNCS 1633, 274–287. — the source of the third value the reference
  interpreter computes: ignorance about the state, not truncation of the trace
  ([`03-semantics.md`](03-semantics.md) Definition 3.11).
- **`[@kleene-1952]`** S. C. Kleene. *Introduction to Metamathematics.* North-Holland, 1952, §64.
  — the strong three-valued tables `rulelang`'s Kleene operators implement
  ([`03-semantics.md`](03-semantics.md) Definition 3.11).
- **`[@vanfraassen-1966]`** B. C. van Fraassen. *Singular Terms, Truth-Value Gaps, and Free Logic.*
  The Journal of Philosophy 63(17):481–495, 1966. — supervaluation, complete for the question
  Kleene is only sound for, and deliberately not implemented
  ([`03-semantics.md`](03-semantics.md) Definition 3.11).
- **`[@kupferman-2003]`** O. Kupferman, M. Y. Vardi. *Vacuity detection in temporal model checking.*
  International Journal on Software Tools for Technology Transfer 4(2):224–233, 2003. (First at
  CHARME 1999.) — the vacuity question (§6.10).
- **`[@beer-2001]`** I. Beer, S. Ben-David, C. Eisner, Y. Rodeh. *Efficient detection of vacuity in
  temporal model checking.* Formal Methods in System Design 18(2):141–163, 2001. — the
  single-occurrence replacement formulation §6.10 implements.
- **`[@geatti-2019]`** L. Geatti, N. Gigante, A. Montanari. *A SAT-based encoding of the one-pass and
  tree-shaped tableau system for LTL.* TABLEAUX 2019, LNCS 11714, 3–20. — the procedure behind
  BLACK, the temporal decision procedure behind the `ltlf` extra (Definition 3.8, §4, §6.10, §6.11).
- **`[@geatti-2021]`** L. Geatti, N. Gigante, A. Montanari, G. Venturato. *Past Matters: Supporting
  LTL+Past in the BLACK Satisfiability Checker.* TIME 2021, LIPIcs 206, 8:1–8:17. — the past
  operators and the finite-trace interpretation that mode of BLACK implements; the source of the
  non-emptiness §6.11's proposition assumes and no guard formula supplies.
- **`[@biere-1999]`** A. Biere, A. Cimatti, E. M. Clarke, Y. Zhu. *Symbolic Model Checking without
  BDDs.* TACAS 1999, LNCS 1579, 193–207. — bounded model checking: writing a bounded run as a
  constraint and handing it to a satisfiability procedure, which is the move `pin(σ)` makes on a
  trace that is already finite (§6.11).
- **`[@flloat]`** M. Favorito, R. Cipollone. *flloat*, a pure-Python LTLf/LDLf-to-DFA library,
  https://github.com/whitemech/flloat — the previous temporal decision procedure behind the
  `ltlf` extra, priced against BLACK and replaced by it (§6.10). Cited as software: it publishes no paper, which is why the key
  convention admits a second shape. Its licence is inconsistent at the source, and this entry
  records three claims rather than one: the PyPI metadata's licence field reads Apache-2.0; the
  LICENSE file the installed wheel ships reads GPL-3.0; and the project's own prose in that same
  wheel's metadata — the upstream README's licence section — reads LGPLv3+. This entry adjudicates
  none of the three: it records the conflict and does not settle which licence governs a reader's
  use of the dependency.

### Explanation, and the reasons behind a decision

- **`[@reiter-1987]`** R. Reiter. *A Theory of Diagnosis from First Principles.* Artificial
  Intelligence 32(1):57–95, 1987. — the conflict/diagnosis minimal-hitting-set duality §3.3
  specialises.
- **`[@shih-2018]`** A. Shih, A. Choi, A. Darwiche. *A Symbolic Approach to Explaining Bayesian
  Network Classifiers.* IJCAI 2018, 5103–5111. — prime-implicant explanations, and an explanation
  read as a minimal sufficient subset of an instantiation (§3.2).
- **`[@ignatiev-2019]`** A. Ignatiev, N. Narodytska, J. Marques-Silva. *Abduction-Based Explanations
  for Machine Learning Models.* AAAI 2019, 1511–1519. — the abductive explanation (AXp).
  Definitions 3 and 4 are this over the deletion lattice (§3.2), and the `artifact` basis is named
  after it (§4.2).
- **`[@ignatiev-2020]`** A. Ignatiev, N. Narodytska, N. Asher, J. Marques-Silva. *From Contrastive to
  Abductive Explanations and Back Again.* AIxIA 2020, LNCS 12414, 335–355. — the AXp/CXp duality
  §3.3 rests on.
- **`[@darwiche-2020]`** A. Darwiche, A. Hirth. *On the Reasons Behind Decisions.* ECAI 2020,
  712–720. — sufficient reasons as prime implicants of a decision, and the vocabulary of §3.2.
- **`[@liffiton-2016]`** M. H. Liffiton, A. Previti, A. Malik, J. Marques-Silva. *Fast, flexible MUS
  enumeration.* Constraints 21(2):223–250, 2016. — MARCO, the seed/shrink/grow enumeration
  `explanations.py` implements (§3.4).
- **`[@waldchen-2021]`** S. Wäldchen, J. MacDonald, S. Hauch, G. Kutyniok. *The Computational
  Complexity of Understanding Binary Classifier Decisions.* Journal of Artificial Intelligence
  Research 70:351–387, 2021. — the `NP^PP`-completeness of deciding sufficiency, in the
  probabilistic reading §3.4 is in.
- **`[@marques-silva-2022]`** J. Marques-Silva, A. Ignatiev. *Delivering Trustworthy AI through
  Formal XAI.* AAAI 2022, 12342–12350. — the model-precise rather than behaviour-sampled side of the
  distinction the `artifact` basis sits on (§4.2).

### Self-reported rationales

- **`[@jacovi-2020]`** A. Jacovi, Y. Goldberg. *Towards Faithfully Interpretable NLP Systems: How
  Should We Define and Evaluate Faithfulness?* ACL 2020, 4198–4205. — faithfulness as against
  plausibility, which is what the `recounted` rung measures (§4.2, §6.4).
- **`[@deyoung-2020]`** J. DeYoung, S. Jain, N. F. Rajani, E. Lehman, C. Xiong, R. Socher,
  B. C. Wallace. *ERASER: A Benchmark to Evaluate Rationalized NLP Models.* ACL 2020, 4443–4458. —
  erasure as the measurement of faithfulness, which is the deletion probe of §3 over a recounted
  set.
- **`[@turpin-2023]`** M. Turpin, J. Michael, E. Perez, S. R. Bowman. *Language Models Don't Always
  Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting.* NeurIPS 2023. — the
  failure the `recounted` rung exists to be one rung below (§4.2).

### Many-valued logic

- **`[@hajek-1998]`** P. Hájek. *Metamathematics of Fuzzy Logic.* Trends in Logic 4, Kluwer, 1998. —
  residuated lattices, and the three fundamental continuous t-norms from which every continuous
  t-norm is an ordinal sum (§5.1, §5.2).
- **`[@dubois-2001]`** D. Dubois, H. Prade. *Possibility Theory, Probability Theory and
  Multiple-Valued Logics: A Clarification.* Annals of Mathematics and Artificial Intelligence
  32:35–66, 2001. — a degree of truth is not a degree of belief, and neither is a fraction of a
  proof (§4.2, §5.4).

### Legal knowledge representation, and the duties

- **`[@benchcapon-1992]`** T. J. M. Bench-Capon, F. P. Coenen. *Isomorphism and legal knowledge based
  systems.* Artificial Intelligence and Law 1(1):65–86, 1992. — the isomorphism discipline
  `verbatim_text` and `drift.py` implement (§6.10).
- **`[@kusner-2017]`** M. J. Kusner, J. R. Loftus, C. Russell, R. Silva. *Counterfactual Fairness.*
  NeurIPS 2017, 4066–4076. — the property `counterfactually_invariant` is an instance of (Definition 3.8).
- **`[@stan-2026]`** I. E. Stan, G. Sciavicco, P. Napoletano. *Symbols and Neurons: A Review of
  Symbolic XAI in Deep Learning.* Journal of Artificial Intelligence Research, 2026. — Table 7
  (p. 36:22) is the duty-to-artifact mapping `table7.toml` transcribes; Section 6.3 (p. 36:24) is
  the scope statement §4.1's chain is the operational form of.

### The registry, and what it does and does not catch

`tests/test_docs_formal.py` holds three things about this list.

1. **Every key cited in the scanned corpus resolves to an entry here**
   (`test_every_citation_key_resolves_to_a_bibliography_entry`). A typo in a key is a failing build,
   not a dangling reference.
2. **Every entry here is cited by at least one claim** outside its own entry
   (`test_every_bibliography_entry_is_cited_by_a_claim`). A source that stops being relied on leaves
   the list rather than accumulating in it.
3. **A source named in the corpus without a key fails the build**
   (`test_a_source_named_without_a_key_is_refused`). This is the half that keeps references from
   drifting back into docstrings: a paragraph naming a publication venue and carrying no key is
   refused, wherever it is.

**The scanned corpus** is `docs/*.md` and `src/reasonsmith/**/*.py`, which is where citations
actually live — the densest concentration in the tree before this document existed was inside
`verdict.py`. Four exclusions are named in the test rather than left implicit, and each is a
statement about the file: `docs/example-output.md` and `docs/nesyarena-conformance-report.md` are
byte-for-byte generated from a builder and contain no prose to cite in;
`docs/legal-sources.md` is the statutory retrieval record, whose sources are laws tracked by
`drift.py` and not scholarly work; and repository-root markdown (`README.md`, `CHANGELOG.md`,
`CLAUDE.md`, `AGENTS.md`, `RESULTS.md`) is either frozen history or agent memory that mirrors these
documents rather than citing independently. Widening the corpus is a one-line change to that tuple.

**What check 3 does not catch, stated because a mechanism whose limit is not stated is trusted
further than it should be.** It works by a list of publication-venue markers, so a source named in a
venue not on that list — a technical report, a thesis, a venue this repository has never cited —
lands unregistered and passes. That is a heuristic and the doc-level checks 1 and 2 are not; the
marker list is in the test and grows when a new venue appears. The alternative, parsing prose for
things that look like citations, produces false positives on a repository whose documents quote
statutes by date and number throughout, and a check that cries wolf is a check somebody switches off.
