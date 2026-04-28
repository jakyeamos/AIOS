#!/usr/bin/env python3
"""
AIOS: discover-github-skills.py
Search GitHub for shareable skill definitions and store them as candidates
in aios.db::github_skill_candidates for review and one-click promotion.

Discovery strategy:
  1. Search GitHub code for files that look like AIOS-compatible skills:
     - Superpowers plugin skills (.agents/skills/*.md, SKILL.md with frontmatter)
     - Claude Code custom instruction files with skill-like structure
     - Prompt library files with purpose/stage metadata
  2. Parse each file for skill metadata (key, purpose, allowed_stages, invariants).
  3. Match against current workflow stage needs or a provided --workflow-key.
  4. Store candidates in github_skill_candidates with status='candidate'.

Usage:
  python3 ~/AIOS/bin/discover-github-skills.py [options]

  --workflow-key   Only find skills relevant to this workflow's stage kinds
  --query          Custom GitHub code search query (overrides auto-query)
  --limit          Max candidates to fetch (default 20)
  --dry-run        Preview without writing to DB
  --token          GitHub token (defaults to `gh auth token`)
  --db             Path to aios.db
  --verbose        Show fetched content and parse details
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "aios.db"
SKILLS_PATH = ROOT / "config" / "workflows" / "skills.json"

GITHUB_API = "https://api.github.com"
# Rate limit: authenticated = 30 search req/min, unauthenticated = 10
REQUEST_DELAY = 2.5  # seconds between API calls

# Patterns that suggest a file is a skill definition
# Must match at least MIN_SIGNAL_SCORE of these to be stored
SKILL_SIGNALS = [
    "allowed_stages",
    "input_schema",
    "output_schema",
    "execution_mode",
    "invariants",
    "failure_conditions",
    "execution_mode: deterministic",
    "execution_mode: heuristic",
    "side_effects",
]
MIN_SIGNAL_SCORE = 2

# Targeted queries — ordered from most to least specific.
# Superpowers plugin skills and AIOS-compatible JSON skill specs first.
DEFAULT_QUERIES = [
    # Skills that explicitly declare allowed_stages AND execution_mode (AIOS format)
    '"allowed_stages" "execution_mode" "invariants" extension:md',
    '"allowed_stages" "execution_mode" "failure_conditions" extension:json',
    # Superpowers skills with stage declarations
    'filename:SKILL.md "allowed_stages" "execution_mode"',
    # Claude Code skill files with purpose + invariants
    'path:.claude/skills "invariants" "execution_mode" extension:md',
]


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def get_token(token_arg: str | None) -> str:
    if token_arg:
        return token_arg
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def gh_get(path: str, token: str) -> dict | list:
    url = f"{GITHUB_API}{path}" if path.startswith("/") else path
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AIOS-skill-discovery/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(f"GitHub rate limit or auth error: {exc}") from exc
        if exc.code == 422:
            return {"items": []}  # Search returned no results
        raise


def search_code(query: str, token: str, per_page: int = 30) -> list[dict]:
    encoded = quote(query)
    path = f"/search/code?q={encoded}&per_page={per_page}"
    result = gh_get(path, token)
    if isinstance(result, dict):
        return result.get("items", [])
    return []


def fetch_raw(repo: str, file_path: str, token: str) -> str:
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/{file_path}"
    headers = {"User-Agent": "AIOS-skill-discovery/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Skill parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_KV_RE = re.compile(r"^(\w+)\s*:\s*(.+)$", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(\{.*?\})\s*\n```", re.DOTALL)


def parse_yaml_simple(text: str) -> dict:
    """Parse simple flat YAML (no nesting) for skill frontmatter."""
    result: dict = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in text.splitlines():
        # List item under current key
        m_item = re.match(r"^\s+-\s+(.+)$", line)
        if m_item and current_key:
            current_list.append(m_item.group(1).strip().strip("\"'"))
            continue

        m_kv = re.match(r"^(\w[\w_-]*)\s*:\s*(.*)$", line)
        if m_kv:
            if current_key and current_list:
                result[current_key] = current_list
            current_list = []
            key = m_kv.group(1)
            value = m_kv.group(2).strip().strip("\"'")
            if not value:
                current_key = key
            else:
                current_key = None
                result[key] = value

    if current_key and current_list:
        result[current_key] = current_list

    return result


def extract_skill_from_markdown(content: str, filename: str) -> dict | None:
    """Try to extract a skill spec from a markdown file."""
    fm_match = _FRONTMATTER_RE.match(content)
    fm: dict = {}
    if fm_match:
        fm = parse_yaml_simple(fm_match.group(1))

    # Also look for JSON blocks that might contain schema
    json_blocks = []
    for block in _JSON_BLOCK_RE.findall(content):
        with contextlib.suppress(Exception):
            json_blocks.append(json.loads(block))

    # Extract key fields
    key = (
        fm.get("key")
        or fm.get("name")
        or fm.get("skill_key")
        or Path(filename).stem.replace("-", "_").replace(" ", "_").lower()
    )
    purpose = (
        fm.get("purpose") or fm.get("description") or fm.get("summary") or _first_paragraph(content)
    )
    allowed_stages = fm.get("allowed_stages") or fm.get("stages") or []
    if isinstance(allowed_stages, str):
        allowed_stages = [s.strip() for s in allowed_stages.split(",")]

    invariants = fm.get("invariants") or []
    if isinstance(invariants, str):
        invariants = [invariants]

    failure_conditions = fm.get("failure_conditions") or []
    execution_mode = fm.get("execution_mode") or "heuristic"

    # Signal score — higher = more likely to be a real skill file
    signal_score = sum(1 for sig in SKILL_SIGNALS if sig in content.lower())
    if signal_score < MIN_SIGNAL_SCORE:
        return None

    return {
        "key": str(key)[:80],
        "purpose": str(purpose)[:300],
        "allowed_stages": allowed_stages if isinstance(allowed_stages, list) else [],
        "invariants": invariants if isinstance(invariants, list) else [],
        "failure_conditions": failure_conditions if isinstance(failure_conditions, list) else [],
        "execution_mode": str(execution_mode),
        "signal_score": signal_score,
        "raw_frontmatter": fm,
    }


def extract_skill_from_json(content: str) -> dict | None:
    """Try to extract a skill spec from a JSON file."""
    try:
        data = json.loads(content)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    signal_score = sum(1 for sig in SKILL_SIGNALS if sig in content)
    if signal_score < MIN_SIGNAL_SCORE:
        return None

    return {
        "key": str(data.get("key", ""))[:80],
        "purpose": str(data.get("purpose", ""))[:300],
        "allowed_stages": data.get("allowed_stages", []),
        "invariants": data.get("invariants", []),
        "failure_conditions": data.get("failure_conditions", []),
        "execution_mode": str(data.get("execution_mode", "heuristic")),
        "signal_score": signal_score,
        "raw_frontmatter": data,
    }


def _first_paragraph(text: str) -> str:
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:200]
    return ""


# ---------------------------------------------------------------------------
# Stage relevance matching
# ---------------------------------------------------------------------------


def load_workflow_stage_kinds(workflow_key: str) -> list[str]:
    """Return the stage kinds used by a workflow from registry.json."""
    registry_path = ROOT / "config" / "workflows" / "registry.json"
    if not registry_path.exists():
        return []
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for wf in registry.get("workflows", []):
            if wf.get("key") == workflow_key:
                return [s.get("kind", "") for s in wf.get("stages", [])]
    except Exception:
        pass
    return []


def skill_matches_workflow(skill: dict, stage_kinds: list[str]) -> bool:
    """Return True if the skill's allowed_stages overlap with workflow stage kinds."""
    if not stage_kinds:
        return True  # no filter — accept all
    skill_stages = set(skill.get("allowed_stages", []))
    return bool(skill_stages & set(stage_kinds))


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_skill_candidates (
            id TEXT PRIMARY KEY,
            workflow_key TEXT NOT NULL,
            skill_key TEXT NOT NULL,
            name TEXT NOT NULL,
            github_url TEXT NOT NULL,
            repo TEXT NOT NULL,
            path TEXT,
            summary TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            detail_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.commit()


def already_stored(conn: sqlite3.Connection, repo: str, path: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM github_skill_candidates WHERE repo = ? AND path = ? LIMIT 1",
        (repo, path),
    ).fetchone()
    return row is not None


def upsert_candidate(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    skill: dict,
    repo: str,
    file_path: str,
    html_url: str,
) -> None:
    candidate_id = f"ghskill-{uuid.uuid4()}"
    tags = skill.get("allowed_stages", [])
    detail = {
        "invariants": skill.get("invariants", []),
        "failure_conditions": skill.get("failure_conditions", []),
        "execution_mode": skill.get("execution_mode", "heuristic"),
        "signal_score": skill.get("signal_score", 0),
        "raw_frontmatter": skill.get("raw_frontmatter", {}),
    }
    conn.execute(
        """
        INSERT INTO github_skill_candidates
            (id, workflow_key, skill_key, name, github_url, repo, path,
             summary, tags_json, detail_json, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate')
        ON CONFLICT DO NOTHING
        """,
        (
            candidate_id,
            workflow_key,
            skill["key"],
            skill["key"].replace("_", " ").title(),
            html_url,
            repo,
            file_path,
            skill["purpose"] or f"Skill from {repo}",
            json.dumps(tags),
            json.dumps(detail),
        ),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover GitHub skill candidates for AIOS workflows."
    )
    parser.add_argument(
        "--workflow-key", default="", help="Filter to skills matching this workflow's stages"
    )
    parser.add_argument(
        "--query", default="", help="Custom GitHub code search query (overrides defaults)"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Max candidates to store (default 20)"
    )
    parser.add_argument("--token", default="", help="GitHub token (defaults to `gh auth token`)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to aios.db")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = get_token(args.token)
    if not token:
        print(
            "WARNING: No GitHub token found. Rate limits will be strict (10 req/min).",
            file=sys.stderr,
        )

    aios_db = Path(args.db).expanduser()
    if not aios_db.exists() and not args.dry_run:
        print(f"ERROR: DB not found: {aios_db}", file=sys.stderr)
        sys.exit(1)

    stage_kinds: list[str] = []
    if args.workflow_key:
        stage_kinds = load_workflow_stage_kinds(args.workflow_key)
        print(f"Filtering to workflow '{args.workflow_key}' stage kinds: {stage_kinds}")

    queries = [args.query] if args.query else DEFAULT_QUERIES
    workflow_key = args.workflow_key or "general"

    aios_conn: sqlite3.Connection | None = None
    if not args.dry_run:
        aios_conn = sqlite3.connect(str(aios_db))
        ensure_table(aios_conn)

    stored = 0
    skipped_dupe = 0
    skipped_no_parse = 0
    skipped_no_match = 0
    errors: list[str] = []

    for query in queries:
        if stored >= args.limit:
            break
        print(f"\nSearching: {query!r}")
        try:
            items = search_code(query, token, per_page=min(30, args.limit * 2))
        except RuntimeError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            break

        print(f"  {len(items)} results")
        time.sleep(REQUEST_DELAY)

        for item in items:
            if stored >= args.limit:
                break

            repo = item.get("repository", {}).get("full_name", "")
            file_path = item.get("path", "")
            html_url = item.get("html_url", "")

            if not repo or not file_path:
                continue

            # Skip already-stored
            if aios_conn and already_stored(aios_conn, repo, file_path):
                skipped_dupe += 1
                continue

            # Fetch raw content
            if args.verbose:
                print(f"  Fetching {repo}/{file_path}")
            content = fetch_raw(repo, file_path, token)
            time.sleep(0.5)

            if not content:
                skipped_no_parse += 1
                continue

            # Parse
            if file_path.endswith(".json"):
                skill = extract_skill_from_json(content)
            else:
                skill = extract_skill_from_markdown(content, Path(file_path).name)

            if not skill or not skill["key"]:
                skipped_no_parse += 1
                continue

            # Check stage relevance
            if stage_kinds and not skill_matches_workflow(skill, stage_kinds):
                skipped_no_match += 1
                if args.verbose:
                    print(f"    skip: stages {skill['allowed_stages']} don't match {stage_kinds}")
                continue

            if args.dry_run:
                print(f"  [DRY RUN] would store: {skill['key']!r} from {repo}/{file_path}")
                print(f"    purpose: {skill['purpose'][:80]}")
                print(f"    stages:  {skill['allowed_stages']}")
                stored += 1
                continue

            try:
                upsert_candidate(
                    aios_conn,
                    workflow_key=workflow_key,
                    skill=skill,
                    repo=repo,
                    file_path=file_path,
                    html_url=html_url,
                )
                aios_conn.commit()
                stored += 1
                print(f"  ✓ {skill['key']!r} — {repo}/{file_path}")
                if args.verbose:
                    print(f"    purpose: {skill['purpose'][:80]}")
                    print(f"    stages:  {skill['allowed_stages']}")
            except Exception as exc:
                errors.append(f"{repo}/{file_path}: {exc}")

    if aios_conn:
        aios_conn.close()

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Summary")
    print(f"  Stored      : {stored}")
    print(f"  Dupes skip  : {skipped_dupe}")
    print(f"  No parse    : {skipped_no_parse}")
    print(f"  No match    : {skipped_no_match}")
    print(f"  Errors      : {len(errors)}")
    for err in errors:
        print(f"    ERROR: {err}", file=sys.stderr)


if __name__ == "__main__":
    main()
