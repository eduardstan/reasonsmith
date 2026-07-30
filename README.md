# reasonsmith

Audit-grade explanations for symbolic and neurosymbolic decisions.

A decision that affects a person carries a legal duty to give reasons. This turns that duty into
something a machine can produce and check: given a decision, the symbolic artifact behind it, and
the duty that applies, `reasonsmith` emits the minimal evidence record that duty requires — and says
plainly which required fields it could not produce. A record that is incomplete is reported as
incomplete, never quietly shortened.

Where the system reasons over proofs it goes further. Exact inference enumerates every reason, so
the reasons an approximate engine actually used can be compared against the complete set. Reasons
that were dropped are named, not estimated — which is the part post-hoc explanation methods cannot
do, because they have no ground truth to compare against.

Status: early. Nothing here is a compliance guarantee, and none of it is legal advice.

## Where the duties come from

The duty-to-artifact mapping is Table 7 of *Symbols and Neurons: A Review of Symbolic XAI in Deep
Learning* (Stan, Sciavicco & Napoletano, JAIR 2026), a review of 273 primary studies that ties
symbolic artifacts to duties under the EU AI Act, GDPR, ECOA/Reg B, FDA GMLP and NIST AI RMF, and
specifies the minimal records each duty needs. That review says what to retain; this produces it.

Table 7 is transcribed verbatim into `src/reasonsmith/table7.toml`. That file is data, not code:
every duty records its row number, and every machine key sits next to the exact cell text it stands
for, so it can be checked against the printed table without the PDF. `traceability_report()` prints
the whole thing side by side. Where a design decision and Table 7 would disagree, Table 7 wins.

## What is here

Four modules and one data file. Deliberately not a framework — there is no plugin system, no rules
engine and no abstraction over duties, because the four duties beyond the two demonstrated are out
of scope and machinery to make them easy would bury the point.

| | |
|---|---|
| `table7.toml` | the six duties, verbatim, with traceability |
| `evidence.py` | the emitter: minimal evidence records, and every required field it could not produce |
| `certificate.py` | the reason-deletion certificate |
| `conformance.py` | the Table 19 checks, including the stratified per-group ones |
| `demo.py` | ECOA / Reg B credit and GDPR Art. 22 clinical, end to end |

### The emitter

`emit(duty_id, decision_id, fields)` returns a record that is either COMPLETE or INCOMPLETE, and an
INCOMPLETE one names the fields it lacks. Nothing is defaulted, inferred or silently dropped; a key
outside the duty's Table 7 row is rejected rather than accepted, and material that is not Table 7
evidence travels in `attachments`, where it cannot be read as discharging the duty. A partial record
presented as complete would launder a compliance gap into a document that reads as authoritative,
which is the failure mode with real-world consequences.

### The reason-deletion certificate

For proof-based systems exact inference enumerates *every* reason, so there is a ground truth that
post-hoc explanation methods do not have. The certificate compares the reasons an engine actually
used against that exact set, names the ones that are missing, and attributes the loss to an
inference setting.

It works through nesyarena's adapter protocol as it stands, by deletion probe: a reason with a fact
no other reason uses can be switched off alone, and if the engine's answer does not move, the
engine's answer did not depend on it. Two independent checks must both hold to pass — the probe
(every reason live) and the value check against the exact oracle — because neither subsumes the
other. An engine that silently drops a reason is caught by the first; one that keeps every reason
and quietly rescales its answer is caught only by the second. Reasons that cannot be probed in
isolation are reported as uncertified and the certificate returns INCONCLUSIVE; they are never
assumed live.

## Install and run

The exact oracle, the ground-program IR, bounded proof enumeration and the adapter protocol all come
from [nesyarena](https://github.com/eduardstan/nesyarena), which is depended on as a library and not
reimplemented here. It is not on PyPI:

```sh
pip install -e path/to/nesyarena
pip install -e .
python -m reasonsmith.demo     # the full report: both domains, the perturbed engines, the checks
pytest
```

`tests/conftest.py` puts `src` on the path, so the tests run without installing this package.

## Findings

- **The stratified check, and the hypothesis registered for it.** The registered hypothesis was that
  low-probability reasons are dropped first, so atypical cases lose reasons faster. It holds in one
  form and not the other. Varying model confidence alone costs a case no reasons at all — top-k
  keeps a fixed number of proofs, and scaling every score down leaves their order unchanged — so
  per-group *coverage* is flat while retained share and fidelity both move against the atypical
  group. Varying how many reasons a case trips does move coverage. A deployment watching coverage
  alone would have seen the confidence-driven harm as clean. Reported as a partial negative result
  because it was registered in advance. The cohorts are frozen synthetic ones built to separate the
  two mechanisms; whether real atypical cases trip more reasons is an empirical question this does
  not answer.
- **Stability bites too.** Under a top-1 setting, drift in a single signal silently replaces the
  reason an applicant is given, on an unchanged file.
- **Pre-existing in nesyarena, not fixed here.** 98 tests pass; `tests/test_e6_findings.py` and
  `tests/test_learning_parity.py` fail to collect because `torch` is not installed. `torch` is an
  optional extra (`learning`), so this is an environment gap rather than a code failure, and it is
  reported rather than fixed silently.

## Limits

Every record and every certificate carries its own limits, and they are not boilerplate. A document
that looks like conformity evidence and is not one is the thing worth avoiding here. Nothing this
produces is a compliance guarantee, and none of it is legal advice. A certificate speaks only about
the one program, base interpretation and query it was run on. Table 7 completeness is a check on the
form of a record, never on the truth of what it contains — the credit demonstration shows a record
that is COMPLETE under Table 7 while the certificate shows four of its five reasons are missing.

## Licence

MIT.
