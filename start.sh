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

if [[ "${1:-}" == "--voice-doctor" ]]; then
  exec python scripts/voice_doctor.py
fi

if [[ "${1:-}" == "--routing-check" ]]; then
  shift
  exec python scripts/check_routing.py "$@"
fi

# Startup deliberately loads the conversational model, the router, the resident
# recogniser and the speech voice before serving anything. `--reload` pays that
# orchestration again on every saved file and can drop the resident processes
# under someone who is mid-conversation, so it is opt-in rather than default.
if [[ "${1:-}" == "--dev" ]]; then
  exec uvicorn app:app --reload --host 127.0.0.1 --port "${PORT:-8765}"
fi

exec uvicorn app:app --host 127.0.0.1 --port "${PORT:-8765}"
