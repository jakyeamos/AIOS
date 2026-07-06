from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.notebooklm_synthesis import (  # noqa: E402
    NotebookLMBackendReadiness,
    NotebookLMCLIAdapter,
    NotebookLMCommandResult,
    NotebookLMMCPAdapter,
    SourceCandidate,
    build_source_bundle,
    check_notebooklm_backend_readiness,
    classify_notebooklm_route,
    export_source_bundle_for_notebooklm,
    load_notebooklm_backend_spec,
    notebooklm_live_use_warnings,
    notebooklm_staging_note_template,
    notebooklm_tool_plan_for_mode,
)


def test_source_of_truth_memory_lookup_stays_local() -> None:
    decision = classify_notebooklm_route("What did I decide about TMCP shortcut skills?")

    assert decision.route_kind == "source_of_truth_memory"
    assert decision.use_notebooklm is False
    assert (
        decision.reason == "Source-of-truth memory lookups should use canonical local memory first."
    )


def test_local_operational_memory_stays_local() -> None:
    decision = classify_notebooklm_route(
        "Resume the last agent session and inspect the previous tool failures."
    )

    assert decision.route_kind == "local_operational_memory"
    assert decision.use_notebooklm is False
    assert decision.reason == "Raw session state, telemetry, and tool traces stay local."


def test_bounded_source_synthesis_uses_notebooklm() -> None:
    decision = classify_notebooklm_route(
        "Compare these 12 uploaded AI skill docs and produce a synthesis report."
    )

    assert decision.route_kind == "notebooklm_mcp"
    assert decision.use_notebooklm is True
    assert decision.mode == "bounded_source_synthesis"


def test_existing_tmcp_plus_uploaded_packet_routes_local_first() -> None:
    decision = classify_notebooklm_route(
        "Use my existing TMCP notes and this uploaded research packet to propose a new "
        "retrieval policy."
    )

    assert decision.route_kind == "local_first_notebooklm_second"
    assert decision.route_steps == (
        "local/TMCP first",
        "NotebookLM MCP second",
        "stage synthesis output",
    )
    assert decision.local_retrieval_first is True


def test_code_search_does_not_use_notebooklm() -> None:
    decision = classify_notebooklm_route("Search the whole repo for broken imports.")

    assert decision.route_kind == "code_search_filesystem"
    assert decision.use_notebooklm is False


def test_connection_discovery_uses_local_first_notebooklm_second() -> None:
    decision = classify_notebooklm_route(
        "Find hidden connections across my AIOS memory notes and suggest what should become "
        "reusable modules."
    )

    assert decision.route_kind == "local_first_notebooklm_second"
    assert decision.use_notebooklm is True
    assert decision.mode == "tmcp_module_discovery"
    assert decision.stage_output is True


def test_learning_opportunity_detection_routes_to_staged_synthesis() -> None:
    decision = classify_notebooklm_route(
        "Based on my recent notes, what should I learn next to improve AIOS?"
    )

    assert decision.mode == "learning_opportunity_detection"
    assert decision.route_steps[-1] == "stage learning path"


def test_contradiction_detection_routes_to_staged_drift_report() -> None:
    decision = classify_notebooklm_route(
        "Compare my older AIOS architecture notes with the current TMCP plan and find what is outdated."
    )

    assert decision.mode == "contradiction_drift_detection"
    assert decision.route_steps[-1] == "stage drift report"


def test_whole_vault_request_is_rejected() -> None:
    decision = classify_notebooklm_route(
        "Send my entire second brain to NotebookLM and organize it."
    )

    assert decision.route_kind == "reject_unbounded_notebooklm"
    assert decision.use_notebooklm is False
    assert decision.reject_reason == "unbounded_source_bundle"


def test_source_bundle_filters_sensitive_raw_and_excess_sources() -> None:
    candidates = [
        SourceCandidate(path="notes/a.md", title="A", source_type="markdown"),
        SourceCandidate(path="logs/session.log", title="Session", source_type="log"),
        SourceCandidate(
            path="notes/secret.md",
            title="Secret",
            source_type="markdown",
            sensitivity_class="secret",
        ),
        SourceCandidate(path="notes/b.md", title="B", source_type="markdown"),
    ]

    bundle = build_source_bundle(
        task="connection discovery",
        route_reason="relationships across selected notes",
        candidates=candidates,
        max_sources=1,
    )

    assert [source.path for source in bundle.sources] == ["notes/a.md"]
    assert [source.exclusion_reason for source in bundle.excluded_sources] == [
        "raw_operational_or_repo_metadata_path",
        "disallowed_sensitivity_class:secret",
        "source_bundle_limit_reached",
    ]


def test_unavailable_adapter_fails_safely_with_provenance() -> None:
    bundle = build_source_bundle(
        task="brief selected notes",
        route_reason="bounded synthesis requested",
        candidates=[SourceCandidate(path="notes/a.md", title="A", source_type="markdown")],
    )
    spec = load_notebooklm_backend_spec()
    readiness = NotebookLMBackendReadiness(
        backend_key=spec.key,
        available=False,
        missing_executables=("nlm",),
        required_tools=spec.required_tools,
        mcp_tool_probe=spec.mcp_tool_probe,
        auth_check_command=spec.recommended_auth_check,
        warnings=("missing_notebooklm_backend_executables",),
    )

    result = NotebookLMMCPAdapter(backend_spec=spec, readiness=readiness).synthesize(
        mode="bounded_source_synthesis",
        query="Summarize these notes.",
        source_bundle=bundle,
    )

    assert result.status == "skipped_unavailable"
    assert result.provenance.source_system == "notebooklm_mcp"
    assert result.provenance.source_bundle_id == bundle.bundle_id
    assert result.warnings[0] == "notebooklm_mcp_unavailable"


def test_staging_template_keeps_promotion_review_explicit() -> None:
    template = notebooklm_staging_note_template("AIOS retrieval policy")

    assert "## Recommended Promotion Target" in template
    assert "- [ ] Obsidian" in template
    assert "- [ ] TMCP" in template
    assert "## Provenance" in template


def test_jacob_bd_backend_contract_loads_from_registry() -> None:
    spec = load_notebooklm_backend_spec()

    assert spec.key == "jacob_bd_notebooklm_mcp_cli"
    assert spec.lifecycle_state == "experimental"
    assert spec.cli_command == "nlm"
    assert spec.mcp_command == "notebooklm-mcp"
    assert spec.required_tools == (
        "server_info",
        "notebook_create",
        "source_add",
        "notebook_query",
    )
    assert (
        "Uses undocumented NotebookLM internal APIs according to upstream README."
        in spec.security_notes
    )


def test_notebooklm_mode_tool_plan_maps_aios_modes_to_mcp_tools() -> None:
    spec = load_notebooklm_backend_spec()

    assert notebooklm_tool_plan_for_mode("bounded_source_synthesis", spec) == (
        "notebook_create",
        "source_add",
        "notebook_query",
    )
    assert notebooklm_tool_plan_for_mode("briefing_digest", spec) == (
        "notebook_create",
        "source_add",
        "studio_create",
    )


def test_backend_readiness_reports_missing_executables_without_auth_side_effects() -> None:
    spec = load_notebooklm_backend_spec()

    readiness = check_notebooklm_backend_readiness(spec)

    assert readiness.backend_key == "jacob_bd_notebooklm_mcp_cli"
    assert readiness.required_tools == spec.required_tools
    assert readiness.mcp_tool_probe == "server_info"
    assert readiness.auth_check_command == ("nlm", "login", "--check")
    assert readiness.available == (readiness.missing_executables == ())


def test_adapter_uses_backend_readiness_warnings_when_skipped() -> None:
    bundle = build_source_bundle(
        task="brief selected notes",
        route_reason="bounded synthesis requested",
        candidates=[SourceCandidate(path="notes/a.md", title="A", source_type="markdown")],
    )
    spec = load_notebooklm_backend_spec()
    readiness = NotebookLMBackendReadiness(
        backend_key=spec.key,
        available=False,
        missing_executables=("nlm", "notebooklm-mcp"),
        required_tools=spec.required_tools,
        mcp_tool_probe=spec.mcp_tool_probe,
        auth_check_command=spec.recommended_auth_check,
        warnings=("missing_notebooklm_backend_executables",),
    )

    result = NotebookLMMCPAdapter(backend_spec=spec, readiness=readiness).synthesize(
        mode="briefing_digest",
        query="Create a briefing.",
        source_bundle=bundle,
    )

    assert result.status == "skipped_unavailable"
    assert result.warnings == (
        "notebooklm_mcp_unavailable",
        "missing_notebooklm_backend_executables",
    )


def test_cli_adapter_runs_guarded_notebook_create_add_sources_and_query() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(args: tuple[str, ...], _timeout: float) -> NotebookLMCommandResult:
        calls.append(args)
        if args == ("nlm", "login", "--check"):
            return NotebookLMCommandResult(args=args, returncode=0, stdout="authenticated")
        if args[:3] == ("nlm", "notebook", "create"):
            return NotebookLMCommandResult(args=args, returncode=0, stdout="notebook-123\n")
        if args[:3] == ("nlm", "source", "add"):
            return NotebookLMCommandResult(args=args, returncode=0, stdout="source added")
        if args[:3] == ("nlm", "notebook", "query"):
            return NotebookLMCommandResult(
                args=args, returncode=0, stdout="Answer\nSource: notes/a.md"
            )
        return NotebookLMCommandResult(args=args, returncode=1, stderr="unexpected command")

    spec = load_notebooklm_backend_spec()
    readiness = NotebookLMBackendReadiness(
        backend_key=spec.key,
        available=True,
        missing_executables=(),
        required_tools=spec.required_tools,
        mcp_tool_probe=spec.mcp_tool_probe,
        auth_check_command=spec.recommended_auth_check,
    )
    bundle = build_source_bundle(
        task="brief selected notes",
        route_reason="bounded synthesis requested",
        candidates=[SourceCandidate(path="notes/a.md", title="A", source_type="markdown")],
    )

    result = NotebookLMCLIAdapter(
        backend_spec=spec,
        readiness=readiness,
        runner=fake_runner,
    ).synthesize(
        mode="bounded_source_synthesis",
        query="Summarize these notes.",
        source_bundle=bundle,
    )

    assert result.status == "completed"
    assert result.answer == "Answer\nSource: notes/a.md"
    assert result.citations == ("Source: notes/a.md",)
    assert calls == [
        ("nlm", "login", "--check"),
        ("nlm", "notebook", "create", "AIOS brief selected notes", "--quiet"),
        ("nlm", "source", "add", "notebook-123", "--file", "notes/a.md", "--wait"),
        ("nlm", "notebook", "query", "notebook-123", "Summarize these notes."),
    ]


def test_cli_adapter_fails_closed_when_auth_check_fails() -> None:
    def fake_runner(args: tuple[str, ...], _timeout: float) -> NotebookLMCommandResult:
        return NotebookLMCommandResult(
            args=args,
            returncode=1,
            stdout="",
            stderr="not authenticated",
        )

    spec = load_notebooklm_backend_spec()
    readiness = NotebookLMBackendReadiness(
        backend_key=spec.key,
        available=True,
        missing_executables=(),
        required_tools=spec.required_tools,
        mcp_tool_probe=spec.mcp_tool_probe,
        auth_check_command=spec.recommended_auth_check,
    )
    bundle = build_source_bundle(
        task="brief selected notes",
        route_reason="bounded synthesis requested",
        candidates=[SourceCandidate(path="notes/a.md", title="A", source_type="markdown")],
    )

    result = NotebookLMCLIAdapter(
        backend_spec=spec,
        readiness=readiness,
        runner=fake_runner,
    ).synthesize(
        mode="bounded_source_synthesis",
        query="Summarize these notes.",
        source_bundle=bundle,
    )

    assert result.status == "skipped_unavailable"
    assert result.warnings == ("notebooklm_cli_auth_unavailable", "not authenticated")


def test_live_use_warnings_block_empty_or_excluded_bundles() -> None:
    bundle = build_source_bundle(
        task="empty",
        route_reason="no candidates",
        candidates=[],
    )

    assert notebooklm_live_use_warnings(bundle) == ("empty_source_bundle",)

    bundle_with_exclusion = build_source_bundle(
        task="excluded",
        route_reason="has sensitive candidate",
        candidates=[
            SourceCandidate(path="notes/a.md", title="A", source_type="markdown"),
            SourceCandidate(
                path="notes/secret.md",
                title="Secret",
                source_type="markdown",
                sensitivity_class="secret",
            ),
        ],
    )

    assert notebooklm_live_use_warnings(bundle_with_exclusion) == (
        "source_bundle_has_exclusions_review_required",
    )


def test_export_source_bundle_for_manual_fallback(tmp_path: Path) -> None:
    bundle = build_source_bundle(
        task="brief selected notes",
        route_reason="bounded synthesis requested",
        candidates=[SourceCandidate(path="notes/a.md", title="A", source_type="markdown")],
    )

    bundle_dir = export_source_bundle_for_notebooklm(bundle, output_root=tmp_path)

    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "prompt.md").read_text(encoding="utf-8").startswith("# NotebookLM Prompt")
    assert "notes/a.md" in (bundle_dir / "upload-instructions.md").read_text(encoding="utf-8")
