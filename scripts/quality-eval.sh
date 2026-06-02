#!/usr/bin/env bash
set -eo pipefail

python_large_count=0
tests_no_assert_count=0
services_import_bin_count=0
ts_large_count=0
vulture_count=0
shellcheck_count=0

count_lines() {
  awk 'NF > 0 { count += 1 } END { print count + 0 }'
}

echo "=== Python files over 500 lines ==="
python_large=$(
  find . -name '*.py' -not -path './.venv/*' -print0 \
    | xargs -0 wc -l \
    | awk '$1 > 500 && $2 != "total"' \
    | sort -rn || true
)
if [[ -n "$python_large" ]]; then
  echo "$python_large"
  python_large_count=$(printf '%s\n' "$python_large" | count_lines)
else
  echo "No Python files over 500 lines found."
fi

echo
echo "=== Test files with no assertions ==="
if [[ -d tests ]]; then
  tests_no_assert=$(grep -rL 'assert\|assertEqual\|assertIn\|pytest.raises' tests/ --include='*.py' || true)
else
  tests_no_assert=""
fi
if [[ -n "$tests_no_assert" ]]; then
  echo "$tests_no_assert"
  tests_no_assert_count=$(printf '%s\n' "$tests_no_assert" | count_lines)
else
  echo "No assertion-free Python test files found."
fi

echo
echo "=== services/ files importing from bin/ ==="
services_import_bin=$(grep -rn 'from bin\.' services/ --include='*.py' || true)
if [[ -n "$services_import_bin" ]]; then
  echo "$services_import_bin"
  services_import_bin_count=$(printf '%s\n' "$services_import_bin" | count_lines)
else
  echo "No services/ imports from bin/ found."
fi

echo
echo "=== TypeScript files over 400 lines in aios-ui/components ==="
if [[ -d aios-ui/components ]]; then
  ts_large=$(
    find aios-ui/components \( -name '*.tsx' -o -name '*.ts' \) -print0 \
      | xargs -0 wc -l \
      | awk '$1 > 400 && $2 != "total"' \
      | sort -rn || true
  )
else
  ts_large=""
fi
if [[ -n "$ts_large" ]]; then
  echo "$ts_large"
  ts_large_count=$(printf '%s\n' "$ts_large" | count_lines)
else
  echo "No TypeScript component files over 400 lines found."
fi

echo
echo "=== Dead-code candidates from vulture ==="
if command -v vulture >/dev/null 2>&1; then
  vulture_output=$(vulture . --min-confidence 80 || true)
  if [[ -n "$vulture_output" ]]; then
    echo "$vulture_output"
    vulture_count=$(printf '%s\n' "$vulture_output" | count_lines)
  else
    echo "No vulture findings at min confidence 80."
  fi
else
  echo "vulture not available - install with uv add --dev vulture"
fi

echo
echo "=== Shellcheck warnings in bin shell scripts ==="
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck_output=$(
    find bin -name '*.sh' -print0 \
      | xargs -0 shellcheck --severity=warning 2>/dev/null || true
  )
  if [[ -n "$shellcheck_output" ]]; then
    echo "$shellcheck_output"
    shellcheck_count=$(printf '%s\n' "$shellcheck_output" | grep -c '^In ' || true)
  else
    echo "shellcheck run complete"
  fi
else
  echo "shellcheck not available"
fi

echo
echo "=== Quality eval summary ==="
printf '%-45s %s\n' "Python files over 500 lines" "$python_large_count"
printf '%-45s %s\n' "Test files with no assertions" "$tests_no_assert_count"
printf '%-45s %s\n' "services/ imports from bin/" "$services_import_bin_count"
printf '%-45s %s\n' "TS component files over 400 lines" "$ts_large_count"
printf '%-45s %s\n' "Vulture findings" "$vulture_count"
printf '%-45s %s\n' "Shellcheck files with findings" "$shellcheck_count"

exit 0
