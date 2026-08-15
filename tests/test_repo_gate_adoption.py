from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.repo_gate_adoption import (  # noqa: E402
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
    build_tmcp_expert_enrichment,
    gate_adoption_output_dir,
    scan_repo_gate_facts,
    validate_gate_matrix,
    validate_gate_rollout_plan,
    validate_repo_scan,
    validate_rubric_pack,
    validate_tmcp_expert_enrichment,
    write_adoption_doc_quality_report,
    write_gate_adoption_artifacts,
)


def _write_repo_fixture(repo: Path) -> None:
    (repo / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "format": "prettier --check .",
                    "install:check": "pnpm install --frozen-lockfile",
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                    "build": "vite build",
                    "dead-code": "knip",
                    "secret-scan": "detect-secrets scan",
                    "dependency-security": "pnpm audit",
                    "package": "pnpm package",
                    "validate": "python scripts/validate.py",
                    "mobile-release": "xcodebuild test",
                    "e2e:smoke": "playwright test --grep @smoke",
                    "runtime:smoke": "playwright test --grep @runtime-smoke",
                    "pre-pr": "pnpm pre-pr-readiness",
                    "release:check": "pnpm deploy:preview:watch",
                    "thermo": "pnpm thermo-nuclear-simplification",
                    "data:validate": "python scripts/validate_data.py",
                    "healthcheck": "python scripts/healthcheck.py",
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "tsconfig.json").write_text("{}", encoding="utf-8")
    (repo / "knip.json").write_text("{}", encoding="utf-8")
    (repo / ".pre-cr.json").write_text("{}", encoding="utf-8")
    (repo / ".aios-quality-gate.json").write_text(
        json.dumps(
            {
                "projectId": "portfolio",
                "preCommitGates": ["test_quality", "pre_cr"],
                "fullGates": [
                    "architecture",
                    "anti_slop",
                    "complexity_budget",
                    "install",
                    "secret_scan",
                    "dependency_security",
                    "package",
                    "validation",
                    "mobile_release",
                    "e2e_smoke",
                    "runtime_smoke",
                    "pre_pr_readiness",
                    "release_rollback_readiness",
                    "thermo_nuclear_simplification",
                    "data_state_integrity",
                    "observability_debuggability",
                ],
            }
        ),
        encoding="utf-8",
    )
    (repo / ".tracker").mkdir()
    (repo / ".tracker" / "PROJECT_TRUTH.md").write_text("# Truth\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "release.md").write_text("# Release\n", encoding="utf-8")
    (repo / "docs" / "rollback.md").write_text("# Rollback\n", encoding="utf-8")
    (repo / "docs" / "observability.md").write_text("# Observability\n", encoding="utf-8")
    (repo / "docs" / "debugging.md").write_text("# Debugging\n", encoding="utf-8")
    (repo / "prisma").mkdir()
    (repo / "prisma" / "schema.prisma").write_text("// schema\n", encoding="utf-8")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")


def test_scan_matrix_and_rollout_plan_are_valid(tmp_path: Path) -> None:
    _write_repo_fixture(tmp_path)

    scan = scan_repo_gate_facts(tmp_path, run_id="gate-run-1")
    matrix = build_gate_matrix(scan=scan, run_id="gate-run-1")
    tmcp_enrichment = build_tmcp_expert_enrichment(
        scan=scan,
        gate_matrix=matrix,
        run_id="gate-run-1",
        skills_library_path=tmp_path / "missing-skills-library",
    )
    rubric_pack = build_rubric_pack(
        scan=scan,
        gate_matrix=matrix,
        run_id="gate-run-1",
        tmcp_enrichment=tmcp_enrichment,
    )
    rollout = build_gate_rollout_plan(
        gate_matrix=matrix,
        run_id="gate-run-1",
        rubric_pack=rubric_pack,
    )

    assert scan["schema"] == REPO_SCAN_SCHEMA
    assert scan["classification"]["profile_status"] == "matched"
    assert scan["quality_profile"]["repo_class"] == "production_public_web_app"
    assert "e2e_smoke" in scan["quality_profile"]["required_gates"]
    assert any(
        item.startswith("quality-pipeline:install:") for item in scan["gate_evidence"]["install"]
    )
    assert any(item.startswith("quality-pipeline:test:") for item in scan["gate_evidence"]["tests"])
    assert scan["visual_proof_route"]["route"] == "local_web_launch_browser_visual"
    assert matrix["schema"] == GATE_MATRIX_SCHEMA
    assert matrix["quality_profile"]["project_id"] == "portfolio"
    assert tmcp_enrichment["schema"] == TMCP_EXPERT_ENRICHMENT_SCHEMA
    assert tmcp_enrichment["status"] == "insufficient_source"
    assert tmcp_enrichment["fallback"] == "aios_standard_rubric"
    assert rubric_pack["schema"] == RUBRIC_PACK_SCHEMA
    assert rollout["schema"] == GATE_ROLLOUT_PLAN_SCHEMA
    assert {gate["id"] for gate in matrix["gates"]} == set(CORE_GATE_IDS)
    by_gate = {gate["id"]: gate for gate in matrix["gates"]}
    assert by_gate["install"]["quality_profile_required"] is True
    assert (
        by_gate["install"]["quality_profile_command"]["command"] == "pnpm install --frozen-lockfile"
    )
    assert by_gate["tests"]["quality_profile_gate_key"] == "test"
    assert by_gate["tests"]["enforcement"] == "hard"
    assert by_gate["pre_cr"]["enforcement"] == "hard"
    assert by_gate["anti_slop"]["enforcement"] == "hard"
    assert by_gate["complexity_budget"]["label"] == "Complexity / Big-O Budget"
    assert by_gate["complexity_budget"]["enforcement"] == "hard"
    expected_hard_gates = {
        "install",
        "secret_scan",
        "dependency_security",
        "package",
        "validation",
        "mobile_release",
        "e2e_smoke",
        "runtime_smoke",
        "pre_pr_readiness",
        "release_rollback_readiness",
        "thermo_nuclear_simplification",
        "data_state_integrity",
        "observability_debuggability",
    }
    assert expected_hard_gates <= set(by_gate)
    assert all(by_gate[gate_id]["enforcement"] == "hard" for gate_id in expected_hard_gates)
    assert "repo_truth" not in by_gate
    assert validate_repo_scan(scan)["passed"] is True
    assert validate_gate_matrix(matrix)["passed"] is True
    assert validate_tmcp_expert_enrichment(tmcp_enrichment)["passed"] is True
    assert validate_rubric_pack(rubric_pack)["passed"] is True
    assert validate_gate_rollout_plan(rollout)["passed"] is True
    assert {rubric["id"] for rubric in rubric_pack["broad_rubrics"]} == set(BROAD_RUBRIC_IDS)
    assert all(rubric["known_evidence"] for rubric in rubric_pack["broad_rubrics"])
    assert all(rubric["root_causes"] for rubric in rubric_pack["broad_rubrics"])
    assert len(rubric_pack["gate_specific_rubrics"]) == len(CORE_GATE_IDS)
    assert all(rubric["known_evidence"] for rubric in rubric_pack["gate_specific_rubrics"])
    assert all(rubric["root_causes"] for rubric in rubric_pack["gate_specific_rubrics"])
    install_rubric = next(
        rubric for rubric in rubric_pack["gate_specific_rubrics"] if rubric["id"] == "gate_install"
    )
    assert install_rubric["quality_profile_required"] is True
    assert install_rubric["quality_profile_command"]["command"] == "pnpm install --frozen-lockfile"
    anti_slop = next(
        rubric
        for rubric in rubric_pack["broad_rubrics"]
        if rubric["id"] == "anti_slop_product_quality"
    )
    assert "passing anti-slop command" in anti_slop["command_gate_caveat"]
    visual_runtime = next(
        rubric
        for rubric in rubric_pack["broad_rubrics"]
        if rubric["id"] == "ui_visual_runtime_verification"
    )
    assert "TMCP UI rubric review" in visual_runtime["command_gate_caveat"]
    assert any("Xcode simulator" in item for item in visual_runtime["required_evidence"])
    assert visual_runtime["visual_proof_route"]["route"] == "local_web_launch_browser_visual"
    complexity = next(
        rubric
        for rubric in rubric_pack["broad_rubrics"]
        if rubric["id"] == "complexity_simplification"
    )
    assert "Thermo/simplifier skills are expert audit engines" in complexity["command_gate_caveat"]
    assert any("runtime complexity risks" in item for item in complexity["required_evidence"])
    assert len(rubric_pack["broad_rubrics"]) == 15
    for gate_id in {
        "runtime_smoke",
        "release_rollback_readiness",
        "data_state_integrity",
        "observability_debuggability",
    }:
        assert by_gate[gate_id]["status"] == "present"
        assert by_gate[gate_id]["enforcement"] == "hard"
    assert rollout["phase_scope_policy"] == "repo_local_gate_scoped"
    assert rollout["phase_owner"] == "target_repo"
    assert rollout["aios_role"] == "portfolio_coordinator_and_evidence_ledger"
    assert rollout["default_granularity"] == "one_phase_per_gate"
    assert rollout["cluster_policy"]["default"] == "do_not_cluster"
    assert rollout["phases"][0]["id"] == "repo-local-gate-install"
    assert all(phase["phase_location"] == "target_repo" for phase in rollout["phases"])
    assert all("source_gate_ids" in phase for phase in rollout["phases"])
    assert not any(phase["id"] == "phase-0-rubric-audit-pack" for phase in rollout["phases"])
    source_gate_ids = {
        gate_id for phase in rollout["phases"] for gate_id in phase.get("source_gate_ids", [])
    }
    assert set(CORE_GATE_IDS) <= source_gate_ids
    lint_phase = next(phase for phase in rollout["phases"] if phase["source_gate_ids"] == ["lint"])
    tests_phase = next(
        phase for phase in rollout["phases"] if phase["source_gate_ids"] == ["tests"]
    )
    final_phase = next(
        phase for phase in rollout["phases"] if phase["phase_type"] == "final_certification"
    )
    assert lint_phase["strict_clearance_required"] is True
    assert tests_phase["strict_clearance_required"] is True
    assert any("inherited baseline failures" in action for action in lint_phase["actions"])
    assert any("full repo `tests` command" in action for action in tests_phase["actions"])
    assert any("full lint and full test" in action for action in final_phase["actions"])
    assert any(
        "No repo is adoption_ready" in criterion for criterion in final_phase["acceptance_criteria"]
    )


def test_write_gate_adoption_artifacts(tmp_path: Path) -> None:
    _write_repo_fixture(tmp_path)
    (tmp_path / ".git" / "info").mkdir(parents=True)
    scan = scan_repo_gate_facts(tmp_path, run_id="gate-run-1")
    matrix = build_gate_matrix(scan=scan, run_id="gate-run-1")
    tmcp_enrichment = build_tmcp_expert_enrichment(
        scan=scan,
        gate_matrix=matrix,
        run_id="gate-run-1",
        skills_library_path=tmp_path / "missing-skills-library",
    )
    rubric_pack = build_rubric_pack(
        scan=scan,
        gate_matrix=matrix,
        run_id="gate-run-1",
        tmcp_enrichment=tmcp_enrichment,
    )
    rollout = build_gate_rollout_plan(
        gate_matrix=matrix,
        run_id="gate-run-1",
        rubric_pack=rubric_pack,
    )

    output_dir = gate_adoption_output_dir(tmp_path, "gate-run-1")
    paths = write_gate_adoption_artifacts(
        output_dir=output_dir,
        repo_root=tmp_path,
        repo_scan=scan,
        gate_matrix=matrix,
        rubric_pack=rubric_pack,
        rollout_plan=rollout,
    )

    assert paths["repo_scan_json"].exists()
    assert output_dir == tmp_path / AIOS_BACKFILL_DIR_NAME / "gate-adoption" / "gate-run-1"
    assert tmp_path / AIOS_BACKFILL_DIR_NAME in paths["repo_scan_json"].parents
    assert not (tmp_path / ".git" / "info" / "exclude").exists()
    first_broad_rubric = rubric_pack["broad_rubrics"][0]
    assert first_broad_rubric["audit_doc_path"].startswith(
        f"{AIOS_BACKFILL_DIR_NAME}/gate-adoption/gate-run-1/rubrics/"
    )
    assert (
        paths["gate_matrix_markdown"].read_text(encoding="utf-8").startswith("# Repo Gate Matrix")
    )
    assert (
        json.loads(paths["tmcp_expert_enrichment_json"].read_text(encoding="utf-8"))["schema"]
        == TMCP_EXPERT_ENRICHMENT_SCHEMA
    )
    assert (
        json.loads(paths["rubric_pack_json"].read_text(encoding="utf-8"))["schema"]
        == RUBRIC_PACK_SCHEMA
    )
    assert "Broad Quality Rubrics" in paths["rubric_pack_markdown"].read_text(encoding="utf-8")
    manifest = json.loads(paths["rubric_detail_manifest_json"].read_text(encoding="utf-8"))
    expected_rubric_ids = {
        *(rubric["id"] for rubric in rubric_pack["broad_rubrics"]),
        *(rubric["id"] for rubric in rubric_pack["gate_specific_rubrics"]),
    }
    assert manifest["schema"] == RUBRIC_DETAIL_MANIFEST_SCHEMA
    assert manifest["rubric_count"] == len(expected_rubric_ids)
    assert manifest["document_count"] == len(expected_rubric_ids) * 4
    assert paths["rubric_docs_dir"].exists()
    assert output_dir in paths["rubric_docs_dir"].parents
    assert {row["rubric_id"] for row in manifest["documents"]} == expected_rubric_ids
    for row in manifest["documents"]:
        audit_markdown_path = Path(row["audit_markdown_path"])
        audit_json_path = Path(row["audit_json_path"])
        implementation_markdown_path = Path(row["implementation_markdown_path"])
        implementation_json_path = Path(row["implementation_json_path"])
        assert tmp_path / AIOS_BACKFILL_DIR_NAME in audit_markdown_path.parents
        assert audit_markdown_path.exists()
        assert audit_json_path.exists()
        assert implementation_markdown_path.exists()
        assert implementation_json_path.exists()
    first_manifest_row = manifest["documents"][0]
    lint_manifest_row = next(
        row for row in manifest["documents"] if row["rubric_id"] == "gate_lint"
    )
    audit_json = json.loads(Path(first_manifest_row["audit_json_path"]).read_text(encoding="utf-8"))
    implementation_json = json.loads(
        Path(first_manifest_row["implementation_json_path"]).read_text(encoding="utf-8")
    )
    lint_implementation_json = json.loads(
        Path(lint_manifest_row["implementation_json_path"]).read_text(encoding="utf-8")
    )
    audit_markdown = Path(first_manifest_row["audit_markdown_path"]).read_text(encoding="utf-8")
    implementation_markdown = Path(first_manifest_row["implementation_markdown_path"]).read_text(
        encoding="utf-8"
    )
    assert audit_json["schema"] == RUBRIC_AUDIT_SCHEMA
    assert implementation_json["schema"] == RUBRIC_IMPLEMENTATION_SCHEMA
    assert any(
        "full repo `lint` command" in step
        for step in lint_implementation_json["implementation_steps"]
    )
    assert any(
        "not adoption certification proof" in step
        for step in lint_implementation_json["implementation_steps"]
    )
    for heading in {
        "## Current Evidence Found",
        "## Blockers",
        "## Missing Proof",
        "## Validation Commands",
    }:
        assert heading in audit_markdown
    for heading in {
        "## Root Causes",
        "## Likely Affected Files Or Scripts",
        "## Execution Risks",
        "## Verification Commands",
        "## Phase Scope",
    }:
        assert heading in implementation_markdown
    assert (
        json.loads(paths["rollout_plan_json"].read_text(encoding="utf-8"))["schema"]
        == GATE_ROLLOUT_PLAN_SCHEMA
    )
    rollout_markdown = paths["rollout_plan_markdown"].read_text(encoding="utf-8")
    assert "Phase owner: `target_repo`" in rollout_markdown
    assert "repo-local-gate-install" in rollout_markdown
    assert "Generate Scoped GSD Phases" not in rollout_markdown
    quality_paths = write_adoption_doc_quality_report(output_dir)
    quality_report = json.loads(
        quality_paths["adoption_doc_quality_json"].read_text(encoding="utf-8")
    )
    assert quality_report["schema"] == ADOPTION_DOC_QUALITY_SCHEMA
    assert quality_report["passed"] is True
    assert quality_report["structurally_valid"] is True
    assert quality_report["ready_for_phase_planning"] is True
    assert quality_report["ready_for_execution"] is True
    assert quality_report["warning_count"] == 0
    assert quality_report["phase_planning_blocker_count"] == 0
    assert Path(quality_paths["adoption_doc_quality_markdown"]).exists()


def test_bidcamp_profile_skips_optional_gates_and_generates_setup_actions(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "BidCamp"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                    "build": "vite build",
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "tsconfig.json").write_text("{}", encoding="utf-8")
    (repo / ".pre-cr.json").write_text("{}", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "aios-quality.yml").write_text(
        "name: aios\n",
        encoding="utf-8",
    )

    scan = scan_repo_gate_facts(repo, run_id="bidcamp-run")
    matrix = build_gate_matrix(scan=scan, run_id="bidcamp-run")
    rubric_pack = build_rubric_pack(scan=scan, gate_matrix=matrix, run_id="bidcamp-run")

    by_gate = {gate["id"]: gate for gate in matrix["gates"]}
    assert by_gate["structural_scan"]["status"] == "present"
    assert by_gate["structural_scan"]["quality_profile_gate_key"] == "architecture"
    assert by_gate["mobile_release"]["status"] == "skipped"
    assert by_gate["local_hook"]["status"] == "skipped"
    assert by_gate["local_quality_contract"]["status"] == "absent"
    assert matrix["summary"]["skipped"] == 2

    by_rubric = {rubric["id"]: rubric for rubric in rubric_pack["gate_specific_rubrics"]}
    assert any(
        "pnpm exec prettier --check ." in action
        for action in by_rubric["gate_formatter"]["setup_actions"]
    )
    assert any(
        "pnpm exec knip" in action for action in by_rubric["gate_dead_code"]["setup_actions"]
    )
    assert any(
        ".aios-quality-gate.json" in action
        for action in by_rubric["gate_local_quality_contract"]["setup_actions"]
    )
    assert by_rubric["gate_mobile_release"]["accepted_exceptions"]
    assert by_rubric["gate_local_hook"]["known_evidence"][0].startswith("adoption-skip:")


def test_gate_matrix_validation_rejects_missing_core_gate() -> None:
    result = validate_gate_matrix(
        {
            "schema": GATE_MATRIX_SCHEMA,
            "run_id": "gate-run-1",
            "gates": [{"id": "lint"}],
        }
    )

    assert result["passed"] is False
    assert "Gate matrix missing core gates" in result["issues"][0]


def test_rubric_pack_validation_rejects_missing_broad_rubrics() -> None:
    result = validate_rubric_pack(
        {
            "schema": RUBRIC_PACK_SCHEMA,
            "run_id": "gate-run-1",
            "broad_rubrics": [],
            "gate_specific_rubrics": [{"id": "gate_lint"}],
        }
    )

    assert result["passed"] is False
    assert "broad rubrics" in result["issues"][0]


def test_tmcp_expert_enrichment_validation_requires_fallback_for_insufficient_source() -> None:
    result = validate_tmcp_expert_enrichment(
        {
            "schema": TMCP_EXPERT_ENRICHMENT_SCHEMA,
            "run_id": "gate-run-1",
            "status": "insufficient_source",
            "fallback": None,
        }
    )

    assert result["passed"] is False
    assert "fall back" in result["issues"][0]


def test_gate_rollout_validation_rejects_aios_owned_or_unexplained_cluster() -> None:
    result = validate_gate_rollout_plan(
        {
            "schema": GATE_ROLLOUT_PLAN_SCHEMA,
            "phase_scope_policy": "repo_local_gate_scoped",
            "phase_owner": "target_repo",
            "aios_role": "portfolio_coordinator_and_evidence_ledger",
            "phases": [
                {
                    "id": "bad-aios-phase",
                    "phase_type": "gate_specific_remediation",
                    "phase_location": "aios",
                    "source_gate_ids": ["complexity_budget"],
                    "verification": ["verify"],
                },
                {
                    "id": "bad-cluster",
                    "phase_type": "gate_specific_remediation",
                    "phase_location": "target_repo",
                    "source_gate_ids": [
                        "complexity_budget",
                        "thermo_nuclear_simplification",
                    ],
                    "verification": ["verify"],
                },
                {
                    "id": "repo-local-final-adoption-certification",
                    "phase_type": "final_certification",
                    "phase_location": "target_repo",
                    "source_gate_ids": [],
                    "verification": ["verify"],
                },
            ],
        }
    )

    assert result["passed"] is False
    assert any("target repo" in issue for issue in result["issues"])
    assert any(
        "clusters gates without an explicit rationale" in issue for issue in result["issues"]
    )
