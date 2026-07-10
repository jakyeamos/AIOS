from __future__ import annotations

from typing import TYPE_CHECKING

from services.business.citations import citation_token
from services.business.sources_db import DbSource
from services.business.taxonomy import ConceptMatch, detect_concepts, excerpt_sentences
from services.business.wiki.frontmatter import default_business_fields, render_frontmatter

if TYPE_CHECKING:
    from services.business.llm.models import SourceAnalysis


def render_summary_page(source: DbSource, analysis: SourceAnalysis | None = None) -> str:
    concepts = detect_concepts(source)
    concept_titles = [concept.title for concept in concepts]
    cite = citation_token(source.source_id)

    if analysis:
        summary = analysis.summary or excerpt_sentences(source.body_text)
        quote = analysis.key_quote or (
            source.body_text.strip().splitlines()[0] if source.body_text.strip() else ""
        )
        relevance = analysis.business_relevance
        llm_status = analysis.provider
        quality = "agent-reviewed" if analysis.confidence >= 0.7 else "agent-generated"
        confidence = analysis.confidence
    else:
        summary = excerpt_sentences(source.body_text)
        quote = source.body_text.strip().splitlines()[0] if source.body_text.strip() else ""
        relevance = (
            "Deterministic compile pass tagged this source as relevant to: "
            f"{', '.join(concept_titles) or 'general business feedback'}."
        )
        llm_status = "skipped"
        quality = "agent-generated"
        confidence = 0.65

    title = source.subject_or_title or source.source_id
    fields = default_business_fields(
        page_type="business-summary",
        title=title,
        source_ids=[source.source_id],
        tags=["summary", *source.tags],
        sensitivity=source.privacy_level,
        confidence=confidence,
    )
    fields["quality"] = quality
    fields["llm_status"] = llm_status
    fields["related"] = [f"concepts/{concept.slug}" for concept in concepts]

    extra_sections = ""
    if analysis:
        if analysis.objections:
            extra_sections += "\n## Objections\n\n" + "\n".join(
                f"- {item}" for item in analysis.objections
            )
        if analysis.excitement_signals:
            extra_sections += "\n\n## Excitement signals\n\n" + "\n".join(
                f"- {item}" for item in analysis.excitement_signals
            )
        if analysis.sentiment:
            extra_sections += f"\n\n## Sentiment\n\n{analysis.sentiment}\n"

    body = f"""# {title}

## Source metadata

- Type: {source.source_type}
- Author: {source.author_name or "unknown"}
- Channel: {source.channel_or_thread or "n/a"}
- Occurred: {source.occurred_at}
- Citation: {cite}

## Summary

{summary}

## Key quote

> {quote}

## Extracted concepts

{chr(10).join(f"- [[concepts/{concept.slug}|{concept.title}]] ({concept.business_label})" for concept in concepts) or "- none detected"}

## Business relevance

{relevance}
{extra_sections}
## Evidence

- {cite}
"""
    return render_frontmatter(fields) + "\n" + body


def render_concept_page(
    concept: ConceptMatch,
    sources: list[DbSource],
    *,
    existing_body: str | None = None,
    evidence_date: str,
) -> str:
    source_ids = [source.source_id for source in sources]
    fields = default_business_fields(
        page_type="business-concept",
        title=concept.title,
        source_ids=source_ids,
        tags=["concept", concept.slug, concept.business_label],
        confidence=min(0.9, 0.55 + 0.1 * len(sources)),
    )

    if existing_body:
        evidence_block = _render_new_evidence(sources, evidence_date)
        marker = f"## New evidence ({evidence_date})"
        if marker in existing_body:
            return existing_body
        return existing_body.rstrip() + "\n\n" + evidence_block + "\n"

    citations = [citation_token(source.source_id) for source in sources]
    quotes = "\n".join(
        f"- {citation_token(source.source_id)}: {excerpt_sentences(source.body_text, 2, 220)}"
        for source in sources
    )
    body = f"""# {concept.title}

## Definition (business context)

{concept.title} shows up in student and market feedback as a recurring theme labeled **{concept.business_label}**.

## What people are saying

{quotes}

## Recurring questions

{_bullet_questions(sources)}

## Recurring problems

{_bullet_problems(sources, concept)}

## Evidence

{chr(10).join(f"- {cite}" for cite in citations)}

## Related course sections

{_related_sections(sources)}

## Open questions

- Needs human review to confirm whether this concept deserves promotion to trusted.
"""
    return render_frontmatter(fields) + "\n" + body


def render_course_page(
    sources: list[DbSource],
    *,
    course_title: str,
    course_slug: str,
    existing_body: str | None = None,
    evidence_date: str,
) -> str:
    source_ids = [source.source_id for source in sources]
    fields = default_business_fields(
        page_type="business-course",
        title=course_title,
        source_ids=source_ids,
        tags=["course", course_slug],
        confidence=min(0.9, 0.6 + 0.08 * len(sources)),
    )
    fields["related"] = [f"concepts/{slug}" for slug in sorted(_concept_slugs_for_sources(sources))]

    if existing_body:
        evidence_block = _render_course_evidence(sources, evidence_date)
        marker = f"## New evidence ({evidence_date})"
        if marker in existing_body:
            return existing_body
        return existing_body.rstrip() + "\n\n" + evidence_block + "\n"

    body = f"""# {course_title}

## Intended audience

Builders learning agent workflows, context engineering, and cohort-style implementation.

## Known student pain points

{_bullet_field(sources, ("confus", "lost", "unclear", "pain"))}

## Questions students asked

{_bullet_questions(sources)}

## Objections and confusions

{_bullet_field(sources, ("pricing", "objection", "friction", "high"))}

## Excitement signals

{_bullet_field(sources, ("excited", "demand", "want to learn", "positive"))}

## Suggested improvements

{_bullet_field(sources, ("suggest", "should add", "would help", "need"))}

## Evidence

{chr(10).join(f"- {citation_token(source.source_id)}" for source in sources)}
"""
    return render_frontmatter(fields) + "\n" + body


def _render_new_evidence(sources: list[DbSource], evidence_date: str) -> str:
    lines = [f"## New evidence ({evidence_date})", ""]
    for source in sources:
        lines.append(
            f"- {citation_token(source.source_id)}: {excerpt_sentences(source.body_text, 2, 220)}"
        )
    return "\n".join(lines)


def _render_course_evidence(sources: list[DbSource], evidence_date: str) -> str:
    lines = [f"## New evidence ({evidence_date})", ""]
    for source in sources:
        lines.append(
            f"- {source.subject_or_title or source.source_id} {citation_token(source.source_id)}"
        )
    return "\n".join(lines)


def _bullet_questions(sources: list[DbSource]) -> str:
    lines: list[str] = []
    for source in sources:
        for line in source.body_text.splitlines():
            if "?" in line:
                lines.append(f"- {citation_token(source.source_id)}: {line.strip()}")
    return "\n".join(lines[:6]) or "- none captured yet"


def _bullet_problems(sources: list[DbSource], concept: ConceptMatch) -> str:
    lines: list[str] = []
    for source in sources:
        if concept.slug in source.combined_text.lower() or "confus" in source.body_text.lower():
            lines.append(
                f"- {citation_token(source.source_id)}: {excerpt_sentences(source.body_text, 1, 180)}"
            )
    return "\n".join(lines[:5]) or "- none captured yet"


def _related_sections(sources: list[DbSource]) -> str:
    from services.business.taxonomy import detect_course_sections

    sections: set[str] = set()
    for source in sources:
        sections.update(detect_course_sections(source))
    return "\n".join(f"- {section}" for section in sorted(sections)) or "- not specified"


def _bullet_field(sources: list[DbSource], keywords: tuple[str, ...]) -> str:
    lines: list[str] = []
    for source in sources:
        for line in source.body_text.splitlines():
            lower = line.lower()
            if any(keyword in lower for keyword in keywords):
                lines.append(f"- {citation_token(source.source_id)}: {line.strip()}")
    return "\n".join(lines[:8]) or "- none captured yet"


def _concept_slugs_for_sources(sources: list[DbSource]) -> set[str]:
    slugs: set[str] = set()
    for source in sources:
        for concept in detect_concepts(source):
            slugs.add(concept.slug)
    return slugs
