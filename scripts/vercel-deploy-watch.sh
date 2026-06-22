#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-preview}"
TIMEOUT="${VERCEL_DEPLOY_TIMEOUT:-15m}"

case "$MODE" in
  preview)
    DEPLOY_CMD=(vercel deploy --yes)
    ;;
  prod)
    DEPLOY_CMD=(vercel deploy --prod --yes)
    ;;
  *)
    echo "ERROR: mode must be 'preview' or 'prod'." >&2
    exit 2
    ;;
esac

if ! command -v vercel >/dev/null 2>&1; then
  echo "ERROR: vercel CLI is not installed or not available on PATH." >&2
  exit 127
fi

if [ -n "${VERCEL_TOKEN:-}" ]; then
  DEPLOY_CMD+=(--token "$VERCEL_TOKEN")
fi

echo "Starting Vercel $MODE deployment..."

DEPLOY_URL="$("${DEPLOY_CMD[@]}")"

echo "Deployment URL: $DEPLOY_URL"
echo "Waiting for deployment to finish..."

INSPECT_CMD=(vercel inspect "$DEPLOY_URL" --logs --wait --timeout="$TIMEOUT")

if [ -n "${VERCEL_TOKEN:-}" ]; then
  INSPECT_CMD+=(--token "$VERCEL_TOKEN")
fi

"${INSPECT_CMD[@]}"

echo "Deployment succeeded: $DEPLOY_URL"
