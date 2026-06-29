import pytest

from lyubava.core.config import (
    DEFAULT_DRIFT_DATA_WARN_THRESHOLD,
    DEFAULT_DRIFT_MIN_SAMPLES,
    DEFAULT_DRIFT_WINDOW_SIZE,
    Settings,
)


def test_settings_from_env_uses_drift_defaults_when_absent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DRIFT_WINDOW_SIZE", raising=False)
    monkeypatch.delenv("DRIFT_MIN_SAMPLES", raising=False)
    monkeypatch.delenv("DRIFT_DATA_WARN_THRESHOLD", raising=False)

    settings = Settings.from_env()

    assert settings.drift_window_size == DEFAULT_DRIFT_WINDOW_SIZE
    assert settings.drift_min_samples == DEFAULT_DRIFT_MIN_SAMPLES
    assert settings.drift_data_warn_threshold == DEFAULT_DRIFT_DATA_WARN_THRESHOLD


def test_settings_from_env_raises_for_invalid_drift_int(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DRIFT_WINDOW_SIZE", "not-an-int")

    with pytest.raises(RuntimeError, match="DRIFT_WINDOW_SIZE"):
        Settings.from_env()


def test_settings_from_env_raises_for_invalid_drift_float(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DRIFT_TARGET_WARN_THRESHOLD", "not-a-float")

    with pytest.raises(RuntimeError, match="DRIFT_TARGET_WARN_THRESHOLD"):
        Settings.from_env()
