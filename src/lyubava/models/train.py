from __future__ import annotations

import argparse
import inspect
import json
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
        "report_to": "none",
        "seed": seed,
    }

    # Compatibility across Transformers versions:
    # newer versions use eval_strategy, older versions use evaluation_strategy.
    signature = inspect.signature(TrainingArguments.__init__)
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = "epoch"
    else:
        kwargs["evaluation_strategy"] = "epoch"

    return TrainingArguments(**kwargs)


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
) -> dict[str, float]:
    set_seed(seed)

    labels_path = data_dir / "labels.json"
    label2id, id2label = load_labels(labels_path)

    dataset = build_dataset(data_dir)

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
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        compute_metrics=compute_metrics,
    )

    trainer.train()

    eval_metrics = trainer.evaluate()

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
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
