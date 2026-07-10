#!/usr/bin/env python3
"""
AIOS: business-query.py
FTS-backed business memory Q&A.

Usage:
  python3 ~/AIOS/bin/business-query.py "What do students think about autocompact?"
  python3 ~/AIOS/bin/business-query.py "What are people excited to learn?" --llm
  python3 ~/AIOS/bin/business-query.py "Missing talking points for cohort?" --save-question
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services.business.paths import DB_PATH  # noqa: E402
from services.business.query import answer_question  # noqa: E402
from services.business.schema import ensure_business_memory_schema  # noqa: E402


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_business_memory_schema(conn)
    return conn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Business question to answer")
    parser.add_argument("--llm", action="store_true", help="Use LLM synthesis when available")
    parser.add_argument("--provider", choices=["auto", "api", "cli", "agent"], default=None)
    parser.add_argument("--save-question", action="store_true", help="Save answer as question page")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown answer")
    args = parser.parse_args(argv)

    conn = _connect()
    result = answer_question(
        conn,
        args.question,
        use_llm=bool(args.llm),
        provider_name=args.provider,
        save_question=bool(args.save_question),
    )
    conn.close()

    if args.json:
        payload = {
            "ok": True,
            "question": result.question,
            "answer": result.answer,
            "llm_used": result.llm_used,
            "llm_provider": result.llm_provider,
            "saved_question_path": result.saved_question_path,
            "hits": [asdict(hit) for hit in result.hits],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(result.answer)
        if result.saved_question_path:
            print(f"\n---\nSaved: {result.saved_question_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
