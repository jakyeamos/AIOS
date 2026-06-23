#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION_ORDER: tuple[str, ...] = (
    "# Relevant Memory Briefing",
    "## Current Truth",
    "## Relevant Prior Decisions",
    "## Constraints",
    "## Causal / Dependency Chain",
    "## Contradictions or Stale Information",
    "## Open Questions",
    "## Sources / Provenance",
)

RAW_JSON_PATTERN = re.compile(r"(^|\s)[{\[]\s*\"?[A-Za-z0-9_ -]+\"?\s*:", re.MULTILINE)
VALIDITY_STATUSES: tuple[str, ...] = ("superseded", "contradicted")


def validate_packet(markdown: str, *, max_tokens: int = 4096) -> list[str]:
    violations: list[str] = []
    violations.extend(check_section_order(markdown))
    violations.extend(check_provenance_present(markdown))
    violations.extend(check_no_raw_json(markdown))
    violations.extend(check_validity_markers(markdown))
    violations.extend(check_token_count(markdown, max_tokens=max_tokens))
    return violations


def check_section_order(markdown: str) -> list[str]:
    headings = [line.strip() for line in markdown.splitlines() if line.startswith("#")]
    if not headings or headings[0] != "# Relevant Memory Briefing":
        return ["packet must start with '# Relevant Memory Briefing'"]

    known_headings = [heading for heading in headings if heading in SECTION_ORDER]
    positions = [SECTION_ORDER.index(heading) for heading in known_headings]
    if positions != sorted(positions):
        return ["packet sections are not in the required contract order"]
    return []


def check_provenance_present(markdown: str) -> list[str]:
    body = _section_body(markdown, "## Sources / Provenance")
    if body is None:
        return ["Sources / Provenance section is missing"]
    if not any(line.strip().startswith("- ") for line in body.splitlines()):
        return ["Sources / Provenance section must contain at least one source row"]
    return []


def check_no_raw_json(markdown: str) -> list[str]:
    if RAW_JSON_PATTERN.search(markdown):
        return ["packet appears to contain raw JSON or graph rows"]
    return []


def check_validity_markers(markdown: str) -> list[str]:
    violations: list[str] = []
    for line in markdown.splitlines():
        lowered = line.lower()
        for status in VALIDITY_STATUSES:
            if status not in lowered:
                continue
            if f"{status}:" not in lowered and f"({status})" not in lowered:
                violations.append(
                    f"{status} fact must include an explicit validity marker: {line.strip()}"
                )
    return violations


def check_token_count(markdown: str, *, max_tokens: int = 4096) -> list[str]:
    token_count = _estimated_tokens(markdown)
    if token_count > max_tokens:
        return [f"packet token estimate {token_count} exceeds max {max_tokens}"]
    return []


def _section_body(markdown: str, heading: str) -> str | None:
    lines = markdown.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return None
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _estimated_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an AIOS memory packet Markdown file.")
    parser.add_argument("packet_markdown_file", type=Path)
    parser.add_argument("--max-tokens", type=int, default=4096)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv or sys.argv[1:]))
    markdown = args.packet_markdown_file.read_text(encoding="utf-8")
    violations = validate_packet(markdown, max_tokens=args.max_tokens)
    if violations:
        print("Memory packet validation failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Memory packet validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
