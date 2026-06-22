from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.tmcp_runtime import (  # noqa: E402
    compile_tmcp_packet,
    ensure_tmcp_schema,
    persist_tmcp_traversal_receipt,
)


def _seed_tmcp_library(root: Path) -> Path:
    tmcp = root / "skills.tmcp"
    for directory in ("tasks", "modules", "branches", "shortcuts"):
        (tmcp / directory).mkdir(parents=True, exist_ok=True)
    (tmcp / "router.md").write_text("# Router\n\nLOAD task nodes.\n", encoding="utf-8")
    (tmcp / "tasks" / "implementation.md").write_text(
        "# Implementation\n\n## Transition Edges\n\n## Custom Skill Construction\n",
        encoding="utf-8",
    )
    for module in (
        "context_gathering",
        "evidence_first",
        "provenance_policy",
        "output_contract",
        "test_gate",
    ):
        (tmcp / "modules" / f"{module}.md").write_text(
            f"# Module {module}\n\nUse {module}.\n",
            encoding="utf-8",
        )
    (tmcp / "branches" / "direct_implementation.branch.md").write_text(
        "# Direct Implementation\n\nProceed when intent is explicit.\n",
        encoding="utf-8",
    )
    (tmcp / "shortcuts" / "candidate.md").write_text(
        "# Shortcut Candidate\n\n## Promotion Threshold\n",
        encoding="utf-8",
    )
    return root


def test_compile_tmcp_packet_selects_task_and_stable_fingerprint(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        context_receipt_id="packet-1",
        skills_library_path=library,
    )
    again = compile_tmcp_packet(
        objective="Implement another feature and run tests",
        project_path="/tmp/project",
        context_receipt_id="packet-2",
        skills_library_path=library,
    )

    assert packet["status"] == "compiled"
    assert packet["task_id"] == "implementation"
    assert "@task:implementation" in packet["selected_nodes"]
    assert "@module:test_gate" in packet["selected_nodes"]
    assert packet["selected_branches"][0]["branch"] == "@branch:direct_implementation"
    assert "AIOS TMCP Custom Skill Packet" in packet["packet_markdown"]
    assert packet["source_graph_version"] != "missing"
    assert packet["shortcut_candidate"]["fallback"] == "router_traversal"
    assert packet["shortcut_candidate"]["status"] == "needs_revalidation"
    assert packet["shortcut_candidate"]["usable_as_default"] is False
    assert "stale_candidate" in packet["shortcut_governance"]["allowed_statuses"]
    assert "split_more_specific" in packet["shortcut_governance"]["rebuild_outcomes"]
    assert "Shortcut Freshness" in packet["packet_markdown"]
    assert packet["traversal_fingerprint"] == again["traversal_fingerprint"]
    assert packet["token_estimates"]["custom_skill_tokens"] > 0


def test_persist_tmcp_traversal_receipt_records_packet(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    packet = compile_tmcp_packet(
        objective="Implement the feature",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    conn = sqlite3.connect(":memory:")

    ensure_tmcp_schema(conn)
    receipt_id = persist_tmcp_traversal_receipt(
        conn,
        packet=packet,
        run_id="run-1",
        invocation_id="invoke-1",
        session_id="session-1",
    )

    row = conn.execute(
        """
        SELECT task_id, traversal_fingerprint, packet_json, execution_outcome
        FROM tmcp_traversal_receipts
        WHERE id = ?
        """,
        (receipt_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "implementation"
    assert row[1] == packet["traversal_fingerprint"]
    assert json.loads(row[2])["entry_node"] == "@task:implementation"
    assert row[3] == "pending"


def test_compile_tmcp_packet_promotes_repeated_successful_fingerprint(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")
    conn = sqlite3.connect(":memory:")
    ensure_tmcp_schema(conn)
    seed_packet = compile_tmcp_packet(
        objective="Implement the feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
    )
    seed_packet["token_estimates"] = {
        **seed_packet["token_estimates"],
        "estimated_token_delta": 120,
    }
    for index in range(3):
        persist_tmcp_traversal_receipt(
            conn,
            packet=seed_packet,
            run_id=f"run-{index}",
            invocation_id=f"invoke-{index}",
            session_id=f"session-{index}",
            execution_outcome="completed",
            validation_evidence=["scope_check passed"],
        )

    packet = compile_tmcp_packet(
        objective="Implement another feature and run tests",
        project_path="/tmp/project",
        skills_library_path=library,
        receipt_conn=conn,
    )

    assert packet["shortcut_candidate"]["matched"] is True
    assert packet["shortcut_candidate"]["status"] == "active"
    assert packet["shortcut_candidate"]["usable_as_default"] is True
    assert packet["shortcut_candidate"]["promotion_stats"]["successful_count"] == 3
    assert packet["entry_node"].startswith("@shortcut:implementation:")
    assert packet["selected_nodes"][0] == packet["entry_node"]


def test_compile_tmcp_packet_can_cross_into_registered_portable_namespace(tmp_path: Path) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Make this generated SaaS dashboard feel polished instead of generic shadcn",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert packet["task_id"] == "visual_polish"
    assert "@namespace:portable_dev_process/@task:visual_polish" in packet["selected_nodes"]
    assert (
        "@namespace:portable_dev_process/@module:visual_polish_system"
        in packet["selected_nodes"]
    )
    assert (
        "@namespace:portable_dev_process/@module:enterprise_saas_visual_polish"
        in packet["selected_nodes"]
    )
    assert packet["registry_overlay"]["matched"] is True
    assert packet["registry_overlay"]["namespaces"][0]["namespace"] == "portable_dev_process"
    assert "Namespace portable_dev_process task visual_polish" in packet["packet_markdown"]


def test_compile_tmcp_packet_selects_tenure_branch_only_when_intent_matches(
    tmp_path: Path,
) -> None:
    library = _seed_tmcp_library(tmp_path / "skills-library")

    packet = compile_tmcp_packet(
        objective="Apply the Tenure visual polish system to this SOP search screen",
        project_path="/tmp/project",
        skills_library_path=library,
    )

    assert (
        "@namespace:portable_dev_process/@branch:tenure_visual_identity"
        in packet["selected_nodes"]
    )
    namespace = packet["registry_overlay"]["namespaces"][0]
    assert namespace["selected_branch"] == "tenure_visual_identity"
