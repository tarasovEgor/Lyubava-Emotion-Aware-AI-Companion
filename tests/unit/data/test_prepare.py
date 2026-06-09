import json
from pathlib import Path

import pandas as pd
import pytest

from lyubava.data.emotions import EMOTION_MAP, LABEL2ID, LABELS
from lyubava.data.prepare import (
    clean_text,
    load_config,
    prepare_dataset,
    process_split,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
RAW_DIR = FIXTURES_DIR / "raw"
PROCESSED_DIR = FIXTURES_DIR / "processed"
DATA_CONFIG = FIXTURES_DIR / "data_ci.yaml"


@pytest.fixture(autouse=True)
def cleanup_processed_dir():
    yield
    if PROCESSED_DIR.exists():
        for path in PROCESSED_DIR.iterdir():
            path.unlink()
        PROCESSED_DIR.rmdir()


def test_clean_text_normalizes_whitespace():
    assert clean_text("  hello   world \n") == "hello world"


def test_emotion_map_targets_are_registered_labels():
    assert set(EMOTION_MAP.values()).issubset(set(LABELS))


def test_process_split_maps_emotions_and_drops_invalid_rows(tmp_path: Path):
    input_path = tmp_path / "split.csv"
    input_path.write_text(
        """utterance,context
I feel great,joyful
unknown label,not_a_real_emotion
""",
        encoding="utf-8",
    )

    processed_df, stats = process_split(
        input_path=input_path,
        text_column="utterance",
        source_label_column="context",
        target_label_column="emotion",
    )

    assert stats["raw_rows"] == 2
    assert stats["processed_rows"] == 1
    assert stats["dropped_rows"] == 1
    assert processed_df.iloc[0]["emotion"] == "joy"
    assert processed_df.iloc[0]["label"] == LABEL2ID["joy"]


def test_process_split_requires_expected_columns(tmp_path: Path):
    input_path = tmp_path / "split.csv"
    input_path.write_text("utterance\nhello\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing columns"):
        process_split(
            input_path=input_path,
            text_column="utterance",
            source_label_column="context",
            target_label_column="emotion",
        )


def test_prepare_dataset_writes_processed_files_and_metadata():
    config = load_config(DATA_CONFIG)
    assert config.raw_dir.resolve() == RAW_DIR.resolve()

    prepare_dataset(DATA_CONFIG)

    train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
    assert list(train_df.columns) == ["text", "emotion", "label"]
    assert len(train_df) == 2
    assert set(train_df["emotion"]) == {"joy", "fear"}

    labels_payload = json.loads(
        (PROCESSED_DIR / "labels.json").read_text(encoding="utf-8")
    )
    assert labels_payload["labels"] == LABELS

    stats_payload = json.loads(
        (PROCESSED_DIR / "data_stats.json").read_text(encoding="utf-8")
    )
    assert stats_payload["train"]["processed_rows"] == 2
    assert stats_payload["valid"]["processed_rows"] == 2
    assert stats_payload["test"]["processed_rows"] == 2
