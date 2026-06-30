"""Prepare raw EmpatheticDialogues CSV files for model training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from lyubava.data.emotions import EMOTION_MAP, ID2LABEL, LABEL2ID, LABELS


@dataclass
class DataConfig:
    raw_dir: Path
    processed_dir: Path
    splits: dict[str, str]
    text_column: str
    source_label_column: str
    target_label_column: str


def load_config(config_path: str | Path) -> DataConfig:
    """Load data preparation config from YAML."""

    config_path = Path(config_path)

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return DataConfig(
        raw_dir=Path(config["raw_dir"]),
        processed_dir=Path(config["processed_dir"]),
        splits=config["splits"],
        text_column=config["text_column"],
        source_label_column=config["source_label_column"],
        target_label_column=config["target_label_column"],
    )


def clean_text(value: Any) -> str:
    """Basic text cleaning."""

    text = str(value)
    text = " ".join(text.split())
    return text.strip()


def process_split(
    input_path: Path,
    text_column: str,
    source_label_column: str,
    target_label_column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Process one raw CSV split."""

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, on_bad_lines="skip")
    raw_rows = len(df)

    required_columns = {text_column, source_label_column}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns in {input_path}: {sorted(missing_columns)}")

    df = df[[text_column, source_label_column]].copy()

    df[text_column] = df[text_column].map(clean_text)
    df[source_label_column] = df[source_label_column].astype(str).str.strip()

    df[target_label_column] = df[source_label_column].map(EMOTION_MAP)

    df = df.dropna(subset=[text_column, target_label_column])
    df = df[df[text_column] != ""]

    df["label"] = df[target_label_column].map(LABEL2ID)

    df = df.rename(columns={text_column: "text"})
    df = df[["text", target_label_column, "label"]]

    processed_rows = len(df)

    stats = {
        "input_path": str(input_path),
        "raw_rows": raw_rows,
        "processed_rows": processed_rows,
        "dropped_rows": raw_rows - processed_rows,
        "label_distribution": df[target_label_column].value_counts().to_dict(),
    }

    return df, stats


def save_metadata(processed_dir: Path, split_stats: dict[str, Any]) -> None:
    """Save label mapping and data preparation statistics."""

    labels_path = processed_dir / "labels.json"
    stats_path = processed_dir / "data_stats.json"

    labels_payload = {
        "labels": LABELS,
        "label2id": LABEL2ID,
        "id2label": {str(key): value for key, value in ID2LABEL.items()},
    }

    with labels_path.open("w", encoding="utf-8") as file:
        json.dump(labels_payload, file, indent=2, ensure_ascii=False)

    with stats_path.open("w", encoding="utf-8") as file:
        json.dump(split_stats, file, indent=2, ensure_ascii=False)


def prepare_dataset(config_path: str | Path) -> None:
    """Prepare all dataset splits and save processed CSV files."""

    config = load_config(config_path)
    config.processed_dir.mkdir(parents=True, exist_ok=True)

    all_stats: dict[str, Any] = {}

    for split_name, filename in config.splits.items():
        input_path = config.raw_dir / filename

        processed_df, split_stats = process_split(
            input_path=input_path,
            text_column=config.text_column,
            source_label_column=config.source_label_column,
            target_label_column=config.target_label_column,
        )

        output_path = config.processed_dir / f"{split_name}.csv"
        processed_df.to_csv(output_path, index=False)

        split_stats["output_path"] = str(output_path)
        all_stats[split_name] = split_stats

        print(
            f"Prepared {split_name}: "
            f"{split_stats['processed_rows']} rows "
            f"saved to {output_path}"
        )

    save_metadata(config.processed_dir, all_stats)

    print(f"Saved metadata to {config.processed_dir}")
