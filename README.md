# Lyubava — Emotion-Aware AI Companion

## ✨ Overview

**Lyubava** is an emotion-aware AI companion designed to make conversations feel more human, supportive, and emotionally intelligent.

It analyzes the tone of user messages, estimates the user's emotional state, and adapts its reply style accordingly — whether the moment calls for support, motivation, light humor, or a calm neutral tone.

Unlike generic assistants, Lyubava also maintains an internal **mood model** that can evolve through conversation history, creating a stronger sense of continuity, personality, and warmth.

---

## 🌸 Core Idea

Lyubava is a virtual AI companion that can:

- analyze message tone and sentiment
- detect emotional cues in text
- infer the user’s emotional state
- choose the most fitting response style
- maintain a lightweight emotional memory
- adjust its own “mood” over time based on interactions
- provide warm, safe, and consistent companionship

---

## 🧠 Key Features

### 1. Adaptive Communication Style

Depending on the detected emotional state and conversation context, Lyubava can respond in different styles:

- **Supportive** — empathy, softness, reassurance
- **Motivational** — encouragement, confidence, forward movement
- **Playful** — light humor, warmth, energy
- **Neutral** — calm, balanced, practical communication

### 2. Persistent Mood Model

Lyubava has an internal emotional state that may shift based on:

- recent conversations
- recurring user mood patterns
- interaction frequency
- positive or negative conversational momentum

This creates a stronger feeling of continuity and character.

### 3. Conversational Memory

The system can remember selected non-sensitive information such as:

- preferred response tone
- topics the user enjoys
- emotional tendencies over time
- what kind of support feels most useful

---

## 📁 Suggested Project Structure

    src/
└── lyubava/
    ├── raw/
    │   ├── train.csv
    │   ├── valid.csv
    │   └── test.csv
    ├── data/
    │   ├── emotions.py
    │   └── prepare.py
    ├── models/
    │   ├── train.py
    │   ├── evaluate.py
    │   └── predict.py
    ├── api/
    │   ├── schemas.py
    │   └── main.py
    ├── companion/
    ├── monitoring/
    └── utils/

scripts/
├── prepare_data.py
├── run_emotion_pipeline.py
├── evaluate_model.py
├── smoke_predict.py
└── run_api.py   # optional local convenience only, not needed for Docker

---