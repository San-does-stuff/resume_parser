import math
import pickle
from collections import Counter, defaultdict
import sys
sys.modules["naive_bayes"] = sys.modules[__name__]

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

    def predict_top(self, X_test: list[str], top_n: int = 3, display_temperature: float = 10.0) -> list[list[dict[str, float | str]]]:
        """
        Like predict(), but instead of only returning the single best
        guess, this returns the top "top_n" guesses for each piece of
        text, ranked from most likely to least likely.

        Each guess includes two different confidence numbers:
        - "confidence": the model's real, unmodified probability. Naive
          Bayes tends to be overconfident (it multiplies many word
          probabilities together as if they were independent), so the
          winning class can end up with 99%+ while #2 and #3 round down
          to 0%, even though the model did still "consider" them.
        - "display_confidence": the same ranking, but softened using a
          technique called temperature scaling, so the numbers are more
          readable and comparable to each other (e.g. 45% / 33% / 22%
          instead of 99% / 0% / 0%). This does NOT change which label
          wins -- it only spreads the percentages out for display.

        Returns a list (one item per input text) of lists of
        {"label": ..., "confidence": ..., "display_confidence": ...}.
        """
        all_results: list[list[dict[str, float | str]]] = []

        for text in X_test:
            tokens = tokenize(text)
            scores = self._score_tokens(tokens)

            true_probabilities = self._scores_to_probabilities(scores, temperature=1.0)
            display_probabilities = self._scores_to_probabilities(scores, temperature=display_temperature)

            # Rank by the TRUE probabilities (temperature never changes
            # which label is more likely, only how spread out the numbers
            # look, but we rank on the real numbers to be safe).
            ranked_labels = sorted(true_probabilities.items(), key=lambda item: item[1], reverse=True)
            top_labels = ranked_labels[:top_n]

            text_results = []
            for label, confidence in top_labels:
                text_results.append({
                    "label": label,
                    "confidence": confidence,
                    "display_confidence": display_probabilities[label],
                })

            all_results.append(text_results)

        return all_results

    def _scores_to_probabilities(self, scores: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
        """Turn raw log-scores into normal 0-1 probabilities that add up to 1.

        "temperature" softens or sharpens the result without changing the
        ranking: temperature=1.0 gives the true probabilities, while a
        higher temperature (like 10) spreads the numbers out to be more
        human-readable when one class dominates too heavily.
        """
        max_score = max(scores.values())
        stabilized = {
            label: math.exp((score - max_score) / temperature)
            for label, score in scores.items()
        }
        total = sum(stabilized.values()) or 1.0

        probabilities = {}
        for label, value in stabilized.items():
            probabilities[label] = value / total

        return probabilities

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

        # Newer model files are saved as a plain dictionary (see save_model
        # above). Older model files were saved by pickling the whole
        # NaiveBayesClassifier object directly, so "payload" comes back as
        # an object instead of a dict. Handle both cases here so either
        # kind of saved file can still be loaded.
        if isinstance(payload, dict):
            data = payload
        else:
            data = payload.__dict__

        self.class_priors = data["class_priors"]
        self.word_counts = data["word_counts"]
        self.total_words_per_class = data["total_words_per_class"]
        self.class_counts = data["class_counts"]
        self.vocabulary = data["vocabulary"]
        self.trained = data["trained"]