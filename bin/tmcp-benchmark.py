#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.tmcp_benchmark import (  # noqa: E402
    aggregate_results,
    create_benchmark_scaffold,
    freeze_benchmark,
    import_task_manifest,
    preflight_benchmark,
    randomize_condition_map,
    refresh_discovery,
    run_task_condition,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage the TMCP multi-project benchmark scaffold."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--parent", type=Path, default=ROOT.parent)
    init_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")

    discover_parser = subparsers.add_parser("discover")
    discover_parser.add_argument("--parent", type=Path, default=ROOT.parent)
    discover_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    preflight_parser.add_argument("--preferred", nargs="*", default=["BIP-Console", "Bballedu"])

    task_parser = subparsers.add_parser("task")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)
    import_parser = task_subparsers.add_parser("import")
    import_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    import_parser.add_argument("--file", type=Path, required=True)

    condition_parser = subparsers.add_parser("conditions")
    condition_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    condition_parser.add_argument("--seed", type=int, required=True)
    condition_parser.add_argument("--repeats", type=int, default=1)

    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    freeze_parser.add_argument("--model-config", type=Path)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--task-id", required=True)
    run_parser.add_argument("--condition-id", required=True)
    run_parser.add_argument("--executor", default="stub")

    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--output", type=Path, default=ROOT / "tmcp-benchmark")
    args = parser.parse_args()

    if args.command == "init":
        result = create_benchmark_scaffold(parent_dir=args.parent, output_root=args.output)
    elif args.command == "discover":
        result = refresh_discovery(parent_dir=args.parent, output_root=args.output)
    elif args.command == "preflight":
        result = preflight_benchmark(
            output_root=args.output,
            preferred_projects=tuple(args.preferred),
        )
    elif args.command == "task" and args.task_command == "import":
        payload = json.loads(args.file.read_text(encoding="utf-8"))
        result = import_task_manifest(
            output_root=args.output,
            task_families=payload.get("task_families", []),
            tasks=payload.get("tasks", []),
        )
    elif args.command == "conditions":
        result = randomize_condition_map(
            output_root=args.output,
            seed=args.seed,
            repeats=args.repeats,
        )
    elif args.command == "freeze":
        model_config = {
            "model": "unset",
            "model_version": "unset",
            "reasoning_level": "unset",
            "tool_permissions": "local",
            "network_access": "disabled",
        }
        if args.model_config:
            model_config = json.loads(args.model_config.read_text(encoding="utf-8"))
        result = freeze_benchmark(output_root=args.output, model_config=model_config)
    elif args.command == "run":
        result = run_task_condition(
            output_root=args.output,
            run_id=args.run_id,
            task_id=args.task_id,
            condition_anonymous_id=args.condition_id,
            executor=args.executor,
        )
    elif args.command == "aggregate":
        result = aggregate_results(output_root=args.output)
    else:
        parser.error("Unsupported command.")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
