#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.execution_strategy import (  # noqa: E402
    StrategySelectionError,
    build_strategy_registry_snapshot,
    load_strategy_catalog,
    load_task_specs,
    validate_strategy_catalog,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-root",
        default=str(ROOT / "config" / "execution-strategies"),
        help="Execution strategy config root",
    )
    args = parser.parse_args()

    config_root = Path(args.config_root).expanduser().resolve()
    task_specs_path = config_root / "task-specs.json"
    strategies_path = config_root / "strategies.json"
    registry_path = config_root / "registry.json"

    try:
        task_specs = load_task_specs(task_specs_path)
        strategy_catalog = load_strategy_catalog(strategies_path)
        errors = validate_strategy_catalog(task_specs, strategy_catalog)
        if errors:
            print("Execution strategy validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1

        snapshot = build_strategy_registry_snapshot(task_specs, strategy_catalog)
        payload = {
            "generated_at": _now_iso(),
            "task_specs_file": str(task_specs_path),
            "strategies_file": str(strategies_path),
            "task_families": sorted(task_specs.keys()),
            "selection": snapshot["strategy_selection"],
        }
        registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(
            "Execution strategy validation passed: "
            f"task_families={len(task_specs)} "
            f"strategies={len(snapshot['strategy_selection'])} "
            f"registry={registry_path}"
        )
        return 0
    except StrategySelectionError as exc:
        print(f"Execution strategy validation failed: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"Execution strategy validation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
