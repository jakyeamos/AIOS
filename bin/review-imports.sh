#!/usr/bin/env bash
# AIOS: review-imports.sh -- read-only batch review
set -euo pipefail

DB=~/AIOS/data/aios.db
SEP="----------------------------------------------------------------"

if [[ $# -eq 0 ]]; then
  echo "Usage: review-imports.sh --batch <id>"
  echo "       review-imports.sh --all-staged"
  exit 1
fi

MODE="$1"
BATCH_ID="${2:-}"

print_all_staged() {
  echo ""
  echo "All staged batches"
  echo "$SEP"
  sqlite3 "$DB" "
    SELECT batch_id,
           source,
           COUNT(*) AS total,
           SUM(CASE WHEN quality='deferred' THEN 1 ELSE 0 END) AS deferred,
           MIN(conversation_date) || ' -> ' || MAX(conversation_date) AS date_range
    FROM ai_history_imports
    WHERE status = 'staged'
    GROUP BY batch_id, source
    ORDER BY batch_id DESC;
  " | while IFS='|' read -r bid src total deferred range; do
    echo "  Batch $bid ($src): $total conversations, $deferred deferred - $range"
  done
  echo ""
}

print_batch_review() {
  echo ""
  echo "Batch: $BATCH_ID"
  echo "$SEP"

  sqlite3 "$DB" "
    SELECT
      source,
      COUNT(*) AS total,
      SUM(CASE WHEN quality='keep' THEN 1 ELSE 0 END) AS keep_count,
      SUM(CASE WHEN quality='deferred' THEN 1 ELSE 0 END) AS deferred_count,
      MIN(conversation_date) AS earliest,
      MAX(conversation_date) AS latest
    FROM ai_history_imports
    WHERE batch_id = '$BATCH_ID'
    GROUP BY source
    ORDER BY source;
  " | while IFS='|' read -r src total keep deferred earliest latest; do
    echo "  Source:   $src"
    echo "  Total:    $total"
    echo "  Keep:     $keep"
    echo "  Deferred: $deferred"
    echo "  Range:    $earliest -> $latest"
  done

  echo ""
  echo "Deferred conversations (thin individually, still included in pattern analysis):"
  deferred_lines=$(
    sqlite3 "$DB" "
      SELECT id, conversation_date, title
      FROM ai_history_imports
      WHERE batch_id = '$BATCH_ID' AND quality = 'deferred'
      ORDER BY conversation_date;
    "
  )
  if [[ -z "$deferred_lines" ]]; then
    echo "  (none)"
  else
    while IFS='|' read -r id date title; do
      echo "  $id [$date] ${title:0:60}"
    done <<< "$deferred_lines"
  fi

  echo ""
  echo "Keep conversations (use IDs with --exclude):"
  keep_lines=$(
    sqlite3 "$DB" "
      SELECT id, conversation_date, title
      FROM ai_history_imports
      WHERE batch_id = '$BATCH_ID' AND quality = 'keep'
      ORDER BY conversation_date
      LIMIT 20;
    "
  )
  if [[ -z "$keep_lines" ]]; then
    echo "  (none)"
  else
    while IFS='|' read -r id date title; do
      echo "  $id [$date] ${title:0:60}"
    done <<< "$keep_lines"
  fi

  echo ""
  echo "Aggregate topic candidates (3+ conversations, including deferred):"
  python3 - "$DB" "$BATCH_ID" <<'PY'
import json
import sqlite3
import sys

db_path, batch_id = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db_path)
rows = conn.execute(
    "SELECT topic_tags, quality FROM ai_history_imports WHERE batch_id = ?",
    (batch_id,),
).fetchall()

counts = {}
for payload, quality in rows:
    for tag in json.loads(payload or "[]"):
        entry = counts.setdefault(tag, {"total": 0, "keep": 0, "deferred": 0})
        entry["total"] += 1
        if quality == "deferred":
            entry["deferred"] += 1
        else:
            entry["keep"] += 1

matches = sorted(
    (
        (tag, detail["total"], detail["keep"], detail["deferred"])
        for tag, detail in counts.items()
        if detail["total"] >= 3
    ),
    key=lambda item: (-item[1], item[0]),
)[:15]

if not matches:
    print("  (none above threshold)")
else:
    for tag, total, keep_count, deferred_count in matches:
        print(f"  {tag} ({total} total: {keep_count} keep, {deferred_count} deferred)")
PY

  echo ""
  echo "Deferred-only topic candidates (3+ deferred conversations):"
  python3 - "$DB" "$BATCH_ID" <<'PY'
import json
import sqlite3
import sys

db_path, batch_id = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db_path)
rows = conn.execute(
    "SELECT topic_tags FROM ai_history_imports WHERE batch_id = ? AND quality = 'deferred'",
    (batch_id,),
).fetchall()

counts = {}
for (payload,) in rows:
    for tag in json.loads(payload or "[]"):
        counts[tag] = counts.get(tag, 0) + 1

matches = sorted(
    ((tag, count) for tag, count in counts.items() if count >= 3),
    key=lambda item: (-item[1], item[0]),
)[:15]

if not matches:
    print("  (none above threshold)")
else:
    for tag, count in matches:
        print(f"  {tag} ({count} deferred conversations)")
PY

  echo ""
  echo "$SEP"
  echo "To review:  review-imports.sh --batch $BATCH_ID"
  echo "To promote: promote-imports.sh --batch $BATCH_ID"
  echo "To include deferred: promote-imports.sh --batch $BATCH_ID --include-deferred"
  echo "To exclude: promote-imports.sh --batch $BATCH_ID --exclude id1,id2"
  echo ""
}

case "$MODE" in
  --all-staged)
    print_all_staged
    ;;
  --batch)
    if [[ -z "$BATCH_ID" ]]; then
      echo "Usage: review-imports.sh --batch <id>"
      exit 1
    fi
    print_batch_review
    ;;
  *)
    echo "Unknown mode: $MODE"
    exit 1
    ;;
esac
