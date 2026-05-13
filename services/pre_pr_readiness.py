from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
from pathlib import Path
from typing import Any, BinaryIO

DEFAULT_TIMEOUT_SECONDS = 330
DEFAULT_PRE_CR_REPO = Path.home() / "projects" / "pre-cr-suite-lsp"
DEFAULT_SERVER_ENTRY = DEFAULT_PRE_CR_REPO / "packages" / "server" / "dist" / "server.js"
EXIT_DEPENDENCY = 4
EXIT_RUNTIME = 5

IGNORED_PREFIXES = (
    ".planning/",
    "docs/",
    "logs/",
    "aios/context/compiled/",
    "aios/context/receipts/",
)
IGNORED_SUFFIXES = {
    ".csv",
    ".db",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".lock",
    ".md",
    ".png",
    ".sql",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
UNSUPPORTED_SUFFIXES = {
    ".bash",
    ".cjs",
    ".js",
    ".jsx",
    ".lua",
    ".mjs",
    ".sh",
    ".ts",
    ".tsx",
    ".zsh",
}


def resolve_server_entry(
    server_entry: str | None = None,
    pre_cr_repo: str | None = None,
) -> Path:
    if server_entry:
        resolved = Path(server_entry).expanduser().resolve()
    else:
        repo_root = Path(pre_cr_repo).expanduser().resolve() if pre_cr_repo else DEFAULT_PRE_CR_REPO.resolve()
        resolved = repo_root / "packages" / "server" / "dist" / "server.js"
    if not resolved.is_file():
        raise _cli_error(
            "pre-cr-server-missing",
            f"Pre-CR server entrypoint not found: {resolved}",
            EXIT_DEPENDENCY,
        )
    return resolved


def classify_changed_paths(paths: list[str]) -> dict[str, list[str]]:
    supported: list[str] = []
    unsupported: list[str] = []
    ignored: list[str] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/").lstrip("./")
        suffix = Path(normalized).suffix.lower()
        if normalized.endswith(".d.ts"):
            ignored.append(normalized)
            continue
        if normalized.startswith(IGNORED_PREFIXES) or suffix in IGNORED_SUFFIXES:
            ignored.append(normalized)
            continue
        if suffix == ".py":
            supported.append(normalized)
            continue
        if suffix in UNSUPPORTED_SUFFIXES:
            unsupported.append(normalized)
            continue
        ignored.append(normalized)
    return {
        "supported": sorted(set(supported)),
        "unsupported": sorted(set(unsupported)),
        "ignored": sorted(set(ignored)),
    }


def summarize_pre_pr_readiness(
    *,
    workspace_root: Path,
    run_result: dict[str, Any],
    server_entry: Path,
) -> dict[str, Any]:
    result = run_result.get("result")
    if not isinstance(result, dict):
        return {
            "workspace_root": str(workspace_root),
            "server_entry": str(server_entry),
            "status": "fail",
            "supported_changed_files": [],
            "unsupported_changed_files": [],
            "ignored_changed_files": [],
            "coverage": None,
            "findings": [
                {
                    "severity": "error",
                    "code": "pre_cr_run_failed",
                    "summary": str(run_result.get("error") or "Pre-CR did not return a result."),
                }
            ],
            "pre_cr": run_result,
        }

    changed_files = result.get("changedFiles")
    changed_paths = [
        str(entry.get("path"))
        for entry in changed_files
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ] if isinstance(changed_files, list) else []
    classified = classify_changed_paths(changed_paths)

    findings: list[dict[str, Any]] = []
    if not changed_paths:
        findings.append(
            {
                "severity": "error",
                "code": "no_changes",
                "summary": "Pre-PR readiness cannot run against an empty diff.",
            }
        )

    if classified["unsupported"]:
        findings.append(
            {
                "severity": "error",
                "code": "unsupported_surface",
                "summary": "This gate does not yet cover changed JS/TS/shell surfaces in AIOS.",
                "files": classified["unsupported"],
            }
        )

    health = result.get("health") if isinstance(result.get("health"), dict) else {}
    issues = health.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            severity = str(issue.get("severity") or "warning")
            findings.append(
                {
                    "severity": severity,
                    "code": f"pre_cr_{issue.get('code', 'issue')}",
                    "summary": str(issue.get("message") or "Pre-CR reported a project issue."),
                    "hint": issue.get("hint"),
                }
            )

    test_run = result.get("testRun") if isinstance(result.get("testRun"), dict) else None
    if test_run and not bool(test_run.get("success")):
        findings.append(
            {
                "severity": "error",
                "code": "test_run_failed",
                "summary": "Pre-CR test execution failed before coverage validation completed.",
                "command": test_run.get("command"),
                "exit_code": test_run.get("exitCode"),
            }
        )

    coverage_check = result.get("coverageCheck") if isinstance(result.get("coverageCheck"), dict) else None
    if coverage_check is None:
        findings.append(
            {
                "severity": "error",
                "code": "coverage_check_missing",
                "summary": "Pre-CR did not produce a changed-line coverage result.",
            }
        )
    elif not bool(coverage_check.get("passed")):
        findings.append(
            {
                "severity": "error",
                "code": "coverage_below_threshold",
                "summary": "Changed-line coverage is below the configured threshold.",
                "coverage_percent": coverage_check.get("coveragePercent"),
                "threshold": coverage_check.get("threshold"),
            }
        )

    status = "fail" if any(item["severity"] == "error" for item in findings) else "pass"
    return {
        "workspace_root": str(workspace_root),
        "server_entry": str(server_entry),
        "status": status,
        "supported_changed_files": classified["supported"],
        "unsupported_changed_files": classified["unsupported"],
        "ignored_changed_files": classified["ignored"],
        "coverage": coverage_check,
        "findings": findings,
        "pre_cr": run_result,
    }


def pre_pr_readiness_payload(
    *,
    workspace_root: str | Path,
    server_entry: str | None = None,
    pre_cr_repo: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    node_bin = shutil.which("node")
    if not node_bin:
        raise _cli_error("node-not-found", "Node.js is required for Pre-PR readiness", EXIT_DEPENDENCY)

    resolved_workspace = Path(workspace_root).expanduser().resolve()
    resolved_server = resolve_server_entry(server_entry=server_entry, pre_cr_repo=pre_cr_repo)
    session = _PreCrSession(
        workspace_root=resolved_workspace,
        server_entry=resolved_server,
        node_bin=Path(node_bin),
        timeout_seconds=timeout_seconds,
    )
    run_result = session.run_pre_cr_check()
    return summarize_pre_pr_readiness(
        workspace_root=resolved_workspace,
        run_result=run_result,
        server_entry=resolved_server,
    )


class _PreCrSession:
    def __init__(
        self,
        *,
        workspace_root: Path,
        server_entry: Path,
        node_bin: Path,
        timeout_seconds: int,
    ) -> None:
        self.workspace_root = workspace_root
        self.server_entry = server_entry
        self.timeout_seconds = timeout_seconds
        repo_root = server_entry.parents[3]
        self.process = subprocess.Popen(
            [str(node_bin), str(server_entry), "--stdio"],
            cwd=str(repo_root),
            env={
                **os.environ,
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "status.showUntrackedFiles",
                "GIT_CONFIG_VALUE_0": "all",
            },
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            raise _cli_error("pre-cr-process-failed", "Failed to start Pre-CR server process", EXIT_RUNTIME)
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self.next_id = 1

    def run_pre_cr_check(self) -> dict[str, Any]:
        try:
            self._request(
                "initialize",
                {
                    "processId": None,
                    "clientInfo": {"name": "AIOS", "version": "0.1.0"},
                    "rootUri": self.workspace_root.as_uri(),
                    "workspaceFolders": [
                        {
                            "uri": self.workspace_root.as_uri(),
                            "name": self.workspace_root.name,
                        }
                    ],
                    "capabilities": {
                        "workspace": {
                            "configuration": False,
                            "workspaceFolders": True,
                        }
                    },
                },
            )
            self._notify("initialized", {})
            return self._request("$/preCr/runPreCrCheck", {})
        finally:
            self._close()

    def _close(self) -> None:
        try:
            self._request("shutdown", {})
        except Exception:
            pass
        try:
            self._notify("exit", {})
        except Exception:
            pass
        try:
            self.process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=2)

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        while True:
            message = _read_message(self.stdout, timeout_seconds=self.timeout_seconds)
            if message.get("id") == request_id:
                if "error" in message:
                    error = message["error"]
                    detail = json.dumps(error, sort_keys=True)
                    raise _cli_error("pre-cr-rpc-error", f"{method} failed: {detail}", EXIT_RUNTIME)
                return message.get("result", {})

    def _send(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.stdin.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
        self.stdin.write(encoded)
        self.stdin.flush()


def _read_message(stream: BinaryIO, *, timeout_seconds: int) -> dict[str, Any]:
    ready, _, _ = select.select([stream], [], [], timeout_seconds)
    if not ready:
        raise _cli_error("pre-cr-timeout", "Timed out waiting for Pre-CR server output", EXIT_RUNTIME)
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            raise _cli_error("pre-cr-eof", "Pre-CR server closed the connection unexpectedly", EXIT_RUNTIME)
        if line == b"\r\n":
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.strip().lower()] = value.strip()
    content_length = headers.get("content-length")
    if not content_length:
        raise _cli_error("pre-cr-protocol-error", "Missing Content-Length header from Pre-CR server", EXIT_RUNTIME)
    body = stream.read(int(content_length))
    if not body:
        raise _cli_error("pre-cr-protocol-error", "Empty message body from Pre-CR server", EXIT_RUNTIME)
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise _cli_error("pre-cr-protocol-error", "Invalid JSON-RPC payload from Pre-CR server", EXIT_RUNTIME)
    return payload


def _cli_error(code: str, message: str, exit_code: int) -> Exception:
    from services.aios_cli import CLIError

    return CLIError(code, message, exit_code)
