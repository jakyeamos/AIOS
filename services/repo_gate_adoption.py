from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_quality_certifier.core import (
    ADOPTION_DOC_QUALITY_SCHEMA,
    AIOS_BACKFILL_DIR_NAME,
    BROAD_RUBRIC_IDS,
    CORE_GATE_IDS,
    GATE_MATRIX_SCHEMA,
    GATE_ROLLOUT_PLAN_SCHEMA,
    REPO_SCAN_SCHEMA,
    RUBRIC_AUDIT_SCHEMA,
    RUBRIC_DETAIL_MANIFEST_SCHEMA,
    RUBRIC_IMPLEMENTATION_SCHEMA,
    RUBRIC_PACK_SCHEMA,
    TMCP_EXPERT_ENRICHMENT_SCHEMA,
    build_gate_matrix,
    build_gate_rollout_plan,
    build_rubric_pack,
    evaluate_adoption_doc_quality,
    gate_adoption_output_dir,
    render_adoption_doc_quality_markdown,
    render_gate_matrix_markdown,
    render_gate_rollout_markdown,
    render_rubric_audit_markdown,
    render_rubric_detail_manifest_markdown,
    render_rubric_implementation_markdown,
    render_rubric_pack_markdown,
    render_tmcp_expert_enrichment_markdown,
    scan_repo_gate_facts,
    validate_gate_matrix,
    validate_gate_rollout_plan,
    validate_repo_scan,
    validate_rubric_pack,
    validate_tmcp_expert_enrichment,
    write_adoption_doc_quality_report,
    write_gate_adoption_artifacts,
    write_rubric_detail_documents,
)
from repo_quality_certifier.core import (
    build_tmcp_expert_enrichment as _build_tmcp_expert_enrichment,
)
from services.tmcp_runtime import DEFAULT_SKILLS_LIBRARY, compile_tmcp_packet


def build_tmcp_expert_enrichment(
    *,
    scan: dict[str, Any],
    gate_matrix: dict[str, Any],
    run_id: str,
    skills_library_path: Path | None = None,
) -> dict[str, Any]:
    return _build_tmcp_expert_enrichment(
        scan=scan,
        gate_matrix=gate_matrix,
        run_id=run_id,
        skills_library_path=skills_library_path,
        tmcp_compiler=compile_tmcp_packet,
        default_skills_library=DEFAULT_SKILLS_LIBRARY,
        tmcp_domain="aios_internal",
    )


__all__ = [
    "ADOPTION_DOC_QUALITY_SCHEMA",
    "AIOS_BACKFILL_DIR_NAME",
    "BROAD_RUBRIC_IDS",
    "CORE_GATE_IDS",
    "GATE_MATRIX_SCHEMA",
    "GATE_ROLLOUT_PLAN_SCHEMA",
    "REPO_SCAN_SCHEMA",
    "RUBRIC_AUDIT_SCHEMA",
    "RUBRIC_DETAIL_MANIFEST_SCHEMA",
    "RUBRIC_IMPLEMENTATION_SCHEMA",
    "RUBRIC_PACK_SCHEMA",
    "TMCP_EXPERT_ENRICHMENT_SCHEMA",
    "build_gate_matrix",
    "build_gate_rollout_plan",
    "build_rubric_pack",
    "build_tmcp_expert_enrichment",
    "evaluate_adoption_doc_quality",
    "gate_adoption_output_dir",
    "render_adoption_doc_quality_markdown",
    "render_gate_matrix_markdown",
    "render_gate_rollout_markdown",
    "render_rubric_audit_markdown",
    "render_rubric_detail_manifest_markdown",
    "render_rubric_implementation_markdown",
    "render_rubric_pack_markdown",
    "render_tmcp_expert_enrichment_markdown",
    "scan_repo_gate_facts",
    "validate_gate_matrix",
    "validate_gate_rollout_plan",
    "validate_repo_scan",
    "validate_rubric_pack",
    "validate_tmcp_expert_enrichment",
    "write_adoption_doc_quality_report",
    "write_gate_adoption_artifacts",
    "write_rubric_detail_documents",
]
