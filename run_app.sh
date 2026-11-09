#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Falta .venv. Sigue la instalación local del README.md."
  exit 1
fi
exec .venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false "$@"
