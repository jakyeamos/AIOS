from __future__ import annotations

from typing import Any

WEIGHTS = {
    "complexity": 0.25,
    "measurability": 0.20,
    "reproducibility": 0.15,
    "aios_relevance": 0.15,
    "learning_value": 0.10,
    "safety": 0.10,
    "benchmark_coverage_need": 0.05,
}
HARD_BLOCKERS = {
    "dirty_repo",
    "secret_risk",
    "no_start_sha",
    "unmeasurable_task",
    "too_small",
    "too_large",
    "private_external_system",
}


def _recommendation(score: float) -> str:
    if score >= 85:
        return "excellent_shadow_candidate"
    if score >= 70:
        return "good_shadow_candidate"
    if score >= 40:
        return "possible_shadow_candidate"
    return "trace_only"


def score_shadow_candidate(trace_record: dict[str, Any]) -> dict[str, Any]:
    blockers = [
        str(blocker)
        for blocker in trace_record.get("blockers", [])
        if str(blocker) in HARD_BLOCKERS
    ]
    if blockers:
        return {
            "score": 0.0,
            "recommendation": "trace_only",
            "reasons": [],
            "blockers": blockers,
        }
    components = trace_record.get("components", {})
    if not isinstance(components, dict):
        components = {}
    score = 0.0
    reasons: list[str] = []
    for key, weight in WEIGHTS.items():
        value = float(components.get(key, trace_record.get(key, 0)))
        bounded = max(0.0, min(100.0, value))
        score += bounded * weight
        if bounded >= 70:
            reasons.append(f"{key}:{int(bounded)}")
    rounded = round(score, 2)
    return {
        "score": rounded,
        "recommendation": _recommendation(rounded),
        "reasons": reasons,
        "blockers": blockers,
    }
