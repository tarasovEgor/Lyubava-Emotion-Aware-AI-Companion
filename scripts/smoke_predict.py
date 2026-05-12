"""CLI script for smoke-testing a trained emotion classifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lyubava.models.predict import EmotionPredictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a smoke-test prediction with a trained Lyubava model."
    )

    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
        help="Path to trained model directory.",
    )

    parser.add_argument(
        "--text",
        type=str,
        default="I feel really lonely today.",
        help="Text to classify.",
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=128,
        help="Maximum token length.",
    )

    parser.add_argument(
        "--expected-emotion",
        type=str,
        default=None,
        help="Optional expected emotion. If provided, script fails if prediction differs.",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Optional minimum confidence. If provided, script fails if confidence is lower.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Loading model from: {args.model_dir}")

    predictor = EmotionPredictor(
        model_dir=args.model_dir,
        max_length=args.max_length,
    )

    result = predictor.predict(args.text)

    payload = {
        "text": args.text,
        "result": result,
    }

    print("Prediction:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.expected_emotion is not None:
        predicted_emotion = result["emotion"]

        if predicted_emotion != args.expected_emotion:
            print(
                f"Smoke test failed: expected emotion '{args.expected_emotion}', "
                f"got '{predicted_emotion}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.min_confidence is not None:
        confidence = float(result["confidence"])

        if confidence < args.min_confidence:
            print(
                f"Smoke test failed: expected confidence >= {args.min_confidence}, "
                f"got {confidence}.",
                file=sys.stderr,
            )
            sys.exit(1)

    print("Smoke test passed.")


if __name__ == "__main__":
    main()