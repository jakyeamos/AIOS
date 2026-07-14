from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "capture-v1-input-fixtures.json"
sys.path.insert(0, str(ROOT))

from services.capture_v1 import (  # noqa: E402
    CaptureInputError,
    build_capture,
    validate_capture_envelope,
)


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _objects(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _string(value: object) -> str:
    assert isinstance(value, str)
    return value


def _fixtures() -> list[dict[str, object]]:
    value = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, list)
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def test_capture_fixtures_produce_valid_envelopes_and_preserve_structure() -> None:
    envelopes = [
        build_capture(fixture, captured_at="2026-07-14T18:00:00Z") for fixture in _fixtures()
    ]

    assert len(envelopes) == 3
    assert all(validate_capture_envelope(envelope) == [] for envelope in envelopes)

    footnote_structure = _object(_object(envelopes[0]["content"])["structure"])
    assert footnote_structure["headings"] == 1
    assert footnote_structure["footnotes"] == 1
    assert footnote_structure["math"] == 1

    code_structure = _object(_object(envelopes[1]["content"])["structure"])
    assert code_structure["headings"] == 1
    assert code_structure["code_blocks"] == 1
    removals = _objects(_object(envelopes[1]["provenance"])["removals"])
    assert any(item["selector"] == ".ad" for item in removals)
    assert "ignored advertisement" not in _string(_object(envelopes[1]["content"])["markdown"])

    recipe = envelopes[2]
    adapter = _object(recipe["adapter"])
    field_sources = _objects(adapter["field_sources"])
    assert adapter["name"] == "clipper-recipes"
    assert field_sources[2]["canonical_field"] == "instructions"
    assert "Bake." in _string(_object(recipe["content"])["markdown"])
    assert recipe["enrichment"] == {"status": "not_requested", "outputs": []}


def test_capture_is_deterministic_for_a_fixed_timestamp() -> None:
    fixture = _fixtures()[0]

    first = build_capture(fixture, captured_at="2026-07-14T18:00:00Z")
    second = build_capture(fixture, captured_at="2026-07-14T18:00:00Z")

    assert first == second


def test_capture_rejects_invalid_json_input() -> None:
    fixture = _fixtures()[2]
    source = _object(fixture["source"])
    source["content"] = "{not-json}"
    fixture["source"] = source

    with pytest.raises(CaptureInputError, match="not valid JSON"):
        build_capture(fixture, captured_at="2026-07-14T18:00:00Z")


def test_contract_schema_is_pinned_in_aios() -> None:
    schema = json.loads(
        (ROOT / "config" / "contracts" / "capture.v1.schema.json").read_text(encoding="utf-8")
    )

    assert schema["title"] == "Second-brain capture envelope v1"
    assert schema["properties"]["schema_version"]["const"] == "capture.v1"
    assert set(schema["required"]) == {
        "schema_version",
        "captured_at",
        "source",
        "metadata",
        "content",
        "adapter",
        "provenance",
        "validation",
        "enrichment",
    }
