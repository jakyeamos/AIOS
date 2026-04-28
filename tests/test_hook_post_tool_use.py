from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_hook_module():
    module_path = ROOT / "bin" / "hook-post-tool-use.py"
    spec = importlib.util.spec_from_file_location("hook_post_tool_use", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safe_load_stdin_recovers_literal_newlines_in_json_strings() -> None:
    module = _load_hook_module()
    raw = b'{"session_id":"s1","tool_response":{"stdout":"line one\nline two","stderr":""}}'

    old_stdin = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    try:
        data = module._safe_load_stdin()
    finally:
        sys.stdin = old_stdin

    assert data["tool_response"]["stdout"] == "line one\nline two"
