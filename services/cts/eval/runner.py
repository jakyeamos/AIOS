from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..mcp_server import CTSService
from .scorer import score_set
from .token_benchmark import benchmark_payload_tokens


@dataclass(slots=True)
class EvalCase:
    id: str
    query_type: str
    prompt: dict[str, Any]
    expected: list[str]


def load_cases(cases_dir: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in sorted(cases_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases.append(
            EvalCase(
                id=str(payload["id"]),
                query_type=str(payload["query_type"]),
                prompt=dict(payload.get("prompt", {})),
                expected=list(payload.get("expected", [])),
            )
        )
    return cases


def _extract_labels(query_type: str, response: dict[str, Any]) -> list[str]:
    if query_type == "semantic_search":
        return [row.get("qualified_name", "") for row in response.get("results", [])]
    if query_type == "impact_radius":
        if not response.get("results"):
            return []
        top = response["results"][0]
        return list(top.get("impacted_files", []))
    if query_type == "query_graph":
        labels: list[str] = []
        for row in response.get("results", []):
            if "node" in row:
                labels.append(row["node"].get("qualified_name", ""))
            if "edge" in row:
                labels.append(
                    f"{row['edge'].get('source_qualified', '')}->{row['edge'].get('target_qualified', '')}"
                )
        return labels
    return []


def execute_case(service: CTSService, case: EvalCase) -> dict[str, Any]:
    prompt = dict(case.prompt)
    response: dict[str, Any]
    try:
        if case.query_type == "semantic_search":
            response = service.semantic_search_nodes(**prompt)
        elif case.query_type == "impact_radius":
            response = service.get_impact_radius(**prompt)
        elif case.query_type == "query_graph":
            response = service.query_graph(**prompt)
        elif case.query_type == "architecture_overview":
            response = service.get_architecture_overview(**prompt)
        elif case.query_type == "detect_changes":
            response = service.detect_changes(**prompt)
        elif case.query_type == "minimal_context":
            response = service.get_minimal_context(**prompt)
        else:
            raise ValueError(f"Unsupported case query_type: {case.query_type}")
    except Exception as exc:
        return {
            "id": case.id,
            "query_type": case.query_type,
            "error": str(exc),
            "score": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "task_success": False},
            "token_usage": {"prompt_tokens": 0, "response_tokens": 0, "total_tokens": 0},
            "predicted_count": 0,
            "expected_count": len(case.expected),
            "response_meta": {
                "index_status": None,
                "has_low_confidence_results": None,
                "has_stale_results": None,
                "fallback_used": None,
            },
        }
    predicted = _extract_labels(case.query_type, response)
    score = score_set(predicted, case.expected)
    tokens = benchmark_payload_tokens(prompt, response)
    return {
        "id": case.id,
        "query_type": case.query_type,
        "score": asdict(score),
        "token_usage": asdict(tokens),
        "predicted_count": len(predicted),
        "expected_count": len(case.expected),
        "response_meta": {
            "index_status": response.get("index_status"),
            "has_low_confidence_results": response.get("has_low_confidence_results"),
            "has_stale_results": response.get("has_stale_results"),
            "fallback_used": response.get("fallback_used"),
        },
    }


def run_suite(service: CTSService, cases_dir: Path) -> dict[str, Any]:
    cases = load_cases(cases_dir)
    results = [execute_case(service, case) for case in cases]
    if not results:
        return {"cases": [], "summary": {"count": 0}}
    p = sum(item["score"]["precision"] for item in results) / len(results)
    r = sum(item["score"]["recall"] for item in results) / len(results)
    f1 = sum(item["score"]["f1"] for item in results) / len(results)
    success = sum(1 for item in results if item["score"]["task_success"]) / len(results)
    total_tokens = sum(item["token_usage"]["total_tokens"] for item in results)
    return {
        "cases": results,
        "summary": {
            "count": len(results),
            "avg_precision": round(p, 3),
            "avg_recall": round(r, 3),
            "avg_f1": round(f1, 3),
            "task_success_rate": round(success, 3),
            "total_tokens": total_tokens,
        },
    }
