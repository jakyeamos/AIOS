#!/bin/bash
# AIOS weekly maintenance — runs extract, promote, lint
# Cron: every Monday at 9am
set -euo pipefail

export AIOS_VAULT_ROOT="${AIOS_VAULT_ROOT:-$HOME/projects/Vaults/Command-Center}"
LOG="$HOME/AIOS/logs/maintenance.log"
echo "=== maintenance run $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"

# Extract learnings from new session handoffs
python3 "$HOME/AIOS/bin/extract-handoff-learnings.py" >> "$LOG" 2>&1
# Score all patterns and auto-promote/demote based on frequency+impact gates
python3 "$HOME/AIOS/bin/score-patterns.py" >> "$LOG" 2>&1
# Legacy (bigram extraction disabled internally, runs as no-op)
python3 "$HOME/AIOS/bin/extract-patterns.py" >> "$LOG" 2>&1
python3 "$HOME/AIOS/bin/build-domain-files.py" >> "$LOG" 2>&1
python3 "$HOME/AIOS/bin/extract-bug-motifs.py" >> "$LOG" 2>&1
python3 "$HOME/AIOS/bin/vault-lint.py" >> "$LOG" 2>&1

# Retire session handoffs past their TTL
python3 - >> "$LOG" 2>&1 <<'PYEOF'
import os, re, shutil
from datetime import date, datetime
from pathlib import Path

vault_root = Path(os.environ.get("AIOS_VAULT_ROOT", str(Path.home() / "projects/Vaults/Command-Center"))).expanduser()
HANDOFFS = vault_root / "02 AI OS/02 Session Handoffs"
ARCHIVE  = vault_root / "09 Archive/Session Archive"
LOG_FILE = Path.home() / "AIOS/logs/handoff-retirement.log"

today = date.today()
ARCHIVE.mkdir(parents=True, exist_ok=True)

ttl_pattern = re.compile(r"^ttl:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
moved = []

for f in HANDOFFS.glob("*.md"):
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        continue
    m = ttl_pattern.search(text)
    if not m:
        continue
    try:
        ttl_date = date.fromisoformat(m.group(1))
    except ValueError:
        continue
    if ttl_date < today:
        dest = ARCHIVE / f.name
        shutil.move(str(f), str(dest))
        moved.append(f.name)

if moved:
    ts = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as log:
        for name in moved:
            log.write(f"{ts} retired {name}\n")
    print(f"Retired {len(moved)} handoffs")
else:
    print("No handoffs to retire")
PYEOF

# Tune RTK compression thresholds from accumulated event data
python3 "$HOME/AIOS/bin/rtk-tune-thresholds.py" >> "$LOG" 2>&1

echo "done" >> "$LOG"
