from __future__ import annotations

import json
from pathlib import Path

from services.business.paths import CONFIG_DIR

DEFAULT_SOURCES_CONFIG = {
    "manual": {
        "enabled": True,
        "inbox_path": "staging/raw-sources/manual/inbox",
    },
    "gmail": {
        "enabled": False,
        "queries": ["label:students newer_than:30d"],
        "exclude": ["in:trash", "in:spam"],
    },
    "discord": {
        "enabled": False,
        "guild_ids": [],
        "channel_ids": [],
    },
    "x": {
        "enabled": False,
        "modes": ["own_posts", "mentions", "bookmarks"],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_sources_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    json_path = CONFIG_DIR / "business-sources.json"
    if json_path.exists():
        return _deep_merge(
            DEFAULT_SOURCES_CONFIG, json.loads(json_path.read_text(encoding="utf-8"))
        )
    return dict(DEFAULT_SOURCES_CONFIG)


def write_default_config_files() -> list[Path]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    json_path = CONFIG_DIR / "business-sources.json"
    if not json_path.exists():
        json_path.write_text(json.dumps(DEFAULT_SOURCES_CONFIG, indent=2) + "\n", encoding="utf-8")
        written.append(json_path)
    taxonomy_path = CONFIG_DIR / "business-taxonomy.json"
    if not taxonomy_path.exists():
        taxonomy = {
            "business_concepts": [
                "student pain point",
                "course section",
                "objection",
                "excitement signal",
                "testimonial",
                "feature request",
                "bug/confusion",
                "launch feedback",
                "pricing concern",
                "content gap",
            ],
            "course_analysis_fields": [
                "missing talking points",
                "repeated questions",
                "misunderstood concepts",
                "requested examples",
                "exercises students want",
                "objections",
                "positive reactions",
            ],
        }
        taxonomy_path.write_text(json.dumps(taxonomy, indent=2) + "\n", encoding="utf-8")
        written.append(taxonomy_path)
    return written
