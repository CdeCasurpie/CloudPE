#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
if [ ! -f frontend/dist/index.html ]; then
  echo "Falta compilar la interfaz: cd frontend && npm ci && npm run build"
  exit 1
fi
exec .venv/bin/python -m uvicorn cloudlab.web:app --host 127.0.0.1 --port 8765 "$@"
