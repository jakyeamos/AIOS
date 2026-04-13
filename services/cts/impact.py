from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import BlastRadiusResult


@dataclass(slots=True)
class ChangeRisk:
    file_path: str
    impacted_nodes: int
    impacted_files: int
    avg_confidence: float
    stale_nodes: int
    low_confidence_estimate: bool
    risk_score: float


class ImpactAnalyzer:
    def __init__(self, store) -> None:
        self.store = store

    def get_impact_radius(
        self,
        repo_id: str,
        changed_files: list[str],
        max_depth: int = 3,
    ) -> BlastRadiusResult:
        raw = self.store.get_impact_radius(
            repo_id=repo_id,
            changed_files=changed_files,
            max_depth=max_depth,
        )
        impacted_nodes = raw["impacted_nodes"]
        low_conf_count = sum(1 for node in impacted_nodes if node.confidence < 0.6)
        stale_count = sum(1 for node in impacted_nodes if node.is_stale)
        unindexed = self.store.get_unindexed_files(repo_id, changed_files)
        risk_summary = self._risk_summary(changed_files, raw["impacted_files"], impacted_nodes)
        return BlastRadiusResult(
            changed_nodes=raw["changed_nodes"],
            impacted_nodes=impacted_nodes,
            impacted_files=raw["impacted_files"],
            edges=raw["edges"],
            truncated=raw["truncated"],
            total_impacted=raw["total_impacted"],
            risk_summary=risk_summary,
            low_confidence_count=low_conf_count,
            stale_count=stale_count,
            unindexed_changed_files=unindexed,
        )

    def detect_changes(
        self,
        repo_id: str,
        changed_files: list[str],
        base: str = "HEAD~1",
    ) -> dict[str, Any]:
        impact = self.get_impact_radius(repo_id, changed_files, max_depth=3)
        indexed_count = len(changed_files) - len(impact.unindexed_changed_files)
        coverage = indexed_count / len(changed_files) if changed_files else 1.0
        return {
            "base": base,
            "changed_files": changed_files,
            "impact": {
                "impacted_files": impact.impacted_files,
                "total_impacted_nodes": impact.total_impacted,
                "truncated": impact.truncated,
            },
            "risk_summary": impact.risk_summary,
            "low_confidence_estimate": impact.low_confidence_count > 0,
            "stale_nodes": impact.stale_count,
            "unindexed_changed_files": impact.unindexed_changed_files,
            "index_coverage_pct": coverage,
        }

    @staticmethod
    def _risk_summary(
        changed_files: list[str],
        impacted_files: list[str],
        impacted_nodes: list,
    ) -> dict[str, Any]:
        if not changed_files:
            return {
                "risk_score": 0.0,
                "tier": "low",
                "rationale": "No changed files supplied.",
            }
        avg_conf = (
            sum(node.confidence for node in impacted_nodes) / len(impacted_nodes)
            if impacted_nodes
            else 0.0
        )
        stale_nodes = sum(1 for node in impacted_nodes if node.is_stale)
        spread_factor = min(1.0, len(set(impacted_files)) / max(1, len(changed_files) * 4))
        reach_factor = min(1.0, len(impacted_nodes) / 120.0)
        confidence_penalty = 1.0 - avg_conf
        stale_penalty = min(1.0, stale_nodes / 20.0)
        score = (spread_factor * 0.35) + (reach_factor * 0.35) + (confidence_penalty * 0.2) + (
            stale_penalty * 0.1
        )
        if score >= 0.7:
            tier = "high"
        elif score >= 0.45:
            tier = "medium"
        else:
            tier = "low"
        return {
            "risk_score": round(score, 3),
            "tier": tier,
            "avg_confidence": round(avg_conf, 3),
            "stale_nodes": stale_nodes,
            "changed_files_count": len(changed_files),
            "impacted_files_count": len(set(impacted_files)),
            "impacted_nodes_count": len(impacted_nodes),
        }

