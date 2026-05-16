from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT_RULES_PATH = ROOT / "config" / "agent-rules.md"

RULE_HEADING_RE = re.compile(r"^##\s+Rule\s+\d+\s+[—-]\s+(.+?)\s*$")


@dataclass(frozen=True)
class AgentRule:
    title: str
    body: str


def load_agent_rules(path: Path | None = None) -> list[AgentRule]:
    rules_path = path or DEFAULT_AGENT_RULES_PATH
    try:
        content = rules_path.read_text(encoding="utf-8")
    except OSError:
        return []

    rules: list[AgentRule] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in content.splitlines():
        heading = RULE_HEADING_RE.match(line)
        if heading:
            if current_title:
                rules.append(AgentRule(title=current_title, body="\n".join(current_body).strip()))
            current_title = heading.group(1).strip()
            current_body = []
            continue
        if current_title:
            current_body.append(line)

    if current_title:
        rules.append(AgentRule(title=current_title, body="\n".join(current_body).strip()))

    return rules


def agent_rules_context(path: Path | None = None, *, max_rules: int | None = None) -> str:
    rules = load_agent_rules(path)
    if max_rules is not None:
        rules = rules[:max_rules]
    if not rules:
        return ""
    lines = ["**AIOS agent rules:**"]
    for rule in rules:
        first_sentence = rule.body.splitlines()[0].strip() if rule.body else ""
        if first_sentence:
            lines.append(f"- {rule.title}: {first_sentence}")
        else:
            lines.append(f"- {rule.title}")
    return "\n".join(lines)
