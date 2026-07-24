import argparse
import csv
import hashlib
import re
from collections import Counter


SKILL_SPLIT_PATTERN = re.compile(r"[,;/|]+")
MULTISPACE_PATTERN = re.compile(r"\s+")

NOISE_SKILL_PATTERNS = (
    re.compile(r"^\d{1,4}$"),
    re.compile(r"^[0-9]+\.[0-9]+$"),
    re.compile(r"^(19|20)\d{2}$"),
    re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)$", re.IGNORECASE),
)

SKILL_ALIASES = {
    "node js": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "react js": "react",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "gcp": "google cloud",
    "aws cloud": "aws",
    "tailwindcss": "tailwind",
    "springboot": "spring boot",
    "ml": "machine learning",
    "nlp": "natural language processing",
}

LIKELY_LOCATION_TOKENS = {
    "new york",
    "san francisco",
    "los angeles",
    "chicago",
    "kathmandu",
    "lalitpur",
    "nepal",
}


def normalize_whitespace(value: str) -> str:
    return MULTISPACE_PATTERN.sub(" ", (value or "").strip())


def normalize_skill(skill: str) -> str:
    cleaned = normalize_whitespace(skill.lower())
    if cleaned in SKILL_ALIASES:
        cleaned = SKILL_ALIASES[cleaned]
    return cleaned


def is_noise_skill(skill: str) -> bool:
    if not skill:
        return True
    if skill in LIKELY_LOCATION_TOKENS:
        return True
    if len(skill) <= 1:
        return True
    return any(pattern.match(skill) for pattern in NOISE_SKILL_PATTERNS)


def split_and_clean_skills(skills_value: str) -> list[str]:
    raw_tokens = SKILL_SPLIT_PATTERN.split(skills_value or "")
    cleaned_tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        normalized = normalize_skill(token)
        if not normalized or is_noise_skill(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned_tokens.append(normalized)
    return cleaned_tokens


def text_fingerprint(text: str) -> str:
    normalized = normalize_whitespace((text or "").lower())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def load_rows(dataset_path: str) -> list[dict[str, str]]:
    with open(dataset_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [row for row in reader]


def clean_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    seen_resume_hashes: set[str] = set()
    cleaned: list[dict[str, str]] = []
    stats = Counter()

    for row in rows:
        job_category = normalize_whitespace(row.get("job_category", ""))
        resume_text = normalize_whitespace(row.get("resume_text", ""))

        if not job_category or not resume_text:
            stats["dropped_missing_required"] += 1
            continue

        resume_hash = text_fingerprint(resume_text)
        if resume_hash in seen_resume_hashes:
            stats["dropped_duplicate_resume_text"] += 1
            continue
        seen_resume_hashes.add(resume_hash)

        cleaned_row = dict(row)
        cleaned_row["job_category"] = job_category
        cleaned_row["resume_text"] = resume_text
        cleaned_row["education"] = normalize_whitespace(row.get("education", ""))
        cleaned_row["experience"] = normalize_whitespace(row.get("experience", ""))

        cleaned_skills = split_and_clean_skills(row.get("skills", ""))
        cleaned_row["skills"] = ", ".join(cleaned_skills)

        if not cleaned_skills:
            stats["rows_with_empty_skills_after_cleaning"] += 1

        cleaned.append(cleaned_row)
        stats["kept_rows"] += 1

    return cleaned, dict(stats)


def write_rows(output_path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean resume dataset for training.")
    parser.add_argument(
        "--input-path",
        default="datasets/structured_resume_dataset.csv",
        help="Input CSV dataset path.",
    )
    parser.add_argument(
        "--output-path",
        default="datasets/structured_resume_dataset.cleaned.csv",
        help="Output CSV dataset path.",
    )
    args = parser.parse_args()

    rows = load_rows(args.input_path)
    if not rows:
        raise ValueError("No rows found in input dataset.")
    fieldnames = list(rows[0].keys())

    cleaned_rows, stats = clean_rows(rows)
    write_rows(args.output_path, cleaned_rows, fieldnames)

    print(f"Input rows: {len(rows)}")
    print(f"Cleaned rows: {len(cleaned_rows)}")
    print(f"Dropped duplicates: {stats.get('dropped_duplicate_resume_text', 0)}")
    print(f"Dropped missing required fields: {stats.get('dropped_missing_required', 0)}")
    print(f"Rows with empty skills after cleaning: {stats.get('rows_with_empty_skills_after_cleaning', 0)}")
    print(f"Wrote cleaned dataset: {args.output_path}")


if __name__ == "__main__":
    main()
