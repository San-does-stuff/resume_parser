import csv
import json
import os
import random
import argparse
from collections import Counter

from .naive_bayes import NaiveBayesClassifier
from .preprocessing import combine_feature_text


def evaluate_model(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    if not y_true:
        return {"accuracy": 0.0}

    correct = sum(1 for true_label, pred_label in zip(y_true, y_pred) if true_label == pred_label)
    accuracy = correct / len(y_true)

    metrics = {"accuracy": accuracy}
    categories = sorted(set(y_true))

    for category in categories:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == p == category)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != category and p == category)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == category and p != category)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

        metrics[f"{category}_precision"] = precision
        metrics[f"{category}_recall"] = recall
        metrics[f"{category}_f1"] = f1

    return metrics


def train_and_save_model(
    dataset_path: str = "datasets/structured_resume_dataset.csv",
    cleaned_dataset_path: str = "datasets/structured_resume_dataset.cleaned.csv",
    prefer_cleaned_dataset: bool = True,
    rebalance_classes: bool = True,
    rebalance_target_count: int | None = None,
    model_output_path: str = "media/models/naive_bayes_model.pkl",
    metrics_output_path: str = "media/models/model_metrics.json",
    train_ratio: float = 0.8,
    seed: int = 42,
) -> dict[str, float]:
    selected_dataset_path = _select_dataset_path(
        dataset_path=dataset_path,
        cleaned_dataset_path=cleaned_dataset_path,
        prefer_cleaned_dataset=prefer_cleaned_dataset,
    )
    rows = _load_dataset(selected_dataset_path)
    if not rows:
        raise ValueError(f"No rows found in dataset: {selected_dataset_path}")

    random.Random(seed).shuffle(rows)

    split_idx = int(len(rows) * train_ratio)
    train_rows = rows[:split_idx]
    test_rows = rows[split_idx:]

    train_label_dist_before = Counter(row["job_category"] for row in train_rows)
    if rebalance_classes:
        train_rows = _rebalance_training_rows(
            train_rows=train_rows,
            seed=seed,
            target_count=rebalance_target_count,
        )
    train_label_dist_after = Counter(row["job_category"] for row in train_rows)

    X_train = [_to_feature_text(row) for row in train_rows]
    y_train = [row["job_category"] for row in train_rows]
    X_test = [_to_feature_text(row) for row in test_rows]
    y_test = [row["job_category"] for row in test_rows]

    classifier = NaiveBayesClassifier()
    classifier.train(X_train, y_train)

    predictions = classifier.predict(X_test)
    y_pred = [item["label"] for item in predictions]
    metrics = evaluate_model(y_test, y_pred)

    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    classifier.save_model(model_output_path)
    with open(metrics_output_path, "w", encoding="utf-8") as metrics_file:
        json.dump(metrics, metrics_file, indent=2)

    print(f"Dataset used: {selected_dataset_path}")
    print(f"Rebalancing enabled: {rebalance_classes}")
    if rebalance_classes:
        print(f"Train class distribution (before): {dict(train_label_dist_before)}")
        print(f"Train class distribution (after): {dict(train_label_dist_after)}")
    else:
        print(f"Train class distribution: {dict(train_label_dist_before)}")
    print(f"Trained on {len(train_rows)} rows, tested on {len(test_rows)} rows.")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    return metrics


def _load_dataset(dataset_path: str) -> list[dict[str, str]]:
    with open(dataset_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [row for row in reader if row.get("job_category") and row.get("resume_text")]


def _select_dataset_path(dataset_path: str, cleaned_dataset_path: str, prefer_cleaned_dataset: bool) -> str:
    if prefer_cleaned_dataset and os.path.exists(cleaned_dataset_path):
        return cleaned_dataset_path
    return dataset_path


def _rebalance_training_rows(
    train_rows: list[dict[str, str]],
    seed: int = 42,
    target_count: int | None = None,
) -> list[dict[str, str]]:
    if not train_rows:
        return train_rows

    grouped: dict[str, list[dict[str, str]]] = {}
    for row in train_rows:
        label = row["job_category"]
        grouped.setdefault(label, []).append(row)

    max_count = max(len(rows) for rows in grouped.values())
    desired_count = target_count if target_count and target_count > 0 else max_count

    rng = random.Random(seed)
    balanced_rows: list[dict[str, str]] = []
    for label, rows in grouped.items():
        balanced_rows.extend(rows)
        shortfall = desired_count - len(rows)
        if shortfall > 0:
            balanced_rows.extend(rng.choices(rows, k=shortfall))

    rng.shuffle(balanced_rows)
    return balanced_rows


def _to_feature_text(row: dict[str, str]) -> str:
    return combine_feature_text(
        resume_text=row.get("resume_text", ""),
        skills=row.get("skills", ""),
        education=row.get("education", ""),
        experience=row.get("experience", ""),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train resume classifier.")
    parser.add_argument("--dataset-path", default="datasets/structured_resume_dataset.csv")
    parser.add_argument("--cleaned-dataset-path", default="datasets/structured_resume_dataset.cleaned.csv")
    parser.add_argument("--prefer-cleaned-dataset", action="store_true", default=True)
    parser.add_argument("--disable-prefer-cleaned-dataset", action="store_true")
    parser.add_argument("--rebalance-classes", action="store_true", default=True)
    parser.add_argument("--disable-rebalance-classes", action="store_true")
    parser.add_argument("--rebalance-target-count", type=int, default=None)
    parser.add_argument("--model-output-path", default="media/models/naive_bayes_model.pkl")
    parser.add_argument("--metrics-output-path", default="media/models/model_metrics.json")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    prefer_cleaned = args.prefer_cleaned_dataset and not args.disable_prefer_cleaned_dataset
    rebalance = args.rebalance_classes and not args.disable_rebalance_classes

    train_and_save_model(
        dataset_path=args.dataset_path,
        cleaned_dataset_path=args.cleaned_dataset_path,
        prefer_cleaned_dataset=prefer_cleaned,
        rebalance_classes=rebalance,
        rebalance_target_count=args.rebalance_target_count,
        model_output_path=args.model_output_path,
        metrics_output_path=args.metrics_output_path,
        train_ratio=args.train_ratio,
        seed=args.seed,
    )
