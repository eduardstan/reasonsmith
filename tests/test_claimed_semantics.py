"""Closed-vocabulary tests for inference artefact semantics claims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

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


def test_every_shipped_claimed_semantics_literal_is_in_the_vocabulary():
    """Derive declarations from source so this cannot drift behind a hand-copied inventory."""
    root = Path(__file__).parents[1] / "src" / "reasonsmith"
    declarations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and any(
                    isinstance(target, ast.Attribute) and target.attr == "claimed_semantics"
                    for target in node.targets
                )
            ):
                declarations.append(node.value.value)

    assert declarations
    assert set(declarations) <= set(CLAIMED_SEMANTICS)
