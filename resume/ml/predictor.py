import os
import json
import logging
from pathlib import Path

from .naive_bayes import NaiveBayesClassifier
from .preprocessing import combine_feature_text
from .train_model import train_and_save_model


logger = logging.getLogger(__name__)


def ensure_model_artifacts(
    model_path: str = "media/models/naive_bayes_model.pkl",
    metrics_path: str = "media/models/model_metrics.json",
) -> None:
    model_file = Path(model_path)
    metrics_file = Path(metrics_path)
    if model_file.exists() and metrics_file.exists():
        return

    enhanced_dataset = Path("datasets/structured_resume_dataset.enhanced.csv")
    enhanced_cleaned = Path("datasets/structured_resume_dataset.enhanced.cleaned.csv")
    default_dataset = Path("datasets/structured_resume_dataset.csv")
    default_cleaned = Path("datasets/structured_resume_dataset.cleaned.csv")

    dataset_path = enhanced_dataset if enhanced_dataset.exists() else default_dataset
    cleaned_path = enhanced_cleaned if enhanced_cleaned.exists() else default_cleaned

    logger.warning(
        "Model artifacts missing. Auto-training model with dataset=%s cleaned=%s",
        dataset_path,
        cleaned_path,
    )
    train_and_save_model(
        dataset_path=str(dataset_path),
        cleaned_dataset_path=str(cleaned_path),
        prefer_cleaned_dataset=True,
        model_output_path=model_path,
        metrics_output_path=metrics_path,
    )


class JobPredictor:
    def __init__(
        self,
        model_path: str = "media/models/naive_bayes_model.pkl",
        metrics_path: str = "media/models/model_metrics.json",
    ):
        self.model_path = model_path
        self.metrics_path = metrics_path
        self.model = NaiveBayesClassifier()
        self.ready = False
        self.model_accuracy = 0.0

        if os.path.exists(model_path):
            self.model.load_model(model_path)
            self.ready = True
        self.model_accuracy = self._load_model_accuracy()

    def predict_job(self, resume_text: str, skills: str = "", education: str = "", experience: str = "") -> dict[str, str | float]:
        if not self.ready:
            return {"job_category": "Not Trained", "confidence": 0.0}

        feature_text = combine_feature_text(
            resume_text=resume_text,
            skills=skills,
            education=education,
            experience=experience,
        )
        result = self.model.predict([feature_text])[0]
        # Keep confidence in a realistic UI range; avoid absolute 100% display.
        confidence = float(result["confidence"])
        confidence = min(max(confidence, 0.0), 0.99)
        return {
            "job_category": str(result["label"]),
            "confidence": confidence,
            "model_accuracy": self.model_accuracy,
        }

    def _load_model_accuracy(self) -> float:
        if not os.path.exists(self.metrics_path):
            return 0.0
        try:
            with open(self.metrics_path, "r", encoding="utf-8") as metrics_file:
                metrics = json.load(metrics_file)
            return float(metrics.get("accuracy", 0.0))
        except (ValueError, TypeError, OSError):
            return 0.0
