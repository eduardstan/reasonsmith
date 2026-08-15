# Marabou slice-4 soundness gate

This is the committed soundness corpus and gate record for neural-SUT slice 4. The corpus is
`tests/neural_soundness_corpus.py`; run it from a checkout with:

```console
PYTHONPATH=src python tests/neural_soundness_corpus.py
```

Complete mode is **not admitted** by this change. The runner therefore records the existing
`complete_mode_not_admitted` refusal for every case; that is a failed/unavailable gate, not a
clean pass and not a universal result. Marabou remains `probed`-only, and bounded `UNSAT` remains
provenance-only.

## Pin and installation evidence

| item | value |
|---|---|
| Marabou release | `2.0.0` (`v2.0.0`) |
| Marabou source commit | `d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d` |
| VNN-LIB profile | `1.0` |
| runner Python | `3.12.9` (`/home/eduard/miniconda3/bin/python`) |
| pip | `25.0` |
| CPU path | open-source; no Gurobi |
| source tag resolution | `d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d` |
| first pip attempt log SHA-256 | `c02e2fdc15da1e9e03151dea9e7ce471cca11b1b51e63b88838325255afc5cd3` |
| build attempt log SHA-256 | `ec582312986efe212211af277abdcc95e8f1af7dab73eda94503a232ea6d3d87` |

The pinned source was attempted with:

```console
python -m pip install 'git+https://github.com/NeuralNetworkVerification/Marabou.git@d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d'
python -m pip install --no-build-isolation --ignore-requires-python \
  'git+https://github.com/NeuralNetworkVerification/Marabou.git@d4b51bf5b14fc2dcd7f28c34d8f4fe4c7447cb6d'
```

Pip first refused the release metadata on this runner (`Python 3.12.9 not in '<=3.12,>=3.8'`).
With `--ignore-requires-python --no-build-isolation`, the source build still failed before producing
a wheel: its bundled OpenBLAS build could not detect the CPU without `gfortran`, and its bundled
pybind11 configuration is incompatible with this runner's CMake 4.4.2. No `maraboupy` package or
`marabou` executable was installed, so complete mode could not be run soundly.

## Corpus cases and results

Each case has a finite reference label. The assertion-order variant only reorders assertions and
adds a comment; it preserves the model and VNN-LIB semantics. `e3b0c442…` is SHA-256 of empty
stdout/stderr because the closed-mode refusal starts no child process.

| case | variant | reference | result | failure | model SHA-256 | query SHA-256 | stdout/stderr SHA-256 |
|---|---|---:|---|---|---|---|---|
| `counterfactual-sat-discriminatory` | `original` | `sat` | `unsupported` | `complete_mode_not_admitted` | `22c8610077f25b2ca457ebbdfc4b90f527a44bddd3b442ff749ecc0ea98053d2` | `e85b7a70fd16dd973adbb44042cf8c2cab9deb66775ac6e4e2a4f2cae19c1543` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `counterfactual-sat-discriminatory` | `assertion-order` | `sat` | `unsupported` | `complete_mode_not_admitted` | `22c8610077f25b2ca457ebbdfc4b90f527a44bddd3b442ff749ecc0ea98053d2` | `bcdd01f0631d1f7818f3d608fec8f02cc7971104dde346e4225d372ada4dd5a0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `counterfactual-unsat-constant` | `original` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `5c1790c53a40ec3e9e846530f5c2aff700a3876135308696131d452085366b20` | `e85b7a70fd16dd973adbb44042cf8c2cab9deb66775ac6e4e2a4f2cae19c1543` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `counterfactual-unsat-constant` | `assertion-order` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `5c1790c53a40ec3e9e846530f5c2aff700a3876135308696131d452085366b20` | `bcdd01f0631d1f7818f3d608fec8f02cc7971104dde346e4225d372ada4dd5a0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `monotonicity-sat-decreasing` | `original` | `sat` | `unsupported` | `complete_mode_not_admitted` | `aff47b24774992d34cc2222a98104a160b5f1ef71c8985439e8fd60ee8f50ca8` | `e0e9d9b8f8ba9cd840ad722e36296404cef535d62639a375e02cea273568129b` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `monotonicity-sat-decreasing` | `assertion-order` | `sat` | `unsupported` | `complete_mode_not_admitted` | `aff47b24774992d34cc2222a98104a160b5f1ef71c8985439e8fd60ee8f50ca8` | `4e5ca644cd578a1bb0465b1689dd8fc9b71fa7aa20725477e8c69a544a651ae5` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `monotonicity-unsat-increasing` | `original` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `6d96ee965fcbca9a9b388820b3a459132a72535b4cd773c31e080f7598b0898f` | `e0e9d9b8f8ba9cd840ad722e36296404cef535d62639a375e02cea273568129b` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `monotonicity-unsat-increasing` | `assertion-order` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `6d96ee965fcbca9a9b388820b3a459132a72535b4cd773c31e080f7598b0898f` | `4e5ca644cd578a1bb0465b1689dd8fc9b71fa7aa20725477e8c69a544a651ae5` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `linf-sat-identity` | `original` | `sat` | `unsupported` | `complete_mode_not_admitted` | `6d96ee965fcbca9a9b388820b3a459132a72535b4cd773c31e080f7598b0898f` | `d89005de26ea33a176da11aaae9fafd0410d41f6bc222ad6e58f5ae133d6176f` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `linf-sat-identity` | `assertion-order` | `sat` | `unsupported` | `complete_mode_not_admitted` | `6d96ee965fcbca9a9b388820b3a459132a72535b4cd773c31e080f7598b0898f` | `00de0504fb8cf5df8e2e1e2e166fc93d98b92a577beb0f2cf9d9d24584212005` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `linf-unsat-constant` | `original` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `9441e8438ec0e6842cace749837d1d02e7688a9975cb947ffc2b444ff15932ce` | `d89005de26ea33a176da11aaae9fafd0410d41f6bc222ad6e58f5ae133d6176f` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `linf-unsat-constant` | `assertion-order` | `unsat` | `unsupported` | `complete_mode_not_admitted` | `9441e8438ec0e6842cace749837d1d02e7688a9975cb947ffc2b444ff15932ce` | `00de0504fb8cf5df8e2e1e2e166fc93d98b92a577beb0f2cf9d9d24584212005` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The six finite reference cases cover discriminatory counterfactual SAT, constant-output
counterfactual UNSAT, decreasing/increasing monotonicity, and identity/constant L∞ local
robustness. The corpus runner compares any future admitted complete `SAT`/`UNSAT` output to those
reference labels; `UNKNOWN`, timeout, crash, malformed output, unsupported queries, and this
closed-mode refusal never become evidence.

## Admission decision

Because the pinned open-source path did not produce a runnable complete verifier and the corpus
could not pass on that path, `MarabouVerifier.max_strength` stays `probed`, `modes` stays
`{bounded-search}`, and `COMPLETE_MODE` remains refused. The VNN-COMP 2024 soundness incident
remains a gating risk rather than a footnote. The first `proved` integration is deferred to
alpha-beta-CROWN in slice 6; see ROADMAP objective 8 and the slice-4 fallback note there.
