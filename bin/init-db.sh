#!/usr/bin/env bash
# Initialize the AIOS SQLite database
# Usage: ~/AIOS/bin/init-db.sh

set -euo pipefail

DB="$HOME/AIOS/data/aios.db"
SCHEMA="$HOME/AIOS/data/schema.sql"

if [[ -f "$DB" ]]; then
  echo "Database already exists at $DB"
  echo "Run with --force to reinitialize (DESTROYS ALL DATA):"
  echo "  $0 --force"
  exit 0
fi

if [[ "${1:-}" == "--force" ]]; then
  echo "Removing existing database..."
  rm -f "$DB"
fi

echo "Creating $DB..."
sqlite3 "$DB" < "$SCHEMA"
echo "Done. Tables created:"
sqlite3 "$DB" ".tables"

echo "Creating staging directories..."
mkdir -p "$HOME/AIOS/staging/session-handoffs"
mkdir -p "$HOME/AIOS/staging/pattern-candidates"
mkdir -p "$HOME/AIOS/staging/knowledge-drafts"
mkdir -p "$HOME/AIOS/logs/closed"
mkdir -p "$HOME/AIOS/logs/summaries"
echo "Staging dirs ready."
