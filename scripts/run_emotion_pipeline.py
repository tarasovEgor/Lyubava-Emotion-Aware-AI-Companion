"""CLI script for training, evaluating, and smoke-testing the emotion model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lyubava.models.evaluate import evaluate_model
from lyubava.models.predict import EmotionPredictor
from lyubava.models.train import train


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train, evaluate, and test Lyubava emotion classifier."
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed/empatheticdialogues"),
        help="Path to processed dataset directory.",
    )

    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
        help="Directory where the trained model will be saved.",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports/evaluation"),
        help="Directory where evaluation reports will be saved.",
    )

    parser.add_argument(
        "--base-model",
        type=str,
        default="distilbert-base-uncased",
        help="Base Hugging Face model name.",
    )

    parser.add_argument(
        "--test-split",
        type=str,
        default="test",
        help="Dataset split to use for final evaluation.",
    )

    parser.add_argument(
        "--prediction-text",
        type=str,
        default="I feel really lonely today.",
        help="Text used for a smoke-test prediction after training.",
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

    print("Training emotion classifier...")

    validation_metrics = train(
        data_dir=args.data_dir,
        output_dir=args.model_dir,
        model_name=args.base_model,
        max_length=args.max_length,
        learning_rate=args.learning_rate,
        train_batch_size=args.train_batch_size,
        eval_batch_size=args.eval_batch_size,
        num_train_epochs=args.num_train_epochs,
        weight_decay=args.weight_decay,
        seed=args.seed,
    )

    print("Validation metrics:")
    print(json.dumps(validation_metrics, indent=2))

    print(f"Evaluating model on '{args.test_split}' split...")

    test_metrics = evaluate_model(
        model_dir=args.model_dir,
        data_dir=args.data_dir,
        output_dir=args.reports_dir,
        split=args.test_split,
        batch_size=args.eval_batch_size,
        max_length=args.max_length,
    )

    print("Test metrics:")
    print(json.dumps(test_metrics, indent=2))

    print("Running smoke-test prediction...")

    predictor = EmotionPredictor(
        model_dir=args.model_dir,
        max_length=args.max_length,
    )

    prediction = predictor.predict(args.prediction_text)

    print("Prediction:")
    print(
        json.dumps(
            {
                "text": args.prediction_text,
                "result": prediction,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()