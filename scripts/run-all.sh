#!/usr/bin/env bash
# Bring up the full Frontend-v1 demo stack: the four BFF servers (8010-8013) +
# the Bridge core (8000) in the background, then the theater Vite dev server
# (5173, proxying /console /ops /portal /timewarp to their BFF ports).
# Ctrl-C tears the whole group down.
set -euo pipefail
here="$(dirname "$0")"
root="$(cd "$here/.." && pwd)"

pids=()
cleanup() {
  echo "Shutting down demo stack..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

for svc in core console ops portal timewarp; do
  echo "Starting $svc..."
  bash "$here/run-$svc.sh" &
  pids+=("$!")
done

echo "Starting theater (Vite dev)..."
( cd "$root/frontend" && pnpm --filter theater dev ) &
pids+=("$!")

wait
