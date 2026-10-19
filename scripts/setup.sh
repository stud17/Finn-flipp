#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  finnflip_python=""
  for candidate in python3.14 python3.13 python3.12 python3 "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 12))' 2>/dev/null; then
      finnflip_python="$candidate"
      break
    fi
  done
  if [[ -z "$finnflip_python" ]]; then
    echo 'Installer Python 3.12 eller nyere før oppsett.' >&2
    exit 1
  fi
  "$finnflip_python" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.lock.txt
echo 'Oppsett ferdig. Start med: .venv/bin/python -m streamlit run app.py'
