"""Emotion label mapping for the EmpatheticDialogues dataset."""

EMOTION_MAP: dict[str, str] = {
    "joyful": "joy",
    "excited": "joy",
    "proud": "joy",
    "hopeful": "joy",
    "confident": "joy",
    "content": "joy",
    "prepared": "joy",
    "anticipating": "joy",
    "sad": "sadness",
    "lonely": "sadness",
    "nostalgic": "sadness",
    "disappointed": "sadness",
    "devastated": "sadness",
    "grieving": "sadness",
    "angry": "anger",
    "annoyed": "anger",
    "furious": "anger",
    "jealous": "anger",
    "disgusted": "anger",
    "afraid": "fear",
    "terrified": "fear",
    "anxious": "fear",
    "apprehensive": "fear",
    "surprised": "surprise",
    "impressed": "surprise",
    "guilty": "guilt",
    "ashamed": "guilt",
    "embarrassed": "guilt",
    "caring": "love",
    "trusting": "love",
    "faithful": "love",
    "sentimental": "love",
}


LABELS: list[str] = [
    "anger",
    "fear",
    "guilt",
    "joy",
    "love",
    "sadness",
    "surprise",
]

LABEL2ID: dict[str, int] = {label: idx for idx, label in enumerate(LABELS)}
ID2LABEL: dict[int, str] = {idx: label for label, idx in LABEL2ID.items()}
