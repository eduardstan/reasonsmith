from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_builder_spec = importlib.util.spec_from_file_location(
    "build_report_schema", Path(__file__).parents[1] / "docs" / "build_report_schema.py"
)
_builder = importlib.util.module_from_spec(_builder_spec)
assert _builder_spec.loader is not None
_builder_spec.loader.exec_module(_builder)
build_schema = _builder.build_schema
from reasonsmith import demo  # noqa: E402
from reasonsmith.report import JSON_SCHEMA_VERSION, check_conformance  # noqa: E402
from reasonsmith.schema import _schema_for_values, schema_from_payloads  # noqa: E402
from reasonsmith.spec import load_pack  # noqa: E402


def test_committed_schema_is_generated_from_report_to_dict():
    schema = build_schema()
    schema_path = (
        Path(__file__).parents[1]
        / "docs"
        / "schema"
        / f"report-v{JSON_SCHEMA_VERSION}.schema.json"
    )
    committed = json.loads(schema_path.read_text())
    assert committed == schema

    report = check_conformance(demo.deployed_credit_system(), load_pack("ecoa"))
    payload = report.to_dict()
    assert schema["properties"]["schema_version"]["const"] == JSON_SCHEMA_VERSION
    assert set(schema["properties"]) == set(payload)
    result_schema = schema["properties"]["results"]["items"]
    assert payload["results"]
    assert set(result_schema["properties"]) == set(payload["results"][0])
    assert set(result_schema["required"]) == set(payload["results"][0])


def test_schema_builder_refuses_empty_and_handles_unusual_json_values():
    import pytest

    with pytest.raises(ValueError):
        schema_from_payloads([])
    assert _schema_for_values([object()])["type"]
