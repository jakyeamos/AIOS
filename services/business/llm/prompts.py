from __future__ import annotations

import json

from services.business.llm.models import SourceAnalysis
from services.business.sources_db import DbSource

ANALYSIS_JSON_SCHEMA = """
{
  "source_id": "string",
  "summary": "2-4 sentence summary",
  "key_quote": "short verbatim quote from source",
  "business_relevance": "why this matters for course/business decisions",
  "concepts": ["slug-like concept ids, e.g. autocompact"],
  "objections": ["objections or confusions, if any"],
  "excitement_signals": ["positive demand signals, if any"],
  "sentiment": "positive|mixed|negative|neutral",
  "confidence": 0.0-1.0
}
"""


def build_analysis_prompt(source: DbSource) -> str:
    tags = ", ".join(source.tags) if source.tags else "none"
    return f"""You analyze business feedback for a course creator's knowledge wiki.

Return ONLY valid JSON matching this schema (no markdown fences):
{ANALYSIS_JSON_SCHEMA}

Rules:
- Preserve provenance: base claims only on the source text below.
- Do not invent facts.
- concepts should be short slug-style identifiers.
- confidence reflects how actionable/clear the signal is.

Source ID: {source.source_id}
Type: {source.source_type}
Author: {source.author_name or "unknown"}
Channel: {source.channel_or_thread or "n/a"}
Subject: {source.subject_or_title or "n/a"}
Tags: {tags}

Source text:
\"\"\"
{source.body_text[:6000]}
\"\"\"
"""


def parse_analysis_json(raw: str, source_id: str, provider: str) -> SourceAnalysis:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    data["source_id"] = source_id
    data["provider"] = provider
    return SourceAnalysis.from_dict(data)


def build_query_prompt(question: str, hits: list) -> str:
    context_blocks: list[str] = []
    for hit in hits:
        cite = (
            f"[src:{hit.source_id.removeprefix('src_')}]" if hit.source_id else f"wiki:{hit.path}"
        )
        context_blocks.append(
            f"### {hit.title} ({hit.tier})\nPath: {hit.path}\nCitation token: {cite}\n{hit.excerpt}\n"
        )
    context = "\n".join(context_blocks) or "No retrieved context."
    return f"""Answer this business question using ONLY the retrieved context below.

Return markdown with:
1. A direct answer (2-6 sentences)
2. A "Evidence" section with bullet citations using [src:...] tokens exactly as provided
3. A "Wiki pages" section listing relevant wiki paths
4. If uncertain, say what is missing

Question: {question}

Retrieved context:
{context}
"""
