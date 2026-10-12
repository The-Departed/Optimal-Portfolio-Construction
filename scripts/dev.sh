#!/usr/bin/env bash
# Start the FastAPI backend (port 8000) and Vite frontend (port 5173) together.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(cd "$root/backend" && uv run uvicorn app.main:app --reload --port 8000) &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null' EXIT

cd "$root/frontend" && npm run dev
