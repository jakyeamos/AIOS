from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from services.business.connectors.manual import ManualConnector
from services.business.models import SourceRecord
from services.business.normalize import normalize_manual_file, write_immutable_raw
from services.business.store import persist_records
from services.storage import connect

CAPTURED_AT = "2026-07-14T18:00:00+00:00"


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_markdown_manual_source_uses_capture_v1_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    source = tmp_path / "lesson.md"
    source.write_text(
        "---\ntitle: A lesson\ntags: [alpha, beta]\ntimestamp: 2026-07-14\n---\n\n# Heading\n\nBody.",
        encoding="utf-8",
    )

    record = normalize_manual_file(source, fetched_at=CAPTURED_AT)

    assert record.subject_or_title == "A lesson"
    assert record.tags == ["alpha", "beta"]
    assert record.body_text == "# Heading\n\nBody."
    assert record.capture["schema_version"] == "capture.v1"
    provenance = record.capture["provenance"]
    assert isinstance(provenance, dict)
    assert provenance["profile"] == "business.manual"
    assert record.to_json_dict()["capture"] == record.capture


def test_html_manual_source_records_capture_removals(tmp_path: Path) -> None:
    source = tmp_path / "article.html"
    source.write_text(
        "<html><body><h1>Article</h1><p>Keep this.</p>"
        "<div class='ad'>Remove this.</div><script>ignore()</script></body></html>",
        encoding="utf-8",
    )

    record = normalize_manual_file(source, fetched_at=CAPTURED_AT)

    assert record.body_text == "# Article\n\nKeep this."
    provenance = record.capture["provenance"]
    assert isinstance(provenance, dict)
    removals = provenance["removals"]
    assert isinstance(removals, list)
    assert {item["selector"] for item in removals if isinstance(item, dict)} == {".ad", "script"}


def test_json_and_csv_manual_sources_use_the_same_capture_boundary(tmp_path: Path) -> None:
    json_source = tmp_path / "record.json"
    json_source.write_text(
        json.dumps(
            {
                "title": "JSON note",
                "body": "Captured body",
                "timestamp": "2026-07-14T18:00:00Z",
                "tags": ["json"],
            }
        ),
        encoding="utf-8",
    )
    csv_source = tmp_path / "table.csv"
    csv_source.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")

    json_record = normalize_manual_file(json_source, fetched_at=CAPTURED_AT)
    csv_record = normalize_manual_file(csv_source, fetched_at=CAPTURED_AT)

    assert json_record.body_text.startswith("# JSON note")
    assert json_record.tags == ["json"]
    assert _mapping(json_record.capture["adapter"])["name"] == "business.manual"
    assert csv_record.body_text.startswith("| name | value |")
    assert _mapping(csv_record.capture["source"])["input_format"] == "CSV"


def test_existing_source_record_json_remains_backward_compatible(tmp_path: Path) -> None:
    source = tmp_path / "existing.json"
    original = SourceRecord(
        source_id="src_manual_2026_07_14_abc123",
        source_type="manual",
        timestamp="2026-07-14T18:00:00+00:00",
        fetched_at=CAPTURED_AT,
        body_text="Existing normalized body",
        hash="sha256:abc123",
    )
    source.write_text(json.dumps(original.to_json_dict()), encoding="utf-8")

    record = normalize_manual_file(source, fetched_at=CAPTURED_AT)

    assert record == original


def test_manual_connector_discovers_capture_v1_file_formats(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("A note", encoding="utf-8")
    (tmp_path / "article.html").write_text("<p>An article</p>", encoding="utf-8")
    (tmp_path / "table.csv").write_text("name\nalpha\n", encoding="utf-8")
    (tmp_path / "ignored.bin").write_bytes(b"ignored")

    records = ManualConnector(inbox_path=tmp_path).sync(None)

    assert len(records) == 3
    assert {_mapping(record.capture["source"])["input_format"] for record in records} == {
        "Markdown",
        "HTML",
        "CSV",
    }


def test_immutable_raw_record_contains_capture_provenance(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("A note", encoding="utf-8")
    record = normalize_manual_file(source, fetched_at=CAPTURED_AT)

    raw_path = write_immutable_raw(record, tmp_path / "raw")
    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    assert payload["body_text"] == "A note"
    assert payload["capture"]["schema_version"] == "capture.v1"


def test_business_store_persists_capture_metadata_without_extra_write_authority(
    tmp_path: Path,
) -> None:
    source = tmp_path / "note.md"
    source.write_text("A note", encoding="utf-8")
    record = normalize_manual_file(source, fetched_at=CAPTURED_AT)
    conn = connect(tmp_path / "aios.db")
    try:
        summary = persist_records(conn, [record], source_type="manual")
        row = conn.execute(
            "SELECT raw_path, content_hash FROM memory_raw_sources WHERE id = ?",
            (record.source_id,),
        ).fetchone()
    finally:
        conn.close()

    assert summary.records_new == 1
    assert row is not None
    raw_payload = json.loads(Path(row["raw_path"]).read_text(encoding="utf-8"))
    assert row["content_hash"] == record.hash
    assert raw_payload["capture"]["provenance"]["profile"] == "business.manual"
