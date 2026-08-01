"""reasonsmith: Table 7 of a published review, made executable.

What this module is for:
  Package root defining version metadata and the overall module taxonomy for audit-grade evidence
  records, reason-deletion certificates, and formal regulation conformance checks.

  The original evidence and verification surface:
    table7.toml     the duty schema, transcribed verbatim from the paper
    evidence.py     the emitter — minimal evidence records, with every field it could not produce
    certificate.py  the reason-deletion certificate, over nesyarena's exact oracle
    conformance.py  the Table 19 checks, including stratified per-group ones
    demo.py         ECOA / Reg B credit and GDPR Art. 22 clinical, end to end

  The v0.2 conformance surface:
    verdict.py      the strength lattice (unattainable < observed < probed < proved) and verdicts
    spec.py         requirements with verbatim provenance, loaded from packs/*.toml
    sut.py          the system-under-test protocol: capabilities, a decision trace, exposed logic
    report.py       the unattainable analysis and the conformance report
    rulelang.py     the whitelisted mini-language rules and properties are parsed and run in
    adapters/       JSONL decision-log, Python-callable and rule-based-system adapters
    engines/        record completeness, rtamt temporal monitors and the Z3 proved engine
    cli.py          checks a JSONL decision log against a requirement pack
    packs/          Table 7, EU AI Act, GDPR, and ECOA / Regulation B requirements

What a reader must not break:
  - Every rung of the lattice except `probed` is implemented here; `probed` needs an engine that
    does not exist yet, and a requirement whose formalism no engine covers is reported as not
    evaluated rather than judged by a weaker check.
    Why this matters: Claiming a higher strength without an engine would launder unverified claims.
  - `proved` is claimed only on what the solver actually established: `engines/proved.py` refuses
    an unmodelled construct, an `unknown` or timed-out solver result, and premises no input can
    satisfy, and it replays a counterexample before reporting a violation.
    Why this matters: Evaluated status must reflect actual engine verification, not fallbacks.
  - Nothing produced here is a compliance guarantee and nothing here is legal advice.
    Why this matters: Technical record checks cannot replace legal determination or guarantees.
"""

__version__ = "0.2.0"
