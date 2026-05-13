from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD_ID = "experimentation.divergent_strategy_standard"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_divergent_strategy_standard_is_registered() -> None:
    registry = _load_json(ROOT / "config" / "standards" / "registry.json")

    standard = next(item for item in registry["standards"] if item["id"] == STANDARD_ID)

    assert "experimentation" in registry["profile"]["domains"]
    assert standard["expected_state"]["candidate_portfolio"] is True
    assert standard["expected_state"]["judge_rationale"] is True
    assert standard["expected_state"]["entropy_observation"] is True
    assert standard["expected_state"]["approval_gated_writebacks"] is True
    assert standard["expected_state"]["promotion_requires_evidence"] is True


def test_quality_pipeline_exposes_divergent_strategy_gate_for_aios() -> None:
    config = _load_json(ROOT / "config" / "quality-pipeline.json")
    gates = {gate["key"]: gate for gate in config["standard"]["gates"]}
    aios = next(project for project in config["projects"] if project["project_id"] == "aios")

    assert gates["divergent_strategy_standard"]["applicability"] == ["aios_experiment_surface"]
    assert "aios_experiment_surface" in aios["applies_to"]
    assert "divergent_strategy_standard" in aios["gates"]


def test_quality_pipeline_exposes_pre_pr_readiness_gate_for_aios() -> None:
    config = _load_json(ROOT / "config" / "quality-pipeline.json")
    gates = {gate["key"]: gate for gate in config["standard"]["gates"]}
    aios = next(project for project in config["projects"] if project["project_id"] == "aios")

    assert gates["pre_pr_readiness"]["applicability"] == ["aios_experiment_surface"]
    assert "pre_pr_readiness" in aios["gates"]


def test_corpus_and_experiment_repos_include_divergent_strategy_standard() -> None:
    corpus = _load_json(ROOT / "docs" / "aios" / "corpus" / "config.json")
    test_repos = _load_json(ROOT / "config" / "experiments" / "test-repos.json")

    command = next(
        item for item in corpus["commands"] if item["name"] == "divergent-strategy-standard-smoke"
    )

    assert command["suite"] == "divergent-strategy"
    assert any("divergent_runs" in row["sql"] for row in command["assertions"]["dbRows"])
    assert all(
        "divergent-strategy-standard" in repo["experiment_uses"]
        for repo in test_repos["test_repos"]
    )
