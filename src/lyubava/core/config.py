import os
from dataclasses import dataclass

DEFAULT_MODEL_DIR = "models/emotion_classifier"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-oss-120b"
DEFAULT_CHAT_TEMPERATURE = 0.7
DEFAULT_DRIFT_WINDOW_SIZE = 500
DEFAULT_DRIFT_MIN_SAMPLES = 100
DEFAULT_DRIFT_BASELINE_PATH = "monitoring/baselines/drift-baseline.json"
DEFAULT_DRIFT_DATA_WARN_THRESHOLD = 0.1
DEFAULT_DRIFT_DATA_CRITICAL_THRESHOLD = 0.25
DEFAULT_DRIFT_CONCEPT_WARN_THRESHOLD = 0.1
DEFAULT_DRIFT_CONCEPT_CRITICAL_THRESHOLD = 0.25
DEFAULT_DRIFT_TARGET_WARN_THRESHOLD = 0.1
DEFAULT_DRIFT_TARGET_CRITICAL_THRESHOLD = 0.25
DEFAULT_PREDICTIONS_FEED_MAX_ITEMS = 500


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid integer.") from exc


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid float.") from exc


@dataclass(frozen=True)
class Settings:
    model_dir: str = DEFAULT_MODEL_DIR
    openrouter_api_key: str | None = None
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    chat_temperature: float = DEFAULT_CHAT_TEMPERATURE
    drift_window_size: int = DEFAULT_DRIFT_WINDOW_SIZE
    drift_min_samples: int = DEFAULT_DRIFT_MIN_SAMPLES
    drift_baseline_path: str | None = DEFAULT_DRIFT_BASELINE_PATH
    drift_data_warn_threshold: float = DEFAULT_DRIFT_DATA_WARN_THRESHOLD
    drift_data_critical_threshold: float = DEFAULT_DRIFT_DATA_CRITICAL_THRESHOLD
    drift_concept_warn_threshold: float = DEFAULT_DRIFT_CONCEPT_WARN_THRESHOLD
    drift_concept_critical_threshold: float = DEFAULT_DRIFT_CONCEPT_CRITICAL_THRESHOLD
    drift_target_warn_threshold: float = DEFAULT_DRIFT_TARGET_WARN_THRESHOLD
    drift_target_critical_threshold: float = DEFAULT_DRIFT_TARGET_CRITICAL_THRESHOLD
    predictions_feed_max_items: int = DEFAULT_PREDICTIONS_FEED_MAX_ITEMS

    @classmethod
    def from_env(cls) -> "Settings":
        temperature_raw = os.getenv("CHAT_TEMPERATURE", str(DEFAULT_CHAT_TEMPERATURE))
        try:
            chat_temperature = float(temperature_raw)
        except ValueError as exc:
            raise RuntimeError("CHAT_TEMPERATURE must be a valid float.") from exc

        return cls(
            model_dir=os.getenv("MODEL_DIR", DEFAULT_MODEL_DIR),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                DEFAULT_OPENROUTER_BASE_URL,
            ),
            openrouter_model=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            chat_temperature=chat_temperature,
            drift_window_size=_get_env_int("DRIFT_WINDOW_SIZE", DEFAULT_DRIFT_WINDOW_SIZE),
            drift_min_samples=_get_env_int("DRIFT_MIN_SAMPLES", DEFAULT_DRIFT_MIN_SAMPLES),
            drift_baseline_path=os.getenv(
                "DRIFT_BASELINE_PATH", DEFAULT_DRIFT_BASELINE_PATH
            ),
            drift_data_warn_threshold=_get_env_float(
                "DRIFT_DATA_WARN_THRESHOLD",
                DEFAULT_DRIFT_DATA_WARN_THRESHOLD,
            ),
            drift_data_critical_threshold=_get_env_float(
                "DRIFT_DATA_CRITICAL_THRESHOLD",
                DEFAULT_DRIFT_DATA_CRITICAL_THRESHOLD,
            ),
            drift_concept_warn_threshold=_get_env_float(
                "DRIFT_CONCEPT_WARN_THRESHOLD",
                DEFAULT_DRIFT_CONCEPT_WARN_THRESHOLD,
            ),
            drift_concept_critical_threshold=_get_env_float(
                "DRIFT_CONCEPT_CRITICAL_THRESHOLD",
                DEFAULT_DRIFT_CONCEPT_CRITICAL_THRESHOLD,
            ),
            drift_target_warn_threshold=_get_env_float(
                "DRIFT_TARGET_WARN_THRESHOLD",
                DEFAULT_DRIFT_TARGET_WARN_THRESHOLD,
            ),
            drift_target_critical_threshold=_get_env_float(
                "DRIFT_TARGET_CRITICAL_THRESHOLD",
                DEFAULT_DRIFT_TARGET_CRITICAL_THRESHOLD,
            ),
            predictions_feed_max_items=_get_env_int(
                "PREDICTIONS_FEED_MAX_ITEMS",
                DEFAULT_PREDICTIONS_FEED_MAX_ITEMS,
            ),
        )
