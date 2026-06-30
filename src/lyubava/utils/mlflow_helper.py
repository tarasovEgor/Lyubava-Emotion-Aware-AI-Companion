from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
import mlflow
import yaml
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MLFLOW_CONFIG: dict[str, Any] = {
    "experiment_name": "lyubava-emotion-classifier",
    "tracking_uri": "file:./mlruns",
    "artifact_location": None,
    "run": {
        "name_prefix": "emotion-classifier",
        "tags": {
            "project": "Lyubava-Emotion-Aware-AI-Companion",
            "task": "emotion-classification",
            "framework": "transformers",
        },
    },
    "artifacts": {
        "model_artifact_path": "model",
        "log_output_dir": True,
        "log_data_stats": True,
        "log_dvc_file": True,
    },
    "s3": {
        "enabled": False,
        "endpoint_url_env_var": "MLFLOW_S3_ENDPOINT_URL",
        "bucket_auto_create": True,
        "required_env_vars": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
    },
    "model_registry": {
        "enabled": True,
        "registered_model_name": "lyubava-emotion-classifier",
        "await_registration_for": 300,
        "stage": None,
        "aliases": {"champion": True},
        "tags": {
            "domain": "nlp",
            "model_type": "sequence-classification",
            "dataset": "empatheticdialogues",
        },
    },
}


@dataclass(frozen=True)
class MLflowConfig:
    experiment_name: str
    tracking_uri: str
    artifact_location: str | None = None
    run_name_prefix: str = "emotion-classifier"
    run_tags: dict[str, str] = field(default_factory=dict)
    model_artifact_path: str = "model"
    log_output_dir: bool = True
    log_data_stats: bool = True
    log_dvc_file: bool = True
    s3_enabled: bool = False
    s3_endpoint_url_env_var: str = "MLFLOW_S3_ENDPOINT_URL"
    s3_bucket_auto_create: bool = True
    s3_required_env_vars: tuple[str, ...] = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    )
    registry_enabled: bool = True
    registered_model_name: str = "lyubava-emotion-classifier"
    await_registration_for: int = 300
    registry_stage: str | None = None
    registry_aliases: dict[str, bool] = field(default_factory=dict)
    registry_tags: dict[str, str] = field(default_factory=dict)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def _extract_bucket_from_uri(uri: str | None) -> str | None:
    if not uri or not uri.startswith("s3://"):
        return None
    parsed = urlparse(uri)
    return parsed.netloc or None


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


def ensure_s3_bucket(
    artifact_location: str | None,
    endpoint_url: str | None = None,
) -> str | None:
    bucket_name = _extract_bucket_from_uri(artifact_location)
    if not bucket_name:
        return None

    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url or os.getenv("MLFLOW_S3_ENDPOINT_URL"),
    )

    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise RuntimeError(
                f"Unable to check existence of S3 bucket '{bucket_name}'."
            ) from exc

        region = (
            os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION") or "us-east-1"
        )
        create_kwargs: dict[str, Any] = {"Bucket": bucket_name}
        if region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": region,
            }
        s3_client.create_bucket(**create_kwargs)

    return bucket_name


def get_dvc_data_output(
    data_dvc_path: Path = Path("data.dvc"),
) -> dict[str, Any] | None:
    if not data_dvc_path.exists():
        return None

    with data_dvc_path.open("r", encoding="utf-8") as f:
        dvc_metadata = yaml.safe_load(f) or {}

    for output in dvc_metadata.get("outs", []):
        if output.get("path") == "data" and output.get("md5"):
            return output

    outputs = dvc_metadata.get("outs") or []
    return outputs[0] if outputs else None


def get_dvc_data_hash(data_dvc_path: Path = Path("data.dvc")) -> str | None:
    output = get_dvc_data_output(data_dvc_path)
    md5_hash = output.get("md5") if output else None
    return str(md5_hash) if md5_hash else None


def set_dataset_tags_from_dvc(data_dvc_path: Path = Path("data.dvc")) -> str | None:
    output = get_dvc_data_output(data_dvc_path)
    dvc_hash = str(output.get("md5")) if output and output.get("md5") else None
    if dvc_hash:
        mlflow.set_tags(
            {
                "dataset.version": dvc_hash,
                "dataset.dvc_hash": dvc_hash,
                "dataset.dvc_file": str(data_dvc_path),
                "dataset.path": str(output.get("path", "data")),
                "dataset.hash_type": str(output.get("hash", "md5")),
                "dataset.size": str(output.get("size", "")),
                "dataset.nfiles": str(output.get("nfiles", "")),
            }
        )
    return dvc_hash


def load_mlflow_config(
    config_path: Path | str = Path("configs/mlflow.yaml"),
) -> MLflowConfig:
    path = Path(config_path)
    raw_config: dict[str, Any] = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

    raw_config = _expand_env(raw_config)
    config = _deep_merge(DEFAULT_MLFLOW_CONFIG, raw_config)
    run_config = config.get("run", {})
    artifacts_config = config.get("artifacts", {})
    s3_config = config.get("s3", {})
    registry_config = config.get("model_registry", {})

    tracking_uri = str(config["tracking_uri"])
    if "$" in tracking_uri:
        tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI", DEFAULT_MLFLOW_CONFIG["tracking_uri"]
        )

    return MLflowConfig(
        experiment_name=str(config["experiment_name"]),
        tracking_uri=tracking_uri,
        artifact_location=config.get("artifact_location"),
        run_name_prefix=str(run_config.get("name_prefix", "emotion-classifier")),
        run_tags={str(k): str(v) for k, v in run_config.get("tags", {}).items()},
        model_artifact_path=str(artifacts_config.get("model_artifact_path", "model")),
        log_output_dir=bool(artifacts_config.get("log_output_dir", True)),
        log_data_stats=bool(artifacts_config.get("log_data_stats", True)),
        log_dvc_file=bool(artifacts_config.get("log_dvc_file", True)),
        s3_enabled=bool(s3_config.get("enabled", False)),
        s3_endpoint_url_env_var=str(
            s3_config.get("endpoint_url_env_var", "MLFLOW_S3_ENDPOINT_URL")
        ),
        s3_bucket_auto_create=bool(s3_config.get("bucket_auto_create", True)),
        s3_required_env_vars=tuple(
            str(env_var) for env_var in s3_config.get("required_env_vars", [])
        ),
        registry_enabled=bool(registry_config.get("enabled", True)),
        registered_model_name=str(
            registry_config.get("registered_model_name", "lyubava-emotion-classifier")
        ),
        await_registration_for=int(registry_config.get("await_registration_for", 300)),
        registry_stage=registry_config.get("stage"),
        registry_aliases={
            str(k): bool(v) for k, v in registry_config.get("aliases", {}).items()
        },
        registry_tags={
            str(k): str(v) for k, v in registry_config.get("tags", {}).items()
        },
    )


def validate_s3_environment(config: MLflowConfig) -> None:
    uses_s3_artifacts = bool(
        config.artifact_location and config.artifact_location.startswith("s3://")
    )
    if not config.s3_enabled and not uses_s3_artifacts:
        return

    missing_env_vars = [
        env_var for env_var in config.s3_required_env_vars if not os.getenv(env_var)
    ]
    if missing_env_vars:
        raise RuntimeError(
            "MLflow S3 artifact storage is enabled, but required environment "
            f"variables are missing: {', '.join(missing_env_vars)}"
        )

    if boto3.Session().get_credentials() is None:
        raise RuntimeError(
            "MLflow S3 artifact storage is enabled, but boto3 could not resolve "
            "AWS credentials from the current environment."
        )


def initialize_mlflow(
    config_path: Path | str = Path("configs/mlflow.yaml"),
) -> MLflowConfig:
    config = load_mlflow_config(config_path)
    validate_s3_environment(config)

    if config.s3_bucket_auto_create and (
        config.s3_enabled
        or (config.artifact_location and config.artifact_location.startswith("s3://"))
    ):
        ensure_s3_bucket(
            artifact_location=config.artifact_location,
            endpoint_url=os.getenv(config.s3_endpoint_url_env_var),
        )

    mlflow.set_tracking_uri(config.tracking_uri)
    mlflow.set_registry_uri(config.tracking_uri)
    experiment = mlflow.get_experiment_by_name(config.experiment_name)
    if experiment is None:
        mlflow.create_experiment(
            name=config.experiment_name,
            artifact_location=config.artifact_location,
        )
    mlflow.set_experiment(config.experiment_name)

    os.environ["MLFLOW_TRACKING_URI"] = config.tracking_uri
    os.environ["MLFLOW_EXPERIMENT_NAME"] = config.experiment_name

    return config


def build_run_name(config: MLflowConfig, model_name: str, seed: int) -> str:
    safe_model_name = model_name.replace("/", "-")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{config.run_name_prefix}-{safe_model_name}-seed{seed}-{timestamp}"


def log_dvc_metadata(
    data_dir: Path,
    data_dvc_path: Path = Path("data.dvc"),
    stats_path: Path | None = None,
    artifact_dir: str = "data",
    log_dvc_file: bool = True,
    log_data_stats: bool = True,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    resolved_stats_path = stats_path or data_dir / "data_stats.json"

    if log_dvc_file and data_dvc_path.exists():
        with data_dvc_path.open("r", encoding="utf-8") as f:
            dvc_metadata = yaml.safe_load(f) or {}

        metadata["dvc"] = dvc_metadata
        mlflow.log_dict(dvc_metadata, f"{artifact_dir}/data.dvc.json")
        mlflow.log_artifact(str(data_dvc_path), artifact_path=artifact_dir)

    if log_data_stats and resolved_stats_path.exists():
        with resolved_stats_path.open("r", encoding="utf-8") as f:
            data_stats = json.load(f)

        metadata["data_stats"] = data_stats
        mlflow.log_dict(data_stats, f"{artifact_dir}/data_stats.json")
        mlflow.log_artifact(str(resolved_stats_path), artifact_path=artifact_dir)

    return metadata


def log_training_artifacts(
    output_dir: Path, artifact_path: str = "training_output"
) -> None:
    if output_dir.exists():
        mlflow.log_artifacts(str(output_dir), artifact_path=artifact_path)


def _get_pinned_requirement(package_name: str) -> str | None:
    try:
        version = metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None

    # Local labels like torch==2.11.0+cu128 are not installable from PyPI.
    version = version.split("+", maxsplit=1)[0]
    return f"{package_name}=={version}"


def build_transformers_pip_requirements() -> list[str]:
    package_names = (
        "mlflow",
        "transformers",
        "torch",
        "accelerate",
        "numpy",
        "pandas",
        "scikit-learn",
        "tokenizers",
        "safetensors",
    )
    return [
        requirement
        for package_name in package_names
        if (requirement := _get_pinned_requirement(package_name)) is not None
    ]


def log_transformers_model(
    model: Any,
    tokenizer: Any,
    artifact_path: str,
    task: str = "text-classification",
) -> str:
    model_info = mlflow.transformers.log_model(
        transformers_model={"model": model, "tokenizer": tokenizer},
        artifact_path=artifact_path,
        task=task,
        pip_requirements=build_transformers_pip_requirements(),
    )

    run = mlflow.active_run()
    if run is None:
        raise RuntimeError("Cannot build MLflow model URI without an active run.")

    return getattr(model_info, "model_uri", f"runs:/{run.info.run_id}/{artifact_path}")


def register_model(
    model_uri: str,
    config: MLflowConfig,
    extra_tags: dict[str, str] | None = None,
) -> Any | None:
    if not config.registry_enabled:
        return None

    model_version = mlflow.register_model(
        model_uri=model_uri,
        name=config.registered_model_name,
        await_registration_for=config.await_registration_for,
    )

    client = mlflow.MlflowClient()
    tags = dict(config.registry_tags)
    if extra_tags:
        tags.update(extra_tags)

    for key, value in tags.items():
        client.set_model_version_tag(
            name=config.registered_model_name,
            version=model_version.version,
            key=key,
            value=str(value),
        )

    if config.registry_stage:
        client.transition_model_version_stage(
            name=config.registered_model_name,
            version=model_version.version,
            stage=config.registry_stage,
            archive_existing_versions=False,
        )

    for alias, enabled in config.registry_aliases.items():
        if enabled:
            client.set_registered_model_alias(
                name=config.registered_model_name,
                alias=alias,
                version=model_version.version,
            )

    return model_version
