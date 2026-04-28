from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments


REQUIRED_COLUMNS = {"text", "emotion", "label"}


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


def get_id2label(model: AutoModelForSequenceClassification) -> dict[int, str]:
    return {int(k): str(v) for k, v in model.config.id2label.items()}


def tokenize_dataset(
    dataset: Dataset,
    tokenizer: AutoTokenizer,
    max_length: int,
) -> Dataset:
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


def evaluate_model(
    model_dir: Path,
    data_dir: Path,
    output_dir: Path,
    split: str,
    batch_size: int,
    max_length: int,
) -> dict[str, Any]:
    split_path = data_dir / f"{split}.csv"
    df = load_split(split_path)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))

    id2label = get_id2label(model)
    label_ids = sorted(id2label.keys())
    target_names = [id2label[label_id] for label_id in label_ids]

    dataset = Dataset.from_pandas(
        df[["text", "label"]],
        preserve_index=False,
    )

    tokenized_dataset = tokenize_dataset(
        dataset=dataset,
        tokenizer=tokenizer,
        max_length=max_length,
    )

    args = TrainingArguments(
        output_dir=str(output_dir / "_tmp_trainer"),
        per_device_eval_batch_size=batch_size,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
    )

    predictions_output = trainer.predict(tokenized_dataset)
    logits = predictions_output.predictions

    y_true = df["label"].to_numpy()
    y_pred = np.argmax(logits, axis=-1)

    report = classification_report(
        y_true,
        y_pred,
        labels=label_ids,
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )

    metrics: dict[str, Any] = {
        "split": split,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "per_class": {
            emotion: {
                "precision": report[emotion]["precision"],
                "recall": report[emotion]["recall"],
                "f1": report[emotion]["f1-score"],
                "support": report[emotion]["support"],
            }
            for emotion in target_names
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    with (output_dir / "classification_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    predictions_df = df.copy()
    predictions_df["predicted_label"] = y_pred
    predictions_df["predicted_emotion"] = [id2label[int(label)] for label in y_pred]
    predictions_df.to_csv(output_dir / "predictions.csv", index=False)

    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Lyubava emotion classifier.")

    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed/empatheticdialogues"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/evaluation"),
    )
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=128)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    metrics = evaluate_model(
        model_dir=args.model_dir,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        split=args.split,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()