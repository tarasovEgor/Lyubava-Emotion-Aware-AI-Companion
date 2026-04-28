FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV MODEL_DIR=/app/models/emotion_classifier

# run as non-root.
RUN useradd --create-home --shell /bin/bash appuser

# Copy package metadata and source.
COPY pyproject.toml ./
COPY src ./src

# Install the application package and dependencies.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy trained model artifact for local Docker testing.
# In future CI/CD, this should come from DVC, MLflow, object storage, or a model registry.
COPY models/emotion_classifier ./models/emotion_classifier

USER appuser

EXPOSE 8000

CMD ["uvicorn", "lyubava.api.main:app", "--host", "0.0.0.0", "--port", "8000"]