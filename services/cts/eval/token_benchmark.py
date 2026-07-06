from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def estimate_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, int(len(stripped) / 4))


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int
    response_tokens: int
    total_tokens: int


def benchmark_payload_tokens(prompt: dict[str, Any], response: dict[str, Any]) -> TokenUsage:
    prompt_text = json.dumps(prompt, sort_keys=True)
    response_text = json.dumps(response, sort_keys=True)
    prompt_tokens = estimate_tokens(prompt_text)
    response_tokens = estimate_tokens(response_text)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        total_tokens=prompt_tokens + response_tokens,
    )
