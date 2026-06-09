"""Create a minimal HuggingFace model directory for Docker smoke tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from lyubava.data.emotions import ID2LABEL, LABEL2ID, LABELS

DEFAULT_BASE_MODEL = "prajjwal1/bert-tiny"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a lightweight emotion-classifier stub for CI/CD."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
        help="Directory where the stub model will be saved.",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default=DEFAULT_BASE_MODEL,
        help="Small pretrained model used as the stub backbone.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = AutoConfig.from_pretrained(
        args.base_model,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        config=config,
    )

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print(f"Stub model saved to {args.output_dir}")


if __name__ == "__main__":
    main()
