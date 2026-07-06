from __future__ import annotations

import shlex
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

Recommendation = Literal["safe_to_suggest", "manual_review_required", "never_auto_allow"]
AUTO_ALLOW_CHANNEL = "meta_learning_auto_allow_recommendations"

READ_ONLY_COMMANDS = {
    "cat",
    "date",
    "find",
    "grep",
    "head",
    "ls",
    "pwd",
    "rg",
    "sed",
    "tail",
    "tree",
    "wc",
}
TEST_OR_QUALITY_TOKENS = {
    "test",
    "tests",
    "pytest",
    "vitest",
    "lint",
    "ruff",
    "typecheck",
    "format",
    "check",
}
WRITE_COMMANDS = {
    "apply_patch",
    "chmod",
    "cp",
    "mkdir",
    "mv",
    "python",
    "python3",
    "rsync",
    "tee",
    "touch",
}
PACKAGE_COMMANDS = {"npm", "pnpm", "yarn", "uv", "pip", "brew"}
NETWORK_COMMANDS = {"curl", "gh", "ssh", "scp", "vercel", "wget"}
GIT_COMMANDS = {"git"}
DESTRUCTIVE_COMMANDS = {"rm", "rmdir", "unlink", "shred"}
SHELL_EXPANSION_TOKENS = ("*", "?", "$(", "`", ">", ">>", "<", "|", "&&", "||", ";")
SECRET_TOKENS = ("secret", "credential", "token", "password", "keychain", "env")
DEPLOY_TOKENS = ("deploy", "publish", "release", "prod", "production")


@dataclass(frozen=True)
class AutoAllowAssessment:
    command: str
    frequency: int
    recommendation: Recommendation
    risk_score: int
    read_only: bool
    write_capable: bool
    filesystem_writes: bool
    network_access: bool
    credential_exposure_risk: bool
    destructive_potential: bool
    reversible: bool
    repo_sensitive: bool
    sandboxable: bool
    dry_run_support: bool
    reasons: list[str]
    channel: str = AUTO_ALLOW_CHANNEL

    @property
    def separated_from_learning_proposals(self) -> bool:
        return self.channel == AUTO_ALLOW_CHANNEL

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["separated_from_learning_proposals"] = self.separated_from_learning_proposals
        return data


def assess_auto_allow_candidate(
    command: str,
    *,
    frequency: int = 1,
    repo_sensitive: bool = True,
    dry_run_support: bool | None = None,
) -> AutoAllowAssessment:
    tokens = _tokens(command)
    primary = tokens[0] if tokens else ""
    text = command.lower()
    flags = _flags(command, tokens, repo_sensitive=repo_sensitive, dry_run_support=dry_run_support)
    reasons = _reasons(primary, text, flags, frequency)
    risk_score = _risk_score(flags, frequency)
    recommendation = _recommendation(primary, text, flags)
    return AutoAllowAssessment(
        command=command,
        frequency=frequency,
        recommendation=recommendation,
        risk_score=risk_score,
        read_only=flags["read_only"],
        write_capable=flags["write_capable"],
        filesystem_writes=flags["filesystem_writes"],
        network_access=flags["network_access"],
        credential_exposure_risk=flags["credential_exposure_risk"],
        destructive_potential=flags["destructive_potential"],
        reversible=flags["reversible"],
        repo_sensitive=repo_sensitive,
        sandboxable=flags["sandboxable"],
        dry_run_support=flags["dry_run_support"],
        reasons=reasons,
    )


def assess_auto_allow_candidates(
    commands: Iterable[str],
    *,
    repo_sensitive: bool = True,
) -> list[AutoAllowAssessment]:
    frequencies: dict[str, int] = {}
    for command in commands:
        frequencies[command] = frequencies.get(command, 0) + 1
    return [
        assess_auto_allow_candidate(
            command,
            frequency=frequency,
            repo_sensitive=repo_sensitive,
        )
        for command, frequency in sorted(frequencies.items())
    ]


def assessments_to_dicts(assessments: Iterable[AutoAllowAssessment]) -> list[dict[str, Any]]:
    return [assessment.to_dict() for assessment in assessments]


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _flags(
    command: str,
    tokens: list[str],
    *,
    repo_sensitive: bool,
    dry_run_support: bool | None,
) -> dict[str, bool]:
    primary = tokens[0] if tokens else ""
    lowered_tokens = [token.lower() for token in tokens]
    text = command.lower()
    shell_expansion = any(token in command for token in SHELL_EXPANSION_TOKENS)
    destructive = primary in DESTRUCTIVE_COMMANDS or any(
        token in text for token in ("delete", "destroy")
    )
    credential = any(token in text for token in SECRET_TOKENS)
    deploy = any(token in text for token in DEPLOY_TOKENS)
    package_install = primary in PACKAGE_COMMANDS and any(
        token in lowered_tokens for token in ("add", "install", "sync", "lock", "rebuild")
    )
    network = (
        primary in NETWORK_COMMANDS
        or text.startswith("open ")
        or "http://" in text
        or "https://" in text
    )
    git_operation = primary in GIT_COMMANDS
    filesystem_writes = (
        primary in WRITE_COMMANDS
        or package_install
        or git_operation
        or destructive
        or any(token in lowered_tokens for token in ("--write", "--fix", "--apply"))
    )
    test_or_quality = _is_test_or_quality(lowered_tokens)
    read_only = primary in READ_ONLY_COMMANDS and not shell_expansion
    write_capable = filesystem_writes or network or shell_expansion
    reversible = test_or_quality or (not filesystem_writes and not destructive and not network)
    sandboxable = not credential and not deploy and not destructive and not network
    return {
        "read_only": read_only,
        "write_capable": write_capable,
        "filesystem_writes": filesystem_writes,
        "network_access": network,
        "credential_exposure_risk": credential,
        "destructive_potential": destructive or deploy,
        "reversible": reversible,
        "repo_sensitive": repo_sensitive,
        "sandboxable": sandboxable,
        "dry_run_support": bool(dry_run_support)
        if dry_run_support is not None
        else "--dry-run" in lowered_tokens,
        "test_or_quality": test_or_quality,
        "shell_expansion": shell_expansion,
        "package_install": package_install,
        "git_operation": git_operation,
        "deploy": deploy,
    }


def _recommendation(primary: str, text: str, flags: dict[str, bool]) -> Recommendation:
    if (
        flags["destructive_potential"]
        or flags["credential_exposure_risk"]
        or flags["deploy"]
        or (flags["network_access"] and _external_write(text))
    ):
        return "never_auto_allow"
    if (
        flags["filesystem_writes"]
        or flags["network_access"]
        or flags["git_operation"]
        or flags["package_install"]
        or flags["shell_expansion"]
    ):
        return "manual_review_required"
    if flags["read_only"] or flags["test_or_quality"] or primary in {"make"}:
        return "safe_to_suggest"
    return "manual_review_required"


def _risk_score(flags: dict[str, bool], frequency: int) -> int:
    score = 0
    if flags["read_only"] or flags["test_or_quality"]:
        score -= 2
    if frequency >= 3:
        score -= 1
    if flags["filesystem_writes"]:
        score += 3
    if flags["network_access"]:
        score += 3
    if flags["git_operation"]:
        score += 2
    if flags["package_install"]:
        score += 3
    if flags["shell_expansion"]:
        score += 3
    if flags["credential_exposure_risk"]:
        score += 5
    if flags["destructive_potential"]:
        score += 6
    if not flags["reversible"]:
        score += 2
    if not flags["sandboxable"]:
        score += 2
    return max(0, score)


def _reasons(primary: str, text: str, flags: dict[str, bool], frequency: int) -> list[str]:
    reasons: list[str] = [f"frequency={frequency}"]
    if flags["read_only"]:
        reasons.append("read-only local inspection")
    if flags["test_or_quality"]:
        reasons.append("test/lint/format quality command")
    if flags["filesystem_writes"]:
        reasons.append("filesystem write capability")
    if flags["network_access"]:
        reasons.append("network access")
    if flags["git_operation"]:
        reasons.append("git operation requires review")
    if flags["package_install"]:
        reasons.append("package or lockfile mutation risk")
    if flags["credential_exposure_risk"]:
        reasons.append("credential exposure risk")
    if flags["destructive_potential"]:
        reasons.append("destructive/deploy/release potential")
    if flags["shell_expansion"]:
        reasons.append("shell expansion or dynamic argument risk")
    if _external_write(text):
        reasons.append("external network write")
    if primary == "make":
        reasons.append("make target requires target-specific review unless known safe")
    return reasons


def _is_test_or_quality(tokens: list[str]) -> bool:
    return any(token in TEST_OR_QUALITY_TOKENS for token in tokens) and not any(
        token in {"add", "install", "deploy", "publish", "release"} for token in tokens
    )


def _external_write(text: str) -> bool:
    return any(token in text for token in ("-x post", "-x put", "-x patch", " deploy", " publish"))
