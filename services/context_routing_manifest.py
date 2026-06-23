"""Helpers for inspecting context routing manifest payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_MANIFEST_FIELDS = {
    "task_id",
    "run_id",
    "phase",
    "context_sources_loaded",
    "context_sources_skipped",
    "retrieval_reasons",
    "estimated_context_tokens",
    "second_brain_available",
    "second_brain_used",
    "fallback_used",
    "caveats",
}


def load_context_routing_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Context receipt payload must be a JSON object.")
    manifest = payload.get("context_routing_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Context receipt payload has no context_routing_manifest object.")
    validate_context_routing_manifest(manifest)
    return manifest


def validate_context_routing_manifest(manifest: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing:
        raise ValueError(f"Context routing manifest missing fields: {', '.join(missing)}")
    if not isinstance(manifest["context_sources_loaded"], list):
        raise ValueError("context_sources_loaded must be a list.")
    if not isinstance(manifest["context_sources_skipped"], list):
        raise ValueError("context_sources_skipped must be a list.")
    if not isinstance(manifest["retrieval_reasons"], dict):
        raise ValueError("retrieval_reasons must be an object.")
    for field in ("second_brain_available", "second_brain_used", "fallback_used"):
        if not isinstance(manifest[field], bool):
            raise ValueError(f"{field} must be a boolean.")
    if not isinstance(manifest["estimated_context_tokens"], int):
        raise ValueError("estimated_context_tokens must be an integer.")
    for source in [*manifest["context_sources_loaded"], *manifest["context_sources_skipped"]]:
        if not isinstance(source, dict):
            raise ValueError("Context source entries must be objects.")
        for field in ("id", "path", "category", "reason"):
            if field not in source:
                raise ValueError(f"Context source missing {field}.")
