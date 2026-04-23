from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.architecture_enforcement import run_enforcement  # noqa: E402


def _write_registry(
    tmp_path: Path,
    *,
    profiles: list[dict],
    projects: list[dict],
) -> Path:
    config_dir = tmp_path / "config" / "architecture-enforcement"
    config_dir.mkdir(parents=True)
    (config_dir / "profiles.json").write_text(
        json.dumps({"version": "test", "profiles": profiles}),
        encoding="utf-8",
    )
    (config_dir / "projects.json").write_text(
        json.dumps({"version": "test", "projects": projects}),
        encoding="utf-8",
    )
    return config_dir


def test_python_profile_fails_when_services_import_bin(tmp_path: Path) -> None:
    (tmp_path / "bin").mkdir()
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "bin" / "runtime_helper.py").write_text(
        "def run() -> None:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "services" / "worker.py").write_text(
        "import runtime_helper\n",
        encoding="utf-8",
    )

    profiles = [
        {
            "id": "python-service-v1",
            "adapters": [
                {
                    "id": "python-import-boundaries",
                    "type": "python_import_rules",
                    "include": ["bin", "services"],
                    "layers_from_path": {"bin": "bin", "services": "services"},
                    "forbidden_imports": [
                        {
                            "source_layer": "services",
                            "target_layer": "bin",
                            "reason": "Services cannot import bin modules.",
                        }
                    ],
                    "fail_on_cycles": True,
                }
            ],
        }
    ]
    projects = [
        {
            "id": "demo",
            "name": "demo",
            "path": ".",
            "profile_bindings": [{"profile_id": "python-service-v1", "working_directory": "."}],
        }
    ]
    config_dir = _write_registry(tmp_path, profiles=profiles, projects=projects)
    report = run_enforcement(project_ids=["demo"], config_dir=config_dir, repo_root=tmp_path)

    assert report["ok"] is False
    adapter = report["projects"][0]["profiles"][0]["adapters"][0]
    assert adapter["status"] == "failed"
    assert any(v["code"] == "forbidden-import-layer" for v in adapter["violations"])


def test_python_profile_fails_on_cycles(tmp_path: Path) -> None:
    services = tmp_path / "services"
    services.mkdir()
    (services / "__init__.py").write_text("", encoding="utf-8")
    (services / "alpha.py").write_text("import services.beta\n", encoding="utf-8")
    (services / "beta.py").write_text("import services.alpha\n", encoding="utf-8")

    profiles = [
        {
            "id": "python-service-v1",
            "adapters": [
                {
                    "id": "python-import-boundaries",
                    "type": "python_import_rules",
                    "include": ["services"],
                    "layers_from_path": {"services": "services"},
                    "forbidden_imports": [],
                    "fail_on_cycles": True,
                }
            ],
        }
    ]
    projects = [
        {
            "id": "demo",
            "name": "demo",
            "path": ".",
            "profile_bindings": [{"profile_id": "python-service-v1", "working_directory": "."}],
        }
    ]
    config_dir = _write_registry(tmp_path, profiles=profiles, projects=projects)
    report = run_enforcement(project_ids=["demo"], config_dir=config_dir, repo_root=tmp_path)

    assert report["ok"] is False
    adapter = report["projects"][0]["profiles"][0]["adapters"][0]
    assert adapter["status"] == "failed"
    assert any(v["code"] == "dependency-cycle" for v in adapter["violations"])
