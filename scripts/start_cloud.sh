#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Kjør bash scripts/setup.sh først.' >&2
  exit 1
fi
# Bind to the cloud task's interface so its port preview can reach Streamlit.
# This is a task preview, not a deployment with authentication.
exec .venv/bin/python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
