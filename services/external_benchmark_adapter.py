from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_eval_contract import (
    normalize_external_result as _contract_normalize_external_result,
)
from agent_eval_contract import (
    to_swe_bench_format as _contract_to_swe_bench_format,
)
from agent_eval_contract import (
    to_terminal_bench_format as _contract_to_terminal_bench_format,
)

from services.eval_run_service import FINAL_STATUSES

__all__ = ["normalize_external_result", "to_swe_bench_format", "to_terminal_bench_format"]


def _contract_task(eval_task_dict: Mapping[str, Any]) -> dict[str, Any]:
    # Translate an AIOS eval_tasks row into the field names the
    # agent-eval-contract 0.3.0 EvalTask surface expects.
    task = dict(eval_task_dict)
    task.setdefault("task_id", task.get("id"))
    task.setdefault("repo", task.get("repo_id"))
    task.setdefault("description", task.get("prompt_summary"))
    task.setdefault("start_revision", task.get("start_sha"))
    return task


def to_swe_bench_format(eval_task_dict: Mapping[str, Any]) -> dict[str, Any]:
    return _contract_to_swe_bench_format(_contract_task(eval_task_dict))


def to_terminal_bench_format(eval_task_dict: Mapping[str, Any]) -> dict[str, Any]:
    return _contract_to_terminal_bench_format(_contract_task(eval_task_dict))


def normalize_external_result(
    external_result: Mapping[str, Any],
    *,
    eval_task_id: str,
    harness: str,
    model: str,
) -> dict[str, Any]:
    normalized = _contract_normalize_external_result(
        external_result,
        eval_task_id=eval_task_id,
        harness=harness,
        model=model,
    )
    final_status = (
        normalized.final_status if normalized.final_status in FINAL_STATUSES else "failed"
    )
    return {
        "task_id": normalized.task_id,
        "condition": "external_harness",
        "mode": "external",
        "harness": normalized.harness,
        "model": normalized.model,
        "context_profile": "external_clean_room",
        "final_status": final_status,
        "tests_run": list(normalized.checks),
        "duration_ms": normalized.duration_ms,
    }
