from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import lyubava.core.lifecycle as lifecycle
from lyubava.api.main import create_app


class DummyPredictor:
    def predict(self, text: str) -> dict[str, str | float]:
        return {"emotion": "sadness", "confidence": 0.99}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        lifecycle, "EmotionPredictor", lambda model_dir: DummyPredictor()
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
