#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_CLASSIFICATIONS = {
    "debug",
    "plan",
    "refactor",
    "implement",
    "review",
    "explain",
    "other",
}
REQUIRED_FIELDS = (
    "id",
    "name",
    "version",
    "classification",
    "tags",
    "purpose",
    "when_to_use",
    "when_not_to_use",
    "required_inputs",
    "output_contract",
    "eval_criteria",
    "owner",
    "last_updated",
    "changelog",
)


class FrontmatterError(ValueError):
    pass


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar(value: str) -> Any:
    cleaned = value.strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        return cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'") and len(cleaned) >= 2:
        return cleaned[1:-1]
    lowered = cleaned.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if cleaned.startswith("[") and cleaned.endswith("]"):
        inner = cleaned[1:-1].strip()
        if not inner:
            return []
        parts = [part.strip() for part in inner.split(",")]
        return [_parse_scalar(part) for part in parts]
    return cleaned


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise FrontmatterError(f"Expected key/value line, got: {line}")
    key, raw_value = line.split(":", 1)
    key = key.strip()
    if not key:
        raise FrontmatterError(f"Missing key in line: {line}")
    return key, raw_value.lstrip()


def _parse_folded(lines: list[str], index: int, indent: int) -> tuple[str, int]:
    chunks: list[str] = []
    i = index
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        line_indent = _leading_spaces(line)
        if line_indent < indent:
            break
        chunks.append(line.strip())
        i += 1
    return " ".join(chunks).strip(), i


def _parse_mapping(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    i = index
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        line_indent = _leading_spaces(line)
        if line_indent < indent:
            break
        if line_indent > indent:
            raise FrontmatterError(f"Unexpected indentation in mapping: {line}")
        key, raw_value = _split_key_value(stripped)
        if raw_value == ">":
            i += 1
            value, i = _parse_folded(lines, i, indent + 2)
        elif raw_value == "":
            i += 1
            value, i = _parse_block(lines, i, indent + 2)
        else:
            value = _parse_scalar(raw_value)
            i += 1
        data[key] = value
    return data, i


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = index
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        line_indent = _leading_spaces(line)
        if line_indent < indent:
            break
        if line_indent != indent or not stripped.startswith("- "):
            raise FrontmatterError(f"Expected list item at indent {indent}: {line}")
        payload = stripped[2:].strip()
        if payload == "":
            i += 1
            nested, i = _parse_block(lines, i, indent + 2)
            items.append(nested)
            continue
        if ":" in payload:
            key, raw_value = _split_key_value(payload)
            item: dict[str, Any] = {}
            if raw_value == ">":
                i += 1
                folded, i = _parse_folded(lines, i, indent + 2)
                item[key] = folded
            elif raw_value == "":
                i += 1
                nested, i = _parse_block(lines, i, indent + 2)
                item[key] = nested
            else:
                item[key] = _parse_scalar(raw_value)
                i += 1

            while i < len(lines):
                extra_line = lines[i]
                if not extra_line.strip():
                    i += 1
                    continue
                extra_indent = _leading_spaces(extra_line)
                if extra_indent < indent + 2:
                    break
                if extra_indent == indent and extra_line.strip().startswith("- "):
                    break
                if extra_indent != indent + 2:
                    raise FrontmatterError(f"Unexpected indentation in list mapping: {extra_line}")
                sub_key, sub_raw = _split_key_value(extra_line.strip())
                if sub_raw == ">":
                    i += 1
                    sub_value, i = _parse_folded(lines, i, indent + 4)
                elif sub_raw == "":
                    i += 1
                    sub_value, i = _parse_block(lines, i, indent + 4)
                else:
                    sub_value = _parse_scalar(sub_raw)
                    i += 1
                item[sub_key] = sub_value
            items.append(item)
            continue

        items.append(_parse_scalar(payload))
        i += 1
    return items, i


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    i = index
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return {}, i
    line = lines[i]
    line_indent = _leading_spaces(line)
    if line_indent < indent:
        return {}, i
    if line_indent != indent:
        raise FrontmatterError(f"Unexpected indentation at block start: {line}")
    if line.strip().startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_mapping(lines, i, indent)


def parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        raise FrontmatterError("Missing starting frontmatter delimiter")
    lines = markdown.splitlines()
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        raise FrontmatterError("Missing closing frontmatter delimiter")
    frontmatter_lines = lines[1:end_index]
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    if not frontmatter_lines:
        raise FrontmatterError("Frontmatter section is empty")
    frontmatter, consumed = _parse_mapping(frontmatter_lines, 0, 0)
    if consumed < len(frontmatter_lines):
        trailing = frontmatter_lines[consumed:]
        if any(line.strip() for line in trailing):
            raise FrontmatterError("Unexpected trailing frontmatter content")
    return frontmatter, body


def _is_non_empty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return value is not None


def _normalize_templates(prompts_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    templates: list[dict[str, Any]] = []
    for path in sorted(prompts_root.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            frontmatter, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            templates.append({"path": path, "frontmatter": frontmatter, "body": body})
        except (FrontmatterError, OSError) as exc:
            errors.append(f"{path}: {exc}")
    return templates, errors


def validate_templates(prompts_root: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    templates, errors = _normalize_templates(prompts_root)
    warnings: list[str] = []

    ids_seen: dict[str, Path] = {}
    registry_rows: list[dict[str, Any]] = []
    for template in templates:
        path = template["path"]
        fm = template["frontmatter"]
        template_errors: list[str] = []

        for field in REQUIRED_FIELDS:
            if field not in fm or not _is_non_empty(fm[field]):
                template_errors.append(f"missing required field '{field}'")

            template_id = str(fm.get("id", "")).strip()
        if template_id:
            first_path = ids_seen.get(template_id)
            if first_path and first_path != path:
                template_errors.append(f"duplicate id '{template_id}' also used by {first_path.name}")
            ids_seen[template_id] = path

            if path.stem != template_id:
                template_errors.append(
                    f"id '{template_id}' does not match filename '{path.stem}'"
                )

            eval_case_path = prompts_root / "evals" / template_id / "cases.md"
            if not eval_case_path.exists():
                warnings.append(f"{path}: missing eval file {eval_case_path}")

        classification = str(fm.get("classification", "")).strip()
        if classification and classification not in VALID_CLASSIFICATIONS:
            template_errors.append(f"invalid classification '{classification}'")

        required_inputs = fm.get("required_inputs", [])
        if not isinstance(required_inputs, list) or len(required_inputs) == 0:
            template_errors.append("'required_inputs' must be a non-empty list")

        eval_criteria = fm.get("eval_criteria", [])
        if not isinstance(eval_criteria, list) or len(eval_criteria) == 0:
            template_errors.append("'eval_criteria' must be a non-empty list")

        changelog = fm.get("changelog", [])
        if not isinstance(changelog, list) or len(changelog) == 0:
            template_errors.append("'changelog' must be a non-empty list")

        if template_errors:
            errors.extend([f"{path}: {error}" for error in template_errors])
            continue

        row = {
            "id": template_id,
            "name": fm["name"],
            "version": fm["version"],
            "classification": classification,
            "tags": fm.get("tags", []),
            "purpose": fm["purpose"],
            "required_inputs": required_inputs,
            "optional_inputs": fm.get("optional_inputs", []),
            "last_updated": fm["last_updated"],
            "file": f"prompts/{path.name}",
        }
        registry_rows.append(row)

    registry_rows.sort(key=lambda item: str(item["id"]))
    return registry_rows, errors, warnings


def write_registry(prompts_root: Path, rows: list[dict[str, Any]]) -> Path:
    registry_path = prompts_root / "registry.json"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "templates": rows,
    }
    registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return registry_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AIOS prompt templates and generate registry.json")
    parser.add_argument(
        "--prompts-root",
        default=str((Path.home() / "AIOS" / "prompts").resolve()),
        help="Path to prompts root (default: ~/AIOS/prompts)",
    )
    args = parser.parse_args(argv)
    prompts_root = Path(args.prompts_root).expanduser().resolve()

    if not prompts_root.exists():
        print(f"prompts root not found: {prompts_root}")
        return 1

    rows, errors, warnings = validate_templates(prompts_root)
    for warning in warnings:
        print(f"warning: {warning}")

    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1

    registry_path = write_registry(prompts_root, rows)
    print(f"validated {len(rows)} template(s)")
    print(f"wrote {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
