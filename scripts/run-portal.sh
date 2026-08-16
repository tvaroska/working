#!/usr/bin/env bash
# End-user / Provider Portal BFF (REST, A2UI Path-B) — port 8012 (docs/lessons-learned.md §C2).
set -euo pipefail
cd "$(dirname "$0")/../agents"
export BRIDGE_CLOCK_MODE="${BRIDGE_CLOCK_MODE:-virtual}"
export BRIDGE_EXTRACTION_ENGINE="${BRIDGE_EXTRACTION_ENGINE:-fixture}"
export BRIDGE_SEAM_MODE="${BRIDGE_SEAM_MODE:-local}"
exec uv run uvicorn agents.address.portal_server:app \
  --host "${PORTAL_HOST:-127.0.0.1}" --port "${PORTAL_PORT:-8012}"
