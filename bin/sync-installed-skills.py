#!/usr/bin/env python3
"""
AIOS: sync-installed-skills.py
Scan ~/.agents/skills/ and ~/.claude/skills/ for installed superpowers
SKILL.md files and register them in config/workflows/skills.json so they
appear as toggleable skills in the workflow sandbox.

Superpowers skills use a different schema (name, description, allowed-tools)
than AIOS skills (key, purpose, allowed_stages, execution_mode).  This script
bridges the two: it reads the SKILL.md frontmatter, infers allowed_stages from
the skill's name/description, and upserts the entry into skills.json.

Skills already in skills.json are updated if the description changed.
Skills no longer installed are NOT removed (user may have added them manually).

Usage:
  python3 ~/AIOS/bin/sync-installed-skills.py [--dry-run] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_PATH = ROOT / "config" / "workflows" / "skills.json"

SKILL_DIRS = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]

# Skill directory prefixes that are infrastructure/orchestration tools,
# not workflow content skills. These are excluded from skills.json.
EXCLUDED_PREFIXES = (
    "gsd-", "gsd_",
    "opencli-", "opencli_",
    "claude-mem", "claude_mem",
    "skill-creator", "skill_creator",
    "commit-commands", "commit_commands",
    "claude-md", "claude_md",
)

# Map skill name keywords → likely allowed_stages
# Ordered most-specific first
STAGE_HINTS: list[tuple[list[str], list[str]]] = [
    (["humaniz", "prose", "rewrite", "edit"], ["transform"]),
    (["validat", "check", "verify", "lint", "review"], ["validate"]),
    (["generat", "draft", "write", "creat"], ["generate"]),
    (["retriev", "fetch", "search", "rag", "corpus", "context"], ["enrich_context"]),
    (["normaliz", "classif", "intent", "route", "parse"], ["normalize_prompt", "parse_request"]),
    (["debug", "fix", "diagnos"], ["generate", "validate"]),
    (["test", "spec", "coverage"], ["validate"]),
    (["deploy", "build", "ci", "pipeline"], ["finalize"]),
]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def infer_stages(name: str, description: str) -> list[str]:
    text = f"{name} {description}".lower()
    for keywords, stages in STAGE_HINTS:
        if any(kw in text for kw in keywords):
            return stages
    return ["generate"]  # safe default


def parse_frontmatter(text: str) -> dict:
    """Parse simple YAML frontmatter from a SKILL.md file."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: dict = {}
    current_key: str | None = None
    current_list: list[str] = []
    for line in m.group(1).splitlines():
        item_m = re.match(r"^\s+-\s+(.+)$", line)
        if item_m and current_key:
            current_list.append(item_m.group(1).strip().strip("\"'"))
            continue
        kv_m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if kv_m:
            if current_key and current_list:
                result[current_key] = current_list
            current_list = []
            key, value = kv_m.group(1), kv_m.group(2).strip().strip("\"'")
            if not value:
                current_key = key
            else:
                current_key = None
                result[key] = value
    if current_key and current_list:
        result[current_key] = current_list
    return result


def normalize_key(name: str) -> str:
    """Convert skill name to a snake_case key."""
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return key[:60] or "skill"


def skill_from_file(skill_dir: Path) -> dict | None:
    """Read a skill directory and return an AIOS skill spec, or None."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm = parse_frontmatter(content)
    if not fm:
        return None

    raw_name = str(fm.get("name") or skill_dir.name).strip()
    # Normalize: "react:components" → "react_components"
    name = re.sub(r"[^a-z0-9_]+", "_", raw_name.lower()).strip("_")
    key = name or normalize_key(skill_dir.name)

    # Description: can be multi-line YAML block (stored as string with newlines)
    raw_desc = fm.get("description", "")
    if isinstance(raw_desc, list):
        purpose = " ".join(raw_desc).strip()
    else:
        purpose = str(raw_desc).replace("\n", " ").strip()
    if not purpose:
        # Fall back to first non-empty body paragraph
        body = FRONTMATTER_RE.sub("", content).strip()
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                purpose = line[:300]
                break
    purpose = purpose[:300] or f"Installed skill: {raw_name}"

    allowed_stages = infer_stages(key, purpose)

    return {
        "key": key,
        "purpose": purpose,
        "allowed_stages": allowed_stages,
        "input_schema": {},
        "output_schema": {},
        "invariants": [],
        "failure_conditions": [],
        "side_effects": [],
        "execution_mode": "heuristic",
        "_source": str(skill_md),
        "_installed_name": raw_name,
    }


def load_skills_json() -> dict:
    if not SKILLS_PATH.exists():
        return {"version": "generated", "skills": []}
    return json.loads(SKILLS_PATH.read_text(encoding="utf-8"))


def save_skills_json(data: dict) -> None:
    SKILLS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync installed superpowers skills into skills.json."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Discover all installed skill directories
    found: dict[str, dict] = {}  # key → skill spec
    for base in SKILL_DIRS:
        if not base.exists():
            continue
        for skill_dir in sorted(base.iterdir()):
            if not skill_dir.is_dir():
                continue
            dir_name = skill_dir.name.lower()
            if any(dir_name.startswith(p) for p in EXCLUDED_PREFIXES):
                continue
            spec = skill_from_file(skill_dir)
            if spec is None:
                continue
            key = spec["key"]
            # De-duplicate across dirs (first found wins)
            if key not in found:
                found[key] = spec
                if args.verbose:
                    print(f"  found: {key!r} ({spec['_source']})")

    if not found:
        print("No installed skills found.")
        return

    print(f"Found {len(found)} installed skill(s).")

    data = load_skills_json()
    skills: list[dict] = data.get("skills", [])
    existing_keys = {s["key"]: i for i, s in enumerate(skills)}

    added: list[str] = []
    updated: list[str] = []

    for key, spec in found.items():
        # Strip internal metadata before writing
        clean = {k: v for k, v in spec.items() if not k.startswith("_")}

        if key in existing_keys:
            idx = existing_keys[key]
            old = skills[idx]
            if (
                old.get("purpose") != clean["purpose"]
                or old.get("allowed_stages") != clean["allowed_stages"]
            ):
                skills[idx] = {**old, **clean}  # preserve any manual fields
                updated.append(key)
        else:
            skills.append(clean)
            added.append(key)

    data["skills"] = skills

    prefix = "[DRY RUN] " if args.dry_run else ""
    if added:
        print(f"{prefix}Added: {', '.join(added)}")
    if updated:
        print(f"{prefix}Updated: {', '.join(updated)}")
    if not added and not updated:
        print("skills.json already up to date.")
        return

    if not args.dry_run:
        save_skills_json(data)
        print(f"Written → {SKILLS_PATH}")


if __name__ == "__main__":
    main()
