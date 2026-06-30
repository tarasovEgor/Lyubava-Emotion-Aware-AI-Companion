#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${DAGSHUB_ACCESS_KEY_ID:-}" && -n "${DAGSHUB_SECRET_ACCESS_KEY:-}" ]]; then
  endpoint_url="${DVC_S3_ENDPOINT_URL:-https://dagshub.com/ekurmanaliev50/Lyubava.s3}"
  access_key_id="${DAGSHUB_ACCESS_KEY_ID}"
  secret_access_key="${DAGSHUB_SECRET_ACCESS_KEY}"
else
  if [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    endpoint_url="${DVC_S3_ENDPOINT_URL:-http://localhost:9000}"
    access_key_id="${AWS_ACCESS_KEY_ID}"
    secret_access_key="${AWS_SECRET_ACCESS_KEY}"
  else
    echo "Set either DAGSHUB_ACCESS_KEY_ID/DAGSHUB_SECRET_ACCESS_KEY or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY." >&2
    echo "For minikube defaults use AWS creds: minioadmin / minioadmin123" >&2
    exit 1
  fi
fi

dvc remote modify --local origin endpointurl "${endpoint_url}"
dvc remote modify --local origin access_key_id "${access_key_id}"
dvc remote modify --local origin secret_access_key "${secret_access_key}"

echo "Pulling models from DVC remote (endpoint: ${endpoint_url})..."
dvc pull models.dvc

if [[ ! -d "models/emotion_classifier" ]]; then
  echo "Expected models/emotion_classifier after dvc pull, but directory is missing." >&2
  exit 1
fi

echo "Model artifacts are ready at models/emotion_classifier"
