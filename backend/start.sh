#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
fi

if [ "${BACKEND_RUN_MIGRATIONS:-true}" = "true" ]; then
  python3 manage.py migrate
fi

exec python3 manage.py runserver "${BACKEND_HOST:-0.0.0.0}:${BACKEND_PORT:-8000}"
