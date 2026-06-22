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
DEFAULT_TMCP_REGISTRY = ROOT / "config" / "tmcp" / "registry.json"
TMCP_PACKET_SCHEMA = "tmcp-runtime-packet-v0.1"
TMCP_RECEIPT_SCHEMA = "tmcp-traversal-receipt-v0.3"
SHORTCUT_STATUSES = (
    "active",
    "stale_candidate",
    "needs_revalidation",
    "superseded",
    "deprecated",
    "conflict_branch",
)
SHORTCUT_REBUILD_OUTCOMES = (
    "revalidate_unchanged",
    "regenerate_new_version",
    "split_more_specific",
    "create_conflict_branches",
    "deprecate_not_useful",
)

TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "audit": ("audit", "review", "inspect", "evaluate"),
    "implementation": ("implement", "edit", "patch", "fix", "refactor", "build"),
    "planning": ("plan", "roadmap", "phase", "acceptance"),
    "research": ("research", "investigate", "source", "citation"),
    "debugging": ("debug", "bug", "root cause", "failure"),
    "testing": ("test", "verify", "validate", "quality gate"),
    "documentation": ("document", "readme", "docs", "writeback"),
    "agent_workflow": ("agent", "workflow", "routing", "skill", "prompt", "tmcp", "gsd"),
    "visual_polish": (
        "visual polish",
        "product ui polish",
        "enterprise saas",
        "dashboard polish",
        "ai ui",
        "realistic demo data",
        "generic shadcn",
    ),
}
TASK_PRIORITY = (
    "implementation",
    "debugging",
    "audit",
    "visual_polish",
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
    receipt_conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    library = skills_library_path or DEFAULT_SKILLS_LIBRARY
    tmcp_root = library / "skills.tmcp"
    objective_text = objective.strip()
    task_id = _select_task(objective_text)
    modules = _select_modules(objective_text, task_id, tmcp_root)
    branch_id = _select_branch(objective_text)
    registry_overlay = _select_registry_overlay(objective_text, task_id)
    router_selected_nodes = [
        f"@task:{task_id}",
        *(f"@module:{item}" for item in modules),
        f"@branch:{branch_id}",
        *registry_overlay["selected_nodes"],
    ]
    graph_version = _combined_graph_version(tmcp_root, registry_overlay["graph_paths"])
    fingerprint = _fingerprint(
        task_id=task_id,
        selected_nodes=router_selected_nodes,
        project_scope=_project_scope(project_path),
    )
    skipped_nodes = _skipped_nodes(task_id, modules)
    shortcut = _shortcut_summary(tmcp_root)
    shortcut_candidate = _shortcut_candidate(
        tmcp_root=tmcp_root,
        task_id=task_id,
        graph_version=graph_version,
        fingerprint=fingerprint,
        receipt_conn=receipt_conn,
    )
    selected_nodes = router_selected_nodes
    entry_node = f"@task:{task_id}"
    if shortcut_candidate["matched"] and shortcut_candidate["usable_as_default"]:
        entry_node = str(shortcut_candidate["node"])
        selected_nodes = [entry_node, *router_selected_nodes]

    node_sections = [
        _node_excerpt("Router", tmcp_root / "router.md"),
        _optional_node_excerpt(f"Task {task_id}", tmcp_root / "tasks" / f"{task_id}.md"),
        *(_node_excerpt(f"Module {module_id}", tmcp_root / "modules" / f"{module_id}.md") for module_id in modules),
        _optional_node_excerpt(f"Branch {branch_id}", tmcp_root / "branches" / f"{branch_id}.branch.md"),
        *registry_overlay["sections"],
        shortcut,
    ]
    node_sections = [section for section in node_sections if section]
    packet_markdown = _packet_markdown(
        objective=objective_text,
        task_id=task_id,
        selected_nodes=selected_nodes,
        skipped_nodes=skipped_nodes,
        context_receipt_id=context_receipt_id,
        shortcut_candidate=shortcut_candidate,
        sections=node_sections,
    )
    token_estimates = {
        "custom_skill_tokens": _estimate_tokens(packet_markdown),
        "baseline_skill_tokens": _estimate_baseline_tokens(tmcp_root, task_id, packet_markdown),
    }
    token_estimates["estimated_token_delta"] = (
        token_estimates["baseline_skill_tokens"] - token_estimates["custom_skill_tokens"]
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
        "source_graph_version": graph_version,
        "entry_node": entry_node,
        "selected_nodes": selected_nodes,
        "skipped_nodes": skipped_nodes,
        "selected_branches": [{"branch": f"@branch:{branch_id}", "reason": _branch_reason(branch_id)}],
        "registry_overlay": registry_overlay["metadata"],
        "shortcut_candidate": shortcut_candidate,
        "shortcut_governance": {
            "allowed_statuses": list(SHORTCUT_STATUSES),
            "rebuild_outcomes": list(SHORTCUT_REBUILD_OUTCOMES),
            "default_fallback": "router_traversal",
            "generated_artifact_not_source_of_truth": True,
            "requires_behavioral_tests_for_default": True,
        },
        "transition_trace": _transition_trace(task_id, modules, branch_id, shortcut_candidate),
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


def update_tmcp_traversal_receipt_outcome(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    execution_outcome: str,
    validation_evidence: list[str] | None = None,
) -> None:
    ensure_tmcp_schema(conn)
    conn.execute(
        """
        UPDATE tmcp_traversal_receipts
        SET execution_outcome = ?,
            validation_evidence_json = ?
        WHERE id = ?
        """,
        (
            execution_outcome,
            json.dumps(validation_evidence or [], sort_keys=True),
            receipt_id,
        ),
    )


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
    if task_id == "visual_polish":
        modules.extend(("visual_polish_system", "enterprise_saas_visual_polish", "data_realism_polish"))
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


def _shortcut_candidate(
    *,
    tmcp_root: Path,
    task_id: str,
    graph_version: str,
    fingerprint: str,
    receipt_conn: sqlite3.Connection | None,
) -> dict[str, Any]:
    candidate_path = tmcp_root / "shortcuts" / "candidate.md"
    promoted = _promoted_shortcut_from_receipts(
        receipt_conn=receipt_conn,
        task_id=task_id,
        graph_version=graph_version,
        fingerprint=fingerprint,
    )
    if promoted is not None:
        return promoted
    return {
        "node": "@shortcut:candidate",
        "matched": False,
        "status": "needs_revalidation" if candidate_path.exists() else "stale_candidate",
        "usable_as_default": False,
        "freshness": "uncertain",
        "source_graph_version": graph_version,
        "source_tasks": [f"@task:{task_id}"],
        "source_modules": [],
        "source_branches": [],
        "source_skills": [],
        "fallback": "router_traversal",
        "reason": "No valid active shortcut with current graph version and confirmed unchanged source material was found.",
        "repair_recommendation": "Use router traversal and evaluate whether this path should revalidate, regenerate, split, branch, or deprecate an existing shortcut.",
    }


def _promoted_shortcut_from_receipts(
    *,
    receipt_conn: sqlite3.Connection | None,
    task_id: str,
    graph_version: str,
    fingerprint: str,
) -> dict[str, Any] | None:
    if receipt_conn is None:
        return None
    ensure_tmcp_schema(receipt_conn)
    rows = receipt_conn.execute(
        """
        SELECT id, packet_json, token_estimates_json, execution_outcome, validation_evidence_json
        FROM tmcp_traversal_receipts
        WHERE traversal_fingerprint = ?
        ORDER BY created_at DESC
        """,
        (fingerprint,),
    ).fetchall()
    if len(rows) < 3:
        return None

    qualifying: list[dict[str, Any]] = []
    for row in rows:
        packet = _json_object(row[1])
        if packet.get("task_id") != task_id:
            continue
        if packet.get("source_graph_version") != graph_version:
            continue
        evidence = _json_list(row[4])
        selected_nodes = _json_list(packet.get("selected_nodes"))
        if _has_unresolved_shortcut_blocker(evidence, selected_nodes):
            continue
        token_estimates = _json_object(row[2]) or _json_object(packet.get("token_estimates"))
        qualifying.append(
            {
                "id": row[0],
                "outcome": str(row[3]),
                "positive_token_roi": int(token_estimates.get("estimated_token_delta", 0)) > 0,
            }
        )

    if len(qualifying) < 3:
        return None
    successful = [row for row in qualifying if row["outcome"] in {"completed", "pass", "passed", "success"}]
    success_rate = len(successful) / len(qualifying)
    positive_roi_count = sum(1 for row in successful if row["positive_token_roi"])
    if len(successful) < 3 or success_rate < 0.8 or positive_roi_count < 2:
        return None

    shortcut_node = f"@shortcut:{task_id}:{fingerprint[:12]}"
    return {
        "node": shortcut_node,
        "matched": True,
        "status": "active",
        "usable_as_default": True,
        "freshness": "confirmed",
        "source_graph_version": graph_version,
        "source_tasks": [f"@task:{task_id}"],
        "source_modules": [],
        "source_branches": [],
        "source_skills": [],
        "fallback": "router_traversal",
        "reason": "Persisted TMCP traversal receipts meet promotion thresholds for this fingerprint.",
        "evidence_receipt_ids": [row["id"] for row in successful[:3]],
        "promotion_stats": {
            "use_count": len(qualifying),
            "successful_count": len(successful),
            "validation_success_rate": round(success_rate, 3),
            "positive_token_roi_count": positive_roi_count,
            "missed_requirement_count": 0,
        },
    }


def _json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _has_unresolved_shortcut_blocker(evidence: list[Any], selected_nodes: list[Any]) -> bool:
    evidence_text = json.dumps(evidence, sort_keys=True).lower()
    if "missed_requirement" in evidence_text or "unresolved_repair" in evidence_text:
        return True
    return any(isinstance(node, str) and "conflict_branch" in node for node in selected_nodes)


def _node_excerpt(title: str, path: Path, *, max_chars: int = 1800) -> str:
    if not path.exists():
        return f"## {title}\n\nMissing TMCP node: `{path}`.\n"
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "\n...(truncated)"
    return f"## {title}\n\nSource: `{path}`\n\n{content}\n"


def _optional_node_excerpt(title: str, path: Path, *, max_chars: int = 1800) -> str:
    if not path.exists():
        return ""
    return _node_excerpt(title, path, max_chars=max_chars)


def _packet_markdown(
    *,
    objective: str,
    task_id: str,
    selected_nodes: list[str],
    skipped_nodes: list[dict[str, str]],
    context_receipt_id: str | None,
    shortcut_candidate: dict[str, Any],
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
            "## Shortcut Freshness",
            f"- Candidate: {shortcut_candidate['node']}",
            f"- Status: {shortcut_candidate['status']}",
            f"- Source graph version: {shortcut_candidate['source_graph_version']}",
            f"- Default usable: {shortcut_candidate['usable_as_default']}",
            f"- Fallback: {shortcut_candidate['fallback']}",
            f"- Reason: {shortcut_candidate['reason']}",
            "",
            "## Execution Instruction",
            "- Use this packet as the run-specific skill overlay before executing the workflow.",
            "- Preserve project/context compiler instructions when they are stricter than this packet.",
            "- Record validation evidence so this traversal can later be promoted, repaired, or demoted.",
            "- If shortcut freshness is uncertain, continue with router traversal.",
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


def _graph_version(tmcp_root: Path) -> str:
    if not tmcp_root.exists():
        return "missing"
    digest = hashlib.sha256()
    for path in sorted(tmcp_root.rglob("*.md")):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        digest.update(path.relative_to(tmcp_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _combined_graph_version(tmcp_root: Path, extra_paths: list[Path]) -> str:
    digest = hashlib.sha256()
    digest.update(_graph_version(tmcp_root).encode("utf-8"))
    for root in sorted(extra_paths):
        digest.update(str(root).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_graph_version(root).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _select_registry_overlay(objective: str, task_id: str) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "selected_nodes": [],
        "sections": [],
        "graph_paths": [],
        "metadata": {
            "schema": "tmcp-registry-overlay-v0.1",
            "matched": False,
            "namespaces": [],
            "skipped_namespaces": [],
        },
    }
    if not DEFAULT_TMCP_REGISTRY.exists():
        return empty

    try:
        registry = json.loads(DEFAULT_TMCP_REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            **empty,
            "metadata": {
                **empty["metadata"],
                "registry_error": f"Invalid JSON in {DEFAULT_TMCP_REGISTRY}",
            },
        }

    namespaces = registry.get("namespaces")
    if not isinstance(namespaces, dict):
        return empty

    selected_nodes: list[str] = []
    sections: list[str] = []
    graph_paths: list[Path] = []
    selected_namespaces: list[dict[str, Any]] = []
    skipped_namespaces: list[dict[str, str]] = []

    for namespace_id, raw_namespace in namespaces.items():
        if not isinstance(namespace_id, str) or not isinstance(raw_namespace, dict):
            continue
        manifest_path = ROOT / "config" / "tmcp" / str(raw_namespace.get("manifest", ""))
        namespace_root = ROOT / "config" / "tmcp" / str(raw_namespace.get("path", ""))
        manifest = _json_file(manifest_path)
        route = _select_manifest_task(objective, task_id, manifest)
        if route is None:
            skipped_namespaces.append(
                {
                    "namespace": namespace_id,
                    "reason": "No manifest task trigger changed behavior for this objective.",
                }
            )
            continue

        graph_paths.append(namespace_root)
        task_id_from_manifest = route["task_id"]
        required_modules = route["modules"]
        optional_nodes = route["optional"]
        branch_id = route.get("branch_id")
        prefix = f"@namespace:{namespace_id}"

        selected_nodes.append(f"{prefix}/@task:{task_id_from_manifest}")
        selected_nodes.extend(f"{prefix}/@module:{module}" for module in required_modules)
        if branch_id:
            selected_nodes.append(f"{prefix}/@branch:{branch_id}")

        sections.append(
            _node_excerpt(
                f"Namespace {namespace_id} router",
                ROOT / "config" / "tmcp" / str(raw_namespace.get("router", "")),
                max_chars=1200,
            )
        )
        sections.append(
            _node_excerpt(
                f"Namespace {namespace_id} task {task_id_from_manifest}",
                namespace_root / "tasks" / f"{task_id_from_manifest}.md",
            )
        )
        for module_id in required_modules:
            sections.append(
                _node_excerpt(
                    f"Namespace {namespace_id} module {module_id}",
                    namespace_root / "modules" / f"{module_id}.md",
                )
            )
        if branch_id:
            sections.append(
                _node_excerpt(
                    f"Namespace {namespace_id} branch {branch_id}",
                    namespace_root / "branches" / f"{branch_id}.branch.md",
                )
            )

        selected_namespaces.append(
            {
                "namespace": namespace_id,
                "task": task_id_from_manifest,
                "modules": required_modules,
                "optional_nodes": optional_nodes,
                "selected_branch": branch_id,
                "portable": bool(raw_namespace.get("portable", False)),
                "requires_aios_runtime": bool(raw_namespace.get("requires_aios_runtime", True)),
                "reason": route["reason"],
            }
        )

    return {
        "selected_nodes": selected_nodes,
        "sections": [section for section in sections if section],
        "graph_paths": graph_paths,
        "metadata": {
            "schema": "tmcp-registry-overlay-v0.1",
            "matched": bool(selected_namespaces),
            "registry": str(DEFAULT_TMCP_REGISTRY),
            "namespaces": selected_namespaces,
            "skipped_namespaces": skipped_namespaces,
            "entry_policy": registry.get("entry_policy"),
        },
    }


def _json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _select_manifest_task(objective: str, task_id: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    tasks = _json_object(_json_object(manifest.get("nodes")).get("tasks"))
    lowered = objective.lower()
    best_task_id = ""
    best_score = 0
    best_task: dict[str, Any] = {}
    for candidate_id, raw_task in tasks.items():
        if not isinstance(candidate_id, str) or not isinstance(raw_task, dict):
            continue
        triggers = raw_task.get("triggers")
        if not isinstance(triggers, list):
            triggers = []
        score = sum(1 for trigger in triggers if isinstance(trigger, str) and trigger.lower() in lowered)
        if candidate_id == task_id:
            score += 2
        if score > best_score:
            best_task_id = candidate_id
            best_score = score
            best_task = raw_task
    if best_score <= 0:
        return None

    modules = [
        Path(str(module_ref)).stem
        for module_ref in _json_list(best_task.get("requires"))
        if isinstance(module_ref, str)
    ]
    optional = [
        str(node_ref)
        for node_ref in _json_list(best_task.get("optional"))
        if isinstance(node_ref, str)
    ]
    branch_id = _select_manifest_branch(objective, optional)
    return {
        "task_id": best_task_id,
        "modules": modules,
        "optional": optional,
        "branch_id": branch_id,
        "reason": f"Manifest trigger score {best_score} matched objective.",
    }


def _select_manifest_branch(objective: str, optional_nodes: list[str]) -> str | None:
    lowered = objective.lower()
    if (
        "branches/tenure_visual_identity.branch.md" in optional_nodes
        and ("tenure" in lowered or "sop" in lowered)
    ):
        return "tenure_visual_identity"
    return None


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


def _transition_trace(
    task_id: str,
    modules: list[str],
    branch_id: str,
    shortcut_candidate: dict[str, Any],
) -> list[dict[str, str]]:
    if shortcut_candidate["matched"] and shortcut_candidate["usable_as_default"]:
        trace = [
            {
                "from": "ROUTER.START",
                "to": str(shortcut_candidate["node"]),
                "action": "USE",
                "why": "Persisted traversal receipts met promotion thresholds.",
            },
            {
                "from": str(shortcut_candidate["node"]),
                "to": f"@task:{task_id}",
                "action": "LOAD",
                "why": "Promoted shortcut preserves the underlying validated task path.",
            },
        ]
    else:
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
