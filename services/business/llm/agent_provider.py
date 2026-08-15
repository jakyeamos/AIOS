from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from services.business import paths
from services.business.llm.base import LLMProvider
from services.business.llm.models import SourceAnalysis
from services.business.llm.prompts import build_analysis_prompt
from services.business.sources_db import DbSource


class AgentLLMProvider(LLMProvider):
    """Queue analysis jobs for a subscription agent; responses applied via llm-apply."""

    name = "agent"

    def __init__(self, *, run_id: str | None = None) -> None:
        self.run_id = run_id or _new_run_id()
        self.job_dir = paths.LLM_JOBS_ROOT / self.run_id
        self.response_dir = paths.LLM_RESPONSES_ROOT / self.run_id

    def is_available(self) -> bool:
        return True

    def analyze_source(self, source: DbSource) -> SourceAnalysis | None:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        job_path = self.job_dir / f"{source.source_id}.json"
        if job_path.exists():
            return None
        job_path.write_text(
            json.dumps(
                {
                    "source_id": source.source_id,
                    "prompt": build_analysis_prompt(source),
                    "expected_schema": "SourceAnalysis JSON per business LLM prompts",
                    "response_path": str(self.response_dir / f"{source.source_id}.json"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return None

    def finalize_manifest(self, sources: list[DbSource]) -> Path:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": self.run_id,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "instructions": (
                "For each job file, run analysis in your agent session (subscription). "
                "Write JSON responses to the matching response_path. "
                "Then run: python3 ~/AIOS/bin/business-compile.py --llm-apply --run-id "
                f"{self.run_id}"
            ),
            "jobs": [str(self.job_dir / f"{source.source_id}.json") for source in sources],
            "response_dir": str(self.response_dir),
        }
        manifest_path = self.job_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path


def _new_run_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"agent-{stamp}"


def load_agent_responses(run_id: str) -> dict[str, SourceAnalysis]:
    from services.business import paths

    response_dir = paths.LLM_RESPONSES_ROOT / run_id
    if not response_dir.exists():
        return {}
    from services.business.llm.prompts import parse_analysis_json

    results: dict[str, SourceAnalysis] = {}
    for path in sorted(response_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "source_id" in data and "summary" in data:
            results[str(data["source_id"])] = SourceAnalysis.from_dict(
                {**data, "provider": "agent"}
            )
            continue
        source_id = path.stem
        if isinstance(data, dict) and "raw" in data:
            results[source_id] = parse_analysis_json(str(data["raw"]), source_id, "agent")
    return results
