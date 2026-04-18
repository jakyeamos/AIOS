#!/usr/bin/env zsh
# takeout-ingest.sh — Google Takeout → Obsidian vault pipeline
#
# Usage:
#   takeout-ingest.sh <takeout.zip | takeout-dir>
#   takeout-ingest.sh <takeout.zip> --service drive
#   takeout-ingest.sh <takeout.zip> --vault ~/projects/Vaults/Command-Center
#
# Handles both zipped exports and pre-extracted directories.
# Writes processed markdown to vault/Personal-Corpus/ and leaves raw data untouched.

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
DEFAULT_VAULT="${AIOS_VAULT_ROOT:-$HOME/projects/Vaults/Command-Center}"
VAULT="${VAULT:-$DEFAULT_VAULT}"
WORK_DIR="/tmp/takeout-ingest-$$"
SERVICE="all"
INPUT=""

cleanup() { [[ -d "$WORK_DIR" ]] && rm -rf "$WORK_DIR"; }
trap cleanup EXIT

usage() {
    echo "Usage: takeout-ingest.sh <takeout.zip | dir> [--vault PATH] [--service all|drive|chat|calendar|activity|notebooklm|voice]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault)   VAULT="$2";   shift 2 ;;
        --service) SERVICE="$2"; shift 2 ;;
        --help|-h) usage ;;
        *)         INPUT="$1";   shift ;;
    esac
done

[[ -z "$INPUT" ]] && usage

# ── Resolve takeout directory ─────────────────────────────────────────────────

if [[ -f "$INPUT" && "$INPUT" == *.zip ]]; then
    echo "Extracting $(basename "$INPUT")..."
    mkdir -p "$WORK_DIR"
    unzip -q "$INPUT" -d "$WORK_DIR"
    TAKEOUT_DIR=$(find "$WORK_DIR" -maxdepth 2 -name "Takeout" -type d 2>/dev/null | head -1)
    [[ -z "$TAKEOUT_DIR" ]] && TAKEOUT_DIR="$WORK_DIR"
elif [[ -d "$INPUT" ]]; then
    TAKEOUT_DIR="$INPUT"
else
    echo "Error: '$INPUT' is not a .zip file or directory"
    exit 1
fi

# ── Dependencies ──────────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

if ! command -v pandoc &>/dev/null; then
    echo "pandoc not found — installing via Homebrew..."
    brew install pandoc
fi

python3 -c "import icalendar" 2>/dev/null || pip3 install icalendar -q

# ── Run processor ─────────────────────────────────────────────────────────────

python3 "$SCRIPT_DIR/takeout-process.py" \
    --takeout "$TAKEOUT_DIR" \
    --vault   "$VAULT" \
    --service "$SERVICE"

echo ""
echo "Corpus: $VAULT/Personal-Corpus/"
echo "The raw export can now be deleted."
