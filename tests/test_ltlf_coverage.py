"""Behavioral tests for finite-trace backend refusals and subprocess boundary."""

from types import SimpleNamespace

import pytest

from reasonsmith import ltlf


def test_black_version_must_identify_black(monkeypatch):
    monkeypatch.setenv("BLACK_SAT_PATH", "/tmp/fake-black")
    monkeypatch.setattr(ltlf, "_verify_black_binary", lambda path: path == "/tmp/fake-black")

    assert ltlf._get_black_path() == "/tmp/fake-black"


def test_invalid_explicit_black_path_is_refused_without_fallback(monkeypatch):
    monkeypatch.setenv("BLACK_SAT_PATH", "/tmp/not-black")
    monkeypatch.setattr(ltlf, "_verify_black_binary", lambda path: False)
    monkeypatch.setattr(ltlf.shutil, "which", lambda name: "/usr/bin/black-sat")

    assert ltlf._get_black_path() is None


@pytest.mark.parametrize(
    "exception, message",
    [
        (ltlf.subprocess.TimeoutExpired("black", 1), "timed out after 30 seconds"),
        (OSError("missing"), "could not be executed: missing"),
    ],
)
def test_black_execution_failures_are_refusals(monkeypatch, exception, message):
    monkeypatch.setattr(ltlf, "_get_black_path", lambda: "/tmp/black-sat")

    def fail(*args, **kwargs):
        raise exception

    monkeypatch.setattr(ltlf.subprocess, "run", fail)
    with pytest.raises(ltlf.UnsupportedConstructError, match=message):
        ltlf._run_black("p0")


def test_black_nonzero_and_unknown_output_are_refusals(monkeypatch):
    monkeypatch.setattr(ltlf, "_get_black_path", lambda: "/tmp/black-sat")
    monkeypatch.setattr(
        ltlf.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="", stderr="bad input"),
    )
    with pytest.raises(ltlf.UnsupportedConstructError, match="exit code 2: bad input"):
        ltlf._run_black("p0")

    monkeypatch.setattr(
        ltlf.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="MAYBE", stderr=""),
    )
    with pytest.raises(ltlf.UnsupportedConstructError, match="unexpected output"):
        ltlf._run_black("p0")


@pytest.mark.parametrize(
    "spec, message",
    [
        ('once(present(signal))', "past operator"),
        ('counterfactually_invariant(outcome, protected)', "pair of executions"),
        ('min(1, 2)', "not a boolean property"),
    ],
)
def test_render_refuses_constructs_without_a_trace_spelling(spec, message):
    with pytest.raises(ltlf.UnsupportedConstructError, match=message):
        ltlf.to_ltlf(spec, ltlf.Abstraction())


def test_render_maps_equivalence_and_contains_axiom():
    abstraction = ltlf.Abstraction()

    rendered = ltlf.to_ltlf(
        'contains(reason, "internal") <=> present(reason)', abstraction
    )

    assert "->" in rendered
    assert abstraction.axioms == ["G(p0 -> p1)"]


def test_satisfiable_empty_trace_is_false_without_calling_black(monkeypatch):
    monkeypatch.setattr(ltlf, "_run_black", lambda formula: (_ for _ in ()).throw(AssertionError()))

    assert ltlf.accepts("p0", []) is False


def test_accepts_empty_valuation_pins_nonempty_trace(monkeypatch):
    seen = []
    monkeypatch.setattr(ltlf, "_run_black", lambda formula: seen.append(formula) or True)

    assert ltlf.accepts("p0", [{}]) is True
    assert "X True" in seen[0]


def test_atom_budget_refusal_precedes_black(monkeypatch):
    monkeypatch.setattr(ltlf, "ATOM_BUDGET", 1)
    monkeypatch.setattr(ltlf, "_run_black", lambda formula: (_ for _ in ()).throw(AssertionError()))

    with pytest.raises(ltlf.UnsupportedConstructError, match="propositional atoms"):
        ltlf._decide("p0 & p1")
