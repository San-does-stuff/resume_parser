import math
import pickle
from collections import Counter, defaultdict

from .preprocessing import tokenize


class NaiveBayesClassifier:
    def __init__(self):
        self.class_priors: dict[str, float] = {}
        self.word_counts: dict[str, Counter[str]] = {}
        self.total_words_per_class: dict[str, int] = {}
        self.class_counts: dict[str, int] = {}
        self.vocabulary: set[str] = set()
        self.trained = False

    def train(self, X_train: list[str], y_train: list[str]) -> None:
        doc_count = len(X_train)
        if doc_count == 0:
            raise ValueError("Training data is empty.")
        if doc_count != len(y_train):
            raise ValueError("X_train and y_train length mismatch.")

        class_doc_counts: defaultdict[str, int] = defaultdict(int)
        class_word_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
        total_words_per_class: defaultdict[str, int] = defaultdict(int)

        for text, label in zip(X_train, y_train):
            class_doc_counts[label] += 1
            tokens = tokenize(text)
            self.vocabulary.update(tokens)
            for token in tokens:
                class_word_counts[label][token] += 1
                total_words_per_class[label] += 1

        self.class_priors = {label: count / doc_count for label, count in class_doc_counts.items()}
        self.word_counts = dict(class_word_counts)
        self.total_words_per_class = dict(total_words_per_class)
        self.class_counts = dict(class_doc_counts)
        self.trained = True

    def _score_tokens(self, tokens: list[str]) -> dict[str, float]:
        if not self.trained:
            raise ValueError("Model is not trained.")

        vocab_size = max(len(self.vocabulary), 1)
        scores: dict[str, float] = {}

        for label, prior in self.class_priors.items():
            score = math.log(prior)
            total_words = self.total_words_per_class.get(label, 0)
            for token in tokens:
                token_count = self.word_counts[label].get(token, 0)
                likelihood = (token_count + 1) / (total_words + vocab_size)
                score += math.log(likelihood)
            scores[label] = score
        return scores

    def predict(self, X_test: list[str]) -> list[dict[str, float | str]]:
        results: list[dict[str, float | str]] = []
        for text in X_test:
            tokens = tokenize(text)
            scores = self._score_tokens(tokens)
            predicted_label = max(scores, key=scores.get)
            confidence = self._confidence_from_log_scores(scores, predicted_label)
            results.append({"label": predicted_label, "confidence": confidence})
        return results

    def _confidence_from_log_scores(self, scores: dict[str, float], predicted_label: str) -> float:
        max_score = max(scores.values())
        stabilized = {label: math.exp(score - max_score) for label, score in scores.items()}
        denominator = sum(stabilized.values()) or 1.0
        return stabilized[predicted_label] / denominator

    def save_model(self, filepath: str) -> None:
        payload = {
            "class_priors": self.class_priors,
            "word_counts": self.word_counts,
            "total_words_per_class": self.total_words_per_class,
            "class_counts": self.class_counts,
            "vocabulary": self.vocabulary,
            "trained": self.trained,
        }
        with open(filepath, "wb") as model_file:
            pickle.dump(payload, model_file)

    def load_model(self, filepath: str) -> None:
        with open(filepath, "rb") as model_file:
            payload = pickle.load(model_file)
        self.class_priors = payload["class_priors"]
        self.word_counts = payload["word_counts"]
        self.total_words_per_class = payload["total_words_per_class"]
        self.class_counts = payload["class_counts"]
        self.vocabulary = payload["vocabulary"]
        self.trained = payload["trained"]
