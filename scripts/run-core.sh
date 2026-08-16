#!/usr/bin/env bash
# Bridge core inbound A2A edge — port 8000 (docs/lessons-learned.md §C2).
# Run from agents/ (bridge is an editable dep there); create_app is a factory.
set -euo pipefail
cd "$(dirname "$0")/../agents"
export BRIDGE_CLOCK_MODE="${BRIDGE_CLOCK_MODE:-virtual}"
export BRIDGE_EXTRACTION_ENGINE="${BRIDGE_EXTRACTION_ENGINE:-fixture}"
export BRIDGE_SEAM_MODE="${BRIDGE_SEAM_MODE:-local}"
exec uv run uvicorn --factory bridge.edges.a2a.app:create_app \
  --host "${CORE_HOST:-127.0.0.1}" --port "${CORE_PORT:-8000}"
