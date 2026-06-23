from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_auto_allow import (  # noqa: E402
    AUTO_ALLOW_CHANNEL,
    assess_auto_allow_candidate,
    assess_auto_allow_candidates,
    assessments_to_dicts,
)


def test_read_only_local_inspection_is_safe_to_suggest() -> None:
    assessment = assess_auto_allow_candidate("rg META-06 .planning/REQUIREMENTS.md", frequency=4)

    assert assessment.recommendation == "safe_to_suggest"
    assert assessment.read_only
    assert not assessment.filesystem_writes
    assert assessment.risk_score == 0
    assert assessment.channel == AUTO_ALLOW_CHANNEL
    assert assessment.separated_from_learning_proposals


def test_test_and_lint_commands_are_safe_to_suggest() -> None:
    pytest = assess_auto_allow_candidate("uv run pytest -q tests/test_meta_learning_auto_allow.py")
    lint = assess_auto_allow_candidate("pnpm lint")

    assert pytest.recommendation == "safe_to_suggest"
    assert lint.recommendation == "safe_to_suggest"
    assert "test/lint/format quality command" in pytest.reasons


def test_write_git_package_and_network_commands_require_manual_review() -> None:
    write = assess_auto_allow_candidate("python3 scripts/update_state.py")
    git = assess_auto_allow_candidate("git commit -m test")
    package = assess_auto_allow_candidate("pnpm add zod")
    network = assess_auto_allow_candidate("curl -I https://example.com")

    assert write.recommendation == "manual_review_required"
    assert git.recommendation == "manual_review_required"
    assert package.recommendation == "manual_review_required"
    assert network.recommendation == "manual_review_required"
    assert git.filesystem_writes
    assert package.filesystem_writes
    assert network.network_access


def test_shell_expansion_and_dynamic_arguments_require_manual_review() -> None:
    assessment = assess_auto_allow_candidate("grep TODO services/*.py")

    assert assessment.recommendation == "manual_review_required"
    assert "shell expansion or dynamic argument risk" in assessment.reasons


def test_destructive_secret_and_deploy_commands_are_never_auto_allowed() -> None:
    destructive = assess_auto_allow_candidate("rm -rf data/meta-learning")
    secret = assess_auto_allow_candidate("cat ~/.ssh/id_rsa token")
    deploy = assess_auto_allow_candidate("vercel deploy --prod")
    external_write = assess_auto_allow_candidate("curl -X POST https://api.example.com/items")

    assert destructive.recommendation == "never_auto_allow"
    assert secret.recommendation == "never_auto_allow"
    assert deploy.recommendation == "never_auto_allow"
    assert external_write.recommendation == "never_auto_allow"


def test_batch_assessment_reports_frequency_separately_from_learning_proposals() -> None:
    assessments = assess_auto_allow_candidates(["rg foo", "rg foo", "git status"])
    payload = assessments_to_dicts(assessments)
    by_command = {item["command"]: item for item in payload}

    assert by_command["rg foo"]["frequency"] == 2
    assert by_command["rg foo"]["channel"] == AUTO_ALLOW_CHANNEL
    assert by_command["git status"]["recommendation"] == "manual_review_required"
