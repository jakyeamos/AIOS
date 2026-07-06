from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_LIBRARY = ROOT / "skills-library"
DEFAULT_TMCP_REGISTRY = ROOT / "config" / "tmcp" / "registry.json"
BEHAVIOR_ATOM_REGISTRY_PATH = ROOT / "config" / "tmcp" / "behavior-atoms.json"
TMCP_PACKET_SCHEMA = "tmcp-runtime-packet-v0.1"
TMCP_RECEIPT_SCHEMA = "tmcp-traversal-receipt-v0.3"
TMCP_EVENT_SCHEMA = "tmcp-receipt-event-v0.1"
TMCP_ADHERENCE_SCHEMA = "tmcp-packet-adherence-v0.1"
TMCP_PACKET_DIFF_SCHEMA = "tmcp-packet-diff-v0.1"
TMCP_RUNTIME_EXPANSION_SCHEMA = "tmcp-runtime-expansion-v0.1"
SHORTCUT_STATUSES = (
    "active",
    "stale_candidate",
    "needs_revalidation",
    "scoped",
    "too_broad",
    "demoted",
    "quality_blocked",
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
    "audit": ("audit", "review", "inspect", "evaluate", "compare"),
    "implementation": ("implement", "edit", "patch", "fix", "refactor", "build"),
    "planning": ("plan", "roadmap", "phase", "acceptance", "strategy", "strategies", "promotion"),
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

DEFAULT_MODULES: tuple[str, ...] = (
    "context_gathering",
    "evidence_first",
    "provenance_policy",
    "output_contract",
)

PHASE_PROFILES: dict[str, dict[str, tuple[str, ...]]] = {
    "planning": {
        "atoms": ("execution_ready_plan", "acceptance_criteria", "risk_review"),
        "modules": ("context_gathering", "evidence_first"),
    },
    "implementation": {
        "atoms": ("read_before_edit", "bounded_change", "verification_gate"),
        "modules": ("minimal_patch_policy", "test_gate"),
    },
    "testing": {
        "atoms": ("test_authoring", "verification_gate", "claim_evidence"),
        "modules": ("test_gate",),
    },
    "review": {
        "atoms": ("risk_review", "finding_evidence", "evidence_trace"),
        "modules": ("evidence_first", "test_gate"),
    },
    "repair": {
        "atoms": ("reproduce_first", "root_cause_analysis", "bounded_change"),
        "modules": ("evidence_first", "test_gate"),
    },
    "closeout": {
        "atoms": ("evidence_trace", "validation_reporting", "claim_evidence"),
        "modules": ("output_contract", "test_gate"),
    },
}

DOMAIN_PROFILES: dict[str, dict[str, tuple[str, ...]]] = {
    "web_app": {
        "terms": ("next", "react", "frontend", "web app", "server action"),
        "atoms": ("verification_gate", "ui_quality"),
    },
    "ui_polish": {
        "terms": ("visual", "polish", "dashboard", "browser", "screenshot"),
        "atoms": ("ui_quality", "visual_verification"),
    },
    "data_science": {
        "terms": ("model", "notebook", "dataframe", "analysis", "metric"),
        "atoms": ("source_grounding", "verification_gate"),
    },
    "resume_job_workflow": {
        "terms": ("resume", "job", "application", "recruiter"),
        "atoms": ("source_grounding", "term_consistency"),
    },
    "sports_analytics": {
        "terms": ("sports", "lineup", "odds", "projection", "analytics"),
        "atoms": ("source_grounding", "verification_gate"),
    },
    "legal_timeline": {
        "terms": ("legal", "criminal", "timeline", "case", "evidence"),
        "atoms": ("source_grounding", "evidence_trace"),
    },
    "aios_internal": {
        "terms": ("aios", "tmcp", "context compiler", "managed run", "skill graph"),
        "atoms": ("skill_routing", "workflow_selection"),
    },
    "second_brain": {
        "terms": ("vault", "obsidian", "second brain", "knowledge", "synthesis"),
        "atoms": ("source_grounding", "provenance_trace"),
    },
}

ATOM_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "verification_gate": ("test", "pytest", "pnpm", "validate", "verification", "passed", "failed"),
    "claim_evidence": ("passed", "failed", "verification", "evidence", "checked"),
    "read_before_edit": ("read", "inspect", "opened", "reviewed", "rg", "sed"),
    "evidence_trace": ("evidence", "trace", "receipt", "source", "artifact"),
    "ui_quality": ("screenshot", "browser", "visual", "polish", "render"),
    "visual_verification": ("screenshot", "browser", "playwright", "viewport"),
    "source_grounding": ("source", "citation", "link", "reference", "paper"),
    "citation_discipline": ("citation", "quote", "source", "link"),
    "truth_update": ("project.md", "truth", "state", "updated"),
    "reproduce_first": ("reproduce", "failing", "failure", "before fix"),
    "root_cause_analysis": ("root cause", "cause", "because", "diagnosed"),
    "bounded_change": ("scoped", "minimal", "bounded", "only changed"),
    "risk_review": ("risk", "finding", "severity", "regression"),
    "finding_evidence": ("file", "line", "evidence", "finding"),
}

OPERATING_LANGUAGE_TERMS = (
    "operating language",
    "glossary",
    "ubiquitous language",
    "canonical vocabulary",
    "domain language",
    "architecture language",
    "leading word",
    "leading words",
    "vocabulary",
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
            node_usefulness_json TEXT NOT NULL DEFAULT '{}',
            omitted_requirements_json TEXT NOT NULL DEFAULT '[]',
            execution_outcome TEXT NOT NULL DEFAULT 'pending',
            validation_evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    _ensure_tmcp_column(conn, "node_usefulness_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_tmcp_column(conn, "omitted_requirements_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_tmcp_column(conn, "adherence_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_tmcp_column(conn, "phase", "TEXT")
    _ensure_tmcp_column(conn, "domain", "TEXT")
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tmcp_receipt_events (
            id TEXT PRIMARY KEY,
            receipt_id TEXT REFERENCES tmcp_traversal_receipts(id),
            run_id TEXT,
            invocation_id TEXT,
            event_type TEXT NOT NULL,
            node TEXT,
            behavior_atom TEXT,
            summary TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tmcp_receipt_events_receipt
          ON tmcp_receipt_events(receipt_id, created_at)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tmcp_intervention_events (
            id TEXT PRIMARY KEY,
            receipt_id TEXT REFERENCES tmcp_traversal_receipts(id),
            run_id TEXT,
            invocation_id TEXT,
            intervention_type TEXT NOT NULL,
            node TEXT,
            behavior_atom TEXT,
            summary TEXT NOT NULL,
            outcome TEXT NOT NULL DEFAULT 'recorded',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tmcp_intervention_events_receipt
          ON tmcp_intervention_events(receipt_id, created_at)
        """
    )


def _ensure_tmcp_column(conn: sqlite3.Connection, column: str, definition: str) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(tmcp_traversal_receipts)")}
    if column not in existing:
        conn.execute(f"ALTER TABLE tmcp_traversal_receipts ADD COLUMN {column} {definition}")


def compile_tmcp_packet(
    *,
    objective: str,
    project_path: str | None = None,
    context_receipt_id: str | None = None,
    skills_library_path: Path | None = None,
    receipt_conn: sqlite3.Connection | None = None,
    phase: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    library = skills_library_path or DEFAULT_SKILLS_LIBRARY
    tmcp_root = library / "skills.tmcp"
    graph = _load_graph(tmcp_root)
    objective_text = objective.strip()
    phase_id = _select_phase(objective_text, phase)
    domain_id = _select_domain(objective_text, project_path, domain)
    project_scope = _project_scope(project_path)
    if graph:
        task_id, task_scores = _select_task_from_graph(objective_text, graph, project_scope)
        modules, module_scores = _select_modules_from_graph(
            objective_text, task_id, graph, tmcp_root
        )
        modules = _apply_phase_domain_modules(modules, phase_id, domain_id, tmcp_root)
        source_skill_nodes, source_skill_scores = _select_source_skills_from_graph(
            objective_text,
            task_id,
            graph,
            library,
            project_scope,
            domain_id,
        )
        graph_warnings: list[str] = []
    else:
        task_id = _select_task(objective_text)
        modules = _select_modules(objective_text, task_id, tmcp_root)
        modules = _apply_phase_domain_modules(modules, phase_id, domain_id, tmcp_root)
        source_skill_nodes = []
        task_scores = {}
        module_scores = {}
        source_skill_scores = {}
        graph_warnings = ["skills.tmcp/graph.json missing; used heuristic TMCP traversal fallback."]
    optimization = _optimize_selection(
        objective=objective_text,
        task_id=task_id,
        modules=modules,
        source_skill_nodes=source_skill_nodes,
        graph=graph,
    )
    required_profile_atoms = sorted(
        {
            *optimization["behavior_atoms"],
            *PHASE_PROFILES.get(phase_id, {}).get("atoms", ()),
            *DOMAIN_PROFILES.get(domain_id, {}).get("atoms", ()),
        }
    )
    modules = optimization["modules"]
    source_skill_nodes = optimization["source_skill_nodes"]
    branch_id = _select_branch(objective_text, task_id)
    registry_overlay = _select_registry_overlay(objective_text, task_id, modules)
    router_selected_nodes = [
        f"@task:{task_id}",
        *(f"@module:{item}" for item in modules),
        *(str(item["node"]) for item in source_skill_nodes),
        f"@branch:{branch_id}",
        *registry_overlay["selected_nodes"],
    ]
    graph_version = _combined_graph_version(tmcp_root, registry_overlay["graph_paths"])
    selected_source_hashes = _selected_source_hashes(library, source_skill_nodes)
    fingerprint = _fingerprint(
        task_id=task_id,
        selected_nodes=router_selected_nodes,
        project_scope=project_scope,
    )
    skipped_nodes = _skipped_nodes(task_id, modules)
    skipped_nodes.extend(optimization["skipped_nodes"])
    shortcut = _shortcut_summary(tmcp_root)
    shortcut_candidate = _shortcut_candidate(
        tmcp_root=tmcp_root,
        task_id=task_id,
        graph_version=graph_version,
        fingerprint=fingerprint,
        source_hashes=selected_source_hashes,
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
        *(
            _node_excerpt(f"Module {module_id}", tmcp_root / "modules" / f"{module_id}.md")
            for module_id in modules
        ),
        *(
            _source_skill_section_excerpt(
                f"Source skill {source_skill['id']}",
                library / str(source_skill["path"]),
                max_chars=1600,
            )
            for source_skill in source_skill_nodes
        ),
        _optional_node_excerpt(
            f"Branch {branch_id}", tmcp_root / "branches" / f"{branch_id}.branch.md"
        ),
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
        "phase": phase_id,
        "domain": domain_id,
        "objective": objective_text,
        "project_path": project_path,
        "context_receipt_id": context_receipt_id,
        "source_graph_version": graph_version,
        "entry_node": entry_node,
        "selected_nodes": selected_nodes,
        "skipped_nodes": skipped_nodes,
        "selected_branches": [
            {"branch": f"@branch:{branch_id}", "reason": _branch_reason(branch_id)}
        ],
        "registry_overlay": registry_overlay["metadata"],
        "graph_metadata": {
            "matched": bool(graph),
            "schema": graph.get("schema") if graph else None,
            "warnings": graph_warnings,
        },
        "candidate_scores": {
            "tasks": task_scores,
            "modules": module_scores,
            "source_skills": source_skill_scores,
        },
        "source_skill_nodes": source_skill_nodes,
        "source_hashes": selected_source_hashes,
        "behavior_atoms": required_profile_atoms,
        "phase_profile": _phase_profile_summary(phase_id),
        "domain_profile": _domain_profile_summary(domain_id),
        "packet_optimization": optimization["metadata"],
        "node_usefulness": optimization["node_usefulness"],
        "omitted_requirements": optimization["omitted_requirements"],
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
            token_estimates_json, node_usefulness_json, omitted_requirements_json,
            execution_outcome, validation_evidence_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(packet.get("node_usefulness", {}), sort_keys=True),
            json.dumps(packet.get("omitted_requirements", []), sort_keys=True),
            execution_outcome,
            json.dumps(validation_evidence or [], sort_keys=True),
            now_iso(),
        ),
    )
    conn.execute(
        """
        UPDATE tmcp_traversal_receipts
        SET phase = ?, domain = ?
        WHERE id = ?
        """,
        (
            packet.get("phase"),
            packet.get("domain"),
            receipt_id,
        ),
    )
    record_tmcp_receipt_event(
        conn,
        receipt_id=receipt_id,
        event_type="packet_compiled",
        summary="TMCP packet compiled and persisted.",
        run_id=run_id,
        invocation_id=invocation_id,
        metadata={
            "selected_nodes": packet.get("selected_nodes", []),
            "behavior_atoms": packet.get("behavior_atoms", []),
            "phase": packet.get("phase"),
            "domain": packet.get("domain"),
        },
    )
    for node in _json_list(packet.get("selected_nodes")):
        record_tmcp_receipt_event(
            conn,
            receipt_id=receipt_id,
            event_type="node_selected",
            summary=f"Selected TMCP node {node}.",
            run_id=run_id,
            invocation_id=invocation_id,
            node=str(node),
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


def expand_tmcp_packet_for_requirement_change(
    conn: sqlite3.Connection,
    *,
    current_packet: dict[str, Any],
    reason: str,
    objective: str | None = None,
    project_path: str | None = None,
    context_receipt_id: str | None = None,
    skills_library_path: Path | None = None,
    run_id: str | None = None,
    invocation_id: str | None = None,
    session_id: str | None = None,
    phase: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    ensure_tmcp_schema(conn)
    previous_receipt_id = _optional_str(current_packet.get("receipt_id"))
    active_packet = compile_tmcp_packet(
        objective=objective or str(current_packet.get("objective", "")),
        project_path=project_path
        if project_path is not None
        else _optional_str(current_packet.get("project_path")),
        context_receipt_id=context_receipt_id
        if context_receipt_id is not None
        else _optional_str(current_packet.get("context_receipt_id")),
        skills_library_path=skills_library_path or _skills_library_from_packet(current_packet),
        receipt_conn=conn,
        phase=phase if phase is not None else _optional_str(current_packet.get("phase")),
        domain=domain if domain is not None else _optional_str(current_packet.get("domain")),
    )
    packet_diff = diff_tmcp_packets(current_packet, active_packet)
    receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=active_packet,
        run_id=run_id,
        invocation_id=invocation_id,
        session_id=session_id,
        execution_outcome="active_runtime_expansion",
        validation_evidence=[
            f"runtime requirement change: {reason}",
            f"previous_receipt_id={previous_receipt_id or 'none'}",
        ],
    )
    active_packet["receipt_id"] = receipt_id
    conn.execute(
        """
        UPDATE tmcp_traversal_receipts
        SET packet_json = ?
        WHERE id = ?
        """,
        (json.dumps(active_packet, sort_keys=True), receipt_id),
    )
    if previous_receipt_id:
        update_tmcp_traversal_receipt_outcome(
            conn,
            receipt_id=previous_receipt_id,
            execution_outcome="superseded_by_runtime_expansion",
            validation_evidence=[
                f"active_receipt_id={receipt_id}",
                f"runtime requirement change: {reason}",
            ],
        )
    metadata = {
        "reason": reason,
        "previous_receipt_id": previous_receipt_id,
        "new_receipt_id": receipt_id,
        "packet_diff": packet_diff,
        "phase": active_packet.get("phase"),
        "domain": active_packet.get("domain"),
        "selected_nodes": active_packet.get("selected_nodes", []),
    }
    intervention_id = record_tmcp_intervention_event(
        conn,
        receipt_id=receipt_id,
        run_id=run_id,
        invocation_id=invocation_id,
        intervention_type="runtime_packet_expansion",
        summary=f"Runtime TMCP packet expanded after requirement change: {reason}",
        outcome="expanded_packet_required",
        metadata=metadata,
    )
    record_tmcp_receipt_event(
        conn,
        receipt_id=receipt_id,
        run_id=run_id,
        invocation_id=invocation_id,
        event_type="packet_expanded",
        summary="Runtime TMCP packet expansion became the active workflow packet.",
        metadata=metadata,
    )
    return {
        "schema": TMCP_RUNTIME_EXPANSION_SCHEMA,
        "status": "expanded",
        "reason": reason,
        "previous_receipt_id": previous_receipt_id,
        "receipt_id": receipt_id,
        "intervention_id": intervention_id,
        "packet_diff": packet_diff,
        "active_packet": active_packet,
    }


def update_tmcp_receipt_feedback(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    node_usefulness: dict[str, Any] | None = None,
    omitted_requirements: list[dict[str, Any]] | None = None,
    validation_evidence: list[Any] | None = None,
    execution_outcome: str | None = None,
) -> dict[str, Any]:
    ensure_tmcp_schema(conn)
    row = conn.execute(
        """
        SELECT packet_json, node_usefulness_json, omitted_requirements_json,
               validation_evidence_json, execution_outcome
        FROM tmcp_traversal_receipts
        WHERE id = ?
        """,
        (receipt_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown TMCP traversal receipt: {receipt_id}")

    packet = _json_object(row[0])
    merged_usefulness = _json_object(row[1])
    if node_usefulness:
        for node, payload in node_usefulness.items():
            node_key = str(node)
            existing = _json_object(merged_usefulness.get(node_key))
            if isinstance(payload, dict):
                merged_usefulness[node_key] = {**existing, **payload}
            else:
                merged_usefulness[node_key] = {"feedback": payload}

    merged_omitted = _merge_omitted_requirements(_json_list(row[2]), omitted_requirements or [])
    merged_evidence = _json_list(row[3])
    merged_evidence.extend(validation_evidence or [])
    outcome = execution_outcome or str(row[4] or "pending")

    packet["node_usefulness"] = merged_usefulness
    packet["omitted_requirements"] = merged_omitted
    if validation_evidence:
        packet["validation_evidence"] = merged_evidence
    packet["repair_recommendations"] = _repair_recommendations_from_omissions(merged_omitted)
    conn.execute(
        """
        UPDATE tmcp_traversal_receipts
        SET packet_json = ?,
            node_usefulness_json = ?,
            omitted_requirements_json = ?,
            validation_evidence_json = ?,
            execution_outcome = ?
        WHERE id = ?
        """,
        (
            json.dumps(packet, sort_keys=True),
            json.dumps(merged_usefulness, sort_keys=True),
            json.dumps(merged_omitted, sort_keys=True),
            json.dumps(merged_evidence, sort_keys=True),
            outcome,
            receipt_id,
        ),
    )
    return {
        "schema": "tmcp-receipt-feedback-v0.1",
        "receipt_id": receipt_id,
        "execution_outcome": outcome,
        "node_usefulness": merged_usefulness,
        "omitted_requirements": merged_omitted,
        "repair_recommendations": packet["repair_recommendations"],
    }


def record_tmcp_receipt_event(
    conn: sqlite3.Connection,
    *,
    receipt_id: str | None,
    event_type: str,
    summary: str,
    run_id: str | None = None,
    invocation_id: str | None = None,
    node: str | None = None,
    behavior_atom: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_tmcp_schema(conn)
    event_id = f"tmcp-event-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO tmcp_receipt_events (
            id, receipt_id, run_id, invocation_id, event_type, node,
            behavior_atom, summary, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            receipt_id,
            run_id,
            invocation_id,
            event_type,
            node,
            behavior_atom,
            summary,
            json.dumps(metadata or {}, sort_keys=True),
            now_iso(),
        ),
    )
    return event_id


def record_tmcp_intervention_event(
    conn: sqlite3.Connection,
    *,
    receipt_id: str | None,
    intervention_type: str,
    summary: str,
    run_id: str | None = None,
    invocation_id: str | None = None,
    node: str | None = None,
    behavior_atom: str | None = None,
    outcome: str = "recorded",
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_tmcp_schema(conn)
    event_id = f"tmcp-intervention-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO tmcp_intervention_events (
            id, receipt_id, run_id, invocation_id, intervention_type, node,
            behavior_atom, summary, outcome, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            receipt_id,
            run_id,
            invocation_id,
            intervention_type,
            node,
            behavior_atom,
            summary,
            outcome,
            json.dumps(metadata or {}, sort_keys=True),
            now_iso(),
        ),
    )
    return event_id


def evaluate_tmcp_packet_adherence(
    *,
    packet: dict[str, Any],
    evidence: list[Any] | None = None,
    final_summary: str = "",
    validation_commands: list[str] | None = None,
) -> dict[str, Any]:
    evidence_items = evidence or []
    validation_items = validation_commands or []
    evidence_text = " ".join(
        [
            final_summary,
            *validation_items,
            json.dumps(evidence_items, sort_keys=True),
        ]
    ).lower()
    required_atoms = [str(atom) for atom in _json_list(packet.get("behavior_atoms"))]
    atom_results: dict[str, dict[str, Any]] = {}
    ignored: list[dict[str, str]] = []
    observed_count = 0
    for atom in required_atoms:
        observed = _atom_observed(atom, evidence_text)
        status = "observed" if observed else "ignored"
        if observed:
            observed_count += 1
        else:
            ignored.append(
                {
                    "requirement": atom,
                    "reason": "Packet required this behavior atom, but no matching action or evidence was observed.",
                    "failure_mode": "agent_compliance_failure",
                }
            )
        atom_results[atom] = {
            "required": True,
            "status": status,
            "observed": observed,
            "evidence_terms": list(ATOM_EVIDENCE_TERMS.get(atom, ())),
        }

    adherence_rate = round(observed_count / len(required_atoms), 3) if required_atoms else 1.0
    return {
        "schema": TMCP_ADHERENCE_SCHEMA,
        "status": "pass" if not ignored else "fail",
        "adherence_rate": adherence_rate,
        "required_behavior_atoms": required_atoms,
        "atom_results": atom_results,
        "ignored_requirements": ignored,
        "failure_classification": ("agent_compliance_failure" if ignored else "adhered_to_packet"),
    }


def persist_tmcp_packet_adherence(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    adherence: dict[str, Any],
    run_id: str | None = None,
    invocation_id: str | None = None,
) -> None:
    ensure_tmcp_schema(conn)
    row = conn.execute(
        "SELECT packet_json, omitted_requirements_json FROM tmcp_traversal_receipts WHERE id = ?",
        (receipt_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown TMCP traversal receipt: {receipt_id}")
    packet = _json_object(row[0])
    ignored = [
        item for item in _json_list(adherence.get("ignored_requirements")) if isinstance(item, dict)
    ]
    merged_omitted = _merge_omitted_requirements(_json_list(row[1]), ignored)
    packet["packet_adherence"] = adherence
    packet["omitted_requirements"] = merged_omitted
    conn.execute(
        """
        UPDATE tmcp_traversal_receipts
        SET packet_json = ?,
            adherence_json = ?,
            omitted_requirements_json = ?
        WHERE id = ?
        """,
        (
            json.dumps(packet, sort_keys=True),
            json.dumps(adherence, sort_keys=True),
            json.dumps(merged_omitted, sort_keys=True),
            receipt_id,
        ),
    )
    for atom, result in _json_object(adherence.get("atom_results")).items():
        record_tmcp_receipt_event(
            conn,
            receipt_id=receipt_id,
            event_type="agent_action_observed"
            if result.get("observed")
            else "required_behavior_ignored",
            summary=f"Behavior atom {atom} adherence status: {result.get('status')}.",
            run_id=run_id,
            invocation_id=invocation_id,
            behavior_atom=str(atom),
            metadata=_json_object(result),
        )


def diff_tmcp_packets(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_nodes = {str(item) for item in _json_list(before.get("selected_nodes"))}
    after_nodes = {str(item) for item in _json_list(after.get("selected_nodes"))}
    before_atoms = {str(item) for item in _json_list(before.get("behavior_atoms"))}
    after_atoms = {str(item) for item in _json_list(after.get("behavior_atoms"))}
    before_tokens = _json_object(before.get("token_estimates"))
    after_tokens = _json_object(after.get("token_estimates"))
    return {
        "schema": TMCP_PACKET_DIFF_SCHEMA,
        "task_changed": before.get("task_id") != after.get("task_id"),
        "phase_changed": before.get("phase") != after.get("phase"),
        "domain_changed": before.get("domain") != after.get("domain"),
        "nodes_added": sorted(after_nodes - before_nodes),
        "nodes_removed": sorted(before_nodes - after_nodes),
        "behavior_atoms_gained": sorted(after_atoms - before_atoms),
        "behavior_atoms_lost": sorted(before_atoms - after_atoms),
        "token_delta": int(after_tokens.get("custom_skill_tokens", 0) or 0)
        - int(before_tokens.get("custom_skill_tokens", 0) or 0),
        "routing_change_reason": _routing_change_reason(before, after),
    }


def explain_tmcp_packet(packet: dict[str, Any]) -> dict[str, Any]:
    token_estimates = _json_object(packet.get("token_estimates"))
    selected = [str(item) for item in _json_list(packet.get("selected_nodes"))]
    skipped = [item for item in _json_list(packet.get("skipped_nodes")) if isinstance(item, dict)]
    return {
        "schema": "tmcp-packet-explanation-v0.1",
        "status": packet.get("status"),
        "task_id": packet.get("task_id"),
        "entry_node": packet.get("entry_node"),
        "selected_nodes": selected,
        "skipped_nodes": skipped,
        "source_skill_nodes": _json_list(packet.get("source_skill_nodes")),
        "behavior_atoms": _json_list(packet.get("behavior_atoms")),
        "candidate_scores": _json_object(packet.get("candidate_scores")),
        "packet_optimization": _json_object(packet.get("packet_optimization")),
        "token_estimates": token_estimates,
        "estimated_token_roi": {
            "baseline_skill_tokens": token_estimates.get("baseline_skill_tokens"),
            "custom_skill_tokens": token_estimates.get("custom_skill_tokens"),
            "estimated_token_delta": token_estimates.get("estimated_token_delta"),
            "positive": int(token_estimates.get("estimated_token_delta", 0) or 0) > 0,
        },
        "shortcut_candidate": _json_object(packet.get("shortcut_candidate")),
        "omitted_requirements": _json_list(packet.get("omitted_requirements")),
        "repair_recommendations": _repair_recommendations_from_omissions(
            _json_list(packet.get("omitted_requirements"))
        ),
        "graph_metadata": _json_object(packet.get("graph_metadata")),
    }


def tmcp_learning_summary(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    ensure_tmcp_schema(conn)
    query = """
        SELECT id, task_id, packet_json, selected_nodes_json, token_estimates_json,
               node_usefulness_json, omitted_requirements_json, execution_outcome,
               validation_evidence_json, created_at
        FROM tmcp_traversal_receipts
    """
    params: tuple[Any, ...] = ()
    if task_id:
        query += " WHERE task_id = ?"
        params = (task_id,)
    query += " ORDER BY created_at DESC LIMIT ?"
    params = (*params, max(1, limit))

    node_stats: dict[str, dict[str, Any]] = {}
    atom_stats: dict[str, dict[str, Any]] = {}
    omitted_counts: dict[str, int] = {}
    receipt_count = 0
    success_count = 0
    for row in conn.execute(query, params).fetchall():
        receipt_count += 1
        packet = _json_object(row[2])
        selected_nodes = [str(item) for item in _json_list(row[3])]
        token_estimates = _json_object(row[4]) or _json_object(packet.get("token_estimates"))
        node_usefulness = _json_object(row[5]) or _json_object(packet.get("node_usefulness"))
        omitted = _json_list(row[6])
        outcome = str(row[7])
        success = outcome in {"completed", "pass", "passed", "success"}
        if success:
            success_count += 1
        token_delta = int(token_estimates.get("estimated_token_delta", 0) or 0)
        for node in selected_nodes:
            stats = node_stats.setdefault(
                node,
                {
                    "use_count": 0,
                    "success_count": 0,
                    "positive_token_roi_count": 0,
                    "token_delta_total": 0,
                },
            )
            stats["use_count"] += 1
            stats["success_count"] += int(success)
            stats["positive_token_roi_count"] += int(token_delta > 0)
            stats["token_delta_total"] += token_delta

            node_feedback = _json_object(node_usefulness.get(node))
            for atom in _json_list(node_feedback.get("behavior_atoms")):
                atom_key = str(atom)
                atom = atom_stats.setdefault(
                    atom_key,
                    {
                        "use_count": 0,
                        "success_count": 0,
                        "positive_token_roi_count": 0,
                        "token_delta_total": 0,
                    },
                )
                atom["use_count"] += 1
                atom["success_count"] += int(success)
                atom["positive_token_roi_count"] += int(token_delta > 0)
                atom["token_delta_total"] += token_delta
        for omission in omitted:
            if isinstance(omission, dict):
                requirement = str(omission.get("requirement", "unknown"))
            else:
                requirement = str(omission)
            omitted_counts[requirement] = omitted_counts.get(requirement, 0) + 1

    return {
        "schema": "tmcp-learning-summary-v0.1",
        "task_id": task_id,
        "receipt_count": receipt_count,
        "success_count": success_count,
        "node_roi": _finalize_roi_stats(node_stats),
        "behavior_atom_roi": _finalize_roi_stats(atom_stats),
        "missed_requirements": dict(sorted(omitted_counts.items())),
        "repair_recommendations": _repair_recommendations_from_counts(omitted_counts),
    }


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


def _load_graph(tmcp_root: Path) -> dict[str, Any]:
    graph_path = tmcp_root / "graph.json"
    if not graph_path.exists():
        return {}
    try:
        parsed = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict) or parsed.get("schema") != "tmcp-graph-v0.1":
        return {}
    return parsed


def _select_task_from_graph(
    objective: str,
    graph: dict[str, Any],
    project_scope: str,
) -> tuple[str, dict[str, int]]:
    tasks = _json_object(graph.get("tasks"))
    scores: dict[str, int] = {}
    for task_id, row in tasks.items():
        if not isinstance(task_id, str) or not isinstance(row, dict):
            continue
        score = _score_graph_row(objective, row)
        if task_id == "agent_workflow" and any(
            term in objective.lower() for term in ("skill", "tmcp", "agent", "workflow")
        ):
            score += 2
        if (
            project_scope != "unknown"
            and project_scope in str(row.get("project_scope", "")).lower()
        ):
            score += 3
        scores[task_id] = score
    if not scores:
        return _select_task(objective), {}
    best_score = max(scores.values())
    if best_score <= 0:
        return "agent_workflow", scores
    for task_id in TASK_PRIORITY:
        if scores.get(task_id) == best_score:
            return task_id, scores
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0], scores


def _select_modules_from_graph(
    objective: str,
    task_id: str,
    graph: dict[str, Any],
    tmcp_root: Path,
) -> tuple[list[str], dict[str, int]]:
    modules = _json_object(graph.get("modules"))
    tasks = _json_object(graph.get("tasks"))
    task = _json_object(tasks.get(task_id))
    required = [
        str(item) for item in _json_list(task.get("required_modules")) if isinstance(item, str)
    ]
    selected = list(DEFAULT_MODULES)
    scores: dict[str, int] = {}
    for module_id, row in modules.items():
        if not isinstance(module_id, str) or not isinstance(row, dict):
            continue
        score = _score_graph_row(objective, row)
        if module_id in required:
            score += 2
        if module_id == "test_gate" and (
            task_id in {"implementation", "debugging", "planning", "testing"}
            or any(term in objective.lower() for term in ("test", "verify", "validate"))
        ):
            score += 4
        if module_id == "tool_use_policy" and any(
            term in objective.lower() for term in ("tool", "command", "browser", "shell", "mcp")
        ):
            score += 4
        if score > 0:
            selected.append(module_id)
        scores[module_id] = score
    return [
        module_id for module_id in dict.fromkeys(selected) if _module_exists(tmcp_root, module_id)
    ], scores


def _apply_phase_domain_modules(
    modules: list[str],
    phase: str,
    domain: str,
    tmcp_root: Path,
) -> list[str]:
    selected = list(modules)
    for module_id in PHASE_PROFILES.get(phase, {}).get("modules", ()):
        selected.append(module_id)
    if domain == "ui_polish":
        selected.extend(("visual_polish_system", "test_gate"))
    return [
        module_id for module_id in dict.fromkeys(selected) if _module_exists(tmcp_root, module_id)
    ]


def _select_source_skills_from_graph(
    objective: str,
    task_id: str,
    graph: dict[str, Any],
    library: Path,
    project_scope: str,
    domain: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source_skills = _json_object(graph.get("source_skills"))
    scores: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    objective_terms = _terms(objective)
    for skill_id, row in source_skills.items():
        if not isinstance(skill_id, str) or not isinstance(row, dict):
            continue
        score = _score_graph_row(objective, row)
        concept = str(row.get("concept_key", ""))
        if task_id in concept:
            score += 2
        tiers = _json_list(row.get("source_tiers"))
        if "project_authoritative" in tiers:
            score += 2
        searchable = " ".join(
            str(row.get(key, "")) for key in ("id", "concept_key", "title")
        ).lower()
        if project_scope != "unknown" and project_scope in searchable:
            score += 3
        if domain != "general" and domain.replace("_", "-") in searchable.replace("_", "-"):
            score += 4
        skill_terms = set(_json_list(row.get("triggers")))
        if objective_terms & {str(term).lower() for term in skill_terms}:
            score += 2
        path = row.get("path")
        if score >= 6 and isinstance(path, str) and (library / path).exists():
            selected.append(
                {
                    "id": skill_id,
                    "node": str(row.get("node", f"@source_skill:{skill_id}")),
                    "path": path,
                    "score": score,
                    "source_tiers": [str(item) for item in tiers],
                    "reason": "Graph source-skill score met the precision inclusion threshold.",
                }
            )
        scores[skill_id] = score
    selected.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    return selected[:3], dict(sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:20])


def _select_phase(objective: str, phase: str | None) -> str:
    if phase and phase in PHASE_PROFILES:
        return phase
    lowered = objective.lower()
    if any(term in lowered for term in ("closeout", "final", "summarize", "claim")):
        return "closeout"
    if any(term in lowered for term in ("repair", "fix failing", "rerun", "regression")):
        return "repair"
    if any(term in lowered for term in ("review", "audit", "inspect")):
        return "review"
    if any(term in lowered for term in ("test", "verify", "validate")):
        return "testing"
    if any(term in lowered for term in ("plan", "phase", "acceptance")):
        return "planning"
    if any(term in lowered for term in ("implement", "build", "patch", "edit", "fix")):
        return "implementation"
    return "implementation"


def _select_domain(objective: str, project_path: str | None, domain: str | None) -> str:
    if domain and domain in DOMAIN_PROFILES:
        return domain
    haystack = f"{objective} {project_path or ''}".lower()
    for domain_id, profile in DOMAIN_PROFILES.items():
        if any(term in haystack for term in profile.get("terms", ())):
            return domain_id
    return "general"


def _phase_profile_summary(phase: str) -> dict[str, Any]:
    profile = PHASE_PROFILES.get(phase, {})
    return {
        "phase": phase,
        "behavior_atoms": list(profile.get("atoms", ())),
        "modules": list(profile.get("modules", ())),
    }


def _domain_profile_summary(domain: str) -> dict[str, Any]:
    profile = DOMAIN_PROFILES.get(domain, {})
    return {
        "domain": domain,
        "behavior_atoms": list(profile.get("atoms", ())),
        "terms": list(profile.get("terms", ())),
    }


def _score_graph_row(objective: str, row: dict[str, Any]) -> int:
    lowered = objective.lower()
    score = 0
    for trigger in _json_list(row.get("triggers")):
        if not isinstance(trigger, str):
            continue
        trigger_text = trigger.lower()
        if trigger_text and trigger_text in lowered:
            score += 4
        elif trigger_text and trigger_text in _terms(lowered):
            score += 2
    searchable = " ".join(
        str(row.get(key, "")) for key in ("id", "node", "concept_key", "title", "type")
    ).lower()
    score += len(_terms(lowered) & _terms(searchable))
    return score


def _terms(value: str) -> set[str]:
    stop = {"this", "that", "with", "from", "into", "the", "and", "for", "your"}
    return {
        term
        for term in re.split(r"[^a-z0-9]+", value.lower())
        if len(term) >= 3 and term not in stop
    }


def _selected_source_hashes(
    library: Path, source_skill_nodes: list[dict[str, Any]]
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for source_skill in source_skill_nodes:
        node = str(source_skill.get("node", ""))
        path_value = source_skill.get("path")
        if not node or not isinstance(path_value, str):
            continue
        path = library / path_value
        try:
            content = path.read_bytes()
        except OSError:
            continue
        hashes[node] = hashlib.sha256(content).hexdigest()
    return dict(sorted(hashes.items()))


def _optimize_selection(
    *,
    objective: str,
    task_id: str,
    modules: list[str],
    source_skill_nodes: list[dict[str, Any]],
    graph: dict[str, Any],
) -> dict[str, Any]:
    module_rows = _json_object(graph.get("modules")) if graph else {}
    task_rows = _json_object(graph.get("tasks")) if graph else {}
    source_rows = _json_object(graph.get("source_skills")) if graph else {}
    task_row = _json_object(task_rows.get(task_id))
    selected_source_atoms: set[str] = set()
    for source_skill in source_skill_nodes:
        row = _json_object(source_rows.get(str(source_skill.get("id", ""))))
        selected_source_atoms.update(str(atom) for atom in _json_list(row.get("behavior_atoms")))

    optimized_modules: list[str] = []
    skipped_nodes: list[dict[str, str]] = []
    covered_atoms: set[str] = {str(atom) for atom in _json_list(task_row.get("behavior_atoms"))}
    for module_id in modules:
        row = _json_object(module_rows.get(module_id))
        atoms = {str(atom) for atom in _json_list(row.get("behavior_atoms"))}
        risk = str(row.get("risk_if_omitted", "medium"))
        if atoms and atoms <= selected_source_atoms and risk != "high":
            skipped_nodes.append(
                {
                    "node": f"@module:{module_id}",
                    "reason": "Skipped by behavior diff: selected source skill already adds the same behavior atoms.",
                }
            )
            continue
        if atoms and atoms <= covered_atoms and risk == "low":
            skipped_nodes.append(
                {
                    "node": f"@module:{module_id}",
                    "reason": "Skipped by packet optimizer: behavior atoms were already covered by earlier nodes.",
                }
            )
            continue
        optimized_modules.append(module_id)
        covered_atoms.update(atoms)

    source_skill_nodes = sorted(
        source_skill_nodes,
        key=lambda item: (
            -int(item.get("score", 0)),
            int(_json_object(source_rows.get(str(item.get("id", "")))).get("token_cost", 400)),
            str(item.get("id", "")),
        ),
    )[:3]
    for source_skill in source_skill_nodes:
        row = _json_object(source_rows.get(str(source_skill.get("id", ""))))
        covered_atoms.update(str(atom) for atom in _json_list(row.get("behavior_atoms")))

    omitted_requirements = _omitted_requirements(
        objective, covered_atoms, optimized_modules, task_id
    )
    node_usefulness = {
        f"@task:{task_id}": {
            "prior": "required",
            "reason": "Entry task selected by prompt intent.",
            "behavior_atoms": _json_list(task_row.get("behavior_atoms")),
        },
        **{
            f"@module:{module_id}": {
                "prior": _node_usefulness_prior(_json_object(module_rows.get(module_id))),
                "behavior_atoms": _json_list(
                    _json_object(module_rows.get(module_id)).get("behavior_atoms")
                ),
            }
            for module_id in optimized_modules
        },
        **{
            str(source_skill["node"]): {
                "prior": "high" if source_skill.get("score", 0) >= 8 else "medium",
                "behavior_atoms": _json_list(
                    _json_object(source_rows.get(str(source_skill.get("id", "")))).get(
                        "behavior_atoms"
                    )
                ),
            }
            for source_skill in source_skill_nodes
        },
    }
    return {
        "modules": optimized_modules,
        "source_skill_nodes": source_skill_nodes,
        "skipped_nodes": skipped_nodes,
        "behavior_atoms": sorted(covered_atoms),
        "omitted_requirements": omitted_requirements,
        "node_usefulness": node_usefulness,
        "metadata": {
            "schema": "tmcp-packet-optimization-v0.1",
            "initial_module_count": len(modules),
            "optimized_module_count": len(optimized_modules),
            "source_skill_count": len(source_skill_nodes),
            "skipped_redundant_count": len(skipped_nodes),
            "strategy": "behavior_atom_diff_then_token_cap",
        },
    }


def _node_usefulness_prior(row: dict[str, Any]) -> str:
    risk = str(row.get("risk_if_omitted", "medium"))
    if risk == "high":
        return "high"
    if int(row.get("token_cost", 200) or 200) <= 220:
        return "medium"
    return "low"


def _omitted_requirements(
    objective: str,
    covered_atoms: set[str],
    modules: list[str],
    task_id: str,
) -> list[dict[str, str]]:
    lowered = objective.lower()
    omitted: list[dict[str, str]] = []
    if (
        any(term in lowered for term in ("test", "verify", "validate"))
        and "verification_gate" not in covered_atoms
    ):
        omitted.append(
            {
                "requirement": "verification_gate",
                "reason": "Prompt requested validation but no selected node contributed a verification behavior atom.",
            }
        )
    if (
        any(term in lowered for term in ("browser", "screenshot", "visual"))
        and "ui_quality" not in covered_atoms
    ):
        omitted.append(
            {
                "requirement": "ui_quality",
                "reason": "Prompt requested UI/visual work but no selected node contributed a UI quality behavior atom.",
            }
        )
    if (
        task_id == "implementation"
        and "test_gate" not in modules
        and "verification_gate" not in covered_atoms
    ):
        omitted.append(
            {
                "requirement": "implementation_validation",
                "reason": "Implementation task lacks an explicit validation node.",
            }
        )
    return omitted


def _select_modules(objective: str, task_id: str, tmcp_root: Path) -> list[str]:
    lowered = objective.lower()
    modules = list(DEFAULT_MODULES)
    if any(term in lowered for term in OPERATING_LANGUAGE_TERMS):
        modules.append("operating_language")
    if task_id in {"implementation", "debugging", "planning", "testing"} or any(
        term in lowered for term in ("test", "verify", "validate")
    ):
        modules.append("test_gate")
    if any(term in lowered for term in ("tool", "command", "browser", "shell", "mcp")):
        modules.append("tool_use_policy")
    if task_id == "visual_polish":
        modules.extend(
            ("visual_polish_system", "enterprise_saas_visual_polish", "data_realism_polish")
        )
    return [
        module_id for module_id in dict.fromkeys(modules) if _module_exists(tmcp_root, module_id)
    ]


def _select_branch(objective: str, task_id: str) -> str:
    lowered = objective.lower()
    direct_terms = ("implement", "fix", "patch", "edit", "do this", "build", "wire")
    if any(term in lowered for term in direct_terms):
        return "direct_implementation"
    if task_id in {"audit", "planning", "research", "testing", "documentation"}:
        return "approval_before_edit"
    return "ambiguous_task_resolution"


def _skipped_nodes(task_id: str, modules: list[str]) -> list[dict[str, str]]:
    selected = {task_id, *modules}
    skipped: list[dict[str, str]] = []
    for candidate in ("research", "documentation", "testing"):
        if candidate not in selected and candidate != task_id:
            skipped.append(
                {"node": f"@task:{candidate}", "reason": "Not required by objective classifier."}
            )
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
    source_hashes: dict[str, str],
    receipt_conn: sqlite3.Connection | None,
) -> dict[str, Any]:
    candidate_path = tmcp_root / "shortcuts" / "candidate.md"
    promoted = _promoted_shortcut_from_receipts(
        receipt_conn=receipt_conn,
        task_id=task_id,
        graph_version=graph_version,
        fingerprint=fingerprint,
        source_hashes=source_hashes,
    )
    if promoted is not None:
        _materialize_shortcut(tmcp_root, promoted)
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
        "source_hashes": source_hashes,
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
    source_hashes: dict[str, str],
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
        packet_source_hashes = _json_object(packet.get("source_hashes"))
        if source_hashes and packet_source_hashes != source_hashes:
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
    successful = [
        row for row in qualifying if row["outcome"] in {"completed", "pass", "passed", "success"}
    ]
    success_rate = len(successful) / len(qualifying)
    positive_roi_count = sum(1 for row in successful if row["positive_token_roi"])
    if len(successful) < 3 or success_rate < 0.8 or positive_roi_count < 2:
        return None

    shortcut_node = f"@shortcut:{task_id}:{fingerprint[:12]}"
    latest_packet = _json_object(rows[0][1])
    selected_nodes = [str(item) for item in _json_list(latest_packet.get("selected_nodes"))]
    latest_token_estimates = _json_object(latest_packet.get("token_estimates"))
    return {
        "node": shortcut_node,
        "matched": True,
        "status": "active",
        "usable_as_default": True,
        "freshness": "confirmed",
        "source_graph_version": graph_version,
        "source_tasks": [f"@task:{task_id}"],
        "source_modules": [node for node in selected_nodes if node.startswith("@module:")],
        "source_branches": [node for node in selected_nodes if node.startswith("@branch:")],
        "source_skills": [node for node in selected_nodes if node.startswith("@source_skill:")],
        "source_hashes": source_hashes,
        "compiled_packet": {
            "selected_nodes": selected_nodes,
            "behavior_atoms": _json_list(latest_packet.get("behavior_atoms")),
            "token_estimates": latest_token_estimates,
        },
        "known_failure_cases": [],
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


def _materialize_shortcut(tmcp_root: Path, shortcut: dict[str, Any]) -> None:
    node = str(shortcut.get("node", ""))
    match = re.match(r"^@shortcut:([a-zA-Z0-9_-]+):([a-f0-9]+)$", node)
    if not match or not tmcp_root.exists():
        return
    task_id, digest = match.groups()
    target_dir = tmcp_root / "shortcuts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{task_id}-{digest}.md"
    content = "\n".join(
        [
            f"# Shortcut: {task_id} {digest}",
            "",
            f"Shortcut Node: {node}",
            f"Status: {shortcut.get('status', 'active')}",
            f"Source graph version: {shortcut.get('source_graph_version', '')}",
            "",
            "## Source Nodes",
            *(f"- {item}" for item in _json_list(shortcut.get("source_tasks"))),
            *(f"- {item}" for item in _json_list(shortcut.get("source_modules"))),
            *(f"- {item}" for item in _json_list(shortcut.get("source_branches"))),
            *(f"- {item}" for item in _json_list(shortcut.get("source_skills"))),
            "",
            "## Evidence",
            *(f"- {item}" for item in _json_list(shortcut.get("evidence_receipt_ids"))),
            "",
            "## Source Hashes",
            *(
                f"- {node}: {digest}"
                for node, digest in sorted(_json_object(shortcut.get("source_hashes")).items())
            ),
            "",
            "## Compiled Packet",
            "```json",
            json.dumps(_json_object(shortcut.get("compiled_packet")), indent=2, sort_keys=True),
            "```",
            "",
            "## Known Failure Cases",
            *(
                f"- {item}"
                for item in (_json_list(shortcut.get("known_failure_cases")) or ["none recorded"])
            ),
            "",
            "## Fallback",
            str(shortcut.get("fallback", "router_traversal")),
            "",
        ]
    )
    try:
        target.write_text(content, encoding="utf-8")
    except OSError:
        return


@lru_cache(maxsize=1)
def _behavior_atom_registry() -> dict[str, Any]:
    if not BEHAVIOR_ATOM_REGISTRY_PATH.exists():
        return {"schema": "tmcp-behavior-atoms-fallback", "semantic_section_labels": {}}
    try:
        parsed = json.loads(BEHAVIOR_ATOM_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "tmcp-behavior-atoms-fallback", "semantic_section_labels": {}}
    return parsed if isinstance(parsed, dict) else {"schema": "tmcp-behavior-atoms-fallback"}


def _merge_omitted_requirements(
    existing: list[Any],
    updates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in existing:
        if isinstance(item, dict):
            requirement = str(item.get("requirement", "unknown"))
            merged[requirement] = {str(key): value for key, value in item.items()}
        else:
            merged[str(item)] = {"requirement": str(item)}
    for item in updates:
        requirement = str(item.get("requirement", "unknown"))
        merged[requirement] = {**merged.get(requirement, {}), **item, "requirement": requirement}
    return [merged[key] for key in sorted(merged)]


def _repair_recommendations_from_omissions(omissions: list[Any]) -> list[dict[str, str]]:
    counts: dict[str, int] = {}
    for omission in omissions:
        if isinstance(omission, dict):
            requirement = str(omission.get("requirement", "unknown"))
        else:
            requirement = str(omission)
        counts[requirement] = counts.get(requirement, 0) + 1
    return _repair_recommendations_from_counts(counts)


def _repair_recommendations_from_counts(counts: dict[str, int]) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    for requirement, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if requirement in {"verification_gate", "implementation_validation"}:
            action = "Raise test_gate scoring and add a golden prompt that requires validation."
        elif requirement == "ui_quality":
            action = "Raise visual_polish scoring and require visual_verification for browser or screenshot prompts."
        else:
            action = (
                "Add or retune a trigger so traversal covers this behavior atom when requested."
            )
        recommendations.append(
            {
                "requirement": requirement,
                "miss_count": str(count),
                "recommended_action": action,
            }
        )
    return recommendations


def _finalize_roi_stats(stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    finalized: dict[str, dict[str, Any]] = {}
    for key, row in stats.items():
        use_count = int(row.get("use_count", 0) or 0)
        success_count = int(row.get("success_count", 0) or 0)
        token_delta_total = int(row.get("token_delta_total", 0) or 0)
        finalized[key] = {
            "use_count": use_count,
            "success_count": success_count,
            "success_rate": round(success_count / use_count, 3) if use_count else None,
            "positive_token_roi_count": int(row.get("positive_token_roi_count", 0) or 0),
            "average_token_delta": round(token_delta_total / use_count, 3) if use_count else None,
        }
    return dict(sorted(finalized.items()))


def _atom_observed(atom: str, evidence_text: str) -> bool:
    terms = ATOM_EVIDENCE_TERMS.get(atom)
    if not terms:
        return True
    if atom in {"verification_gate", "claim_evidence", "test_authoring"} and any(
        phrase in evidence_text
        for phrase in ("not run", "no test", "no validation", "without validation", "did not run")
    ):
        return False
    return any(term in evidence_text for term in terms)


def _routing_change_reason(before: dict[str, Any], after: dict[str, Any]) -> str:
    reasons: list[str] = []
    if before.get("task_id") != after.get("task_id"):
        reasons.append("task changed")
    if before.get("phase") != after.get("phase"):
        reasons.append("phase changed")
    if before.get("domain") != after.get("domain"):
        reasons.append("domain changed")
    before_shortcut = _json_object(before.get("shortcut_candidate"))
    after_shortcut = _json_object(after.get("shortcut_candidate"))
    if before_shortcut.get("node") != after_shortcut.get("node"):
        reasons.append("shortcut candidate changed")
    return (
        ", ".join(reasons)
        if reasons
        else "same task/phase/domain; node selection changed by scoring or graph metadata"
    )


def shortcut_governance_recommendation(shortcut: dict[str, Any]) -> dict[str, Any]:
    stats = _json_object(shortcut.get("promotion_stats"))
    success_rate = float(stats.get("validation_success_rate", 0) or 0)
    missed = int(stats.get("missed_requirement_count", 0) or 0)
    positive_roi = int(stats.get("positive_token_roi_count", 0) or 0)
    scope = str(shortcut.get("scope", "global"))
    if missed:
        status = "demoted"
        action = "Demote shortcut and fall back to graph traversal until missed requirements are repaired."
    elif success_rate and success_rate < 0.8:
        status = "quality_blocked"
        action = "Block promotion because quality is below shortcut threshold."
    elif positive_roi <= 0:
        status = "quality_blocked"
        action = "Block promotion because token savings are not positive."
    elif scope not in {"global", "cross_project"}:
        status = "scoped"
        action = "Keep shortcut active only for the proven repo or domain scope."
    else:
        status = str(shortcut.get("status", "active"))
        action = "Shortcut can remain active while freshness and quality evidence hold."
    return {
        "schema": "tmcp-shortcut-governance-v0.1",
        "node": shortcut.get("node"),
        "recommended_status": status,
        "recommended_action": action,
        "preserve_artifact": True,
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


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _skills_library_from_packet(packet: dict[str, Any]) -> Path | None:
    source = _optional_str(packet.get("source"))
    if source is None:
        return None
    source_path = Path(source)
    if source_path.name == "skills.tmcp":
        return source_path.parent
    return source_path


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


def _source_skill_section_excerpt(title: str, path: Path, *, max_chars: int = 1600) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    sections = _markdown_sections(content)
    scored_sections = sorted(
        (
            (_semantic_section_score(heading, section), index, section)
            for index, (heading, section) in enumerate(sections)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    preferred = [section for score, _index, section in scored_sections if score > 0]
    excerpt = "\n\n".join(preferred[:4]).strip() or content.strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "\n...(truncated)"
    return f"## {title}\n\nSource: `{path}`\n\n{excerpt}\n"


def _semantic_section_score(heading: str, section: str) -> int:
    labels = _json_object(_behavior_atom_registry().get("semantic_section_labels"))
    haystack = f"{heading}\n{section[:400]}".lower()
    score = 0
    label_weights = {
        "triggers": 6,
        "constraints": 5,
        "procedure": 5,
        "validation": 5,
        "failure_modes": 4,
    }
    for label, patterns in labels.items():
        weight = label_weights.get(str(label), 2)
        for pattern in _json_list(patterns):
            if str(pattern).lower() in haystack:
                score += weight
                break
    if heading.lower() in {"examples", "example", "appendix", "notes"}:
        score -= 4
    return score


def _markdown_sections(content: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = "preamble"
    current_lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line.lstrip("#").strip() or "section"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return [(heading, section) for heading, section in sections if section]


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
            "## Packet Optimization",
            "- Include only behavior-changing nodes for this objective.",
            "- Prefer source-skill excerpts over generic modules when they add the same behavior with stronger provenance.",
            "- Treat skipped nodes as negative selection evidence for future routing.",
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
    graph_inputs = [
        *tmcp_root.rglob("*.md"),
        tmcp_root / "graph.json",
        tmcp_root.parent / "skills.lock",
    ]
    for path in sorted({path for path in graph_inputs if path.exists()}):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        digest.update(path.relative_to(tmcp_root.parent).as_posix().encode("utf-8"))
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


def _select_registry_overlay(
    objective: str,
    task_id: str,
    canonical_modules: list[str],
) -> dict[str, Any]:
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
        route = _select_manifest_task(objective, task_id, manifest, canonical_modules)
        if route is not None and _should_skip_overlay_for_tmcp_internal_work(objective, route):
            skipped_namespaces.append(
                {
                    "namespace": namespace_id,
                    "reason": (
                        "TMCP-internal routing work uses the canonical graph unless "
                        "instruction hygiene is explicitly requested."
                    ),
                }
            )
            continue
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
                "matched_triggers": route["matched_triggers"],
                "behavior_added": route["behavior_added"],
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


def _should_skip_overlay_for_tmcp_internal_work(
    objective: str,
    route: dict[str, Any],
) -> bool:
    lowered = objective.lower()
    internal_terms = (
        "tmcp",
        "skill graph",
        "canonical graph",
        "manifest trigger",
        "manifest triggers",
        "packet selection",
        "route selection",
        "routing",
    )
    if not any(term in lowered for term in internal_terms):
        return False
    return route.get("task_id") != "instruction_hygiene"


def _json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _select_manifest_task(
    objective: str,
    task_id: str,
    manifest: dict[str, Any],
    canonical_modules: list[str],
) -> dict[str, Any] | None:
    tasks = _json_object(_json_object(manifest.get("nodes")).get("tasks"))
    lowered = objective.lower()
    best_task_id = ""
    best_score = 0
    best_task: dict[str, Any] = {}
    best_matched_triggers: list[str] = []
    for candidate_id, raw_task in tasks.items():
        if not isinstance(candidate_id, str) or not isinstance(raw_task, dict):
            continue
        triggers = raw_task.get("triggers")
        if not isinstance(triggers, list):
            triggers = []
        matched_triggers = [
            str(trigger)
            for trigger in triggers
            if isinstance(trigger, str) and _trigger_matches(lowered, trigger)
        ]
        score = len(matched_triggers)
        if candidate_id == task_id:
            score += 2
        if score > best_score:
            best_task_id = candidate_id
            best_score = score
            best_task = raw_task
            best_matched_triggers = matched_triggers
    if best_score <= 0 or not best_matched_triggers:
        return None
    if len(best_matched_triggers) < 2 and best_task_id != "visual_polish":
        return None
    if best_task_id == "planning_review" and not any(
        term in lowered
        for term in ("compare", "strategy", "workflow", "promotion", "quality", "test")
    ):
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
    behavior_added = [
        f"module:{module_id}" for module_id in modules if module_id not in canonical_modules
    ]
    if branch_id:
        behavior_added.append(f"branch:{branch_id}")
    if not behavior_added:
        return None
    return {
        "task_id": best_task_id,
        "modules": modules,
        "optional": optional,
        "branch_id": branch_id,
        "matched_triggers": best_matched_triggers,
        "behavior_added": behavior_added,
        "reason": (
            f"Manifest triggers {', '.join(best_matched_triggers)} matched objective "
            f"and added {', '.join(behavior_added)}."
        ),
    }


def _select_manifest_branch(objective: str, optional_nodes: list[str]) -> str | None:
    lowered = objective.lower()
    if "branches/tenure_visual_identity.branch.md" in optional_nodes and (
        "tenure" in lowered or "sop" in lowered
    ):
        return "tenure_visual_identity"
    return None


def _trigger_matches(lowered_objective: str, trigger: str) -> bool:
    trigger_text = trigger.lower()
    if trigger_text in lowered_objective:
        return True
    trigger_terms = _terms(trigger_text)
    if not trigger_terms:
        return False
    objective_terms = _terms(lowered_objective)
    overlap = trigger_terms & objective_terms
    return len(overlap) >= max(2, len(trigger_terms) - 1)


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
    if branch_id == "approval_before_edit":
        return "Objective is read-only or planning-oriented; require approval before edits."
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
