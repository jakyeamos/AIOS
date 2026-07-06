from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.pre_pr_readiness import (  # noqa: E402
    classify_changed_paths,
    summarize_pre_pr_readiness,
)


def test_classify_changed_paths_respects_aios_scope() -> None:
    classified = classify_changed_paths(
        [
            "services/aios_cli.py",
            "bin/hook-stop.py",
            "aios-ui/app/page.tsx",
            "tools/context-compile.mjs",
            "README.md",
            "config/quality-pipeline.json",
            "aios-ui/next-env.d.ts",
        ]
    )

    assert classified["supported"] == ["bin/hook-stop.py", "services/aios_cli.py"]
    assert classified["unsupported"] == ["aios-ui/app/page.tsx", "tools/context-compile.mjs"]
    assert classified["ignored"] == ["README.md", "aios-ui/next-env.d.ts", "config/quality-pipeline.json"]


def test_summarize_pre_pr_readiness_fails_on_unsupported_surfaces() -> None:
    summary = summarize_pre_pr_readiness(
        workspace_root=Path("/repo"),
        server_entry=Path("/pre-cr/server.js"),
        run_result={
            "result": {
                "changedFiles": [
                    {"path": "services/pre_pr_readiness.py"},
                    {"path": "aios-ui/app/page.tsx"},
                ],
                "health": {
                    "issues": [],
                },
                "testRun": {
                    "success": True,
                    "command": "uv run pytest --cov=.",
                    "exitCode": 0,
                },
                "coverageCheck": {
                    "passed": True,
                    "coveragePercent": 100,
                    "threshold": 80,
                },
            }
        },
    )

    assert summary["status"] == "fail"
    assert summary["unsupported_changed_files"] == ["aios-ui/app/page.tsx"]
    assert any(item["code"] == "unsupported_surface" for item in summary["findings"])
