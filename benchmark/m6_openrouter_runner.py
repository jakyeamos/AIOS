#!/usr/bin/env python3
"""Run a separately scoped OpenRouter completion and freeze its telemetry.

This runner is intentionally not a Codex harness. It records an OpenRouter
API completion as evidence for a separate benchmark lane and never writes the
existing M6 SQLite ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPENROUTER_API = "https://openrouter.ai/api/v1"
RECEIPT_SCHEMA = "aios-m6-openrouter-receipt-v1"
CONDITIONS = {"baseline_repo_only", "aios_portable_context_packet"}


@dataclass(frozen=True)
class OpenRouterConfig:
    model: str
    provider_only: tuple[str, ...] = ()
    reasoning_effort: str | None = None
    timeout_seconds: float = 120.0


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    total_tokens: int
    cost_usd: float | None


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return cast(dict[str, object], value)


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _optional_nonnegative_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative number or null")
    return float(value)


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest for a byte string."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file."""

    return sha256_bytes(path.read_bytes())


def build_request_payload(prompt: str, config: OpenRouterConfig) -> dict[str, object]:
    """Build a pinned, non-fallback OpenRouter request body."""

    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if not config.model.strip():
        raise ValueError("model must not be empty")
    payload: dict[str, object] = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    if config.provider_only:
        payload["provider"] = {
            "only": list(config.provider_only),
            "allow_fallbacks": False,
        }
    if config.reasoning_effort is not None:
        payload["reasoning"] = {"effort": config.reasoning_effort}
    return payload


def _usage_object(response: dict[str, object]) -> dict[str, object]:
    usage = response.get("usage")
    if usage is None:
        raise ValueError("OpenRouter response is missing usage")
    return _object(usage)


def extract_usage(
    response: dict[str, object], generation: dict[str, object] | None = None
) -> Usage:
    """Extract provider-reported token and cost fields without estimating."""

    usage = _usage_object(response)
    details = usage.get("prompt_tokens_details")
    details_object = _object(details) if details is not None else {}
    cost = usage.get("cost")
    if cost is None and generation is not None:
        generation_data = generation.get("data")
        if isinstance(generation_data, dict):
            cost = generation_data.get("total_cost")
        if cost is None:
            cost = generation.get("total_cost")
    return Usage(
        input_tokens=_nonnegative_int(usage.get("prompt_tokens"), "usage.prompt_tokens"),
        output_tokens=_nonnegative_int(usage.get("completion_tokens"), "usage.completion_tokens"),
        cached_input_tokens=_nonnegative_int(
            details_object.get("cached_tokens", 0),
            "usage.prompt_tokens_details.cached_tokens",
        ),
        total_tokens=_nonnegative_int(usage.get("total_tokens"), "usage.total_tokens"),
        cost_usd=_optional_nonnegative_number(cost, "usage.cost/total_cost"),
    )


def response_id(response: dict[str, object]) -> str:
    """Return the provider generation ID required for audit lookup."""

    value = response.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("OpenRouter response is missing id")
    return value


def response_model(response: dict[str, object]) -> str:
    """Return the model actually used by OpenRouter."""

    value = response.get("model")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("OpenRouter response is missing model")
    return value


def generation_provider(generation: dict[str, object] | None) -> str | None:
    """Return the underlying provider name from the generation lookup."""

    if generation is None:
        return None
    data = generation.get("data")
    if not isinstance(data, dict):
        return None
    value = data.get("provider_name")
    return value if isinstance(value, str) and value.strip() else None


def has_tool_calls(response: dict[str, object]) -> bool:
    """Return whether the completion asks a client-side harness to execute tools."""

    choices = response.get("choices")
    if not isinstance(choices, list):
        return False
    for choice in choices:
        choice_object = _object(choice)
        message = choice_object.get("message")
        if not isinstance(message, dict):
            continue
        if isinstance(message.get("tool_calls"), list) and message["tool_calls"]:
            return True
    return False


def _request_json(
    *,
    url: str,
    method: str,
    api_key: str,
    body: bytes | None,
    timeout_seconds: float,
) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=timeout_seconds) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    return _object(parsed)


def fetch_completion(
    *,
    prompt: str,
    config: OpenRouterConfig,
    api_key: str,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Fetch a completion and its auditable generation record."""

    payload = build_request_payload(prompt, config)
    response = _request_json(
        url=f"{OPENROUTER_API}/chat/completions",
        method="POST",
        api_key=api_key,
        body=json.dumps(payload, sort_keys=True).encode("utf-8"),
        timeout_seconds=config.timeout_seconds,
    )
    generation: dict[str, object] | None = None
    generation_id = response_id(response)
    try:
        generation = _request_json(
            url=f"{OPENROUTER_API}/generation?{urlencode({'id': generation_id})}",
            method="GET",
            api_key=api_key,
            body=None,
            timeout_seconds=config.timeout_seconds,
        )
    except (HTTPError, URLError, ValueError):
        generation = None
    return response, generation


def write_receipt(
    *,
    output_dir: Path,
    pair_id: str,
    run_id: str,
    condition: str,
    prompt: str,
    payload: dict[str, object],
    response: dict[str, object],
    generation: dict[str, object] | None,
    config: OpenRouterConfig,
) -> Path:
    """Write immutable request, response, generation, and receipt artifacts."""

    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {sorted(CONDITIONS)}")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence directory: {output_dir}")
    output_dir.mkdir(parents=True)
    request_path = output_dir / "request.json"
    response_path = output_dir / "provider_response.json"
    generation_path = output_dir / "generation.json"
    prompt_path = output_dir / "prompt.txt"
    request_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(
        json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    prompt_path.write_text(prompt, encoding="utf-8")
    if generation is not None:
        generation_path.write_text(
            json.dumps(generation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    usage = extract_usage(response, generation)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "benchmark_scope": "openrouter_api_completion_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "pair_id": pair_id,
        "run_id": run_id,
        "condition": condition,
        "provider": "openrouter",
        "actual_provider": generation_provider(generation),
        "provider_request_id": response_id(response),
        "requested_model": config.model,
        "actual_model": response_model(response),
        "provider_only": list(config.provider_only),
        "allow_fallbacks": False if config.provider_only else None,
        "reasoning_effort": config.reasoning_effort,
        "usage": asdict(usage),
        "tool_calls_present": has_tool_calls(response),
        "generation_lookup_succeeded": generation is not None,
        "prompt_path": str(prompt_path),
        "prompt_sha256": sha256_file(prompt_path),
        "request_path": str(request_path),
        "request_sha256": sha256_file(request_path),
        "provider_response_path": str(response_path),
        "provider_response_sha256": sha256_file(response_path),
        "generation_path": str(generation_path) if generation is not None else None,
        "generation_sha256": sha256_file(generation_path) if generation is not None else None,
        "score_status": "pending_independent_review",
        "ledger_write": "none",
    }
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    receipt_path.with_suffix(".json.sha256").write_text(
        f"{receipt_sha}  {receipt_path.name}\n", encoding="utf-8"
    )
    return receipt_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--pair-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", ""))
    parser.add_argument("--provider-only", action="append", default=[])
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Required safety acknowledgement before making the live API call.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.allow_network:
        print("refusing live OpenRouter call without --allow-network", file=sys.stderr)
        return 2
    if not args.provider_only:
        print("--provider-only is required for reproducible benchmark evidence", file=sys.stderr)
        return 2
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "OPENROUTER_API_KEY is required and must not be stored in the repository",
            file=sys.stderr,
        )
        return 2
    try:
        prompt = args.prompt.read_text(encoding="utf-8")
        config = OpenRouterConfig(
            model=args.model,
            provider_only=tuple(args.provider_only),
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout,
        )
        payload = build_request_payload(prompt, config)
        response, generation = fetch_completion(prompt=prompt, config=config, api_key=api_key)
        receipt_path = write_receipt(
            output_dir=args.output_dir,
            pair_id=args.pair_id,
            run_id=args.run_id,
            condition=args.condition,
            prompt=prompt,
            payload=payload,
            response=response,
            generation=generation,
            config=config,
        )
    except (OSError, HTTPError, URLError, ValueError, FileExistsError) as error:
        print(f"OpenRouter receipt failed: {error}", file=sys.stderr)
        return 2
    if has_tool_calls(response):
        print(
            "receipt written, but tool calls require a separate local execution harness",
            file=sys.stderr,
        )
        return 3
    print(json.dumps({"receipt": str(receipt_path), "provider_request_id": response_id(response)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
