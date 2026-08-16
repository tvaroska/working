#!/usr/bin/env bash
# Time-warp presenter control BFF (REST, no SSE — B4) — port 8013 (docs/lessons-learned.md §C2).
set -euo pipefail
cd "$(dirname "$0")/../agents"
export BRIDGE_CLOCK_MODE="${BRIDGE_CLOCK_MODE:-virtual}"
export BRIDGE_EXTRACTION_ENGINE="${BRIDGE_EXTRACTION_ENGINE:-fixture}"
export BRIDGE_SEAM_MODE="${BRIDGE_SEAM_MODE:-local}"
exec uv run uvicorn agents.address.timewarp_server:app \
  --host "${TIMEWARP_HOST:-127.0.0.1}" --port "${TIMEWARP_PORT:-8013}"
