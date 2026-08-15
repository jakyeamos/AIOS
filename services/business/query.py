from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from services.business.citations import citation_token, slugify
from services.business.llm.client import resolve_llm_provider
from services.business.llm.prompts import build_query_prompt
from services.business.paths import WIKI_CANDIDATES_ROOT
from services.business.search.fts_search import SearchHit
from services.business.search.retrieve import retrieve_context
from services.business.wiki.frontmatter import default_business_fields, render_frontmatter
from services.business.wiki.io import atomic_write


@dataclass
class QueryResult:
    question: str
    answer: str
    hits: list[SearchHit] = field(default_factory=list)
    llm_used: bool = False
    llm_provider: str | None = None
    saved_question_path: str | None = None


def answer_question(
    conn,
    question: str,
    *,
    use_llm: bool = False,
    provider_name: str | None = None,
    save_question: bool = False,
) -> QueryResult:
    hits = retrieve_context(conn, question)
    if use_llm:
        provider = resolve_llm_provider(provider_name)
        if provider and provider.name == "api" and provider.is_available():
            answer = _llm_answer_api(question, hits)
            result = QueryResult(
                question=question,
                answer=answer,
                hits=hits,
                llm_used=True,
                llm_provider="api",
            )
        elif provider and provider.name == "cli" and provider.is_available():
            answer = _llm_answer_cli(question, hits, provider.cli)  # type: ignore[attr-defined]
            result = QueryResult(
                question=question,
                answer=answer,
                hits=hits,
                llm_used=True,
                llm_provider=f"cli:{provider.cli}",  # type: ignore[attr-defined]
            )
        else:
            result = QueryResult(
                question=question,
                answer=_deterministic_answer(question, hits),
                hits=hits,
                llm_used=False,
                llm_provider=provider.name if provider else None,
            )
    else:
        result = QueryResult(
            question=question, answer=_deterministic_answer(question, hits), hits=hits
        )

    if save_question:
        result.saved_question_path = str(_save_question_page(question, result.answer, hits))
    return result


def _deterministic_answer(question: str, hits: list[SearchHit]) -> str:
    if not hits:
        return (
            f"## Answer\n\nNo matching business memory found for: {question}\n\n"
            "Try ingesting sources and running `business-compile.py` first."
        )

    lines = ["## Answer\n", f"Question: {question}\n"]
    wiki_lines: list[str] = []
    evidence: list[str] = []

    for hit in hits[:8]:
        if hit.tier == "wiki":
            wiki_lines.append(f"- [[{hit.path}|{hit.title}]] — {hit.excerpt}")
        if hit.source_id:
            evidence.append(f"- {citation_token(hit.source_id)}: {hit.excerpt}")

    if wiki_lines:
        lines.append("### What the wiki says\n")
        lines.extend(wiki_lines)
        lines.append("")

    if evidence:
        lines.append("### Evidence\n")
        lines.extend(evidence)
        lines.append("")

    if _is_excitement_question(question):
        lines.append("### Excitement signals (from matches)\n")
        for hit in hits:
            if "excited" in hit.excerpt.lower() or "demand" in hit.excerpt.lower():
                lines.append(f"- {hit.excerpt}")
        lines.append("")

    lines.append("_Deterministic FTS answer — use `--llm` for synthesis._")
    return "\n".join(lines)


def _is_excitement_question(question: str) -> bool:
    lower = question.lower()
    return "excited" in lower or "want to learn" in lower


def _llm_answer_api(question: str, hits: list[SearchHit]) -> str:
    prompt = build_query_prompt(question, hits)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _deterministic_answer(question, hits)
    base_url = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a business memory analyst. Cite sources."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return f"{content.strip()}\n\n_Synthesized via LLM provider: api_"
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return _deterministic_answer(question, hits)


def _llm_answer_cli(question: str, hits: list[SearchHit], cli: str) -> str:
    import shutil
    import subprocess

    if not shutil.which(cli):
        return _deterministic_answer(question, hits)
    prompt = build_query_prompt(question, hits)
    if cli == "codex":
        cmd = ["codex", "exec", prompt]
    elif cli == "claude":
        cmd = ["claude", "-p", prompt]
    else:
        cmd = [cli, prompt]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _deterministic_answer(question, hits)
    if completed.returncode != 0 or not completed.stdout.strip():
        return _deterministic_answer(question, hits)
    return f"{completed.stdout.strip()}\n\n_Synthesized via LLM provider: cli:{cli}_"


def _save_question_page(question: str, answer: str, hits: list[SearchHit]) -> str:
    slug = slugify(question)[:80]
    path = WIKI_CANDIDATES_ROOT / "questions" / f"{slug}.md"
    source_ids = [hit.source_id for hit in hits if hit.source_id]
    fields = default_business_fields(
        page_type="business-question",
        title=question,
        source_ids=source_ids,
        tags=["question"],
        confidence=0.7,
    )
    fields["quality"] = "agent-reviewed"
    related = [hit.path for hit in hits if hit.tier == "wiki"][:8]
    fields["related"] = related
    body = f"# {question}\n\n{answer}\n"
    atomic_write(path, render_frontmatter(fields) + "\n" + body)
    return str(path)
