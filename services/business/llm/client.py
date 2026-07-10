from __future__ import annotations

import os
import shutil

from services.business.llm.agent_provider import AgentLLMProvider
from services.business.llm.api_provider import ApiLLMProvider
from services.business.llm.base import LLMProvider
from services.business.llm.cli_provider import CliLLMProvider

VALID_PROVIDERS = ("api", "cli", "agent", "auto")


def resolve_llm_provider(name: str | None = None) -> LLMProvider | None:
    chosen = (name or os.environ.get("BUSINESS_LLM_PROVIDER") or "auto").strip().lower()
    if chosen not in VALID_PROVIDERS:
        raise ValueError(f"Unknown LLM provider '{chosen}'. Use: {', '.join(VALID_PROVIDERS)}")

    if chosen == "auto":
        return _auto_detect_provider()
    if chosen == "api":
        return ApiLLMProvider()
    if chosen == "cli":
        return CliLLMProvider()
    return AgentLLMProvider()


def _auto_detect_provider() -> LLMProvider | None:
    api = ApiLLMProvider()
    if api.is_available():
        return api
    cli = CliLLMProvider()
    if cli.is_available():
        return cli
    if os.environ.get("BUSINESS_LLM_AGENT", "").lower() in {"1", "true", "yes"}:
        return AgentLLMProvider()
    if os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_TRACE_ID"):
        return AgentLLMProvider()
    return None


def provider_status(name: str | None = None) -> dict:
    chosen = (name or os.environ.get("BUSINESS_LLM_PROVIDER") or "auto").strip().lower()
    providers = {
        "api": ApiLLMProvider().is_available(),
        "cli": CliLLMProvider().is_available(),
        "agent": True,
    }
    resolved = _auto_detect_provider() if chosen == "auto" else resolve_llm_provider(chosen)
    auto = _auto_detect_provider()
    return {
        "configured": chosen,
        "available": {key: providers[key] for key in providers},
        "resolved": resolved.name if resolved else None,
        "auto_resolved": auto.name if auto else None,
        "cli_binary": CliLLMProvider().cli if shutil.which("codex") or shutil.which("claude") else None,
        "has_openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
    }
