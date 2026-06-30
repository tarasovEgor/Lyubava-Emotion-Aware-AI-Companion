#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
  echo "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set (MinIO credentials)." >&2
  echo "Also set DVC_S3_ENDPOINT_URL to your MinIO API endpoint." >&2
  exit 1
fi

run_dvc() {
  if [[ -x ".venv/bin/dvc" ]]; then
    .venv/bin/dvc "$@"
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    uv run --no-sync dvc "$@"
    return
  fi

  dvc "$@"
}

endpoint_url="${DVC_S3_ENDPOINT_URL:-http://localhost:9000}"

run_dvc remote modify --local origin endpointurl "${endpoint_url}"
run_dvc remote modify --local origin access_key_id "${AWS_ACCESS_KEY_ID}"
run_dvc remote modify --local origin secret_access_key "${AWS_SECRET_ACCESS_KEY}"

echo "Pulling models from DVC remote (MinIO endpoint: ${endpoint_url})..."
run_dvc pull models.dvc

if [[ ! -d "models/emotion_classifier" ]]; then
  echo "Expected models/emotion_classifier after dvc pull, but directory is missing." >&2
  exit 1
fi

echo "Model artifacts are ready at models/emotion_classifier"
