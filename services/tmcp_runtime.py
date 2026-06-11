from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_LIBRARY = ROOT / "skills-library"
TMCP_PACKET_SCHEMA = "tmcp-runtime-packet-v0.1"
TMCP_RECEIPT_SCHEMA = "tmcp-traversal-receipt-v0.3"

TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "audit": ("audit", "review", "inspect", "evaluate"),
    "implementation": ("implement", "edit", "patch", "fix", "refactor", "build"),
    "planning": ("plan", "roadmap", "phase", "acceptance"),
    "research": ("research", "investigate", "source", "citation"),
    "debugging": ("debug", "bug", "root cause", "failure"),
    "testing": ("test", "verify", "validate", "quality gate"),
    "documentation": ("document", "readme", "docs", "writeback"),
    "agent_workflow": ("agent", "workflow", "routing", "skill", "prompt", "tmcp", "gsd"),
}
TASK_PRIORITY = (
    "implementation",
    "debugging",
    "audit",
    "planning",
    "research",
    "testing",
    "documentation",
    "agent_workflow",
)

DEFAULT_MODULES = (
    "context_gathering",
    "evidence_first",
    "provenance_policy",
    "output_contract",
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_tmcp_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tmcp_traversal_receipts (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES orchestration_runs(id),
            invocation_id TEXT REFERENCES orchestration_invocations(id),
            session_id TEXT REFERENCES sessions(id),
            project_path TEXT,
            task_id TEXT NOT NULL,
            traversal_fingerprint TEXT NOT NULL,
            packet_json TEXT NOT NULL,
            selected_nodes_json TEXT NOT NULL DEFAULT '[]',
            skipped_nodes_json TEXT NOT NULL DEFAULT '[]',
            token_estimates_json TEXT NOT NULL DEFAULT '{}',
            execution_outcome TEXT NOT NULL DEFAULT 'pending',
            validation_evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tmcp_traversal_receipts_run
          ON tmcp_traversal_receipts(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tmcp_traversal_receipts_fingerprint
          ON tmcp_traversal_receipts(traversal_fingerprint, created_at DESC)
        """
    )


def compile_tmcp_packet(
    *,
    objective: str,
    project_path: str | None = None,
    context_receipt_id: str | None = None,
    skills_library_path: Path | None = None,
) -> dict[str, Any]:
    library = skills_library_path or DEFAULT_SKILLS_LIBRARY
    tmcp_root = library / "skills.tmcp"
    objective_text = objective.strip()
    task_id = _select_task(objective_text)
    modules = _select_modules(objective_text, task_id, tmcp_root)
    branch_id = _select_branch(objective_text)
    selected_nodes = [f"@task:{task_id}", *(f"@module:{item}" for item in modules), f"@branch:{branch_id}"]
    skipped_nodes = _skipped_nodes(task_id, modules)
    shortcut = _shortcut_summary(tmcp_root)

    node_sections = [
        _node_excerpt("Router", tmcp_root / "router.md"),
        _node_excerpt(f"Task {task_id}", tmcp_root / "tasks" / f"{task_id}.md"),
        *(_node_excerpt(f"Module {module_id}", tmcp_root / "modules" / f"{module_id}.md") for module_id in modules),
        _node_excerpt(f"Branch {branch_id}", tmcp_root / "branches" / f"{branch_id}.branch.md"),
        shortcut,
    ]
    node_sections = [section for section in node_sections if section]
    packet_markdown = _packet_markdown(
        objective=objective_text,
        task_id=task_id,
        selected_nodes=selected_nodes,
        skipped_nodes=skipped_nodes,
        context_receipt_id=context_receipt_id,
        sections=node_sections,
    )
    token_estimates = {
        "custom_skill_tokens": _estimate_tokens(packet_markdown),
        "baseline_skill_tokens": _estimate_baseline_tokens(tmcp_root, task_id, packet_markdown),
    }
    token_estimates["estimated_token_delta"] = (
        token_estimates["baseline_skill_tokens"] - token_estimates["custom_skill_tokens"]
    )
    fingerprint = _fingerprint(
        task_id=task_id,
        selected_nodes=selected_nodes,
        project_scope=_project_scope(project_path),
    )
    status = "compiled" if tmcp_root.exists() else "fallback_missing_tmcp_library"

    return {
        "schema": TMCP_PACKET_SCHEMA,
        "receipt_schema": TMCP_RECEIPT_SCHEMA,
        "status": status,
        "task_id": task_id,
        "objective": objective_text,
        "project_path": project_path,
        "context_receipt_id": context_receipt_id,
        "entry_node": f"@task:{task_id}",
        "selected_nodes": selected_nodes,
        "skipped_nodes": skipped_nodes,
        "selected_branches": [{"branch": f"@branch:{branch_id}", "reason": _branch_reason(branch_id)}],
        "shortcut_candidate": {
            "node": "@shortcut:candidate",
            "matched": False,
            "reason": "Promoted shortcut lookup is not enabled yet; compile normal TMCP path.",
        },
        "transition_trace": _transition_trace(task_id, modules, branch_id),
        "traversal_fingerprint": fingerprint,
        "token_estimates": token_estimates,
        "packet_markdown": packet_markdown,
        "source": str(tmcp_root),
        "created_at": now_iso(),
    }


def persist_tmcp_traversal_receipt(
    conn: sqlite3.Connection,
    *,
    packet: dict[str, Any],
    run_id: str | None,
    invocation_id: str | None,
    session_id: str | None,
    execution_outcome: str = "pending",
    validation_evidence: list[str] | None = None,
) -> str:
    ensure_tmcp_schema(conn)
    receipt_id = f"tmcp-receipt-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO tmcp_traversal_receipts (
            id, run_id, invocation_id, session_id, project_path, task_id,
            traversal_fingerprint, packet_json, selected_nodes_json, skipped_nodes_json,
            token_estimates_json, execution_outcome, validation_evidence_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            receipt_id,
            run_id,
            invocation_id,
            session_id,
            packet.get("project_path"),
            str(packet.get("task_id", "agent_workflow")),
            str(packet.get("traversal_fingerprint", "")),
            json.dumps(packet, sort_keys=True),
            json.dumps(packet.get("selected_nodes", []), sort_keys=True),
            json.dumps(packet.get("skipped_nodes", []), sort_keys=True),
            json.dumps(packet.get("token_estimates", {}), sort_keys=True),
            execution_outcome,
            json.dumps(validation_evidence or [], sort_keys=True),
            now_iso(),
        ),
    )
    return receipt_id


def _select_task(objective: str) -> str:
    lowered = objective.lower()
    scores: dict[str, int] = {}
    for task_id, terms in TASK_KEYWORDS.items():
        scores[task_id] = sum(1 for term in terms if term in lowered)
    max_score = max(scores.values())
    if max_score <= 0:
        return "agent_workflow"
    for task_id in TASK_PRIORITY:
        if scores.get(task_id) == max_score:
            return task_id
    return "agent_workflow"


def _select_modules(objective: str, task_id: str, tmcp_root: Path) -> list[str]:
    lowered = objective.lower()
    modules = list(DEFAULT_MODULES)
    if task_id in {"implementation", "debugging", "testing"} or any(
        term in lowered for term in ("test", "verify", "validate")
    ):
        modules.append("test_gate")
    if any(term in lowered for term in ("tool", "command", "browser", "shell", "mcp")):
        modules.append("tool_use_policy")
    return [module_id for module_id in dict.fromkeys(modules) if _module_exists(tmcp_root, module_id)]


def _select_branch(objective: str) -> str:
    lowered = objective.lower()
    direct_terms = ("implement", "fix", "patch", "edit", "do this", "build", "wire")
    if any(term in lowered for term in direct_terms):
        return "direct_implementation"
    return "ambiguous_task_resolution"


def _skipped_nodes(task_id: str, modules: list[str]) -> list[dict[str, str]]:
    selected = {task_id, *modules}
    skipped: list[dict[str, str]] = []
    for candidate in ("research", "documentation", "testing"):
        if candidate not in selected and candidate != task_id:
            skipped.append({"node": f"@task:{candidate}", "reason": "Not required by objective classifier."})
    return skipped


def _shortcut_summary(tmcp_root: Path) -> str:
    shortcut = tmcp_root / "shortcuts" / "candidate.md"
    if not shortcut.exists():
        return ""
    return _node_excerpt("Shortcut candidate", shortcut, max_chars=1200)


def _node_excerpt(title: str, path: Path, *, max_chars: int = 1800) -> str:
    if not path.exists():
        return f"## {title}\n\nMissing TMCP node: `{path}`.\n"
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "\n...(truncated)"
    return f"## {title}\n\nSource: `{path}`\n\n{content}\n"


def _packet_markdown(
    *,
    objective: str,
    task_id: str,
    selected_nodes: list[str],
    skipped_nodes: list[dict[str, str]],
    context_receipt_id: str | None,
    sections: list[str],
) -> str:
    skipped_lines = [f"- {row['node']}: {row['reason']}" for row in skipped_nodes]
    receipt_line = context_receipt_id or "none"
    return "\n".join(
        [
            "# AIOS TMCP Custom Skill Packet",
            "",
            f"Objective: {objective}",
            f"Task: @task:{task_id}",
            f"Context receipt: {receipt_line}",
            "",
            "## Selected Nodes",
            *(f"- {node}" for node in selected_nodes),
            "",
            "## Skipped Plausible Nodes",
            *(skipped_lines or ["- none"]),
            "",
            "## Execution Instruction",
            "- Use this packet as the run-specific skill overlay before executing the workflow.",
            "- Preserve project/context compiler instructions when they are stricter than this packet.",
            "- Record validation evidence so this traversal can later be promoted, repaired, or demoted.",
            "",
            *sections,
        ]
    )


def _module_exists(tmcp_root: Path, module_id: str) -> bool:
    return (tmcp_root / "modules" / f"{module_id}.md").exists() or not tmcp_root.exists()


def _estimate_tokens(text: str) -> int:
    words = len(re.findall(r"\S+", text))
    return max(1, round(words * 1.33))


def _estimate_baseline_tokens(tmcp_root: Path, task_id: str, packet_markdown: str) -> int:
    task_path = tmcp_root / "tasks" / f"{task_id}.md"
    if task_path.exists():
        sibling_tokens = sum(
            _estimate_tokens(path.read_text(encoding="utf-8", errors="replace"))
            for path in sorted((tmcp_root / "tasks").glob("*.md"))
        )
        return max(_estimate_tokens(packet_markdown), sibling_tokens)
    return max(_estimate_tokens(packet_markdown) * 2, _estimate_tokens(packet_markdown) + 400)


def _fingerprint(*, task_id: str, selected_nodes: list[str], project_scope: str) -> str:
    payload = json.dumps(
        {
            "task_id": task_id,
            "selected_nodes": selected_nodes,
            "project_scope": project_scope,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _project_scope(project_path: str | None) -> str:
    if not project_path:
        return "unknown"
    return Path(project_path).name or "unknown"


def _branch_reason(branch_id: str) -> str:
    if branch_id == "direct_implementation":
        return "Objective contains direct implementation language."
    return "Objective did not clearly grant direct implementation; preserve ambiguity branch."


def _transition_trace(task_id: str, modules: list[str], branch_id: str) -> list[dict[str, str]]:
    trace = [
        {
            "from": "ROUTER.START",
            "to": f"@task:{task_id}",
            "action": "LOAD",
            "why": "Objective keyword classification selected the task node.",
        }
    ]
    previous = f"@task:{task_id}"
    for module_id in modules:
        trace.append(
            {
                "from": previous,
                "to": f"@module:{module_id}",
                "action": "USE",
                "why": "Module is part of the minimal managed-run TMCP overlay.",
            }
        )
        previous = f"@module:{module_id}"
    trace.append(
        {
            "from": previous,
            "to": f"@branch:{branch_id}",
            "action": "USE",
            "why": _branch_reason(branch_id),
        }
    )
    return trace
