#!/bin/zsh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SEED_BASE=42
CONTEXT_LENGTH=8192
TMP_RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rtca-clean-ttft.XXXXXX")"
SERVER_LOG="$TMP_RUN_DIR/ollama-serve.log"
SERVER_PID=""
OLLAMA_APP_WAS_RUNNING=0

cleanup() {
  local status=$?
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  if (( OLLAMA_APP_WAS_RUNNING )); then
    open -a Ollama >/dev/null 2>&1 || true
  fi
  if (( status != 0 )); then
    echo
    echo "Clean TTFT replication failed (exit $status)."
    echo "Temporary Ollama log: $SERVER_LOG"
  fi
  exit $status
}
trap cleanup EXIT INT TERM

echo "== Update repository =="
git pull --ff-only

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: repository is not clean after pull. Commit/stash unrelated changes first." >&2
  git status --short >&2
  exit 1
fi

command -v ollama >/dev/null || { echo "ERROR: ollama is not on PATH" >&2; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 is required" >&2; exit 1; }
python3 -c 'import httpx' >/dev/null 2>&1 || {
  echo "ERROR: Python dependency httpx is missing. Run: python3 -m pip install -r requirements.txt" >&2
  exit 1
}

if pgrep -x Ollama >/dev/null 2>&1; then
  OLLAMA_APP_WAS_RUNNING=1
fi

echo "== Stop existing Ollama processes =="
osascript -e 'quit app "Ollama"' >/dev/null 2>&1 || true
pkill -f '[o]llama serve' >/dev/null 2>&1 || true

# Wait for the old API endpoint to disappear so we cannot accidentally benchmark
# against a stale server from another binary.
for _ in {1..20}; do
  if ! curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo "ERROR: an Ollama server is still listening on 127.0.0.1:11434" >&2
  exit 1
fi

echo "== Start dedicated Ollama server (context=$CONTEXT_LENGTH) =="
OLLAMA_CONTEXT_LENGTH="$CONTEXT_LENGTH" ollama serve >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in {1..60}; do
  if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  echo "ERROR: dedicated Ollama server did not become ready" >&2
  exit 1
fi

CLIENT_RAW="$(ollama --version 2>&1)"
SERVER_RAW="$(curl -fsS http://127.0.0.1:11434/api/version)"
CLIENT_VERSION="$(printf '%s\n' "$CLIENT_RAW" | sed -nE 's/^ollama version is ([^ ]+).*/\1/p' | head -1)"
SERVER_VERSION="$(printf '%s' "$SERVER_RAW" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')"

if [[ -z "$CLIENT_VERSION" || -z "$SERVER_VERSION" ]]; then
  echo "ERROR: could not parse Ollama versions" >&2
  echo "client: $CLIENT_RAW" >&2
  echo "server: $SERVER_RAW" >&2
  exit 1
fi

echo "client version: $CLIENT_VERSION"
echo "server version: $SERVER_VERSION"
if [[ "$CLIENT_VERSION" != "$SERVER_VERSION" ]]; then
  echo "ERROR: clean run requires matching client/server versions" >&2
  exit 1
fi

# Confirm the dedicated server owns the expected process and show its allocation
# after the runner has loaded each model. The runner itself records the exact
# model identifiers, warmups and request timing.
OUTPUT_DIR="evaluation/results/rtca-experiment-b2-ttft-clean-$(date -u +%Y%m%dT%H%M%SZ)"

echo "== Run clean TTFT replication =="
echo "output: $OUTPUT_DIR"
echo "seed base: $SEED_BASE"
echo "context length: $CONTEXT_LENGTH"
python3 -m scripts.run_rtca_ttft_clean \
  --output-dir "$OUTPUT_DIR" \
  --seed-base "$SEED_BASE" \
  --context-length "$CONTEXT_LENGTH" \
  --ollama-server-version "$SERVER_VERSION" \
  --ollama-client-version "$CLIENT_VERSION"

echo
echo "== Result summary =="
cat "$OUTPUT_DIR/ttft-summary.md"

echo
echo "== Runtime process snapshot =="
ollama ps || true

echo
echo "== Validate result provenance =="
python3 - "$OUTPUT_DIR" "$CLIENT_VERSION" "$CONTEXT_LENGTH" "$SEED_BASE" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
version = sys.argv[2]
context = int(sys.argv[3])
seed = int(sys.argv[4])
manifest = json.loads((root / "manifest.json").read_text())
summary = json.loads((root / "ttft-summary.json").read_text())
rep = manifest.get("reproducibility", {})
assert manifest.get("status") == "complete"
assert manifest.get("planned_primary_decisions") == 75
assert rep.get("clean_replication") is True
assert rep.get("ollama_server_version") == version
assert rep.get("ollama_client_version") == version
assert rep.get("versions_matched") is True
assert rep.get("context_length") == context
assert rep.get("seed_base") == seed
assert len(summary.get("by_model", {})) == 3
for model_id, values in summary["by_model"].items():
    assert values.get("n") == 25, (model_id, values.get("n"))
print("provenance validation: PASS")
PY

# Only the newly generated evidence bundle is committed. The script itself and
# clean-run wrapper arrived via the initial git pull and should already be clean.
git add -- "$OUTPUT_DIR"

CHANGED="$(git diff --cached --name-only)"
if [[ -z "$CHANGED" ]]; then
  echo "ERROR: no result files were staged" >&2
  exit 1
fi
if print -r -- "$CHANGED" | grep -v "^${OUTPUT_DIR}/" >/dev/null; then
  echo "ERROR: staged changes include files outside the new result directory" >&2
  git diff --cached --name-only >&2
  exit 1
fi

echo
echo "== Commit and push evidence =="
git commit -m "Store clean RTCA TTFT replication"
git push

SHA="$(git rev-parse HEAD)"
echo
echo "=============================================="
echo "CLEAN TTFT REPLICATION COMPLETE"
echo "RESULT_DIR: $OUTPUT_DIR"
echo "SHA TO GIVE CHATGPT: $SHA"
echo "=============================================="

trap - EXIT INT TERM
if [[ -n "$SERVER_PID" ]]; then
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" >/dev/null 2>&1 || true
fi
if (( OLLAMA_APP_WAS_RUNNING )); then
  open -a Ollama >/dev/null 2>&1 || true
fi
rm -rf "$TMP_RUN_DIR"
