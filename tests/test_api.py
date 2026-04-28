from fastapi.testclient import TestClient

from lyubava.api import main as api_main


class DummyPredictor:
    def predict(self, text: str) -> dict:
        return {
            "emotion": "sadness",
            "confidence": 0.99,
        }


def test_health(monkeypatch):
    monkeypatch.setattr(api_main, "EmotionPredictor", lambda model_dir: DummyPredictor())

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_emotion(monkeypatch):
    monkeypatch.setattr(api_main, "EmotionPredictor", lambda model_dir: DummyPredictor())

    with TestClient(api_main.app) as client:
        response = client.post(
            "/predict-emotion",
            json={"text": "I feel really lonely today."},
        )

    assert response.status_code == 200
    assert response.json()["emotion"] == "sadness"
    assert 0.0 <= response.json()["confidence"] <= 1.0


def test_predict_emotion_rejects_empty_text(monkeypatch):
    monkeypatch.setattr(api_main, "EmotionPredictor", lambda model_dir: DummyPredictor())

    with TestClient(api_main.app) as client:
        response = client.post(
            "/predict-emotion",
            json={"text": ""},
        )

    assert response.status_code == 422