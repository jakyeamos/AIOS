#!/usr/bin/env bash
# review_candidates.sh — show sessions flagged with reusable prompts
# Read-only. No actions. Use this to decide if any prompts belong in the library.
set -euo pipefail

DB=~/AIOS/data/aios.db

results=$(sqlite3 "$DB" "
  SELECT
    s.id,
    p.name,
    s.started_at,
    pu.prompt_text,
    pu.classification
  FROM prompts_used pu
  JOIN sessions s ON pu.session_id = s.id
  LEFT JOIN projects p ON s.project_id = p.id
  WHERE pu.reusable_candidate = 1
  ORDER BY s.started_at DESC
  LIMIT 50;
")

if [[ -z "$results" ]]; then
  echo "No reusable prompts flagged."
  exit 0
fi

echo ""
echo "Flagged reusable prompts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

current_session=""
while IFS='|' read -r session_id project started prompt_text classification; do
  if [[ "$session_id" != "$current_session" ]]; do
    display_date=$(python3 -c "
from datetime import datetime
try: print(datetime.fromisoformat('$started').strftime('%b %d %H:%M'))
except: print('$started')
" 2>/dev/null || echo "$started")
    echo ""
    echo "  ${project:-unknown} — $display_date  (${session_id:0:8}…)"
    current_session="$session_id"
  fi
  echo "  [$classification]"
  echo "$prompt_text" | fold -s -w 72 | sed 's/^/    /'
  echo ""
done <<< "$results"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
count=$(echo "$results" | wc -l | tr -d ' ')
echo "$count flagged prompt(s). Add to prompt library manually via QuickAdd → New Prompt."
