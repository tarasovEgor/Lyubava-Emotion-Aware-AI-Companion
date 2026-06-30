FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV MODEL_DIR=/app/models/emotion_classifier
ENV PATH="/app/.venv/bin:$PATH"

# run as non-root.
RUN useradd --create-home --shell /bin/bash appuser

# Copy package metadata and source.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY configs ./configs

# Install CPU PyTorch for local Docker deployments.
RUN pip install --no-cache-dir uv \
    && UV_INDEX_STRATEGY=unsafe-best-match \
       UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu \
       uv sync --frozen --no-dev --no-install-package torch \
    && UV_INDEX_STRATEGY=unsafe-best-match \
       uv pip install "torch>=2.6.0" --index-url https://download.pytorch.org/whl/cpu

# Copy trained model artifact for local Docker testing.
COPY models/emotion_classifier ./models/emotion_classifier
COPY data/processed/empatheticdialogues ./data/processed/empatheticdialogues
COPY monitoring/baselines ./monitoring/baselines

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "lyubava.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
