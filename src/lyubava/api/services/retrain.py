from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Literal

from lyubava.core.config import Settings
from lyubava.models.train import train

RetrainState = Literal["idle", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class RetrainStatus:
    state: RetrainState
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
    metrics: dict[str, Any] | None = None


class RetrainService:
    def __init__(
        self,
        settings: Settings,
        data_dir: Path = Path("data/processed/empatheticdialogues"),
        mlflow_config: Path = Path("configs/mlflow.yaml"),
    ) -> None:
        self._settings = settings
        self._data_dir = data_dir
        self._mlflow_config = mlflow_config
        self._lock = Lock()
        self._status = RetrainStatus(state="idle")

    def get_status(self) -> RetrainStatus:
        with self._lock:
            return self._status

    def start(self) -> RetrainStatus:
        with self._lock:
            if self._status.state == "running":
                return self._status

            self._status = RetrainStatus(
                state="running",
                started_at=datetime.now(UTC).isoformat(),
                message="Retraining started.",
            )

        worker = Thread(target=self._run_training, daemon=True)
        worker.start()
        return self.get_status()

    def _run_training(self) -> None:
        started_at = datetime.now(UTC).isoformat()
        try:
            metrics = train(
                data_dir=self._data_dir,
                output_dir=Path(self._settings.model_dir),
                model_name="distilbert-base-uncased",
                max_length=128,
                learning_rate=2e-5,
                train_batch_size=16,
                eval_batch_size=16,
                num_train_epochs=3,
                weight_decay=0.01,
                seed=42,
                mlflow_config_path=self._mlflow_config,
                enable_mlflow=True,
                use_cpu=True,
            )
            finished_at = datetime.now(UTC).isoformat()
            with self._lock:
                self._status = RetrainStatus(
                    state="succeeded",
                    started_at=started_at,
                    finished_at=finished_at,
                    message="Retraining completed successfully.",
                    metrics=metrics,
                )
        except Exception as exc:  # pragma: no cover - defensive status reporting
            finished_at = datetime.now(UTC).isoformat()
            with self._lock:
                self._status = RetrainStatus(
                    state="failed",
                    started_at=started_at,
                    finished_at=finished_at,
                    message=f"Retraining failed: {exc}",
                )
