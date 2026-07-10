from __future__ import annotations

import json
import re
from dataclasses import dataclass

from services.business.citations import slugify
from services.business.config import CONFIG_DIR
from services.business.sources_db import DbSource

DEFAULT_CONCEPT_PATTERNS: dict[str, tuple[str, str]] = {
    "autocompact": (r"\bautocompact\b", "student pain point"),
    "context-engineering": (r"context (?:window|engineering)", "misunderstood concepts"),
    "agent-loops": (r"agent loops?", "excitement signal"),
    "launch-feedback": (r"launch feedback|launch went", "launch feedback"),
    "pricing-objections": (r"pricing felt|pricing concern|too expensive", "pricing concern"),
}

TAG_TO_CONCEPT: dict[str, str] = {
    "autocompact": "autocompact",
    "student-feedback": "autocompact",
    "excitement-signal": "agent-loops",
    "context-engineering": "context-engineering",
    "launch-feedback": "launch-feedback",
    "pricing-concern": "pricing-objections",
}

COURSE_TAG_RE = re.compile(r"course-section-(\d+)", re.I)
MODULE_RE = re.compile(r"\bmodule\s+(\d+)\b", re.I)
DEFAULT_COURSE_SLUG = "agent-wiki-course"
DEFAULT_COURSE_TITLE = "Agent Wiki Course"


@dataclass(frozen=True)
class ConceptMatch:
    slug: str
    title: str
    business_label: str


def load_taxonomy() -> dict:
    path = CONFIG_DIR / "business-taxonomy.json"
    if not path.exists():
        return {"business_concepts": [], "course_analysis_fields": []}
    return json.loads(path.read_text(encoding="utf-8"))


def detect_concepts(source: DbSource) -> list[ConceptMatch]:
    text = source.combined_text.lower()
    found: dict[str, ConceptMatch] = {}

    for slug, (pattern, label) in DEFAULT_CONCEPT_PATTERNS.items():
        if re.search(pattern, text, re.I):
            title = slug.replace("-", " ").title()
            found[slug] = ConceptMatch(slug=slug, title=title, business_label=label)

    for tag in source.tags:
        slug = TAG_TO_CONCEPT.get(tag)
        if slug and slug not in found:
            found[slug] = ConceptMatch(
                slug=slug,
                title=slug.replace("-", " ").title(),
                business_label=TAG_TO_CONCEPT.get(tag, "student pain point"),
            )

    return list(found.values())


def detect_course_sections(source: DbSource) -> list[str]:
    sections: set[str] = set()
    for tag in source.tags:
        match = COURSE_TAG_RE.search(tag)
        if match:
            sections.add(f"Section {match.group(1)}")
    for match in MODULE_RE.finditer(source.combined_text):
        sections.add(f"Module {match.group(1)}")
    if "cohort" in source.combined_text.lower() and not sections:
        sections.add("General cohort feedback")
    return sorted(sections)


def has_course_signal(source: DbSource) -> bool:
    text = source.combined_text.lower()
    if detect_course_sections(source):
        return True
    course_terms = ("course", "module", "cohort", "lecture", "lesson", "students")
    return any(term in text for term in course_terms)


def excerpt_sentences(text: str, max_sentences: int = 3, max_chars: int = 500) -> str:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    selected: list[str] = []
    total = 0
    for chunk in chunks:
        if not chunk:
            continue
        if len(selected) >= max_sentences or total + len(chunk) > max_chars:
            break
        selected.append(chunk)
        total += len(chunk)
    if not selected:
        return text[:max_chars].strip()
    return " ".join(selected)


def summary_slug(source: DbSource) -> str:
    base = slugify(source.subject_or_title or source.source_id)
    suffix = source.source_id.rsplit("_", 1)[-1]
    return f"{base}-{suffix}"
