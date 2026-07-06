#!/usr/bin/env python3
"""
AIOS: discover-github-skills.py
For each stage in a workflow, understand what the step does, pull its
experiment performance signals, and search GitHub for repos/tools/prompts
that would improve that specific step.

This is NOT a format-matcher. It finds real-world resources — starred repos,
prompt libraries, techniques — and explains why each one is relevant to
the step it was found for. The user reviews and decides what to adopt.

Examples:
  - transform_prose step (humanizer) with low first_pass_success
    → suggests well-reviewed humanizer repos and prompt techniques
  - validate step (citation_checker) with frequent failures
    → suggests citation validation tools and LLM-based checkers
  - enrich_context step with high token cost
    → suggests efficient RAG patterns or retrieval compression tools

Usage:
  python3 ~/AIOS/bin/discover-github-skills.py --workflow-key academic_paper_v1
  python3 ~/AIOS/bin/discover-github-skills.py --workflow-key academic_paper_v1 --stage-key transform_prose
  python3 ~/AIOS/bin/discover-github-skills.py --list-stages academic_paper_v1
  python3 ~/AIOS/bin/discover-github-skills.py --dry-run --verbose
"""

from __future__ import annotations

import argparse
import contextlib
import json
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
REGISTRY_PATH = ROOT / "config" / "workflows" / "registry.json"
SKILLS_PATH = ROOT / "config" / "workflows" / "skills.json"

GITHUB_API = "https://api.github.com"
REQUEST_DELAY = 2.0  # seconds between API calls (stay inside rate limits)
MIN_STARS = 30  # minimum repo stars to surface as a suggestion

# ─── Stage → search strategy ─────────────────────────────────────────────────
#
# Each entry defines how to find GitHub resources for a given stage kind or
# stage key.  query_templates are formatted with {purpose} from the stage spec.
# topic_fallbacks are GitHub topic searches used when code search returns nothing.

STAGE_STRATEGIES: list[dict] = [
    {
        "match_kinds": ["transform"],
        "match_keys": ["humanize", "transform_prose", "humanizer"],
        "label": "Text humanization & prose quality",
        "query_templates": [
            '"humanize" "AI writing" prompt',
            "humanizer prose quality LLM prompt",
            '"writing style" "AI text" improvement',
        ],
        "repo_topics": ["humanizer", "ai-writing", "text-quality", "prose"],
        "repo_queries": [
            "AI writing humanizer",
            "humanizer prose quality LLM",
        ],
        "weakness_metric": "first_pass_success",
        "weakness_direction": "low",
    },
    {
        "match_kinds": ["validate"],
        "match_keys": ["citation_checker", "validate", "citation"],
        "label": "Validation & fact-checking",
        "query_templates": [
            "citation validation LLM",
            '"citation checker" prompt AI',
            "reference validation language model",
        ],
        "repo_topics": ["citation", "fact-checking", "validation", "llm-evaluation"],
        "repo_queries": ["citation checker LLM", "AI fact validation prompt"],
        "weakness_metric": "error_event_rate",
        "weakness_direction": "high",
    },
    {
        "match_kinds": ["validate"],
        "match_keys": ["structure_checker", "meaning_preservation"],
        "label": "Structure & meaning validation",
        "query_templates": [
            "LLM output structure validation prompt",
            '"semantic similarity" text validation',
        ],
        "repo_topics": ["llm-eval", "semantic-similarity", "text-validation"],
        "repo_queries": ["LLM output evaluation structure"],
        "weakness_metric": "first_pass_success",
        "weakness_direction": "low",
    },
    {
        "match_kinds": ["enrich_context"],
        "match_keys": ["enrich_context", "context", "retrieval"],
        "label": "Context retrieval & RAG",
        "query_templates": [
            "RAG retrieval augmented generation efficient",
            "context compression LLM prompt",
            '"personal corpus" retrieval AI writing',
        ],
        "repo_topics": ["rag", "retrieval-augmented-generation", "context-compression"],
        "repo_queries": [
            "RAG context retrieval efficient",
            "personal corpus LLM writing",
        ],
        "weakness_metric": "rtk.tokens_saved",
        "weakness_direction": "low",
    },
    {
        "match_kinds": ["generate"],
        "match_keys": ["draft", "generate", "academic_draft"],
        "label": "Draft generation quality",
        "query_templates": [
            "academic writing prompt AI generation",
            '"structured draft" LLM generation prompt',
            "section generation academic paper AI",
        ],
        "repo_topics": ["academic-writing", "llm-prompts", "writing-assistant"],
        "repo_queries": ["academic writing LLM draft generation"],
        "weakness_metric": "first_pass_success",
        "weakness_direction": "low",
    },
    {
        "match_kinds": ["normalize_prompt"],
        "match_keys": ["normalize_prompt", "normalizer"],
        "label": "Prompt normalization & intent extraction",
        "query_templates": [
            "prompt normalization intent extraction LLM",
            '"prompt template" matching classification',
        ],
        "repo_topics": ["prompt-engineering", "intent-classification", "prompt-library"],
        "repo_queries": ["prompt normalization template matching LLM"],
        "weakness_metric": "prompt_reuse_rate",
        "weakness_direction": "low",
    },
    {
        "match_kinds": ["parse_request"],
        "match_keys": ["parse_request", "parse"],
        "label": "Request parsing & decomposition",
        "query_templates": [
            "task decomposition LLM prompt parsing",
            '"request parsing" AI agent planning',
        ],
        "repo_topics": ["task-decomposition", "ai-planning", "llm-agents"],
        "repo_queries": ["task decomposition LLM planning"],
        "weakness_metric": "follow_up_turns",
        "weakness_direction": "high",
    },
]

# ─── Registry helpers ─────────────────────────────────────────────────────────


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"workflows": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_skills() -> list[dict]:
    if not SKILLS_PATH.exists():
        return []
    data = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    return data.get("skills", [])


def get_workflow(key: str) -> dict | None:
    for wf in load_registry().get("workflows", []):
        if wf.get("key") == key:
            return wf
    return None


def get_stage(workflow: dict, stage_key: str) -> dict | None:
    for stage in workflow.get("stages", []):
        if stage.get("key") == stage_key:
            return stage
    return None


# ─── Experiment / metric helpers ─────────────────────────────────────────────


def load_stage_metrics(db_path: Path, workflow_key: str) -> dict[str, float]:
    """Return {metric_name: avg_value} for this workflow from workflow_metrics."""
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            """
            SELECT metric_name, AVG(metric_value)
            FROM workflow_metrics
            WHERE session_id IN (
                SELECT id FROM sessions WHERE status = 'closed'
            )
            GROUP BY metric_name
            """,
        ).fetchall()
        return {row[0]: float(row[1]) for row in rows if row[1] is not None}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def weakness_signal(stage: dict, strategy: dict, metrics: dict[str, float]) -> str | None:
    """Return a human-readable weakness string if this stage underperforms, else None."""
    metric = strategy.get("weakness_metric", "")
    direction = strategy.get("weakness_direction", "low")
    value = metrics.get(metric)
    if value is None:
        return None
    if direction == "low" and value < 0.6:
        return f"{metric}={value:.2f} (below 0.60 threshold)"
    if direction == "high" and value > 0.3:
        return f"{metric}={value:.2f} (above 0.30 threshold)"
    return None


def strategy_for_stage(stage: dict) -> dict | None:
    kind = stage.get("kind", "")
    key = stage.get("key", "")
    skills = stage.get("required_skills", [])
    combined = f"{kind} {key} {' '.join(skills)}".lower()
    best: dict | None = None
    best_hits = 0
    for strategy in STAGE_STRATEGIES:
        hits = sum(1 for k in strategy["match_kinds"] if k == kind)
        hits += sum(1 for k in strategy["match_keys"] if k in combined)
        if hits > best_hits:
            best_hits = hits
            best = strategy
    return best if best_hits > 0 else None


# ─── GitHub API ───────────────────────────────────────────────────────────────


def get_token(token_arg: str) -> str:
    if token_arg:
        return token_arg
    with contextlib.suppress(Exception):
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    return ""


def gh_request(url: str, token: str) -> dict | list | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AIOS-skill-discovery/2.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        if exc.code in (403, 429):
            print("  rate limit hit, sleeping 30s...", file=sys.stderr)
            time.sleep(30)
        return None
    except Exception:
        return None


def search_repos(query: str, token: str, per_page: int = 5) -> list[dict]:
    encoded = quote(query)
    url = f"{GITHUB_API}/search/repositories?q={encoded}&sort=stars&order=desc&per_page={per_page}"
    result = gh_request(url, token)
    if isinstance(result, dict):
        return result.get("items", [])
    return []


def search_code(query: str, token: str, per_page: int = 5) -> list[dict]:
    encoded = quote(query)
    url = f"{GITHUB_API}/search/code?q={encoded}&per_page={per_page}"
    result = gh_request(url, token)
    if isinstance(result, dict):
        return result.get("items", [])
    return []


# ─── Candidate assembly ───────────────────────────────────────────────────────


def build_candidate(
    *,
    workflow_key: str,
    stage_key: str,
    stage_kind: str,
    strategy: dict,
    repo: dict,
    weakness: str | None,
    source: str,
) -> dict:
    stars = repo.get("stargazers_count", 0)
    description = repo.get("description") or ""
    full_name = repo.get("full_name", "")
    html_url = repo.get("html_url", "")
    topics = repo.get("topics", [])

    relevance = f"Suggested for '{stage_key}' ({stage_kind}) — {strategy['label']}."
    if weakness:
        relevance += f" Experiment signal: {weakness}."

    return {
        "workflow_key": workflow_key,
        "stage_key": stage_key,
        "skill_key": f"{stage_key}_inspiration_{full_name.replace('/', '_').replace('-', '_')[:30]}",
        "name": full_name,
        "github_url": html_url,
        "repo": full_name,
        "path": None,
        "summary": description[:300] or f"GitHub repo: {full_name}",
        "tags": topics[:8] + [stage_kind],
        "detail": {
            "stars": stars,
            "stage_key": stage_key,
            "stage_kind": stage_kind,
            "strategy_label": strategy["label"],
            "weakness_signal": weakness,
            "source": source,
            "relevance": relevance,
            "topics": topics,
        },
    }


# ─── DB ───────────────────────────────────────────────────────────────────────


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
    # Add stage_key column if it doesn't exist yet
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(github_skill_candidates)").fetchall()
    }
    if "stage_key" not in existing:
        conn.execute(
            "ALTER TABLE github_skill_candidates ADD COLUMN stage_key TEXT NOT NULL DEFAULT ''"
        )
    conn.commit()


def already_stored(conn: sqlite3.Connection, repo: str, workflow_key: str, stage_key: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM github_skill_candidates WHERE repo = ? AND workflow_key = ? AND stage_key = ? LIMIT 1",
        (repo, workflow_key, stage_key),
    ).fetchone()
    return row is not None


def store_candidate(conn: sqlite3.Connection, candidate: dict) -> None:
    conn.execute(
        """
        INSERT INTO github_skill_candidates
            (id, workflow_key, skill_key, name, github_url, repo, path,
             summary, tags_json, detail_json, stage_key, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate')
        """,
        (
            f"ghskill-{uuid.uuid4()}",
            candidate["workflow_key"],
            candidate["skill_key"],
            candidate["name"],
            candidate["github_url"],
            candidate["repo"],
            candidate["path"],
            candidate["summary"],
            json.dumps(candidate["tags"]),
            json.dumps(candidate["detail"]),
            candidate.get("stage_key", ""),
        ),
    )


# ─── Main ─────────────────────────────────────────────────────────────────────


def discover_for_stage(
    *,
    workflow_key: str,
    stage: dict,
    strategy: dict,
    metrics: dict[str, float],
    token: str,
    db_conn: sqlite3.Connection | None,
    dry_run: bool,
    verbose: bool,
    limit_per_stage: int,
) -> int:
    stage_key = stage.get("key", "")
    stage_kind = stage.get("kind", "")
    weakness = weakness_signal(stage, strategy, metrics)
    stored = 0

    print(f"\n  Stage: {stage_key} ({stage_kind})")
    print(f"  Strategy: {strategy['label']}")
    if weakness:
        print(f"  Weakness signal: {weakness}")
    else:
        print("  No weakness signal in current data (running discovery anyway)")

    seen_repos: set[str] = set()

    for repo_query in strategy["repo_queries"][:2]:
        if stored >= limit_per_stage:
            break
        if verbose:
            print(f"    Repo search: {repo_query!r}")
        repos = search_repos(repo_query, token, per_page=5)
        time.sleep(REQUEST_DELAY)

        for repo in repos:
            if stored >= limit_per_stage:
                break
            full_name = repo.get("full_name", "")
            stars = repo.get("stargazers_count", 0)
            if stars < MIN_STARS or full_name in seen_repos:
                continue
            seen_repos.add(full_name)

            if db_conn and already_stored(db_conn, full_name, workflow_key, stage_key):
                if verbose:
                    print(f"    skip dupe: {full_name}")
                continue

            candidate = build_candidate(
                workflow_key=workflow_key,
                stage_key=stage_key,
                stage_kind=stage_kind,
                strategy=strategy,
                repo=repo,
                weakness=weakness,
                source="repo_search",
            )

            if dry_run:
                print(f"    [DRY RUN] {full_name} ★{stars} — {repo.get('description', '')[:60]}")
            else:
                assert db_conn is not None  # dry_run=False always opens a connection
                store_candidate(db_conn, candidate)
                db_conn.commit()
                print(f"    ✓ {full_name} ★{stars} — {repo.get('description', '')[:60]}")
            stored += 1

    return stored


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover GitHub improvement suggestions for workflow stages."
    )
    parser.add_argument(
        "--workflow-key", default="", help="Workflow to analyse (e.g. academic_paper_v1)"
    )
    parser.add_argument(
        "--stage-key", default="", help="Only analyse this stage (default: all stages)"
    )
    parser.add_argument(
        "--list-stages", metavar="WORKFLOW_KEY", help="Print stages for a workflow and exit"
    )
    parser.add_argument(
        "--limit", type=int, default=3, help="Max suggestions per stage (default 3)"
    )
    parser.add_argument("--token", default="", help="GitHub token (defaults to `gh auth token`)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_stages:
        wf = get_workflow(args.list_stages)
        if not wf:
            print(f"Workflow not found: {args.list_stages}", file=sys.stderr)
            sys.exit(1)
        print(f"Stages in {args.list_stages}:")
        for stage in wf.get("stages", []):
            skills = ", ".join(stage.get("required_skills", [])) or "(none)"
            print(f"  {stage['key']:<30} kind={stage['kind']:<20} skills=[{skills}]")
        return

    token = get_token(args.token)
    if not token:
        print("WARNING: No GitHub token. Rate limits will be strict.", file=sys.stderr)

    # Resolve workflow
    workflow_key = args.workflow_key
    if not workflow_key:
        # Default to first registered workflow
        workflows = load_registry().get("workflows", [])
        if not workflows:
            print("No workflows registered. Run synthesize-workflows.py first.", file=sys.stderr)
            sys.exit(1)
        workflow_key = workflows[0]["key"]
        print(f"No --workflow-key given, defaulting to: {workflow_key}")

    workflow = get_workflow(workflow_key)
    if not workflow:
        print(f"Workflow not found: {workflow_key}", file=sys.stderr)
        sys.exit(1)

    stages = workflow.get("stages", [])
    if args.stage_key:
        stage = get_stage(workflow, args.stage_key)
        if not stage:
            print(f"Stage not found: {args.stage_key}", file=sys.stderr)
            sys.exit(1)
        stages = [stage]

    db_path = Path(args.db).expanduser()
    metrics = load_stage_metrics(db_path, workflow_key)
    if metrics and args.verbose:
        print(f"Loaded {len(metrics)} metric(s) for context")

    db_conn: sqlite3.Connection | None = None
    if not args.dry_run:
        if not db_path.exists():
            print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
            sys.exit(1)
        db_conn = sqlite3.connect(str(db_path))
        ensure_table(db_conn)

    total = 0
    skipped_no_strategy = []

    print(f"\nAnalysing workflow: {workflow_key} ({len(stages)} stage(s))")
    for stage in stages:
        strategy = strategy_for_stage(stage)
        if not strategy:
            skipped_no_strategy.append(stage.get("key", "?"))
            continue
        n = discover_for_stage(
            workflow_key=workflow_key,
            stage=stage,
            strategy=strategy,
            metrics=metrics,
            token=token,
            db_conn=db_conn,
            dry_run=args.dry_run,
            verbose=args.verbose,
            limit_per_stage=args.limit,
        )
        total += n

    if db_conn:
        db_conn.close()

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Done")
    print(f"  Suggestions stored: {total}")
    if skipped_no_strategy:
        print(f"  No strategy for:  {', '.join(skipped_no_strategy)}")


if __name__ == "__main__":
    main()
