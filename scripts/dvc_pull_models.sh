#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DAGSHUB_ACCESS_KEY_ID:-}" || -z "${DAGSHUB_SECRET_ACCESS_KEY:-}" ]]; then
  echo "DAGSHUB_ACCESS_KEY_ID and DAGSHUB_SECRET_ACCESS_KEY must be set." >&2
  echo "Create keys in DagsHub: Repo -> Settings -> Access Keys." >&2
  exit 1
fi

dvc remote modify --local origin access_key_id "${DAGSHUB_ACCESS_KEY_ID}"
dvc remote modify --local origin secret_access_key "${DAGSHUB_SECRET_ACCESS_KEY}"

echo "Pulling models from DVC remote..."
dvc pull models.dvc

if [[ ! -d "models/emotion_classifier" ]]; then
  echo "Expected models/emotion_classifier after dvc pull, but directory is missing." >&2
  exit 1
fi

echo "Model artifacts are ready at models/emotion_classifier"
