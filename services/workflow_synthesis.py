from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_REGISTRY = REPO_ROOT / "config" / "workflows" / "registry.json"
DEFAULT_SKILL_REGISTRY = REPO_ROOT / "config" / "workflows" / "skills.json"
WORKFLOW_SIGNAL_WEIGHTS = {
    "workflow": 3,
    "playbook": 3,
    "protocol": 3,
    "checklist": 2,
    "steps": 2,
    "pipeline": 2,
    "quality gate": 2,
    "validation": 2,
    "acceptance": 2,
    "agent": 2,
    "pattern": 2,
    "repeat": 2,
    "recurring": 2,
    "template": 1,
    "runbook": 3,
    "taski": 2,
    "aios": 2,
}
VAULT_SKIP_PARTS = {".git", ".obsidian", ".trash"}
VAULT_SKIP_PREFIXES = {
    ("Personal-Corpus", "Calendar"),
    ("02 AI OS", "02 Session Handoffs"),
    ("09 Archive", "AI History", "ChatGPT"),
    ("09 Archive", "AI History", "Claude"),
    ("09 Archive", "AI History", "Claude Code"),
    ("09 Archive", "AI History", "Codex"),
}


class WorkflowProposal(TypedDict):
    id: str
    proposal_key: str
    title: str
    summary: str
    status: str
    source_pattern_ids: list[str]
    workflow_spec: dict[str, Any]
    skill_specs: list[dict[str, Any]]
    validation_plan: dict[str, Any]
    evidence: list[str]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def ensure_workflow_synthesis_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_synthesis_proposals (
          id TEXT PRIMARY KEY,
          proposal_key TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          source_pattern_ids_json TEXT NOT NULL DEFAULT '[]',
          workflow_spec_json TEXT NOT NULL DEFAULT '{}',
          skill_specs_json TEXT NOT NULL DEFAULT '[]',
          validation_plan_json TEXT NOT NULL DEFAULT '{}',
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'pending_approval',
          reviewer TEXT,
          review_note TEXT,
          reviewed_at TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_synthesis_proposals_status
          ON workflow_synthesis_proposals(status, created_at DESC)
        """
    )


def _slugify(value: str) -> str:
    cleaned = re.sub(r"^Recurring [^:]+:\s*", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned.lower()).strip("_")
    return cleaned[:56].strip("_") or "learned_workflow"


def _proposal_key(title: str) -> str:
    slug = _slugify(title)
    if slug.endswith("_v1"):
        return slug
    return f"{slug}_v1"


def _skill_key(proposal_key: str) -> str:
    return f"{proposal_key}_executor"


def _workflow_spec(proposal_key: str, title: str, evidence: list[str]) -> dict[str, Any]:
    readable = title.replace("Recurring workflow pattern:", "").replace("Recurring prompt pattern:", "").strip()
    return {
        "key": proposal_key,
        "name": readable[:80].title(),
        "purpose": f"Reusable workflow synthesized from repeated AIOS pattern evidence: {readable}.",
        "trigger_hints": [readable, title],
        "output_contract": [
            "normalized objective",
            "bounded execution plan",
            "evidence-backed result",
            "validation summary",
        ],
        "required_validations": ["scope_check"],
        "stages": [
            {"key": "parse_request", "kind": "parse_request", "required_skills": []},
            {"key": "normalize_prompt", "kind": "normalize_prompt", "required_skills": ["prompt_library_normalizer"]},
            {"key": "execute_pattern", "kind": "generate", "required_skills": [_skill_key(proposal_key)]},
            {"key": "validate", "kind": "validate", "required_skills": ["scope_check"]},
            {"key": "finalize", "kind": "finalize", "required_skills": []},
        ],
        "synthesis_metadata": {
            "source": "workflow_synthesis",
            "evidence_count": len(evidence),
        },
    }


def _skill_spec(proposal_key: str, title: str) -> dict[str, Any]:
    return {
        "key": _skill_key(proposal_key),
        "purpose": f"Execute the learned pattern captured by: {title}.",
        "allowed_stages": ["generate"],
        "input_schema": {
            "objective": "string",
            "normalized_prompt": "string",
        },
        "output_schema": {
            "result_text": "string",
            "evidence": "string[]",
        },
        "invariants": [
            "Preserve user intent.",
            "Use the learned pattern only when trigger evidence matches.",
            "Return explicit evidence for why the workflow applied.",
        ],
        "failure_conditions": [
            "No trigger overlap with source pattern.",
            "Output cannot be validated by scope_check.",
        ],
        "side_effects": [],
        "execution_mode": "heuristic",
    }


def _validation_plan(proposal_key: str, evidence: list[str]) -> dict[str, Any]:
    return {
        "proposal_key": proposal_key,
        "acceptance_checks": [
            "Workflow registry validates against skill registry.",
            "scope_check passes on generated output.",
            "At least one source evidence item is represented in trigger hints.",
        ],
        "seed_evidence": evidence[:8],
    }


def _proposal_from_row(row: sqlite3.Row | tuple[Any, ...]) -> WorkflowProposal:
    if isinstance(row, sqlite3.Row):
        values = row
        get = values.__getitem__
    else:
        columns = [
            "id",
            "proposal_key",
            "title",
            "summary",
            "source_pattern_ids_json",
            "workflow_spec_json",
            "skill_specs_json",
            "validation_plan_json",
            "evidence_json",
            "status",
        ]
        data = dict(zip(columns, row, strict=False))
        get = data.__getitem__
    return {
        "id": str(get("id")),
        "proposal_key": str(get("proposal_key")),
        "title": str(get("title")),
        "summary": str(get("summary")),
        "source_pattern_ids": _parse_json_list(str(get("source_pattern_ids_json"))),
        "workflow_spec": json.loads(str(get("workflow_spec_json"))),
        "skill_specs": json.loads(str(get("skill_specs_json"))),
        "validation_plan": json.loads(str(get("validation_plan_json"))),
        "evidence": _parse_json_list(str(get("evidence_json"))),
        "status": str(get("status")),
    }


def _eligible_patterns(conn: sqlite3.Connection, min_confidence: float, limit: int) -> list[dict[str, Any]]:
    if not _table_exists(conn, "patterns"):
        return []
    rows = conn.execute(
        """
        SELECT id, class, title, evidence, confidence, domain, state, status, human_approved
        FROM patterns
        WHERE class IN ('workflow', 'prompt')
          AND COALESCE(status, '') != 'discarded'
          AND confidence >= ?
        ORDER BY human_approved DESC, confidence DESC, created_at DESC
        LIMIT ?
        """,
        (min_confidence, limit),
    ).fetchall()
    return [
        {
            "id": str(row[0]),
            "class": str(row[1]),
            "title": str(row[2]),
            "evidence": _parse_json_list(row[3]),
            "confidence": float(row[4]),
            "domain": row[5],
            "state": row[6],
            "status": row[7],
            "human_approved": bool(row[8]),
        }
        for row in rows
    ]


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :].lstrip()


def _markdown_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip() or path.stem
    return path.stem.replace("-", " ").replace("_", " ").strip() or "Vault workflow"


def _path_is_skipped(path: Path, vault_root: Path) -> bool:
    try:
        relative = path.relative_to(vault_root)
    except ValueError:
        relative = path
    parts = relative.parts
    if path.name.startswith("."):
        return True
    if any(part in VAULT_SKIP_PARTS for part in parts):
        return True
    return any(parts[: len(prefix)] == prefix for prefix in VAULT_SKIP_PREFIXES)


def _vault_signal_score(title: str, text: str) -> int:
    haystack = f"{title}\n{text}".lower()
    score = 0
    for term, weight in WORKFLOW_SIGNAL_WEIGHTS.items():
        occurrences = haystack.count(term)
        if occurrences:
            score += min(occurrences, 4) * weight
    heading_or_list_lines = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("#", "- ", "* ", "1. ", "2. ", "3. ")):
            heading_or_list_lines += 1
    return score + min(heading_or_list_lines, 8)


def _vault_evidence(path: Path, vault_root: Path, text: str) -> list[str]:
    relative = str(path.relative_to(vault_root))
    evidence = [f"vault:{relative}"]
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line.strip())
        if not stripped:
            continue
        lower = stripped.lower()
        if stripped.startswith("#") or any(term in lower for term in WORKFLOW_SIGNAL_WEIGHTS):
            evidence.append(f"{relative}: {stripped[:220]}")
        if len(evidence) >= 8:
            break
    return evidence


def _vault_candidates(vault_root: Path, min_confidence: float, limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not vault_root.is_dir():
        return []
    candidates: list[dict[str, Any]] = []
    for path in sorted(vault_root.rglob("*.md")):
        if _path_is_skipped(path, vault_root):
            continue
        try:
            if path.stat().st_size > 350_000:
                continue
            text = _strip_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        title = _markdown_title(path, text)
        score = _vault_signal_score(title, text)
        confidence = min(0.96, 0.58 + (score * 0.025))
        if confidence < min_confidence:
            continue
        relative = str(path.relative_to(vault_root))
        candidates.append(
            {
                "id": f"vault:{relative}",
                "class": "vault_workflow",
                "title": f"Vault workflow candidate: {title}",
                "evidence": _vault_evidence(path, vault_root, text),
                "confidence": confidence,
                "score": score,
                "relative_path": relative,
            }
        )
    candidates.sort(key=lambda item: (-float(item["confidence"]), str(item["relative_path"])))
    return candidates[:limit]


def _insert_synthesis_proposal(
    conn: sqlite3.Connection,
    *,
    proposal_key: str,
    title: str,
    summary: str,
    source_ids: list[str],
    evidence: list[str],
) -> WorkflowProposal | None:
    existing = conn.execute(
        "SELECT id FROM workflow_synthesis_proposals WHERE proposal_key = ? LIMIT 1",
        (proposal_key,),
    ).fetchone()
    if existing:
        return None
    workflow_spec = _workflow_spec(proposal_key, title, evidence)
    skill_specs = [_skill_spec(proposal_key, title)]
    validation_plan = _validation_plan(proposal_key, evidence)
    proposal_id = f"workflow-proposal-{uuid.uuid4()}"
    timestamp = _now_iso()
    conn.execute(
        """
        INSERT INTO workflow_synthesis_proposals (
          id, proposal_key, title, summary, source_pattern_ids_json, workflow_spec_json,
          skill_specs_json, validation_plan_json, evidence_json, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?, ?)
        """,
        (
            proposal_id,
            proposal_key,
            f"Workflow synthesis proposal: {workflow_spec['name']}",
            summary,
            _json(source_ids),
            _json(workflow_spec),
            _json(skill_specs),
            _json(validation_plan),
            _json(evidence),
            timestamp,
            timestamp,
        ),
    )
    row = conn.execute(
        """
        SELECT id, proposal_key, title, summary, source_pattern_ids_json, workflow_spec_json,
               skill_specs_json, validation_plan_json, evidence_json, status
        FROM workflow_synthesis_proposals
        WHERE id = ?
        """,
        (proposal_id,),
    ).fetchone()
    return _proposal_from_row(row)


def _insert_writeback(conn: sqlite3.Connection, proposal: WorkflowProposal) -> None:
    if not _table_exists(conn, "improvement_writebacks"):
        return
    existing = conn.execute(
        """
        SELECT 1 FROM improvement_writebacks
        WHERE layer_type = 'workflow' AND layer_key = ?
        LIMIT 1
        """,
        (proposal["proposal_key"],),
    ).fetchone()
    if existing:
        return
    timestamp = _now_iso()
    writeback_id = f"writeback-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary, evidence_json,
          proposed_change_json, impact_scope, status, requires_approval, approval_reason,
          token_regressive, created_at, updated_at
        )
        VALUES (?, NULL, NULL, 'workflow', ?, ?, ?, ?, ?, 'workflow-default', 'pending_approval', 1, ?, 0, ?, ?)
        """,
        (
            writeback_id,
            proposal["proposal_key"],
            proposal["title"],
            proposal["summary"],
            _json(proposal["evidence"]),
            _json(
                {
                    "source": "workflow_synthesis",
                    "proposal_id": proposal["id"],
                    "workflow_spec": proposal["workflow_spec"],
                    "skill_specs": proposal["skill_specs"],
                    "validation_plan": proposal["validation_plan"],
                }
            ),
            "Synthesized workflows must be reviewed before registry mutation.",
            timestamp,
            timestamp,
        ),
    )


def synthesize_workflow_proposals(
    conn: sqlite3.Connection,
    *,
    min_confidence: float = 0.75,
    limit: int = 20,
    vault_root: Path | None = None,
    queue_writebacks: bool = True,
) -> list[WorkflowProposal]:
    ensure_workflow_synthesis_schema(conn)
    proposals: list[WorkflowProposal] = []
    for pattern in _eligible_patterns(conn, min_confidence, limit):
        proposal_key = _proposal_key(pattern["title"])
        evidence = pattern["evidence"] or [pattern["title"]]
        summary = (
            f"Synthesized from {pattern['class']} pattern with confidence "
            f"{pattern['confidence']:.2f}; review before adding to workflow registry."
        )
        proposal = _insert_synthesis_proposal(
            conn,
            proposal_key=proposal_key,
            title=pattern["title"],
            summary=summary,
            source_ids=[pattern["id"]],
            evidence=evidence,
        )
        if proposal is None:
            continue
        if queue_writebacks:
            _insert_writeback(conn, proposal)
        proposals.append(proposal)

    remaining = max(0, limit - len(proposals))
    if vault_root is not None and remaining:
        for candidate in _vault_candidates(vault_root, min_confidence, remaining):
            source_key = f"{candidate['title']} {candidate['relative_path']}"
            proposal_key = _proposal_key(source_key)
            summary = (
                f"Backfilled from Obsidian vault note {candidate['relative_path']} "
                f"with workflow signal confidence {candidate['confidence']:.2f}; review before registry mutation."
            )
            proposal = _insert_synthesis_proposal(
                conn,
                proposal_key=proposal_key,
                title=candidate["title"],
                summary=summary,
                source_ids=[candidate["id"]],
                evidence=candidate["evidence"],
            )
            if proposal is None:
                continue
            if queue_writebacks:
                _insert_writeback(conn, proposal)
            proposals.append(proposal)
    return proposals


def _load_json_object(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return loaded


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def approve_workflow_proposal(
    conn: sqlite3.Connection,
    *,
    proposal_id: str,
    actor: str,
    registry_path: Path = DEFAULT_WORKFLOW_REGISTRY,
    skills_path: Path = DEFAULT_SKILL_REGISTRY,
    note: str | None = None,
) -> WorkflowProposal:
    ensure_workflow_synthesis_schema(conn)
    row = conn.execute(
        """
        SELECT id, proposal_key, title, summary, source_pattern_ids_json, workflow_spec_json,
               skill_specs_json, validation_plan_json, evidence_json, status
        FROM workflow_synthesis_proposals
        WHERE id = ?
        LIMIT 1
        """,
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Workflow synthesis proposal not found: {proposal_id}")
    proposal = _proposal_from_row(row)
    if proposal["status"] == "approved":
        return proposal

    workflow_registry = _load_json_object(registry_path, {"version": "generated", "stage_kinds": [], "workflows": []})
    skill_registry = _load_json_object(skills_path, {"version": "generated", "skills": []})
    workflows = workflow_registry.setdefault("workflows", [])
    skills = skill_registry.setdefault("skills", [])
    if not isinstance(workflows, list) or not isinstance(skills, list):
        raise ValueError("Workflow and skill registries must contain list fields.")

    if not any(isinstance(item, dict) and item.get("key") == proposal["proposal_key"] for item in workflows):
        workflows.append(proposal["workflow_spec"])
    existing_skill_keys = {item.get("key") for item in skills if isinstance(item, dict)}
    for skill in proposal["skill_specs"]:
        if skill["key"] not in existing_skill_keys:
            skills.append(skill)
            existing_skill_keys.add(skill["key"])

    _write_json(registry_path, workflow_registry)
    _write_json(skills_path, skill_registry)

    reviewed_at = _now_iso()
    conn.execute(
        """
        UPDATE workflow_synthesis_proposals
        SET status = 'approved',
            reviewer = ?,
            review_note = ?,
            reviewed_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (actor, note, reviewed_at, reviewed_at, proposal_id),
    )
    proposal["status"] = "approved"
    return proposal
