"""Closed-vocabulary tests for inference artefact semantics claims."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from nesyarena.ir import Atom, GroundProgram

from reasonsmith.artifacts import reference_semantics
from reasonsmith.artifacts.ground_program import GroundProgramArtifact
from reasonsmith.artifacts.reason_trace import ReasonTraceArtifact
from reasonsmith.certificate import Certificate
from reasonsmith.spec import CLAIMED_SEMANTICS, normalize_claimed_semantics


def test_claimed_semantics_outside_vocabulary_is_refused_with_accepted_set():
    with pytest.raises(ValueError, match="Accepted:.*distribution semantics") as caught:
        normalize_claimed_semantics("top-2 approximation of distribution semantics")

    assert all(repr(value) in str(caught.value) for value in CLAIMED_SEMANTICS)


def test_certificate_post_init_refuses_unknown_claimed_semantics():
    with pytest.raises(ValueError, match="Accepted:"):
        Certificate(
            query="decision-1",
            adapter_name="example",
            claimed_semantics="invented semantics",
            exact_depth=None,
            exact_value=0.0,
            engine_value=0.0,
            tol=1e-9,
            verdicts=(),
            attribution="none",
        )


def test_certificate_retains_canonical_semantics_at_its_public_boundary():
    certificate = Certificate(
        query="decision-1",
        adapter_name="example",
        claimed_semantics=" Distribution Semantics ",
        exact_depth=None,
        exact_value=0.0,
        engine_value=0.0,
        tol=1e-9,
        verdicts=(),
        attribution="none",
        exact_semantics=" DISTRIBUTION SEMANTICS ",
    )

    assert certificate.claimed_semantics == "distribution semantics"
    assert certificate.exact_semantics == "distribution semantics"


def test_reference_semantics_canonicalizes_and_refuses_unknown_values():
    assert (
        reference_semantics(SimpleNamespace(exact_semantics=" Distribution Semantics "))
        == "distribution semantics"
    )
    with pytest.raises(ValueError, match="Accepted:"):
        reference_semantics(SimpleNamespace(exact_semantics="invented semantics"))


def test_every_shipped_artefact_family_exposes_only_normalized_claims():
    query = Atom("decision")
    ground_program = GroundProgramArtifact(
        GroundProgram(()),
        {},
        query,
        SimpleNamespace(name="ground-program", claimed_semantics="distribution semantics"),
        0,
        monotone=True,
    )
    reason_trace = ReasonTraceArtifact(
        query,
        {},
        lambda suppressed: 0.0,
        engine_name="reason-trace",
        claimed_semantics="free-text rationale",
        monotone=True,
    )

    assert ground_program.claimed_semantics in CLAIMED_SEMANTICS
    assert ground_program.exact_semantics in CLAIMED_SEMANTICS
    assert reason_trace.claimed_semantics in CLAIMED_SEMANTICS

    invalid_adapter = SimpleNamespace(name="invalid", claimed_semantics="invented semantics")
    invalid_ground_program = GroundProgramArtifact(
        GroundProgram(()), {}, query, invalid_adapter, 0, monotone=True
    )
    with pytest.raises(ValueError, match="Accepted:"):
        _ = invalid_ground_program.claimed_semantics
    with pytest.raises(ValueError, match="Accepted:"):
        ReasonTraceArtifact(
            query,
            {},
            lambda suppressed: 0.0,
            engine_name="invalid",
            claimed_semantics="invented semantics",
            monotone=True,
        )
