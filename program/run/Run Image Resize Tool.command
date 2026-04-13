#!/bin/bash
# Launches the app from the project folder (parent of this file).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$(command -v python3 || true)"
if [[ -z "$PY" ]]; then
  osascript -e 'display dialog "Python 3 not found. Install from python.org/downloads" buttons {"OK"} default button 1' || true
  exit 1
fi
"$PY" -m pip install -q -r requirements.txt
exec "$PY" app.py
