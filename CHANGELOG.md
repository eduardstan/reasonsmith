# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This file starts at 0.3.0:
releases before it predate the file and are not reconstructed here.

## [Unreleased]

### Added

- `contains(signal, "phrase")`, a property-language atom that reads *what a statement says* rather
  than whether a field is blank. Its first argument is a signal name and its second a string
  literal, so the wording a duty forbids is fixed by the pack and never supplied by the system
  being audited. Comparison folds ASCII case and nothing else, and a non-ASCII phrase is refused at
  load time — the fold has to stay reproducible character-for-character by the Z3 encoding, so a
  fold that is not one-to-one would let the solver and the interpreter disagree about the same
  string. It is a substring test and claims to be nothing more: it does not model *specific*. See
  [docs/semantics.md](docs/semantics.md) §2 and [docs/authoring-packs.md](docs/authoring-packs.md),
  *a phrase in a `spec` is the clause's own words*.

### Changed

- **A `logical` duty is now answered from a decision trace.** A `logical` property is a property of
  one decision record, so a trace of them is evidence about it; the build used to report *not
  evaluated* while that evidence sat in front of it, which was the fragment's label deciding what
  could be checked. `docs/semantics.md` §3.5 already stated the principle in its first bullet and
  contradicted it two bullets later. A presence conjunction still keeps the record engine and its
  per-signal, per-record diagnostics; every other state formula is monitored per record. The
  separate rule that a temporal duty never rises above `observed` is unchanged.

  **What this means for an existing run:** a `logical` duty against a system that exposes only a
  decision log used to be reported *not evaluated* and could now be reported `violated`, so a run
  that exited 0 can exit 2 on evidence it always had. Two shapes still cannot be monitored and stay
  not evaluated: a comparison against a Boolean constant, and an implication written
  `Implies(a, b)` rather than `(a) -> (b)` — the monitor renders the `spec` as the pack wrote it.
- **12 CFR 1002.9(b)(2) checks the clause's own negative constraint, and carries its trigger.** The
  duty was a conjunction of `present()` atoms, so a reason of `"n/a"` satisfied it. It now also
  checks that the statement is not one of the two the clause itself calls insufficient, which makes
  it falsifiable against a plain decision log with no oracle. Its fragment moved from `record` to
  `logical`, so a log holding a single decision is now reported not evaluated on it rather than
  satisfied.

  The property is guarded by the trigger the clause states in its own first words — it governs the
  statement *required by paragraph (a)(2)(i)* — so a creditor that lawfully took the (a)(2)(ii)
  disclosure branch is **no longer reported violated**. The cost is stated rather than hidden:
  where a log carries no statement of reasons at all, the duty is `satisfied` vacuously and no
  report outcome distinguishes that from a trace that was checked and met
  ([docs/semantics.md](docs/semantics.md) §4).

### Fixed

- The Z3 encoding of `present()`'s blankness rule now also governs `contains()`, so the solver and
  the reference interpreter agree that a value the record does not carry carries no phrase.

## [0.3.0]

### Added

- A second applicability gate, `domains`, beside the existing regulatory-class `scope` gate. It
  records the *kind of decision* a duty is about, from `reasonsmith.spec.DECISION_DOMAINS`, and is
  matched by intersection against what a system declares. See
  [docs/authoring-packs.md](docs/authoring-packs.md) for the vocabulary rules and
  [docs/semantics.md](docs/semantics.md) §4 for what a not-applicable verdict on it does and does
  not say.
- A report whose duties were skipped for a missing declaration says so: `render_text`,
  `render_html` and the CLI's stderr all carry a line naming how many duties were reported not
  applicable solely because the system declared no decision domain, and what to pass to check
  them. Exit codes are unchanged.

### Changed — breaking

- **A requirement block without `domains` no longer loads.** Loading a pack that has one fails with
  `missing required field(s): domains`. Every externally authored pack must add `domains = [...]`
  naming the kinds of decision the duty is about, or `domains = []` for a duty that is about no
  particular kind of decision. There is deliberately no default: a wildcard reachable by
  forgetting the field would defeat the gate, so the omission is refused the way a missing
  `binding` or `scope` already is.
- **An invocation that declares no decision domain now reports domain-limited duties
  `not_applicable` rather than checking them.** Declare what the system decides with
  `--system-domain <domain>` (repeatable), or set `system_domains` on an adapter. All three
  requirements of the shipped ECOA pack and two rows of the Table 7 pack are domain-limited today,
  so an existing ECOA run without the flag now checks nothing and reports every duty not
  applicable. `reasonsmith` never infers a system's decision domain.
