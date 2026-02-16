#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ] || [ "${FRONTEND_FORCE_INSTALL:-false}" = "true" ]; then
  if [ -f "package-lock.json" ]; then
    npm ci --no-audit --no-fund
  else
    npm install --no-audit --no-fund
  fi
fi

if [ "${FRONTEND_TYPECHECK_ON_START:-true}" = "true" ]; then
  npm run typecheck
fi

exec npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-5173}"
