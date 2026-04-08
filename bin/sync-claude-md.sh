#!/usr/bin/env bash
# sync-claude-md.sh — Detect and apply changes between source CLAUDE.md files and vault notes
# Usage: sync-claude-md.sh [--dry-run] [--project <name>]

set -euo pipefail

VAULT="$HOME/Vaults/Command-Center/06 Knowledge/Claude-Context"
DRY_RUN=false
FILTER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --project) FILTER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Map: vault_note => source_file
declare -A SOURCES=(
  ["global.md"]="$HOME/.claude/CLAUDE.md"
  ["amos-saas.md"]="$HOME/Projects/amos-saas/CLAUDE.md"
  ["bball.md"]="$HOME/Projects/Bball/CLAUDE.md"
  ["fantasy.md"]="$HOME/Projects/Fantasy/CLAUDE.md"
  ["remodelvision.md"]="$HOME/Projects/remodelvision/.claude/CLAUDE.md"
  ["soundscape.md"]="$HOME/Projects/soundscape-app/CLAUDE.md"
  ["amos-group.md"]="$HOME/Projects/amos-group/CLAUDE.md"
  ["dispatches.md"]="$HOME/Projects/dispatches-from-cyberspace/docs/meta/CLAUDE.md"
)

TODAY=$(date +%Y-%m-%d)
CHANGED=0
MISSING=0
SYNCED=0

echo "=== Claude-MD Sync $(date '+%Y-%m-%d %H:%M') ==="
echo ""

for NOTE in "${!SOURCES[@]}"; do
  SOURCE="${SOURCES[$NOTE]}"
  VAULT_NOTE="$VAULT/$NOTE"

  # Filter to specific project if requested
  if [[ -n "$FILTER" && "$NOTE" != *"$FILTER"* ]]; then
    continue
  fi

  # Check source exists
  if [[ ! -f "$SOURCE" ]]; then
    echo "  MISSING  $NOTE (source not found: $SOURCE)"
    ((MISSING++)) || true
    continue
  fi

  # Check vault note exists
  if [[ ! -f "$VAULT_NOTE" ]]; then
    echo "  NEW      $NOTE (vault note missing — run with --project to create)"
    ((MISSING++)) || true
    continue
  fi

  # Extract the body of the vault note (after frontmatter) for comparison
  # Compare source hash vs hash stored in vault note
  SOURCE_HASH=$(md5 -q "$SOURCE" 2>/dev/null || md5sum "$SOURCE" | cut -d' ' -f1)
  STORED_HASH=$(grep "^source_hash:" "$VAULT_NOTE" 2>/dev/null | awk '{print $2}' || echo "")

  if [[ "$SOURCE_HASH" == "$STORED_HASH" ]]; then
    echo "  OK       $NOTE"
    ((SYNCED++)) || true
    continue
  fi

  echo "  CHANGED  $NOTE"
  echo "           source: $SOURCE"

  if [[ "$DRY_RUN" == true ]]; then
    echo "           (dry-run: skipping update)"
    ((CHANGED++)) || true
    continue
  fi

  # Show diff of source vs what's in vault (skip frontmatter block)
  SOURCE_CONTENT=$(cat "$SOURCE")
  VAULT_BODY=$(awk '/^---$/{n++; if(n==2){found=1; next}} found{print}' "$VAULT_NOTE")

  echo ""
  echo "  --- Source changes ---"
  diff <(echo "$VAULT_BODY") <(echo "$SOURCE_CONTENT") | head -40 || true
  echo ""

  read -rp "  Update vault note? [y/N] " CONFIRM
  if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    # Rewrite frontmatter with updated hash and date, preserve existing fields
    FRONTMATTER=$(awk '/^---$/{n++; if(n==2){exit}} n==1{print}' "$VAULT_NOTE" | grep -v "^source_hash:" | grep -v "^last_synced:")

    {
      echo "---"
      echo "$FRONTMATTER"
      echo "last_synced: $TODAY"
      echo "source_hash: $SOURCE_HASH"
      echo "---"
      echo ""
      cat "$SOURCE"
    } > "$VAULT_NOTE"

    echo "  Updated $NOTE"
    ((CHANGED++)) || true
  else
    echo "  Skipped $NOTE"
  fi
done

echo ""
echo "=== Summary: $SYNCED up-to-date, $CHANGED changed, $MISSING missing ==="
