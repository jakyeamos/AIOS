"""
AIOS: AI History Import — core module
Parses ChatGPT exports, Claude `conversations.json` exports, Codex session
rollouts, and Claude Code local JSONL sessions into normalized conversation
dicts. Renders conversation dicts as Obsidian markdown notes.

This module is imported by tests and called by the CLI (import-ai-history.py).
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


# --- Configuration ---

MIN_EXCHANGE_COUNT = 2    # minimum complete Q&A pairs to qualify as 'keep'
MIN_ASSISTANT_WORDS = 100 # minimum total words across all assistant responses for 'keep'
EPOCH_DATE = "1970-01-01"
CODEX_TEXT_TYPES = {"input_text", "output_text"}

TOPIC_MAP = {
    "context": "topic/context-management",
    "retrieval": "topic/retrieval",
    "rag": "topic/rag",
    "embed": "topic/embeddings",
    "prompt": "topic/prompting",
    "debug": "topic/debugging",
    "architect": "topic/architecture",
    "refactor": "topic/refactoring",
    "test": "topic/testing",
    "deploy": "topic/deployment",
    "perform": "topic/performance",
    "typescript": "topic/typescript",
    "python": "topic/python",
    "react": "topic/react",
    "nextjs": "topic/nextjs",
    "next.js": "topic/nextjs",
    "sql": "topic/sql",
    "database": "topic/database",
    "prisma": "topic/database",
    "api": "topic/api",
    "auth": "topic/auth",
    "fantasy": "topic/fantasy-sports",
    "basketball": "topic/basketball",
    "obsidian": "topic/obsidian",
    "llm": "topic/ai-tools",
}


# --- Utility functions ---

def make_id(source: str, source_id: str, date: str, title: str) -> str:
    """Deterministic 12-char ID for deduplication, preferring source-native IDs."""
    raw = f"{source}:{source_id or ''}:{date}:{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace for stable slugs, titles, and summaries."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def title_to_slug(title: str) -> str:
    """Convert a conversation title to a URL-safe slug, max 6 words and 32 chars."""
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_whitespace(title).lower()).strip("-")
    words = [w for w in slug.split("-") if w]
    result = "-".join(words[:6])
    while len(result) > 32 and "-" in result:
        result = result.rsplit("-", 1)[0]
    return result or "untitled"


def make_file_suffix(source_id: str, fallback_id: str) -> str:
    """Stable 8-char suffix for filenames, derived from source-native ID when available."""
    raw = source_id or fallback_id
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def extract_text_parts(parts: list, allowed_types: set[str] | None = None) -> str:
    """Flatten mixed string/dict content items into plain text."""
    chunks: list[str] = []
    for part in parts or []:
        chunk = ""
        if isinstance(part, str):
            chunk = normalize_whitespace(part)
        elif isinstance(part, dict):
            part_type = part.get("type")
            if allowed_types is not None and part_type not in allowed_types:
                continue
            chunk = normalize_whitespace(part.get("text") or "")
            if not chunk and isinstance(part.get("parts"), list):
                chunk = normalize_whitespace(" ".join(str(item) for item in part["parts"] if isinstance(item, str)))
        if chunk:
            chunks.append(chunk)
    return "\n\n".join(chunks).strip()


def first_substantive_exchange(exchanges: list[dict]) -> dict | None:
    for ex in exchanges:
        question = normalize_whitespace(ex.get("question", ""))
        answer = normalize_whitespace(ex.get("answer", ""))
        if question or answer:
            return ex
    return None


def build_signal_text(title: str, exchanges: list[dict]) -> str:
    """Text used for deterministic topic/entity heuristics in phase 1."""
    parts = [normalize_whitespace(title)]
    ex = first_substantive_exchange(exchanges)
    if ex:
        if normalize_whitespace(ex.get("question", "")):
            parts.append(normalize_whitespace(ex["question"]))
        if normalize_whitespace(ex.get("answer", "")):
            parts.append(normalize_whitespace(ex["answer"]))
    return "\n".join(parts)


def extract_tags(source: str, title: str, exchanges: list[dict]) -> list[str]:
    """Derive topic tags from the title plus the first substantive exchange."""
    base = [f"ai-history/{source}"]
    lower = build_signal_text(title, exchanges).lower()
    seen: set[str] = set()
    for keyword, tag in TOPIC_MAP.items():
        if keyword in lower and tag not in seen:
            base.append(tag)
            seen.add(tag)
    return base


def build_summary(title: str, exchanges: list[dict]) -> str:
    """Deterministic phase-1 summary using the title plus the first substantive exchange."""
    ex = first_substantive_exchange(exchanges)
    clean_title = normalize_whitespace(title)
    if not ex:
        return clean_title or "No summary available."
    answer = normalize_whitespace(ex.get("answer", ""))
    question = normalize_whitespace(ex.get("question", ""))
    if answer:
        return f"{clean_title}. {answer[:280]}".strip()
    if question:
        return f"{clean_title}. {question[:220]}".strip()
    return clean_title or "No summary available."


def is_complete_exchange(exchange: dict) -> bool:
    return bool(
        normalize_whitespace(exchange.get("question", ""))
        and normalize_whitespace(exchange.get("answer", ""))
    )


def score_quality(exchanges: list[dict]) -> str:
    """
    Return 'keep' or 'deferred'.
    Deferred if fewer than MIN_EXCHANGE_COUNT complete Q&A pairs,
    or if total assistant word count is below MIN_ASSISTANT_WORDS.
    """
    complete_exchanges = [ex for ex in exchanges if is_complete_exchange(ex)]
    if len(complete_exchanges) < MIN_EXCHANGE_COUNT:
        return "deferred"
    total_words = sum(
        len(normalize_whitespace(ex.get("answer", "")).split())
        for ex in complete_exchanges
    )
    if total_words < MIN_ASSISTANT_WORDS:
        return "deferred"
    return "keep"


def messages_to_exchanges(messages: list[dict]) -> list[dict]:
    """
    Convert an ordered list of {role, text, time} dicts into
    a list of {question, answer} exchange dicts.
    Consecutive assistant messages are joined; orphan assistant messages are skipped.
    """
    exchanges: list[dict] = []
    i = 0
    while i < len(messages):
        if messages[i]["role"] == "user":
            question = messages[i]["text"]
            answer_parts: list[str] = []
            i += 1
            while i < len(messages) and messages[i]["role"] == "assistant":
                text = messages[i]["text"].strip()
                if text:
                    answer_parts.append(text)
                i += 1
            answer = "\n\n".join(answer_parts)
            if question.strip():
                exchanges.append({"question": question, "answer": answer})
        else:
            i += 1
    return exchanges


def select_key_exchanges(exchanges: list[dict], n: int = 5) -> list[dict]:
    """
    Return up to n exchanges, selecting the most substantive (longest answers)
    while preserving original order.
    """
    complete_exchanges = [ex for ex in exchanges if is_complete_exchange(ex)]
    if len(complete_exchanges) <= n:
        return complete_exchanges
    indexed = sorted(
        enumerate(complete_exchanges),
        key=lambda x: len(x[1].get("answer", "")),
        reverse=True,
    )
    top_indices = sorted(idx for idx, _ in indexed[:n])
    return [complete_exchanges[i] for i in top_indices]


# --- ChatGPT parser ---

def parse_chatgpt_messages(mapping: dict) -> list[dict]:
    """
    Extract user and assistant messages from a ChatGPT mapping dict.
    Returns messages sorted by create_time ascending.
    """
    messages: list[dict] = []
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        role = msg.get("author", {}).get("role", "")
        if role not in ("user", "assistant"):
            continue
        parts = msg.get("content", {}).get("parts", [])
        text = extract_text_parts(parts)
        if not text or text == "...":
            continue
        create_time = msg.get("create_time") or 0.0
        messages.append({"role": role, "text": text, "time": float(create_time)})
    messages.sort(key=lambda x: x["time"])
    return messages


def parse_chatgpt_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a single ChatGPT conversation object into a normalized conv dict."""
    title = normalize_whitespace(raw.get("title") or "Untitled Conversation") or "Untitled Conversation"
    create_time = float(raw.get("create_time") or 0)
    date = datetime.fromtimestamp(create_time, tz=timezone.utc).strftime("%Y-%m-%d")
    source_id = str(raw.get("conversation_id") or raw.get("id") or "")
    mapping = raw.get("mapping") or {}
    messages = parse_chatgpt_messages(mapping)
    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)
    tags = extract_tags("chatgpt", title, exchanges)
    topic_tags = [t for t in tags if t.startswith("topic/")]
    summary = build_summary(title, exchanges)
    return {
        "id": make_id("chatgpt", source_id, date, title),
        "source": "chatgpt",
        "source_id": source_id,
        "model": "unknown",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


# --- Claude parser ---

def iso_to_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return EPOCH_DATE


def iso_to_ts(value: str, fallback: float = 0.0) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return fallback


def extract_claude_message_text(message: dict) -> str:
    """
    Prefer the top-level text field when present. Fall back to concatenating
    `content[]` items of type `text`. Ignore `thinking`, `tool_use`,
    `tool_result`, and `token_budget` in phase 1 exchange extraction.
    """
    text = normalize_whitespace(message.get("text") or "")
    if text:
        return text
    parts: list[str] = []
    for part in message.get("content") or []:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        chunk = normalize_whitespace(part.get("text") or "")
        if chunk:
            parts.append(chunk)
    return "\n\n".join(parts).strip()


def strip_codex_scaffolding(text: str) -> str:
    """Remove setup-only user scaffolding from Codex session text."""
    clean = str(text or "")
    clean = re.sub(r"(?s)# AGENTS\.md instructions.*?(?=<environment_context>|$)", "", clean)
    clean = re.sub(r"(?s)<environment_context>.*?</environment_context>", "", clean)
    clean = re.sub(r"(?s)<turn_aborted>.*?</turn_aborted>", "", clean)
    return normalize_whitespace(clean)


def extract_codex_message_text(content: list) -> str:
    return extract_text_parts(content, allowed_types=CODEX_TEXT_TYPES)


def load_codex_title_index(path: Path) -> dict[str, str]:
    """Load session titles from a colocated snapshot or the live Codex index."""
    candidates: list[Path] = []
    if path.is_dir():
        candidates.append(path / "session_index.jsonl")
    else:
        candidates.append(path.parent / "session_index.jsonl")
    candidates.append(Path.home() / ".codex" / "session_index.jsonl")

    titles: dict[str, str] = {}
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        with candidate.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                session_id = str(item.get("id") or "")
                title = normalize_whitespace(item.get("thread_name") or item.get("title") or "")
                if session_id and title:
                    titles[session_id] = title
        if titles:
            break
    return titles


def infer_codex_session_id(path: Path) -> str:
    stem = path.stem
    if "rollout-" in stem and len(stem) >= 36:
        candidate = stem[-36:]
        if re.fullmatch(r"[0-9a-f-]{36}", candidate):
            return candidate
    return ""


def load_codex_rollout(path: Path, title_index: dict[str, str]) -> dict | None:
    session_meta: dict = {}
    messages: list[dict] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") == "session_meta":
                session_meta = item.get("payload") or {}
                continue
            if item.get("type") != "response_item":
                continue
            payload = item.get("payload") or {}
            if payload.get("type") != "message":
                continue
            role = (payload.get("role") or "").strip().lower()
            if role not in {"user", "assistant"}:
                continue
            text = extract_codex_message_text(payload.get("content") or [])
            if not text:
                continue
            messages.append(
                {
                    "role": role,
                    "phase": payload.get("phase") or "none",
                    "text": text,
                }
            )

    session_id = str(session_meta.get("id") or infer_codex_session_id(path))
    if not session_id:
        return None
    return {
        "session_id": session_id,
        "title": normalize_whitespace(title_index.get(session_id) or ""),
        "created_at": session_meta.get("timestamp") or "",
        "source": session_meta.get("source") or "unknown",
        "model_provider": session_meta.get("model_provider") or "unknown",
        "rollout_path": path.name,
        "messages": messages,
    }


def load_codex_export(path: str) -> list[dict]:
    """
    Accept either a single rollout JSONL file or a directory of rollout files and
    normalize them into a common session shape.
    """
    base_path = Path(path).expanduser()
    if not base_path.exists():
        raise FileNotFoundError(f"Codex export not found: {base_path}")
    if base_path.is_file() and base_path.suffix != ".jsonl":
        raise ValueError(f"Expected a rollout .jsonl file or snapshot directory, got {base_path.name}")

    title_index = load_codex_title_index(base_path)
    if base_path.is_dir():
        rollout_paths = sorted(
            file_path
            for file_path in base_path.rglob("*.jsonl")
            if file_path.name != "session_index.jsonl"
        )
    else:
        rollout_paths = [base_path]
    if not rollout_paths:
        raise ValueError(f"No Codex rollout files found at {base_path}")

    sessions: list[dict] = []
    for rollout_path in rollout_paths:
        normalized = load_codex_rollout(rollout_path, title_index)
        if normalized is not None:
            sessions.append(normalized)

    if not sessions:
        raise ValueError(f"No valid Codex sessions found at {base_path}")
    sessions.sort(key=lambda item: (item.get("created_at") or "", item.get("session_id") or ""))
    return sessions


def first_codex_user_prompt(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        prompt = strip_codex_scaffolding(message.get("text") or "")
        if prompt:
            return prompt
    return ""


def parse_codex_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a normalized Codex session dict into the shared conversation shape."""
    messages_raw = raw.get("messages") or []
    title = normalize_whitespace(raw.get("title") or "") or first_codex_user_prompt(messages_raw) or "Untitled Conversation"
    source_id = str(raw.get("session_id") or "")
    created_at = raw.get("created_at") or ""
    date = iso_to_date(created_at)

    messages: list[dict] = []
    for message in messages_raw:
        role = (message.get("role") or "").strip().lower()
        phase = (message.get("phase") or "none").strip().lower()
        text = normalize_whitespace(message.get("text") or "")
        if role == "user":
            text = strip_codex_scaffolding(text)
            if not text:
                continue
        elif role == "assistant":
            if phase != "final_answer":
                continue
        else:
            continue
        if text:
            messages.append({"role": role, "text": text, "time": len(messages)})

    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)
    tags = extract_tags("codex", title, exchanges)
    topic_tags = [tag for tag in tags if tag.startswith("topic/")]
    summary = build_summary(title, exchanges)
    return {
        "id": make_id("codex", source_id, date, title),
        "source": "codex",
        "source_id": source_id,
        "model": normalize_whitespace(raw.get("model_provider") or "unknown") or "unknown",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


def parse_claude_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a single Claude conversation object into a normalized conv dict."""
    title = normalize_whitespace(raw.get("name") or "Untitled Conversation") or "Untitled Conversation"
    source_id = str(raw.get("uuid") or "")
    messages_raw = raw.get("chat_messages") or []
    created_at = raw.get("created_at") or raw.get("updated_at") or ""
    if not created_at:
        created_at = next(
            (m.get("created_at") or m.get("updated_at") or "" for m in messages_raw if isinstance(m, dict)),
            "",
        )
    date = iso_to_date(created_at)
    messages: list[dict] = []
    for m in messages_raw:
        sender = (m.get("sender") or "").strip().lower()
        if sender in ("human", "user"):
            role = "user"
        elif sender == "assistant":
            role = "assistant"
        else:
            continue
        text = extract_claude_message_text(m)
        if text:
            messages.append({
                "role": role,
                "text": text,
                "time": iso_to_ts(m.get("created_at") or created_at),
            })
    messages.sort(key=lambda x: x["time"])
    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)
    tags = extract_tags("claude", title, exchanges)
    topic_tags = [t for t in tags if t.startswith("topic/")]
    summary = build_summary(title, exchanges)
    return {
        "id": make_id("claude", source_id, date, title),
        "source": "claude",
        "source_id": source_id,
        "model": "unknown",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


# --- Claude Code parser ---

_CC_SCAFFOLD_TAGS = (
    "local-command-caveat",
    "system-reminder",
    "command-name",
    "command-message",
    "command-args",
    "local-command-stdout",
    "objective",
)
_CC_SCAFFOLD_RE = re.compile(
    r"(?s)<(?:" + "|".join(_CC_SCAFFOLD_TAGS) + r")>.*?</(?:" + "|".join(_CC_SCAFFOLD_TAGS) + r")>"
)


def strip_claude_code_scaffolding(text: str) -> str:
    """Remove Claude Code system/hook scaffolding from a user message."""
    return normalize_whitespace(_CC_SCAFFOLD_RE.sub("", text))


def extract_claude_code_message_text(content: str | list) -> str:
    """
    Extract plain text from a Claude Code message content field.
    content is a raw string or a list of typed blocks.
    Only `text` blocks are kept; tool_use, tool_result, and thinking are skipped.
    """
    if isinstance(content, str):
        return normalize_whitespace(content)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            chunk = normalize_whitespace(block.get("text") or "")
            if chunk:
                parts.append(chunk)
        return "\n\n".join(parts).strip()
    return ""


def cwd_to_project_tag(project_dir_name: str) -> str:
    """
    Derive a project/X tag from a ~/.claude/projects/ directory name.

    -Users-jakyeamos-Desktop-Fantasy  ->  project/desktop-fantasy
    -Users-jakyeamos                  ->  project/home
    """
    name = project_dir_name.lstrip("-")
    name = re.sub(r"^Users-[^-]+-?", "", name, count=1)
    name = name.strip("-").lower() or "home"
    return f"project/{name}"


def load_claude_code_session(path: Path, project_dir_name: str) -> dict | None:
    """
    Parse a single Claude Code session JSONL file.
    Skips isMeta (skill/hook injections) and isSidechain events.
    Returns a normalized session dict or None if no usable messages remain.
    """
    messages: list[dict] = []
    first_timestamp: str = ""
    model: str = "claude-code"
    cwd: str = ""

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            if event_type not in ("user", "assistant"):
                continue
            if event.get("isMeta") or event.get("isSidechain"):
                continue

            if not first_timestamp:
                first_timestamp = event.get("timestamp") or ""
            if not cwd and event.get("cwd"):
                cwd = event["cwd"]

            msg = event.get("message") or {}
            role = msg.get("role") or ""
            if role not in ("user", "assistant"):
                continue

            if role == "assistant" and model == "claude-code":
                extracted = normalize_whitespace(msg.get("model") or "")
                if extracted:
                    model = extracted

            text = extract_claude_code_message_text(msg.get("content", ""))
            if role == "user":
                text = strip_claude_code_scaffolding(text)

            if not text:
                continue

            ts = event.get("timestamp") or first_timestamp
            messages.append({
                "role": role,
                "text": text,
                "time": iso_to_ts(ts) if ts else float(len(messages)),
            })

    if not messages:
        return None

    return {
        "session_id": path.stem,
        "created_at": first_timestamp,
        "cwd": cwd,
        "model": model,
        "project_dir": project_dir_name,
        "messages": messages,
    }


def load_claude_code_export(path: str) -> list[dict]:
    """
    Walk a ~/.claude/projects/ directory (or a single project subdir) and
    return normalized session dicts. Observer sessions and sessions with no
    usable messages after scaffolding removal are excluded.

    Accepts:
      - ~/.claude/projects/            (all projects)
      - ~/.claude/projects/<proj-dir>  (one project)
    """
    base = Path(path).expanduser()
    if not base.exists():
        raise FileNotFoundError(f"Claude Code sessions dir not found: {base}")

    has_jsonl = any(f.suffix == ".jsonl" for f in base.iterdir() if f.is_file())
    project_dirs = [base] if has_jsonl else sorted(d for d in base.iterdir() if d.is_dir())

    sessions: list[dict] = []
    for project_dir in project_dirs:
        if "--claude-mem" in project_dir.name:
            continue
        for jsonl_file in sorted(project_dir.glob("*.jsonl")):
            session = load_claude_code_session(jsonl_file, project_dir.name)
            if session:
                sessions.append(session)

    sessions.sort(key=lambda s: (s.get("created_at") or "", s.get("session_id") or ""))
    return sessions


def _first_claude_code_user_prompt(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            return normalize_whitespace(msg.get("text") or "")
    return ""


def parse_claude_code_conversation(raw: dict, batch_id: str) -> dict:
    """Parse a normalized Claude Code session dict into the shared conversation shape."""
    messages_raw = raw.get("messages") or []
    source_id = str(raw.get("session_id") or "")
    created_at = raw.get("created_at") or ""
    date = iso_to_date(created_at)
    project_dir = raw.get("project_dir") or ""

    first_user = _first_claude_code_user_prompt(messages_raw)
    if len(first_user) > 80:
        truncated = first_user[:80].rsplit(" ", 1)[0]
        title = normalize_whitespace(truncated) or first_user[:80]
    else:
        title = first_user
    title = title or "Untitled Conversation"

    messages = [
        {"role": m["role"], "text": m["text"], "time": m["time"]}
        for m in messages_raw
    ]
    exchanges = messages_to_exchanges(messages)
    key_exchanges = select_key_exchanges(exchanges)
    quality = score_quality(exchanges)
    slug = title_to_slug(title)

    base_tags = extract_tags("claude-code", title, exchanges)
    project_tag = cwd_to_project_tag(project_dir)
    tags = [base_tags[0], project_tag] + base_tags[1:]
    topic_tags = [t for t in tags if t.startswith("topic/")]

    summary = build_summary(title, exchanges)
    return {
        "id": make_id("claude-code", source_id, date, title),
        "source": "claude-code",
        "source_id": source_id,
        "model": normalize_whitespace(raw.get("model") or "claude-code") or "claude-code",
        "date": date,
        "title": title,
        "slug": slug,
        "tags": tags,
        "topic_tags": topic_tags,
        "batch_id": batch_id,
        "quality": quality,
        "summary": summary or "No summary available.",
        "key_exchanges": key_exchanges,
        "exchange_count": len(exchanges),
    }


# --- Markdown renderer ---

def yaml_quote(value: str) -> str:
    """Render a YAML-safe scalar without pulling in a YAML dependency."""
    return json.dumps(str(value), ensure_ascii=False)


def render_markdown(conv: dict) -> str:
    """Render a normalized conv dict as an Obsidian markdown note."""
    tags_yaml = "\n".join(f"  - {yaml_quote(t)}" for t in conv["tags"])
    exchanges_md = ""
    for ex in conv["key_exchanges"]:
        q = ex["question"].replace("\n", " ").strip()
        a = ex["answer"].strip()
        exchanges_md += f"\n**Q:** {q}\n\n**A:** {a}\n"
    if not exchanges_md:
        exchanges_md = "\n<!-- No exchanges extracted -->\n"
    return (
        f"---\n"
        f"type: ai-history\n"
        f"source: {conv['source']}\n"
        f"model: {yaml_quote(conv.get('model', 'unknown'))}\n"
        f"date: {conv['date']}\n"
        f"title: {yaml_quote(conv['title'])}\n"
        f"slug: {conv['slug']}\n"
        f"tags:\n{tags_yaml}\n"
        f"import_batch: {yaml_quote(conv['batch_id'])}\n"
        f"quality: {conv['quality']}\n"
        f"---\n\n"
        f"## Summary\n\n{conv['summary']}\n\n"
        f"## Why This Mattered\n\n"
        f"<!-- Fill in: why past-you was asking this, what problem it connected to, "
        f"why future-you might care -->\n\n"
        f"## Key Exchanges\n{exchanges_md}\n"
        f"## Concepts Discussed\n\n"
        f"<!-- Add [[wikilinks]] to concept pages if applicable -->\n\n"
        f"## Notes\n\n"
        f"<!-- Manual additions post-import -->\n"
    )
