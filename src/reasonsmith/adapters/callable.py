"""Callable wrapper adapter for reasonsmith v0.10.2.

What this module is for:
  Wraps any Python callable or model object (e.g. scikit-learn, PyTorch, custom function) into a
  SystemUnderTest.

What a reader must not break:
  - Capabilities must be declared by the author explicitly and never inferred from object
    inspection.
    Why this matters: Object inspection can falsely guess capabilities based on dummy attributes
    or method names rather than genuine model outputs.
  - The capability basis stays `"declared"`. This adapter sets no `capability_basis` attribute,
    which is what `report._unattainable_result` falls back to, and that is correct here: the
    capabilities came from the author, not from a trace.
    Why this matters: Distinction between declared capabilities and trace-derived capabilities
    must remain explicit in report findings.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from reasonsmith.neural import DeclaredInputSpace
from reasonsmith.sut import BaseSUT


class CallableAdapter(BaseSUT):
    """System Under Test adapter wrapping a Python model or callable."""

    def __init__(
        self,
        target: Any,
        declared_capabilities: set[str] | Iterable[str],
        test_inputs: Iterable[Any] | None = None,
        decisions: Iterable[dict[str, Any]] | None = None,
        input_space: DeclaredInputSpace | Mapping[str, Any] | None = None,
        frontier_ai_status: str | None = None,
    ):
        super().__init__(declared_capabilities, frontier_ai_status=frontier_ai_status)
        if target is None:
            raise ValueError("CallableAdapter requires a non-None target model or function")
        self.target = target
        self._test_inputs = list(test_inputs) if test_inputs is not None else None
        self._precomputed_decisions = list(decisions) if decisions is not None else None
        self._input_space = (
            None if input_space is None else DeclaredInputSpace.from_value(input_space)
        )
        self._validate_input_template()

    def _validate_input_template(self) -> None:
        """Reject a declaration that disagrees with a target-owned prompt template."""
        if self._input_space is None:
            return
        target_template = getattr(self.target, "template", None)
        if target_template is None:
            target_template = getattr(self.target, "prompt_template", None)
        declared = self._input_space.template
        if target_template is None or declared is None or declared.text is None:
            return
        if target_template != declared.text:
            raise ValueError(
                "CallableAdapter input_space template does not match the target's actual template"
            )

    def input_space(self) -> DeclaredInputSpace | None:
        """Return the optional finite input space declared for active replay."""
        return self._input_space

    def decide(self, case: Any) -> Any:
        """Execute decision on a single case using target's decide, predict, or call method."""
        if hasattr(self.target, "decide") and callable(self.target.decide):
            return self.target.decide(case)
        if hasattr(self.target, "predict") and callable(self.target.predict):
            return self.target.predict(case)
        if callable(self.target):
            return self.target(case)
        raise TypeError(
            f"Target object {type(self.target).__name__} is not callable "
            "and has no decide() or predict() method"
        )

    def decisions(self) -> Iterable[dict[str, Any]]:
        """Return decision records.

        If precomputed decisions were provided, returns them.
        If test inputs were provided, executes `decide(case)` for each case and formats records.
        """
        if self._precomputed_decisions is not None:
            return list(self._precomputed_decisions)

        if self._test_inputs is None:
            return []

        records: list[dict[str, Any]] = []
        for case in self._test_inputs:
            output = self.decide(case)
            if isinstance(output, dict):
                records.append(output)
            elif isinstance(case, dict):
                rec = dict(case)
                rec["decision"] = output
                records.append(rec)
            else:
                records.append({"input": case, "decision": output})
        return records


#: Alias for CallableAdapter
CallableSUT = CallableAdapter
