#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----)"
)

BBDSE_CHILDREN = [
    "BBDS-Analytics-Product-Suite",
    "CLFE",
    "Cap-Fit Builder",
    "Coach Value Over Expected",
    "RTE",
    "RTE Transferable Signals",
    "SMWI",
    "Signal Lab",
    "Versatility Tax",
    "Womens Stats",
]

INDEPENDENT_CHILDREN = ["LIS"]


def _markdown_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.md")
        if ".git" not in path.parts and not any(part.startswith(".obsidian") for part in path.parts)
    ]


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _check_secret_free(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_PATTERN.search(text):
            failures.append(f"secret_pattern:{_relative(path, root)}")
    return failures


def _check_frontmatter(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            continue
        lines = text.splitlines()
        if len(lines) < 2 or "---" not in lines[1:]:
            failures.append(f"frontmatter_unclosed:{_relative(path, root)}")
    return failures


def _check_wikilinks(root: Path, paths: list[Path]) -> list[str]:
    failures: list[str] = []
    names = {path.stem for path in paths}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"\[\[([^\]|#]+)", text):
            target = match.group(1).strip()
            if target and target not in names:
                failures.append(f"wikilink_missing:{_relative(path, root)}->{target}")
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
    protected_tmp = [path for path in markdown if path.name.startswith(".tmp-")]
    failures.extend(f"protected_tmp_markdown:{_relative(path, root)}" for path in protected_tmp)
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
    for child in BBDSE_CHILDREN + INDEPENDENT_CHILDREN:
        child_path = root / child
        if not child_path.exists():
            failures.append(f"missing_child:{child}")
            continue
        if child in BBDSE_CHILDREN and not (child_path / ".pre-cr.json").exists():
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
        f"delegated_children={len(BBDSE_CHILDREN)} independent_children={len(INDEPENDENT_CHILDREN)}"
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
