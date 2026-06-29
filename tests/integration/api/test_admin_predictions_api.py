from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import lyubava.core.lifecycle as lifecycle
from lyubava.api.main import create_app


class DummyLLMClient:
    def __init__(self, settings):
        _ = settings

    def generate_reply(self, user_message: str, system_prompt: str, history_messages=None):
        _ = history_messages
        return type(
            "DummyReply",
            (),
            {
                "text": f"reply:{user_message}",
                "provider": "dummy-provider",
                "model": "dummy-model",
                "system_prompt": system_prompt,
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "response_metadata": {"finish_reason": "stop"},
            },
        )()


@pytest.fixture
def client_with_chat(monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(lifecycle, "OpenRouterLLMClient", DummyLLMClient)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_admin_predictions_returns_items(client_with_chat):
    chat_payload = {"session_id": "admin-feed-session", "message": "Мне немного тревожно"}
    chat_response = client_with_chat.post("/v1/chat", json=chat_payload)
    assert chat_response.status_code == 200

    response = client_with_chat.get("/v1/admin/predictions?limit=10")
    assert response.status_code == 200

    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 1

    row = payload["items"][0]
    assert set(row.keys()) == {
        "timestamp",
        "session_id",
        "text",
        "predicted_emotion",
        "confidence",
        "model",
        "provider",
    }
    assert row["session_id"] == "admin-feed-session"
    assert row["text"] == "Мне немного тревожно"


def test_get_admin_predictions_respects_limit(client_with_chat):
    for idx in range(3):
        payload = {"session_id": f"session-{idx}", "message": f"message-{idx}"}
        assert client_with_chat.post("/v1/chat", json=payload).status_code == 200

    response = client_with_chat.get("/v1/admin/predictions?limit=1")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
