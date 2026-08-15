from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_runner():
    path = ROOT / "bin" / "run-pre-cr-python-tests.py"
    spec = importlib.util.spec_from_file_location("run_pre_cr_python_tests", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_executable_lines_use_python_bytecode_not_multiline_literal_contents(
    tmp_path: Path,
) -> None:
    module = _load_runner()
    source = tmp_path / "sample.py"
    source.write_text(
        "def query():\n"
        "    statement = '''\n"
        "    SELECT id\n"
        "    FROM records\n"
        "    '''\n"
        "    return statement\n",
        encoding="utf-8",
    )

    executable = module._executable_lines(source)

    assert 3 not in executable
    assert 4 not in executable
    assert 6 in executable
