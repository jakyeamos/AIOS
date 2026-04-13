#!/usr/bin/env bash
# auto_ingest.sh — auto-promote all AIOS session summary candidates to Obsidian
# Runs hourly via cron. No human interaction required.
set -euo pipefail

DB=~/AIOS/data/aios.db
SUMMARIES=~/AIOS/logs/summaries
VAULT=~/Vaults/Command-Center
HANDOFFS="$VAULT/02 AI OS/02 Session Handoffs"
LOG=~/AIOS/logs/hooks.log

mkdir -p "$HANDOFFS"

log() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") [auto_ingest] $1" >> "$LOG"
}

files=("$SUMMARIES"/*.json)
if [[ ! -e "${files[0]}" ]]; then
  exit 0
fi

ingested=0

for file in "${files[@]}"; do
  session_id=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('session_id',''))")
  [[ -z "$session_id" ]] && continue

  project_id=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('project_id',''))")
  started=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('started_at',''))")
  ended=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('ended_at',''))")
  prompt_count=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('prompt_count',0))")
  reusable=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('reusable_prompt_count',0))")
  objective=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('objective') or '')")
  classifications=$(python3 -c "import json; d=json.load(open('$file')); print(', '.join(d.get('prompt_classifications',[])))")

  artifacts=$(python3 -c "
import json
d = json.load(open('$file'))
paths = list(dict.fromkeys(a['path'] for a in d.get('artifacts',[]) if a.get('path')))
print('\n'.join(f'- {p}' for p in paths) if paths else '- (none)')
")

  if [[ -n "$project_id" ]]; then
    project_name=$(sqlite3 "$DB" "SELECT name FROM projects WHERE id='$project_id';" 2>/dev/null || echo "")
  fi
  [[ -z "${project_name:-}" ]] && project_name="unknown"

  file_date=$(python3 -c "
from datetime import datetime
try: print(datetime.fromisoformat('$started').strftime('%Y-%m-%d'))
except: print('unknown-date')
" 2>/dev/null || echo "unknown-date")

  safe_project=$(echo "$project_name" | tr ' /' '-' | tr -cd '[:alnum:]-')
  short_id="${session_id:0:8}"
  note_file="$HANDOFFS/${file_date}-${safe_project}-${short_id}.md"

  reusable_flag=""
  [[ "$reusable" -gt 0 ]] && reusable_flag=" #review/prompts"

  cat > "$note_file" << NOTEEOF
---
type: session
project: $project_name
tool: claude-code
started: $started
ended: $ended
status: closed
objective: ${objective:-}
session_id: $session_id
prompt_count: $prompt_count
reusable_flagged: $reusable
tags:
  - ai/session
---

## Objective

${objective:-(not recorded)}

## Prompt Types

${classifications:-(none)}

## Artifacts Changed

$artifacts
NOTEEOF

  rm "$file"
  ingested=$((ingested + 1))
  log "ingested session $short_id → $(basename "$note_file")${reusable_flag}"
done

[[ $ingested -gt 0 ]] && log "$ingested session(s) ingested"
