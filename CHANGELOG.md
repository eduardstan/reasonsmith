# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This file starts at 0.3.0:
releases before it predate the file and are not reconstructed here.

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
