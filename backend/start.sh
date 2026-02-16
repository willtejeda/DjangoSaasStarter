#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
fi

python3 manage.py migrate
exec python3 manage.py runserver 0.0.0.0:${BACKEND_PORT:-8000}
