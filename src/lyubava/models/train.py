from __future__ import annotations

import argparse
import inspect
import json
import sys
from contextlib import nullcontext
import mlflow
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)

from transformers.integrations import MLflowCallback

from lyubava.utils.mlflow_helper import (
    build_run_name,
    get_dvc_data_hash,
    initialize_mlflow,
    log_dvc_metadata,
    log_training_artifacts,
    log_transformers_model,
    register_model,
    set_dataset_tags_from_dvc,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REQUIRED_COLUMNS = {"text", "emotion", "label"}


def load_labels(labels_path: Path) -> tuple[dict[str, int], dict[int, str]]:
    with labels_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "label2id" in data:
        label2id = {str(k): int(v) for k, v in data["label2id"].items()}
    elif "labels" in data:
        label2id = {label: idx for idx, label in enumerate(data["labels"])}
    else:
        raise ValueError(
            f"Unsupported labels.json format in {labels_path}. "
            "Expected either 'label2id' or 'labels'."
        )

    if "id2label" in data:
        id2label = {int(k): str(v) for k, v in data["id2label"].items()}
    else:
        id2label = {idx: label for label, idx in label2id.items()}

    return label2id, id2label


def load_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset split: {path}")

    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    df = df[["text", "emotion", "label"]].copy()
    df["text"] = df["text"].astype(str)
    df["label"] = df["label"].astype(int)

    return df.reset_index(drop=True)


def build_dataset(data_dir: Path) -> DatasetDict:
    train_df = load_split(data_dir / "train.csv")
    valid_df = load_split(data_dir / "valid.csv")

    return DatasetDict(
        {
            "train": Dataset.from_pandas(
                train_df[["text", "label"]],
                preserve_index=False,
            ),
            "validation": Dataset.from_pandas(
                valid_df[["text", "label"]],
                preserve_index=False,
            ),
        }
    )


def limit_dataset_samples(
    dataset: DatasetDict,
    max_train_samples: int | None = None,
    max_eval_samples: int | None = None,
) -> DatasetDict:
    if max_train_samples is not None:
        dataset["train"] = dataset["train"].select(
            range(min(max_train_samples, len(dataset["train"])))
        )

    if max_eval_samples is not None:
        dataset["validation"] = dataset["validation"].select(
            range(min(max_eval_samples, len(dataset["validation"])))
        )

    return dataset


def tokenize_dataset(
    dataset: DatasetDict,
    tokenizer: AutoTokenizer,
    max_length: int,
) -> DatasetDict:
    def tokenize_batch(batch: dict[str, list[Any]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            padding="max_length",
            truncation=True,
            max_length=max_length,
        )

    return dataset.map(
        tokenize_batch,
        batched=True,
        remove_columns=["text"],
    )


def compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    return {
        "accuracy": accuracy_score(labels, predictions),
        "macro_f1": f1_score(labels, predictions, average="macro", zero_division=0),
        "weighted_f1": f1_score(
            labels, predictions, average="weighted", zero_division=0
        ),
    }


def make_training_args(
    output_dir: Path,
    learning_rate: float,
    train_batch_size: int,
    eval_batch_size: int,
    num_train_epochs: float,
    weight_decay: float,
    seed: int,
    report_to: str | list[str] = "none",
    run_name: str | None = None,
    use_cpu: bool = False,
) -> TrainingArguments:
    kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "learning_rate": learning_rate,
        "per_device_train_batch_size": train_batch_size,
        "per_device_eval_batch_size": eval_batch_size,
        "num_train_epochs": num_train_epochs,
        "weight_decay": weight_decay,
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "macro_f1",
        "greater_is_better": True,
        "save_total_limit": 2,
        "logging_strategy": "steps",
        "logging_steps": 50,
        "report_to": report_to,
        "run_name": run_name,
        "seed": seed,
        "use_cpu": use_cpu,
    }

    # Compatibility across Transformers versions:
    # newer versions use eval_strategy, older versions use evaluation_strategy.
    signature = inspect.signature(TrainingArguments.__init__)
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = "epoch"
    else:
        kwargs["evaluation_strategy"] = "epoch"

    return TrainingArguments(**kwargs)


def make_trainer(
    model: AutoModelForSequenceClassification,
    training_args: TrainingArguments,
    train_dataset: Dataset,
    eval_dataset: Dataset,
    tokenizer: AutoTokenizer,
    callbacks: list[Any] | None,
) -> Trainer:
    kwargs: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "compute_metrics": compute_metrics,
        "callbacks": callbacks,
    }

    signature = inspect.signature(Trainer.__init__)
    if "processing_class" in signature.parameters:
        kwargs["processing_class"] = tokenizer
    else:
        kwargs["tokenizer"] = tokenizer

    return Trainer(**kwargs)


def train(
    data_dir: Path,
    output_dir: Path,
    model_name: str,
    max_length: int,
    learning_rate: float,
    train_batch_size: int,
    eval_batch_size: int,
    num_train_epochs: float,
    weight_decay: float,
    seed: int,
    mlflow_config_path: Path = Path("configs/mlflow.yaml"),
    enable_mlflow: bool = True,
    max_train_samples: int | None = None,
    max_eval_samples: int | None = None,
    use_cpu: bool = False,
) -> dict[str, float | str]:
    set_seed(seed)

    mlflow_config = initialize_mlflow(mlflow_config_path) if enable_mlflow else None
    run_name = (
        build_run_name(mlflow_config, model_name=model_name, seed=seed)
        if mlflow_config
        else None
    )

    labels_path = data_dir / "labels.json"
    label2id, id2label = load_labels(labels_path)

    dataset = limit_dataset_samples(
        dataset=build_dataset(data_dir),
        max_train_samples=max_train_samples,
        max_eval_samples=max_eval_samples,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    tokenized_dataset = tokenize_dataset(
        dataset=dataset,
        tokenizer=tokenizer,
        max_length=max_length,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(label2id),
        label2id=label2id,
        id2label=id2label,
    )

    training_args = make_training_args(
        output_dir=output_dir,
        learning_rate=learning_rate,
        train_batch_size=train_batch_size,
        eval_batch_size=eval_batch_size,
        num_train_epochs=num_train_epochs,
        weight_decay=weight_decay,
        seed=seed,
        report_to="none",
        run_name=run_name,
        use_cpu=use_cpu,
    )

    callbacks = [MLflowCallback()] if mlflow_config else None

    trainer = make_trainer(
        model=model,
        training_args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        tokenizer=tokenizer,
        callbacks=callbacks,
    )

    dvc_hash = get_dvc_data_hash() if mlflow_config else None
    run_context = (
        mlflow.start_run(
            run_name=run_name,
            tags={
                **mlflow_config.run_tags,
                **({"dataset.dvc_hash": dvc_hash} if dvc_hash else {}),
            },
        )
        if mlflow_config
        else nullcontext()
    )

    with run_context:
        if mlflow_config:
            dvc_hash = set_dataset_tags_from_dvc()
            if dvc_hash:
                mlflow.log_param("dataset_dvc_hash", dvc_hash)

            mlflow.log_params(
                {
                    "model_name": model_name,
                    "max_length": max_length,
                    "learning_rate": learning_rate,
                    "train_batch_size": train_batch_size,
                    "eval_batch_size": eval_batch_size,
                    "num_train_epochs": num_train_epochs,
                    "weight_decay": weight_decay,
                    "seed": seed,
                    "train_rows": len(dataset["train"]),
                    "validation_rows": len(dataset["validation"]),
                    "max_train_samples": max_train_samples or "",
                    "max_eval_samples": max_eval_samples or "",
                    "num_labels": len(label2id),
                }
            )
            mlflow.log_dict(
                {
                    "label2id": label2id,
                    "id2label": {str(k): v for k, v in id2label.items()},
                },
                "metadata/label_metadata.json",
            )
            if mlflow_config.log_dvc_file or mlflow_config.log_data_stats:
                log_dvc_metadata(
                    data_dir=data_dir,
                    log_dvc_file=mlflow_config.log_dvc_file,
                    log_data_stats=mlflow_config.log_data_stats,
                )

        trainer.train()

        eval_metrics: dict[str, float | str] = trainer.evaluate()

        output_dir.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))

        with (output_dir / "label_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "label2id": label2id,
                    "id2label": {str(k): v for k, v in id2label.items()},
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        with (output_dir / "validation_metrics.json").open("w", encoding="utf-8") as f:
            json.dump(eval_metrics, f, indent=2)

        if mlflow_config:
            mlflow.log_metrics(
                {
                    key: float(value)
                    for key, value in eval_metrics.items()
                    if isinstance(value, int | float)
                }
            )
            mlflow.log_artifact(
                str(output_dir / "label_metadata.json"),
                artifact_path="metadata",
            )
            mlflow.log_artifact(
                str(output_dir / "validation_metrics.json"),
                artifact_path="metrics",
            )

            model_uri = log_transformers_model(
                model=trainer.model,
                tokenizer=tokenizer,
                artifact_path=mlflow_config.model_artifact_path,
            )

            if mlflow_config.log_output_dir:
                log_training_artifacts(
                    output_dir=output_dir,
                    artifact_path="training_output",
                )

            model_version = register_model(
                model_uri=model_uri,
                config=mlflow_config,
                extra_tags={
                    "dataset.dvc_hash": dvc_hash or "",
                    "source_run_name": run_name or "",
                    "metric_macro_f1": str(eval_metrics.get("eval_macro_f1", "")),
                },
            )

            if model_version is not None:
                eval_metrics["registered_model_name"] = model_version.name
                eval_metrics["registered_model_version"] = model_version.version

        return eval_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Lyubava emotion classifier.")

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed/empatheticdialogues"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="distilbert-base-uncased",
    )
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--train-batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=16)
    parser.add_argument("--num-train-epochs", type=float, default=3)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--use-cpu",
        action="store_true",
        help="Force CPU training even if a CUDA device is visible.",
    )
    parser.add_argument(
        "--max-train-samples",
        type=int,
        default=None,
        help="Limit training rows for quick CPU smoke-runs.",
    )
    parser.add_argument(
        "--max-eval-samples",
        type=int,
        default=None,
        help="Limit validation rows for quick CPU smoke-runs.",
    )
    parser.add_argument(
        "--mlflow-config",
        type=Path,
        default=Path("configs/mlflow.yaml"),
        help="Path to MLflow tracking and registry configuration.",
    )
    parser.add_argument(
        "--disable-mlflow",
        action="store_true",
        help="Disable MLflow tracking for quick local/debug runs.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    metrics = train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        model_name=args.model_name,
        max_length=args.max_length,
        learning_rate=args.learning_rate,
        train_batch_size=args.train_batch_size,
        eval_batch_size=args.eval_batch_size,
        num_train_epochs=args.num_train_epochs,
        weight_decay=args.weight_decay,
        seed=args.seed,
        mlflow_config_path=args.mlflow_config,
        enable_mlflow=not args.disable_mlflow,
        max_train_samples=args.max_train_samples,
        max_eval_samples=args.max_eval_samples,
        use_cpu=args.use_cpu,
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
