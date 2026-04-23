from __future__ import annotations

import ast
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = REPO_ROOT / "config" / "architecture-enforcement"


@dataclass(frozen=True)
class ProjectConfig:
    id: str
    name: str
    path: Path
    profile_bindings: list[dict[str, Any]]
    proof_target: bool


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_path(path: str, *, base: Path) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    return (base / expanded).resolve()


def load_registry(config_dir: Path = DEFAULT_CONFIG_DIR, repo_root: Path = REPO_ROOT) -> tuple[
    dict[str, dict[str, Any]], list[ProjectConfig]
]:
    profiles_path = config_dir / "profiles.json"
    projects_path = config_dir / "projects.json"

    profiles_raw = _read_json(profiles_path)
    projects_raw = _read_json(projects_path)

    profiles: dict[str, dict[str, Any]] = {}
    for item in profiles_raw.get("profiles", []):
        profile_id = item.get("id")
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError(f"Invalid profile id in {profiles_path}")
        profiles[profile_id] = item

    projects: list[ProjectConfig] = []
    for item in projects_raw.get("projects", []):
        project_id = item.get("id")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError(f"Invalid project id in {projects_path}")
        projects.append(
            ProjectConfig(
                id=project_id,
                name=str(item.get("name", project_id)),
                path=_resolve_path(str(item.get("path", ".")), base=repo_root),
                profile_bindings=list(item.get("profile_bindings", [])),
                proof_target=bool(item.get("proof_target", False)),
            )
        )
    return profiles, projects


def _is_identifier(stem: str) -> bool:
    return stem.isidentifier()


def _module_name_for_file(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root)
    parts = list(relative.parts)
    if not parts:
        return None

    if parts[0] == "services":
        module_parts = [*parts]
        module_parts[-1] = path.stem
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        return ".".join(module_parts) if module_parts else None

    if parts[0] == "bin":
        stem = path.stem
        if _is_identifier(stem):
            return stem
        return None

    return None


def _layer_for_path(path: Path, root: Path, layers_from_path: dict[str, str]) -> str | None:
    relative = path.relative_to(root).as_posix()
    for prefix, layer in layers_from_path.items():
        normalized = prefix.rstrip("/")
        if relative == normalized or relative.startswith(f"{normalized}/"):
            return layer
    return None


def _resolve_relative_import(module_name: str, import_module: str | None, level: int) -> str | None:
    if level <= 0:
        return import_module

    module_parts = module_name.split(".")
    package_parts = module_parts[:-1]
    if level - 1 > len(package_parts):
        return None
    keep = len(package_parts) - (level - 1)
    prefix_parts = package_parts[:keep]
    if import_module:
        return ".".join([*prefix_parts, import_module])
    return ".".join(prefix_parts) if prefix_parts else None


def _extract_imports(file_path: Path, module_name: str | None) -> list[str]:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        if isinstance(node, ast.ImportFrom):
            resolved = _resolve_relative_import(module_name or "", node.module, node.level)
            if resolved:
                imports.append(resolved)
    return imports


def _resolve_local_module(import_name: str, known_modules: set[str]) -> str | None:
    candidate = import_name
    while candidate:
        if candidate in known_modules:
            return candidate
        if "." not in candidate:
            break
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _target_layer(import_name: str, known_layers: dict[str, str]) -> str | None:
    candidate = import_name
    while candidate:
        layer = known_layers.get(candidate)
        if layer:
            return layer
        if "." not in candidate:
            break
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _tarjan_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def strong_connect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in indices:
                strong_connect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while stack:
                popped = stack.pop()
                on_stack.remove(popped)
                component.append(popped)
                if popped == node:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))
            elif component and component[0] in graph.get(component[0], set()):
                cycles.append(component)

    for node in graph:
        if node not in indices:
            strong_connect(node)
    return cycles


def _run_python_import_rules(adapter: dict[str, Any], working_dir: Path) -> dict[str, Any]:
    include = [str(item) for item in adapter.get("include", [])]
    layers_from_path = {
        str(key): str(value) for key, value in dict(adapter.get("layers_from_path", {})).items()
    }
    forbidden_imports = list(adapter.get("forbidden_imports", []))
    fail_on_cycles = bool(adapter.get("fail_on_cycles", True))

    python_files: list[Path] = []
    for rel in include:
        base = (working_dir / rel).resolve()
        if base.exists():
            python_files.extend(sorted(base.rglob("*.py")))

    module_to_file: dict[str, Path] = {}
    module_to_layer: dict[str, str] = {}
    for file_path in python_files:
        module_name = _module_name_for_file(file_path, working_dir)
        if not module_name:
            continue
        module_to_file[module_name] = file_path
        layer = _layer_for_path(file_path, working_dir, layers_from_path)
        if layer:
            module_to_layer[module_name] = layer

    graph: dict[str, set[str]] = {module: set() for module in module_to_file}
    violations: list[dict[str, Any]] = []
    known_modules = set(module_to_file)

    for module_name, file_path in module_to_file.items():
        source_layer = module_to_layer.get(module_name)
        imports = _extract_imports(file_path, module_name)
        for import_name in imports:
            target_module = _resolve_local_module(import_name, known_modules)
            if target_module:
                graph[module_name].add(target_module)
            target_layer = _target_layer(import_name, module_to_layer)
            if not source_layer or not target_layer:
                continue
            for rule in forbidden_imports:
                if (
                    source_layer == rule.get("source_layer")
                    and target_layer == rule.get("target_layer")
                ):
                    target_display = target_module or import_name
                    violations.append(
                        {
                            "code": "forbidden-import-layer",
                            "module": module_name,
                            "path": str(file_path),
                            "import": import_name,
                            "target": target_display,
                            "message": str(rule.get("reason", "Forbidden layer import.")),
                        }
                    )

    if fail_on_cycles:
        for cycle in _tarjan_cycles(graph):
            violations.append(
                {
                    "code": "dependency-cycle",
                    "module": cycle[0],
                    "path": str(module_to_file.get(cycle[0], "")),
                    "import": " -> ".join(cycle),
                    "target": cycle[-1],
                    "message": f"Dependency cycle detected: {' -> '.join(cycle)}",
                }
            )

    return {
        "status": "passed" if not violations else "failed",
        "violations": violations,
        "details": {
            "files_scanned": len(python_files),
            "modules_scanned": len(module_to_file),
        },
    }


def _run_command_adapter(adapter: dict[str, Any], working_dir: Path) -> dict[str, Any]:
    command = adapter.get("command")
    if not isinstance(command, list) or not command:
        return {
            "status": "error",
            "violations": [
                {
                    "code": "invalid-command",
                    "message": "Command adapter requires a non-empty list command.",
                }
            ],
            "details": {},
        }

    required_paths = [str(path) for path in adapter.get("requires_paths", [])]
    missing_paths = [
        path for path in required_paths if not (working_dir / path).exists()
    ]
    if missing_paths:
        return {
            "status": "skipped",
            "violations": [],
            "details": {"missing_paths": missing_paths},
        }

    executable = str(command[0])
    if "/" in executable:
        executable_exists = (working_dir / executable).exists() or Path(executable).exists()
    else:
        executable_exists = shutil.which(executable) is not None
    if not executable_exists:
        return {
            "status": "failed",
            "violations": [
                {
                    "code": "missing-tool",
                    "message": f"Required executable not found: {executable}",
                }
            ],
            "details": {"command": command},
        }

    completed = subprocess.run(
        command,
        cwd=working_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    details = {
        "command": command,
        "return_code": completed.returncode,
        "stdout_tail": "\n".join(stdout.splitlines()[-20:]) if stdout else "",
        "stderr_tail": "\n".join(stderr.splitlines()[-20:]) if stderr else "",
    }
    if completed.returncode == 0:
        return {"status": "passed", "violations": [], "details": details}
    return {
        "status": "failed",
        "violations": [
            {
                "code": "command-failed",
                "message": f"Command exited with code {completed.returncode}.",
            }
        ],
        "details": details,
    }


def _run_adapter(adapter: dict[str, Any], working_dir: Path) -> dict[str, Any]:
    adapter_type = str(adapter.get("type", ""))
    adapter_id = str(adapter.get("id", adapter_type or "adapter"))

    if not working_dir.exists():
        return {
            "adapter_id": adapter_id,
            "type": adapter_type,
            "status": "skipped",
            "violations": [],
            "details": {"reason": f"Working directory not found: {working_dir}"},
        }

    if adapter_type == "python_import_rules":
        result = _run_python_import_rules(adapter, working_dir)
    elif adapter_type == "command":
        result = _run_command_adapter(adapter, working_dir)
    else:
        result = {
            "status": "error",
            "violations": [
                {
                    "code": "unsupported-adapter",
                    "message": f"Unsupported adapter type: {adapter_type}",
                }
            ],
            "details": {},
        }
    return {
        "adapter_id": adapter_id,
        "type": adapter_type,
        **result,
    }


def _project_for_id(projects: list[ProjectConfig], project_id: str) -> ProjectConfig:
    for project in projects:
        if project.id == project_id:
            return project
    raise ValueError(f"Unknown project id: {project_id}")


def run_enforcement(
    project_ids: list[str] | None = None,
    *,
    config_dir: Path = DEFAULT_CONFIG_DIR,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    profiles, projects = load_registry(config_dir=config_dir, repo_root=repo_root)
    selected_projects = projects if project_ids is None else [
        _project_for_id(projects, project_id) for project_id in project_ids
    ]

    project_reports: list[dict[str, Any]] = []
    for project in selected_projects:
        if not project.path.exists():
            project_reports.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "path": str(project.path),
                    "proof_target": project.proof_target,
                    "status": "missing",
                    "profiles": [],
                }
            )
            continue

        profile_reports: list[dict[str, Any]] = []
        for binding in project.profile_bindings:
            profile_id = str(binding.get("profile_id", ""))
            profile = profiles.get(profile_id)
            if profile is None:
                profile_reports.append(
                    {
                        "profile_id": profile_id,
                        "status": "error",
                        "adapters": [],
                        "violations": [
                            {
                                "code": "unknown-profile",
                                "message": f"Profile not found: {profile_id}",
                            }
                        ],
                    }
                )
                continue

            working_directory = str(binding.get("working_directory", "."))
            working_dir = _resolve_path(working_directory, base=project.path)
            adapters = [
                _run_adapter(adapter, working_dir)
                for adapter in profile.get("adapters", [])
            ]
            profile_status = "passed"
            if any(adapter["status"] == "error" for adapter in adapters):
                profile_status = "error"
            elif any(adapter["status"] == "failed" for adapter in adapters):
                profile_status = "failed"
            elif adapters and all(adapter["status"] == "skipped" for adapter in adapters):
                profile_status = "skipped"

            profile_reports.append(
                {
                    "profile_id": profile_id,
                    "stack": profile.get("stack"),
                    "working_directory": str(working_dir),
                    "status": profile_status,
                    "adapters": adapters,
                }
            )

        project_status = "passed"
        if any(profile["status"] == "error" for profile in profile_reports):
            project_status = "error"
        elif any(profile["status"] == "failed" for profile in profile_reports):
            project_status = "failed"
        elif profile_reports and all(profile["status"] == "skipped" for profile in profile_reports):
            project_status = "skipped"

        project_reports.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "path": str(project.path),
                "proof_target": project.proof_target,
                "status": project_status,
                "profiles": profile_reports,
            }
        )

    failed_projects = sum(1 for project in project_reports if project["status"] == "failed")
    error_projects = sum(1 for project in project_reports if project["status"] == "error")
    ok = failed_projects == 0 and error_projects == 0

    return {
        "ok": ok,
        "generated_at": _now(),
        "projects": project_reports,
        "summary": {
            "total_projects": len(project_reports),
            "failed_projects": failed_projects,
            "error_projects": error_projects,
            "missing_projects": sum(1 for project in project_reports if project["status"] == "missing"),
        },
    }
