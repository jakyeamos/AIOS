#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|SECRET_KEY|-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----)",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
REQUIRED_TRUSTED_FIELDS = [
    "type",
    "status",
    "quality",
    "trust",
    "sensitivity",
    "tags",
    "created",
    "updated",
    "last_reviewed",
    "source",
    "related",
]
TRUSTED_ROOTS = {
    "00 Maps",
    "01 Dashboard",
    "02 AI OS",
    "03 Projects",
    "04 Personal",
    "05 Areas",
    "06 Knowledge",
    "07 Templates",
    "08 Bases",
}
RAW_ROOTS = {"09 Archive", "Personal-Corpus", "Quarantine"}
GENERIC_TITLES = {"new note", "untitled document", "untitled spreadsheet", "todo", "to do", "add", "dd", "the"}

BBDSE_CHILDREN = [
    "BBDS-Analytics-Product-Suite",
    "CLFE",
    "Cap-Fit Builder",
    "Coach Value Over Expected",
    "LIS",
    "RTE",
    "RTE Transferable Signals",
    "SMWI",
    "Signal Lab",
    "Versatility Tax",
    "Womens Stats",
]


def _markdown_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.md")
        if ".git" not in path.parts and not any(part.startswith(".obsidian") for part in path.parts)
    ]


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _safe_relative(path: Path, root: Path) -> str:
    relative = _relative(path, root)
    relative = SECRET_PATTERN.sub("<redacted-secret>", relative)
    return PHONE_PATTERN.sub("<redacted-phone>", relative)


def _is_under(path: Path, root: str) -> bool:
    return root in path.parts


def _is_quarantine(path: Path) -> bool:
    return _is_under(path, "Quarantine")


def _is_archive_or_raw(path: Path) -> bool:
    return any(_is_under(path, part) for part in RAW_ROOTS)


def _frontmatter_and_body(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    frontmatter = text[4:end].strip()
    body = text[end + 4 :].lstrip("\n")
    parsed: dict[str, str] = {}
    current_key = ""
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "-")):
            if current_key and parsed.get(current_key, "") == "":
                parsed[current_key] = "list"
            continue
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        current_key = key.strip()
        parsed[current_key] = raw_value.strip().strip('"')
    return parsed, body


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, _body = _frontmatter_and_body(text)
    return frontmatter


def _trust_for(path: Path, frontmatter: dict[str, str]) -> str:
    if frontmatter.get("trust"):
        return frontmatter["trust"]
    if _is_quarantine(path):
        return "quarantine"
    if _is_under(path, ".aios") and _is_under(path, "audit"):
        return "raw"
    if _is_under(path, "02 Session Handoffs"):
        return "raw"
    if _is_archive_or_raw(path):
        return "raw"
    return "working"


def _trusted_candidate(path: Path, frontmatter: dict[str, str]) -> bool:
    trust = _trust_for(path, frontmatter)
    return trust in {"trusted", "working"} and not _is_quarantine(path)


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+", text))


def _title_key(path: Path) -> str:
    stem = re.sub(r"\([0-9]+\)$", "", path.stem).strip()
    return re.sub(r"\s+", " ", stem).lower()


def _strip_fenced_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _known_wikilink_targets(root: Path, paths: list[Path]) -> set[str]:
    targets: set[str] = set()
    for path in paths:
        relative = path.relative_to(root)
        no_suffix = relative.with_suffix("")
        targets.add(path.stem)
        targets.add(str(no_suffix))
        if relative.parts and relative.parts[0] == "Command-Center":
            targets.add(str(Path(*relative.parts[1:]).with_suffix("")))
    return targets


def _check_secret_free(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        if _is_quarantine(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_PATTERN.search(f"{path.name}\n{text}"):
            failures.append(f"unsafe_content:{_safe_relative(path, root)}:secret_pattern")
    return failures


def _check_frontmatter(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            continue
        lines = text.splitlines()
        if len(lines) < 2 or "---" not in lines[1:]:
            failures.append(f"frontmatter_unclosed:{_safe_relative(path, root)}")
    return failures


def _check_wikilinks(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    targets = _known_wikilink_targets(root, paths)
    for path in paths:
        frontmatter = _frontmatter(path)
        if not _trusted_candidate(path, frontmatter):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = _strip_fenced_code(text)
        for match in re.finditer(r"\[\[([^\]|#]+)", text):
            target = match.group(1).strip()
            if target and target not in targets:
                failures.append(f"broken_trusted_wikilink:{_safe_relative(path, root)}->{target}")
    return failures


def _check_trusted_metadata(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        frontmatter = _frontmatter(path)
        if not _trusted_candidate(path, frontmatter):
            continue
        missing = [field for field in REQUIRED_TRUSTED_FIELDS if not frontmatter.get(field)]
        if "area" not in frontmatter and "project" not in frontmatter:
            missing.append("area_or_project")
        for field in missing:
            failures.append(f"missing_metadata:{_safe_relative(path, root)}:{field}")
    return failures


def _check_stale_trusted_notes(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    cutoff = date.today().toordinal() - 180
    for path in paths:
        frontmatter = _frontmatter(path)
        if not _trusted_candidate(path, frontmatter):
            continue
        reviewed = frontmatter.get("last_reviewed")
        if not reviewed:
            continue
        try:
            reviewed_date = date.fromisoformat(reviewed[:10])
        except ValueError:
            failures.append(f"stale_note_invalid_date:{_safe_relative(path, root)}:last_reviewed")
            continue
        if reviewed_date.toordinal() < cutoff:
            failures.append(f"stale_trusted_note:{_safe_relative(path, root)}:last_reviewed={reviewed[:10]}")
    return failures


def _check_raw_notes_in_trusted_areas(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        frontmatter = _frontmatter(path)
        trust = _trust_for(path, frontmatter)
        first = path.relative_to(root).parts[0]
        if first in TRUSTED_ROOTS and trust in {"raw", "quarantine"}:
            failures.append(f"raw_in_trusted_area:{_safe_relative(path, root)}:trust={trust}")
    return failures


def _check_quarantine_candidates(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        if _is_quarantine(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        frontmatter, body = _frontmatter_and_body(text)
        combined = f"{path.name}\n{text}"
        if path.name.startswith(".tmp-"):
            failures.append(f"quarantine_candidate:{_safe_relative(path, root)}:tmp")
        elif SECRET_PATTERN.search(combined):
            failures.append(f"quarantine_candidate:{_safe_relative(path, root)}:secret_like")
        elif PHONE_PATTERN.search(combined):
            failures.append(f"quarantine_candidate:{_safe_relative(path, root)}:phone_like")
        elif _is_under(path, "Personal-Corpus") and not frontmatter and (
            _word_count(body) <= 12 or _title_key(path) in GENERIC_TITLES
        ):
            failures.append(f"quarantine_candidate:{_safe_relative(path, root)}:low_context")
    return failures


def validate_vault(root: Path) -> int:
    failures: list[str] = []
    required = ["README.md", ".tracker/PROJECT_TRUTH.md", ".obsidian", "Command-Center"]
    for item in required:
        if not (root / item).exists():
            failures.append(f"missing_required:{item}")
    markdown = _markdown_files(root)
    if not markdown:
        failures.append("missing_markdown_content")
    failures.extend(_check_secret_free(root, markdown))
    failures.extend(_check_frontmatter(root, markdown))
    failures.extend(_check_wikilinks(root, markdown))
    failures.extend(_check_trusted_metadata(root, markdown))
    failures.extend(_check_stale_trusted_notes(root, markdown))
    failures.extend(_check_raw_notes_in_trusted_areas(root, markdown))
    failures.extend(_check_quarantine_candidates(root, markdown))
    if failures:
        print("\n".join(failures))
        return 1
    print(f"vault_validation_pass markdown_files={len(markdown)}")
    return 0


def _precr_status(path: Path) -> str:
    if not (path / ".pre-cr.json").exists():
        return "missing_pre_cr"
    result = subprocess.run(
        ["pre-cr", "run", "--json", "--workspace", str(path)],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if result.returncode == 0:
        return "pass"
    return f"fail:{result.returncode}"


def validate_bbdse(root: Path, *, run_delegated: bool) -> int:
    failures: list[str] = []
    required_docs = ["docs/project-truth.md", "docs/child-project-ownership.md"]
    for item in required_docs:
        if not (root / item).exists():
            failures.append(f"missing_required:{item}")
    for child in BBDSE_CHILDREN:
        child_path = root / child
        if not child_path.exists():
            failures.append(f"missing_child:{child}")
            continue
        if not (child_path / ".pre-cr.json").exists():
            failures.append(f"missing_child_pre_cr:{child}")
    if not failures and run_delegated:
        statuses = {child: _precr_status(root / child) for child in BBDSE_CHILDREN}
        for child, status in statuses.items():
            print(f"delegated_pre_cr {child}: {status}")
            if status != "pass":
                failures.append(f"delegated_pre_cr_{status}:{child}")
    if failures:
        print("\n".join(failures))
        return 1
    print(
        "bbdse_validation_pass "
        f"delegated_children={len(BBDSE_CHILDREN)} independent_children=0"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AIOS content/container linked repos.")
    parser.add_argument("--project", choices=["Vaults", "BBDSE"], required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-delegated", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.expanduser().resolve()
    if args.project == "Vaults":
        return validate_vault(root)
    return validate_bbdse(root, run_delegated=args.run_delegated)


if __name__ == "__main__":
    raise SystemExit(main())
