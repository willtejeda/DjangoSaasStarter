#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  trap - INT TERM EXIT
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

if [ "${START_SKIP_BACKEND:-false}" != "true" ]; then
  bash "$ROOT_DIR/backend/start.sh" &
  BACKEND_PID=$!
fi

if [ "${START_SKIP_FRONTEND:-false}" != "true" ]; then
  bash "$ROOT_DIR/frontend/start.sh" &
  FRONTEND_PID=$!
fi

if [ -z "${BACKEND_PID:-}" ] && [ -z "${FRONTEND_PID:-}" ]; then
  echo "Nothing to start. Set START_SKIP_BACKEND/START_SKIP_FRONTEND to false."
  exit 1
fi

EXIT_CODE=0
while true; do
  if [ -n "${BACKEND_PID:-}" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID" || EXIT_CODE=$?
    break
  fi

  if [ -n "${FRONTEND_PID:-}" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    wait "$FRONTEND_PID" || EXIT_CODE=$?
    break
  fi

  sleep 1
done

cleanup
exit "$EXIT_CODE"
