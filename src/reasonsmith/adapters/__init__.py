"""Adapters for System Under Test implementations in reasonsmith.

What this module is for:
  Exports System Under Test (SUT) adapters (`JSONLAdapter`, `CallableAdapter`, `RulesAdapter`).

What a reader must not break:
  - Do not export SUT adapters that infer capabilities without explicit declarations or
    trace-derived basis labeling.
    Why this matters: Conformance reports must explicitly label whether a system's capability set
    was authoritatively declared or derived from a sample trace.
"""

from reasonsmith.adapters.callable import CallableAdapter, CallableSUT
from reasonsmith.adapters.jsonl import JSONLAdapter, JsonlSUT
from reasonsmith.adapters.rules import RulesAdapter, RulesSUT

__all__ = [
    "JSONLAdapter",
    "JsonlSUT",
    "CallableAdapter",
    "CallableSUT",
    "RulesAdapter",
    "RulesSUT",
]
