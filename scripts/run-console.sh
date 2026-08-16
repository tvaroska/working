#!/usr/bin/env bash
# Processing-Agent Console BFF (SSE) — port 8010 (docs/lessons-learned.md §C2).
set -euo pipefail
cd "$(dirname "$0")/../agents"
export BRIDGE_CLOCK_MODE="${BRIDGE_CLOCK_MODE:-virtual}"
export BRIDGE_EXTRACTION_ENGINE="${BRIDGE_EXTRACTION_ENGINE:-fixture}"
export BRIDGE_SEAM_MODE="${BRIDGE_SEAM_MODE:-local}"
exec uv run uvicorn agents.address.console_server:app \
  --host "${CONSOLE_HOST:-127.0.0.1}" --port "${CONSOLE_PORT:-8010}"
