#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".env" ]]; then
  echo "ERROR: .env 파일이 없습니다."
  exit 1
fi

read_env() {
  local key="$1"
  python3 - "$key" <<'PY'
import sys

key = sys.argv[1]
value = ""
with open(".env", "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            value = v.strip().strip('"').strip("'")
            break
print(value, end="")
PY
}

VERTEX_RAG_CORPUS="$(read_env "VERTEX_RAG_CORPUS")"
DISCOVERY_ENGINE_ENGINE_ID="$(read_env "DISCOVERY_ENGINE_ENGINE_ID")"
REASONING_ENGINE_APP_NAME="$(read_env "REASONING_ENGINE_APP_NAME")"
REASONING_ENGINE_ID="$(read_env "REASONING_ENGINE_ID")"
REASONING_ENGINE_LOCATION="$(read_env "REASONING_ENGINE_LOCATION")"

if [[ -z "$VERTEX_RAG_CORPUS" ]]; then
  echo "ERROR: .env 의 VERTEX_RAG_CORPUS 값이 비어 있습니다."
  exit 1
fi

if [[ -z "$DISCOVERY_ENGINE_ENGINE_ID" ]]; then
  echo "ERROR: .env 의 DISCOVERY_ENGINE_ENGINE_ID 값이 비어 있습니다."
  exit 1
fi

gcloud builds submit --config=cloudbuild.yaml . \
  --substitutions="_VERTEX_RAG_CORPUS=${VERTEX_RAG_CORPUS},_DISCOVERY_ENGINE_ENGINE_ID=${DISCOVERY_ENGINE_ENGINE_ID},_REASONING_ENGINE_APP_NAME=${REASONING_ENGINE_APP_NAME},_REASONING_ENGINE_ID=${REASONING_ENGINE_ID},_REASONING_ENGINE_LOCATION=${REASONING_ENGINE_LOCATION}"

