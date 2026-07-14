"""Deterministic source normalization for the ``capture.v1`` envelope."""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser

type JsonObject = dict[str, object]

SUPPORTED_FORMATS = {"URL", "HTML", "Markdown", "JSON", "CSV"}
VALIDATION_STATUSES = {"valid", "partial", "invalid"}
ENRICHMENT_STATUSES = {"not_requested", "pending", "complete", "failed"}


class CaptureInputError(ValueError):
    """Raised when a source adapter input cannot be normalized."""


@dataclass(frozen=True)
class _HtmlExtraction:
    markdown: str
    removals: list[JsonObject]


class _DeterministicHtmlParser(HTMLParser):
    _BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._lines: list[str] = []
        self._active_tag: str | None = None
        self._active_buffer: list[str] = []
        self._active_attrs: dict[str, str] = {}
        self._pre_buffer: list[str] = []
        self._pre_language = ""
        self._pre_depth = 0
        self._skip_depth = 0
        self._removal_counts: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_depth:
            self._skip_depth += 1
            return

        attributes = {key: value or "" for key, value in attrs}
        selector = self._removal_selector(tag, attributes)
        if selector is not None:
            self._removal_counts[selector] += 1
            self._skip_depth = 1
            return

        if tag == "pre":
            self._flush_block()
            self._pre_buffer = []
            self._pre_language = self._language(attributes.get("class", ""))
            self._pre_depth = 1
            return

        if self._pre_depth:
            return

        if tag in self._BLOCK_TAGS:
            self._flush_block()
            self._active_tag = tag
            self._active_buffer = []
            self._active_attrs = attributes
        elif tag == "br" and self._active_tag:
            self._active_buffer.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return

        if self._pre_depth:
            if tag == "pre":
                self._flush_pre()
                self._pre_depth = 0
            return

        if self._active_tag == tag:
            self._flush_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._pre_depth:
            self._pre_buffer.append(data)
        elif self._active_tag:
            self._active_buffer.append(data)

    def finish(self) -> _HtmlExtraction:
        self._flush_pre()
        self._flush_block()
        removals = [
            {
                "stage": "html-filter",
                "selector": selector,
                "count": count,
                "reason": "non-content",
            }
            for selector, count in sorted(self._removal_counts.items())
        ]
        return _HtmlExtraction("\n\n".join(self._lines).strip(), removals)

    def _flush_block(self) -> None:
        if self._active_tag is None:
            return
        text = _collapse_whitespace(unescape("".join(self._active_buffer)))
        tag = self._active_tag
        attributes = self._active_attrs
        self._active_tag = None
        self._active_buffer = []
        self._active_attrs = {}
        if not text:
            return

        if tag.startswith("h"):
            self._lines.append(f"{'#' * int(tag[1])} {text}")
        elif tag == "li":
            self._lines.append(f"- {text}")
        elif tag == "blockquote" and attributes.get("data-callout"):
            callout = attributes["data-callout"].strip().upper() or "NOTE"
            self._lines.append(f"> [!{callout}]\n> {text}")
        elif tag == "blockquote":
            self._lines.append(f"> {text}")
        else:
            self._lines.append(text)

    def _flush_pre(self) -> None:
        if not self._pre_buffer:
            return
        code = "".join(self._pre_buffer).strip("\n")
        self._pre_buffer = []
        if not code:
            return
        fence = f"```{self._pre_language}\n{code}\n```"
        self._lines.append(fence)

    @staticmethod
    def _language(class_value: str) -> str:
        match = re.search(r"(?:^|\s)language-([\w+-]+)", class_value)
        return match.group(1) if match else ""

    @staticmethod
    def _removal_selector(tag: str, attributes: Mapping[str, str]) -> str | None:
        if tag in {"script", "style", "noscript"}:
            return tag
        classes = set(attributes.get("class", "").lower().split())
        for marker in ("ad", "advert", "hidden"):
            if marker in classes:
                return f".{marker}"
        return None


def build_capture(
    payload: Mapping[str, object],
    *,
    captured_at: str | None = None,
    profile: str | None = None,
) -> JsonObject:
    """Normalize one adapter payload into a validated ``capture.v1`` envelope."""

    source_input = _mapping(payload.get("source"), "source")
    provider = _string(source_input.get("provider"), "source.provider")
    input_format = _string(source_input.get("input_format"), "source.input_format")
    if input_format not in SUPPORTED_FORMATS:
        raise CaptureInputError(
            f"source.input_format must be one of {sorted(SUPPORTED_FORMATS)}, got {input_format!r}"
        )
    source_uri = _string_or_none(source_input.get("source_uri"), "source.source_uri")
    raw_content = _string(source_input.get("content"), "source.content")

    metadata = dict(_mapping(payload.get("metadata", {}), "metadata"))
    adapter = _adapter_payload(payload.get("adapter"))
    provenance = _provenance_payload(payload.get("provenance", {}), profile=profile)
    normalized_markdown, normalized_html, generated_removals = _normalize_content(
        input_format,
        raw_content,
        metadata,
    )
    removals = [dict(item) for item in _object_list(provenance["removals"], "provenance.removals")]
    removals.extend(generated_removals)
    provenance["removals"] = removals

    envelope: JsonObject = {
        "schema_version": "capture.v1",
        "captured_at": captured_at or _now_iso(),
        "source": {
            "provider": provider,
            "input_format": input_format,
            "source_uri": source_uri,
            "content_hash": f"sha256:{sha256(raw_content.encode('utf-8')).hexdigest()}",
        },
        "metadata": metadata,
        "content": {
            "html": normalized_html,
            "markdown": normalized_markdown,
            "word_count": _word_count(normalized_markdown),
            "structure": _structure_counts(normalized_markdown),
        },
        "adapter": adapter,
        "provenance": provenance,
        "validation": {"status": "valid", "warnings": []},
        "enrichment": {"status": "not_requested", "outputs": []},
    }
    errors = validate_capture_envelope(envelope)
    if errors:
        envelope["validation"] = {"status": "invalid", "warnings": errors}
    return envelope


def validate_capture_envelope(envelope: Mapping[str, object]) -> list[str]:
    """Return deterministic contract violations without mutating the envelope."""

    errors: list[str] = []
    for key in (
        "schema_version",
        "captured_at",
        "source",
        "metadata",
        "content",
        "adapter",
        "provenance",
        "validation",
        "enrichment",
    ):
        if key not in envelope:
            errors.append(f"missing {key}")

    if envelope.get("schema_version") != "capture.v1":
        errors.append("schema_version must be capture.v1")
    captured_at = envelope.get("captured_at")
    if isinstance(captured_at, str):
        try:
            parsed = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("captured_at must include a timezone")
        except ValueError:
            errors.append("captured_at must be an ISO date-time")
    else:
        errors.append("captured_at must be a string")

    source = _validation_mapping(envelope.get("source"), "source", errors)
    if source is not None:
        _validation_string(source, "provider", "source.provider", errors)
        input_format = _validation_string(source, "input_format", "source.input_format", errors)
        if input_format is not None and input_format not in SUPPORTED_FORMATS:
            errors.append("source.input_format is unsupported")
        _validation_string_or_none(source, "source_uri", "source.source_uri", errors)
        _validation_string(source, "content_hash", "source.content_hash", errors)

    if not isinstance(envelope.get("metadata"), Mapping):
        errors.append("metadata must be an object")

    content = _validation_mapping(envelope.get("content"), "content", errors)
    if content is not None:
        _validation_string_or_none(content, "html", "content.html", errors)
        _validation_string(content, "markdown", "content.markdown", errors)
        _validation_nonnegative_int(content, "word_count", "content.word_count", errors)
        structure = _validation_mapping(content.get("structure"), "content.structure", errors)
        if structure is not None:
            for key in ("headings", "code_blocks", "footnotes", "math", "callouts"):
                _validation_nonnegative_int(structure, key, f"content.structure.{key}", errors)

    adapter = _validation_mapping(envelope.get("adapter"), "adapter", errors)
    if adapter is not None:
        for key in ("name", "version", "trigger"):
            _validation_string(adapter, key, f"adapter.{key}", errors)
        _validation_field_sources(adapter.get("field_sources"), errors)

    provenance = _validation_mapping(envelope.get("provenance"), "provenance", errors)
    if provenance is not None:
        _validation_string(provenance, "extractor", "provenance.extractor", errors)
        _validation_string_or_none(
            provenance,
            "content_selector",
            "provenance.content_selector",
            errors,
        )
        if not isinstance(provenance.get("options"), Mapping):
            errors.append("provenance.options must be an object")
        _validation_nonnegative_int(provenance, "retries", "provenance.retries", errors)
        _validation_string(provenance, "profile", "provenance.profile", errors)
        _validation_removals(provenance.get("removals"), errors)

    validation = _validation_mapping(envelope.get("validation"), "validation", errors)
    if validation is not None:
        status = _validation_string(validation, "status", "validation.status", errors)
        if status is not None and status not in VALIDATION_STATUSES:
            errors.append("validation.status is unsupported")
        _validation_string_list(validation.get("warnings"), "validation.warnings", errors)

    enrichment = _validation_mapping(envelope.get("enrichment"), "enrichment", errors)
    if enrichment is not None:
        status = _validation_string(enrichment, "status", "enrichment.status", errors)
        if status is not None and status not in ENRICHMENT_STATUSES:
            errors.append("enrichment.status is unsupported")
        _validation_string_list(enrichment.get("outputs"), "enrichment.outputs", errors)
    return errors


def _normalize_content(
    input_format: str,
    raw_content: str,
    metadata: Mapping[str, object],
) -> tuple[str, str | None, list[JsonObject]]:
    if input_format in {"HTML", "URL"} and raw_content.lstrip().startswith("<"):
        parser = _DeterministicHtmlParser()
        parser.feed(raw_content)
        extracted = parser.finish()
        return (
            extracted.markdown,
            raw_content if input_format == "HTML" else None,
            extracted.removals,
        )
    if input_format == "JSON":
        try:
            value = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise CaptureInputError(f"source.content is not valid JSON: {exc.msg}") from exc
        return _json_to_markdown(value, _metadata_title(metadata)), None, []
    if input_format == "CSV":
        return _csv_to_markdown(raw_content), None, []
    return raw_content.strip(), None, []


def _json_to_markdown(value: object, title: str) -> str:
    lines = [f"# {title}"] if title else []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)) or item is None:
                lines.append(f"**{key}:** {_scalar_text(item)}")
            elif isinstance(item, list):
                lines.append(f"## {key}")
                for entry in item:
                    if isinstance(entry, Mapping) and isinstance(entry.get("text"), str):
                        lines.append(f"- {entry['text']}")
                    else:
                        lines.append(f"- {_scalar_text(entry)}")
            else:
                lines.extend(
                    [f"## {key}", "```json", json.dumps(item, indent=2, sort_keys=True), "```"]
                )
    else:
        lines.append(_scalar_text(value))
    return "\n\n".join(line for line in lines if line).strip()


def _csv_to_markdown(raw_content: str) -> str:
    reader = csv.DictReader(io.StringIO(raw_content))
    headers = list(reader.fieldnames or [])
    if not headers:
        raise CaptureInputError("source.content CSV must include a header row")
    rows = [dict(row) for row in reader]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header) or "") for header in headers) + " |")
    return "\n".join(lines)


def _structure_counts(markdown: str) -> JsonObject:
    without_code = re.sub(r"(?ms)^```.*?^```\s*", "", markdown)
    footnote_definitions = set(re.findall(r"^\[\^([^\]]+)\]:", markdown, re.MULTILINE))
    footnote_references = set(re.findall(r"\[\^([^\]]+)\]", markdown))
    math_matches = re.findall(
        r"\$\$.*?\$\$|\$(?:\\.|[^$\n])+\$|\\\([^)]*\\\)|\\\[[\s\S]*?\\\]",
        without_code,
        re.DOTALL,
    )
    return {
        "headings": len(re.findall(r"^\s{0,3}#{1,6}\s+\S", markdown, re.MULTILINE)),
        "code_blocks": len(re.findall(r"^```", markdown, re.MULTILINE)) // 2,
        "footnotes": len(footnote_definitions or footnote_references),
        "math": len(math_matches),
        "callouts": len(re.findall(r"^>\s*\[!", markdown, re.MULTILINE | re.IGNORECASE)),
    }


def _adapter_payload(value: object) -> JsonObject:
    source = _mapping(value, "adapter")
    field_sources_value = source.get("field_sources", [])
    if not isinstance(field_sources_value, list):
        raise CaptureInputError("adapter.field_sources must be an array")
    field_sources: list[JsonObject] = []
    for index, item in enumerate(field_sources_value):
        field_source = _mapping(item, f"adapter.field_sources[{index}]")
        field_sources.append(
            {
                "canonical_field": _string(
                    field_source.get("canonical_field"),
                    f"adapter.field_sources[{index}].canonical_field",
                ),
                "source_expression": _string(
                    field_source.get("source_expression"),
                    f"adapter.field_sources[{index}].source_expression",
                ),
            }
        )
    return {
        "name": _string(source.get("name"), "adapter.name"),
        "version": _string(source.get("version"), "adapter.version"),
        "trigger": _string(source.get("trigger"), "adapter.trigger"),
        "field_sources": field_sources,
    }


def _provenance_payload(value: object, *, profile: str | None) -> JsonObject:
    source = _mapping(value, "provenance")
    removals_value = source.get("removals", [])
    if not isinstance(removals_value, list):
        raise CaptureInputError("provenance.removals must be an array")
    removals = [
        dict(_mapping(item, f"provenance.removals[{index}]"))
        for index, item in enumerate(removals_value)
    ]
    return {
        "extractor": _string(source.get("extractor") or "aios.capture_v1", "provenance.extractor"),
        "content_selector": _string_or_none(
            source.get("content_selector"),
            "provenance.content_selector",
        ),
        "options": dict(_mapping(source.get("options", {}), "provenance.options")),
        "retries": _nonnegative_int(source.get("retries", 0), "provenance.retries"),
        "profile": profile or _string(source.get("profile") or "default", "provenance.profile"),
        "removals": removals,
    }


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CaptureInputError(f"{label} must be an object")
    return value


def _object_list(value: object, label: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise CaptureInputError(f"{label} must be an array of objects")
    return [item for item in value if isinstance(item, Mapping)]


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaptureInputError(f"{label} must be a non-empty string")
    return value


def _string_or_none(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CaptureInputError(f"{label} must be a string or null")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CaptureInputError(f"{label} must be a non-negative integer")
    return value


def _metadata_title(metadata: Mapping[str, object]) -> str:
    title = metadata.get("title")
    return title.strip() if isinstance(title, str) else "Captured JSON"


def _scalar_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, sort_keys=True)


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _word_count(markdown: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", markdown))


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validation_mapping(
    value: object,
    label: str,
    errors: list[str],
) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        errors.append(f"{label} must be an object")
        return None
    return value


def _validation_string(
    mapping: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty string")
        return None
    return value


def _validation_string_or_none(
    mapping: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> None:
    value = mapping.get(key)
    if value is not None and not isinstance(value, str):
        errors.append(f"{label} must be a string or null")


def _validation_nonnegative_int(
    mapping: Mapping[str, object],
    key: str,
    label: str,
    errors: list[str],
) -> None:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"{label} must be a non-negative integer")


def _validation_string_list(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label} must be an array of strings")


def _validation_field_sources(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("adapter.field_sources must be an array")
        return
    for index, item in enumerate(value):
        field_source = _validation_mapping(item, f"adapter.field_sources[{index}]", errors)
        if field_source is not None:
            _validation_string(
                field_source,
                "canonical_field",
                f"adapter.field_sources[{index}].canonical_field",
                errors,
            )
            _validation_string(
                field_source,
                "source_expression",
                f"adapter.field_sources[{index}].source_expression",
                errors,
            )


def _validation_removals(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("provenance.removals must be an array")
        return
    for index, item in enumerate(value):
        removal = _validation_mapping(item, f"provenance.removals[{index}]", errors)
        if removal is not None:
            _validation_string(removal, "stage", f"provenance.removals[{index}].stage", errors)
            _validation_string_or_none(
                removal,
                "selector",
                f"provenance.removals[{index}].selector",
                errors,
            )
            _validation_nonnegative_int(
                removal,
                "count",
                f"provenance.removals[{index}].count",
                errors,
            )
            _validation_string(removal, "reason", f"provenance.removals[{index}].reason", errors)
