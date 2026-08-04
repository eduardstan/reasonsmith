# Subset-minimal sufficient reasons for a decision of a probabilistic program

This document defines the object the reason-deletion certificate measures. It is written before the
code that measures it, because the defect it repairs is a definition defect and not an
implementation one: the instrument asked a question about *single facts* and reported an answer
about *reasons*, and the two are not the same question.

Read [`semantics.md`](semantics.md) §3 (`certificate`, and *The inference artefact*) first — it
states what the certificate's verdicts mean. This document states what a `deleted` reason **is**.

---

## 0. The defect, in one paragraph

`certificate.certify_artifact` switched each reason off **alone**: for a reason `r`, it took a fact
of `r` that no other enumerated reason uses, set that fact's probability to zero, and re-ran the
system's own engine. If the engine's answer did not move, `r` was reported `deleted` — and a
`deleted` reason is what drives a **violated** verdict on
`ecoa_reg_b_1002_9_b_2_principal_reasons_complete`.

Two reasons that are **jointly** necessary and **individually** removable defeat that test. Removing
either one alone leaves the engine's answer where it was, because the other still carries it; both
are therefore reported `deleted`, and the tool accuses a creditor of omitting two reasons its
inference demonstrably used. This is unsoundness in the direction that matters — a **false
accusation**, produced by an instrument whose whole purpose is to make one only on measured
evidence.

The repair is not to probe harder. It is to say what a reason the answer depends on **is**, over the
whole space of perturbations the artefact admits rather than over the singletons, and then to
measure that.

---

## 1. The setting

Fix one decision.

- `A` — the artefact's **facts**: whatever `artifacts.InferenceArtifact` treats as switchable. For
  the one shipped family (`artifacts/ground_program.py`) these are the EDB atoms of a nesyarena
  ground program.
- `β : A → [0,1]` — the **base interpretation**, one independent probability per fact.
- `q` — the decision, as a query atom.
- `R = {r₁, …, r_n}`, each `rᵢ ⊆ A` — the **reasons**: every support bounded proof enumeration finds
  for `q` at the artefact's own `exact_depth`. Write `A_q = ⋃ᵢ rᵢ`.
- `φ_q = ⋁ᵢ ⋀_{a ∈ rᵢ} a` — the decision's DNF over those supports.
- `V(β) = Pr_β[φ_q]` — **exact inference**: nesyarena's exact weighted model count.
- `E(β)` — the **engine's** answer to `q` on the same program and the same `β`. A black box; the
  only thing this document assumes about it is the monotonicity the artefact declares (§4).
- `tol` — the certificate's tolerance, `1e-9` by default.

This is not a classifier over a feature space, which is the setting the published formal-XAI
definitions are stated in (§9). Two things differ and both matter:

1. **The decision is a probability, not a label.** There is no `f(v) = c` to preserve. What is
   preserved is the engine's *answer*, up to `tol`.
2. **The perturbation space is not a product of feature domains.** The artefact protocol has a
   `without(fact)` and, deliberately, no `with_(fact)`. So the reachable interpretations are exactly
   the ones below `β` in the deletion order.

Both differences make the definitions below **weaker** than their classifier counterparts, never
stronger. That is the correct direction and §7 states what it costs.

---

## 2. The perturbation space: the deletion lattice

> **Definition 1 (deletion lattice).** For `D ⊆ A_q`, write `β[D↦0]` for the interpretation `β` with
> every fact in `D` set to probability zero. The **deletion lattice** of this decision is
> `L(β) = { β[D↦0] : D ⊆ A_q }`, ordered by `⊆` on `D`.
>
> `L(β)` is the whole of what the artefact protocol can reach. `β` itself is its top element.

Two facts about it, both used below.

`V(β[D↦0]) = Pr_β[φ_q ∧ ⋀_{a∈D} ¬a]`: giving a fact probability zero deletes exactly the worlds in
which it holds. So deletion is *conditioning the decision's models away*, and the exact side of the
instrument is a measure over a shrinking set of worlds.

> **Definition 2 (moved).** `MOVED(D) ⟺ |E(β) − E(β[D↦0])| > tol`.
>
> One evaluation of `MOVED` is one **engine probe**: the cost unit everything in §7 is counted in.

---

## 3. The definitions

The shape is Ignatiev, Narodytska and Marques-Silva's abductive explanation (AXp) and its
contrastive dual (CXp), with the feature space replaced by the deletion lattice and "same
prediction" replaced by "same answer within `tol`".

> **Definition 3 (deletion-sufficient set).** `S ⊆ A_q` is **sufficient** for the engine's answer at
> `β` iff for every `D ⊆ A_q \ S`, `¬MOVED(D)`.
>
> In words: holding the facts of `S` on, nothing that can be switched off outside `S` changes the
> answer. `S` is enough on its own.

> **Definition 4 (AXp — subset-minimal sufficient reason).** `S ⊆ A_q` is an **abductive
> explanation** of the engine's answer iff `S` is sufficient and no proper subset of `S` is.
>
> This is the object the title names: a *subset-minimal sufficient reason for a decision of a
> probabilistic program*, over the perturbation space that program's artefact admits.

> **Definition 5 (CXp — subset-minimal contrastive set).** `C ⊆ A_q` is **contrastive** iff
> `MOVED(C)`, and a **CXp** iff it is contrastive and no proper subset of it is.
>
> In words: `C` is a smallest set of facts whose *joint* removal the engine notices. A CXp of size 1
> is exactly what the old per-fact probe could see. Every CXp of size ≥ 2 is a joint necessity the
> old probe was blind to.

> **Definition 6 (relevance).** A fact `a ∈ A_q` is **relevant** iff it belongs to some AXp of the
> engine's answer, and **irrelevant** otherwise.

---

## 4. The duality, and why the monotonicity declaration is its precondition

An artefact declares whether its inference is **monotone in its facts** — adding a fact never
retracts a reason that held without it (`artifacts.InferenceArtifact.monotone`, landed in
[#112](https://github.com/eduardstan/reasonsmith/pull/112)).
Under that declaration `E` is non-decreasing in `β`, so:

> **Lemma 1 (upward closure).** If `MOVED(D)` and `D ⊆ D'` then `MOVED(D')`.
>
> `E(β[D'↦0]) ≤ E(β[D↦0]) ≤ E(β)`, and `MOVED(D)` says the middle term is more than `tol` below the
> right one.

Everything else follows from Lemma 1, and none of it holds without it. That is the point worth
recording: the declaration [#112](https://github.com/eduardstan/reasonsmith/pull/112) added for
a *soundness* reason — so that a lawfully retracted reason
is not read as a dropped one — turns out to be exactly the precondition the AXp/CXp theory needs. It
is not two premises, it is one.

> **Lemma 2 (sufficiency is a hitting-set condition).** `S` is sufficient ⟺ `A_q \ S` is not moved
> ⟺ `A_q \ S` contains no CXp ⟺ `S` intersects every CXp.
>
> Left-to-right of the first ⟺ is Definition 3 at `D = A_q \ S`; right-to-left is Lemma 1.

> **Theorem (minimal-hitting-set duality).** The AXps are exactly the minimal hitting sets of the
> CXps, and the CXps are exactly the minimal hitting sets of the AXps.
>
> This is Reiter's 1987 duality between conflicts and diagnoses, as related to abductive and
> contrastive explanations by Ignatiev, Narodytska, Asher and Marques-Silva (§9). Lemma 2 is the only
> thing specialising it to the deletion lattice.

> **Corollary 1.** `⋃ AXps = ⋃ CXps`. A fact is relevant iff it belongs to some CXp.
>
> The union of the minimal hitting sets of a family is the union of the family.

> **Corollary 2 (pruning).** A fact `a` with `MOVED({a})` belongs to no CXp of size > 1, because
> `{a}` is already contrastive and no CXp properly contains another.
>
> This is what lets the search below ignore every fact the per-fact probe already settled.

> **Corollary 3 (short circuit).** If `¬MOVED(A_q)` then there is no CXp at all, every fact is
> irrelevant, and `∅` is the unique AXp — one engine probe settles the whole decision.
>
> By Lemma 1, `¬MOVED(A_q)` implies `¬MOVED(D)` for every `D`.

---

## 5. Reasons, not facts: the corrected `deleted`

The duty is about **reasons**, so the fact-level notion has to be lifted, and the lift is where the
old instrument's second problem — a reason whose every fact is shared with another reason — is
answered as well as it can be.

> **Definition 7 (a reason the engine's answer depends on).** `r ∈ R` is **live** iff some fact of
> `r` that no other reason in `R` uses is relevant.
>
> The privacy condition is what makes the conclusion *about `r`*. A shared relevant fact establishes
> that the engine depends on **that fact**, and cannot say through which of the reasons carrying it.

> **Definition 8 (a deleted reason).** `r ∈ R` is **deleted** iff **no** fact of `r` — private or
> shared — is relevant.
>
> No attribution problem arises here, and that is why the quantifier is over all facts and not just
> the private ones. If no fact of `r` is relevant then by Corollary 1 no CXp meets `r`, so by Lemma 2
> `A_q \ r` is sufficient: the engine's answer survives the removal of the whole of `r` in every
> context the lattice reaches. Nothing needs attributing, because there is nothing to attribute.

> **Definition 9 (undetermined).** `r ∈ R` is **undetermined** iff it is neither live nor shown
> deleted: the enumeration of CXps was not exhausted within budget, or the only relevant facts of
> `r` are shared with another reason.

Four consequences, each of which the code must hold:

1. **`live` needs one witness; `deleted` needs the complete enumeration.** Live is existential over
   CXps and is established by finding one. Deleted is universal and is established only by an
   enumeration that terminated (§7).
2. **The old per-fact probe survives inside this, unchanged and still sound.** A private fact `a ∈ r`
   with `MOVED({a})` is a CXp of size 1 (Corollary 2), so `r` is live by Definition 7. Every reason
   the old instrument called `live` is live under this definition. The old instrument was sound on
   `live` and unsound only on `deleted`, and only `deleted` changes.
3. **`undetermined` is a strictly weaker claim than `deleted` and never a stronger one.** It is not
   counted as a missing reason, so it cannot drive a violated verdict; it is reported, so a reader is
   never told a reason was cleared when the search ran out.
4. **A shared-fact reason is no longer silently pooled with a zero-signal probe.** The three
   not-certified states — `unseparable` (no private fact to attribute a movement to), `inconclusive`
   (the probe carried no exact signal at all) and `undetermined` (the joint search did not resolve
   it) — are different facts about the evidence and are reported apart. `Certificate.uncertified`
   remains their union, because every one of them means the same thing to a verdict: *not counted
   deleted, not counted live*.

---

## 6. What this has to do with the missing probability mass

`docs/example-output.md` prints, for decision `APP-1042`:

```
exact value 0.991399   engine value 0.765600   gap -0.225799   tolerance 1e-09
...
ATTRIBUTION: ... The missing probability mass is 0.225799.
```

That figure is on a **different axis** from everything above, and the certificate has always run
both checks precisely because neither implies the other (`certificate.py`, *Both independent checks
must pass*). Stating the relation exactly:

**The mass is a value-gap, not a deletion measurement.** `0.225799 = V(β) − E(β)`. Both terms are
evaluated at the *same* `β`, with nothing switched off. It compares two aggregation policies over
one interpretation: exact weighted model counting over all of `φ_q`, against whatever the engine
does. For a top-`k` engine that reports `Pr_β[φ_kept]` it is `Pr_β[φ_q ∧ ¬φ_kept]` — the probability
of exactly those worlds in which the decision holds *only* by way of a proof the engine discarded.

**The deletion side is a different function.** Write `Δ(D) = V(β) − V(β[D↦0])`. Then

> `Δ(D) = Pr_β[φ_q ∧ ⋁_{a∈D} a]`,

which is the measure of a union of events indexed by `D`, hence **monotone and submodular** in `D`.
`MOVED`, by contrast, is merely **upward-closed** (Lemma 1) and is not submodular in any sense: joint
necessity *is* the statement `MOVED({a,b}) ∧ ¬MOVED({a}) ∧ ¬MOVED({b})`, which no submodular
indicator admits.

That asymmetry is the defect stated in two lines. The old rule read the exact side one fact at a
time, where submodularity means single probes **over**-state what a fact exclusively carries; and it
read the engine side one fact at a time, where mere upward-closure means single probes
**under**-state what the engine depends on. Both errors push the same way — toward `deleted` — and
they compose.

**So the mass licenses one claim and not the other.** `0.225799` is evidence that the engine's
*value* is wrong, and it is the figure the attribution reasons about when it names top-`k`
truncation. It is **not** evidence that any particular reason is irrelevant. In the demonstration
those two happen to agree — the engine really does depend on none of C02–C05, which the corrected
search confirms with one probe by Corollary 3 — but the agreement is a fact about that engine, not a
consequence of the arithmetic. Nothing in the certificate now reads a mass as a dependence.

**And the sum is not the gap.** `Σ_r Δ(private facts of r)` over the deleted reasons is not
`V(β) − E(β)`, in either direction. Submodularity gives `Σ ≥ Δ(⋃)` for the deletion side, and the
gap is not a `Δ` at all. No rendering here adds per-reason drops up, and none may start.

---

## 7. Cost, budget, and what a partial enumeration may claim

Deciding relevance is hard, and the honest statement of how hard is Wäldchen, MacDonald, Hauch and
Kutyniok's: deciding whether a set of features suffices for a classifier decision is
`NP^PP`-complete, and this setting is a probabilistic one of exactly that shape. Here the engine is a
black box, so the only oracle is a probe, and the search is over `2^|A_q|` deletion patterns where
the old probe was linear in reasons.

**The search.** CXps are enumerated by the MARCO loop of Liffiton, Previti, Malik and Marques-Silva,
with Z3 as the NP oracle over the subset lattice — a Boolean `x_a` per searchable fact, blocking
clauses recording what has been covered — and the *engine* as the membership oracle:

- **Space.** `A_q` minus every fact the per-fact probe already found singleton-moving (Corollary 2).
- **Short circuit.** `¬MOVED(A_q)` ends the search exhaustively in one probe (Corollary 3). This is
  the common case for a truncating engine and it is why the demonstration costs one extra probe.
- **Seed.** Any subset the map solver has not covered.
- **Shrink.** A moved seed is minimised by dropping one fact at a time while it still moves,
  yielding a CXp; supersets of it are blocked.
- **Grow.** An unmoved seed is extended one fact at a time while it stays unmoved, yielding a
  maximal unmoved set (whose complement is an AXp, by Lemma 2); subsets of it are blocked.
- **Termination.** The map solver going unsatisfiable means every subset is covered, so **every** CXp
  has been found and `⋃ CXps` is the complete relevant set.

**The budget.** Engine probes are counted and capped. The cap, the probes spent, and — the field that
carries the whole claim — **whether the enumeration terminated** travel on the certificate and into
`RequirementResult.details[PROBE_BUDGET_KEY]`, under the discipline `PROBE_BUDGET_FIELDS` already
forces on every `probed` verdict: *a bounded search read as a guarantee is the overclaim the lattice
exists to prevent, and a budget a reader cannot see is a bound that may as well not exist.*

**A partial enumeration degrades downward, always.** If the budget is spent before the map solver is
exhausted:

- every CXp found is still a CXp, so every reason shown **live** stays live — the claim is
  existential and one witness is one witness;
- no reason may be reported **deleted**, because that claim is universal over CXps and the
  enumeration did not finish. Such a reason is `undetermined`.

So a shorter search reports **fewer** missing reasons, never more. There is no setting of the budget
at which this instrument accuses a system it would otherwise have cleared, and that is the
invariant to keep when tuning it.

---

## 8. What this does not do

- **It does not widen the perturbation space.** The lattice is downward-only, because the protocol
  is (`artifacts.InferenceArtifact.without`, and deliberately no `with_`). An AXp here is an AXp
  *relative to the deletions the artefact admits*, which is a weaker object than an AXp over a full
  feature space. §2 of `semantics.md` and the `LIMITS` string say the same thing about `deleted` and
  they still say it.
- **It does not detect defeat.** A defeater holding no fact of any enumerated reason is still never
  switched off, still leaves no fingerprint, and is still refused at the declaration
  (`semantics.md` §3, *The inference artefact*). Nothing here weakens that refusal and nothing here
  substitutes for it.
- **It does not attribute a shared fact.** A reason all of whose relevant facts are shared is
  `undetermined`, not live and not deleted. Splitting such a reason from its sharers is a question
  about the *program*, not about the probe. This is a real change in the other direction: a reason
  the old instrument called `deleted` on the strength of one private fact, while a *shared* fact of
  it moves the engine, is now `undetermined` — the old label asserted the engine's answer did not
  depend on that reason while a deletion of one of its facts moved the engine, which it had no
  evidence for. `docs/example-output.md`'s drift window is the shipped instance.
- **It does not promote an `unseparable` or `inconclusive` reason to `deleted`.** Definition 8 would
  license it — a reason no fact of which is relevant needs no attribution — and the implementation
  deliberately does not, so this pass can only ever move a reason *out* of `deleted`. Minting new
  accusations out of a search whose completeness rests on a monotonicity declaration nothing here
  confirms is a decision to make on purpose, not a corollary to fall into.
- **It does not make the reasons correct.** The certificate still says only that the engine used all
  the reasons exact inference found, on this program and this interpretation.
- **It does not measure a group.** Nothing here says anything about a set of reasons a notice owes
  collectively; the duty is read reason by reason, as it was.

---

## 9. Sources

Published work only, and every definition above is a specialisation of one of these rather than a
new one.

- R. Reiter. *A Theory of Diagnosis from First Principles.* Artificial Intelligence 32(1):57–95,
  1987. — the conflict/diagnosis minimal-hitting-set duality the Theorem in §4 specialises.
- A. Shih, A. Choi, A. Darwiche. *A Symbolic Approach to Explaining Bayesian Network Classifiers.*
  IJCAI 2018, 5103–5111. — prime-implicant explanations of a decision, and the reading of an
  explanation as a minimal sufficient subset of an instantiation.
- A. Ignatiev, N. Narodytska, J. Marques-Silva. *Abduction-Based Explanations for Machine Learning
  Models.* AAAI 2019, 1511–1519. — the abductive explanation (AXp): a subset-minimal set of literals
  that, with the model, entails the prediction. Definitions 3 and 4 are this over the deletion
  lattice.
- A. Ignatiev, N. Narodytska, N. Asher, J. Marques-Silva. *From Contrastive to Abductive
  Explanations and Back Again.* AIxIA 2020, LNCS 12414, 335–355. — the AXp/CXp minimal-hitting-set
  duality, on which §4 rests.
- A. Darwiche, A. Hirth. *On the Reasons Behind Decisions.* ECAI 2020, 712–720. — sufficient reasons
  as prime implicants of a decision, and the vocabulary of §3.
- M. Liffiton, A. Previti, A. Malik, J. Marques-Silva. *Fast, flexible MUS enumeration.* Constraints
  21(2):223–250, 2016. — MARCO, the seed/shrink/grow enumeration §7 implements.
- S. Wäldchen, J. MacDonald, S. Hauch, G. Kutyniok. *The Computational Complexity of Understanding
  Binary Classifier Decisions.* JAIR 70:351–387, 2021. — the `NP^PP`-completeness §7 cites, and the
  probabilistic reading of sufficiency.

The exact inference this is measured against — the ground-program IR, the bounded proof enumeration
and the exact weighted model count — is nesyarena's and is depended on, not reimplemented. See
`CLAUDE.md`, *Dependency*.
