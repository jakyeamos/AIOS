from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOKLM_BACKENDS_PATH = ROOT / "config" / "notebooklm" / "backends.json"

NotebookLMMode = Literal[
    "bounded_source_synthesis",
    "connection_discovery",
    "knowledge_cartography",
    "tmcp_module_discovery",
    "learning_opportunity_detection",
    "contradiction_drift_detection",
    "project_resurfacing",
    "briefing_digest",
]
ALL_NOTEBOOKLM_MODES: tuple[NotebookLMMode, ...] = (
    "bounded_source_synthesis",
    "connection_discovery",
    "knowledge_cartography",
    "tmcp_module_discovery",
    "learning_opportunity_detection",
    "contradiction_drift_detection",
    "project_resurfacing",
    "briefing_digest",
)

RouteKind = Literal[
    "code_search_filesystem",
    "source_of_truth_memory",
    "local_operational_memory",
    "tmcp",
    "notebooklm_mcp",
    "local_first_notebooklm_second",
    "web_search",
    "reject_unbounded_notebooklm",
]

SENSITIVE_CLASSES = frozenset({"secret", "credential", "sensitive", "raw_operational"})
RAW_OPERATIONAL_PARTS = frozenset({"logs", "data", ".git"})
DEFAULT_BACKEND_KEY = "jacob_bd_notebooklm_mcp_cli"

@dataclass(frozen=True)
class NotebookLMRouteDecision:
    route_kind: RouteKind
    route_steps: tuple[str, ...]
    reason: str
    use_notebooklm: bool
    local_retrieval_first: bool
    stage_output: bool
    human_review_required: bool
    mode: NotebookLMMode | None = None
    reject_reason: str | None = None

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCandidate:
    path: str
    title: str
    source_type: str
    last_modified: str | None = None
    inclusion_reason: str = ""
    sensitivity_class: str = "normal"


@dataclass(frozen=True)
class ExcludedSource:
    path: str
    exclusion_reason: str


@dataclass(frozen=True)
class SourceBundle:
    bundle_name: str
    bundle_id: str
    created_at: str
    created_by: str
    task: str
    route_reason: str
    sources: tuple[SourceCandidate, ...]
    excluded_sources: tuple[ExcludedSource, ...] = ()

    @property
    def source_count(self) -> int:
        return len(self.sources)

    def to_json(self) -> dict[str, object]:
        payload = asdict(self)
        payload["source_count"] = self.source_count
        return payload


@dataclass(frozen=True)
class NotebookLMProvenance:
    source_system: str
    route_type: NotebookLMMode
    source_bundle_name: str
    source_bundle_id: str
    source_count: int
    notebook_id_or_alias: str | None
    query: str
    timestamp: str
    agent: str
    reason_for_route: str
    local_retrieval_used_first: bool
    output_destination: str
    promoted_to_obsidian: bool = False
    promoted_to_tmcp: bool = False
    promoted_to_project_docs: bool = False
    human_review_required: bool = True

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotebookLMSynthesisResult:
    status: Literal["completed", "skipped_unavailable"]
    answer: str
    citations: tuple[str, ...]
    provenance: NotebookLMProvenance
    warnings: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotebookLMCommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str = ""


class NotebookLMCommandRunner(Protocol):
    def __call__(self, args: tuple[str, ...], timeout: float) -> NotebookLMCommandResult:
        ...


@dataclass(frozen=True)
class NotebookLMBackendSpec:
    key: str
    name: str
    lifecycle_state: str
    source_url: str
    install_command: str
    cli_command: str
    mcp_command: str
    required_executables: tuple[str, ...]
    recommended_auth_check: tuple[str, ...]
    mcp_tool_probe: str
    required_tools: tuple[str, ...]
    optional_tools: tuple[str, ...]
    mode_tool_plan: dict[NotebookLMMode, tuple[str, ...]]
    security_notes: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotebookLMBackendReadiness:
    backend_key: str
    available: bool
    missing_executables: tuple[str, ...]
    required_tools: tuple[str, ...]
    mcp_tool_probe: str
    auth_check_command: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NotebookLMCLIExecution:
    notebook_id: str
    commands: tuple[tuple[str, ...], ...]
    answer: str
    citations: tuple[str, ...] = ()


class NotebookLMBackend(Protocol):
    def synthesize(
        self,
        *,
        mode: NotebookLMMode,
        query: str,
        source_bundle: SourceBundle,
        notebook_id_or_alias: str | None = None,
        agent: str = "aios",
        output_destination: str = "aios/staging/notebooklm",
    ) -> NotebookLMSynthesisResult:
        ...


class NotebookLMMCPAdapter:
    """Optional adapter boundary for a NotebookLM MCP server."""

    def __init__(
        self,
        *,
        backend_spec: NotebookLMBackendSpec | None = None,
        readiness: NotebookLMBackendReadiness | None = None,
    ) -> None:
        self.backend_spec = backend_spec or load_notebooklm_backend_spec()
        self.readiness = readiness or check_notebooklm_backend_readiness(self.backend_spec)

    def synthesize(
        self,
        *,
        mode: NotebookLMMode,
        query: str,
        source_bundle: SourceBundle,
        notebook_id_or_alias: str | None = None,
        agent: str = "aios",
        output_destination: str = "aios/staging/notebooklm",
    ) -> NotebookLMSynthesisResult:
        provenance = build_notebooklm_provenance(
            mode=mode,
            query=query,
            source_bundle=source_bundle,
            notebook_id_or_alias=notebook_id_or_alias,
            agent=agent,
            reason_for_route=source_bundle.route_reason,
            local_retrieval_used_first=True,
            output_destination=output_destination,
        )
        if not self.readiness.available:
            return NotebookLMSynthesisResult(
                status="skipped_unavailable",
                answer=(
                    "NotebookLM MCP is unavailable. AIOS should continue with local retrieval "
                    "and stage any local synthesis with the skipped NotebookLM provenance."
                ),
                citations=(),
                provenance=provenance,
                warnings=("notebooklm_mcp_unavailable", *self.readiness.warnings),
            )
        tool_plan = notebooklm_tool_plan_for_mode(mode, self.backend_spec)
        raise NotImplementedError(
            "NotebookLM MCP live invocation is not wired yet. "
            f"Backend {self.backend_spec.key} is ready; expected tool plan: {', '.join(tool_plan)}."
        )


class NotebookLMCLIAdapter:
    """Guarded live adapter for jacob-bd/notebooklm-mcp-cli's `nlm` command."""

    def __init__(
        self,
        *,
        backend_spec: NotebookLMBackendSpec | None = None,
        readiness: NotebookLMBackendReadiness | None = None,
        runner: NotebookLMCommandRunner | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.backend_spec = backend_spec or load_notebooklm_backend_spec()
        self.readiness = readiness or check_notebooklm_backend_readiness(self.backend_spec)
        self.runner = runner or run_notebooklm_command
        self.timeout_seconds = timeout_seconds

    def synthesize(
        self,
        *,
        mode: NotebookLMMode,
        query: str,
        source_bundle: SourceBundle,
        notebook_id_or_alias: str | None = None,
        agent: str = "aios",
        output_destination: str = "aios/staging/notebooklm",
        require_auth_check: bool = True,
    ) -> NotebookLMSynthesisResult:
        provenance = build_notebooklm_provenance(
            mode=mode,
            query=query,
            source_bundle=source_bundle,
            notebook_id_or_alias=notebook_id_or_alias,
            agent=agent,
            reason_for_route=source_bundle.route_reason,
            local_retrieval_used_first=True,
            output_destination=output_destination,
        )
        warnings = notebooklm_live_use_warnings(source_bundle)
        if warnings:
            return NotebookLMSynthesisResult(
                status="skipped_unavailable",
                answer="NotebookLM live synthesis was skipped because the source bundle is not safe for live use.",
                citations=(),
                provenance=provenance,
                warnings=warnings,
            )
        if not self.readiness.available:
            return NotebookLMSynthesisResult(
                status="skipped_unavailable",
                answer="NotebookLM CLI backend is unavailable.",
                citations=(),
                provenance=provenance,
                warnings=("notebooklm_cli_unavailable", *self.readiness.warnings),
            )
        if require_auth_check:
            auth = self._run(self.readiness.auth_check_command)
            if auth.returncode != 0:
                return NotebookLMSynthesisResult(
                    status="skipped_unavailable",
                    answer="NotebookLM CLI authentication is unavailable. Run `nlm login` before live use.",
                    citations=(),
                    provenance=provenance,
                    warnings=("notebooklm_cli_auth_unavailable", _stderr_or_stdout(auth)),
                )

        try:
            execution = self._execute(mode=mode, query=query, source_bundle=source_bundle, notebook_id_or_alias=notebook_id_or_alias)
        except RuntimeError as error:
            return NotebookLMSynthesisResult(
                status="skipped_unavailable",
                answer=f"NotebookLM CLI execution failed: {error}",
                citations=(),
                provenance=provenance,
                warnings=("notebooklm_cli_execution_failed",),
            )

        return NotebookLMSynthesisResult(
            status="completed",
            answer=execution.answer,
            citations=execution.citations,
            provenance=build_notebooklm_provenance(
                mode=mode,
                query=query,
                source_bundle=source_bundle,
                notebook_id_or_alias=execution.notebook_id,
                agent=agent,
                reason_for_route=source_bundle.route_reason,
                local_retrieval_used_first=True,
                output_destination=output_destination,
            ),
            warnings=("experimental_notebooklm_backend",),
        )

    def _execute(
        self,
        *,
        mode: NotebookLMMode,
        query: str,
        source_bundle: SourceBundle,
        notebook_id_or_alias: str | None,
    ) -> NotebookLMCLIExecution:
        commands: list[tuple[str, ...]] = []
        notebook_id = notebook_id_or_alias
        if notebook_id is None:
            create_command = (
                self.backend_spec.cli_command,
                "notebook",
                "create",
                _notebook_title_for_bundle(source_bundle),
                "--quiet",
            )
            create = self._run(create_command)
            commands.append(create_command)
            _raise_for_command(create, "create notebook")
            notebook_id = _first_output_line(create.stdout)
        if not notebook_id:
            raise RuntimeError("notebook create did not return a notebook id")

        for source in source_bundle.sources:
            source_command = _source_add_command(self.backend_spec.cli_command, notebook_id, source)
            add = self._run(source_command)
            commands.append(source_command)
            _raise_for_command(add, f"add source {source.path}")

        if mode == "briefing_digest":
            query = _briefing_query(query)
        query_command = (self.backend_spec.cli_command, "notebook", "query", notebook_id, query)
        queried = self._run(query_command)
        commands.append(query_command)
        _raise_for_command(queried, "query notebook")
        return NotebookLMCLIExecution(
            notebook_id=notebook_id,
            commands=tuple(commands),
            answer=queried.stdout.strip(),
            citations=_extract_citation_lines(queried.stdout),
        )

    def _run(self, args: tuple[str, ...]) -> NotebookLMCommandResult:
        return self.runner(args, self.timeout_seconds)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_notebooklm_backend_spec(
    backend_key: str = DEFAULT_BACKEND_KEY,
    *,
    path: Path | None = None,
) -> NotebookLMBackendSpec:
    registry_path = path or DEFAULT_NOTEBOOKLM_BACKENDS_PATH
    with registry_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    backends = loaded.get("backends")
    if not isinstance(backends, list):
        raise ValueError(f"NotebookLM backend registry at {registry_path} must contain backends.")
    for item in backends:
        if not isinstance(item, dict) or item.get("key") != backend_key:
            continue
        readiness = item.get("readiness_probe") or {}
        if not isinstance(readiness, dict):
            raise ValueError(f"NotebookLM backend {backend_key} readiness_probe must be an object.")
        raw_plan = item.get("mode_tool_plan") or {}
        if not isinstance(raw_plan, dict):
            raise ValueError(f"NotebookLM backend {backend_key} mode_tool_plan must be an object.")
        return NotebookLMBackendSpec(
            key=str(item["key"]),
            name=str(item.get("name", backend_key)),
            lifecycle_state=str(item.get("lifecycle_state", "experimental")),
            source_url=str(item.get("source_url", "")),
            install_command=str(item.get("install_command", "")),
            cli_command=str(item.get("cli_command", "nlm")),
            mcp_command=str(item.get("mcp_command", "notebooklm-mcp")),
            required_executables=tuple(
                str(value) for value in readiness.get("required_executables", []) if value
            ),
            recommended_auth_check=tuple(
                str(value) for value in readiness.get("recommended_auth_check", []) if value
            ),
            mcp_tool_probe=str(readiness.get("mcp_tool_probe", "server_info")),
            required_tools=tuple(str(value) for value in item.get("required_tools", []) if value),
            optional_tools=tuple(str(value) for value in item.get("optional_tools", []) if value),
            mode_tool_plan={
                _mode_key(mode): tuple(str(tool) for tool in tools if tool)
                for mode, tools in raw_plan.items()
                if isinstance(tools, list)
            },
            security_notes=tuple(str(value) for value in item.get("security_notes", []) if value),
        )
    raise ValueError(f"NotebookLM backend {backend_key!r} not found in {registry_path}.")


def check_notebooklm_backend_readiness(
    backend_spec: NotebookLMBackendSpec,
) -> NotebookLMBackendReadiness:
    missing = tuple(
        executable
        for executable in backend_spec.required_executables
        if shutil.which(executable) is None
    )
    warnings: list[str] = []
    if missing:
        warnings.append("missing_notebooklm_backend_executables")
    if backend_spec.lifecycle_state != "active":
        warnings.append(f"backend_lifecycle_state:{backend_spec.lifecycle_state}")
    return NotebookLMBackendReadiness(
        backend_key=backend_spec.key,
        available=not missing,
        missing_executables=missing,
        required_tools=backend_spec.required_tools,
        mcp_tool_probe=backend_spec.mcp_tool_probe,
        auth_check_command=backend_spec.recommended_auth_check,
        warnings=tuple(warnings),
    )


def run_notebooklm_command(args: tuple[str, ...], timeout: float) -> NotebookLMCommandResult:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return NotebookLMCommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def notebooklm_live_use_warnings(source_bundle: SourceBundle) -> tuple[str, ...]:
    warnings: list[str] = []
    if not source_bundle.sources:
        warnings.append("empty_source_bundle")
    if source_bundle.excluded_sources:
        warnings.append("source_bundle_has_exclusions_review_required")
    for source in source_bundle.sources:
        reason = _source_exclusion_reason(source, 0, max_sources=1_000_000)
        if reason:
            warnings.append(f"unsafe_source:{source.path}:{reason}")
    return tuple(warnings)


def notebooklm_tool_plan_for_mode(
    mode: NotebookLMMode,
    backend_spec: NotebookLMBackendSpec | None = None,
) -> tuple[str, ...]:
    spec = backend_spec or load_notebooklm_backend_spec()
    return spec.mode_tool_plan.get(mode, spec.required_tools)


def _mode_key(value: str) -> NotebookLMMode:
    if value not in ALL_NOTEBOOKLM_MODES:
        raise ValueError(f"Unsupported NotebookLM mode in backend config: {value}")
    return cast(NotebookLMMode, value)


def classify_notebooklm_route(objective: str) -> NotebookLMRouteDecision:
    text = " ".join(objective.lower().split())

    if _has_any(text, "entire second brain", "whole vault", "entire vault", "dump my vault"):
        return NotebookLMRouteDecision(
            route_kind="reject_unbounded_notebooklm",
            route_steps=("reject whole-vault dump", "ask for a bounded topic, folder, or project"),
            reason="NotebookLM source bundles must be bounded and selected by AIOS or the user.",
            use_notebooklm=False,
            local_retrieval_first=True,
            stage_output=False,
            human_review_required=True,
            reject_reason="unbounded_source_bundle",
        )

    if _has_any(text, "search the whole repo", "broken imports", "code search"):
        return NotebookLMRouteDecision(
            route_kind="code_search_filesystem",
            route_steps=("use repo tools", "use shell/code search/local files"),
            reason="Repo inspection and code execution tasks should use filesystem tools.",
            use_notebooklm=False,
            local_retrieval_first=False,
            stage_output=False,
            human_review_required=False,
        )

    if _has_any(text, "resume the last agent session", "previous tool failures", "session state"):
        return NotebookLMRouteDecision(
            route_kind="local_operational_memory",
            route_steps=("use SQLite/local operational memory",),
            reason="Raw session state, telemetry, and tool traces stay local.",
            use_notebooklm=False,
            local_retrieval_first=False,
            stage_output=False,
            human_review_required=False,
        )

    if _has_any(text, "what did i decide", "source-of-truth", "source of truth"):
        return NotebookLMRouteDecision(
            route_kind="source_of_truth_memory",
            route_steps=("use Obsidian/local markdown/TMCP",),
            reason="Source-of-truth memory lookups should use canonical local memory first.",
            use_notebooklm=False,
            local_retrieval_first=True,
            stage_output=False,
            human_review_required=False,
        )

    if _has_any(text, "existing tmcp notes") and _has_any(text, "uploaded research packet"):
        return NotebookLMRouteDecision(
            route_kind="local_first_notebooklm_second",
            route_steps=("local/TMCP first", "NotebookLM MCP second", "stage synthesis output"),
            reason=(
                "Canonical AIOS context comes from local memory; the uploaded packet can be "
                "synthesized as a bounded source bundle."
            ),
            use_notebooklm=True,
            local_retrieval_first=True,
            stage_output=True,
            human_review_required=True,
            mode="bounded_source_synthesis",
        )

    if _has_any(text, "hidden connections", "cross-note", "reusable modules", "knowledge clusters"):
        mode: NotebookLMMode = "tmcp_module_discovery" if "module" in text else "connection_discovery"
        return NotebookLMRouteDecision(
            route_kind="local_first_notebooklm_second",
            route_steps=(
                "local retrieval selects relevant notes",
                "NotebookLM MCP performs connection discovery",
                "stage results",
                "suggest Obsidian/TMCP promotion",
            ),
            reason="The task asks for relationships and reusable abstractions, not simple fact lookup.",
            use_notebooklm=True,
            local_retrieval_first=True,
            stage_output=True,
            human_review_required=True,
            mode=mode,
        )

    if _has_any(text, "learn next", "learning opportunity", "learning path"):
        return NotebookLMRouteDecision(
            route_kind="local_first_notebooklm_second",
            route_steps=(
                "local retrieval selects recent relevant notes",
                "build bounded source bundle",
                "NotebookLM MCP synthesizes learning opportunities",
                "stage learning path",
            ),
            reason="The task asks for synthesis across notes and learning gaps.",
            use_notebooklm=True,
            local_retrieval_first=True,
            stage_output=True,
            human_review_required=True,
            mode="learning_opportunity_detection",
        )

    if _has_any(text, "outdated", "older", "contradiction", "drift", "stale assumption"):
        return NotebookLMRouteDecision(
            route_kind="local_first_notebooklm_second",
            route_steps=(
                "local retrieval selects older and current notes",
                "NotebookLM MCP performs drift/contradiction detection",
                "stage drift report",
            ),
            reason="The task requires comparison and stale-assumption detection.",
            use_notebooklm=True,
            local_retrieval_first=True,
            stage_output=True,
            human_review_required=True,
            mode="contradiction_drift_detection",
        )

    if _has_any(text, "uploaded", "selected documents", "source bundle", "papers", "transcripts") and _has_any(
        text, "compare", "synthesis", "summarize", "brief", "digest"
    ):
        return NotebookLMRouteDecision(
            route_kind="notebooklm_mcp",
            route_steps=("use NotebookLM MCP over the selected bounded source bundle",),
            reason="The task is bounded source synthesis over selected documents.",
            use_notebooklm=True,
            local_retrieval_first=False,
            stage_output=True,
            human_review_required=True,
            mode="bounded_source_synthesis",
        )

    return NotebookLMRouteDecision(
        route_kind="source_of_truth_memory",
        route_steps=("use Obsidian/local markdown/TMCP first",),
        reason="Default second-brain tasks stay on canonical local memory unless synthesis is required.",
        use_notebooklm=False,
        local_retrieval_first=True,
        stage_output=False,
        human_review_required=False,
    )


def build_source_bundle(
    *,
    task: str,
    route_reason: str,
    candidates: list[SourceCandidate],
    bundle_name: str | None = None,
    created_by: str = "aios",
    max_sources: int = 20,
) -> SourceBundle:
    included: list[SourceCandidate] = []
    excluded: list[ExcludedSource] = []

    for candidate in candidates:
        exclusion_reason = _source_exclusion_reason(candidate, len(included), max_sources)
        if exclusion_reason:
            excluded.append(ExcludedSource(path=candidate.path, exclusion_reason=exclusion_reason))
            continue
        included.append(candidate)

    bundle_seed = "\n".join([task, route_reason, *(source.path for source in included)])
    digest = hashlib.sha256(bundle_seed.encode("utf-8")).hexdigest()[:12]
    return SourceBundle(
        bundle_name=bundle_name or _slug(task),
        bundle_id=f"source-bundle-{digest}",
        created_at=now_iso(),
        created_by=created_by,
        task=task,
        route_reason=route_reason,
        sources=tuple(included),
        excluded_sources=tuple(excluded),
    )


def export_source_bundle_for_notebooklm(
    source_bundle: SourceBundle,
    *,
    output_root: Path | None = None,
) -> Path:
    root = output_root or ROOT / "staging" / "notebooklm"
    bundle_dir = root / source_bundle.bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(
        json.dumps(source_bundle.to_json(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (bundle_dir / "prompt.md").write_text(
        _default_prompt_for_bundle(source_bundle),
        encoding="utf-8",
    )
    (bundle_dir / "upload-instructions.md").write_text(
        _upload_instructions(source_bundle),
        encoding="utf-8",
    )
    return bundle_dir


def build_notebooklm_provenance(
    *,
    mode: NotebookLMMode,
    query: str,
    source_bundle: SourceBundle,
    notebook_id_or_alias: str | None,
    agent: str,
    reason_for_route: str,
    local_retrieval_used_first: bool,
    output_destination: str,
) -> NotebookLMProvenance:
    return NotebookLMProvenance(
        source_system="notebooklm_mcp",
        route_type=mode,
        source_bundle_name=source_bundle.bundle_name,
        source_bundle_id=source_bundle.bundle_id,
        source_count=source_bundle.source_count,
        notebook_id_or_alias=notebook_id_or_alias,
        query=query,
        timestamp=now_iso(),
        agent=agent,
        reason_for_route=reason_for_route,
        local_retrieval_used_first=local_retrieval_used_first,
        output_destination=output_destination,
    )


def notebooklm_staging_note_template(title: str) -> str:
    return f"""# NotebookLM Synthesis: {title}

## Mode

- [ ] Bounded source synthesis
- [ ] Connection discovery
- [ ] Knowledge cartography
- [ ] TMCP module discovery
- [ ] Learning opportunity detection
- [ ] Contradiction / drift detection
- [ ] Project resurfacing
- [ ] Briefing / digest

## Source Bundle

## Original Query

## Summary

## Key Findings

## Important Connections

## Contradictions / Open Questions

## Learning Opportunities

## Candidate TMCP Modules

## Recommended Promotion Target

- [ ] Obsidian
- [ ] TMCP
- [ ] Project docs
- [ ] Keep staged
- [ ] Discard

## Provenance

## Review Notes
"""


def _source_exclusion_reason(
    candidate: SourceCandidate, included_count: int, max_sources: int
) -> str | None:
    if candidate.sensitivity_class in SENSITIVE_CLASSES:
        return f"disallowed_sensitivity_class:{candidate.sensitivity_class}"
    path_parts = {part.lower() for part in Path(candidate.path).parts}
    if path_parts & RAW_OPERATIONAL_PARTS:
        return "raw_operational_or_repo_metadata_path"
    if included_count >= max_sources:
        return "source_bundle_limit_reached"
    return None


def _source_add_command(cli_command: str, notebook_id: str, source: SourceCandidate) -> tuple[str, ...]:
    match source.source_type:
        case "url":
            return (cli_command, "source", "add", notebook_id, "--url", source.path, "--wait")
        case "text":
            return (
                cli_command,
                "source",
                "add",
                notebook_id,
                "--text",
                source.path,
                "--title",
                source.title,
                "--wait",
            )
        case "drive":
            return (cli_command, "source", "add", notebook_id, "--drive", source.path, "--wait")
        case _:
            return (cli_command, "source", "add", notebook_id, "--file", source.path, "--wait")


def _raise_for_command(result: NotebookLMCommandResult, action: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(f"{action} failed: {_stderr_or_stdout(result)}")


def _stderr_or_stdout(result: NotebookLMCommandResult) -> str:
    return (result.stderr or result.stdout or "no command output").strip()


def _first_output_line(value: str) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _notebook_title_for_bundle(source_bundle: SourceBundle) -> str:
    title = source_bundle.bundle_name.replace("-", " ").strip()
    return f"AIOS {title}"[:120]


def _briefing_query(query: str) -> str:
    return (
        f"{query}\n\n"
        "Return a structured briefing with Summary, Key Ideas, Open Questions, FAQ, "
        "Glossary, Suggested Next Actions, and source-grounded provenance."
    )


def _extract_citation_lines(value: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in value.splitlines()
        if line.strip().lower().startswith(("source:", "citation:", "["))
    )


def _default_prompt_for_bundle(source_bundle: SourceBundle) -> str:
    return (
        f"# NotebookLM Prompt: {source_bundle.bundle_name}\n\n"
        f"Task: {source_bundle.task}\n\n"
        "Use only the uploaded source bundle. Identify relationships, contradictions, "
        "learning opportunities, reusable TMCP candidates, and any uncertainty. "
        "Return source-grounded findings with provenance."
    )


def _upload_instructions(source_bundle: SourceBundle) -> str:
    source_lines = "\n".join(f"- `{source.path}` ({source.source_type})" for source in source_bundle.sources)
    return (
        f"# Upload Instructions: {source_bundle.bundle_name}\n\n"
        "Use this only if live `nlm` automation is unavailable.\n\n"
        "1. Create a NotebookLM notebook.\n"
        "2. Upload or add these bounded sources:\n"
        f"{source_lines}\n"
        "3. Ask NotebookLM with `prompt.md`.\n"
        "4. Paste or export the result back into AIOS staging.\n"
    )


def _slug(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in value.strip()]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug[:72] or f"notebooklm-bundle-{uuid.uuid4()}"


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)
