#!/usr/bin/env bash
# Daily health check — queries aios.db and writes report to Obsidian dashboard
set -euo pipefail

DB=~/AIOS/data/aios.db
VAULT="${AIOS_VAULT_ROOT:-$HOME/projects/Vaults/Command-Center}"
REPORT="$VAULT/01 Dashboard/Health Check.md"
NOW=$(date "+%Y-%m-%d %H:%M")
WEEK_AGO=$(date -v-7d +"%Y-%m-%dT%H:%M:%SZ")
DAY_AGO=$(date -v-24H +"%Y-%m-%dT%H:%M:%SZ")

# --- Query aios.db ---
ACTIVE_PROJECTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM projects WHERE status='active';")
SESSIONS_WEEK=$(sqlite3 "$DB" "SELECT COUNT(*) FROM sessions WHERE started_at > '$WEEK_AGO';")
EVENTS_TODAY=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tool_events WHERE event_time > '$DAY_AGO';")
OPEN_BUGS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM bug_log WHERE status='open';")
REUSABLE_PROMPTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM prompts_used WHERE reusable_candidate=1 AND session_id IN (SELECT id FROM sessions WHERE started_at > '$WEEK_AGO');")
AI_IMPORTED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE status='promoted';" 2>/dev/null || echo 0)
AI_STAGED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE status='staged';" 2>/dev/null || echo 0)
AI_DEFERRED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE quality='deferred';" 2>/dev/null || echo 0)

RECENT_SESSIONS=$(sqlite3 "$DB" \
  "SELECT '- ' || p.name || ' (' || s.tool || ') ' || s.started_at
   FROM sessions s LEFT JOIN projects p ON s.project_id = p.id
   ORDER BY s.started_at DESC LIMIT 5;")

TOP_PROJECTS=$(sqlite3 "$DB" \
  "SELECT '- ' || p.name || ': ' || COUNT(s.id) || ' sessions'
   FROM projects p LEFT JOIN sessions s ON s.project_id = p.id
   WHERE p.status = 'active'
   GROUP BY p.id ORDER BY COUNT(s.id) DESC;")

OPEN_BUG_LIST=$(sqlite3 "$DB" \
  "SELECT '- [' || b.id || '] ' || p.name || ': ' || b.symptom
   FROM bug_log b LEFT JOIN projects p ON b.project_id = p.id
   WHERE b.status = 'open' ORDER BY b.created_at DESC LIMIT 10;")

CANDIDATES=$(find ~/AIOS/logs/summaries/ -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')

# --- Write report to vault ---
cat > "$REPORT" << EOF
---
type: dashboard
updated: ${NOW}
tags: [dashboard, health]
---

# System Health — ${NOW}

## At a Glance

| Metric | Value |
|--------|-------|
| Active projects | ${ACTIVE_PROJECTS} |
| Sessions (7 days) | ${SESSIONS_WEEK} |
| Tool events (24h) | ${EVENTS_TODAY} |
| Reusable prompts flagged (7d) | ${REUSABLE_PROMPTS} |
| Open bugs | ${OPEN_BUGS} |
| Session candidates in AIOS | ${CANDIDATES} |
| AI history imported | ${AI_IMPORTED} |
| AI history staged (pending review) | ${AI_STAGED} |
| AI history deferred | ${AI_DEFERRED} |

## Recent Sessions

${RECENT_SESSIONS:-_No sessions recorded yet_}

## Activity by Project

${TOP_PROJECTS:-_No session data yet_}

## Open Bugs

${OPEN_BUG_LIST:-_No open bugs_}

---
_Source: \`~/AIOS/data/aios.db\` · Candidates: \`~/AIOS/logs/summaries/\`_
EOF

# --- macOS notification ---
osascript -e "display notification \"${SESSIONS_WEEK} sessions · ${OPEN_BUGS} bugs · ${CANDIDATES} candidates\" with title \"AI OS Health Check\" subtitle \"${NOW}\""

echo "Health check complete → $REPORT"
