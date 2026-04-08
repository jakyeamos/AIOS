#!/usr/bin/env python3
"""
AIOS: vault-search.py
Thin search wrapper over the Obsidian vault filesystem.

Modes:
  --note <project_name>               Return project note content
  --grep <terms> [--section <h2>]     Grep vault, return matches with context
  --handoffs <project_name> --last N  Return last N handoff notes for project
  --tags <tag1,tag2>                  Return notes matching all specified tags

Scope modifiers:
  --source archive    Restrict grep to 09 Archive/ subdirectory only

Output: JSON — {results: [{path, title, excerpt, tags}], count: N}
Capped at 5 results. Total output kept under 500 tokens (~375 words).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

VAULT = os.path.expanduser("~/Vaults/Command-Center")
ARCHIVE_DIR = os.path.join(VAULT, "09 Archive")
MAX_RESULTS = 5
MAX_EXCERPT_CHARS = 300


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter fields as a dict. Returns {} if none."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = text[3:end].strip()
    result = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    # Handle tags list
    tags_match = re.search(r"^tags:\s*\n((?:\s+-\s+.+\n?)+)", text[:end + 4], re.MULTILINE)
    if tags_match:
        result["tags"] = re.findall(r"-\s+(.+)", tags_match.group(1))
    return result


def get_title(text: str, path: str) -> str:
    """Derive title from first H1 or filename."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return Path(path).stem


def excerpt(text: str, max_chars: int = MAX_EXCERPT_CHARS) -> str:
    """Return first substantive lines of content (skip frontmatter)."""
    # Skip frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip()
    # Skip H1
    text = re.sub(r"^#\s+.+\n", "", text, count=1)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    return truncated[:last_space] + "…" if last_space > 0 else truncated + "…"


def walk_vault(root_dir: str | None = None) -> list[tuple[str, str]]:
    """Yield (path, content) for all .md files under root_dir (default: full vault)."""
    search_root = root_dir if root_dir else VAULT
    results = []
    for root, dirs, files in os.walk(search_root):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.endswith(".md"):
                full_path = os.path.join(root, fname)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    results.append((full_path, content))
                except Exception:
                    pass
    return results


def mode_note(project_name: str) -> dict:
    """Return the project note for a given project name."""
    projects_dir = os.path.join(VAULT, "03 Projects")
    candidates = [
        os.path.join(projects_dir, f"{project_name}.md"),
        os.path.join(projects_dir, f"{project_name.capitalize()}.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            fm = parse_frontmatter(content)
            return {
                "results": [{
                    "path": path,
                    "title": get_title(content, path),
                    "excerpt": excerpt(content, 600),
                    "tags": fm.get("tags", []),
                }],
                "count": 1,
            }
    return {"results": [], "count": 0, "error": f"No project note found for '{project_name}'"}


def mode_grep(terms: str, section: str | None = None, source: str | None = None) -> dict:
    """Search vault for notes containing all terms."""
    term_list = [t.lower() for t in terms.split() if len(t) > 2]
    if not term_list:
        return {"results": [], "count": 0, "error": "No valid search terms"}

    search_root = ARCHIVE_DIR if source == "archive" else None
    matches = []
    for path, content in walk_vault(search_root):
        search_content = content.lower()
        if not all(t in search_content for t in term_list):
            continue
        # If section filter, check that section exists and contains terms
        if section:
            sec_pattern = re.compile(rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)", re.DOTALL | re.IGNORECASE)
            sec_match = sec_pattern.search(content)
            if not sec_match:
                continue
            sec_text = sec_match.group(1).lower()
            if not all(t in sec_text for t in term_list):
                continue
        fm = parse_frontmatter(content)
        mtime = os.path.getmtime(path)
        matches.append((mtime, path, content, fm))

    matches.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, path, content, fm in matches[:MAX_RESULTS]:
        results.append({
            "path": path,
            "title": get_title(content, path),
            "excerpt": excerpt(content),
            "tags": fm.get("tags", []),
        })
    return {"results": results, "count": len(results)}


def mode_handoffs(project_name: str, last: int = 3) -> dict:
    """Return the last N session handoff notes for a project."""
    handoffs_dir = os.path.join(VAULT, "02 AI OS", "02 Session Handoffs")
    if not os.path.exists(handoffs_dir):
        return {"results": [], "count": 0, "error": "Handoffs directory not found"}

    project_lower = project_name.lower()
    candidates = []
    for fname in os.listdir(handoffs_dir):
        if not fname.endswith(".md"):
            continue
        if project_lower not in fname.lower():
            continue
        full_path = os.path.join(handoffs_dir, fname)
        mtime = os.path.getmtime(full_path)
        candidates.append((mtime, full_path, fname))

    candidates.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, path, fname in candidates[:last]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        # Extract key sections for handoffs
        handoff_excerpt = _extract_handoff_sections(content)
        results.append({
            "path": path,
            "title": fname.replace(".md", ""),
            "excerpt": handoff_excerpt,
            "tags": fm.get("tags", []),
            "started": fm.get("started", ""),
        })
    return {"results": results, "count": len(results)}


def _extract_handoff_sections(content: str) -> str:
    """Extract Outcome, Key Changes, and Next Actions from a handoff note."""
    sections = ["Outcome", "Key Changes", "Decisions", "Next Actions"]
    parts = []
    for sec in sections:
        pattern = re.compile(rf"## {sec}\n(.*?)(?=\n## |\Z)", re.DOTALL)
        m = pattern.search(content)
        if m:
            text = m.group(1).strip()
            if text and not text.startswith("<!--"):
                parts.append(f"### {sec}\n{text[:200]}")
    return "\n\n".join(parts)[:MAX_EXCERPT_CHARS * 2]


def mode_tags(tags_str: str) -> dict:
    """Return notes matching all specified tags."""
    required_tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
    if not required_tags:
        return {"results": [], "count": 0, "error": "No tags specified"}

    matches = []
    for path, content in walk_vault():
        fm = parse_frontmatter(content)
        note_tags = [t.lower() for t in fm.get("tags", [])]
        if all(rt in note_tags for rt in required_tags):
            mtime = os.path.getmtime(path)
            matches.append((mtime, path, content, fm))

    matches.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, path, content, fm in matches[:MAX_RESULTS]:
        results.append({
            "path": path,
            "title": get_title(content, path),
            "excerpt": excerpt(content),
            "tags": fm.get("tags", []),
        })
    return {"results": results, "count": len(results)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the Obsidian vault")
    parser.add_argument("--note", help="Project name to retrieve project note")
    parser.add_argument("--grep", help="Terms to search for (space-separated)")
    parser.add_argument("--section", help="Limit grep to a specific H2 section")
    parser.add_argument("--source", choices=["archive"], help="Restrict search scope (archive = 09 Archive/)")
    parser.add_argument("--handoffs", help="Project name to retrieve handoff notes")
    parser.add_argument("--last", type=int, default=3, help="Number of handoffs to return (default: 3)")
    parser.add_argument("--tags", help="Comma-separated tags — return notes matching all")
    args = parser.parse_args()

    if args.note:
        result = mode_note(args.note)
    elif args.grep:
        result = mode_grep(args.grep, section=args.section, source=args.source)
    elif args.handoffs:
        result = mode_handoffs(args.handoffs, last=args.last)
    elif args.tags:
        result = mode_tags(args.tags)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
