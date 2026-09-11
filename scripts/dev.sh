#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/ first.'; exit 1; }
command -v npm >/dev/null || { echo 'Install Node.js 22.12+ and npm first.'; exit 1; }
uv sync --frozen --python 3.12
npm --prefix frontend ci
uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
api_pid=$!
cleanup() { kill "$api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
npm --prefix frontend run dev
