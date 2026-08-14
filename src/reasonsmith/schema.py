"""Generated JSON Schema helpers for the conformance report envelope.

The property names come from ``to_dict()`` payloads, not a second hand-maintained field list.
The report's additive-key convention is represented by ``additionalProperties: true`` while the
current emitted keys remain required and are checked by the shape tests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from reasonsmith.report import JSON_SCHEMA_VERSION


def _schema_for_values(values: Sequence[Any]) -> dict[str, Any]:
    present = [value for value in values if value is not None]
    nullable = len(present) != len(values)
    if not present:
        # Current report optionals are nullable strings (including an absent strength); keeping
        # null in the generated type is what lets a consumer validate both outcomes.
        return {"type": ["string", "null"]}

    if all(isinstance(value, Mapping) for value in present):
        keys = sorted({key for value in present for key in value})
        properties = {
            key: _schema_for_values([value[key] for value in present if key in value])
            for key in keys
        }
        required = sorted(key for key in keys if all(key in value for value in present))
        result: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "required": required,
            # New report keys are additive under JSON_SCHEMA_VERSION's contract.
            "additionalProperties": True,
        }
    elif all(isinstance(value, list) for value in present):
        items = [item for value in present for item in value]
        result = {"type": "array", "items": _schema_for_values(items) if items else {}}
    elif all(isinstance(value, bool) for value in present):
        result = {"type": "boolean"}
    elif all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        result = {"type": "integer"}
    elif all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present):
        result = {"type": "number"}
    elif all(isinstance(value, str) for value in present):
        result = {"type": "string"}
    else:
        result = {"type": ["object", "array", "boolean", "integer", "number", "string"]}

    if nullable:
        result["type"] = (
            [result["type"], "null"]
            if isinstance(result["type"], str)
            else [*result["type"], "null"]
        )
    return result


def schema_from_payloads(payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the report schema from one or more actual ``to_dict`` payloads."""
    if not payloads:
        raise ValueError("at least one report payload is required")
    schema = _schema_for_values(list(payloads))
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"https://reasonsmith.dev/schema/report-v{JSON_SCHEMA_VERSION}.schema.json",
            "title": "reasonsmith conformance report envelope",
        }
    )
    schema["properties"]["schema_version"] = {
        "const": JSON_SCHEMA_VERSION,
        "type": "integer",
    }
    return schema
