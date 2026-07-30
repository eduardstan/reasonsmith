"""reasonsmith: Table 7 of a published review, made executable.

Four modules and one data file:

  table7.toml     the duty schema, transcribed verbatim from the paper
  evidence.py     the emitter — minimal evidence records, with every field it could not produce
  certificate.py  the reason-deletion certificate, over nesyarena's exact oracle
  conformance.py  the Table 19 checks, including stratified per-group ones
  demo.py         ECOA / Reg B credit and GDPR Art. 22 clinical, end to end

Nothing produced here is a compliance guarantee and nothing here is legal advice.
"""

__version__ = "0.1.0"
