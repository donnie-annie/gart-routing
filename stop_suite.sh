#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -f start_controllers.py ]; then
  "$PYTHON_BIN" start_controllers.py stop || true
fi

if [ -d logs ]; then
  for pidfile in logs/*.pid; do
    [ -e "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  done
fi

echo "GART Routing Suite stopped"
