from __future__ import annotations

import os
import shutil
import subprocess

from services.business.llm.base import LLMProvider
from services.business.llm.models import SourceAnalysis
from services.business.llm.prompts import build_analysis_prompt, parse_analysis_json
from services.business.sources_db import DbSource


class CliLLMProvider(LLMProvider):
    """Invoke subscribed CLIs: Claude Code (`claude -p`) or Codex (`codex exec`)."""

    name = "cli"

    def __init__(
        self,
        *,
        cli: str | None = None,
        timeout_s: int = 180,
    ) -> None:
        self.cli = (cli or os.environ.get("BUSINESS_LLM_CLI") or self._detect_cli() or "").strip()
        self.timeout_s = timeout_s

    def _detect_cli(self) -> str | None:
        if os.environ.get("BUSINESS_LLM_CLI"):
            return os.environ["BUSINESS_LLM_CLI"]
        if shutil.which("codex"):
            return "codex"
        if shutil.which("claude"):
            return "claude"
        return None

    def is_available(self) -> bool:
        return bool(self.cli and shutil.which(self.cli))

    def analyze_source(self, source: DbSource) -> SourceAnalysis | None:
        if not self.is_available():
            return None
        prompt = build_analysis_prompt(source)
        if self.cli == "codex":
            cmd = ["codex", "exec", "-c", 'sandbox_permissions=["disk-full-read-access"]', prompt]
        elif self.cli == "claude":
            cmd = ["claude", "-p", prompt]
        else:
            cmd = [self.cli, prompt]
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raise RuntimeError(f"cli llm invoke failed: {exc}") from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise RuntimeError(f"cli llm exited {completed.returncode}: {stderr[:300]}")
        output = (completed.stdout or "").strip()
        if not output:
            return None
        return parse_analysis_json(output, source.source_id, f"cli:{self.cli}")
