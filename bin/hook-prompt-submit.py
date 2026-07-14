#!/usr/bin/env python3
"""
AIOS hook: UserPromptSubmit
Logs prompt metadata, flags reusable candidates, and retrieves relevant context.
"""

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_paths import get_vault_root, get_vault_subpath, rewrite_legacy_vault_path  # noqa: E402
from hook_lifecycle import (  # noqa: E402
    ensure_session,
    load_hook_payload,
    resolve_hook_session_id,
)

from services.storage import connect as connect_storage  # noqa: E402

DB = os.environ.get("AIOS_DB", os.path.expanduser("~/AIOS/data/aios.db"))
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
VAULT_SEARCH = os.path.expanduser("~/AIOS/bin/vault-search.py")
POLICY_PATH = os.path.expanduser("~/AIOS/config/retrieval-policy.json")
MAX_RETRIEVAL_CHARS = 1200  # ~300 tokens
PROMPTS_ROOT = os.environ.get("AIOS_PROMPTS_ROOT", os.path.expanduser("~/AIOS/prompts"))
PROMPT_REGISTRY_PATH = os.path.join(PROMPTS_ROOT, "registry.json")
PROMPT_PURPOSE_MAX_CHARS = 200
PROMPT_MATCH_MIN_SCORE = 1

REUSABLE_SIGNALS = [
    "how do i",
    "how to",
    "explain",
    "refactor",
    "review",
    "write a",
    "create a",
    "generate",
    "plan",
    "debug",
    "fix",
    "help me",
]

CONTROL_PROMPTS = {
    "continue",
    "go on",
    "keep going",
    "ok",
    "okay",
    "yes",
    "no",
    "y",
    "n",
    "thanks",
    "thank you",
}

COMMAND_PREFIXES = ("/", "!", "cd ", "ls", "pwd", "git ", "npm ", "pnpm ", "python ", "python3 ")

CLASSIFICATIONS = {
    "debug": ["debug", "fix", "error", "bug", "broken", "failing", "crash"],
    "plan": ["plan", "roadmap", "design", "architect", "how should"],
    "refactor": ["refactor", "clean up", "simplify", "improve", "optimize"],
    "implement": ["implement", "write the", "build the", "build out", "code the"],
    "review": ["review", "check", "audit", "analyze", "evaluate"],
    "explain": ["explain", "what is", "how does", "what does", "why does"],
}


def _tokenize_text(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", value.lower()) if token}


def _input_names(rows: object) -> list[str]:
    if not isinstance(rows, list):
        return []
    names: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            for key in row:
                names.append(str(key))
    return names


def _extract_body(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    lines = markdown.splitlines()
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        return markdown
    return "\n".join(lines[end_index + 1 :]).lstrip("\n")


def _load_prompt_registry() -> list[dict]:
    try:
        with open(PROMPT_REGISTRY_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
        templates = payload.get("templates", [])
        if isinstance(templates, list):
            return [item for item in templates if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _template_paths(template: dict) -> list[str]:
    template_id = str(template.get("id", "")).strip()
    file_value = str(template.get("file", "")).strip()
    prompts_parent = os.path.dirname(PROMPTS_ROOT)
    candidates = []
    if file_value:
        if os.path.isabs(file_value):
            candidates.append(file_value)
        candidates.append(os.path.join(prompts_parent, file_value))
        candidates.append(os.path.join(PROMPTS_ROOT, os.path.basename(file_value)))
    if template_id:
        candidates.append(os.path.join(PROMPTS_ROOT, f"{template_id}.md"))
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _template_body_hash(template: dict) -> str | None:
    for path in _template_paths(template):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                return hashlib.sha256(_extract_body(handle.read()).encode("utf-8")).hexdigest()
    return None


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _data_backed_prompt_templates(conn: sqlite3.Connection) -> list[dict]:
    templates = _load_prompt_registry()
    if not templates or not _table_exists(conn, "prompt_library_links"):
        return []

    backed = []
    for template in templates:
        prompt_hash = _template_body_hash(template)
        if not prompt_hash:
            continue
        linked = conn.execute(
            "SELECT 1 FROM prompt_library_links WHERE prompt_hash = ? LIMIT 1",
            (prompt_hash,),
        ).fetchone()
        if linked:
            backed.append(template)
    return backed


def _render_template_hint(template: dict) -> str:
    template_id = str(template.get("id", ""))
    name = str(template.get("name", template_id))
    version = str(template.get("version", ""))
    purpose = str(template.get("purpose", "")).strip()
    purpose = re.sub(r"\s+", " ", purpose)
    if len(purpose) > PROMPT_PURPOSE_MAX_CHARS:
        purpose = purpose[:PROMPT_PURPOSE_MAX_CHARS].rstrip() + "..."

    required = ", ".join(_input_names(template.get("required_inputs")))
    optional_names = _input_names(template.get("optional_inputs"))
    optional = ", ".join(optional_names) if optional_names else ""
    full_template_path = os.path.join(PROMPTS_ROOT, f"{template_id}.md")

    required_text = required if required else "(none)"
    optional_text = f" | Optional: {optional}" if optional else ""

    return (
        f"**Prompt template match: {name} v{version}**\n"
        f"Purpose: {purpose}\n"
        f"Required: {required_text}{optional_text}\n"
        f"Full template: cat {full_template_path}"
    )


def _best_prompt_template(
    classification: str, prompt: str, templates: list[dict] | None = None
) -> dict | None:
    templates = templates if templates is not None else _load_prompt_registry()
    if not templates:
        return None

    prompt_tokens = _tokenize_text(prompt)
    best_score = -1
    best_template: dict | None = None
    for template in templates:
        score = 0
        if str(template.get("classification", "")).strip() == classification:
            score += 1

        tags = template.get("tags", [])
        tag_tokens: set[str] = set()
        if isinstance(tags, list):
            for tag in tags:
                tag_tokens.update(_tokenize_text(str(tag)))
        score += len(tag_tokens & prompt_tokens)

        if score > best_score and score >= PROMPT_MATCH_MIN_SCORE:
            best_score = score
            best_template = template

    return best_template


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [prompt-submit] {msg}\n")
    except Exception:
        pass


def load_policy() -> dict:
    try:
        with open(POLICY_PATH) as f:
            return json.load(f)
    except Exception:
        return {
            "prompt_retrieval": {
                "enabled": True,
                "debug": {"search_bug_log": True, "search_archive": True, "max_results": 3},
                "plan": {"search_handoff_decisions": True, "max_handoffs": 2},
                "review": {"search_handoff_decisions": True, "max_handoffs": 2},
            },
            "reusable_prompt_hint": {"enabled": True},
        }


def classify(text: str) -> str:
    lower = text.lower()
    for label, keywords in CLASSIFICATIONS.items():
        if any(k in lower for k in keywords):
            return label
    return "other"


def is_reusable_candidate(text: str) -> int:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if normalized in CONTROL_PROMPTS:
        return 0
    if normalized.startswith(COMMAND_PREFIXES):
        return 0
    if len(normalized.split()) < 6:
        return 0

    lower = normalized
    return 1 if any(s in lower for s in REUSABLE_SIGNALS) else 0


def vault_search(args: list[str]) -> dict:
    try:
        result = subprocess.run(
            ["python3", VAULT_SEARCH] + args,
            capture_output=True,
            text=True,
            timeout=6,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {"results": [], "count": 0}


def retrieve_context(
    classification: str, prompt: str, project_name: str, conn: sqlite3.Connection, policy: dict
) -> tuple[str, str]:
    """
    Returns (context_text, source_description) based on classification.
    Returns ("", "") if nothing retrieved.
    """
    retrieval_cfg = policy.get("prompt_retrieval", {})
    parts = []
    source = ""
    matched_template = _best_prompt_template(
        classification, prompt, _data_backed_prompt_templates(conn)
    )
    if matched_template:
        parts.append(_render_template_hint(matched_template))
        source = "prompt_library"
    if not retrieval_cfg.get("enabled", True):
        if not parts:
            return "", ""
        context_only = "\n\n".join(parts)
        if len(context_only) > MAX_RETRIEVAL_CHARS:
            context_only = context_only[:MAX_RETRIEVAL_CHARS] + "\n_(retrieval truncated)_"
        return context_only, source

    # Vault accessibility guard — skip vault-backed retrieval if vault isn't mounted
    vault_root = str(get_vault_root())
    vault_accessible = os.path.isdir(vault_root)

    if classification == "debug":
        cfg = retrieval_cfg.get("debug", {})

        if cfg.get("search_bug_log", True) and project_name:
            # Look up open bugs for this project
            try:
                cur = conn.execute(
                    """
                    SELECT b.symptom, b.root_cause, b.fix
                    FROM bug_log b
                    JOIN projects p ON b.project_id = p.id
                    WHERE p.name = ? AND b.status = 'open'
                    ORDER BY b.created_at DESC LIMIT ?
                    """,
                    (project_name, cfg.get("max_results", 3)),
                )
                bugs = cur.fetchall()
                if bugs:
                    bug_lines = []
                    for symptom, root_cause, _fix in bugs:
                        line = f"- {symptom}"
                        if root_cause:
                            line += f" (cause: {root_cause})"
                        bug_lines.append(line)
                    parts.append("**Open bugs (this project):**\n" + "\n".join(bug_lines))
                    source = "bug_log"
            except Exception:
                pass

        if cfg.get("search_archive", True) and not parts:
            # Only search archive if no open bugs matched (avoid noise when bugs already surfaced)
            stop = {"this", "that", "with", "from", "have", "what", "when", "where", "which"}
            terms = " ".join(w for w in prompt.lower().split() if len(w) >= 4 and w not in stop)[
                :60
            ]
            if terms:
                archive_result = vault_search(
                    ["--grep", terms, "--section", "Key Changes", "--source", "archive"]
                )
                if archive_result.get("count", 0) > 0:
                    titles = [r["title"] for r in archive_result["results"][:2]]
                    parts.append(f"**Related archive notes:** {', '.join(titles)}")
                    source = source or "archive"

    elif classification in ("plan", "review", "refactor"):
        cfg = retrieval_cfg.get(classification, {})
        if cfg.get("search_handoff_decisions", True) and project_name and vault_accessible:
            max_handoffs = cfg.get("max_handoffs", 2)
            handoff_result = vault_search(["--handoffs", project_name, "--last", str(max_handoffs)])
            if handoff_result.get("count", 0) > 0:
                decision_parts = []
                for r in handoff_result["results"]:
                    excerpt = r.get("excerpt", "")
                    # Extract decisions section
                    m = re.search(r"### Decisions\n(.+?)(?=\n###|\Z)", excerpt, re.DOTALL)
                    if m:
                        dec_text = m.group(1).strip()[:300]
                        if dec_text:
                            decision_parts.append(dec_text)
                if decision_parts:
                    parts.append(
                        "**Prior decisions (recent sessions):**\n" + "\n---\n".join(decision_parts)
                    )
                    source = "handoff_decisions"

    elif classification == "implement":
        cfg = retrieval_cfg.get("implement", {})
        if cfg.get("search_handoff_next_actions", True) and project_name and vault_accessible:
            max_handoffs = cfg.get("max_handoffs", 2)
            handoff_result = vault_search(["--handoffs", project_name, "--last", str(max_handoffs)])
            if handoff_result.get("count", 0) > 0:
                action_parts = []
                for r in handoff_result["results"]:
                    excerpt = r.get("excerpt", "")
                    m = re.search(r"### Next Actions\n(.+?)(?=\n###|\Z)", excerpt, re.DOTALL)
                    if m:
                        actions_text = m.group(1).strip()[:300]
                        if actions_text:
                            action_parts.append(actions_text)
                if action_parts:
                    parts.append(
                        "**Next actions from recent sessions:**\n" + "\n---\n".join(action_parts)
                    )
                    source = "handoff_next_actions"

    # Rules retrieval
    rules_cfg = policy.get("rules_retrieval", {})
    if rules_cfg.get("enabled", False):
        class_rules_cfg = rules_cfg.get(classification, {})
        domain = class_rules_cfg.get("domain")
        max_rules = class_rules_cfg.get("max_rules", 2)
        min_confidence = class_rules_cfg.get("min_confidence", 0.70)
        if domain:
            try:
                cur = conn.execute(
                    """
                    SELECT title, body, confidence FROM active_rules
                    WHERE domain = ? AND confidence >= ?
                    ORDER BY confidence DESC LIMIT ?
                    """,
                    (domain, min_confidence, max_rules),
                )
                rule_rows = cur.fetchall()
                if rule_rows:
                    rule_lines = []
                    for title, body, _ in rule_rows:
                        rule_lines.append("- " + (body.strip() if body else title))
                    parts.append("**Applicable rules:**\n" + "\n".join(rule_lines))
                    source = source or "rules"
            except Exception:
                pass

    # Wiki retrieval (human-curated vault entries only — never staging)
    wiki_cfg = policy.get("wiki_retrieval", {})
    if wiki_cfg.get("enabled", False) and classification in wiki_cfg.get("classifications", []):
        wiki_dir_raw = wiki_cfg.get(
            "vault_wiki_dir",
            str(get_vault_subpath("06 Knowledge", "Wiki")),
        )
        wiki_dir = os.path.expanduser(rewrite_legacy_vault_path(wiki_dir_raw) or wiki_dir_raw)
        if os.path.isdir(wiki_dir):
            try:
                # Extract key terms from prompt (skip short/stop words)
                stop = {
                    "this",
                    "that",
                    "with",
                    "from",
                    "have",
                    "what",
                    "when",
                    "where",
                    "which",
                    "does",
                    "why",
                    "how",
                    "the",
                    "and",
                    "for",
                    "you",
                }
                terms = [w for w in prompt.lower().split() if len(w) >= 4 and w not in stop][:6]
                if terms:
                    max_results = wiki_cfg.get("max_results", 2)
                    max_chars = wiki_cfg.get("max_chars_per_entry", 300)
                    hits = []
                    for fname in sorted(os.listdir(wiki_dir)):
                        if not fname.endswith(".md"):
                            continue
                        fname_lower = fname.lower()
                        if any(t in fname_lower for t in terms):
                            fpath = os.path.join(wiki_dir, fname)
                            try:
                                with open(fpath, encoding="utf-8", errors="replace") as handle:
                                    text = handle.read(max_chars * 2)
                                # Strip frontmatter
                                if text.startswith("---"):
                                    end = text.find("---", 3)
                                    text = text[end + 3 :].strip() if end > 0 else text
                                hits.append(f"**{fname[:-3]}:** {text[:max_chars].strip()}")
                            except Exception:
                                pass
                            if len(hits) >= max_results:
                                break
                    if hits:
                        parts.append("**Wiki (curated):**\n" + "\n\n".join(hits))
                        source = source or "wiki"
            except Exception:
                pass  # graceful fallback

    # Reusable prompt hint
    if not matched_template and policy.get("reusable_prompt_hint", {}).get("enabled", True):
        prompt_lower = prompt.lower()
        try:
            cur = conn.execute(
                "SELECT prompt_text FROM prompts_used WHERE reusable_candidate=1 ORDER BY rowid DESC LIMIT 50"
            )
            for (prior_text,) in cur.fetchall():
                if prior_text and len(prior_text) > 10:
                    prior_words = set(prior_text.lower().split())
                    prompt_words = set(prompt_lower.split())
                    if len(prior_words) > 0:
                        overlap = len(prior_words & prompt_words) / len(prior_words)
                        if overlap >= 0.6 and prior_text != prompt:
                            parts.append(
                                f"**Similar past prompt (reusable):** _{prior_text[:120]}_"
                            )
                            source = source or "prompt_library"
                            break
        except Exception:
            pass

    if not parts:
        return "", ""

    context = "\n\n".join(parts)
    if len(context) > MAX_RETRIEVAL_CHARS:
        context = context[:MAX_RETRIEVAL_CHARS] + "\n_(retrieval truncated)_"
    return context, source


def get_project_name(conn: sqlite3.Connection, session_id: str) -> str:
    try:
        cur = conn.execute(
            "SELECT p.name FROM sessions s JOIN projects p ON s.project_id = p.id WHERE s.id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        return row[0] if row else ""
    except Exception:
        return ""


def main() -> None:
    data = load_hook_payload(log=log, hook_name="prompt-submit")

    session_id = data.get("session_id", "")
    prompt = data.get("prompt", "")

    if not session_id or not prompt:
        sys.exit(0)

    policy = load_policy()
    retrieval_context = ""
    retrieval_source = ""

    try:
        conn = connect_storage(DB)
        resolved_session_id = resolve_hook_session_id(
            conn,
            payload_session_id=session_id,
            payload_cwd=data.get("cwd"),
            logs_dir=os.path.dirname(LOG),
            hook_name="prompt-submit",
            log=log,
        )
        if not resolved_session_id:
            conn.close()
            sys.exit(0)
        session_id = resolved_session_id
        ensure_session(
            conn,
            session_id=session_id,
            cwd=data.get("cwd"),
            objective=prompt.strip().splitlines()[0][:160].strip() if prompt.strip() else None,
            source_event="UserPromptSubmit",
            log=log,
        )

        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
        classification = classify(prompt)
        reusable = is_reusable_candidate(prompt)

        project_name = get_project_name(conn, session_id)

        retrieval_context, retrieval_source = retrieve_context(
            classification, prompt, project_name, conn, policy
        )

        conn.execute(
            """
            INSERT INTO prompts_used
              (id, session_id, prompt_hash, prompt_text, classification, reusable_candidate,
               retrieval_fired, retrieval_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                prompt_hash,
                prompt,
                classification,
                reusable,
                1 if retrieval_context else 0,
                retrieval_source if retrieval_source else None,
            ),
        )

        # Backfill objective from first prompt if session has none
        obj_row = conn.execute(
            "SELECT objective FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if obj_row and obj_row[0] is None:
            first_line = prompt.strip().splitlines()[0][:160].strip()
            if first_line:
                conn.execute(
                    "UPDATE sessions SET objective = ? WHERE id = ? AND objective IS NULL",
                    (first_line, session_id),
                )
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'UserPromptSubmit', ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                datetime.now(UTC).isoformat(),
                json.dumps(
                    {
                        "session_id": session_id,
                        "classification": classification,
                        "reusable": reusable,
                        "prompt_hash": prompt_hash,
                        "retrieval_fired": bool(retrieval_context),
                        "retrieval_source": retrieval_source,
                    }
                ),
            ),
        )
        conn.commit()
        conn.close()
        log(
            f"prompt logged ({classification}, reusable={reusable}, retrieval={bool(retrieval_context)}) session={session_id}"
        )
    except Exception as e:
        log(f"db error: {e}")

    # Inject retrieval context if found
    if retrieval_context:
        print(
            json.dumps(
                {"context": f"<!-- AIOS retrieval ({retrieval_source}) -->\n{retrieval_context}"}
            )
        )


if __name__ == "__main__":
    main()
