"""
predictor.py

Loads the already-trained Naive Bayes model and uses it to predict a
job_category for a given resume.

We assume the model has already been trained and saved to disk
(media/models/naive_bayes_model.pkl) along with its accuracy info
(media/models/model_metrics.json). This file does NOT train anything --
it only loads and predicts.
"""

import json
import os

from .naive_bayes import NaiveBayesClassifier
from .preprocessing import combine_feature_text


class JobPredictor:
    def __init__(
        self,
        model_path="media/models/naive_bayes_model.pkl",
        metrics_path="media/models/model_metrics.json",
    ):
        self.model_path = model_path
        self.metrics_path = metrics_path
        self.ready = False
        self.model_accuracy = 0.0

        self.model = NaiveBayesClassifier()
        self.load_everything()

    def load_everything(self):
        """Load the trained model file and the saved accuracy number."""
        if os.path.exists(self.model_path):
            self.model.load_model(self.model_path)
            self.ready = True
        else:
            print(f"WARNING: model file not found at {self.model_path}")

        self.model_accuracy = self.load_accuracy()

    def load_accuracy(self):
        """Read the accuracy number that was saved when the model was
        trained. Returns 0.0 if the file is missing or broken."""
        if not os.path.exists(self.metrics_path):
            return 0.0

        try:
            with open(self.metrics_path, "r", encoding="utf-8") as metrics_file:
                metrics = json.load(metrics_file)
            return float(metrics.get("accuracy", 0.0))
        except (ValueError, TypeError, OSError):
            return 0.0

    def predict_job(self, resume_text="", skills="", education="", experience="", min_confidence=0.15):
        """Predict a job_category for one resume. Returns a dictionary
        with job_category, confidence, and model_accuracy.

        If the model isn't confident about any single category (its top
        guess barely beats the rest), we return "Uncertain" instead of a
        specific job title, since a low-confidence guess is not much
        better than a random pick out of 150+ categories.
        """
        if not self.ready:
            return {"job_category": "Not Trained", "confidence": 0.0}

        feature_text = combine_feature_text(
            resume_text=resume_text,
            skills=skills,
            education=education,
            experience=experience,
        )

        results = self.model.predict([feature_text])
        result = results[0]

        # Keep confidence between 0 and 0.99 so the UI never shows a
        # slightly misleading "100% confident".
        confidence = float(result["confidence"])
        if confidence > 0.99:
            confidence = 0.99
        if confidence < 0.0:
            confidence = 0.0

        if confidence < min_confidence:
            return {
                "job_category": "Uncertain",
                "confidence": confidence,
                "model_accuracy": self.model_accuracy,
            }

        return {
            "job_category": str(result["label"]),
            "confidence": confidence,
            "model_accuracy": self.model_accuracy,
        }

    def predict_top_jobs(self, resume_text="", skills="", education="", experience="", top_n=3):
        """Predict the top N most likely job categories for one resume,
        ranked from most to least likely. Returns a list of dictionaries,
        each with job_category and confidence."""
        if not self.ready:
            return [{"job_category": "Not Trained", "confidence": 0.0}]

        feature_text = combine_feature_text(
            resume_text=resume_text,
            skills=skills,
            education=education,
            experience=experience,
        )

        top_results = self.model.predict_top([feature_text], top_n=top_n)[0]

        predictions = []
        for result in top_results:
            confidence = float(result["confidence"])
            if confidence > 0.99:
                confidence = 0.99
            if confidence < 0.0:
                confidence = 0.0

            display_confidence = float(result["display_confidence"])
            if display_confidence > 1.0:
                display_confidence = 1.0
            if display_confidence < 0.0:
                display_confidence = 0.0

            predictions.append({
                "job_category": str(result["label"]),
                "confidence": confidence,
                "display_confidence": display_confidence,
            })

        return predictions