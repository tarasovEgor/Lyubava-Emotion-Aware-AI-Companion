import os
from dataclasses import dataclass


DEFAULT_MODEL_DIR = "models/emotion_classifier"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-oss-120b"
DEFAULT_CHAT_TEMPERATURE = 0.7


@dataclass(frozen=True)
class Settings:
    model_dir: str = DEFAULT_MODEL_DIR
    openrouter_api_key: str | None = None
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    chat_temperature: float = DEFAULT_CHAT_TEMPERATURE

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
        )
