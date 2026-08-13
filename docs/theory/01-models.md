# 1 — Models

**Definition 1.1 (decision record).** Fix a set of signal names $\Sigma$ and a set of values
$\mathrm{Val}$. A decision record $r_i$ is a finite partial map from $\Sigma$ to
$\mathrm{Val}$. The record is the unit returned by `sut.decisions()` and by a replayed
`decide(case)`.

**Definition 1.2 (presence).** A signal is present in a record when its value is defined and is
neither `None`, the blank string, nor an empty list, dictionary, set, or tuple. The values `0` and
`False` are present. An empty reason collection is not present. This is the predicate implemented by
`report._is_present`.

**Definition 1.3 (decision log).** A decision log is a finite word
$\sigma = r_0 \dots r_{n-1}$ of decision records. Its length is $n$.

**Definition 1.4 (empty log).** The log of length zero is the empty log $\varepsilon$.

**Definition 1.5 (observation model).** For a log $\sigma$, the observation model $O(\sigma)$ has
exactly one trace, namely $\sigma$. It interprets a signal at each position by looking it up in the
corresponding record. Thus `sut.decisions()` supplies the observed structure and does not supply
additional traces.

**Definition 1.6 (declaration model).** A system declaration is
$L = (\mathrm{Var}, \mathrm{sorts}, \mathrm{rules}, \mathrm{constraints}, \mathrm{computes})$.
The declaration model $D(L)$ is a symbolic description of the set of finite logs whose records are
executions of `rules` on inputs satisfying `constraints`. Each name in `Var` has a declared sort;
`computes` marks names produced by the rules, while the remaining declared names are supplied to the
rules. A name in neither set has no notion in the declaration.

**Remark 1.1 (no transition system).** No transition relation is modelled. In particular,
$r_{i+1}$ is unconstrained by $r_i$; temporal operators range over log position, not over a state
reachable from a prior state. Consequently no reachability question is expressible in this language.
This is the positional evaluation performed by `rulelang.eval_temporal_trace`, which evaluates by
index and slice and carries no state.

**Definition 1.7 (system-under-test signature).** A system under test exposes the following
signature, where each operation may be absent when its protocol permits absence:

| Operation | Mathematical object | Role |
|---|---|---|
| `capabilities()` | a set $\mathrm{Cap}$ of signal names | emission declaration |
| `decisions()` | a log $\sigma$ | observed evidence |
| `logic()` | a declaration $L$, or no declaration | symbolic description |
| `decide(case)` | a decision record | replay procedure |
| `artifact(decision)` | an inference artefact | inference procedure |

`capabilities()` is authoritative only when declared by the system. A capability set derived from a
trace is evidence about that trace, not automatically about the system.

**Definition 1.8 (reach gates).** Let $c$ be a declared regulatory class, let $\mathrm{Dom}$ be
the declared decision-domain set, and let $C$ be the declared capability set. A requirement is
reached in the following order:

1. A nonempty scope that does not contain $c$ yields `not_applicable` and no strength.
2. A nonempty domain set disjoint from $\mathrm{Dom}$ yields `not_applicable` and no strength.
3. A capability set that does not contain every required signal yields `unattainable` and
   `inconclusive`.
4. Otherwise the requirement reaches the evidence ladder.

An undeclared class or domain therefore cannot reach `satisfied`. These gates do not model a trigger
inside a decision; that is a separate property-level question.
