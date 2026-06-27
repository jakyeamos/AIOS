# Quality Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `quality-runner` as a standalone Python audit-and-plan package with CLI and MCP surfaces.

**Architecture:** Quality Runner uses one core package that discovers repo facts, compiles standards, detects capabilities, normalizes audit findings, writes `.quality-runner/` artifacts, and produces remediation plans. The CLI and MCP layers are thin wrappers over the same core functions. Version 1 is read-only except for writing `.quality-runner/runs/<run-id>/` artifacts.

**Tech Stack:** Python 3.12, stdlib-only core, argparse CLI, stdio JSON-RPC MCP server, pytest, Ruff, BasedPyright, Vulture.

---

## File Structure

Create a new standalone repository at `/Users/jakyeamos/quality-runner`.

```text
/Users/jakyeamos/quality-runner/
  pyproject.toml
  README.md
  quality_runner/
    __init__.py
    __main__.py
    artifacts.py
    audit.py
    capabilities.py
    cli.py
    discovery.py
    findings.py
    mcp.py
    planning.py
    standards.py
    workflow.py
    plugin/
      SKILL.md
      manifest.json
  tests/
    test_quality_runner.py
```

Responsibilities:

- `discovery.py`: repo fact scanning without running repo commands.
- `standards.py`: `jakyeamos` profile and local instruction ingestion.
- `capabilities.py`: available/missing quality-surface detection.
- `findings.py`: shared finding/evidence contracts and validation.
- `audit.py`: evidence-backed audit report synthesis.
- `planning.py`: ordered remediation slices and agent handoff.
- `artifacts.py`: artifact-path creation and JSON/Markdown writing.
- `workflow.py`: orchestration functions used by CLI and MCP.
- `cli.py`: human-facing command surface.
- `mcp.py`: stdio JSON-RPC MCP tool surface.
- `plugin/`: installable metadata for agent hosts.

## Task 1: Scaffold Standalone Package

**Files:**
- Create: `/Users/jakyeamos/quality-runner/pyproject.toml`
- Create: `/Users/jakyeamos/quality-runner/README.md`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/__init__.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/__main__.py`
- Create: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Create repository directory**

Run:

```bash
mkdir -p /Users/jakyeamos/quality-runner/quality_runner /Users/jakyeamos/quality-runner/tests
```

Expected: directories exist.

- [ ] **Step 2: Initialize git**

Run:

```bash
git -C /Users/jakyeamos/quality-runner init
```

Expected: repository initialized.

- [ ] **Step 3: Add package metadata**

Create `/Users/jakyeamos/quality-runner/pyproject.toml`:

```toml
[project]
name = "quality-runner"
version = "0.1.0"
description = "Standalone audit-and-plan quality orchestrator with CLI and MCP surfaces."
requires-python = ">=3.12"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project.scripts]
quality-runner = "quality_runner.cli:main"
quality-runner-mcp = "quality_runner.mcp:main"

[tool.setuptools.package-data]
quality_runner = ["plugin/*.json", "plugin/*.md"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "SIM"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["B", "SIM"]

[tool.basedpyright]
pythonVersion = "3.12"
include = ["quality_runner", "tests"]
typeCheckingMode = "standard"
reportMissingImports = "warning"
reportMissingModuleSource = "none"
```

- [ ] **Step 4: Add initial package files**

Create `/Users/jakyeamos/quality-runner/quality_runner/__init__.py`:

```python
from __future__ import annotations

__version__ = "0.1.0"
```

Create `/Users/jakyeamos/quality-runner/quality_runner/__main__.py`:

```python
from __future__ import annotations

from quality_runner.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Add README**

Create `/Users/jakyeamos/quality-runner/README.md`:

```markdown
# Quality Runner

Quality Runner is a standalone audit-and-plan quality orchestrator.

Version 1 inspects a target repository, compiles applicable standards, detects available quality capabilities, writes audit artifacts, and produces an ordered remediation plan. It does not edit target source files or create commits.

## Commands

```bash
quality-runner doctor
quality-runner inspect /path/to/repo --json
quality-runner audit /path/to/repo --standards jakyeamos --json
quality-runner plan /path/to/repo --standards jakyeamos --json
quality-runner run /path/to/repo --standards jakyeamos --json
quality-runner status /path/to/repo --json
quality-runner export-handoff /path/to/repo --run-id <run-id>
```
```

- [ ] **Step 6: Add bootstrap import test**

Create `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_imports_without_aios() -> None:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        "import quality_runner; "
        "print(quality_runner.__version__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "0.1.0"
```

- [ ] **Step 7: Run bootstrap test**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: `1 passed`.

- [ ] **Step 8: Commit scaffold**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add pyproject.toml README.md quality_runner tests
git -C /Users/jakyeamos/quality-runner commit -m "Scaffold Quality Runner package"
```

## Task 2: Add Core Contracts and Artifact Writer

**Files:**
- Create: `/Users/jakyeamos/quality-runner/quality_runner/findings.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/artifacts.py`
- Modify: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Add failing artifact and validation tests**

Append to `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python
import json

from quality_runner.artifacts import artifact_dir, write_json
from quality_runner.findings import validate_audit_report, validate_remediation_plan


def test_artifact_dir_uses_quality_runner_namespace(tmp_path: Path) -> None:
    path = artifact_dir(tmp_path, "run-001")

    assert path == tmp_path / ".quality-runner" / "runs" / "run-001"


def test_write_json_creates_parent_and_stable_json(tmp_path: Path) -> None:
    path = write_json(tmp_path / "nested" / "payload.json", {"b": 2, "a": 1})

    assert path.exists()
    assert path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'


def test_validate_audit_report_rejects_findings_without_evidence() -> None:
    report = {
        "schema": "quality-runner-audit-report-v0.1",
        "findings": [
            {
                "id": "missing-evidence",
                "severity": "warning",
                "category": "docs",
                "summary": "No evidence",
                "evidence": [],
                "recommended_fix": "Add evidence",
                "verification": ["review report"],
            }
        ],
    }

    result = validate_audit_report(report)

    assert result["passed"] is False
    assert result["errors"] == ["finding missing-evidence has no evidence"]


def test_validate_remediation_plan_rejects_slices_without_verification() -> None:
    plan = {
        "schema": "quality-runner-remediation-plan-v0.1",
        "slices": [
            {
                "id": "slice-001",
                "title": "No verification",
                "findings": ["finding-001"],
                "verification": [],
            }
        ],
    }

    result = validate_remediation_plan(plan)

    assert result["passed"] is False
    assert result["errors"] == ["slice slice-001 has no verification"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: import failures for `quality_runner.artifacts` and `quality_runner.findings`.

- [ ] **Step 3: Implement finding validation**

Create `/Users/jakyeamos/quality-runner/quality_runner/findings.py`:

```python
from __future__ import annotations

from typing import Any

ValidationResult = dict[str, Any]


def validate_audit_report(report: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    for finding in _dict_items(report.get("findings")):
        finding_id = str(finding.get("id", "unknown"))
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"finding {finding_id} has no evidence")
    return {"passed": not errors, "errors": errors}


def validate_remediation_plan(plan: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    for slice_item in _dict_items(plan.get("slices")):
        slice_id = str(slice_item.get("id", "unknown"))
        verification = slice_item.get("verification")
        if not isinstance(verification, list) or not verification:
            errors.append(f"slice {slice_id} has no verification")
    return {"passed": not errors, "errors": errors}


def _dict_items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
```

- [ ] **Step 4: Implement artifact helpers**

Create `/Users/jakyeamos/quality-runner/quality_runner/artifacts.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def artifact_dir(repo_root: Path, run_id: str) -> Path:
    return repo_root.expanduser().resolve() / ".quality-runner" / "runs" / run_id


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit contracts**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add quality_runner tests
git -C /Users/jakyeamos/quality-runner commit -m "Add Quality Runner core contracts"
```

## Task 3: Implement Repo Discovery, Standards, and Capabilities

**Files:**
- Create: `/Users/jakyeamos/quality-runner/quality_runner/discovery.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/standards.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/capabilities.py`
- Modify: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Add failing discovery and standards tests**

Append to `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python
from quality_runner.capabilities import detect_capabilities
from quality_runner.discovery import inspect_repo
from quality_runner.standards import compile_standards


def _write_js_fixture(repo: Path) -> None:
    (repo / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                    "build": "vite build",
                    "dead-code": "knip",
                    "pre-cr": "pre-cr",
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text(
        "Always use pnpm. Full lint, typecheck, tests, and dead-code scans are required.\n",
        encoding="utf-8",
    )
    (repo / ".pre-cr.json").write_text("{}", encoding="utf-8")
    (repo / ".tracker").mkdir()
    (repo / ".tracker" / "PROJECT_TRUTH.md").write_text("---\nprojectName: Fixture\n---\n", encoding="utf-8")


def test_inspect_repo_detects_js_quality_surfaces(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)

    scan = inspect_repo(tmp_path, run_id="scan-001")

    assert scan["schema"] == "quality-runner-repo-scan-v0.1"
    assert scan["package_manager"] == "pnpm"
    assert scan["languages"] == ["javascript"]
    assert scan["scripts"]["lint"] == "eslint ."
    assert scan["pre_cr_config"] == ".pre-cr.json"
    assert scan["truth_file"] == ".tracker/PROJECT_TRUTH.md"


def test_compile_standards_preserves_profile_and_local_provenance(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)
    scan = inspect_repo(tmp_path, run_id="scan-001")

    packet = compile_standards(repo_root=tmp_path, scan=scan, profile="jakyeamos")

    assert packet["schema"] == "quality-runner-standards-packet-v0.1"
    assert packet["profile"] == "jakyeamos"
    sources = {source["path"] for source in packet["sources"]}
    assert "AGENTS.md" in sources
    requirement_ids = {requirement["id"] for requirement in packet["requirements"]}
    assert "use_pnpm" in requirement_ids
    assert "truth_file_current" in requirement_ids


def test_detect_capabilities_records_missing_expected_surfaces(tmp_path: Path) -> None:
    scan = inspect_repo(tmp_path, run_id="empty-001")
    packet = compile_standards(repo_root=tmp_path, scan=scan, profile="jakyeamos")

    capability_map = detect_capabilities(scan=scan, standards_packet=packet)

    assert capability_map["schema"] == "quality-runner-capability-map-v0.1"
    missing_ids = {item["id"] for item in capability_map["missing"]}
    assert "lint" in missing_ids
    assert "tests" in missing_ids
    assert "truth_file" in missing_ids
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: import failures for discovery, standards, and capabilities.

- [ ] **Step 3: Implement repo discovery**

Create `/Users/jakyeamos/quality-runner/quality_runner/discovery.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_SCAN_SCHEMA = "quality-runner-repo-scan-v0.1"


def inspect_repo(repo_root: Path, *, run_id: str) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    package_json = _read_package_json(root / "package.json")
    scripts = _scripts(package_json)
    languages = _languages(root, package_json)
    return {
        "schema": REPO_SCAN_SCHEMA,
        "run_id": run_id,
        "repo_root": str(root),
        "is_git_repo": (root / ".git").exists(),
        "package_manager": _package_manager(root, package_json),
        "languages": languages,
        "scripts": scripts,
        "agent_instruction_files": _existing(root, ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]),
        "pre_cr_config": _first_existing(root, [".pre-cr.json"]),
        "truth_file": _first_existing(root, [".tracker/PROJECT_TRUTH.md", "PROJECT_TRUTH.md"]),
        "quality_contract": _first_existing(root, [".aios-quality-gate.json"]),
        "ci_files": _existing(root, [".github/workflows/ci.yml", ".github/workflows/test.yml"]),
    }


def _read_package_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _scripts(package_json: dict[str, Any]) -> dict[str, str]:
    raw = package_json.get("scripts")
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _languages(root: Path, package_json: dict[str, Any]) -> list[str]:
    languages: list[str] = []
    if package_json or (root / "tsconfig.json").exists():
        languages.append("javascript")
    if (root / "pyproject.toml").exists() or any(root.glob("*.py")):
        languages.append("python")
    if any(root.glob("*.sh")):
        languages.append("shell")
    return languages


def _package_manager(root: Path, package_json: dict[str, Any]) -> str:
    if (root / "pnpm-lock.yaml").exists() or package_json:
        return "pnpm"
    if (root / "uv.lock").exists() or (root / "pyproject.toml").exists():
        return "uv"
    return "unknown"


def _existing(root: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if (root / path).exists()]


def _first_existing(root: Path, paths: list[str]) -> str | None:
    for path in paths:
        if (root / path).exists():
            return path
    return None
```

- [ ] **Step 4: Implement standards compiler**

Create `/Users/jakyeamos/quality-runner/quality_runner/standards.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

STANDARDS_PACKET_SCHEMA = "quality-runner-standards-packet-v0.1"

JAKYEAMOS_REQUIREMENTS = [
    {
        "id": "use_pnpm",
        "level": "hard",
        "summary": "JavaScript projects use pnpm, never npm or yarn.",
        "verification": ["inspect package manager and scripts"],
    },
    {
        "id": "quality_ladder",
        "level": "hard",
        "summary": "Formatter, lint, typecheck, tests, dead-code, and structure checks must be explicit.",
        "verification": ["inspect capability map"],
    },
    {
        "id": "truth_file_current",
        "level": "hard",
        "summary": "Managed repos keep a live project truth file current after material changes.",
        "verification": ["inspect truth-file presence and freshness"],
    },
    {
        "id": "audit_and_plan_only",
        "level": "hard",
        "summary": "Quality Runner v1 writes artifacts only and does not modify target source files.",
        "verification": ["compare target repo writes against .quality-runner/"],
    },
]


def compile_standards(
    *,
    repo_root: Path,
    scan: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    if profile != "jakyeamos":
        raise ValueError(f"Unsupported standards profile: {profile}")
    root = repo_root.expanduser().resolve()
    sources = [{"kind": "profile", "path": "quality-runner:profiles/jakyeamos"}]
    for relative in scan.get("agent_instruction_files", []):
        if isinstance(relative, str):
            sources.append({"kind": "instruction_file", "path": relative})
    if scan.get("truth_file"):
        sources.append({"kind": "truth_file", "path": scan["truth_file"]})
    return {
        "schema": STANDARDS_PACKET_SCHEMA,
        "profile": profile,
        "repo_root": str(root),
        "sources": sources,
        "requirements": JAKYEAMOS_REQUIREMENTS,
    }
```

- [ ] **Step 5: Implement capability detection**

Create `/Users/jakyeamos/quality-runner/quality_runner/capabilities.py`:

```python
from __future__ import annotations

from typing import Any

CAPABILITY_MAP_SCHEMA = "quality-runner-capability-map-v0.1"

SCRIPT_CAPABILITIES = {
    "formatter": ("format", "fmt"),
    "lint": ("lint",),
    "typecheck": ("typecheck", "type-check"),
    "tests": ("test", "tests"),
    "build": ("build",),
    "dead_code": ("dead-code", "dead_code", "knip"),
    "runtime_smoke": ("smoke", "runtime:smoke", "test:runtime-smoke"),
    "pre_pr": ("pre-pr", "pre-pr-readiness"),
}


def detect_capabilities(
    *,
    scan: dict[str, Any],
    standards_packet: dict[str, Any],
) -> dict[str, Any]:
    scripts = scan.get("scripts")
    scripts = scripts if isinstance(scripts, dict) else {}
    available: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for capability_id, aliases in SCRIPT_CAPABILITIES.items():
        command = _script_command(scripts, aliases)
        if command:
            available.append(
                {
                    "id": capability_id,
                    "kind": "script",
                    "read_only": True,
                    "evidence": [f"package.json:scripts.{command[0]}"],
                    "command": command[1],
                }
            )
        else:
            missing.append(
                {
                    "id": capability_id,
                    "kind": "script",
                    "reason": "No matching package script detected.",
                }
            )
    if scan.get("pre_cr_config"):
        available.append(
            {
                "id": "pre_cr",
                "kind": "config",
                "read_only": True,
                "evidence": [str(scan["pre_cr_config"])],
            }
        )
    else:
        missing.append({"id": "pre_cr", "kind": "config", "reason": "No .pre-cr.json detected."})
    if scan.get("truth_file"):
        available.append(
            {
                "id": "truth_file",
                "kind": "policy",
                "read_only": True,
                "evidence": [str(scan["truth_file"])],
            }
        )
    else:
        missing.append(
            {"id": "truth_file", "kind": "policy", "reason": "No project truth file detected."}
        )
    return {
        "schema": CAPABILITY_MAP_SCHEMA,
        "profile": standards_packet.get("profile", "unknown"),
        "available": available,
        "missing": missing,
    }


def _script_command(scripts: dict[object, object], aliases: tuple[str, ...]) -> tuple[str, str] | None:
    for alias in aliases:
        value = scripts.get(alias)
        if isinstance(value, str) and value:
            return alias, value
    return None
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit discovery layer**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add quality_runner tests
git -C /Users/jakyeamos/quality-runner commit -m "Add repo discovery and standards detection"
```

## Task 4: Implement Audit, Planning, and Workflow Orchestration

**Files:**
- Create: `/Users/jakyeamos/quality-runner/quality_runner/audit.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/planning.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/workflow.py`
- Modify: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Add failing workflow tests**

Append to `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python
from quality_runner.workflow import inspect_payload, run_payload


def test_run_payload_writes_audit_plan_and_handoff(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)

    payload = run_payload(repo_root=tmp_path, run_id="run-001", profile="jakyeamos")

    assert payload["schema"] == "quality-runner-run-result-v0.1"
    assert payload["status"] == "planned"
    assert payload["implementation_allowed"] is False
    artifact_paths = payload["artifact_paths"]
    assert Path(artifact_paths["repo_scan_json"]).exists()
    assert Path(artifact_paths["standards_packet_json"]).exists()
    assert Path(artifact_paths["capability_map_json"]).exists()
    assert Path(artifact_paths["audit_report_json"]).exists()
    assert Path(artifact_paths["remediation_plan_json"]).exists()
    assert Path(artifact_paths["agent_handoff_md"]).exists()


def test_run_payload_records_missing_capability_findings(tmp_path: Path) -> None:
    payload = run_payload(repo_root=tmp_path, run_id="empty-run", profile="jakyeamos")
    audit_report = json.loads(Path(payload["artifact_paths"]["audit_report_json"]).read_text())

    finding_ids = {finding["id"] for finding in audit_report["findings"]}
    assert "missing-lint" in finding_ids
    assert "missing-tests" in finding_ids
    assert "missing-truth-file" in finding_ids


def test_inspect_payload_does_not_write_audit_plan(tmp_path: Path) -> None:
    payload = inspect_payload(repo_root=tmp_path, run_id="inspect-001", profile="jakyeamos")

    assert payload["schema"] == "quality-runner-inspect-result-v0.1"
    assert Path(payload["artifact_paths"]["repo_scan_json"]).exists()
    assert "audit_report_json" not in payload["artifact_paths"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: import failure for `quality_runner.workflow`.

- [ ] **Step 3: Implement audit report builder**

Create `/Users/jakyeamos/quality-runner/quality_runner/audit.py`:

```python
from __future__ import annotations

from typing import Any

AUDIT_REPORT_SCHEMA = "quality-runner-audit-report-v0.1"

SEVERITY_BY_CAPABILITY = {
    "lint": "blocker",
    "tests": "blocker",
    "typecheck": "blocker",
    "truth_file": "blocker",
}


def build_audit_report(
    *,
    run_id: str,
    scan: dict[str, Any],
    standards_packet: dict[str, Any],
    capability_map: dict[str, Any],
) -> dict[str, Any]:
    findings = [_missing_capability_finding(item) for item in capability_map.get("missing", [])]
    return {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": run_id,
        "repo_root": scan["repo_root"],
        "standards_profile": standards_packet["profile"],
        "summary": {
            "finding_count": len(findings),
            "blocker_count": sum(1 for finding in findings if finding["severity"] == "blocker"),
        },
        "findings": findings,
    }


def render_audit_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Quality Runner Audit Report",
        "",
        f"Run ID: `{report['run_id']}`",
        f"Repo: `{report['repo_root']}`",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        lines.extend(
            [
                f"### {finding['id']}",
                "",
                f"- Severity: `{finding['severity']}`",
                f"- Category: `{finding['category']}`",
                f"- Summary: {finding['summary']}",
                f"- Recommended fix: {finding['recommended_fix']}",
                f"- Verification: `{finding['verification'][0]}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _missing_capability_finding(item: object) -> dict[str, Any]:
    missing = item if isinstance(item, dict) else {}
    capability_id = str(missing.get("id", "unknown"))
    return {
        "id": f"missing-{capability_id.replace('_', '-')}",
        "source": "capability_detection",
        "severity": SEVERITY_BY_CAPABILITY.get(capability_id, "warning"),
        "category": _category(capability_id),
        "summary": f"Expected quality capability `{capability_id}` was not detected.",
        "evidence": [
            {
                "kind": "absence",
                "reference": str(missing.get("kind", "capability")),
                "detail": str(missing.get("reason", "Capability was not detected.")),
            }
        ],
        "recommended_fix": f"Add or document the `{capability_id}` quality surface.",
        "verification": ["quality-runner inspect <repo> --json"],
    }


def _category(capability_id: str) -> str:
    if capability_id in {"truth_file"}:
        return "truth"
    if capability_id in {"pre_cr", "pre_pr"}:
        return "workflow"
    if capability_id in {"dead_code", "structural_scan"}:
        return "structure"
    return capability_id
```

- [ ] **Step 4: Implement remediation planner**

Create `/Users/jakyeamos/quality-runner/quality_runner/planning.py`:

```python
from __future__ import annotations

from typing import Any

REMEDIATION_PLAN_SCHEMA = "quality-runner-remediation-plan-v0.1"
AGENT_HANDOFF_SCHEMA = "quality-runner-agent-handoff-v0.1"

PRIORITY = {
    "blocker": 0,
    "warning": 1,
    "observation": 2,
}


def build_remediation_plan(*, run_id: str, audit_report: dict[str, Any]) -> dict[str, Any]:
    findings = sorted(
        audit_report["findings"],
        key=lambda finding: (PRIORITY.get(str(finding["severity"]), 9), str(finding["id"])),
    )
    slices = [_slice_for_finding(index, finding) for index, finding in enumerate(findings, start=1)]
    return {
        "schema": REMEDIATION_PLAN_SCHEMA,
        "run_id": run_id,
        "repo_root": audit_report["repo_root"],
        "implementation_allowed": False,
        "slices": slices,
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Quality Runner Remediation Plan",
        "",
        f"Run ID: `{plan['run_id']}`",
        f"Repo: `{plan['repo_root']}`",
        "",
        "Implementation is not allowed by Quality Runner v1. A coding agent must receive user approval before applying any slice.",
        "",
        "## Slices",
        "",
    ]
    for item in plan["slices"]:
        lines.extend(
            [
                f"### {item['id']}: {item['title']}",
                "",
                f"- Severity: `{item['severity']}`",
                f"- Findings: {', '.join(f'`{finding}`' for finding in item['findings'])}",
                f"- Rationale: {item['rationale']}",
                f"- Verification: `{item['verification'][0]}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def build_agent_handoff(*, run_id: str, audit_report: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    first_slice = plan["slices"][0] if plan["slices"] else None
    return {
        "schema": AGENT_HANDOFF_SCHEMA,
        "run_id": run_id,
        "repo_root": audit_report["repo_root"],
        "implementation_allowed": False,
        "first_recommended_slice": first_slice,
        "summary": "Quality Runner v1 completed audit-and-plan only.",
    }


def render_handoff_markdown(handoff: dict[str, Any]) -> str:
    lines = [
        "# Quality Runner Agent Handoff",
        "",
        f"Run ID: `{handoff['run_id']}`",
        f"Repo: `{handoff['repo_root']}`",
        "",
        "Quality Runner v1 did not modify source files. Get explicit user approval before implementation.",
        "",
    ]
    first_slice = handoff.get("first_recommended_slice")
    if isinstance(first_slice, dict):
        lines.extend(
            [
                "## First Recommended Slice",
                "",
                f"- ID: `{first_slice['id']}`",
                f"- Title: {first_slice['title']}",
                f"- Verification: `{first_slice['verification'][0]}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _slice_for_finding(index: int, finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"slice-{index:03d}",
        "title": finding["summary"],
        "severity": finding["severity"],
        "findings": [finding["id"]],
        "rationale": finding["recommended_fix"],
        "verification": finding["verification"],
    }
```

- [ ] **Step 5: Implement workflow orchestration**

Create `/Users/jakyeamos/quality-runner/quality_runner/workflow.py`:

```python
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from quality_runner.artifacts import artifact_dir, write_json, write_text
from quality_runner.audit import build_audit_report, render_audit_markdown
from quality_runner.capabilities import detect_capabilities
from quality_runner.discovery import inspect_repo
from quality_runner.findings import validate_audit_report, validate_remediation_plan
from quality_runner.planning import (
    build_agent_handoff,
    build_remediation_plan,
    render_handoff_markdown,
    render_plan_markdown,
)
from quality_runner.standards import compile_standards

INSPECT_RESULT_SCHEMA = "quality-runner-inspect-result-v0.1"
RUN_RESULT_SCHEMA = "quality-runner-run-result-v0.1"


def generated_run_id(prefix: str = "quality-runner") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def inspect_payload(*, repo_root: Path, run_id: str, profile: str) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    out_dir = artifact_dir(root, run_id)
    scan = inspect_repo(root, run_id=run_id)
    standards_packet = compile_standards(repo_root=root, scan=scan, profile=profile)
    capability_map = detect_capabilities(scan=scan, standards_packet=standards_packet)
    paths = {
        "repo_scan_json": write_json(out_dir / "repo-scan.json", scan),
        "standards_packet_json": write_json(out_dir / "standards-packet.json", standards_packet),
        "capability_map_json": write_json(out_dir / "capability-map.json", capability_map),
    }
    return {
        "schema": INSPECT_RESULT_SCHEMA,
        "run_id": run_id,
        "status": "inspected",
        "repo_root": str(root),
        "implementation_allowed": False,
        "artifact_paths": {key: str(value) for key, value in paths.items()},
    }


def run_payload(*, repo_root: Path, run_id: str, profile: str) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    out_dir = artifact_dir(root, run_id)
    scan = inspect_repo(root, run_id=run_id)
    standards_packet = compile_standards(repo_root=root, scan=scan, profile=profile)
    capability_map = detect_capabilities(scan=scan, standards_packet=standards_packet)
    audit_report = build_audit_report(
        run_id=run_id,
        scan=scan,
        standards_packet=standards_packet,
        capability_map=capability_map,
    )
    audit_validation = validate_audit_report(audit_report)
    if not audit_validation["passed"]:
        raise ValueError("; ".join(str(error) for error in audit_validation["errors"]))
    remediation_plan = build_remediation_plan(run_id=run_id, audit_report=audit_report)
    plan_validation = validate_remediation_plan(remediation_plan)
    if not plan_validation["passed"]:
        raise ValueError("; ".join(str(error) for error in plan_validation["errors"]))
    handoff = build_agent_handoff(
        run_id=run_id,
        audit_report=audit_report,
        plan=remediation_plan,
    )
    paths = {
        "repo_scan_json": write_json(out_dir / "repo-scan.json", scan),
        "standards_packet_json": write_json(out_dir / "standards-packet.json", standards_packet),
        "capability_map_json": write_json(out_dir / "capability-map.json", capability_map),
        "audit_report_json": write_json(out_dir / "audit-report.json", audit_report),
        "audit_report_md": write_text(out_dir / "audit-report.md", render_audit_markdown(audit_report)),
        "remediation_plan_json": write_json(out_dir / "remediation-plan.json", remediation_plan),
        "remediation_plan_md": write_text(out_dir / "remediation-plan.md", render_plan_markdown(remediation_plan)),
        "agent_handoff_json": write_json(out_dir / "agent-handoff.json", handoff),
        "agent_handoff_md": write_text(out_dir / "agent-handoff.md", render_handoff_markdown(handoff)),
    }
    return {
        "schema": RUN_RESULT_SCHEMA,
        "run_id": run_id,
        "status": "planned",
        "repo_root": str(root),
        "implementation_allowed": False,
        "artifact_paths": {key: str(value) for key, value in paths.items()},
        "finding_count": audit_report["summary"]["finding_count"],
        "slice_count": len(remediation_plan["slices"]),
    }
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit workflow**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add quality_runner tests
git -C /Users/jakyeamos/quality-runner commit -m "Add audit and remediation planning workflow"
```

## Task 5: Add CLI Surface

**Files:**
- Create: `/Users/jakyeamos/quality-runner/quality_runner/cli.py`
- Modify: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python

def test_cli_run_writes_artifacts(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quality_runner",
            "run",
            str(tmp_path),
            "--run-id",
            "cli-run",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema"] == "quality-runner-run-result-v0.1"
    assert payload["implementation_allowed"] is False
    assert Path(payload["artifact_paths"]["agent_handoff_md"]).exists()


def test_cli_doctor_reports_ready() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "quality_runner", "doctor", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema"] == "quality-runner-doctor-result-v0.1"
    assert payload["status"] == "ready"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: import failure for `quality_runner.cli`.

- [ ] **Step 3: Implement CLI**

Create `/Users/jakyeamos/quality-runner/quality_runner/cli.py`:

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from quality_runner import __version__
from quality_runner.workflow import generated_run_id, inspect_payload, run_payload

DOCTOR_RESULT_SCHEMA = "quality-runner-doctor-result-v0.1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quality-runner",
        description="Audit a repo and produce an evidence-backed remediation plan.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Check Quality Runner readiness")
    doctor.add_argument("--json", action="store_true", help="Emit JSON")
    for command in ("inspect", "audit", "plan", "run"):
        subparser = subparsers.add_parser(command, help=f"{command} a target repository")
        _add_repo_args(subparser)
    status = subparsers.add_parser("status", help="List Quality Runner runs for a repository")
    _add_repo_args(status, include_standards=False)
    handoff = subparsers.add_parser("export-handoff", help="Print an existing handoff")
    _add_repo_args(handoff, include_standards=False)
    handoff.add_argument("--run-id", required=True)
    return parser


def _add_repo_args(parser: argparse.ArgumentParser, *, include_standards: bool = True) -> None:
    parser.add_argument("repo_root", help="Target repository")
    if include_standards:
        parser.add_argument("--standards", default="jakyeamos", help="Standards profile")
    parser.add_argument("--run-id", default=None, help="Stable run id")
    parser.add_argument("--json", action="store_true", help="Emit JSON")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "doctor":
        return {
            "schema": DOCTOR_RESULT_SCHEMA,
            "status": "ready",
            "version": __version__,
            "implementation_allowed": False,
        }
    if args.command in {"inspect"}:
        return inspect_payload(
            repo_root=Path(args.repo_root),
            run_id=args.run_id or generated_run_id("quality-runner-inspect"),
            profile=args.standards,
        )
    if args.command in {"audit", "plan", "run"}:
        return run_payload(
            repo_root=Path(args.repo_root),
            run_id=args.run_id or generated_run_id("quality-runner"),
            profile=args.standards,
        )
    if args.command == "status":
        root = Path(args.repo_root).expanduser().resolve()
        runs_dir = root / ".quality-runner" / "runs"
        runs = sorted(path.name for path in runs_dir.iterdir() if path.is_dir()) if runs_dir.exists() else []
        return {
            "schema": "quality-runner-status-result-v0.1",
            "repo_root": str(root),
            "runs": runs,
            "implementation_allowed": False,
        }
    if args.command == "export-handoff":
        root = Path(args.repo_root).expanduser().resolve()
        handoff = root / ".quality-runner" / "runs" / args.run_id / "agent-handoff.md"
        return {
            "schema": "quality-runner-export-handoff-result-v0.1",
            "repo_root": str(root),
            "run_id": args.run_id,
            "handoff_path": str(handoff),
            "handoff": handoff.read_text(encoding="utf-8"),
            "implementation_allowed": False,
        }
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = _run(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Smoke CLI on package repo**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m quality_runner run /Users/jakyeamos/quality-runner --run-id self-smoke --json
```

Expected: JSON output with `schema=quality-runner-run-result-v0.1` and `.quality-runner/runs/self-smoke/agent-handoff.md` exists.

- [ ] **Step 6: Commit CLI**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add quality_runner tests .quality-runner/runs/self-smoke
git -C /Users/jakyeamos/quality-runner commit -m "Add Quality Runner CLI"
```

## Task 6: Add MCP Surface and Plugin Metadata

**Files:**
- Create: `/Users/jakyeamos/quality-runner/quality_runner/mcp.py`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/plugin/manifest.json`
- Create: `/Users/jakyeamos/quality-runner/quality_runner/plugin/SKILL.md`
- Modify: `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`

- [ ] **Step 1: Add failing MCP tests**

Append to `/Users/jakyeamos/quality-runner/tests/test_quality_runner.py`:

```python
from quality_runner.mcp import call_tool, handle_jsonrpc_message, list_tools


def test_mcp_lists_quality_runner_tools() -> None:
    tool_names = {tool["name"] for tool in list_tools()}

    assert tool_names == {
        "quality_runner_doctor",
        "quality_runner_inspect_repo",
        "quality_runner_run",
        "quality_runner_status",
        "quality_runner_export_handoff",
    }


def test_mcp_run_returns_structured_content(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)

    result = call_tool(
        "quality_runner_run",
        {"repo_root": str(tmp_path), "run_id": "mcp-run", "standards": "jakyeamos"},
    )

    assert result["isError"] is False
    structured = result["structuredContent"]
    assert structured["schema"] == "quality-runner-run-result-v0.1"
    assert structured["implementation_allowed"] is False
    assert Path(structured["artifact_paths"]["agent_handoff_md"]).exists()


def test_mcp_jsonrpc_tools_call(tmp_path: Path) -> None:
    _write_js_fixture(tmp_path)

    response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "quality_runner_inspect_repo",
                "arguments": {
                    "repo_root": str(tmp_path),
                    "run_id": "mcp-inspect",
                    "standards": "jakyeamos",
                },
            },
        }
    )

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["structuredContent"]["schema"] == "quality-runner-inspect-result-v0.1"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: import failure for `quality_runner.mcp`.

- [ ] **Step 3: Implement MCP server**

Create `/Users/jakyeamos/quality-runner/quality_runner/mcp.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from quality_runner import __version__
from quality_runner.cli import DOCTOR_RESULT_SCHEMA
from quality_runner.workflow import generated_run_id, inspect_payload, run_payload

MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_RESULT_SCHEMA = "quality-runner-mcp-result-v0.1"


def list_tools() -> list[dict[str, Any]]:
    repo_schema = {
        "type": "object",
        "properties": {
            "repo_root": {"type": "string"},
            "run_id": {"type": "string"},
            "standards": {"type": "string"},
        },
        "required": ["repo_root"],
    }
    return [
        {
            "name": "quality_runner_doctor",
            "description": "Check Quality Runner install readiness.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "quality_runner_inspect_repo",
            "description": "Inspect repo shape and quality capabilities.",
            "inputSchema": repo_schema,
        },
        {
            "name": "quality_runner_run",
            "description": "Run audit-and-plan workflow and write artifacts.",
            "inputSchema": repo_schema,
        },
        {
            "name": "quality_runner_status",
            "description": "List Quality Runner runs for a repo.",
            "inputSchema": repo_schema,
        },
        {
            "name": "quality_runner_export_handoff",
            "description": "Return an existing agent handoff.",
            "inputSchema": repo_schema,
        },
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    if name == "quality_runner_doctor":
        return _tool_result(
            {
                "schema": DOCTOR_RESULT_SCHEMA,
                "status": "ready",
                "version": __version__,
                "implementation_allowed": False,
            }
        )
    repo_root = _repo_root(args)
    run_id = _string_arg(args, "run_id") or generated_run_id("quality-runner-mcp")
    profile = _string_arg(args, "standards") or "jakyeamos"
    if name == "quality_runner_inspect_repo":
        return _tool_result(inspect_payload(repo_root=repo_root, run_id=run_id, profile=profile))
    if name == "quality_runner_run":
        return _tool_result(run_payload(repo_root=repo_root, run_id=run_id, profile=profile))
    if name == "quality_runner_status":
        runs_dir = repo_root.expanduser().resolve() / ".quality-runner" / "runs"
        runs = sorted(path.name for path in runs_dir.iterdir() if path.is_dir()) if runs_dir.exists() else []
        return _tool_result(
            {
                "schema": "quality-runner-status-result-v0.1",
                "repo_root": str(repo_root.expanduser().resolve()),
                "runs": runs,
                "implementation_allowed": False,
            }
        )
    if name == "quality_runner_export_handoff":
        handoff = repo_root.expanduser().resolve() / ".quality-runner" / "runs" / run_id / "agent-handoff.md"
        return _tool_result(
            {
                "schema": "quality-runner-export-handoff-result-v0.1",
                "repo_root": str(repo_root.expanduser().resolve()),
                "run_id": run_id,
                "handoff_path": str(handoff),
                "handoff": handoff.read_text(encoding="utf-8"),
                "implementation_allowed": False,
            }
        )
    raise ValueError(f"Unknown Quality Runner MCP tool: {name}")


def handle_jsonrpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    try:
        if method == "initialize":
            result: dict[str, Any] = {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "quality-runner", "version": __version__},
            }
        elif method == "tools/list":
            result = {"tools": list_tools()}
        elif method == "tools/call":
            params = message.get("params")
            params = params if isinstance(params, dict) else {}
            tool_name = params.get("name")
            if not isinstance(tool_name, str):
                raise ValueError("tools/call requires params.name")
            arguments = params.get("arguments")
            result = call_tool(tool_name, arguments if isinstance(arguments, dict) else {})
        else:
            raise ValueError(f"Unsupported JSON-RPC method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_jsonrpc_message(json.loads(line))
        if response is None:
            continue
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, indent=2, sort_keys=True)
    return {
        "schema": MCP_RESULT_SCHEMA,
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": False,
    }


def _string_arg(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    return value if isinstance(value, str) and value else None


def _repo_root(arguments: dict[str, Any]) -> Path:
    value = _string_arg(arguments, "repo_root")
    if value is None:
        raise ValueError("repo_root is required")
    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add plugin manifest and skill**

Create `/Users/jakyeamos/quality-runner/quality_runner/plugin/manifest.json`:

```json
{
  "schema": "quality-runner-plugin-manifest-v0.1",
  "name": "quality-runner",
  "version": "0.1.0",
  "commands": {
    "run": {
      "command": "quality-runner",
      "args": ["run"]
    },
    "inspect": {
      "command": "quality-runner",
      "args": ["inspect"]
    }
  },
  "mcp": {
    "command": "quality-runner-mcp",
    "tools": [
      "quality_runner_doctor",
      "quality_runner_inspect_repo",
      "quality_runner_run",
      "quality_runner_status",
      "quality_runner_export_handoff"
    ]
  },
  "skill": "SKILL.md"
}
```

Create `/Users/jakyeamos/quality-runner/quality_runner/plugin/SKILL.md`:

```markdown
---
name: quality-runner
description: Run standalone audit-and-plan quality orchestration for a repository, producing evidence-backed remediation plans without modifying source files.
---

# Quality Runner

Use this skill when the user asks to improve a codebase to their standards, run Quality Runner, audit quality gates, or produce a repo remediation plan through the standalone Quality Runner workflow.

Quality Runner v1 is audit-and-plan only. It writes `.quality-runner/` artifacts and does not modify target source files.

Preferred MCP tool: `quality_runner_run`.

CLI fallback:

```bash
quality-runner run /path/to/repo --standards jakyeamos --json
```
```

- [ ] **Step 5: Run MCP tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit MCP surface**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add quality_runner tests pyproject.toml
git -C /Users/jakyeamos/quality-runner commit -m "Add Quality Runner MCP surface"
```

## Task 7: Run Quality Ladder and Prepare Release-Ready State

**Files:**
- Modify: `/Users/jakyeamos/quality-runner/README.md`
- Create: `/Users/jakyeamos/quality-runner/.pre-cr.json`

- [ ] **Step 1: Add Pre-CR config**

Create `/Users/jakyeamos/quality-runner/.pre-cr.json`:

```json
{
  "version": 1,
  "testCommand": "python -m pytest -q",
  "coveragePaths": [],
  "coverageFormat": "none",
  "threshold": 0,
  "excludePatterns": [
    ".quality-runner/**",
    ".venv/**",
    "tests/**"
  ],
  "checks": {
    "coverage": false,
    "security": false,
    "checklist": false
  }
}
```

- [ ] **Step 2: Update README with v1 guarantees**

Add this section to `/Users/jakyeamos/quality-runner/README.md`:

```markdown
## v1 Safety Boundary

Quality Runner v1 may create or update files under `.quality-runner/runs/<run-id>/` in the target repository. It must not edit source files, install dependencies, create commits, call remote services, or execute remediation.

Every generated remediation slice includes verification guidance, but a separate coding agent must receive user approval before implementation.
```

- [ ] **Step 3: Run formatter/lint**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m ruff check .
python -m ruff format --check .
```

Expected: both commands pass. If `ruff` is unavailable, run it through the local AIOS environment only after deciding how the standalone package will manage dev dependencies.

- [ ] **Step 4: Run typecheck**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m basedpyright
```

Expected: pass. If `basedpyright` is unavailable, record the missing local dependency and run the command from the configured project environment after adding dev tooling in a separate commit.

- [ ] **Step 5: Run tests**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Run dead-code scan**

Run:

```bash
cd /Users/jakyeamos/quality-runner
python -m vulture . --min-confidence 70
```

Expected: pass or documented warnings with clear rationale.

- [ ] **Step 7: Commit release readiness docs**

Run:

```bash
git -C /Users/jakyeamos/quality-runner add README.md .pre-cr.json
git -C /Users/jakyeamos/quality-runner commit -m "Document Quality Runner safety boundary"
```

## Task 8: Update AIOS Truth and Optional Consumption Notes

**Files:**
- Modify: `/Users/jakyeamos/AIOS/.tracker/PROJECT_TRUTH.md`
- Create: `/Users/jakyeamos/AIOS/docs/quality/quality-runner-adoption.md`

- [ ] **Step 1: Add AIOS adoption note**

Create `/Users/jakyeamos/AIOS/docs/quality/quality-runner-adoption.md`:

```markdown
# Quality Runner Adoption

Quality Runner lives in `/Users/jakyeamos/quality-runner` as a standalone audit-and-plan package with CLI and MCP surfaces.

AIOS should consume Quality Runner as an external tool. AIOS may provide adapters, standards profiles, or workflow shortcuts, but the standalone package owns the core workflow and `.quality-runner/` artifact contract.

Initial command:

```bash
quality-runner run /path/to/repo --standards jakyeamos --json
```

Initial MCP tool:

```text
quality_runner_run
```
```

- [ ] **Step 2: Update AIOS project truth**

Update `/Users/jakyeamos/AIOS/.tracker/PROJECT_TRUTH.md`:

- mention that Quality Runner now exists as `/Users/jakyeamos/quality-runner`
- set `lastUpdated` to `2026-06-27`
- keep existing Ruff, format, and BasedPyright failures intact unless full checks were rerun
- record focused Quality Runner checks actually run

- [ ] **Step 3: Run doc checks**

Run:

```bash
git -C /Users/jakyeamos/AIOS diff --check -- .tracker/PROJECT_TRUTH.md docs/quality/quality-runner-adoption.md
```

Expected: no output.

- [ ] **Step 4: Commit AIOS adoption note**

Run:

```bash
git -C /Users/jakyeamos/AIOS add .tracker/PROJECT_TRUTH.md docs/quality/quality-runner-adoption.md
git -C /Users/jakyeamos/AIOS commit -m "Record Quality Runner adoption boundary"
```

## Self-Review

Spec coverage:

- Standalone package: Task 1.
- CLI surface: Task 5.
- MCP surface: Task 6.
- Shared core package: Tasks 2-4.
- Pluggable adapter-ready detection: Task 3 establishes capability map and missing-capability findings.
- `.quality-runner/` artifact layout: Tasks 2 and 4.
- Audit-and-plan only boundary: Tasks 4, 5, 6, and 7.
- Evidence-backed findings: Tasks 2 and 4.
- Remediation slices with verification: Tasks 2 and 4.
- Agent handoff: Task 4.
- AIOS remains adapter/consumer, not owner: Task 8.

Placeholder scan:

- No deferred placeholder markers or unspecified implementation steps remain.
- Commands and expected outcomes are explicit.
- Code identifiers introduced in later tasks are defined in earlier tasks or in the same task.

Execution notes:

- Use frequent commits exactly as listed.
- Do not include unrelated AIOS dirty worktree files in any commit.
- Do not install dependencies over the network unless the user explicitly approves it.
- If local `ruff`, `basedpyright`, or `vulture` modules are unavailable in the standalone repo, stop and decide whether to add dev dependencies or run them through an existing local environment.
