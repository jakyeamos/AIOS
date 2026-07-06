from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

BEHAVIORAL_SPEC_WORKFLOW_KEY = "behavioral-spec-verification-loop"
DEFAULT_MIN_SIGNALS_REQUIRED = 4
DEFAULT_CANONICAL_ARTIFACT = "behavioral-spec.xlsx"
DEFAULT_MAX_FIX_ITERATIONS_PER_STORY = 3

_GENERATED_DIR_NAMES = {
    ".git",
    ".next",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
}
_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".rs", ".java", ".cs"}


@dataclass(frozen=True)
class MaturitySignal:
    key: str
    label: str
    passed: bool
    evidence: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MaturityEligibilityReport:
    repo_path: str
    eligible: bool
    explicit_opt_in: bool
    passed_count: int
    min_signals_required: int
    recommended_workflow: str
    lighter_recommendations: tuple[str, ...]
    canonical_artifact: str
    max_fix_iterations_per_story: int
    signals: dict[str, MaturitySignal]
    rationale: str

    def to_json(self) -> dict[str, object]:
        return {
            "repo_path": self.repo_path,
            "eligible": self.eligible,
            "explicit_opt_in": self.explicit_opt_in,
            "passed_count": self.passed_count,
            "min_signals_required": self.min_signals_required,
            "recommended_workflow": self.recommended_workflow,
            "lighter_recommendations": list(self.lighter_recommendations),
            "canonical_artifact": self.canonical_artifact,
            "max_fix_iterations_per_story": self.max_fix_iterations_per_story,
            "signals": {key: signal.to_json() for key, signal in self.signals.items()},
            "rationale": self.rationale,
        }


def _iter_files(repo_path: Path) -> list[Path]:
    if not repo_path.exists():
        return []
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if any(part in _GENERATED_DIR_NAMES for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _source_line_count(files: list[Path]) -> int:
    total = 0
    for path in files:
        if path.suffix not in _SOURCE_SUFFIXES:
            continue
        try:
            total += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            continue
    return total


def _matches(files: list[Path], root: Path, fragments: tuple[str, ...]) -> tuple[str, ...]:
    evidence: list[str] = []
    for path in files:
        relative = _relative(path, root).lower()
        if any(fragment in relative for fragment in fragments):
            evidence.append(_relative(path, root))
    return tuple(sorted(evidence)[:12])


def _route_files(files: list[Path], root: Path) -> tuple[str, ...]:
    candidates: list[str] = []
    for path in files:
        relative = _relative(path, root)
        parts = set(path.parts)
        if (
            (
                path.name in {"page.tsx", "page.jsx", "route.ts", "route.js"}
                or "pages" in parts
                or "screens" in parts
                or "routes" in parts
            )
            and "/api/" not in relative
            and not relative.startswith("pages/api/")
        ):
            candidates.append(relative)
    return tuple(sorted(set(candidates))[:20])


def _api_files(files: list[Path], root: Path) -> tuple[str, ...]:
    candidates: list[str] = []
    for path in files:
        relative = _relative(path, root)
        relative_lower = relative.lower()
        if "/api/" in relative_lower or relative_lower.startswith("pages/api/"):
            candidates.append(relative)
            continue
        if path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "export async function" in text and (
                "action" in relative_lower or "server" in relative_lower
            ):
                candidates.append(relative)
    return tuple(sorted(set(candidates))[:20])


def assess_behavioral_spec_eligibility(
    repo_path: Path | str,
    *,
    explicit_opt_in: bool = False,
    min_signals_required: int = DEFAULT_MIN_SIGNALS_REQUIRED,
) -> MaturityEligibilityReport:
    root = Path(repo_path).expanduser().resolve()
    files = _iter_files(root)
    routes = _route_files(files, root)
    api_files = _api_files(files, root)
    source_lines = _source_line_count(files)
    admin_flow_files = _matches(
        files,
        root,
        ("admin", "settings", "search", "filter", "sort", "import", "export", "payment", "billing"),
    )
    component_files = _matches(files, root, ("component", "components", "widgets", "ui/"))
    background_files = _matches(
        files, root, ("job", "queue", "cron", "email", "notification", "worker")
    )
    tests = _matches(files, root, ("test.", ".test", ".spec", "tests/", "__tests__"))
    schema_files = _matches(
        files,
        root,
        (
            "schema.sql",
            "schema.prisma",
            "models.py",
            "migration",
            "migrations",
            "drizzle",
            "typeorm",
        ),
    )
    auth_files = _matches(files, root, ("auth", "session", "permission", "role", "middleware"))
    package_files = _matches(
        files, root, ("package.json", "next.config", "vite.config", "app/", "pages/")
    )

    raw_signals = (
        MaturitySignal(
            "routes_or_screens", "App has 8+ routes/pages/screens.", len(routes) >= 8, routes
        ),
        MaturitySignal(
            "api_endpoints_or_server_actions",
            "App has 5+ API endpoints/server actions.",
            len(api_files) >= 5,
            api_files,
        ),
        MaturitySignal(
            "auth_or_permissions",
            "App has auth/session/role/permission logic.",
            bool(auth_files),
            auth_files,
        ),
        MaturitySignal(
            "persistent_data_model",
            "App has a persistent database/schema/models.",
            bool(schema_files),
            schema_files,
        ),
        MaturitySignal(
            "test_infrastructure",
            "App has existing test infrastructure.",
            bool(tests),
            tests,
        ),
        MaturitySignal(
            "discoverable_user_facing_features",
            "App has 10+ discoverable user-facing features.",
            len(routes) + len(admin_flow_files) + len(component_files) >= 10,
            tuple(sorted(set(routes + admin_flow_files + component_files))[:20]),
        ),
        MaturitySignal(
            "background_or_notifications",
            "App has background jobs/queues/emails/notifications.",
            bool(background_files),
            background_files,
        ),
        MaturitySignal(
            "source_size",
            "Repo has 5,000+ non-generated source lines.",
            source_lines >= 5000,
            (f"{source_lines} source lines",),
        ),
        MaturitySignal(
            "admin_settings_or_data_flows",
            "App has admin/settings/search/filter/sort/import/export/payment flows.",
            bool(admin_flow_files),
            admin_flow_files,
        ),
        MaturitySignal(
            "web_app_or_product_platform",
            "Web app or product platform detected.",
            bool(package_files),
            package_files,
        ),
    )
    signals = {signal.key: signal for signal in raw_signals}
    passed_count = sum(1 for signal in raw_signals if signal.passed)
    eligible = explicit_opt_in or passed_count >= min_signals_required
    recommended_workflow = BEHAVIORAL_SPEC_WORKFLOW_KEY if eligible else "targeted-quality-loop"
    lighter_recommendations = (
        ()
        if eligible
        else (
            "basic smoke test loop",
            "route/API inventory",
            "pre-PR quality gate",
            "targeted bugfix loop",
            "test backfill plan",
        )
    )
    rationale = (
        f"Explicit opt-in enables {BEHAVIORAL_SPEC_WORKFLOW_KEY}."
        if explicit_opt_in
        else f"{passed_count} of {min_signals_required} required maturity signals passed."
    )
    return MaturityEligibilityReport(
        repo_path=str(root),
        eligible=eligible,
        explicit_opt_in=explicit_opt_in,
        passed_count=passed_count,
        min_signals_required=min_signals_required,
        recommended_workflow=recommended_workflow,
        lighter_recommendations=lighter_recommendations,
        canonical_artifact=DEFAULT_CANONICAL_ARTIFACT,
        max_fix_iterations_per_story=DEFAULT_MAX_FIX_ITERATIONS_PER_STORY,
        signals=signals,
        rationale=rationale,
    )


def objective_requests_behavioral_spec_loop(objective: str) -> bool:
    normalized = objective.lower()
    return (
        BEHAVIORAL_SPEC_WORKFLOW_KEY in normalized
        or "behavioral spec verification loop" in normalized
        or "mature repo rehabilitation" in normalized
    )


def objective_has_manual_maturity_override(objective: str) -> bool:
    normalized = objective.lower()
    return (
        "explicit opt-in" in normalized
        or "manual override" in normalized
        or "force mature" in normalized
        or "force behavioral-spec" in normalized
    )
