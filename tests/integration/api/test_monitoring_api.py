def test_get_monitoring_drift_snapshot(client):
    response = client.get("/v1/monitoring/drift")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service_status"] in {"ok", "insufficient_data", "unavailable"}
    assert isinstance(payload["window_size"], int)
    assert isinstance(payload["min_samples"], int)
    assert isinstance(payload["sample_count"], int)
    assert payload["drift"]["data"]["status"] in {
        "ok",
        "warn",
        "critical",
        "insufficient_data",
        "unavailable",
    }
    assert payload["drift"]["concept"]["status"] in {
        "ok",
        "warn",
        "critical",
        "insufficient_data",
        "unavailable",
    }
    assert payload["drift"]["target"]["status"] in {
        "ok",
        "warn",
        "critical",
        "insufficient_data",
        "unavailable",
    }


def test_get_monitoring_drift_when_service_unavailable(client):
    client.app.state.container.drift_service = None
    client.app.state.container.drift_init_error = "Drift service is not ready."

    response = client.get("/v1/monitoring/drift")

    assert response.status_code == 503
    assert response.json()["detail"] == "Drift service is not ready."


def test_metrics_endpoint_exposes_prometheus_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "lyubava_drift_data_score" in body
    assert "lyubava_drift_concept_score" in body
    assert "lyubava_drift_target_score" in body
    assert "lyubava_drift_status" in body
    assert "lyubava_predictions_total" in body
    assert "lyubava_prediction_confidence_mean" in body
    assert "lyubava_prediction_entropy_mean" in body
    assert "lyubava_prediction_class_ratio" in body
