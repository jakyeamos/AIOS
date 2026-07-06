from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "quality-gates.json"
LOCAL_CONTRACT_NAME = ".aios-quality-gate.json"
TEST_QUALITY_NON_REGRESSION_POLICY = (
    "test_quality fixes must preserve or improve behavior coverage; delete tests only when "
    "they are proven obsolete, redundant with stronger coverage, or pure noise."
)
SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".swift",
}
GateMode = Literal["pre-commit", "full"]


@dataclass(frozen=True)
class QualityGateFinding:
    path: str
    line: int
    rule: str
    message: str


def source_changes(paths: Sequence[str]) -> bool:
    return any(Path(path).suffix.lower() in SOURCE_EXTENSIONS for path in paths)


def validate_commit_quality_gate(
    repo_root: Path,
    changed_paths: Sequence[str],
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    run: bool = True,
) -> list[QualityGateFinding]:
    if not source_changes(changed_paths):
        return []

    registry = _load_registry(registry_path)
    registered = _registered_project_for_root(registry, repo_root)
    contract_path = repo_root / LOCAL_CONTRACT_NAME
    if not contract_path.exists():
        if registered and registered.get("preCommitRequired") is True:
            return [
                QualityGateFinding(
                    LOCAL_CONTRACT_NAME,
                    1,
                    "aios-quality-gate-missing",
                    "registered project must declare .aios-quality-gate.json",
                )
            ]
        return []

    contract, parse_error = _load_contract(contract_path)
    if parse_error is not None:
        return [parse_error]

    findings = validate_contract(contract, registry, registered=registered)
    if findings or not run:
        return findings

    project_id = str(contract["projectId"])
    for gate_id in contract["preCommitGates"]:
        result = run_gate(
            project_id=project_id,
            gate_id=str(gate_id),
            mode="pre-commit",
            repo_root=repo_root,
            registry_path=registry_path,
        )
        if result["status"] != "pass":
            findings.append(
                QualityGateFinding(
                    LOCAL_CONTRACT_NAME,
                    1,
                    "aios-quality-gate-failed",
                    f"{gate_id} failed: {result['summary']}",
                )
            )
            break
    return findings


def validate_contract(
    contract: dict[str, Any],
    registry: dict[str, Any],
    *,
    registered: dict[str, Any] | None,
) -> list[QualityGateFinding]:
    findings: list[QualityGateFinding] = []
    known_gates = _known_gates(registry)
    project_id = contract.get("projectId")
    if not isinstance(project_id, str) or not project_id.strip():
        findings.append(
            QualityGateFinding(
                LOCAL_CONTRACT_NAME,
                1,
                "aios-quality-gate-project",
                "projectId must be a non-empty string",
            )
        )
    elif registered is not None and project_id != registered.get("projectId"):
        findings.append(
            QualityGateFinding(
                LOCAL_CONTRACT_NAME,
                1,
                "aios-quality-gate-project",
                f"projectId must match AIOS registry project {registered.get('projectId')}",
            )
        )

    pre_commit_gates = contract.get("preCommitGates")
    if not isinstance(pre_commit_gates, list) or not pre_commit_gates:
        findings.append(
            QualityGateFinding(
                LOCAL_CONTRACT_NAME,
                1,
                "aios-quality-gate-empty",
                "preCommitGates must list at least one known gate id",
            )
        )
    else:
        findings.extend(_unknown_gate_findings(pre_commit_gates, known_gates, "preCommitGates"))

    full_gates = contract.get("fullGates", [])
    if not isinstance(full_gates, list):
        findings.append(
            QualityGateFinding(
                LOCAL_CONTRACT_NAME,
                1,
                "aios-quality-gate-full",
                "fullGates must be a list when present",
            )
        )
    else:
        findings.extend(_unknown_gate_findings(full_gates, known_gates, "fullGates"))

    if isinstance(project_id, str) and project_id.strip():
        project = _project_by_id(registry, project_id)
        if project is None:
            findings.append(
                QualityGateFinding(
                    LOCAL_CONTRACT_NAME,
                    1,
                    "aios-quality-gate-unregistered",
                    f"{project_id} is not registered in AIOS quality-gates.json",
                )
            )
        else:
            configured_gates = (
                project.get("gates") if isinstance(project.get("gates"), dict) else {}
            )
            declared_gates = (
                [*pre_commit_gates, *full_gates]
                if isinstance(pre_commit_gates, list) and isinstance(full_gates, list)
                else []
            )
            for gate_id in declared_gates:
                if gate_id not in known_gates:
                    continue
                if gate_id not in configured_gates:
                    findings.append(
                        QualityGateFinding(
                            LOCAL_CONTRACT_NAME,
                            1,
                            "aios-quality-gate-unconfigured",
                            f"{project_id} does not configure gate {gate_id}",
                        )
                    )
    return findings


def run_gate(
    *,
    project_id: str,
    gate_id: str,
    mode: GateMode,
    repo_root: Path,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    registry = _load_registry(registry_path)
    project = _project_by_id(registry, project_id)
    if project is None:
        return {
            "status": "fail",
            "projectId": project_id,
            "gateId": gate_id,
            "mode": mode,
            "summary": f"project {project_id} is not registered",
            "commands": [],
        }
    gates_raw = project.get("gates")
    gates = gates_raw if isinstance(gates_raw, dict) else {}
    gate_raw = gates.get(gate_id)
    gate = gate_raw if isinstance(gate_raw, dict) else None
    if gate is None:
        return {
            "status": "fail",
            "projectId": project_id,
            "gateId": gate_id,
            "mode": mode,
            "summary": f"gate {gate_id} is not configured for {project_id}",
            "commands": [],
        }
    command_key = "preCommitCommands" if mode == "pre-commit" else "fullCommands"
    commands = gate.get(command_key)
    if not isinstance(commands, list) or not commands:
        return {
            "status": "skip",
            "projectId": project_id,
            "gateId": gate_id,
            "mode": mode,
            "summary": f"{gate_id} has no {mode} commands",
            "commands": [],
        }

    results: list[dict[str, Any]] = []
    for command in commands:
        argv = _command_argv(command, repo_root)
        if argv is None:
            result = {
                "argv": command,
                "status": "fail",
                "exitCode": 2,
                "summary": "command must be a non-empty argv list",
            }
            results.append(result)
            return _gate_payload(project_id, gate_id, mode, "fail", result["summary"], results)
        completed = subprocess.run(
            argv,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        status = "pass" if completed.returncode == 0 else "fail"
        summary = _command_summary(argv, completed.stdout, completed.stderr, completed.returncode)
        result = {
            "argv": argv,
            "status": status,
            "exitCode": completed.returncode,
            "summary": summary,
        }
        results.append(result)
        if completed.returncode != 0:
            return _gate_payload(
                project_id,
                gate_id,
                mode,
                "fail",
                _summary_with_policy(gate_id, summary),
                results,
            )
    return _gate_payload(
        project_id,
        gate_id,
        mode,
        "pass",
        _summary_with_policy(gate_id, f"{gate_id} passed"),
        results,
    )


def _load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _load_contract(path: Path) -> tuple[dict[str, Any], QualityGateFinding | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {}, QualityGateFinding(
            LOCAL_CONTRACT_NAME,
            error.lineno,
            "aios-quality-gate-invalid",
            f"invalid JSON: {error.msg}",
        )
    if not isinstance(payload, dict):
        return {}, QualityGateFinding(
            LOCAL_CONTRACT_NAME,
            1,
            "aios-quality-gate-invalid",
            "quality gate contract must be a JSON object",
        )
    return payload, None


def _known_gates(registry: dict[str, Any]) -> set[str]:
    gates = registry.get("knownGates")
    if not isinstance(gates, list):
        return set()
    return {str(gate) for gate in gates if isinstance(gate, str) and gate.strip()}


def _registered_project_for_root(
    registry: dict[str, Any], repo_root: Path
) -> dict[str, Any] | None:
    resolved_root = repo_root.expanduser().resolve()
    for project in _projects(registry):
        roots = project.get("roots")
        if not isinstance(roots, list):
            continue
        for root in roots:
            if not isinstance(root, str) or not root.strip():
                continue
            if Path(root).expanduser().resolve() == resolved_root:
                return project
    return None


def _project_by_id(registry: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in _projects(registry):
        if project.get("projectId") == project_id:
            return project
    return None


def _projects(registry: dict[str, Any]) -> list[dict[str, Any]]:
    projects = registry.get("projects")
    if not isinstance(projects, list):
        return []
    return [project for project in projects if isinstance(project, dict)]


def _unknown_gate_findings(
    gates: Sequence[Any],
    known_gates: set[str],
    field: str,
) -> list[QualityGateFinding]:
    findings: list[QualityGateFinding] = []
    for gate in gates:
        if not isinstance(gate, str) or gate not in known_gates:
            findings.append(
                QualityGateFinding(
                    LOCAL_CONTRACT_NAME,
                    1,
                    "aios-quality-gate-unknown",
                    f"{field} contains unknown gate id {gate!r}",
                )
            )
    return findings


def _command_argv(command: Any, repo_root: Path) -> list[str] | None:
    if not isinstance(command, list) or not command:
        return None
    argv: list[str] = []
    for part in command:
        if not isinstance(part, str) or not part:
            return None
        argv.append(part.replace("{repo_root}", str(repo_root)))
    return argv


def _command_summary(argv: Sequence[str], stdout: str, stderr: str, exit_code: int) -> str:
    if exit_code == 0:
        return f"{' '.join(argv)} passed"
    text = (stderr or stdout or "command failed").strip()
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        first_line = "command failed"
    return f"{' '.join(argv)} failed: {first_line[:180]}"


def _gate_payload(
    project_id: str,
    gate_id: str,
    mode: GateMode,
    status: str,
    summary: str,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "status": status,
        "projectId": project_id,
        "gateId": gate_id,
        "mode": mode,
        "summary": summary,
        "commands": commands,
    }
    if gate_id == "test_quality":
        payload["nonRegressionPolicy"] = TEST_QUALITY_NON_REGRESSION_POLICY
    return payload


def _summary_with_policy(gate_id: str, summary: str) -> str:
    if gate_id != "test_quality" or TEST_QUALITY_NON_REGRESSION_POLICY in summary:
        return summary
    return f"{summary}. {TEST_QUALITY_NON_REGRESSION_POLICY}"
