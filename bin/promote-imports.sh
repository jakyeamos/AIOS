#!/usr/bin/env bash
# AIOS: promote-imports.sh -- move staged notes to the vault and scaffold batch synthesis.
set -euo pipefail

DB=~/AIOS/data/aios.db
READY=~/AIOS/staging/ai-history/ready
VAULT_ROOT="${AIOS_VAULT_ROOT:-$HOME/projects/Vaults/Command-Center}"
VAULT="$VAULT_ROOT/09 Archive/AI History"
NOW=$(date "+%Y-%m-%d %H:%M")
SEP="----------------------------------------------------------------"

source_dir_name() {
  case "$1" in
    chatgpt) echo "ChatGPT" ;;
    claude) echo "Claude" ;;
    codex) echo "Codex" ;;
    claude-code) echo "Claude Code" ;;
    *) echo "$1" ;;
  esac
}

make_file_suffix() {
  python3 -c "import hashlib, sys; raw = sys.argv[1] or sys.argv[2]; print(hashlib.sha256(raw.encode()).hexdigest()[:8])" "$1" "$2"
}

if [[ $# -eq 0 || "$1" != "--batch" || -z "${2:-}" ]]; then
  echo "Usage: promote-imports.sh --batch <id> [--exclude id1,id2] [--include-deferred]"
  exit 1
fi

BATCH_ID="$2"
EXCLUDE_IDS=""
INCLUDE_DEFERRED=0
shift 2
while [[ $# -gt 0 ]]; do
  case "$1" in
    --exclude)
      EXCLUDE_IDS="${2:-}"
      shift 2
      ;;
    --include-deferred)
      INCLUDE_DEFERRED=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

is_excluded() {
  local candidate="$1"
  if [[ -z "$EXCLUDE_IDS" ]]; then
    return 1
  fi
  [[ ",$EXCLUDE_IDS," == *",$candidate,"* ]]
}

echo ""
echo "Promoting batch: $BATCH_ID"
echo "Excluded ids:    ${EXCLUDE_IDS:-none}"
echo "Include deferred: $([[ "$INCLUDE_DEFERRED" -eq 1 ]] && echo yes || echo no)"
echo ""

promoted=0
skipped=0
errors=0

while IFS='|' read -r id source source_id quality slug conversation_date; do
  if is_excluded "$id"; then
    echo "  EXCLUDED  $id"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "$quality" == "deferred" && "$INCLUDE_DEFERRED" -ne 1 ]]; then
    skipped=$((skipped + 1))
    continue
  fi

  year="${conversation_date:0:4}"
  src_cap="$(source_dir_name "$source")"
  suffix="$(make_file_suffix "$source_id" "$id")"
  staged_file="$READY/$src_cap/$year/${conversation_date}-${slug}--${suffix}.md"

  if [[ ! -f "$staged_file" ]]; then
    echo "  MISSING   $id (staged file not found)"
    errors=$((errors + 1))
    continue
  fi

  dest_dir="$VAULT/$src_cap/$year"
  mkdir -p "$dest_dir"
  dest="$dest_dir/${conversation_date}-${slug}--${suffix}.md"
  cp "$staged_file" "$dest"

  sqlite3 "$DB" "
    UPDATE ai_history_imports
    SET status = 'promoted',
        vault_path = '$dest',
        promoted_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = '$id';
  "

  echo "  PROMOTED  $dest"
  promoted=$((promoted + 1))
done < <(
  sqlite3 "$DB" "
    SELECT id, source, source_id, quality, slug, conversation_date
    FROM ai_history_imports
    WHERE batch_id = '$BATCH_ID' AND status = 'staged'
    ORDER BY conversation_date;
  "
)

total_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id = '$BATCH_ID';")
total_promoted=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id = '$BATCH_ID' AND status = 'promoted';")
total_deferred=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE batch_id = '$BATCH_ID' AND quality = 'deferred';")
date_range=$(sqlite3 "$DB" "SELECT MIN(conversation_date) || ' -> ' || MAX(conversation_date) FROM ai_history_imports WHERE batch_id = '$BATCH_ID';")
source_val=$(sqlite3 "$DB" "
  SELECT CASE
    WHEN COUNT(DISTINCT source) = 1 THEN MIN(source)
    ELSE 'mixed'
  END
  FROM ai_history_imports
  WHERE batch_id = '$BATCH_ID';
")

batch_note="$VAULT/_Batch-${BATCH_ID}.md"
cat > "$batch_note" <<EOF
---
type: archive-batch
batch_id: ${BATCH_ID}
source: ${source_val}
date_range: "${date_range}"
conversation_count: ${total_count}
promoted_count: ${total_promoted}
deferred_count: ${total_deferred}
promoted_at: ${NOW}
---

# Batch ${BATCH_ID} - What This Archive Taught Me

<!-- Fill in after reviewing promoted conversations. This is where historic data becomes a brain. -->

## Thin Conversation Patterns

<!-- Review deferred clusters from review-imports.sh. Thin notes can still matter in aggregate. -->

- 

## Recurring Themes

-

## Repeated Blind Spots

-

## Prompts That Kept Reappearing

-

## Problems Solved Multiple Times

-

## Concepts That Probably Deserve a Page

<!-- Check entity candidates from review-imports.sh output -->
- [ ]
EOF

echo ""
echo "$SEP"
echo "Batch $BATCH_ID complete"
echo "  Promoted: $promoted"
echo "  Skipped:  $skipped (deferred or excluded)"
echo "  Errors:   $errors"
echo ""
echo "Batch synthesis note scaffolded: $batch_note"
echo ""
echo "Next steps:"
echo "  1. Open $batch_note and fill in the synthesis sections"
echo "  2. Add a link to this batch in 09 Archive/AI History/_Index.md"
if [[ "$INCLUDE_DEFERRED" -ne 1 ]]; then
  echo "  3. Review deferred clusters with review-imports.sh if you want aggregate patterns without promoting every thin note"
fi
