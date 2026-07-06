#!/usr/bin/env python3
"""
AIOS: generate-rule-bundle.py
Generate capability-matched micro-tasks for a promoted rule artifact.

Creates 2-3 tasks in tasks/rule-linked/<bundle_id>/ that test the latent
capability without leaking rule wording. Tasks target observable agent
behavior, not rule compliance.

Usage:
  python3 ~/AIOS/bin/generate-rule-bundle.py --pattern-id <id>
  python3 ~/AIOS/bin/generate-rule-bundle.py --artifact <path.json>
"""

import argparse
import importlib.util as _ilu
import json
import sqlite3
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path


def _load_rule_artifacts():
    spec = _ilu.spec_from_file_location(
        "rule_artifacts",
        Path(__file__).parent / "rule-artifacts.py",
    )
    assert spec is not None
    assert spec.loader is not None
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ra = _load_rule_artifacts()
read_artifact = _ra.read_artifact
write_artifact = _ra.write_artifact

LAB_DIR = Path.home() / "projects/claude-improvement-lab"
TASKS_DIR = LAB_DIR / "tasks/rule-linked"
DB = Path.home() / "AIOS/data/aios.db"

TASK_TOML = """schema_version = "1.1"\n\n[verifier]\ntimeout_sec = 60\n\n[environment]\ntimeout_sec = 180\n"""
TEST_SH = "#!/bin/bash\nset -e\nmkdir -p /logs/verifier\npython3 /tests/test.py\n"

DOCKERFILE_TMPL = """\
FROM autoagent-base
{copy_lines}
RUN mkdir -p /task/output
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _bundle_id(pattern_id: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"bundle-{pattern_id[:8]}-{ts}"


def _write_task(bundle_dir: Path, task_name: str, files: dict[str, str]) -> Path:
    """Write all files for a task. files is {relative_path: content}."""
    task_dir = bundle_dir / task_name
    for rel_path, content in files.items():
        dest = task_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    return task_dir


# ---------------------------------------------------------------------------
# Template families
# ---------------------------------------------------------------------------


def _tasks_verification() -> list[tuple[str, dict[str, str]]]:
    """Tasks that require running tests to confirm correctness before finishing."""

    # ── Task 1: off-by-one bug ──────────────────────────────────────────────
    count_words_py = textwrap.dedent("""\
        def count_words(text: str) -> int:
            \"\"\"Return the number of words in text.\"\"\"
            return len(text.split()) - 1  # BUG: off by one

        def count_sentences(text: str) -> int:
            \"\"\"Return the number of sentences (ending in . ! ?)\"\"\"
            return sum(1 for c in text if c in ".!?")
    """)

    test_count_words_py = textwrap.dedent("""\
        import sys, importlib.util

        def load_module(path):
            spec = importlib.util.spec_from_file_location("module", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        path = sys.argv[1] if len(sys.argv) > 1 else "/task/count_words.py"
        m = load_module(path)

        passed = 0
        tests = [("one", 1), ("one two", 2), ("one two three", 3), ("", 0),
                 ("hello world foo bar baz", 5)]
        for text, expected in tests:
            got = m.count_words(text)
            if got == expected:
                passed += 1
            else:
                print(f"FAIL: count_words({text!r}) = {got}, expected {expected}")

        print(f"{passed}/{len(tests)} tests passed")
        sys.exit(0 if passed == len(tests) else 1)
    """)

    verifier_1 = textwrap.dedent("""\
        \"\"\"Verifier for find-fix-off-by-one.\"\"\"
        import importlib.util, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/count_words.py"

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def load_module(path):
            spec = importlib.util.spec_from_file_location("module", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                m = load_module(OUTPUT_PATH)
            except Exception as e:
                write_score(0.0, f"import error: {e}"); return
            tests = [("one", 1), ("one two", 2), ("one two three", 3), ("", 0),
                     ("hello world foo bar baz", 5)]
            correct = sum(1 for t, exp in tests if m.count_words(t) == exp)
            write_score(correct / len(tests), f"({correct}/{len(tests)} assertions)")

        if __name__ == "__main__": main()
    """)

    dockerfile_1 = DOCKERFILE_TMPL.format(
        copy_lines="COPY count_words.py /task/count_words.py\nCOPY test_count_words.py /task/test_count_words.py"
    )

    task1 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/count_words.py` contains a word-counting module. The tests at `/task/test_count_words.py` currently fail because of a bug.

            Your job:
            1. Read `/task/count_words.py` and `/task/test_count_words.py` to understand what the functions are supposed to do.
            2. Find the bug.
            3. Fix it.
            4. Write the corrected file to `/task/output/count_words.py`.
            5. Run: `python3 /task/test_count_words.py /task/output/count_words.py`
        """),
        "environment/Dockerfile": dockerfile_1,
        "environment/count_words.py": count_words_py,
        "environment/test_count_words.py": test_count_words_py,
        "tests/test.py": verifier_1,
        "tests/test.sh": TEST_SH,
    }

    # ── Task 2: edge-case handling bug ────────────────────────────────────
    divider_py = textwrap.dedent("""\
        def safe_divide(a: float, b: float) -> float | None:
            \"\"\"Divide a by b. Returns None if division is not possible.\"\"\"
            return a / b  # BUG: doesn't handle b == 0

        def percentage(part: float, total: float) -> float:
            \"\"\"Return part/total as a percentage (0-100). Returns 0.0 if total is 0.\"\"\"
            return (part / total) * 100  # BUG: doesn't handle total == 0
    """)

    test_divider_py = textwrap.dedent("""\
        import sys, importlib.util

        def load_module(path):
            spec = importlib.util.spec_from_file_location("module", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        path = sys.argv[1] if len(sys.argv) > 1 else "/task/divider.py"
        m = load_module(path)

        passed, total = 0, 6

        def check(cond, msg):
            global passed
            if cond: passed += 1
            else: print(f"FAIL: {msg}")

        check(m.safe_divide(10, 2) == 5.0, "safe_divide(10,2)==5.0")
        check(m.safe_divide(7, 2) == 3.5,  "safe_divide(7,2)==3.5")
        check(m.safe_divide(5, 0) is None, "safe_divide(5,0) is None")
        check(m.percentage(25, 100) == 25.0, "percentage(25,100)==25.0")
        check(m.percentage(1, 4) == 25.0,    "percentage(1,4)==25.0")
        check(m.percentage(50, 0) == 0.0,    "percentage(50,0)==0.0")

        print(f"{passed}/{total} tests passed")
        sys.exit(0 if passed == total else 1)
    """)

    verifier_2 = textwrap.dedent("""\
        \"\"\"Verifier for patch-handle-edge-cases.\"\"\"
        import importlib.util, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/divider.py"

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def load_module(path):
            spec = importlib.util.spec_from_file_location("module", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                m = load_module(OUTPUT_PATH)
            except Exception as e:
                write_score(0.0, f"import error: {e}"); return
            checks = [
                m.safe_divide(10, 2) == 5.0,
                m.safe_divide(7, 2) == 3.5,
                m.safe_divide(5, 0) is None,
                m.percentage(25, 100) == 25.0,
                m.percentage(1, 4) == 25.0,
                m.percentage(50, 0) == 0.0,
            ]
            correct = sum(checks)
            write_score(correct / len(checks), f"({correct}/{len(checks)} assertions)")

        if __name__ == "__main__": main()
    """)

    dockerfile_2 = DOCKERFILE_TMPL.format(
        copy_lines="COPY divider.py /task/divider.py\nCOPY test_divider.py /task/test_divider.py"
    )

    task2 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/divider.py` has edge-case handling bugs. The tests at `/task/test_divider.py` document what the correct behavior should be.

            Your job:
            1. Read `/task/divider.py` and `/task/test_divider.py` to understand the expected behavior.
            2. Fix the bugs.
            3. Write the corrected file to `/task/output/divider.py`.
            4. Confirm your fix works by running: `python3 /task/test_divider.py /task/output/divider.py`
        """),
        "environment/Dockerfile": dockerfile_2,
        "environment/divider.py": divider_py,
        "environment/test_divider.py": test_divider_py,
        "tests/test.py": verifier_2,
        "tests/test.sh": TEST_SH,
    }

    return [
        ("find-fix-off-by-one", task1),
        ("patch-handle-edge-cases", task2),
    ]


def _tasks_planning() -> list[tuple[str, dict[str, str]]]:
    """Tasks that require multiple ordered steps to complete correctly."""

    # ── Task 1: word frequency pipeline ────────────────────────────────────
    text_txt = "apple apple apple apple apple banana banana banana cherry cherry date elderberry\n"

    verifier_wf = textwrap.dedent("""\
        \"\"\"Verifier for word-freq-pipeline.\"\"\"
        import json, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/top_words.json"
        EXPECTED = [["apple", 5], ["banana", 3], ["cherry", 2], ["date", 1], ["elderberry", 1]]

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                result = json.loads(open(OUTPUT_PATH).read())
            except Exception as e:
                write_score(0.0, f"JSON parse error: {e}"); return
            write_score(1.0 if result == EXPECTED else 0.0,
                        "exact match" if result == EXPECTED else f"mismatch: {result!r}")

        if __name__ == "__main__": main()
    """)

    task1 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/text.txt` contains words separated by whitespace.

            Your job:
            1. Read `/task/text.txt`.
            2. Count word frequencies (treat all words as lowercase, split on whitespace only).
            3. Find the top 5 most common words.
            4. Write the result to `/task/output/top_words.json` as a JSON array of [word, count] pairs, sorted by count descending. For ties, sort alphabetically.

            Example format: `[["apple", 5], ["banana", 3], ...]`
        """),
        "environment/Dockerfile": DOCKERFILE_TMPL.format(copy_lines="COPY text.txt /task/text.txt"),
        "environment/text.txt": text_txt,
        "tests/test.py": verifier_wf,
        "tests/test.sh": TEST_SH,
    }

    # ── Task 2: CSV filter + group sum ─────────────────────────────────────
    sales_csv = textwrap.dedent("""\
        region,product,amount
        North,Widget,150
        South,Gadget,80
        North,Gadget,200
        East,Widget,120
        South,Widget,45
        East,Gadget,300
        North,Widget,90
        South,Gadget,110
        East,Widget,60
    """)

    verifier_csv = textwrap.dedent("""\
        \"\"\"Verifier for csv-group-sum.\"\"\"
        import json, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/regional_totals.json"
        EXPECTED = {"East": 420, "North": 350, "South": 110}

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                result = json.loads(open(OUTPUT_PATH).read())
            except Exception as e:
                write_score(0.0, f"JSON parse error: {e}"); return
            write_score(1.0 if result == EXPECTED else 0.0,
                        "exact match" if result == EXPECTED else f"mismatch: {result!r}")

        if __name__ == "__main__": main()
    """)

    task2 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/sales.csv` contains sales data with columns: region, product, amount.

            Your job:
            1. Read `/task/sales.csv`.
            2. Filter rows where amount > 100.
            3. Sum the amounts by region.
            4. Write the result to `/task/output/regional_totals.json` as a JSON object: `{"region": total_amount, ...}`
        """),
        "environment/Dockerfile": DOCKERFILE_TMPL.format(
            copy_lines="COPY sales.csv /task/sales.csv"
        ),
        "environment/sales.csv": sales_csv,
        "tests/test.py": verifier_csv,
        "tests/test.sh": TEST_SH,
    }

    return [
        ("word-freq-pipeline", task1),
        ("csv-group-sum", task2),
    ]


def _tasks_inspection() -> list[tuple[str, dict[str, str]]]:
    """Tasks that require reading and understanding code before modifying or auditing it."""

    # ── Task 1: extend existing pattern ────────────────────────────────────
    validators_py = textwrap.dedent("""\
        def validate_username(s: str) -> bool:
            \"\"\"Return True if s is a valid username: 3-20 chars, alphanumeric + underscore.\"\"\"
            if not s or not isinstance(s, str):
                return False
            if len(s) < 3 or len(s) > 20:
                return False
            return all(c.isalnum() or c == "_" for c in s)


        def validate_zip_code(s: str) -> bool:
            \"\"\"Return True if s is a valid US zip code: exactly 5 digits.\"\"\"
            if not s or not isinstance(s, str):
                return False
            return len(s) == 5 and s.isdigit()


        def validate_age(s: str) -> bool:
            \"\"\"Return True if s represents a valid age: integer between 0 and 150.\"\"\"
            if not s or not isinstance(s, str):
                return False
            try:
                age = int(s)
            except ValueError:
                return False
            return 0 <= age <= 150
    """)

    verifier_val = textwrap.dedent("""\
        \"\"\"Verifier for extend-validator-pattern.\"\"\"
        import importlib.util, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/validators.py"

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def load_module(path):
            spec = importlib.util.spec_from_file_location("module", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                m = load_module(OUTPUT_PATH)
            except Exception as e:
                write_score(0.0, f"import error: {e}"); return
            if not hasattr(m, "validate_hex_color"):
                write_score(0.0, "validate_hex_color not found"); return
            f = m.validate_hex_color
            checks = [
                f("#ff0000") is True,
                f("#FFFFFF") is True,
                f("#abc123") is True,
                f("") is False,
                f(None) is False,
                f("#xyz") is False,
                f("ff0000") is False,
                f("#gg0000") is False,
                f("#12345") is False,
            ]
            correct = sum(checks)
            write_score(correct / len(checks), f"({correct}/{len(checks)} assertions)")

        if __name__ == "__main__": main()
    """)

    task1 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/validators.py` contains three validation functions.

            Your job:
            1. Read `/task/validators.py` carefully to understand the pattern used by the existing functions.
            2. Add a new function `validate_hex_color(s: str) -> bool` that follows the same pattern.
               A hex color is valid if it starts with `#` followed by exactly 6 hexadecimal characters (0-9, a-f, A-F).
            3. Write the updated file (all four functions) to `/task/output/validators.py`.
        """),
        "environment/Dockerfile": DOCKERFILE_TMPL.format(
            copy_lines="COPY validators.py /task/validators.py"
        ),
        "environment/validators.py": validators_py,
        "tests/test.py": verifier_val,
        "tests/test.sh": TEST_SH,
    }

    # ── Task 2: function signature audit ───────────────────────────────────
    api_py = textwrap.dedent("""\
        def get_user(user_id: int) -> dict:
            \"\"\"Retrieve a user by ID.\"\"\"
            return {"id": user_id, "name": "Unknown"}

        def create_user(name: str, email: str, role: str = "viewer") -> dict:
            \"\"\"Create a new user.\"\"\"
            return {"name": name, "email": email, "role": role}

        def delete_user(user_id: int, force: bool = False) -> bool:
            \"\"\"Delete a user. Returns True on success.\"\"\"
            return True

        def list_users(page: int = 1, limit: int = 10) -> list:
            \"\"\"List users with pagination.\"\"\"
            return []

        def update_user(user_id: int, **kwargs) -> dict | None:
            \"\"\"Update user fields. Returns None if user not found.\"\"\"
            return None
    """)

    verifier_audit = textwrap.dedent("""\
        \"\"\"Verifier for function-signature-audit.\"\"\"
        import json, os

        REWARD_PATH = "/logs/verifier/reward.txt"
        OUTPUT_PATH = "/task/output/audit.json"
        GROUND_TRUTH = {"1": True, "2": True, "3": False, "4": True, "5": True}

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def main():
            if not os.path.exists(OUTPUT_PATH):
                write_score(0.0, "output file not found"); return
            try:
                result = json.loads(open(OUTPUT_PATH).read())
            except Exception as e:
                write_score(0.0, f"JSON parse error: {e}"); return
            if not isinstance(result, dict):
                write_score(0.0, "expected a JSON object"); return
            correct = 0
            for key, want in GROUND_TRUTH.items():
                got_raw = result.get(key)
                got = got_raw if isinstance(got_raw, bool) else (str(got_raw).lower() == "true" if got_raw is not None else None)
                if got == want:
                    correct += 1
                else:
                    print(f"  claim {key}: got {got_raw!r}, want {want}")
            write_score(correct / len(GROUND_TRUTH), f"({correct}/{len(GROUND_TRUTH)} correct)")

        if __name__ == "__main__": main()
    """)

    task2 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The file `/task/api.py` contains a Python module with five functions.

            Read `/task/api.py` carefully. For each of the following claims about the functions, write true or false based ONLY on what you observe in the file. Do not assume or guess.

            Claims:
            1. "get_user takes exactly one required parameter."
            2. "create_user has a default value for the role parameter."
            3. "delete_user returns a string."
            4. "list_users has no required parameters."
            5. "update_user accepts keyword arguments."

            Write your answers to `/task/output/audit.json` as: `{"1": true/false, "2": true/false, ...}`
        """),
        "environment/Dockerfile": DOCKERFILE_TMPL.format(copy_lines="COPY api.py /task/api.py"),
        "environment/api.py": api_py,
        "tests/test.py": verifier_audit,
        "tests/test.sh": TEST_SH,
    }

    return [
        ("extend-validator-pattern", task1),
        ("function-signature-audit", task2),
    ]


def _tasks_incremental() -> list[tuple[str, dict[str, str]]]:
    """Tasks that require consistent changes across multiple files."""

    # ── Task 1: multi-file rename ──────────────────────────────────────────
    lib_py = textwrap.dedent("""\
        def process_data(items: list) -> list:
            \"\"\"Process a list of items and return results.\"\"\"
            return [item * 2 for item in items if item > 0]
    """)

    main_py = textwrap.dedent("""\
        from lib import process_data

        def run(data: list) -> list:
            results = process_data(data)
            return results
    """)

    helpers_py = textwrap.dedent("""\
        from lib import process_data

        def batch_process(batches: list) -> list:
            \"\"\"Process multiple batches using process_data.\"\"\"
            output = []
            for batch in batches:
                output.extend(process_data(batch))
            return output
    """)

    verifier_rename = textwrap.dedent("""\
        \"\"\"Verifier for multi-file-rename.\"\"\"
        import importlib.util, os, sys

        REWARD_PATH = "/logs/verifier/reward.txt"
        FILES = {
            "lib": "/task/output/lib.py",
            "main": "/task/output/main.py",
            "helpers": "/task/output/helpers.py",
        }

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def load_module(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod

        def main():
            for name, path in FILES.items():
                if not os.path.exists(path):
                    write_score(0.0, f"{path} not found"); return

            checks = []
            for name, path in FILES.items():
                content = open(path).read()
                checks.append(("transform_data" in content, f"{name}.py contains transform_data"))
                checks.append(("process_data" not in content, f"{name}.py no longer contains process_data"))

            # Functional test: import lib and run transform_data
            try:
                sys.path.insert(0, "/task/output")
                lib = load_module("lib", FILES["lib"])
                checks.append((hasattr(lib, "transform_data"), "lib.transform_data exists"))
                checks.append((lib.transform_data([1, -2, 3]) == [2, 6], "transform_data([1,-2,3])==[2,6]"))
                helpers = load_module("helpers", FILES["helpers"])
                result = helpers.batch_process([[1, 2], [3, -1]])
                checks.append((result == [2, 4, 6], f"batch_process correct: {result}"))
            except Exception as e:
                checks.append((False, f"import error: {e}"))

            correct = sum(1 for ok, _ in checks if ok)
            for ok, msg in checks:
                if not ok:
                    print(f"  FAIL: {msg}")
            write_score(correct / len(checks), f"({correct}/{len(checks)} checks)")

        if __name__ == "__main__": main()
    """)

    dockerfile_rename = DOCKERFILE_TMPL.format(
        copy_lines="COPY lib.py /task/lib.py\nCOPY main.py /task/main.py\nCOPY helpers.py /task/helpers.py"
    )

    task1 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The function `process_data` is defined in `/task/lib.py` and imported in `/task/main.py` and `/task/helpers.py`.

            Your job:
            Rename `process_data` to `transform_data` across all three files — the definition in `lib.py` and all usages in `main.py` and `helpers.py`.

            Write the updated files to:
            - `/task/output/lib.py`
            - `/task/output/main.py`
            - `/task/output/helpers.py`
        """),
        "environment/Dockerfile": dockerfile_rename,
        "environment/lib.py": lib_py,
        "environment/main.py": main_py,
        "environment/helpers.py": helpers_py,
        "tests/test.py": verifier_rename,
        "tests/test.sh": TEST_SH,
    }

    # ── Task 2: add optional param consistently ───────────────────────────
    service_py = textwrap.dedent("""\
        def fetch_data(url: str, retry: bool = False) -> dict:
            \"\"\"Fetch data from a URL.\"\"\"
            return {"url": url, "data": "sample", "retry": retry}
    """)

    handler_py = textwrap.dedent("""\
        from service import fetch_data

        def handle_request(url: str) -> dict:
            \"\"\"Handle an incoming request by fetching data.\"\"\"
            return fetch_data(url)

        def handle_with_retry(url: str) -> dict:
            \"\"\"Handle a request with retry enabled.\"\"\"
            return fetch_data(url, retry=True)
    """)

    verifier_param = textwrap.dedent("""\
        \"\"\"Verifier for add-optional-param.\"\"\"
        import importlib.util, os, sys, inspect

        REWARD_PATH = "/logs/verifier/reward.txt"

        def write_score(score, reason=""):
            with open(REWARD_PATH, "w") as f: f.write(str(round(score, 4)))
            print(f"Score: {score:.4f}  {reason}")

        def load_module(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod

        def main():
            for path in ["/task/output/service.py", "/task/output/handler.py"]:
                if not os.path.exists(path):
                    write_score(0.0, f"{path} not found"); return
            try:
                sys.path.insert(0, "/task/output")
                svc = load_module("service", "/task/output/service.py")
                hdl = load_module("handler", "/task/output/handler.py")
            except Exception as e:
                write_score(0.0, f"import error: {e}"); return

            checks = []
            sig = inspect.signature(svc.fetch_data)
            params = list(sig.parameters)
            checks.append(("timeout" in params, "fetch_data has timeout param"))
            checks.append((sig.parameters.get("timeout") and sig.parameters["timeout"].default == 30,
                           "timeout default is 30"))

            result = svc.fetch_data("http://example.com")
            checks.append(("timeout" in result, "returned dict includes timeout"))
            checks.append((result.get("timeout") == 30, "default timeout=30 in returned dict"))

            # handle_request should pass timeout=60
            r2 = hdl.handle_request("http://example.com")
            checks.append((r2.get("timeout") == 60, f"handle_request uses timeout=60, got {r2.get('timeout')}"))

            # handle_with_retry should still work (no required changes)
            r3 = hdl.handle_with_retry("http://example.com")
            checks.append((r3.get("retry") is True, "handle_with_retry still sets retry=True"))

            correct = sum(1 for ok, _ in checks if ok)
            for ok, msg in checks:
                if not ok:
                    print(f"  FAIL: {msg}")
            write_score(correct / len(checks), f"({correct}/{len(checks)} checks)")

        if __name__ == "__main__": main()
    """)

    dockerfile_param = DOCKERFILE_TMPL.format(
        copy_lines="COPY service.py /task/service.py\nCOPY handler.py /task/handler.py"
    )

    task2 = {
        "task.toml": TASK_TOML,
        "instruction.md": textwrap.dedent("""\
            The function `fetch_data` in `/task/service.py` currently has two parameters: `url` and `retry`.

            Your job:
            1. Add a third optional parameter `timeout` (default=30) to `fetch_data` in `service.py`. Update the returned dict to include `"timeout": timeout`.
            2. Update `handle_request` in `/task/handler.py` to pass `timeout=60` when calling `fetch_data`. Leave `handle_with_retry` unchanged.
            3. Write the updated files to `/task/output/service.py` and `/task/output/handler.py`.
        """),
        "environment/Dockerfile": dockerfile_param,
        "environment/service.py": service_py,
        "environment/handler.py": handler_py,
        "tests/test.py": verifier_param,
        "tests/test.sh": TEST_SH,
    }

    return [
        ("multi-file-rename", task1),
        ("add-optional-param", task2),
    ]


# ---------------------------------------------------------------------------
# Capability → family mapping
# ---------------------------------------------------------------------------

FAMILY_MAP = {
    "verification": _tasks_verification,
    "completion-validation": _tasks_verification,
    "planning": _tasks_planning,
    "multi-step-execution": _tasks_planning,
    "inspection": _tasks_inspection,
    "claim-calibration": _tasks_inspection,
    "tool-selection": _tasks_inspection,
    "incremental-editing": _tasks_incremental,
}


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------


def generate_bundle(artifact: dict, dry_run: bool = False) -> dict:
    pattern_id = artifact["pattern_id"]
    cap_class = artifact.get("capability_class", "multi-step-execution")
    bundle_id = _bundle_id(pattern_id)

    family_fn = FAMILY_MAP.get(cap_class, _tasks_planning)
    tasks = family_fn()  # list of (task_name, files_dict)

    bundle_dir = TASKS_DIR / bundle_id
    task_manifest = []

    for task_name, files in tasks:
        task_path = bundle_dir / task_name
        if not dry_run:
            _write_task(bundle_dir, task_name, files)
        task_manifest.append(
            {
                "name": task_name,
                "path": str(task_path.relative_to(LAB_DIR)),
                "capability_class": cap_class,
                "family": family_fn.__name__,
            }
        )
        print(f"  {'[DRY] ' if dry_run else ''}wrote task: {task_name}")

    return {
        "bundle_id": bundle_id,
        "pattern_id": pattern_id,
        "capability_class": cap_class,
        "task_manifest": task_manifest,
        "created_at": _now(),
    }


def register_bundle(bundle: dict, artifact: dict) -> None:
    conn = sqlite3.connect(DB)
    conn.execute(
        """
        INSERT INTO rule_eval_bundles
          (id, pattern_id, rule_text, failure_class, capability_class,
           generation_strategy, task_manifest_json, artifact_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bundle["bundle_id"],
            bundle["pattern_id"],
            artifact.get("rule_text", ""),
            "",
            bundle["capability_class"],
            "template-v1",
            json.dumps(bundle["task_manifest"]),
            str(Path.home() / f"AIOS/data/rule-artifacts/{bundle['pattern_id']}.json"),
            bundle["created_at"],
        ),
    )
    conn.execute(
        "UPDATE patterns SET lab_status='bundle_ready' WHERE id=?",
        (bundle["pattern_id"],),
    )
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pattern-id", help="Pattern ID to look up artifact for")
    group.add_argument("--artifact", help="Path to artifact JSON file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be written, don't write"
    )
    args = parser.parse_args()

    if args.pattern_id:
        artifact = read_artifact(args.pattern_id)
        if not artifact:
            print(f"No artifact found for pattern {args.pattern_id}")
            sys.exit(1)
    else:
        artifact = json.loads(Path(args.artifact).read_text())

    print(
        f"Generating bundle for pattern {artifact['pattern_id'][:8]} "
        f"(cap={artifact.get('capability_class')}, mutation={artifact.get('mutation_scope')})"
    )

    bundle = generate_bundle(artifact, dry_run=args.dry_run)

    if not args.dry_run:
        # Update artifact with bundle_id
        artifact["eval_bundle_id"] = bundle["bundle_id"]
        write_artifact(artifact)
        register_bundle(bundle, artifact)
        print(f"\nBundle registered: {bundle['bundle_id']}")
        print(f"Tasks: {[t['name'] for t in bundle['task_manifest']]}")
    else:
        print(f"\n[DRY] Bundle would be: {bundle['bundle_id']}")
        print(f"[DRY] Tasks: {[t['name'] for t in bundle['task_manifest']]}")


if __name__ == "__main__":
    main()
