"""Adapters for System Under Test implementations in reasonsmith.

What this module is for:
  Exports System Under Test (SUT) adapters (`JSONLAdapter`, `CallableAdapter`).

What a reader must not break:
  - Do not export SUT adapters that infer capabilities without explicit declarations or
    trace-derived basis labeling.
"""

from reasonsmith.adapters.callable import CallableAdapter, CallableSUT
from reasonsmith.adapters.jsonl import JSONLAdapter, JsonlSUT

__all__ = [
    "JSONLAdapter",
    "JsonlSUT",
    "CallableAdapter",
    "CallableSUT",
]
