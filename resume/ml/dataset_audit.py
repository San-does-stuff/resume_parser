import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict


NOISE_SKILL_PATTERNS = (
    re.compile(r"^\d{1,4}$"),
    re.compile(r"^[0-9]+\.[0-9]+$"),
    re.compile(r"^(19|20)\d{2}$"),
    re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)$", re.IGNORECASE),
    re.compile(r"^[a-z]{1,2}$"),
)

LIKELY_LOCATION_TOKENS = {
    "new york",
    "san francisco",
    "los angeles",
    "chicago",
    "kathmandu",
    "lalitpur",
    "nepal",
}


def load_rows(dataset_path: str) -> list[dict[str, str]]:
    with open(dataset_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [row for row in reader]


def normalize_whitespace(value: str) -> str:
    return " ".join((value or "").split())


def split_skills(skills_value: str) -> list[str]:
    parts = re.split(r"[,;/|]+", skills_value or "")
    return [normalize_whitespace(token.lower()) for token in parts if normalize_whitespace(token)]


def is_noise_skill(skill: str) -> bool:
    if skill in LIKELY_LOCATION_TOKENS:
        return True
    return any(pattern.match(skill) for pattern in NOISE_SKILL_PATTERNS)


def text_fingerprint(text: str) -> str:
    normalized = normalize_whitespace((text or "").lower())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def audit_dataset(rows: list[dict[str, str]], top_k: int = 25) -> dict[str, object]:
    valid_rows = [r for r in rows if r.get("job_category") and r.get("resume_text")]
    row_count = len(valid_rows)

    class_counts = Counter(row.get("job_category", "").strip() for row in valid_rows)
    max_class = max(class_counts.values()) if class_counts else 0
    min_class = min(class_counts.values()) if class_counts else 0
    imbalance_ratio = (max_class / min_class) if min_class else 0.0

    skill_counter: Counter[str] = Counter()
    noise_skill_counter: Counter[str] = Counter()
    empty_skill_rows = 0

    text_hash_counts: Counter[str] = Counter()
    duplicate_group_examples: defaultdict[str, list[int]] = defaultdict(list)

    low_information_rows = 0
    very_long_rows = 0

    for idx, row in enumerate(valid_rows):
        resume_text = row.get("resume_text", "")
        token_count = len(normalize_whitespace(resume_text).split())
        if token_count < 30:
            low_information_rows += 1
        if token_count > 1800:
            very_long_rows += 1

        text_hash = text_fingerprint(resume_text)
        text_hash_counts[text_hash] += 1
        if len(duplicate_group_examples[text_hash]) < 5:
            duplicate_group_examples[text_hash].append(idx)

        raw_skills = row.get("skills", "")
        skills = split_skills(raw_skills)
        if not skills:
            empty_skill_rows += 1
        for skill in skills:
            skill_counter[skill] += 1
            if is_noise_skill(skill):
                noise_skill_counter[skill] += 1

    duplicated_text_rows = sum(count - 1 for count in text_hash_counts.values() if count > 1)
    duplicate_groups = [
        {"count": count, "row_indexes": duplicate_group_examples[text_hash]}
        for text_hash, count in text_hash_counts.items()
        if count > 1
    ]
    duplicate_groups.sort(key=lambda item: item["count"], reverse=True)

    top_classes = class_counts.most_common(top_k)
    bottom_classes = sorted(class_counts.items(), key=lambda item: item[1])[:top_k]

    top_skills = skill_counter.most_common(top_k)
    top_noise_skills = noise_skill_counter.most_common(top_k)

    return {
        "row_count": row_count,
        "class_count": len(class_counts),
        "class_imbalance_ratio": round(imbalance_ratio, 4),
        "top_classes": top_classes,
        "bottom_classes": bottom_classes,
        "empty_skills_rows": empty_skill_rows,
        "duplicated_text_rows": duplicated_text_rows,
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_groups_top": duplicate_groups[:top_k],
        "low_information_rows_lt_30_tokens": low_information_rows,
        "very_long_rows_gt_1800_tokens": very_long_rows,
        "top_skills": top_skills,
        "top_noise_skills": top_noise_skills,
        "data_quality_risks": build_risk_summary(
            row_count=row_count,
            imbalance_ratio=imbalance_ratio,
            duplicated_text_rows=duplicated_text_rows,
            empty_skill_rows=empty_skill_rows,
            noise_skill_total=sum(noise_skill_counter.values()),
        ),
    }


def build_risk_summary(
    row_count: int,
    imbalance_ratio: float,
    duplicated_text_rows: int,
    empty_skill_rows: int,
    noise_skill_total: int,
) -> list[str]:
    risks: list[str] = []
    if row_count == 0:
        return ["Dataset has no valid rows with job_category + resume_text."]
    if imbalance_ratio >= 8:
        risks.append(f"Severe class imbalance detected (max/min ratio={imbalance_ratio:.2f}).")
    elif imbalance_ratio >= 4:
        risks.append(f"Moderate class imbalance detected (max/min ratio={imbalance_ratio:.2f}).")
    if duplicated_text_rows > row_count * 0.15:
        risks.append("High resume duplication (>15%) may inflate validation scores.")
    if empty_skill_rows > row_count * 0.2:
        risks.append("Many rows have empty skill fields (>20%), feature quality is inconsistent.")
    if noise_skill_total > row_count:
        risks.append("Noise-like skill tokens are frequent; skills column needs cleaning.")
    if not risks:
        risks.append("No critical risk triggered by thresholds, but manual sampling is still recommended.")
    return risks


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit resume dataset quality.")
    parser.add_argument(
        "--dataset-path",
        default="datasets/structured_resume_dataset.csv",
        help="Path to CSV dataset.",
    )
    parser.add_argument(
        "--output-path",
        default="datasets/structured_resume_dataset.audit.json",
        help="Where to write audit JSON report.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=25,
        help="Top K items to include in frequency lists.",
    )
    args = parser.parse_args()

    rows = load_rows(args.dataset_path)
    report = audit_dataset(rows, top_k=args.top_k)

    with open(args.output_path, "w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)

    print(f"Audit complete. Rows: {report['row_count']}, classes: {report['class_count']}")
    print(f"Imbalance ratio (max/min): {report['class_imbalance_ratio']}")
    print(f"Duplicated text rows: {report['duplicated_text_rows']}")
    print(f"Empty skills rows: {report['empty_skills_rows']}")
    print(f"Report written to: {args.output_path}")


if __name__ == "__main__":
    main()
