#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm ci && npm run build)
fi
.venv/bin/python -m scripts.bootstrap
echo 'Open http://127.0.0.1:8000 and choose Try interactive demo or Create an account. No separate simulator needed.'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
