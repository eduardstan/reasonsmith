"""reasonsmith: Table 7 of a published review, made executable.

Four modules and one data file:

  table7.toml     the duty schema, transcribed verbatim from the paper
  evidence.py     the emitter — minimal evidence records, with every field it could not produce
  certificate.py  the reason-deletion certificate, over nesyarena's exact oracle
  conformance.py  the Table 19 checks, including stratified per-group ones
  demo.py         ECOA / Reg B credit and GDPR Art. 22 clinical, end to end

Alongside them, the first slice of the v0.2 conformance core — a verdict carries the strength of
the evidence behind it, and the strongest thing this tool can say is often computable before the
system runs at all:

  verdict.py      the strength lattice (unattainable < observed < probed < proved) and verdicts
  spec.py         requirements with verbatim provenance, loaded from packs/*.toml
  sut.py          the system-under-test protocol: declared capabilities, and a decision trace
  report.py       the unattainable analysis and the conformance report

Only the `unattainable` and `observed` rungs of that lattice are implemented. `probed` and `proved`
need engines that do not exist yet, and a requirement no engine here covers is reported as not
evaluated rather than judged by a weaker check.

Nothing produced here is a compliance guarantee and nothing here is legal advice.
"""

__version__ = "0.1.0"
