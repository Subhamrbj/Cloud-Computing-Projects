#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm ci && npm run build)
fi
.venv/bin/python -m scripts.setup_demo
echo 'See .demo-credentials.json for login. Start the simulator in another terminal as described in README.'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
