#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ]; then
  npm install
fi

exec npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-5173}
