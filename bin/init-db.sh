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
