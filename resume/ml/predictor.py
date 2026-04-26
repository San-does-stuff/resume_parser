import os
import json

from .naive_bayes import NaiveBayesClassifier
from .preprocessing import combine_feature_text


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
