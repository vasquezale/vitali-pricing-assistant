#!/usr/bin/env bash

set -euo pipefail

PORT="${PORT:-8501}"
HOST="${HOST:-127.0.0.1}"

if lsof -i "tcp:${PORT}" >/dev/null 2>&1; then
  ORIGINAL_PORT="${PORT}"
  while lsof -i "tcp:${PORT}" >/dev/null 2>&1; do
    PORT="$((PORT + 1))"
  done
  echo "Puerto ${ORIGINAL_PORT} ocupado. Usando ${PORT}."
fi

uv run python -m streamlit run src/vitali/dashboard/app.py \
  --server.headless false \
  --server.address "${HOST}" \
  --server.port "${PORT}" \
  --browser.gatherUsageStats false
