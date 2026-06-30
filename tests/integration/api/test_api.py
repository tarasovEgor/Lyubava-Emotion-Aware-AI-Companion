def test_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_emotion(client):
    response = client.post(
        "/v1/predict-emotion",
        json={"text": "I feel really lonely today."},
    )
    assert response.status_code == 200
    assert response.json()["emotion"] == "sadness"
    assert 0.0 <= response.json()["confidence"] <= 1.0


def test_predict_emotion_rejects_empty_text(client):
    response = client.post(
        "/v1/predict-emotion",
        json={"text": ""},
    )
    assert response.status_code == 422


def test_services_initialized_in_app_state(client):
    assert hasattr(client.app.state, "container")
    container = client.app.state.container
    assert container.predictor is not None
    assert container.chat_service is None
    assert container.chat_init_error == "OPENROUTER_API_KEY is not set."


def test_chat_unavailable_without_api_key(client):
    response = client.post(
        "/v1/chat",
        json={"session_id": "session-1", "message": "hello"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "OPENROUTER_API_KEY is not set."
