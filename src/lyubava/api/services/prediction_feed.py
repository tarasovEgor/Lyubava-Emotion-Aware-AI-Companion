from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PredictionFeedItem:
    timestamp: str
    session_id: str
    text: str
    predicted_emotion: str
    confidence: float
    model: str
    provider: str


class PredictionFeedService:
    def __init__(self, max_items: int = 500) -> None:
        if max_items < 1:
            raise ValueError("max_items must be greater than or equal to 1")
        self._items: deque[PredictionFeedItem] = deque(maxlen=max_items)

    def append(
        self,
        *,
        timestamp: str,
        session_id: str,
        text: str,
        predicted_emotion: str,
        confidence: float,
        model: str,
        provider: str,
    ) -> None:
        self._items.append(
            PredictionFeedItem(
                timestamp=timestamp,
                session_id=session_id,
                text=text,
                predicted_emotion=predicted_emotion,
                confidence=confidence,
                model=model,
                provider=provider,
            )
        )

    def list_items(self, limit: int) -> list[dict[str, object]]:
        safe_limit = max(1, limit)
        newest_first = reversed(self._items)
        return [asdict(item) for item in list(newest_first)[:safe_limit]]
