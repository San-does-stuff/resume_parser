import csv
import os
import random

from .naive_bayes import NaiveBayesClassifier
from .preprocessing import combine_feature_text

# Configuration
DATASET_PATH = "datasets/Ndataset_1.csv"
MODEL_PATH = "media/models/naive_bayes_model.pkl"

TRAIN_RATIO = 0.8
SEED = 42


def load_dataset(path: str) -> list[dict]:
    """Load dataset from CSV."""
    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [
            row
            for row in reader
            if row["job_category"] and row["resume_text"]
        ]


def prepare_text(row: dict) -> str:
    """Combine resume fields into one text."""
    return combine_feature_text(
        resume_text=row["resume_text"],
        skills=row["skills"],
        education=row["education"],
        experience=row["experience"],
    )


def calculate_accuracy(actual: list[str], predicted: list[str]) -> float:
    correct = sum(a == b for a, b in zip(actual, predicted))
    return correct / len(actual)


def train_model():

    rows = load_dataset(DATASET_PATH)

    random.seed(SEED)
    random.shuffle(rows)

    split = int(len(rows) * TRAIN_RATIO)

    train_rows = rows[:split]
    test_rows = rows[split:]

    X_train = [prepare_text(r) for r in train_rows]
    y_train = [r["job_category"] for r in train_rows]

    X_test = [prepare_text(r) for r in test_rows]
    y_test = [r["job_category"] for r in test_rows]

    model = NaiveBayesClassifier()

    model.train(X_train, y_train)

    predictions = model.predict(X_test)

    y_pred = [p["label"] for p in predictions]

    accuracy = calculate_accuracy(y_test, y_pred)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save_model(MODEL_PATH)

    print(f"Training samples : {len(train_rows)}")
    print(f"Testing samples  : {len(test_rows)}")
    print(f"Accuracy         : {accuracy:.2%}")
    print("Model saved.")


if __name__ == "__main__":
    train_model()