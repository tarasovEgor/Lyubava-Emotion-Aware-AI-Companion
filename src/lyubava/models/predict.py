from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class EmotionPredictor:
    def __init__(
        self,
        model_dir: str | Path = "models/emotion_classifier",
        max_length: int = 128,
        device: str | None = None,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.max_length = max_length

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = torch.device(device)

        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(self.model_dir)
        )
        self.model.to(self.device)
        self.model.eval()

        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}

    def predict(self, text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Input text must be a non-empty string.")

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length,
        )

        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)[0]

        confidence, predicted_id = torch.max(probabilities, dim=-1)
        probability_distribution = {
            self.id2label.get(index, str(index)): round(float(score), 4)
            for index, score in enumerate(probabilities.tolist())
        }

        return {
            "emotion": self.id2label[int(predicted_id.item())],
            "confidence": round(float(confidence.item()), 4),
            "probabilities": probability_distribution,
        }

    def predict_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        return [self.predict(text) for text in texts]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run emotion prediction.")

    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/emotion_classifier"),
    )
    parser.add_argument(
        "--text",
        type=str,
        required=True,
    )
    parser.add_argument("--max-length", type=int, default=128)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    predictor = EmotionPredictor(
        model_dir=args.model_dir,
        max_length=args.max_length,
    )

    result = predictor.predict(args.text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
