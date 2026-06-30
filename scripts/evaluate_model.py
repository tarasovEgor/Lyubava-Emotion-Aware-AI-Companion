"""CLI script for evaluating a trained emotion classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lyubava.models.evaluate import evaluate_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained Lyubava emotion classifier."
    )

    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
        help="Path to trained model directory.",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed/empatheticdialogues"),
        help="Path to processed dataset directory.",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports/evaluation"),
        help="Directory where evaluation reports will be saved.",
    )

    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split to evaluate. Example: test, valid, train.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Evaluation batch size.",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
        help="Maximum token length.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Evaluating model from: {args.model_dir}")
    print(f"Using data from: {args.data_dir}")
    print(f"Split: {args.split}")

    metrics = evaluate_model(
        model_dir=args.model_dir,
        data_dir=args.data_dir,
        output_dir=args.reports_dir,
        split=args.split,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )

    print("Evaluation metrics:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
