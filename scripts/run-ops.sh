#!/usr/bin/env bash
# Servicer Ops Dashboard BFF (SSE) — port 8011 (docs/lessons-learned.md §C2).
set -euo pipefail
cd "$(dirname "$0")/../agents"
export BRIDGE_CLOCK_MODE="${BRIDGE_CLOCK_MODE:-virtual}"
export BRIDGE_EXTRACTION_ENGINE="${BRIDGE_EXTRACTION_ENGINE:-fixture}"
export BRIDGE_SEAM_MODE="${BRIDGE_SEAM_MODE:-local}"
exec uv run uvicorn agents.address.ops_server:app \
  --host "${OPS_HOST:-127.0.0.1}" --port "${OPS_PORT:-8011}"
