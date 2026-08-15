#!/usr/bin/env python3
from __future__ import annotations

import sys
import trace
from pathlib import Path
from types import CodeType

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = Path("/private/tmp/aios-pre-cr-python.lcov")
IGNORED_PATH_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "archive",
    "aios-ui",
    "node_modules",
    "staging",
    "venv",
}


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        if any(part in IGNORED_PATH_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _executable_lines(file_path: Path) -> set[int]:
    source = file_path.read_text(encoding="utf-8")
    code = compile(source, str(file_path), "exec")
    lines: set[int] = set()

    def collect(code_object: CodeType) -> None:
        lines.update(line for _, _, line in code_object.co_lines() if line is not None)
        for value in code_object.co_consts:
            if isinstance(value, CodeType):
                collect(value)

    collect(code)
    return lines


def _write_lcov(counts: dict[tuple[str, int], int]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for file_path in _iter_python_files():
            relative_path = file_path.relative_to(ROOT).as_posix()
            executable = sorted(_executable_lines(file_path))
            if not executable:
                continue
            handle.write(f"SF:{relative_path}\n")
            hit_lines = 0
            for line_number in executable:
                hits = int(counts.get((str(file_path), line_number), 0))
                if hits > 0:
                    hit_lines += 1
                handle.write(f"DA:{line_number},{hits}\n")
            handle.write(f"LF:{len(executable)}\n")
            handle.write(f"LH:{hit_lines}\n")
            handle.write("end_of_record\n")


def main() -> int:
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.exec_prefix])
    exit_code = int(tracer.runfunc(pytest.main, ["-q"]))
    counts = tracer.results().counts
    _write_lcov(counts)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
