#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install -q -r requirements.txt

if [[ "${1:-}" == "--setup-only" ]]; then
  exit 0
fi

exec uvicorn app:app --reload --host 127.0.0.1 --port "${PORT:-8765}"
