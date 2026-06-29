# MLflow Storage Layout

This project uses MLflow with two storage layers:

- Postgres stores metadata: experiments, runs, params, metrics, tags, and model registry records.
- MinIO stores large artifacts: model files, tokenizer files, checkpoints, JSON reports, and DVC metadata copies.

## Services

Configured in `docker-compose.yml`:

- `postgres`: MLflow backend store.
- `minio`: S3-compatible artifact storage.
- `mlflow`: Tracking Server that connects Postgres and MinIO.

Main config files:

- `.env`: local secrets and endpoints.
- `.env.example`: example environment variables.
- `configs/mlflow.yaml`: tracking URI, experiment name, artifact S3 path, and registry settings.

## Postgres

Postgres is the MLflow backend store. It does not store the model binary itself.

Important tables:

- `experiments`: MLflow experiments, for example `lyubava-emotion-classifier`.
- `runs`: one row per training run.
- `params`: run parameters such as `model_name`, `learning_rate`, `train_rows`.
- `metrics`: numeric metrics such as `eval_loss`, `eval_macro_f1`, `train_loss`.
- `tags`: run tags, including `dataset.dvc_hash`.
- `registered_models`: model names in the MLflow Model Registry.
- `model_versions`: model versions such as `v1`, `v2`.
- `model_version_tags`: tags attached to model versions, including DVC dataset hash.
- `registered_model_aliases`: aliases such as `champion -> version 2`.
- `alembic_version`: MLflow database migration version.

Other tables are created by MLflow for optional features such as evaluation datasets, traces, scorers, review queues, webhooks, serving endpoints, and logged-model internals. They are normal for MLflow 3.x even if the project does not actively use all of them.

## MinIO

MinIO is the artifact store. It contains the heavy files referenced by MLflow metadata.

Bucket:

```text
lyubava-mlflow-artifacts
```

Typical objects:

- `.../artifacts/data/data.dvc`
- `.../artifacts/data/data.dvc.json`
- `.../artifacts/data/data_stats.json`
- `.../artifacts/metadata/label_metadata.json`
- `.../artifacts/metrics/validation_metrics.json`
- `.../artifacts/training_output/checkpoint-*/model.safetensors`
- `.../artifacts/training_output/checkpoint-*/config.json`
- `.../artifacts/training_output/checkpoint-*/tokenizer.json`

In short:

```text
Postgres = catalog, history, metrics, params, tags, registry
MinIO    = files, model artifacts, reports, checkpoints
DVC      = dataset version source of truth
```

## DVC Link

Training reads the dataset hash from `data.dvc` and writes it to MLflow:

- run tag: `dataset.dvc_hash`
- run tag: `dataset.version`
- model version tag: `dataset.dvc_hash`

This makes each registered model version traceable to the exact dataset state used for training.

## Smoke Test

Quick CPU run for checking that tracking, artifacts, and registry work:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:PYTHONIOENCODING='utf-8'
$env:CUDA_VISIBLE_DEVICES=''

.\.venv\Scripts\python.exe src\lyubava\models\train.py `
  --output-dir models\mlflow_smoke_test `
  --max-length 16 `
  --train-batch-size 2 `
  --eval-batch-size 2 `
  --num-train-epochs 1 `
  --max-train-samples 4 `
  --max-eval-samples 4 `
  --use-cpu
```

Expected result:

- a new MLflow run appears in `http://localhost:5000`;
- metrics are visible in the run;
- artifacts are stored in MinIO;
- a new version appears under `lyubava-emotion-classifier`;
- alias `champion` points to the newest registered version.
