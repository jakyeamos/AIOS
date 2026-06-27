from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_eval_contract import HARNESS_DIMENSION_NAMES, validate_harness_fixture_components

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "docs" / "aios" / "harness-eval" / "config.json"
DEFAULT_DX_FIXTURE_CONFIG_PATH = (
    REPO_ROOT / "config" / "agent-eval" / "developer-experience-fixtures.json"
)
REQUIRED_DX_FIXTURE_IDS = frozenset(
    {
        "poor_onboarding_repo",
        "public_cli_change",
        "typescript_package_boundary_change",
    }
)
DIMENSION_NAMES = HARNESS_DIMENSION_NAMES


@dataclass(frozen=True)
class HarnessEvalConfigFixture:
    id: str
    category: str
    path: Path


@dataclass(frozen=True)
class HarnessEvalConfig:
    version: int
    eval_name: str
    goal: str
    fixtures: list[HarnessEvalConfigFixture]


@dataclass(frozen=True)
class HarnessEvalFixture:
    id: str
    path: Path
    task_markdown: str
    expected_context_packets: list[str]
    expected_gates: list[dict[str, str]]
    expected_success_criteria: list[str]
    golden_outcome_markdown: str
    scoring: dict[str, Any]
    runs: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class HarnessEvalScore:
    fixture_id: str
    run_id: str
    harness_name: str
    dimensions: dict[str, float | bool]
    failed_dimensions: list[str]
    overall_score: float
    evidence_path: str


@dataclass(frozen=True)
class HarnessEvalSuiteResult:
    eval_name: str
    config_path: str
    totals: dict[str, int | float]
    results: list[HarnessEvalScore]


@dataclass(frozen=True)
class DeveloperExperienceEvalFixture:
    id: str
    category: str
    title: str
    second_brain_modes: list[str]
    expected_capabilities: list[str]
    forbidden_capabilities: list[str]
    criteria: list[str]


@dataclass(frozen=True)
class DeveloperExperienceEvalConfig:
    version: int
    eval_name: str
    category: str
    spec_path: Path
    criteria: list[str]
    fixtures: list[DeveloperExperienceEvalFixture]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_path(_path: Path, raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _set_score(expected: list[str], actual: list[str]) -> tuple[float, float]:
    expected_set = set(expected)
    actual_set = set(actual)
    recall = 1.0 if not expected_set else len(expected_set & actual_set) / len(expected_set)
    if not actual_set:
        precision = 1.0 if not expected_set else 0.0
    else:
        precision = len(expected_set & actual_set) / len(actual_set)
    return round(precision, 4), round(recall, 4)


def _event_types(run: Mapping[str, Any]) -> set[str]:
    event_log = run.get("event_log", [])
    if not isinstance(event_log, list):
        return set()
    events: set[str] = set()
    for event in event_log:
        if isinstance(event, Mapping):
            event_type = event.get("event_type") or event.get("type")
            if event_type:
                events.add(str(event_type))
    return events


def _gate_accuracy(expected_gates: list[dict[str, str]], run: Mapping[str, Any]) -> float:
    if not expected_gates:
        return 1.0
    approval_events = run.get("approval_events", [])
    if not isinstance(approval_events, list):
        approval_events = []
    actual = {
        str(event.get("gate_id")): str(event.get("decision"))
        for event in approval_events
        if isinstance(event, Mapping) and event.get("gate_id")
    }
    matched = 0
    for gate in expected_gates:
        gate_id = gate.get("id")
        expected_decision = gate.get("expected_decision")
        if gate_id and actual.get(gate_id) == expected_decision:
            matched += 1
    return round(matched / len(expected_gates), 4)


def _trace_completeness(scoring: Mapping[str, Any], run: Mapping[str, Any]) -> float:
    required = _as_string_list(scoring.get("required_trace_events"))
    if not required:
        return 1.0
    events = _event_types(run)
    return round(len(set(required) & events) / len(set(required)), 4)


def _false_completion_caught(scoring: Mapping[str, Any], run: Mapping[str, Any]) -> bool:
    if not bool(scoring.get("false_completion_required", False)):
        return True
    test_results = run.get("test_results", {})
    final_judgment = run.get("final_judgment", {})
    test_status = test_results.get("status") if isinstance(test_results, Mapping) else None
    claimed_complete = (
        bool(final_judgment.get("claimed_complete"))
        if isinstance(final_judgment, Mapping)
        else False
    )
    if test_status != "failed" or not claimed_complete:
        return True
    final_status = (
        str(final_judgment.get("status", "")) if isinstance(final_judgment, Mapping) else ""
    )
    return final_status in {
        "blocked",
        "failed",
        "failed_validation",
    } or "false_completion_detected" in _event_types(run)


def _recovery_evidence_present(scoring: Mapping[str, Any], run: Mapping[str, Any]) -> bool:
    if not bool(scoring.get("recovery_required", False)):
        return True
    recovery_events = run.get("recovery_events", [])
    if not isinstance(recovery_events, list) or not recovery_events:
        return False
    kinds = {
        str(event.get("kind"))
        for event in recovery_events
        if isinstance(event, Mapping) and event.get("kind")
    }
    return bool({"diagnosis", "retest"} <= kinds)


def _writeback_usefulness_present(scoring: Mapping[str, Any], run: Mapping[str, Any]) -> bool:
    if not bool(scoring.get("writeback_required", False)):
        return True
    proposals = run.get("writeback_proposals", [])
    if not isinstance(proposals, list):
        return False
    return any(
        isinstance(proposal, Mapping) and proposal.get("usefulness") == "useful"
        for proposal in proposals
    )


def _dimension_passed(value: float | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value >= 1.0


def _overall_score(dimensions: Mapping[str, float | bool]) -> float:
    values = [
        1.0 if value is True else 0.0 if value is False else float(value)
        for value in dimensions.values()
    ]
    if not values:
        return 1.0
    return round(sum(values) / len(values), 4)


def load_harness_eval_config(path: Path = DEFAULT_CONFIG_PATH) -> HarnessEvalConfig:
    resolved = path.expanduser().resolve()
    loaded = _load_json(resolved)
    fixtures_raw = loaded.get("fixtures", [])
    if not isinstance(fixtures_raw, list):
        raise ValueError("harness eval config fixtures must be a list")
    fixtures: list[HarnessEvalConfigFixture] = []
    for item in fixtures_raw:
        if not isinstance(item, Mapping):
            continue
        fixtures.append(
            HarnessEvalConfigFixture(
                id=str(item.get("id", "")),
                category=str(item.get("category", "")),
                path=_resolve_path(resolved, str(item.get("path", ""))),
            )
        )
    return HarnessEvalConfig(
        version=int(loaded.get("version", 1)),
        eval_name=str(loaded.get("eval_name", "")),
        goal=str(loaded.get("goal", "")),
        fixtures=fixtures,
    )


def load_developer_experience_fixtures(
    path: Path = DEFAULT_DX_FIXTURE_CONFIG_PATH,
) -> DeveloperExperienceEvalConfig:
    resolved = path.expanduser().resolve()
    loaded = _load_json(resolved)
    fixtures_raw = loaded.get("fixtures", [])
    if not isinstance(fixtures_raw, list):
        raise ValueError("developer experience fixtures must be a list")

    criteria = _as_string_list(loaded.get("criteria"))
    fixtures: list[DeveloperExperienceEvalFixture] = []
    for item in fixtures_raw:
        if not isinstance(item, Mapping):
            continue
        second_brain_modes = _as_string_list(item.get("second_brain_modes"))
        if not {"available", "unavailable"} <= set(second_brain_modes):
            raise ValueError("developer experience fixtures must cover both second-brain modes")
        fixture_criteria = _as_string_list(item.get("criteria"))
        if not fixture_criteria:
            raise ValueError("developer experience fixture criteria must not be empty")
        fixtures.append(
            DeveloperExperienceEvalFixture(
                id=str(item.get("id", "")),
                category=str(item.get("category", "")),
                title=str(item.get("title", "")),
                second_brain_modes=second_brain_modes,
                expected_capabilities=_as_string_list(item.get("expected_capabilities")),
                forbidden_capabilities=_as_string_list(item.get("forbidden_capabilities")),
                criteria=fixture_criteria,
            )
        )

    fixture_ids = {fixture.id for fixture in fixtures}
    missing = sorted(REQUIRED_DX_FIXTURE_IDS - fixture_ids)
    if missing:
        raise ValueError(f"missing required developer experience fixtures: {', '.join(missing)}")
    if any(fixture.category != "developer-experience" for fixture in fixtures):
        raise ValueError("developer experience fixtures must use category developer-experience")
    if not criteria:
        raise ValueError("developer experience fixture registry criteria must not be empty")

    spec_path = _resolve_path(resolved, str(loaded.get("spec_path", "")))
    return DeveloperExperienceEvalConfig(
        version=int(loaded.get("version", 1)),
        eval_name=str(loaded.get("eval_name", "")),
        category=str(loaded.get("category", "")),
        spec_path=spec_path,
        criteria=criteria,
        fixtures=fixtures,
    )


def developer_experience_fixture_summary(
    path: Path = DEFAULT_DX_FIXTURE_CONFIG_PATH,
) -> dict[str, Any]:
    config = load_developer_experience_fixtures(path)
    fixture_ids = [fixture.id for fixture in config.fixtures]
    return {
        "eval_name": config.eval_name,
        "category": config.category,
        "spec_path": str(config.spec_path),
        "fixture_count": len(config.fixtures),
        "fixture_ids": fixture_ids,
        "criteria_count": len(config.criteria),
        "required_scenarios_present": set(fixture_ids) >= REQUIRED_DX_FIXTURE_IDS,
    }


def load_harness_fixture(path: Path) -> HarnessEvalFixture:
    resolved = path.expanduser().resolve()
    runs_dir = resolved / "runs"
    runs: dict[str, dict[str, Any]] = {}
    for run_path in sorted(runs_dir.glob("*.json")):
        loaded = _load_json(run_path)
        if isinstance(loaded, dict):
            loaded.setdefault("run_id", run_path.stem)
            loaded.setdefault("_evidence_path", str(run_path))
            runs[run_path.stem] = loaded
    task_markdown = (resolved / "task.md").read_text(encoding="utf-8")
    expected_context_packets = _as_string_list(
        _load_json(resolved / "expected_context_packets.json")
    )
    expected_gates = [
        {str(key): str(value) for key, value in item.items()}
        for item in _load_json(resolved / "expected_gates.json")
        if isinstance(item, Mapping)
    ]
    expected_success_criteria = _as_string_list(
        _load_json(resolved / "expected_success_criteria.json")
    )
    golden_outcome_markdown = (resolved / "golden_outcome.md").read_text(encoding="utf-8")
    scoring = _load_json(resolved / "scoring.json")
    validate_harness_fixture_components(
        task_markdown=task_markdown,
        expected_context_packets=expected_context_packets,
        expected_gates=expected_gates,
        expected_success_criteria=expected_success_criteria,
        golden_outcome_markdown=golden_outcome_markdown,
        scoring=scoring,
        runs=runs,
    )
    return HarnessEvalFixture(
        id=resolved.name,
        path=resolved,
        task_markdown=task_markdown,
        expected_context_packets=expected_context_packets,
        expected_gates=expected_gates,
        expected_success_criteria=expected_success_criteria,
        golden_outcome_markdown=golden_outcome_markdown,
        scoring=scoring,
        runs=runs,
    )


def score_harness_run(fixture: HarnessEvalFixture, run: Mapping[str, Any]) -> HarnessEvalScore:
    selected_context = _as_string_list(run.get("selected_context_packets"))
    context_precision, context_recall = _set_score(
        fixture.expected_context_packets, selected_context
    )
    selected_criteria = _as_string_list(run.get("selected_success_criteria"))
    _criteria_precision, criteria_recall = _set_score(
        fixture.expected_success_criteria,
        selected_criteria,
    )
    harness = run.get("harness", {})
    harness_name = (
        str(harness.get("name", "unknown")) if isinstance(harness, Mapping) else "unknown"
    )
    run_id = (
        str(run.get("run_id") or harness.get("mode", harness_name))
        if isinstance(harness, Mapping)
        else harness_name
    )
    dimensions: dict[str, float | bool] = {
        "context_precision": context_precision,
        "context_recall": context_recall,
        "gate_accuracy": _gate_accuracy(fixture.expected_gates, run),
        "success_criteria_recall": criteria_recall,
        "trace_completeness": _trace_completeness(fixture.scoring, run),
        "false_completion_caught": _false_completion_caught(fixture.scoring, run),
        "recovery_evidence_present": _recovery_evidence_present(fixture.scoring, run),
        "writeback_usefulness_present": _writeback_usefulness_present(fixture.scoring, run),
    }
    failed = [name for name in DIMENSION_NAMES if not _dimension_passed(dimensions[name])]
    evidence_path = str(run.get("_evidence_path") or fixture.path / "runs" / f"{run_id}.json")
    return HarnessEvalScore(
        fixture_id=fixture.id,
        run_id=run_id,
        harness_name=harness_name,
        dimensions=dimensions,
        failed_dimensions=failed,
        overall_score=_overall_score(dimensions),
        evidence_path=evidence_path,
    )


def score_suite(config_path: Path = DEFAULT_CONFIG_PATH) -> HarnessEvalSuiteResult:
    config = load_harness_eval_config(config_path)
    results: list[HarnessEvalScore] = []
    for fixture_ref in config.fixtures:
        fixture = load_harness_fixture(fixture_ref.path)
        for run in fixture.runs.values():
            results.append(score_harness_run(fixture, run))
    failed_run_count = sum(1 for result in results if result.failed_dimensions)
    average_score = (
        round(sum(result.overall_score for result in results) / len(results), 4) if results else 1.0
    )
    totals: dict[str, int | float] = {
        "fixture_count": len(config.fixtures),
        "run_count": len(results),
        "failed_run_count": failed_run_count,
        "average_score": average_score,
    }
    return HarnessEvalSuiteResult(
        eval_name=config.eval_name,
        config_path=str(config_path.expanduser().resolve()),
        totals=totals,
        results=results,
    )


def suite_result_to_dict(result: HarnessEvalSuiteResult) -> dict[str, Any]:
    return {
        "eval_name": result.eval_name,
        "config_path": result.config_path,
        "totals": result.totals,
        "results": [
            {
                "fixture_id": score.fixture_id,
                "run_id": score.run_id,
                "harness_name": score.harness_name,
                "dimensions": score.dimensions,
                "failed_dimensions": score.failed_dimensions,
                "overall_score": score.overall_score,
                "evidence_path": score.evidence_path,
            }
            for score in result.results
        ],
    }
