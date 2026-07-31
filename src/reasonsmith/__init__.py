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
    sut.py          the system-under-test protocol: capabilities and a decision trace
    report.py       the unattainable analysis and the conformance report
    adapters/       JSONL decision-log and Python-callable adapters
    engines/        record completeness and rtamt temporal monitors
    cli.py          checks a JSONL decision log against a requirement pack
    packs/          Table 7, EU AI Act, GDPR, and ECOA / Regulation B requirements

What a reader must not break:
  - Only `unattainable` and `observed` rungs of the lattice are implemented here. `probed` and
    `proved` need engines that do not exist yet.
  - Logical requirements have no engine and are reported as not evaluated rather than judged by a
    weaker check.
  - Nothing produced here is a compliance guarantee and nothing here is legal advice.
"""

__version__ = "0.1.0"
