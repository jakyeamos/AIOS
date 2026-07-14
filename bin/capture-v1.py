#!/usr/bin/env python3
"""Normalize one source adapter payload into a capture.v1 JSON envelope."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.capture_v1 import (  # noqa: E402
    CaptureInputError,
    build_capture,
    validate_capture_envelope,
)


def _read_payload(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaptureInputError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaptureInputError(f"input file is not valid JSON: {exc.msg}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Adapter payload JSON")
    parser.add_argument("--output", type=Path, help="Optional envelope output path")
    parser.add_argument("--captured-at", help="Override the capture timestamp")
    parser.add_argument("--profile", help="Override the provenance profile")
    args = parser.parse_args(argv)

    try:
        payload = _read_payload(args.input)
        if not isinstance(payload, dict):
            raise CaptureInputError("input payload must be a JSON object")
        envelope = build_capture(payload, captured_at=args.captured_at, profile=args.profile)
        errors = validate_capture_envelope(envelope)
        if errors:
            raise CaptureInputError("generated envelope failed validation: " + "; ".join(errors))
        rendered = json.dumps(envelope, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except CaptureInputError as exc:
        print(f"capture-v1: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
