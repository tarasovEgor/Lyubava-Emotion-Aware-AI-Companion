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


def test_admin_retrain_start_returns_accepted(client):
    status_payload = {
        "state": "running",
        "started_at": "2026-06-30T12:00:00+00:00",
        "finished_at": None,
        "message": "Retraining started.",
        "metrics": None,
    }

    class StubRetrainService:
        def start(self):
            return type("Status", (), status_payload)()

    client.app.state.container.retrain_service = StubRetrainService()

    response = client.post("/v1/admin/retrain")

    assert response.status_code == 202
    assert response.json() == status_payload


def test_admin_retrain_status_returns_payload(client):
    status_payload = {
        "state": "succeeded",
        "started_at": "2026-06-30T12:00:00+00:00",
        "finished_at": "2026-06-30T12:10:00+00:00",
        "message": "Retraining completed successfully.",
        "metrics": {"eval_accuracy": 0.9},
    }

    class StubRetrainService:
        def get_status(self):
            return type("Status", (), status_payload)()

    client.app.state.container.retrain_service = StubRetrainService()

    response = client.get("/v1/admin/retrain")

    assert response.status_code == 200
    assert response.json() == status_payload
