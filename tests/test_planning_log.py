from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution_symmetric_planner import generate_execution_symmetric_plan  # noqa: E402
from services.planning_context import create_planning_context  # noqa: E402
from services.planning_log import (  # noqa: E402
    build_plan_log_entry,
    build_plan_log_from_execution_plan,
    load_plan_logs,
    managed_run_tmcp_contract_metadata,
    record_plan_log,
)


def test_plan_log_round_trips_jsonl_with_comparison_axes(tmp_path: Path) -> None:
    context = create_planning_context(
        source_invocation="natural_language",
        raw_invocation="Plan a moderate API change",
        workflow="aios",
        phase="planning",
        task_type="api_change",
        complexity="moderate",
        selected_lenses=("interface-contracts", "testing"),
        tmcp_packet_id="packet-1",
        tmcp_receipt_id="receipt-1",
    )
    entry = build_plan_log_entry(
        planning_context=context,
        plan_kind="execution_symmetric",
        route_trigger="auto_routed",
        entry_id="planning-log-test",
        recorded_at="2026-06-23T00:00:00Z",
    )

    log_path = record_plan_log(entry, tmp_path / "planning-events.jsonl")
    loaded = load_plan_logs(log_path)

    assert len(loaded) == 1
    assert loaded[0].id == "planning-log-test"
    assert loaded[0].comparison_axes == {
        "plan_family": "execution_symmetric",
        "workflow_family": "natural_language",
        "invocation_family": "auto_routed",
        "lens_family": "with_selected_lenses",
    }
    assert loaded[0].planning_context.tmcp_receipt_id == "receipt-1"


def test_execution_symmetric_plan_builds_gsd_slash_command_log() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Create the GSD-ready implementation plan",
        source_text="/gsdplanphase 20",
        complexity="complex",
        task_types=("gsd_plan_phase",),
    )

    entry = build_plan_log_from_execution_plan(
        plan=plan,
        source_invocation="slash_command",
        raw_invocation="/gsdplanphase 20",
        task_type="gsd_plan_phase",
        route_trigger="slash_command",
        tmcp_packet_id="packet-gsd",
        tmcp_receipt_id="receipt-gsd",
    )

    assert entry.comparison_axes["workflow_family"] == "gsd_phase"
    assert entry.comparison_axes["invocation_family"] == "slash_command"
    assert entry.planning_context.output_format == "gsd_ready_plan"
    assert entry.planning_context.handoff_target == "gsd"
    assert "executor-readiness" in entry.planning_context.selected_lenses


def test_managed_run_tmcp_contract_requires_packet_and_receipt_for_non_trivial_work() -> None:
    metadata = managed_run_tmcp_contract_metadata(
        complexity="moderate",
        tmcp_packet_id="packet-managed",
        tmcp_receipt_id="receipt-managed",
    )

    assert metadata["tmcp_required"] is True
    assert metadata["tmcp_contract_status"] == "satisfied"


def test_managed_run_tmcp_contract_records_explicit_bypass() -> None:
    metadata = managed_run_tmcp_contract_metadata(
        complexity="complex",
        tmcp_packet_id=None,
        tmcp_receipt_id=None,
        bypass_reason="operator requested no TMCP packet for this dry run",
    )

    assert metadata["tmcp_required"] is True
    assert metadata["tmcp_contract_status"] == "bypassed"
    assert metadata["tmcp_bypass_reason"] == "operator requested no TMCP packet for this dry run"


def test_managed_run_tmcp_contract_rejects_silent_omission() -> None:
    with pytest.raises(ValueError, match="TMCP packet and receipt evidence"):
        managed_run_tmcp_contract_metadata(
            complexity="high_risk",
            tmcp_packet_id=None,
            tmcp_receipt_id=None,
        )


def test_managed_run_tmcp_contract_does_not_require_packet_for_simple_work() -> None:
    metadata = managed_run_tmcp_contract_metadata(
        complexity="simple",
        tmcp_packet_id=None,
        tmcp_receipt_id=None,
    )

    assert metadata["tmcp_required"] is False
    assert metadata["tmcp_contract_status"] == "not_required"
