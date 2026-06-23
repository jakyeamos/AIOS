from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

ALLOWED_PREDICATES: frozenset[str] = frozenset(
    {
        "caused_by",
        "depends_on",
        "blocks",
        "supersedes",
        "contradicts",
        "supports",
        "evidence_for",
        "belongs_to_project",
        "decided_in",
        "implemented_by",
        "requested_by_user",
        "derived_from",
        "related_to",
        "has_open_question",
        "has_constraint",
        "has_risk",
        "has_owner",
        "has_status",
    }
)
VALIDITY_STATUSES: frozenset[str] = frozenset(
    {"active", "superseded", "contradicted", "uncertain", "archived"}
)

RowDict = dict[str, object]


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _row_to_dict(
    cursor: sqlite3.Cursor, row: sqlite3.Row | tuple[object, ...] | None
) -> RowDict | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(zip(row.keys(), row, strict=False))
    columns = [column[0] for column in cursor.description or ()]
    return dict(zip(columns, row, strict=False))


def _fetch_one(conn: sqlite3.Connection, query: str, params: Sequence[object]) -> RowDict | None:
    cursor = conn.execute(query, params)
    return _row_to_dict(cursor, cursor.fetchone())


def _fetch_all(conn: sqlite3.Connection, query: str, params: Sequence[object]) -> list[RowDict]:
    cursor = conn.execute(query, params)
    return [
        row_dict for row in cursor.fetchall() if (row_dict := _row_to_dict(cursor, row)) is not None
    ]


def _json_list(values: Sequence[str] | None) -> str:
    return json.dumps(list(values or []), sort_keys=True)


def _decoded_receipt(row: RowDict | None) -> RowDict | None:
    if row is None:
        return None
    decoded = dict(row)
    for key in ("source_ids", "fact_ids", "relationship_ids"):
        raw = decoded.get(key)
        if not isinstance(raw, str) or not raw:
            decoded[key] = []
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = []
        decoded[key] = parsed if isinstance(parsed, list) else []
    return decoded


def _where_clause(filters: list[tuple[str, object | None]]) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    for column, value in filters:
        if value is None:
            continue
        clauses.append(f"{column} = ?")
        params.append(value)
    return (" WHERE " + " AND ".join(clauses), params) if clauses else ("", params)


def ensure_memory_layer_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_raw_sources (
          id TEXT PRIMARY KEY,
          source_type TEXT NOT NULL,
          source_path TEXT,
          project_id TEXT,
          author TEXT,
          confidence REAL,
          original_content TEXT,
          extraction_status TEXT DEFAULT 'pending',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_raw_sources_project
          ON memory_raw_sources(project_id, source_type, updated_at DESC);
        CREATE TABLE IF NOT EXISTS memory_facts (
          id TEXT PRIMARY KEY,
          fact_text TEXT NOT NULL,
          entity TEXT,
          predicate TEXT,
          object_value TEXT,
          project_scope TEXT,
          validity_status TEXT NOT NULL DEFAULT 'active' CHECK (
            validity_status IN ('active', 'superseded', 'contradicted', 'uncertain', 'archived')
          ),
          source_id TEXT REFERENCES memory_raw_sources(id),
          first_seen TEXT NOT NULL,
          last_confirmed TEXT,
          confidence REAL,
          expires_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_memory_facts_scope_status
          ON memory_facts(project_scope, validity_status, first_seen DESC);
        CREATE INDEX IF NOT EXISTS idx_memory_facts_source ON memory_facts(source_id);
        CREATE TABLE IF NOT EXISTS memory_relationships (
          id TEXT PRIMARY KEY,
          subject_id TEXT NOT NULL,
          predicate TEXT NOT NULL CHECK (
            predicate IN (
              'caused_by',
              'depends_on',
              'blocks',
              'supersedes',
              'contradicts',
              'supports',
              'evidence_for',
              'belongs_to_project',
              'decided_in',
              'implemented_by',
              'requested_by_user',
              'derived_from',
              'related_to',
              'has_open_question',
              'has_constraint',
              'has_risk',
              'has_owner',
              'has_status'
            )
          ),
          object_id TEXT NOT NULL,
          project_scope TEXT,
          confidence REAL DEFAULT 1.0,
          source_id TEXT REFERENCES memory_raw_sources(id),
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_relationships_subject
          ON memory_relationships(subject_id, predicate, object_id);
        CREATE INDEX IF NOT EXISTS idx_memory_relationships_object
          ON memory_relationships(object_id, predicate);
        CREATE TABLE IF NOT EXISTS memory_packet_receipts (
          id TEXT PRIMARY KEY,
          packet_id TEXT NOT NULL,
          compiled_at TEXT NOT NULL,
          source_ids TEXT,
          fact_ids TEXT,
          relationship_ids TEXT,
          token_count INTEGER,
          mode TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_memory_packet_receipts_packet
          ON memory_packet_receipts(packet_id, compiled_at DESC);
        """
    )


class RawSourceMemory:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_memory_layer_schema(conn)

    def insert(
        self,
        *,
        source_type: str,
        id: str | None = None,
        source_path: str | None = None,
        project_id: str | None = None,
        author: str | None = None,
        confidence: float | None = None,
        original_content: str | None = None,
        extraction_status: str = "pending",
    ) -> str:
        source_id = id or _new_id("raw")
        now = _now_iso()
        self.conn.execute(
            """
            INSERT INTO memory_raw_sources (
                id, source_type, source_path, project_id, author, confidence,
                original_content, extraction_status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                source_type,
                source_path,
                project_id,
                author,
                confidence,
                original_content,
                extraction_status,
                now,
                now,
            ),
        )
        self.conn.commit()
        return source_id

    def get(self, source_id: str) -> RowDict | None:
        return _fetch_one(self.conn, "SELECT * FROM memory_raw_sources WHERE id = ?", (source_id,))

    def query(
        self,
        *,
        source_type: str | None = None,
        project_id: str | None = None,
        extraction_status: str | None = None,
        limit: int = 50,
    ) -> list[RowDict]:
        where_sql, params = _where_clause(
            [
                ("source_type", source_type),
                ("project_id", project_id),
                ("extraction_status", extraction_status),
            ]
        )
        return _fetch_all(
            self.conn,
            f"SELECT * FROM memory_raw_sources{where_sql} ORDER BY updated_at DESC LIMIT ?",
            (*params, limit),
        )


class FactMemory:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_memory_layer_schema(conn)

    def insert(
        self,
        *,
        fact_text: str,
        id: str | None = None,
        entity: str | None = None,
        predicate: str | None = None,
        object_value: str | None = None,
        project_scope: str | None = None,
        validity_status: str = "active",
        source_id: str | None = None,
        first_seen: str | None = None,
        last_confirmed: str | None = None,
        confidence: float | None = None,
        expires_at: str | None = None,
    ) -> str:
        if validity_status not in VALIDITY_STATUSES:
            allowed = ", ".join(sorted(VALIDITY_STATUSES))
            raise ValueError(
                f"Unsupported memory fact validity_status '{validity_status}'. Use: {allowed}."
            )
        fact_id = id or _new_id("fact")
        self.conn.execute(
            """
            INSERT INTO memory_facts (
                id, fact_text, entity, predicate, object_value, project_scope,
                validity_status, source_id, first_seen, last_confirmed, confidence, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                fact_text,
                entity,
                predicate,
                object_value,
                project_scope,
                validity_status,
                source_id,
                first_seen or _now_iso(),
                last_confirmed,
                confidence,
                expires_at,
            ),
        )
        self.conn.commit()
        return fact_id

    def get(self, fact_id: str) -> RowDict | None:
        return _fetch_one(self.conn, "SELECT * FROM memory_facts WHERE id = ?", (fact_id,))

    def query(
        self,
        *,
        project_scope: str | None = None,
        validity_status: str | None = None,
        entity: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> list[RowDict]:
        where_sql, params = _where_clause(
            [
                ("project_scope", project_scope),
                ("validity_status", validity_status),
                ("entity", entity),
                ("source_id", source_id),
            ]
        )
        return _fetch_all(
            self.conn,
            f"SELECT * FROM memory_facts{where_sql} ORDER BY first_seen DESC LIMIT ?",
            (*params, limit),
        )


class RelationshipMemory:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_memory_layer_schema(conn)

    def insert(
        self,
        *,
        subject_id: str,
        predicate: str,
        object_id: str,
        id: str | None = None,
        project_scope: str | None = None,
        confidence: float = 1.0,
        source_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        if predicate not in ALLOWED_PREDICATES:
            allowed = ", ".join(sorted(ALLOWED_PREDICATES))
            raise ValueError(
                f"Unsupported memory relationship predicate '{predicate}'. Use: {allowed}."
            )
        relationship_id = id or _new_id("rel")
        self.conn.execute(
            """
            INSERT INTO memory_relationships (
                id, subject_id, predicate, object_id, project_scope, confidence, source_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relationship_id,
                subject_id,
                predicate,
                object_id,
                project_scope,
                confidence,
                source_id,
                created_at or _now_iso(),
            ),
        )
        self.conn.commit()
        return relationship_id

    def get(self, relationship_id: str) -> RowDict | None:
        return _fetch_one(
            self.conn,
            "SELECT * FROM memory_relationships WHERE id = ?",
            (relationship_id,),
        )

    def query(
        self,
        *,
        subject_id: str | None = None,
        predicate: str | None = None,
        object_id: str | None = None,
        project_scope: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> list[RowDict]:
        where_sql, params = _where_clause(
            [
                ("subject_id", subject_id),
                ("predicate", predicate),
                ("object_id", object_id),
                ("project_scope", project_scope),
                ("source_id", source_id),
            ]
        )
        return _fetch_all(
            self.conn,
            f"SELECT * FROM memory_relationships{where_sql} ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        )


class PacketReceiptLog:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        ensure_memory_layer_schema(conn)

    def insert(
        self,
        *,
        packet_id: str,
        id: str | None = None,
        compiled_at: str | None = None,
        source_ids: Sequence[str] | None = None,
        fact_ids: Sequence[str] | None = None,
        relationship_ids: Sequence[str] | None = None,
        token_count: int | None = None,
        mode: str | None = None,
    ) -> str:
        receipt_id = id or _new_id("receipt")
        self.conn.execute(
            """
            INSERT INTO memory_packet_receipts (
                id, packet_id, compiled_at, source_ids, fact_ids,
                relationship_ids, token_count, mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                packet_id,
                compiled_at or _now_iso(),
                _json_list(source_ids),
                _json_list(fact_ids),
                _json_list(relationship_ids),
                token_count,
                mode,
            ),
        )
        self.conn.commit()
        return receipt_id

    def get(self, receipt_id: str) -> RowDict | None:
        return _decoded_receipt(
            _fetch_one(
                self.conn, "SELECT * FROM memory_packet_receipts WHERE id = ?", (receipt_id,)
            )
        )

    def query(
        self,
        *,
        packet_id: str | None = None,
        mode: str | None = None,
        limit: int = 50,
    ) -> list[RowDict]:
        where_sql, params = _where_clause([("packet_id", packet_id), ("mode", mode)])
        rows = _fetch_all(
            self.conn,
            f"SELECT * FROM memory_packet_receipts{where_sql} ORDER BY compiled_at DESC LIMIT ?",
            (*params, limit),
        )
        return [decoded for row in rows if (decoded := _decoded_receipt(row)) is not None]
