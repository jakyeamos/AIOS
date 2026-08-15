from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from services.business.llm.base import LLMProvider
from services.business.llm.models import SourceAnalysis
from services.business.llm.prompts import build_analysis_prompt, parse_analysis_json
from services.business.sources_db import DbSource


class ApiLLMProvider(LLMProvider):
    name = "api"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout_s = timeout_s

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze_source(self, source: DbSource) -> SourceAnalysis | None:
        if not self.api_key:
            return None
        prompt = build_analysis_prompt(source)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You return only valid JSON for business source analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"api llm request failed: {exc}") from exc

        choices = body.get("choices") or []
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content", "")
        return parse_analysis_json(content, source.source_id, self.name)
