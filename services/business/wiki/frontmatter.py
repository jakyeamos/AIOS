from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def render_frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            elif all(isinstance(item, str) for item in value):
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: {json.dumps(value)}")
        else:
            escaped = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines) + "\n"


def default_business_fields(
    *,
    page_type: str,
    title: str,
    source_ids: list[str],
    tags: list[str],
    sensitivity: str = "internal",
    confidence: float = 0.65,
) -> dict[str, Any]:
    today = datetime.now(UTC).date().isoformat()
    return {
        "type": page_type,
        "title": title,
        "status": "draft",
        "quality": "agent-generated",
        "trust": "working",
        "sensitivity": sensitivity,
        "retrieval": "scoped" if sensitivity in {"private", "sensitive"} else "default",
        "area": "business",
        "project": None,
        "created": today,
        "updated": today,
        "last_reviewed": None,
        "source": "business-compiler",
        "source_type": "generated",
        "source_ids": source_ids,
        "evidence": [],
        "confidence": confidence,
        "source_count": len(source_ids),
        "tags": tags,
        "related": [],
        "review-status": "pending",
        "llm_status": "skipped",
    }
