from lyubava.api.services.prediction_feed import PredictionFeedService


def test_prediction_feed_returns_newest_first():
    service = PredictionFeedService(max_items=3)
    service.append(
        timestamp="2026-01-01T10:00:00Z",
        session_id="s1",
        text="hello",
        predicted_emotion="joy",
        confidence=0.9,
        model="m1",
        provider="p1",
    )
    service.append(
        timestamp="2026-01-01T10:01:00Z",
        session_id="s2",
        text="hi",
        predicted_emotion="sadness",
        confidence=0.4,
        model="m2",
        provider="p2",
    )

    items = service.list_items(limit=10)

    assert len(items) == 2
    assert items[0]["session_id"] == "s2"
    assert items[1]["session_id"] == "s1"


def test_prediction_feed_evicts_old_items():
    service = PredictionFeedService(max_items=2)
    service.append(
        timestamp="2026-01-01T10:00:00Z",
        session_id="s1",
        text="one",
        predicted_emotion="joy",
        confidence=0.9,
        model="m1",
        provider="p1",
    )
    service.append(
        timestamp="2026-01-01T10:01:00Z",
        session_id="s2",
        text="two",
        predicted_emotion="sadness",
        confidence=0.4,
        model="m1",
        provider="p1",
    )
    service.append(
        timestamp="2026-01-01T10:02:00Z",
        session_id="s3",
        text="three",
        predicted_emotion="fear",
        confidence=0.2,
        model="m1",
        provider="p1",
    )

    items = service.list_items(limit=10)

    assert len(items) == 2
    assert {item["session_id"] for item in items} == {"s2", "s3"}


def test_prediction_feed_respects_limit():
    service = PredictionFeedService(max_items=5)
    for idx in range(5):
        service.append(
            timestamp=f"2026-01-01T10:0{idx}:00Z",
            session_id=f"s{idx}",
            text=f"text-{idx}",
            predicted_emotion="joy",
            confidence=0.9,
            model="m1",
            provider="p1",
        )

    items = service.list_items(limit=2)
    assert len(items) == 2
    assert items[0]["session_id"] == "s4"
    assert items[1]["session_id"] == "s3"
