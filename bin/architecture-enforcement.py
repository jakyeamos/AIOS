#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.architecture_enforcement import run_enforcement  # noqa: E402


def _project_is_actionable(project: dict) -> bool:
    return project["status"] not in {"missing", "skipped"}


def _print_human(report: dict) -> None:
    for project in report["projects"]:
        print(f"{project['project_id']} [{project['status']}]")
        for profile in project["profiles"]:
            print(f"  - {profile['profile_id']} [{profile['status']}]")
            for adapter in profile["adapters"]:
                print(f"    - {adapter['adapter_id']} [{adapter['status']}]")
                for violation in adapter["violations"]:
                    print(f"      * {violation['code']}: {violation['message']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run AIOS architecture-enforcement checks from profile adapters."
    )
    parser.add_argument("--project", help="Run one project id from projects.json")
    parser.add_argument("--all-projects", action="store_true", help="Run all configured projects")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if args.project and args.all_projects:
        raise SystemExit("--project and --all-projects are mutually exclusive")

    project_ids = None
    if args.project:
        project_ids = [args.project]
    elif not args.all_projects:
        project_ids = ["aios"]

    report = run_enforcement(project_ids=project_ids)
    actionable_projects = [project for project in report["projects"] if _project_is_actionable(project)]
    failures = [
        project for project in actionable_projects if project["status"] in {"failed", "error"}
    ]

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
